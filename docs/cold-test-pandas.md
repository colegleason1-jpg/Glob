# Cold test 4: pandas.merge (pandas 3.0.5)

2026-09-17 · the most common silent data-corruption path in applied analytics.

A join key that has duplicates on **both** sides produces the cartesian product of the
matches. Row counts multiply, every summed column inflates, and nothing is raised.

## Measured

2,000 orders joined to a 398-row customer table — one row per customer per address change,
which is the usual way a "unique" id stops being unique.

| | |
| --- | --- |
| orders rows in | 2,000 |
| customer rows (198 duplicate ids) | 398 |
| rows after merge | **4,045 — 2.02x** |
| exceptions raised | **0** |
| warnings emitted | **0** |

| metric | true | after merge | change |
| --- | --- | --- | --- |
| total revenue | 204,003.13 | 419,091.52 | **+105.4%** |
| mean order value | 102.00 | 103.61 | +1.6% |

Every ordinary check still passes: no nulls introduced, dtypes preserved, every value
still inside the original range.

**The mean is the trap.** It moves 1.6%, so a spot-check of the average looks clean while
the total has doubled. The corruption hides in exactly the statistic people do not check.

## The guard pandas already ships

```python
orders.merge(customers, on="customer_id", how="left", validate="m:1")
# MergeError: Merge keys are not unique in right dataset; not a many-to-one merge
```

Instant, clear, and correct. `inspect.signature(pd.DataFrame.merge)` gives
`validate=None`.

## Class

Fifth confirmation, and the only one so far where the library ships a complete remedy and
leaves it off:

> A component that works under an assumption, with nothing signalling when the assumption
> does not hold, and a failure that passes every ordinary check.
