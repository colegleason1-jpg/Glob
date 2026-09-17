"""Each check has to do two things: fire on the defect, and stay silent otherwise.

The second half is the one that decides whether this is a tool or a nuisance. A check
that flags everything is noise, gets switched off in the first week, and takes the real
findings with it — so every check here is tested against input it must NOT flag.
"""

from __future__ import annotations

import datetime
import random

import pandas as pd
import pytest

from unstated import (CATALOGUE, check_certificate_dates, check_dates,
                      check_hook_precedence, measure_contention,
                      check_detected_encoding,
                      check_domain_encoding, check_merge,
                      check_response_encoding, check_retry,
                      check_paginated, check_specifier,
                      check_split)


# --------------------------------------------------------------------------- #
# dates
# --------------------------------------------------------------------------- #

def _dates(n=400, seed=7):
    rng = random.Random(seed)
    start = datetime.date(2023, 1, 1)
    return [start + datetime.timedelta(days=rng.randrange(365)) for _ in range(n)]


def test_a_day_first_column_is_flagged():
    """The measured case: 37.2% of such a column parses wrong under the defaults."""
    finding = check_dates(d.strftime("%d/%m/%Y") for d in _dates())
    assert finding is not None
    assert finding.severity == "high"
    assert float(finding.observed["rate"].rstrip("%")) > 20.0
    assert "isoparse" in finding.remedy


def test_a_us_column_is_flagged_too():
    """Ambiguity is symmetric. A US-ordered column is just as convention-dependent —
    it happens to be right under the default, which is luck, not safety."""
    assert check_dates(d.strftime("%m/%d/%Y") for d in _dates()) is not None


def test_a_month_name_column_is_not_flagged():
    """The silence case that matters most: an unambiguous format must pass clean."""
    assert check_dates(d.strftime("%d %b %Y") for d in _dates()) is None


def test_an_empty_or_unparseable_column_is_not_flagged():
    """Unparseable input is a different problem, and a loud one. Not this check's job."""
    assert check_dates([]) is None
    assert check_dates(["", "   ", "not a date", "banana"]) is None


def test_iso_is_flagged_and_the_reason_is_in_the_remedy():
    """ISO reads correctly under the default and is transposed by dayfirst=True, so it
    IS convention-dependent — dateutil/dateutil#402. Flagging it is correct, and the
    remedy has to say why, or the finding reads as a false positive."""
    finding = check_dates(d.isoformat() for d in _dates())
    assert finding is not None
    assert "isoparse" in finding.remedy and "#402" in finding.remedy


# --------------------------------------------------------------------------- #
# merge
# --------------------------------------------------------------------------- #

def test_a_many_to_many_join_is_flagged_with_its_real_inflation():
    left = pd.DataFrame({"k": [1, 1, 2, 3], "v": [10, 20, 30, 40]})
    right = pd.DataFrame({"k": [1, 1, 2], "w": ["a", "b", "c"]})
    finding = check_merge(left, right, on="k")
    assert finding is not None
    # k=1: 2 left x 2 right = 4; k=2: 1 x 1 = 1. Five rows out of three matching in.
    assert finding.observed["rows_out"] == 5
    assert finding.observed["matching_rows_in"] == 3
    assert pd.merge(left, right, on="k").shape[0] == finding.observed["rows_out"], (
        "the predicted row count must match what merge actually produces"
    )


def test_a_many_to_one_join_is_not_flagged():
    """The common, safe case. Flagging it would make the check useless."""
    left = pd.DataFrame({"k": [1, 1, 2, 3], "v": [10, 20, 30, 40]})
    right = pd.DataFrame({"k": [1, 2, 3], "w": ["a", "b", "c"]})
    assert check_merge(left, right, on="k") is None


def test_duplicates_on_both_sides_that_never_meet_are_not_flagged():
    """Duplicate keys are not the defect — duplicate keys that MATCH are. A check that
    fired on the former would cry wolf on every join against a reference table."""
    left = pd.DataFrame({"k": [1, 1, 2], "v": [1, 2, 3]})
    right = pd.DataFrame({"k": [8, 8, 9], "w": ["a", "b", "c"]})
    assert check_merge(left, right, on="k") is None


def test_composite_keys_are_handled():
    left = pd.DataFrame({"a": [1, 1], "b": ["x", "x"], "v": [1, 2]})
    right = pd.DataFrame({"a": [1, 1], "b": ["x", "x"], "w": [3, 4]})
    finding = check_merge(left, right, on=["a", "b"])
    assert finding is not None and finding.observed["rows_out"] == 4


