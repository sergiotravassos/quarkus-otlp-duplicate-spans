# E5: minimal reproducer

**Question.** Does it reproduce with an application that has one scheduled span and nothing else, on the latest
Quarkus?

**Setup.** This repository: `PeriodicJob` creates one span every `job.every`. Four JVM pods (ubi9 OpenJDK 21) on
OpenShift Local, same collector as E3/E4 (no keepalive), running at the same time for about 44 minutes:

| | Quarkus | Vert.x | OpenTelemetry SDK |
|---|---|---|---|
| 3.40.1 | 3.40.1 | 4.5.34 | 1.62.0 |
| 3.15.7 | 3.15.7 | 4.5.21 | 1.39.0 |

each with a 20 s and a 25 s job. Written before the run: with the cause found in E4, copies at 20 s on both versions
with a FIN from the app each time, and about 0 at 25 s.

**Result.**

| pod | batches | resent | resent after a FIN from the app |
|---|---|---|---|
| 3.15.7, every 20 s | 131 | 81 (62%) | 81 |
| 3.40.1, every 20 s | 131 | 85 (65%) | 85 |
| 3.15.7, every 25 s | 105 | 0 | — |
| 3.40.1, every 25 s | 105 | 0 | — |

Analysis: `analysis/resends.py collector.log --tcp tcp-4317.txt --ips ips.txt`.
