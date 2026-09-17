# Version-range sweep — all eleven entries

2026-09-17. 22 agents, 0 errors, 94 minutes, ~1.67M tokens. Each of the eleven catalogue
entries was re-measured across its library's release history by one agent, and each
resulting boundary was handed to a second agent **instructed to refute it**.

## Why

The catalogue pinned each entry to the single version it was found on. That is an
under-specified claim: someone running an older release needs to know whether they have the
defect, and if an older version is clean or a newer one fixed it, that is equally
publishable. The immediate prompt was audit 13, where a real finding was deleted because a
newer release fixed it — see [`docs/PROCESS.md`](PROCESS.md).

## Result

| entry | affected span | years | resolved |
| --- | --- | ---: | --- |
| `idna` | 0.6 (2014-04) → 3.20 (2026-09) — **exhaustive, all 34 installable releases** | **12.4** | no |
| `requests` | 2.2.0 (2014-01) → 2.34.2 (2026-05), 9 sampled | **12.4** | no |
| `urllib3` | 1.9 (2014-07, the release that introduced `Retry`) → 2.8.0 (2026-09) | **12.2** | no |
| `python-dateutil` | 2.1 (2012-03) → 2.9.0.post0 (2024-03), 14 releases | **12.0** | no |
| `packaging` | 14.3 (2014-11, first release shipping `specifiers`) → 26.3 (2026-08) | **11.7** | **partially, 26.0** |
| `boto3` | 1.4.4 (2017-01) → 1.43.96 (2026-09), 11 sampled of 2,078 | 9.7 | no |
| `charset-normalizer` | 0.3.0 (2019-09) → 3.5.1 (2026-08), 16 releases | 6.9 | no |
| `pandas` | 0.25.2 (2019-10) → 3.0.5 (2026-07), 12 sampled of 57 | 6.8 | no |
| `optuna` | 1.0.0 (2020-01) → 5.0.0 (2026-09), 5 releases | 6.6 | no |
| `scikit-learn` | 0.22.2.post1 (2020-03) → 1.9.1 (2026-09), 13 confirmed | 6.5 | no |
| `imbalanced-learn` | 0.6.0 (2019-12) → 0.14.2 (2026-06), 10 releases | 6.5 | no |

**Four entries have been silently present for over twelve years.** Ten of eleven are
unresolved at the current release.

## What the adversarial verifiers changed

**Eight of eleven boundary claims were refuted and narrowed.** That is the sweep working;
the published ranges are the corrected ones. The substantive changes:

### Two published numbers were wrong

**`idna`: "8 of 13 domains (62%), 4 producing two registrable names" is wrong.** The table
has always held **12** domains — one row carries two — and the split was internally
inconsistent, since 4 + 2 does not reach 8. Re-measured directly: **7 of 12 (58%), 5
producing two registrable names, 2 refusals.** Corrected in `_catalogue.py` and
`cold-test-idna.md`, with the original figures kept.

**`requests`: the verifier claimed `apparent_encoding` is 11/12, not 12/12.** Re-measured
before acting: **the published 12/12 is correct.** The verifier had conflated two corpora —
the standalone `'£5'` it flags is a member of the character-count table, not the
apparent_encoding corpus. Claim checked and rejected, recorded here because a verifier being
wrong is as much a result as a verifier being right.

### One entry is a regression, not an ancient behaviour

**`python-dateutil`'s second behaviour — `dayfirst=True` transposing unambiguous ISO 8601 —
was introduced at 2.5.2 (2016-03-27).** At 2.5.1 and every release before it the documented
remedy genuinely works: the mixed column goes from 353/2000 wrong to **0/2000**. At 2.5.2
the regression is partly loud (221 of 365 ISO dates raise, 132 flip silently); from 2.5.3
(2016-04-21) it is fully silent and stays that way. dateutil's own NEWS corroborates the
mechanism (gh#233, pr#234). The first behaviour — per-string day/month inference — is
present unchanged across all 14 releases.

### One entry is partially fixed

**`packaging` 26.0 (2026-01-21) flips the pre-release default**, and 16 of the 18
disagreements disappear — measured at all seven 26.x releases, which drop to 2 of 60 (3.3%).
The remaining 2, the exact-pin-accepts-a-local-build direction that this entry rates the
more severe, are **still present and still silent at 26.3.** The floor also moved back: the
defect is present at **14.3**, the first release that shipped `packaging.specifiers` at all,
so it has existed for the entire lifetime of the API.

**The 26.x change is itself silent.** Upgrading past 25.0 reverses the pre-release behaviour
in the opposite direction with 0 warnings.

### Three "byte-identical" claims were false

`scikit-learn` (signature changed at 0.24.2; docstring grew 2,904 → 4,997 characters),
`urllib3` (`retry.py` has ~20 distinct revisions, 9,549 → 20,151 bytes), and `pandas` all
had their invariance claims narrowed. **What is invariant is the behaviour and the silence,
not the code.** For `scikit-learn` specifically: the absence of group support, the absence
of any warning, and the absence of the words group/independent/leak/subject/cluster from the
docstring.

### Sampling density is now stated, not implied

`boto3` is the weakest: **11 releases of 2,078 in range (0.53%), largest untested gap 416
consecutive releases.** `pandas` is 12 of 57. `idna` is the strongest — exhaustive over
every installable release. Each entry's `affected_versions` now says which it is, because
"present in every version" and "present in every version we ran" are different claims.

### One check has a version floor

`unstated.check_retry`'s third gap — `allowed_methods=None` replaying a POST — **cannot fire
before urllib3 1.26.0**, where the attribute did not exist. And `urllib3` 2.8.0 is the first
release in twelve years to attach any deprecation to `Retry.__init__`, though not for the
three gaps this entry measures.

### Reconstructed numbers are flagged as reconstructions

Several agents could not recover the original scripts and rebuilt the smallest probe that
reproduces the key number. Where the rebuilt figure differs from the published one —
`pandas` 2.083x vs 2.08x, `dateutil` 38.1% vs 37.2%, `scikit-learn` 0.9350 vs 0.9472 — the
difference is a seed, and the entries keep their original measured figures. What the sweep
establishes is **presence and silence across versions**, which was byte-identical per agent
at every version; not that the decimals are version-invariant constants.

## Method note

Each measuring agent was told to re-run the *same* measurement rather than a paraphrase, to
binary-search a boundary rather than test every release, to record `install-failed` rather
than infer a neighbour's behaviour, and to delete each venv after use. Each verifying agent
was told to default to `refuted=true` under uncertainty.

The verifiers did substantially more than rubber-stamp: several installed further versions,
wrote independent probes from scratch, checked every release date against PyPI, and read
upstream changelogs. One of them was wrong, and checking it directly is what established
that.