def test_a_missing_key_column_is_an_error_not_a_finding():
    left = pd.DataFrame({"k": [1]})
    right = pd.DataFrame({"j": [1]})
    with pytest.raises(KeyError):
        check_merge(left, right, on="k")


# --------------------------------------------------------------------------- #
# catalogue
# --------------------------------------------------------------------------- #

def test_every_catalogue_entry_carries_its_evidence_and_a_measured_cost():
    """An entry without a number is an opinion. The catalogue is only worth something
    if each row can be checked by the reader against the run that produced it."""
    assert CATALOGUE, "the catalogue is empty"
    for entry in CATALOGUE:
        assert entry.evidence.endswith(".md"), entry
        assert any(ch.isdigit() for ch in entry.cost_when_violated), (
            f"{entry} states no measured cost"
        )
        assert entry.upstream_status, entry


# --------------------------------------------------------------------------- #
# splits
# --------------------------------------------------------------------------- #

def test_repeated_subjects_are_flagged():
    """The measured case: 8 rows per subject overstates accuracy by 14.8%."""
    groups = [s for s in range(150) for _ in range(8)]
    finding = check_split(groups)
    assert finding is not None
    assert finding.severity == "high"
    assert finding.observed["distinct_groups"] == 150
    assert finding.observed["largest_group"] == 8
    assert "GroupShuffleSplit" in finding.remedy


def test_one_row_per_subject_is_not_flagged():
    """The silence case. Independent rows are exactly what the default is for."""
    assert check_split(range(500)) is None
    assert check_split([]) is None


def test_a_single_repeated_subject_is_flagged_but_not_as_high():
    """Severity has to track how much of the data is affected, or every frame with one
    accidental duplicate reads as an emergency and the check gets ignored."""
    groups = list(range(200)) + [7]
    finding = check_split(groups)
    assert finding is not None and finding.severity == "medium"


# --------------------------------------------------------------------------- #
# aws pagination
# --------------------------------------------------------------------------- #

def test_a_truncated_s3_response_is_flagged():
    """The measured case: 1,000 of 2,500 objects, IsTruncated the only signal."""
    response = {"Contents": [{"Key": f"k{i}"} for i in range(1000)],
                "IsTruncated": True, "KeyCount": 1000}
    finding = check_paginated(response, operation="list_objects_v2")
    assert finding is not None
    assert finding.observed["records_in_this_page"] == 1000
    assert "IsTruncated" in finding.observed["truncation_markers"]
    assert "get_paginator" in finding.remedy


def test_a_truncated_dynamodb_response_is_flagged_by_a_different_marker():
    """DynamoDB signals with LastEvaluatedKey, not IsTruncated. A check that only knew
    one marker would pass the service whose cutoff is hardest to notice."""
    response = {"Items": [{"id": {"S": "x"}}] * 49, "Count": 49,
                "LastEvaluatedKey": {"id": {"S": "000048"}}}
    finding = check_paginated(response, operation="scan")
    assert finding is not None
    assert "LastEvaluatedKey" in finding.observed["truncation_markers"]


def test_a_complete_response_is_not_flagged():
    """The silence case. IsTruncated present and False must read as complete."""
    assert check_paginated({"Contents": [{"Key": "a"}], "IsTruncated": False}) is None
    assert check_paginated({"Items": [], "Count": 0}) is None
    assert check_paginated({}) is None
    assert check_paginated("not a mapping") is None


def test_an_empty_token_is_not_a_truncation():
    """Some services return the marker key with an empty value on the last page.
    Treating that as truncation would flag every complete result."""
    assert check_paginated({"Contents": [], "NextToken": ""}) is None
    assert check_paginated({"Items": [], "LastEvaluatedKey": {}}) is None


def test_every_entry_states_the_claim_the_caller_thinks_they_have():
    """A bug is code telling its user something false about the world they care about.

    So every entry names the sentence the caller believes the return value asserts, and
    the sentence it actually asserts. An entry that only describes code behaviour has not
    identified the bug — it has described the mechanism and stopped.
    """
    for entry in CATALOGUE:
        assert entry.impact is not None, f"{entry} has no impact section"
        i = entry.impact
        assert i.believed_claim.endswith("."), (
            f"{entry}: believed_claim should read as a sentence the caller would say"
        )
        assert i.believed_claim != i.actual_claim, entry
        assert any(ch.isdigit() for ch in i.actual_claim), (
            f"{entry}: the actual claim must carry the measured number, not a description"
        )
        assert i.breaks and i.detection, entry


