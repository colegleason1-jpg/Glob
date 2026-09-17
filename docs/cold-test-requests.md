# Audit 11: requests — protocol rank 7

2026-09-17 · **AUDITING: requests 2.33.1** · protocol rank **7** of 15,000, 1,695,910,251
downloads.

**Pre-registered eligibility:** *eligible — encoding detection, redirect and session
behaviour branch on response properties.*

Measured against a local HTTP server sending known UTF-8 bytes under a chosen
`Content-Type`. The content type travels base64-encoded in the request path, because the
first version of this probe put it in the path raw and the space in
`text/plain; charset=utf-8` mangled the request line — which produced an implausible row
and is recorded here rather than quietly fixed.

## Assumption

A `text/*` response that omits `charset` is Latin-1.

## The code

`requests/utils.py`, `get_encoding_from_headers`:

```python
if "charset" in params:
    return params["charset"].strip("'\"")

if "text" in content_type:
    return "ISO-8859-1"

if "application/json" in content_type:
    return "utf-8"
```

`Response.text` then decodes `self.content` with that encoding, and its docstring says
what it is doing:

> The encoding of the response content is determined based solely on HTTP headers,
> **following RFC 2616 to the letter.**

RFC 2616 §3.7.1 (1999) did specify ISO-8859-1 as the default for `text/*`. **RFC 7231
removed that default in 2014**, and RFC 9110 has not restored it. The docstring is
accurate; the letter it follows was superseded eleven years ago.

Three separate mechanical consequences:

1. **The fallback is never reached.** `Response.text` consults `apparent_encoding` only
   when `self.encoding is None`. The header rule has already returned a value, so the
   detector never runs.
2. **`"text" in content_type` is a substring test**, not a media-type test.
3. **It is case-sensitive**, though media type tokens are case-insensitive by
   RFC 9110 §8.3.1.

## Measured

12 UTF-8 bodies, served as `text/plain` with no `charset`:

| | |
| --- | --- |
| `r.text` correct | **0 / 12** |
| `r.apparent_encoding` correct | **12 / 12** |
| non-ASCII characters in the corpus | 35 |
| of those, mangled in `r.text` | **35 (100%)** |
| bodies where `len(r.text)` is wrong | **12 / 12** |
| total characters over-counted | **+43** |
| exceptions raised | **0** |
| warnings emitted | **0** |

Per content type, same UTF-8 body every time:

| `Content-Type` sent | `r.encoding` | `r.text` right? | `r.apparent_encoding` |
| --- | --- | --- | --- |
| `text/plain` | ISO-8859-1 | **NO** | utf-8 |
| `text/html` | ISO-8859-1 | **NO** | utf-8 |
| `text/csv` | ISO-8859-1 | **NO** | utf-8 |
| `text/json` | ISO-8859-1 | **NO** | utf-8 |
| `application/x-subrip-text` | ISO-8859-1 | **NO** | utf-8 |
| `TEXT/PLAIN` | None | yes | utf-8 |
| `Text/Plain` | None | yes | utf-8 |
| `text/plain; charset=utf-8` | utf-8 | yes | utf-8 |
| `application/json` | utf-8 | yes | utf-8 |
| `application/xml` | None | yes | utf-8 |
| *(no header)* | None | yes | utf-8 |

**`text/plain` mojibakes and `TEXT/PLAIN` does not.** Two servers sending identical bytes
under the same media type hand the caller different strings.

Why it never raises, and why the tests pass:

```
body                     r.encoding   r.text correct?  exception?
ASCII only: 'name,qty'   ISO-8859-1   yes              none
one accent: 'café'       ISO-8859-1   NO               none
CJK: '日本'               ISO-8859-1   NO               none
emoji: '📦'               ISO-8859-1   NO               none
```

ISO-8859-1 maps all 256 byte values to characters, so the decode **cannot** fail — there
is no byte sequence that signals the guess was wrong. And ASCII is a fixed point: a test
suite written against ASCII fixtures passes at 100%.

