# Does anything free already catch these?

2026-09-17 · run before continuing the audits, because a yes would make this a feature
rather than a product.

Three adjacent tools, tested against the six findings.

## pandas-vet 2023.8.2 — no overlap

A flake8 plugin. Run against a module committing all six findings: **nothing flagged.**

Its complete check list is style: import conventions (`import pandas as pd`), `.isna` over
`.isnull`, `.loc` over `.at`, avoid `inplace=True`, prefer `.pivot_table`. Fifteen codes,
none about correctness preconditions.

Not prior art.

## pandera 0.33.1 — validates your rules, not your dependencies' assumptions

The strongest free candidate, and the test is direct. Take the merge that inflates 2,000
orders to 4,045 rows and +105.4% on revenue, then validate it with the schema a careful
person actually writes — types, ranges, non-null:

```
pandera schema on the CORRUPTED frame : PASSES
```

Every value is still the right type, non-null and in range. The corruption lives in the
row count and every aggregate, which a column schema does not see.

It *can* catch it — `Check(lambda df: len(df) == 2000)` fails correctly. But that requires
knowing 2,000 was the right answer, which is the entire gap. **pandera checks your data
against rules you write; it has no knowledge of what `pd.merge` assumes and will not tell
you the assumption exists.**

Complementary, not competing. The natural relationship is that this catalogue tells you
which pandera checks you should have written.

## deepchecks — the closest thing, and it looks past this case

Could not be run: it fails to import against scikit-learn 1.9.1
(`'max_error' is not a valid scoring value`). So what follows assesses the **design** of
its relevant check, not a run of it, and should be re-tested when the versions line up.

`TrainTestSamplesMix` detects identical rows appearing in both splits. Our finding is a
different shape — same *subject*, different rows. Measured on the exact scenario from the
sklearn audit, 150 subjects at 8 noisy rows each:

| | |
| --- | --- |
| exact duplicate rows across the split | **0** |
| subjects present on both sides | **138 of 150 (92%)** |

A duplicate-row check sees zero and reports the split clean. No two rows are identical;
every subject is on both sides; the model is scored on people it memorised.

deepchecks is genuinely in this territory and is the tool to watch. On this case, its
mechanism does not reach the failure.

## Verdict

Nothing tested catches any of the six. The distinction that has to survive contact with a
skeptic:

> These tools validate **your data against rules you wrote**. This catalogue validates
> **your dependencies' assumptions against your data** — and tells you the assumption
> exists, which is the part nobody currently supplies.

Two caveats kept deliberately: deepchecks was assessed by design rather than by running
it, and three tools is not a survey. `great_expectations`, `evidently`, `soda` and the
model-validation tooling used inside banks were not tested.