def test_consequences_are_not_asserted_about_anyone_in_particular():
    """The domain is whatever the caller's domain is — oranges, prescriptions, files,
    money. What an entry must never do is assert what a named party experienced, because
    nobody measured that. An invented consequence is the same unmeasured claim this
    catalogue exists to catch, and it collapses the first time somebody checks it.
    """
    for entry in CATALOGUE:
        text = entry.impact.breaks
        assert len(text) > 120, f"{entry}: breaks is too thin to have been thought through"
        # Stated as what stops being true, not as a loss someone suffered.
        for invented in ("cost them", "lost them", "would lose", "costs the industry",
                         "millions", "billions"):
            assert invented not in text.lower(), (
                f"{entry}: breaks asserts a consequence nobody measured ({invented!r})"
            )


# --------------------------------------------------------------------------- #
# version specifiers
# --------------------------------------------------------------------------- #

def test_a_specifier_that_silently_excludes_prereleases_is_flagged():
    """'>=1.0' reads as 'orders at or above 1.0'. It rejects 2.0rc1, which does."""
    finding = check_specifier(">=1.0", ["1.5", "2.0", "2.0rc1", "2.0.dev1"])
    assert finding is not None
    assert finding.observed["stricter_than_it_reads"] == 2
    assert finding.observed["looser_than_it_reads"] == 0
    assert finding.severity == "medium"
    assert "prereleases=True" in finding.remedy


def test_an_exact_pin_that_accepts_a_local_build_is_flagged_high():
    """The sharper direction: '==2.0' accepts 2.0+patched.by.vendor. An exact pin is
    what people write when they mean this artifact and no other, so a finding here is
    about what is running, not about which version resolved."""
    finding = check_specifier("==2.0", ["2.0", "2.0+local", "2.0+patched.by.vendor"])
    assert finding is not None
    assert finding.observed["looser_than_it_reads"] == 2
    assert finding.severity == "high", "accepting the wrong artifact outranks strictness"
    assert "pin the artifact by hash" in finding.remedy


def test_a_specifier_decided_entirely_by_ordering_is_not_flagged():
    """The silence case. Plain final releases against a plain bound must pass clean, or
    the check fires on every requirements file in existence."""
    assert check_specifier(">=1.0", ["1.0", "1.5", "2.0", "3.1"]) is None
    assert check_specifier(">=1.0,<3.0", ["1.0", "2.5"]) is None


def test_unparseable_input_is_skipped_rather_than_flagged():
    """Versions that are not PEP 440 and specifiers that are not specifiers are somebody
    else's problem, and a loud one."""
    assert check_specifier(">=1.0", ["not-a-version", "also bad"]) is None
    assert check_specifier("this is not a specifier", ["1.0"]) is None
    assert check_specifier(">=1.0", []) is None


# --------------------------------------------------------------------------- #
# domain encoding
# --------------------------------------------------------------------------- #

def test_domains_that_encode_to_two_different_hosts_are_flagged():
    """The measured case: the German sharp s yields two registrable names."""
    finding = check_domain_encoding(["straße.de", "faß.de"])
    assert finding is not None
    assert finding.severity == "high"
    assert finding.observed["both_valid_but_different"] == 2
    assert "uts46=True does not reconcile" in finding.remedy


def test_the_domains_most_test_suites_use_are_not_flagged():
    """The silence case, and the reason this defect survives: umlauts, accents and CJK
    encode identically under both standards. A suite exercising these sees nothing, which
    is exactly why a check is needed rather than a test."""
    assert check_domain_encoding(["bücher.de", "café.fr", "日本.jp", "zürich.ch"]) is None
    assert check_domain_encoding(["example.com", "sub.example.co.uk"]) is None
    assert check_domain_encoding([]) is None
    assert check_domain_encoding(["", "   "]) is None


def test_a_name_one_encoder_refuses_is_flagged_as_a_disagreement():
    """A validation step and a fetch step disagreeing about whether the input is a domain
    at all is the same class of split, and must not be silently dropped."""
    finding = check_domain_encoding(["ﬁ.example"])
    assert finding is not None
    assert finding.observed["one_encoder_refused"] == 1


