# legacy

The acquired system and the documents written about it. **Nothing here runs, and nothing in
`app/` or `engine/` imports it.** It is kept because the rebuild's design decisions only make
sense against what they were reacting to, and a claim that eighteen defects were fixed is
worth more when the code containing them is still readable.

| File | What it is |
| --- | --- |
| `acquired-system-v1.py` | The acquired system: 1,146 lines in one file, holding the interface, the optimiser, the simulation, the price assumptions, and the authentication together. Defects **F1–F13** in [`../engine/docs/ADR-001-objective-reformulation.md`](../engine/docs/ADR-001-objective-reformulation.md) are citations into this file. F14 onward are not — see below. |
| `forensic-audit-v1.txt` | The audit of that system, separating what was implemented from what was claimed but never demonstrated. |
| `rebuild-blueprint.pdf` | The target architecture the rebuild was aimed at. |
| `system-map-sketch.png` | Working sketch of the system map. |

## Which defects this file is actually evidence for

This said "F1–F18 are all citations into this file", and it was wrong in a way worth
correcting rather than quietly trimming, because the wrong version flattered the rebuild.

**F1–F13** were found by reading this file, and are citations into it. **F14–F18** were
not: ADR-001 files them under "Found by testing, not by reading" and says in as many words
that they "were not in the original audit". They are the return on writing the test suite,
and several of them were found by driving the rebuilt app rather than by inspecting
anything here.

**F16 and F19 cannot be citations into this file at all.** Both are defects in the chord
and tangent linearisation of a concave-in-funding risk response. This file has no such
thing: its objective is `pl.lpSum(marginal_risks[n] * x[n] ...)`, strictly linear in the
funding scale, and its 0.85 exponent is applied to the risk *parameter*
(`(macro * risk) ** 0.85`), never to `x`. There is no approximation here to have got wrong.
Those two are defects the rebuild introduced in machinery the acquired system did not have
— which is the honest version, and a better argument for the suite than the flattering one.

So the value of keeping this directory is F1–F13, which is still thirteen defects and still
worth the disk. The claim on the rest belongs to the tests.

The parity constants in the test suite exist to prove the rebuild reproduces this system's
*correct* behaviour while fixing the rest, so this file is a specification as much as a
historical artifact. `engine/src/scrcae/legacy/reference.py` is where that parity is encoded —
that module is real, tested code, and is not the same thing as this directory. Read its
module docstring before relying on it: it carries one deliberate divergence from this file,
in how the correlation diagonal is handled, and no test in the parity suite crosses it.

Original filenames were `Best poop.py`, `Forensic audit.txt`, `Supply Chain Resilience &
Capital Allocation Engine — Rebuild Blueprint.pdf`, and a dated screenshot. Renamed on the
way in, because filenames in a repository are read by people deciding whether to take it
seriously.
