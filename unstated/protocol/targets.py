"""Eligibility for the top 100 PyPI packages, registered 2026-09-17 BEFORE any of them
beyond rank 12 was audited.

Registering all 100 at once is stronger than doing it one at a time: the filter cannot be
fitted to results it has not seen. Ranks 1-10 were registered earlier and their recorded
verdicts are reproduced here unchanged.

The criteria, from ``docs/TARGETS.md``, unchanged. A package is ELIGIBLE when it exposes a
callable that:

  1. takes caller-supplied data or configuration, AND
  2. returns a value the caller acts on — not only transport or plumbing, AND
  3. has at least one branch whose behaviour depends on a property of that data.

INELIGIBLE means no runtime data surface (a certificate bundle, build metadata, constants),
pure transport with no interpretation, or a compatibility shim. DEFER means the surface is
real but is already covered by a package audited at a lower rank, so auditing it separately
would double-count one codebase.

**This file is a prediction, not a result.** Being eligible says nothing about whether a
finding exists. Rule 7: the outcome is whatever it is measured to be.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    rank: int
    package: str
    verdict: str        #: "eligible" | "ineligible" | "defer"
    reasoning: str

    VERDICTS = ("eligible", "ineligible", "defer")


#: Top 100 by PyPI downloads, dump dated 2026-09-01, source hugovk/top-pypi-packages.
TARGETS: tuple[Target, ...] = (
 Target(1,  "boto3", "eligible", "pagination and retry behaviour depend on properties of the caller's request and response data"),
 Target(2,  "packaging", "eligible", "version comparison and specifier matching branch on the shape of the version string supplied"),
 Target(3,  "typing-extensions", "ineligible", "type constructs resolved at definition time; nothing is computed from caller data"),
 Target(4,  "certifi", "ineligible", "a certificate bundle; nothing is computed from caller data"),
 Target(5,  "idna", "eligible", "encoding decisions branch on properties of the domain string supplied"),
 Target(6,  "urllib3", "eligible", "Retry behaviour depends on whether the caller's request is idempotent, supplied implicitly"),
 Target(7,  "requests", "eligible", "encoding detection, redirect and session behaviour branch on response properties"),
 Target(8,  "charset-normalizer", "eligible", "its entire job is inferring an assumption about caller-supplied bytes"),
 Target(9,  "setuptools", "ineligible", "build-time metadata; no runtime data surface"),
 Target(10, "cryptography", "eligible", "key and certificate handling branches on properties of supplied material"),
 Target(11, "cffi", "ineligible", "behaviour is decided by the C declarations, not by runtime caller data"),
 Target(12, "pluggy", "eligible", "hook call order and the firstresult rule depend on properties of the plugins the caller registers"),
 Target(13, "pygments", "eligible", "lexer selection is inferred from filename and content — an assumption about caller data"),
 Target(14, "pyyaml", "eligible", "scalar resolution branches on the shape of the supplied string; the Norway problem is the canonical instance"),
 Target(15, "botocore", "defer", "boto3 (rank 1) is a thin layer over it and was audited there; a separate audit double-counts one codebase"),
 Target(16, "python-dateutil", "eligible", "date parsing branches per-string on ambiguous ordering"),
 Target(17, "six", "ineligible", "a compatibility shim; no data surface"),
 Target(18, "pydantic", "eligible", "coercion and validation branch on the runtime shape of the input"),
 Target(19, "numpy", "eligible", "dtype promotion, overflow and casting branch on the data's values and types"),
 Target(20, "click", "eligible", "parameter type conversion branches on the text supplied on the command line"),
 Target(21, "pycparser", "eligible", "a parser; its output depends entirely on properties of caller-supplied source"),
 Target(22, "anyio", "ineligible", "concurrency plumbing; cancellation is structural, not computed from caller data"),
 Target(23, "pytest", "eligible", "fixture resolution and scope branch on properties of the caller's test code"),
 Target(24, "pydantic-core", "defer", "the surface is pydantic (rank 18); auditing both double-counts"),
 Target(25, "iniconfig", "eligible", "an INI parser: returned values depend on the shape of the caller's file"),
 Target(26, "aiobotocore", "defer", "the boto3/botocore surface, audited at rank 1"),
 Target(27, "annotated-types", "ineligible", "metadata classes; nothing is computed"),
 Target(28, "h11", "eligible", "an HTTP/1.1 state machine whose transitions branch on caller-supplied bytes"),
 Target(29, "attrs", "eligible", "converters, validators and generated comparison methods branch on the supplied values"),
 Target(30, "typing-inspection", "ineligible", "introspection of type objects; no runtime data surface"),
 Target(31, "protobuf", "eligible", "field presence and default handling branch on the data — proto3 cannot distinguish unset from zero"),
 Target(32, "fsspec", "eligible", "path resolution and caching branch on the shape of the URL supplied"),
 Target(33, "httpx", "eligible", "the same surface class as requests: encoding, redirects, timeouts, branching on the response"),
 Target(34, "markupsafe", "eligible", "escaping branches on whether the supplied object declares __html__"),
 Target(35, "httpcore", "defer", "the httpx surface (rank 33)"),
 Target(36, "s3transfer", "defer", "the boto3 surface (rank 1)"),
 Target(37, "python-dotenv", "eligible", "quoting, interpolation and export handling branch on the file's contents"),
 Target(38, "platformdirs", "ineligible", "returns OS paths; nothing is computed from caller data"),
 Target(39, "pandas", "eligible", "join, groupby and dtype behaviour branch on properties of the caller's frames"),
 Target(40, "jinja2", "eligible", "autoescape and undefined handling branch on the supplied context and template"),
 Target(41, "pathspec", "eligible", "gitignore-style matching branches on the caller's patterns and paths"),
 Target(42, "grpcio-status", "ineligible", "status code mapping; a lookup table"),
 Target(43, "filelock", "ineligible", "OS lock acquisition; transport-like, no interpretation of caller data"),
 Target(44, "pip", "ineligible", "install tooling; no runtime data surface for a caller"),
 Target(45, "pyjwt", "eligible", "verification branches on the algorithm named inside the token the caller supplies"),
 Target(46, "starlette", "eligible", "routing, form parsing and content negotiation branch on the request"),
 Target(47, "uvicorn", "ineligible", "server plumbing"),
 Target(48, "litellm", "eligible", "provider routing and parameter translation branch on the model string supplied"),
 Target(49, "aiohttp", "eligible", "the same surface class as requests"),
 Target(50, "tqdm", "ineligible", "progress display; the return value is the caller's own iterable"),
 Target(51, "jmespath", "eligible", "expression evaluation over caller-supplied data; results branch on the data's shape"),
 Target(52, "rpds-py", "ineligible", "persistent data structures; no assumption about meaning"),
 Target(53, "yarl", "eligible", "URL normalisation and percent-encoding branch on the input string"),
 Target(54, "jsonschema", "eligible", "validation outcomes branch on the types present in the instance and the schema"),
 Target(55, "rich", "ineligible", "terminal rendering"),
 Target(56, "markdown-it-py", "eligible", "parsing and HTML output branch on the content supplied"),
 Target(57, "multidict", "ineligible", "a container"),
 Target(58, "propcache", "ineligible", "a cache"),
 Target(59, "s3fs", "defer", "the boto3 surface (rank 1)"),
 Target(60, "fastapi", "eligible", "request parsing and response model coercion branch on the supplied data"),
 Target(61, "referencing", "eligible", "$ref resolution branches on the structure of the supplied documents"),
 Target(62, "tomlkit", "eligible", "parse and round-trip behaviour branches on the shape of the supplied values"),
 Target(63, "frozenlist", "ineligible", "a container"),
 Target(64, "jsonschema-specifications", "ineligible", "bundled schema data"),
 Target(65, "pyasn1", "eligible", "decoding branches on the tags and lengths in caller-supplied bytes"),
 Target(66, "wheel", "ineligible", "packaging tooling"),
 Target(67, "websockets", "eligible", "framing and close semantics branch on what the peer sends"),
 Target(68, "aiohappyeyeballs", "ineligible", "connection racing; transport"),
 Target(69, "mdurl", "eligible", "URL encode/decode branches on the input string"),
 Target(70, "aiosignal", "ineligible", "a callback container"),
 Target(71, "google-auth", "eligible", "credential selection and token refresh branch on the supplied credential material"),
 Target(72, "pillow", "eligible", "decoding branches on format, mode and truncation of the supplied image"),
 Target(73, "googleapis-common-protos", "ineligible", "generated message definitions"),
 Target(74, "pytz", "eligible", "localize/normalize branch on the supplied datetime; the naive-attach footgun is the canonical instance"),
 Target(75, "sniffio", "ineligible", "detects the running async library; no caller data"),
 Target(76, "importlib-metadata", "eligible", "version and entry-point resolution branch on what is installed"),
 Target(77, "trove-classifiers", "ineligible", "a list of strings"),
 Target(78, "zipp", "ineligible", "zip path adapter; transport-like"),
 Target(79, "opentelemetry-semantic-conventions", "ineligible", "constants"),
 Target(80, "annotated-doc", "ineligible", "metadata"),
 Target(81, "virtualenv", "ineligible", "environment tooling"),
 Target(82, "hatchling", "ineligible", "build backend"),
 Target(83, "pydantic-settings", "eligible", "environment parsing and coercion branch on the supplied strings"),
 Target(84, "tzdata", "ineligible", "timezone data"),
 Target(85, "wrapt", "eligible", "proxy behaviour branches on the type and protocol support of the wrapped object"),
 Target(86, "ghapi", "eligible", "pagination and response shaping branch on the API response, as boto3 does"),
 Target(87, "greenlet", "ineligible", "coroutine primitives"),
 Target(88, "opentelemetry-api", "ineligible", "a no-op API surface by design"),
 Target(89, "huggingface-hub", "eligible", "cache and revision resolution branch on the supplied repo id and revision"),
 Target(90, "opentelemetry-sdk", "eligible", "sampling decisions branch on trace state and attributes supplied by the caller"),
 Target(91, "pyasn1-modules", "defer", "the pyasn1 surface (rank 65)"),
 Target(92, "tenacity", "eligible", "retry semantics depend on caller-supplied predicates and on whether the call is idempotent"),
 Target(93, "google-api-core", "eligible", "retry and pagination behaviour branch on the response"),
 Target(94, "regex", "eligible", "matching semantics branch on the pattern and differ from the stdlib re in documented ways"),
 Target(95, "pyarrow", "eligible", "type inference and casting branch on the values converted"),
 Target(96, "python-multipart", "eligible", "parsing branches on boundaries and headers in caller-supplied content"),
 Target(97, "textual", "ineligible", "terminal UI framework"),
 Target(98, "openai", "eligible", "retry, streaming and parameter handling branch on the request and response"),
 Target(99, "grpcio", "eligible", "deadline and status handling branch on the call and the peer's response"),
 Target(100, "soupsieve", "eligible", "CSS selector matching branches on the structure of the supplied document"),
)

ELIGIBLE = tuple(t for t in TARGETS if t.verdict == "eligible")
INELIGIBLE = tuple(t for t in TARGETS if t.verdict == "ineligible")
DEFERRED = tuple(t for t in TARGETS if t.verdict == "defer")