def test_the_readme_table_matches_the_catalogue():
    """The README went stale by three audits before anyone noticed, which is the same
    failure this whole catalogue is about: a document claiming something the code no
    longer supports. So the table is generated, and this test is what keeps it honest.
    """
    import pathlib

    readme = pathlib.Path(__file__).resolve().parents[2] / "README.md"
    text = readme.read_text()
    block = text.split("<!-- BEGIN CATALOGUE TABLE")[1].split("<!-- END CATALOGUE TABLE")[0]
    for entry in CATALOGUE:
        assert f"`{entry.library}`" in block, (
            f"{entry.library} is in the catalogue but not in the README table — "
            "regenerate it"
        )
    listed = block.count("\n|") - 2  # header and separator
    assert listed == len(CATALOGUE), (
        f"README table has {listed} rows, catalogue has {len(CATALOGUE)}"
    )

    # The prose counts drifted independently of the table, so they are generated too.
    stated = text.split("<!-- CATALOGUE COUNT -->")[1].split("<!--")[0]
    assert int(stated) == len(CATALOGUE), (
        f"README says {stated} entries, catalogue has {len(CATALOGUE)}"
    )
    stated = text.split("<!-- PROJECT COUNT -->")[1].split("<!--")[0].strip()
    assert int(stated) == len({e.library for e in CATALOGUE}), (
        f"README says {stated} projects, catalogue covers "
        f"{len({e.library for e in CATALOGUE})}"
    )


# --------------------------------------------------------------------------- #
# retries
# --------------------------------------------------------------------------- #

def test_the_default_retry_that_retries_no_status_is_flagged():
    """Retry(total=3) reads as 'try three more times'. Measured against a 503 it sends
    one request, because status_forcelist is empty."""
    from urllib3.util.retry import Retry

    finding = check_retry(Retry(total=3))
    assert finding is not None
    assert finding.severity == "high"
    assert finding.observed["status_forcelist"] == "empty"
    assert "500, 502, 503, 504" in finding.remedy


def test_retrying_statuses_with_no_backoff_is_flagged():
    """The second default, exposed by fixing the first: four attempts in 0.00 seconds at
    a service that is already failing."""
    from urllib3.util.retry import Retry

    finding = check_retry(Retry(total=3, status_forcelist=[503]))
    assert finding is not None
    assert "backoff_factor is 0" in finding.observed["gaps"]


def test_opening_up_every_method_is_flagged():
    """The opposite mistake, usually made while fixing the first two: a POST replayed."""
    from urllib3.util.retry import Retry

    finding = check_retry(
        Retry(total=3, status_forcelist=[503], backoff_factor=0.5, allowed_methods=None)
    )
    assert finding is not None
    assert "non-idempotent request is replayed" in finding.observed["gaps"]


def test_a_considered_retry_configuration_is_not_flagged():
    """The silence case. Someone who named what they are retrying, spaced the attempts,
    and left the method set alone must not be nagged."""
    from urllib3.util.retry import Retry

    assert check_retry(
        Retry(total=3, status_forcelist=[500, 502, 503, 504], backoff_factor=0.5)
    ) is None


def test_retries_turned_off_are_not_flagged():
    """total=0 promises nothing, so there is nothing to be wrong about."""
    from urllib3.util.retry import Retry

    assert check_retry(Retry(total=0)) is None
    assert check_retry(Retry(total=False)) is None


# --------------------------------------------------------------------------- #
# response encoding
#
# These run against a real local HTTP server rather than a stub, because the whole
# finding is about what requests does with a header on the wire. A stub would let the
# test agree with my reading of the source instead of with the library.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def serve():
    """Serve a body under a chosen Content-Type. The type travels base64 in the path so
    a space or semicolon cannot mangle the request line — an earlier version of this
    probe did exactly that and produced a bogus result."""
    import base64
    import http.server
    import socketserver
    import threading

    state: dict[str, bytes] = {"body": b""}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            token = self.path.lstrip("/")
            self.send_response(200)
            if token != "none":
                self.send_header(
                    "Content-Type", base64.urlsafe_b64decode(token.encode()).decode()
                )
            self.send_header("Content-Length", str(len(state["body"])))
            self.end_headers()
            self.wfile.write(state["body"])

        def log_message(self, *a):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    def get(content_type, body):
        import requests

        state["body"] = body
        token = (
            "none" if content_type is None
            else base64.urlsafe_b64encode(content_type.encode()).decode()
        )
        return requests.get(f"http://127.0.0.1:{port}/{token}")

    yield get
    server.shutdown()


