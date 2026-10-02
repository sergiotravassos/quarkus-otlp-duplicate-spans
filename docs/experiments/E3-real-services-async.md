# E3: three real services on OpenShift Local, asynchronous flow

**Question.** Does the effect show up outside the shared environment, with the real services and nothing else
running?

**Setup.** OpenShift Local 2.62 (OpenShift 4.22, arm64 node). Three services from the environment of E1, built as
native images from the same source and dependency versions (Quarkus 3.15.7, Vert.x 4.5.21–4.5.34, OpenTelemetry SDK
1.39.0), but for arm64 and on a different base image:
- A: HTTP endpoint that answers 202 and publishes to Kafka;
- B: Kafka consumer that calls an HTTP mock and publishes the reply;
- C: Kafka consumer that writes audit records to Cassandra.

They run with Kafka (one KRaft node), Cassandra, Oracle, WireMock and Vault in dev mode. The collector is the Red
Hat build of OpenTelemetry 0.158, OTLP gRPC receiver with no keepalive settings, `debug` exporter (detailed). 97
requests to A; the pause before each was drawn from {20, 25, 30, 35, 40, 50, 55, 60, 65, 70, 90, 120 s}, 8 each,
random order (seed 20261003), after a 180 s warm-up.

The setup was written when the run started, not before.

**Expected.** Either copies concentrated at 60 s, as in E1, or none at all.

**Result.** 97/97 requests answered 202. 16 export requests arrived twice (C 8, A 5, B 3). Each copy arrived
0–7 ms after the original. Requests with a resend in at least one service, per pause:

| pause | 20 | 25 | 30 | 35 | 40 | 50 | 55 | 60 | 65 | 70 | 90 | 120 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| resends (3 services × 8) | 3 | 0 | 6 | 0 | 4 | 1 | 0 | 2 | 0 | 0 | 0 | 0 |

Neither prediction held. Copies appeared only after pauses that are multiples of 10 s and never above 60 s. The
collector had no idle setting, so the connection was not being closed by the server. This is what led to E4.
