# Audit 12: charset-normalizer — protocol rank 8

2026-09-17 · **AUDITING: charset-normalizer 3.4.6** · protocol rank **8** of 15,000.

**Pre-registered eligibility:** *eligible — its entire job is inferring an assumption about
caller-supplied bytes.*

This is the detector that scored **12/12** in [audit 11](cold-test-requests.md), where it
produced the correct answer on every body `requests` got wrong. The protocol requires it be
audited on its own terms regardless, and a CLEAN outcome here would have been the more
interesting result for the register.

## Hypotheses, registered before measuring

| | hypothesis | outcome |
| --- | --- | --- |
| H1 | accuracy falls with input length; short inputs guessed wrong with no signal | **not reproduced** — 10/10 round-trip, down to a 2-byte input |
| H2 | single-byte legacy encodings are mutually indistinguishable, so a round-trip silently changes characters | **reproduced** |
| H3 | `steps=5, chunk_size=512` means at most 2,560 bytes are examined; non-ASCII outside the sample is invisible | **not reproduced** — 5/5 round-trip up to a 1,000,045-byte input |
| H4 | `.best()` can return `None`, and the documented idiom invites `.best().encoding` | **reproduced, minor** — `None` on random high bytes; `b"\x80"` returns `cp037` |

Two of four did not reproduce. They are recorded because a protocol that only publishes the
hypotheses that worked is not a protocol.

## Assumption

**A successful decode is evidence the encoding is right.** True for UTF-8. False for every
single-byte encoding.

## The code

`charset_normalizer/legacy.py`, `detect`:

```python
r = from_bytes(byte_str).best()
encoding   = r.encoding if r is not None else None
confidence = 1.0 - r.chaos if r is not None else None
```

**`confidence` is `1.0 - chaos`.** `chaos` measures whether the decoded output *looks like
coherent text*. A wrong single-byte decode also looks like coherent text — it produces
letters, spacing and punctuation, just the wrong letters. The two quantities are named as
though they were the same and are not.

## Measured

20 sentences, each encoded in a legacy encoding actually used for that language:

| | |
| --- | --- |
| exact encoding named | **6 / 20** |
| string round-trips (the metric that matters) | **12 / 20** — 40% wrong |
| exceptions / warnings | **0 / 0** |
| the same 20 texts encoded UTF-8 instead | **20 / 20 correct** |

`chaos` was `0.000` on **7 of the 8 failures** and on 11 of the 12 successes. It does not
separate them. Neither does the field a caller would actually check:

| | `detect()` confidence |
| --- | --- |
| on the 12 correct answers | min 0.938, max 1.000, mean 0.995 |
| on the 8 **wrong** answers | min 0.900, max 1.000, mean **0.988** |
| wrong answers at confidence ≥ 0.9 | **8 / 8** |
| wrong answers at confidence **= 1.000** | **7 / 8** |
| a threshold separating right from wrong | **none exists** |

## Why UTF-8 is different in kind

This is what makes the finding a defect rather than a restatement of an unfixable limit.

| | |
| --- | --- |
| legacy-encoded byte strings that are *also* valid UTF-8 | **0 / 12** |
| byte values decodable in ISO-8859-1 | **256 / 256** |
| byte values decodable in CP1250 | 251 / 256 |

A successful UTF-8 decode rules out almost everything else, so it is **evidence**. A
successful CP1250 decode rules out nothing, so it is **a guess**. The library computes both
and reports them through the same field, at the same number.

## The failure is decided by the text, not by the configuration

ISO-8859-1 and CP1250 agree on **177 of 256** byte values. So the same true encoding, the
same wrong guess, and opposite outcomes:

```
true  : Grüße aus Köln, alles schön hier; Straße gesperrt bis Montag.
got   : Grüße aus Köln, alles schön hier; Straße gesperrt bis Montag.
detect: windows-1250   confidence 1.000   characters changed: 0

true  : El niño está aquí y la señora Muñoz ya pagó la factura.
got   : El nińo está aquí y la seńora Muńoz ya pagó la factura.
detect: windows-1250   confidence 1.000   characters changed: 3   ('ñ' -> 'ń')
```

German umlauts sit at byte positions the two encodings agree on. `ñ` does not. **German
test fixtures pass while Spanish production data is altered**, and no amount of testing
with the first corpus reveals anything about the second.

Overlap for the confusions actually observed:

| pair | bytes agreeing |
| --- | --- |
| ISO-8859-7 vs CP1253 | 214 / 256 |
| ISO-8859-15 vs ISO-8859-10 | 210 / 256 |
| CP1252 vs CP1250 | 198 / 256 |
| ISO-8859-1 vs CP1250 | 177 / 256 |
| ISO-8859-2 vs CP1257 | 152 / 256 |
| CP1254 vs CP850 | 128 / 256 |

## Impact

**Believed:** *I decoded this file, and the detector was 100% confident.*

**Actual:** *I picked one of several readings that all decode without error, and the
confidence number reports that the result looks like text — not that it is the right text.*

### What it does to a name

40 European surnames, read ISO-8859-1 as CP1250:

| | |
| --- | --- |
| names tested | 40 |
| unchanged | 26 |
| **silently altered** | **14 (35%)** |
| of those, changing length | **0 / 14** |
| exceptions | 0 |

```
Muñoz     -> Muńoz          Ørsted    -> Řrsted
Peña      -> Peńa           Åkesson   -> Ĺkesson
Núñez     -> Núńez          Sørensen  -> Sřrensen
Ibáñez    -> Ibáńez         Bjørn     -> Bjřrn
Lefèvre   -> Lefčvre        Håkon     -> Hĺkon
Conceição -> Conceiçăo      João      -> Joăo
```

**Every one is the same length as the original.** A field-width check passes, a truncation
check passes, a not-null check passes, and the value still looks like a name — because it
is a name, just not this person's.

### What breaks is the join, not the total

Nothing fails to reconcile. The row counts are right, the sums are right, the file imported
cleanly. What is broken is **identity**: the altered value no longer matches the record it
belongs to. A customer is created rather than found. A duplicate ledger is opened under a
name differing by one diacritic. A de-duplication pass leaves both rows. A search for the
real name returns nothing.

This is the quietest failure in the catalogue. The louder encoding bugs — [audit
11](cold-test-requests.md) — at least produce visible mojibake that somebody eventually
complains about. `Muńoz` does not look wrong to anyone who is not Señora Muñoz.

**Detection: none, and the confidence field actively misdirects.** The number a careful
caller would check reads 1.000 on the wrong answers.

## Upstream status

**The ambiguity is genuine and unfixable.** Single-byte encodings really are
indistinguishable at the byte level; no library can do better, and this audit does not
claim one could.

**What is reported is a separate choice.** `confidence = 1.0 - chaos` presents a legibility
score under a name that reads as a correctness probability. Upstream has already patched one
symptom — `legacy.detect` subtracts 0.2 when the payload is under 32 bytes
(`jawah/charset_normalizer#391`) — which is an acknowledgement that the number over-reports,
applied to one case and not to the mechanism. Every sample in this audit is over 32 bytes,
which is why they come back at 1.000.

## Outcome

**FINDING.** `unstated.check_detected_encoding(payload, detected)` — it does not try to
detect better. It reports, for the caller's own bytes, how many distinct strings the
plausible encodings produce, which is the number `confidence` does not carry. Silent on
valid UTF-8, on ASCII, on a BOM, and when every candidate agrees. Audit 12, protocol rank 8.