def test_utf8_served_as_text_plain_comes_back_wrong_and_is_flagged(serve):
    """The measurement this entry exists for: the bytes are UTF-8, the server declared no
    charset, and r.text is mojibake with no exception and no warning."""
    truth = "Käse und Brötchen für alle"
    response = serve("text/plain", truth.encode("utf-8"))

    assert response.text != truth                      # the library, not the check
    assert response.encoding == "ISO-8859-1"
    assert len(response.text) == len(truth) + 3        # three umlauts, one extra char each

    finding = check_response_encoding(response)
    assert finding is not None
    assert finding.severity == "high"
    assert finding.observed["body_is_valid_utf8"] == "yes"
    assert finding.observed["utf8_sample"].startswith("Käse")


def test_the_right_answer_was_available_on_the_same_object(serve):
    """apparent_encoding is computed by the same Response and is not consulted, because
    the header rule already produced an answer. This is what makes it a defect rather
    than a hard problem."""
    truth = "Aktivität – naïve café — 日本 — £5"
    response = serve("text/csv", truth.encode("utf-8"))

    assert response.text != truth
    assert response.content.decode(response.apparent_encoding) == truth


def test_an_ascii_body_is_not_flagged(serve):
    """Why this survives a test suite, and why the check must stay quiet about it: ASCII
    is a fixed point of Latin-1, so nothing is being decided."""
    response = serve("text/csv", b"item,qty\nwidget,2\n")

    assert response.text == "item,qty\nwidget,2\n"
    assert check_response_encoding(response) is None


def test_a_declared_charset_is_not_flagged(serve):
    """The server said so. There is no assumption left to be wrong about."""
    truth = "café"
    response = serve("text/plain; charset=utf-8", truth.encode("utf-8"))

    assert response.text == truth
    assert check_response_encoding(response) is None


def test_application_json_is_not_flagged(serve):
    """requests assumes UTF-8 for JSON per RFC 4627, which is the correct assumption."""
    truth = '{"item": "café"}'
    response = serve("application/json", truth.encode("utf-8"))

    assert response.text == truth
    assert check_response_encoding(response) is None


def test_json_labelled_as_text_is_flagged_because_r_json_inherits_it(serve):
    """A server that labels JSON text/plain is common, and r.json() decodes through
    r.text, so the structured value is mojibake too."""
    response = serve("text/plain", '{"item": "café", "qty": 2}'.encode("utf-8"))

    assert response.json()["item"] != "café"
    assert check_response_encoding(response) is not None


def test_the_rule_is_a_substring_test_not_a_media_type_test(serve):
    """'text' in content_type, so a media type that merely contains the letters is
    treated as legacy text."""
    truth = "café"
    response = serve("application/x-subrip-text", truth.encode("utf-8"))

    assert response.encoding == "ISO-8859-1"
    assert response.text != truth
    assert check_response_encoding(response) is not None


def test_the_rule_is_case_sensitive_though_media_types_are_not(serve):
    """RFC 9110 §8.3.1: media type tokens are case-insensitive. Two servers sending
    identical bytes under the same media type hand the caller different strings."""
    truth = "café"

    lower = serve("text/plain", truth.encode("utf-8"))
    upper = serve("TEXT/PLAIN", truth.encode("utf-8"))

    assert lower.text != truth
    assert upper.text == truth
    assert check_response_encoding(lower) is not None
    assert check_response_encoding(upper) is None


# --------------------------------------------------------------------------- #
# encoding detection
#
# The distinction this check exists for is between evidence and a guess. Both tests
# below decode real bytes rather than asserting against a stub, because the claim is
# about what the byte space allows, not about what I believe it allows.
# --------------------------------------------------------------------------- #

def test_a_legacy_single_byte_payload_is_flagged_as_undecidable():
    """Nothing in these bytes can rule out any single-byte encoding, so the answer is a
    guess however confident the detector sounds."""
    truth = "El niño está aquí y la señora Muñoz ya pagó la factura."
    payload = truth.encode("iso-8859-1")

    finding = check_detected_encoding(payload, detected="windows-1250")
    assert finding is not None
    assert finding.severity == "high"
    assert finding.observed["single_byte_candidates_that_decode"] == "19 of 19"
    assert finding.observed["distinct_strings_produced"] > 1


