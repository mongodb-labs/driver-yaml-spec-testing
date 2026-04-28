You are classifying a single MongoDB driver Jira ticket for a research paper on cross-language conformance testing of MongoDB drivers.

Context. MongoDB maintains a dozen or so client driver libraries (PyMongo, mongo-java-driver, mongo-csharp-driver, mongo-go-driver, libmongoc, mongo-rust-driver, the Node driver, the Ruby driver, the PHP libraries, and historically Perl/Swift/Erlang/Haskell/HHVM/the mgo Go fork). Each driver implements a shared set of cross-language **specifications** ("specs") that define identical behavior. Major spec areas include:

- BSON (binary serialization)
- Server Discovery and Monitoring (SDAM) --- how a driver tracks the topology of a replica set or sharded cluster
- Server Selection --- which server to send a given operation to
- Connection Monitoring and Pooling (CMAP) --- the connection pool's lifecycle, eviction, sizing
- Connection String / URI parsing
- DNS seedlist / SRV
- Authentication (SCRAM, X.509, GSSAPI, MONGODB-AWS, MONGODB-OIDC)
- CRUD --- insert/update/delete/find/aggregate semantics, including bulk write
- Commands --- shape of the command-and-response wire protocol
- Command Monitoring --- the public API for observing every command sent and received
- Sessions --- logical sessions, session pooling
- Causal Consistency
- Transactions --- session-scoped multi-document transactions
- Retryable Reads / Retryable Writes
- Change Streams
- Read Concern / Write Concern
- Cursors / find / getMore / killCursors
- Stable API (formerly "Versioned API")
- Client-Side Field-Level Encryption (CSFLE) and Queryable Encryption
- GridFS
- Compression (wire-level)
- Load Balancer support
- OCSP (TLS revocation)
- Logging (standardized log format across drivers)
- OpenTelemetry / tracing
- Index management
- Collation
- Initial DNS seedlist discovery (mongodb+srv://)
- AbstractMongoCRUD operations against time-series and capped collections

The driver tickets we care about for this paper fall into a few buckets. Your job is to classify which bucket the ticket fits into, conservatively.

# Categories

For each ticket, choose **exactly one** primary category. Be conservative: if the ticket is about packaging, build infra, CI, docs typos, dependency bumps, performance only, internal refactors with no behavioral change, support questions, or anything else not about cross-driver behavior or specification conformance, classify it as `not_relevant`.

- `driver_spec_nonconformance` --- The driver was not implementing a published spec correctly. Either the spec said X and the driver did Y, or the driver had a bug in code that implements a spec area, where the bug constitutes a deviation from the spec. Includes spec-level edge cases the driver got wrong.

- `cross_driver_inconsistency` --- The ticket explicitly references behavior in another driver, or implies "driver X does this but driver Y doesn't"; a fix to align with peer drivers; a divergence detected by spec test failures or by user reports of inconsistent behavior across languages.

- `avoidable_by_spec_conformance` --- A driver-internal bug in a component (connection pool, topology monitor, auth, retry logic, etc.) that **plausibly would have been avoided or caught earlier** if the driver had been more rigorously conformant to the relevant spec, or if a more carefully designed spec had existed. Example: a custom connection-pool implementation has a subtle deadlock that CMAP-conformant drivers would have caught earlier via shared CMAP spec tests. Use when the bug is in a *component* covered by a spec, even if the ticket doesn't mention the spec explicitly. This category is broader than `driver_spec_nonconformance`: the bug doesn't have to be a literal spec violation, just plausibly preventable by stronger spec discipline.

- `spec_ambiguity_or_gap` --- A bug whose root cause is the spec itself --- it was ambiguous, silent on this case, or wrong; the fix involved amending the spec (or this ticket links to a DRIVERS or SPEC ticket that did so). Includes "common-mode failures" where multiple drivers implemented the spec the same wrong way.

- `spec_authoring` --- The ticket itself is about writing or amending a specification (typically in DRIVERS or SPEC project), not fixing a driver bug.

- `test_infrastructure` --- About the test runner, YAML test format, UTF schema, spec test infrastructure, or CI plumbing for running spec tests --- not about driver behavior. Includes UTF schema bugs.

- `not_relevant` --- Everything else. Build/packaging, doc typos, performance-only, internal refactors with no behavior change, language-binding issues that don't touch any spec area, vendored-dependency bumps, support questions filed as bugs, etc.

# Spec area

If the ticket touches a spec area, name it. Use one of the spec names listed above (lowercased, hyphen-separated, e.g. `cmap`, `sdam`, `retryable-writes`, `transactions`, `command-monitoring`, `csfle`, `connection-string`, `bson`, `crud`, `change-streams`, `sessions`, `causal-consistency`, `auth`, `auth-oidc`, `auth-aws`, `auth-scram`, `stable-api`, `gridfs`, `compression`, `load-balancer`, `ocsp`, `logging`, `opentelemetry`, `read-concern`, `write-concern`, `server-selection`, `dns-seedlist`, `wire-protocol`, `index-management`, `collation`, `cursors`). If no spec area applies (or you classified as `not_relevant` / `test_infrastructure`), use `none`. If unclear, your best single guess.

# Cross-driver evidence

Set `mentions_other_driver: true` if the summary or description names another driver by language or product name (e.g. "the Java driver does X", "matches behavior of pymongo", "see NODE-1234"), OR if `links` contains a key from a different driver project than the ticket's own.

# Confidence

Give a confidence in your classification: `high`, `medium`, or `low`. Use `low` when the description is very thin or the signal is weak. Default to `medium`.

# Output format

Output **only** a single JSON object on one line, with no markdown fence, no preamble, no explanation outside the JSON. Keys exactly:

```
{"category": "...", "spec_area": "...", "mentions_other_driver": true|false, "confidence": "high|medium|low", "rationale": "<one short sentence, max 25 words>"}
```

The rationale must cite the specific signal you used (a phrase from the summary/description, or a linked ticket key). Do not speculate. If the ticket is too thin to classify, choose `not_relevant` with `confidence: low` and rationale `insufficient detail`.
