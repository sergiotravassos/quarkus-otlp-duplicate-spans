# Experiments

Each experiment had its question, setup and expected outcome written down before the measurement started (E3 and E4
were written at the time they started; see the notes in each file). Times are UTC.

| | where | what | result |
|---|---|---|---|
| [E1](E1-shared-environment-pause-sweep.md) | shared test environment | pause between requests, 20–120 s | copies peak at 60 s (5/16), none above 60 s |
| [E2](E2-server-idle-30s.md) | same, collector `max_connection_idle: 30s` | same sweep | 60 s goes to 0/16, copies remain at 20 s and 30 s |
| [E3](E3-real-services-async.md) | OpenShift Local, three real services, native | pause sweep, async flow | 16 resends, only after pauses that are multiples of 10 s |
| [E4](E4-load-and-short-pauses.md) | same, with packet capture | load blocks + pauses 2–70 s | 24 resends, 24/24 right after a FIN from the app; 0 during load |
| [E5](E5-minimal-reproducer.md) | OpenShift Local, minimal app, JVM | job every 20 s vs 25 s, Quarkus 3.15.7 and 3.40.1 | 62–65% of batches resent at 20 s, 0 at 25 s |
| [E6](E6-timeout-workaround.md) | same | `traces.timeout=65s` | 0 resends |
| [E7](E7-client-x-server.md) | same | client setting × collector `max_connection_idle` (30 s, 60 s, none), plus the patch | with the 65 s timeout or the patch: 0 in every phase |
| [E8](E8-who-closes.md) | same | Vert.x debug log on the client | 27 idle closes, 27 resends, one to one |
| [E9](E9-local-docker.md) | laptop: macOS host vs Linux container | the README path | macOS host 1/106, Linux container 38/92 at 20 s; 0 for both controls |