def test_the_detector_reports_full_confidence_on_a_wrong_answer():
    """The reason the check reports ambiguity rather than trying to detect better. If
    charset-normalizer ever stops returning 1.000 here, this test says so."""
    from charset_normalizer import detect

    truth = "El niño está aquí y la señora Muñoz ya pagó la factura."
    payload = truth.encode("iso-8859-1")

    result = detect(payload)
    assert result["confidence"] >= 0.99
    assert payload.decode(result["encoding"]) != truth      # confident and wrong
    assert len(payload.decode(result["encoding"])) == len(truth)  # and the same length


def test_whether_a_text_survives_depends_on_the_text_not_the_configuration():
    """iso-8859-1 and cp1250 agree on 177 of 256 byte values. A German sentence read as
    cp1250 is unchanged; the Spanish sentence beside it is not. This is why German test
    fixtures pass while Spanish production data is altered."""
    agreeing = sum(
        bytes([i]).decode("iso-8859-1") == bytes([i]).decode("cp1250", errors="replace")
        for i in range(256)
    )
    assert agreeing == 177

    german = "Grüße aus Köln, alles schön hier; Straße gesperrt bis Montag."
    spanish = "El niño está aquí y la señora Muñoz ya pagó la factura."

    assert german.encode("iso-8859-1").decode("cp1250") == german
    assert spanish.encode("iso-8859-1").decode("cp1250") != spanish


def test_valid_utf8_is_not_flagged():
    """UTF-8 is structurally verifiable: of 12 legacy-encoded sentences measured, 0 were
    also valid UTF-8, so a successful decode is real evidence."""
    for truth in ["Grüße aus Köln", "El niño está aquí", "日本語のテキスト", "Москва"]:
        assert check_detected_encoding(truth.encode("utf-8")) is None


def test_ascii_and_bom_and_empty_are_not_flagged():
    """Three cases where nothing is being decided, and the check must stay quiet."""
    assert check_detected_encoding(b"item,qty\nwidget,2\n") is None
    assert check_detected_encoding(b"\xef\xbb\xbf" + "café".encode("utf-8")) is None
    assert check_detected_encoding(b"") is None


def test_utf8_survives_the_corpus_that_legacy_encodings_do_not():
    """The measurement the entry turns on, reduced to its smallest honest form: the same
    texts round-trip under UTF-8 and do not under their own legacy encodings."""
    from charset_normalizer import from_bytes

    corpus = [
        ("cp1252", "Le devis « signé » coûte 15 € - merci d'avance, M. Lefèvre."),
        ("iso-8859-2", "Zażółć gęślą jaźń - to jest polskie zdanie testowe."),
        ("koi8-r", "Москва, привет из России; счёт на оплату готов."),
        ("cp1254", "İstanbul'da hava çok güzel, faturanız hazır efendim."),
    ]

    def round_trips(payload, truth):
        match = from_bytes(payload).best()
        if match is None:
            return False
        try:
            return payload.decode(match.encoding) == truth
        except (UnicodeDecodeError, LookupError):
            return False

    assert sum(round_trips(t.encode("utf-8"), t) for _, t in corpus) == len(corpus)
    assert sum(round_trips(t.encode(e), t) for e, t in corpus) < len(corpus)


# --------------------------------------------------------------------------- #
# certificate dates
#
# The check probes the INSTALLED library by catching the deprecation warning, because
# the same attribute is a defect on cryptography < 42.0.0 and a non-event on >= 42.0.0.
# A version string would be a worse test than the behaviour itself.
# --------------------------------------------------------------------------- #

class _SilentNaiveCert:
    """A certificate as every release from 3.4.8 through 41.0.7 returns it."""

    not_valid_after = datetime.datetime(2026, 10, 1, 12, 0, 0)


class _WarningCert:
    """A certificate as 42.0.0 and later return it: the attribute still works, and says so."""

    not_valid_after_utc = datetime.datetime(
        2026, 10, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
    )

    @property
    def not_valid_after(self):
        import warnings

        warnings.warn("deprecated, use not_valid_after_utc", DeprecationWarning)
        return datetime.datetime(2026, 10, 1, 12, 0, 0)


def _at_timezone(name):
    import os
    import time

    os.environ["TZ"] = name
    time.tzset()


