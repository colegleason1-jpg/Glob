"""Append-only ledger of every finding ever established. **Read the rules before editing.**

This file exists because a finding was deleted from the catalogue on 2026-09-17 without
being asked about. It was a real, measured defect in ``cryptography`` 41.0.7 — silent,
reproducible, and installed on millions of machines — and it was dropped because a later
release fixed it and because a clean result was, at that moment, the tidier answer.

The owner of this repository caught it. That is the wrong person to be catching it.

So the catalogue is no longer the record of what has been found. **This file is.** The
catalogue is a view over it, and ``test_process.py`` fails if the view loses a row.

## The only lawful way to remove an entry

1. The measurement that established it is re-run and **does not reproduce**.
2. A ``Withdrawal`` is appended below, naming what was re-run, what it showed, and who
   approved the removal **by name, in their own words, in the conversation**.
3. Only then may it leave ``CATALOGUE``.

"I no longer think it qualifies" is not a reason. "A newer version fixed it" is not a
reason — that is ``resolved_in``, and the entry stays. Neither is a principle invented
after the fact; see ``docs/PROCESS.md`` for why that one is called out specifically.

Adding to ``ESTABLISHED`` is free and needs nobody's permission. Removing is not.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Withdrawal:
    """A finding removed from the catalogue. Every field is mandatory and none may be empty."""

    key: str                 #: "library|component", matching the ESTABLISHED row
    established_in: str      #: the audit that found it
    remeasured_on: str       #: date the original measurement was re-run
    what_it_showed: str      #: the numbers from the re-run, not a summary of them
    approved_by: str         #: who approved removal, and where they said so
    evidence: str            #: path to the re-run


#: Every finding ever established, by "library|component". APPEND ONLY.
#: A row leaving this tuple is a rewrite of the record, not a correction to it.
ESTABLISHED: tuple[str, ...] = (
    "python-dateutil|parser.parse",
    "pandas|DataFrame.merge",
    "imbalanced-learn|SMOTE",
    "optuna|pruners.MedianPruner",
    "scikit-learn|model_selection.train_test_split",
    "boto3|list/scan/query operations",
    "packaging|SpecifierSet",
    "idna|encode vs the stdlib 'idna' codec",
    "urllib3|util.retry.Retry",
    "requests|Response.text",
    "charset-normalizer|detect / from_bytes(...).best()",
    "cryptography|x509.Certificate.not_valid_after",
)

#: Findings lawfully withdrawn. Empty is the expected state.
WITHDRAWALS: tuple[Withdrawal, ...] = ()

#: Candidates measured but NOT catalogued, held open for a decision rather than dismissed.
#: A judgement call that excludes a measured behaviour is recorded here, with the argument,
#: so the owner can overrule it. Silently dropping one is the failure this file exists for.
HELD_OPEN: tuple[tuple[str, str], ...] = (
    (
        "cryptography|fernet.Fernet.decrypt",
        "decrypt() with no ttl accepts a token of any age — measured accepted at 1 day, "
        "1 year and 10 years, 0 warnings, on every version tested. The timestamp is inside "
        "the token, authenticated, and free to check. Held open rather than catalogued "
        "because it is arguably omission rather than misdirection; the argument originally "
        "used to dismiss it was wrong (it contradicted urllib3|util.retry.Retry). Owner's "
        "call, not mine.",
    ),
    (
        "cryptography|x509.load_pem_x509_certificate",
        "Returns one certificate from a 5-certificate bundle: 4 of 5 silently discarded, "
        "0 warnings. Held open because the function is named singular and the plural form "
        "exists — against which, 'fullchain.pem' is what Let's Encrypt names its output and "
        "the singular name does not stop it being passed. Owner's call.",
    ),
)
