# E1: pause sweep in a shared test environment

**Question.** Does the pause before an export decide whether it is duplicated?

**Setup.** A test environment on OpenShift with Quarkus 3.15.7 services, the Red Hat build of OpenTelemetry
collector, and Tempo. One synchronous service that nobody else was calling. One request at a time; the pause before
each request was drawn from {20, 40, 50, 55, 60, 65, 70, 90, 120 s}, 8 times each, in random order (seed fixed in
advance). The request produces one export batch in each of two modules, so 16 batches per pause. Duplicates were
counted in Tempo (same traceId and spanId stored twice).

**Expected.** If the 60 s HTTP/2 keep-alive is involved, copies concentrate at 60 s and disappear above it.

**Result.**

| pause | batches stored twice |
|---|---|
| 20 s | 2/16 |
| 40 s | 1/16 |
| 50 s | 0/16 |
| 55 s | 1/16 |
| **60 s** | **5/16** |
| 65 s | 0/16 |
| 70 s | 0/16 |
| 90 s | 0/16 |
| 120 s | 0/16 |

60 s against ≥ 65 s: 5/16 against 0/64, Fisher's exact test p = 0.00018.

**What it did not explain.** The copies at 20, 40 and 55 s. E4 and E5 explain them: the trigger is the client's
10 s read idle check, and 60 s is where it lines up with the keep-alive and the 5 s batch grid at the same time. The
synchronous flow spreads one request's spans over several seconds, so its pauses are not exact.