def test_a_silent_naive_certificate_is_flagged_west_of_utc():
    """The unsafe direction: the naive comparison accepts a certificate that has already
    expired, for a window as wide as the host's offset."""
    try:
        _at_timezone("America/Los_Angeles")
        finding = check_certificate_dates(_SilentNaiveCert())
        assert finding is not None
        assert finding.severity == "high"
        assert "ALREADY EXPIRED" in finding.observed["error_in_a_naive_comparison"]
        assert finding.observed["warning_emitted"] == "no"
    finally:
        _at_timezone("UTC")


def test_east_of_utc_is_flagged_as_the_other_failure():
    """Same defect, opposite direction: renewal alarms fire early, every time."""
    try:
        _at_timezone("Pacific/Auckland")
        finding = check_certificate_dates(_SilentNaiveCert())
        assert finding is not None
        assert finding.severity == "medium"
        assert "still-valid" in finding.observed["error_in_a_naive_comparison"]
    finally:
        _at_timezone("UTC")


def test_a_version_that_warns_is_not_flagged():
    """cryptography >= 42.0.0 tells you, which is the whole distinction between FINDING
    and LOUD. The check must go quiet on its own."""
    try:
        _at_timezone("America/Los_Angeles")
        assert check_certificate_dates(_WarningCert()) is None
    finally:
        _at_timezone("UTC")


def test_a_host_at_utc_is_not_flagged():
    """At UTC the naive comparison is correct — by luck, not design. It is also why CI
    never catches this: build hosts run at UTC."""
    _at_timezone("UTC")
    assert check_certificate_dates(_SilentNaiveCert()) is None


def test_the_naive_comparison_really_does_not_raise():
    """The premise of the whole entry. If Python raised TypeError here, nobody would ship
    it — the danger is that both operands are naive, so it compares cleanly."""
    try:
        _at_timezone("America/Los_Angeles")
        expired_six_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        looks_expired = expired_six_hours_ago < datetime.datetime.now()
        assert looks_expired is False, "the expired certificate reads as still valid"
    finally:
        _at_timezone("UTC")


# --------------------------------------------------------------------------- #
# catalogue invariants
# --------------------------------------------------------------------------- #

def test_a_resolved_entry_is_kept_not_deleted():
    """Audit 13 deleted a real finding because a later release fixed it. An entry is a
    claim about VERSIONS: a fix upstream bounds it, and the affected range is still
    installed. This test is the guard on that."""
    resolved = [e for e in CATALOGUE if e.is_resolved]
    assert resolved, "a resolved entry was dropped rather than bounded"
    for entry in resolved:
        assert entry.affected_versions != "not yet ranged", (
            f"{entry.library} claims a fix version without a measured affected range"
        )
        assert entry.evidence, f"{entry.library} has no evidence path"


def test_every_entry_names_the_versions_it_was_measured_on():
    """A verdict is only as wide as the versions measured."""
    for entry in CATALOGUE:
        assert entry.versions_measured.strip(), f"{entry.library} names no version"


# --------------------------------------------------------------------------- #
# hook precedence
#
# The first version of this check had four defects and zero tests. It fired at high
# severity on a stock pytest install with no third-party plugins, counted wrappers as
# contestants, and reported a fabricated "answers_discarded_per_call". Half of what
# follows asserts silence, for exactly that reason.
# --------------------------------------------------------------------------- #

@pytest.fixture
def pluggy_pm():
    """A plugin manager with one first-result hook and one ordinary hook."""
    import pluggy

    hookspec = pluggy.HookspecMarker("t")
    hookimpl = pluggy.HookimplMarker("t")

    class Spec:
        @hookspec(firstresult=True)
        def resolve(self, sku): ...

        @hookspec
        def collect(self, sku): ...

    def answering(value, **opts):
        return type("P", (), {"resolve": hookimpl(**opts)(lambda self, sku, _v=value: _v)})()

    class Observer:
        @hookimpl(wrapper=True)
        def resolve(self, sku):
            return (yield)

    def build(*plugins):
        pm = pluggy.PluginManager("t")
        pm.add_hookspecs(Spec)
        for name, obj in plugins:
            pm.register(obj, name=name)
        return pm

    build.answering = answering
    build.Observer = Observer
    build.hookimpl = hookimpl
    return build