## Impact

**Believed:** *This is the text the server sent.*

**Actual:** *This is the body reinterpreted under a 1999 default the server never asked
for.* 0 of 12 bodies correct; every one of 35 non-ASCII characters replaced by two or
three others.

### It is not only cosmetic — the counts are wrong

| true string | true `len` | `r.text` | `len(r.text)` |
| --- | --- | --- | --- |
| `'café'` | 4 | `'cafÃ©'` | **5** |
| `'naïve'` | 5 | `'naÃ¯ve'` | **6** |
| `'日本'` | 2 | `'æ\x97¥æ\x9c¬'` | **6** |
| `'£5'` | 2 | `'Â£5'` | **3** |
| `'Aktivität'` | 9 | `'AktivitÃ¤t'` | **10** |

A character count read from an API is inflated by exactly the number of non-ASCII
characters upstream — data-dependent, and nobody's constant. If an API reports a quantity,
a field width, a per-character price or a stock count in a `text/*` body, the number the
caller holds is not the number the server sent. **`'日本'` is two characters and arrives as
six.**

### Lookups miss rather than mismatch

```
r.text == 'café'          -> False
'café' in {r.text: 1}     -> False
r.text.upper()            -> 'CAFÃ©'     (true: 'CAFÉ')
```

A product name, a supplier, a city, a patient surname read back from an API no longer
equals the record it was written from. The caller does not get a wrong row — it gets **no
row**, and handles a missing record instead of a corrupt one. That is a different and much
quieter failure than mojibake on a screen.

### Truncation makes it unrecoverable

Latin-1 round-trips, so `r.text.encode('iso-8859-1').decode('utf-8')` repairs the string —
**while it is intact.** Store it in a fixed-width column first and it does not. For the
33-character string `'Käse und Brötchen für alle Kölner'`, across all 37 truncation points
of its mojibake form:

| outcome of repairing the truncated value | count |
| --- | --- |
| raises `UnicodeDecodeError` | 4 |
| repairs, **to different content than the true prefix** | **31** |
| repairs to the right prefix | 2 |

The 31 are the dangerous ones. A `VARCHAR(20)` stores
`'KÃ¤se und BrÃ¶tchen '`; repaired later that is `'Käse und Brötchen '`, where the true
20-character prefix was `'Käse und Brötchen fü'`. No error, different data.

### `r.json()` inherits it

| `Content-Type` | `r.encoding` | `r.json()['item']` |
| --- | --- | --- |
| `application/json` | utf-8 | `'café'` |
| `text/plain` | ISO-8859-1 | `'cafÃ©'` |
| `text/json` | ISO-8859-1 | `'cafÃ©'` |

`Response.json()` decodes through `text` whenever `encoding` is set, so a server that
labels JSON as `text/plain` — common for small internal services — delivers mojibake
inside structured fields. `iter_lines(decode_unicode=True)` is affected the same way.

**Detection: worst case.** ASCII passes, the decode cannot raise, and the failure appears
only when real data carries an accent. It then appears as "weird characters", gets patched
at the display layer, and the counts and the lookups stay wrong underneath.

## Upstream status

**Working as intended, and documented.** `Response.text` states the rule and names the RFC
it follows. The gap is not that the behaviour is hidden — it is that the call site cannot
tell a charset the server *declared* from one requests *assumed*, and the detector that
would have been right 12/12 sits on the same object, unconsulted.

The substring test and the case-sensitivity are not spec-era decisions. They are the rule
as written.

## Outcome

**FINDING.** `unstated.check_response_encoding(response)` — fires when a `text/*` response
with no declared charset carries non-ASCII bytes, and stays silent on ASCII bodies, on a
declared charset, on `application/json`, and on the uppercase spelling that happens to
escape the rule. Audit 11, protocol rank 7.
