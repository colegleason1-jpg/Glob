# Audit 8: packaging — protocol rank 2

2026-09-17 · **AUDITING: packaging 24.0** · protocol rank **2** of 15,000, 2,253,382,953
downloads ([hugovk/top-pypi-packages](https://github.com/hugovk/top-pypi-packages), dump
dated 2026-09-01).

**Pre-registered eligibility**, recorded in `TARGETS.md` before this run: *eligible —
version comparison and specifier matching branch on the shape of the version string
supplied.*

## Assumption

The caller cares only about ordering — not about whether a candidate is a pre-release, or
carries a local build segment.

## Baseline

`>=1.0` reads as "orders at or above 1.0". So the baseline for what a reader expects is
plain version ordering: does `Version(v)` satisfy the arithmetic of the constraint?
packaging adds rules on top of that ordering which depend on properties of `v` the caller
never stated.

## Measured

60 specifier/version pairs across six specifiers people actually write.

| | |
| --- | --- |
| pairs where packaging disagrees with ordering | **18 of 60 (30%)** |
| …because the candidate is a pre-release | 16 |
| …because the candidate carries a local segment | 2 |
| exceptions raised | **0** |
| warnings emitted | **0** |

**They pull in opposite directions**, which is what makes this one entry and not two.

### Stricter than it reads

```
SpecifierSet(">=1.0").contains("2.0rc1")    = False
SpecifierSet(">=1.0").contains("2.0.dev1")  = False
SpecifierSet("!=1.5").contains("2.0b2")     = False
```

All of those order above 1.0. `>=1.0,<3.0` rejects every pre-release in the range.

### Looser than it reads

```
SpecifierSet("==2.0").contains("2.0+local")              = True
SpecifierSet("==2.0").contains("2.0+ubuntu1")            = True
SpecifierSet("==2.0").contains("2.0+patched.by.vendor")  = True
```

`==` is what people write when they mean *this artifact and no other*.

## Impact

**Believed:** *I pinned this to exactly version 2.0.*

**Actual:** *I pinned this to 2.0 or any local build labelled 2.0+anything.*

**Breaks**, in two opposite directions:

* *Loose* — any statement that a specific artifact is what runs. An exact pin accepts a
  rebuilt or vendor-patched package carrying the same base version, so an attestation
  that the audited artifact is deployed does not hold.
* *Strict* — availability of anything published as a pre-release. A fix shipped as
  `2.0rc1` does not satisfy `>=1.0`, so a resolver reports no matching version while one
  orders above the bound, and a team concludes the fix is unavailable.

**Detection:** poor both ways. The result is a boolean, and `False` reads as *no such
version* rather than *excluded by a rule you did not state*. The loose direction is worse:
the pin resolves, the install succeeds, and the lockfile records the version you asked for.

## Upstream status

**Specified.** Both behaviours are PEP 440, both are documented, and `prereleases=` exists.
As with boto3 and dateutil, the gap is not that the knowledge is missing — it is that
nothing at the call site says the constraint does not mean what it reads as.

## Outcome

**FINDING.** `unstated.check_specifier(specifier, versions)`. Recorded in `TARGETS.md` as
audit 8, protocol rank 2.