def test_two_plugins_that_can_both_answer_are_flagged(pluggy_pm):
    """The finding: which one answers is decided by registration order, and the other is
    never called at all."""
    pm = pluggy_pm(("catalogue", pluggy_pm.answering(100)),
                   ("promotion", pluggy_pm.answering(80)))

    finding = check_hook_precedence(pm)
    assert finding is not None
    assert finding.observed["first_result_hooks_contested"] == 1
    assert finding.observed["call_order_first_wins"] == "promotion > catalogue"
    assert finding.observed["plugins_that_will_not_run_on_it"] == 1
    assert pm.hook.resolve(sku="x") == 80


def test_reversing_registration_reverses_the_winner(pluggy_pm):
    """The measurement the entry turns on, as a test rather than a claim."""
    a = pluggy_pm(("catalogue", pluggy_pm.answering(100)),
                  ("promotion", pluggy_pm.answering(80)))
    b = pluggy_pm(("promotion", pluggy_pm.answering(80)),
                  ("catalogue", pluggy_pm.answering(100)))

    assert a.hook.resolve(sku="x") == 80
    assert b.hook.resolve(sku="x") == 100


def test_trylast_runs_first_registered_first_so_the_rule_is_not_lifo(pluggy_pm):
    """The original write-up said LIFO. trylast is FIFO — the opposite — which is why the
    rule had to be restated as buckets."""
    import pluggy

    order = []
    hookimpl = pluggy_pm.hookimpl

    def recorder(name, **opts):
        return type(name, (), {
            "resolve": hookimpl(**opts)(lambda self, sku, _n=name: order.append(_n) or None)
        })()

    for opts, expected in [({}, ["C", "B", "A"]),
                           ({"tryfirst": True}, ["C", "B", "A"]),
                           ({"trylast": True}, ["A", "B", "C"])]:
        order.clear()
        pm = pluggy_pm(*[(n, recorder(n, **opts)) for n in "ABC"])
        pm.hook.resolve(sku="x")
        assert order == expected, f"{opts or 'plain'}: got {order}"


def test_measure_contention_recovers_what_the_loser_would_have_said(pluggy_pm):
    """The original claimed no API exposed this. subset_hook_caller does, exactly."""
    pm = pluggy_pm(("catalogue", pluggy_pm.answering(100)),
                   ("promotion", pluggy_pm.answering(80)))

    result = measure_contention(pm, "resolve", sku="x")
    assert result["winner"] == ("promotion", 80)
    assert result["answers_in_call_order"] == [("promotion", 80), ("catalogue", 100)]
    assert result["implementations_that_never_ran"] == 1
    assert result["genuinely_ambiguous"] is True


# --- silence -------------------------------------------------------------- #

def test_a_wrapper_does_not_make_a_hook_contested(pluggy_pm):
    """Defect 1 of the original check. A wrapper cannot answer, so one answering plugin
    plus a wrapper is not a contest. In stock pytest this alone was two false positives."""
    pm = pluggy_pm(("only", pluggy_pm.answering(100)),
                   ("observer", pluggy_pm.Observer()))

    assert check_hook_precedence(pm) is None
    assert pm.hook.resolve(sku="x") == 100


def test_one_plugin_is_not_flagged(pluggy_pm):
    assert check_hook_precedence(pluggy_pm(("only", pluggy_pm.answering(100)))) is None


def test_no_plugins_is_not_flagged(pluggy_pm):
    assert check_hook_precedence(pluggy_pm()) is None


def test_a_non_firstresult_hook_with_many_impls_is_not_flagged(pluggy_pm):
    """Only first-result hooks discard anything. An ordinary hook returns every answer."""
    import pluggy

    hookimpl = pluggy_pm.hookimpl
    collectors = [("p%d" % i, type("C", (), {
        "collect": hookimpl(lambda self, sku, _v=i: _v)})()) for i in range(5)]
    pm = pluggy_pm(*collectors)

    assert len(pm.hook.collect(sku="x")) == 5
    assert check_hook_precedence(pm) is None


def test_an_object_with_no_hook_relay_is_not_flagged():
    assert check_hook_precedence(object()) is None
    assert check_hook_precedence(None) is None


def test_a_relay_attribute_that_raises_does_not_crash_the_check():
    """The original caught only AttributeError and TypeError, so a relay that raised
    anything else took the check down with it."""
    class Hostile:
        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            raise RuntimeError("no")

    class PM:
        hook = Hostile()

    assert check_hook_precedence(PM()) is None
