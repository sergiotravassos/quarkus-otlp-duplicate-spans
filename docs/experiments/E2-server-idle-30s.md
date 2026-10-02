# E2: collector with max_connection_idle 30 s

**Question.** If the collector closes idle connections after 30 s, do the copies at 60 s go away?

**Setup.** As E1, after the collector's OTLP gRPC receiver got
`keepalive.server_parameters.max_connection_idle: 30s`. Same request, the pause sweep extended with 25, 30 and 35 s.

**Expected.** 60 s drops to about 0; shorter pauses unchanged.

**Result.**

| pause | E1 (no server idle) | E2 (30 s) |
|---|---|---|
| 20 s | 2/16 | 5/16 |
| 25 s | — | 1/16 |
| 30 s | — | 3/16 |
| 35 s | — | 0/16 |
| 40–55 s | 2/48 | 0/48 |
| **60 s** | **5/16** | **0/16** |
| 65–120 s | 0/64 | 0/64 |

The server closes the idle connection before 60 s, so the next export opens a new one and nothing is resent. At
20 s and 30 s the connection is still alive and the client-side race (E4) is untouched. In the same environment,
two services with a 60 s job went from 46% and 26% of spans duplicated to 0%; a busier one went from about 5% to 2.2%.
