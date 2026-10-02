# E7: client setting × collector idle timeout

**Question.** Which combination of exporter timeout (client) and `max_connection_idle` on the collector (server)
removes the duplicates? Does the patch in `patch/` remove them without any setting?

**Setup.** Same collector as E5, run in three consecutive phases of 35 minutes, with the receiver's
`keepalive.server_parameters.max_connection_idle` set to A = 30 s, B = 60 s, C = not set. The first 2 minutes of
each phase are not counted (the collector restarts). Eight JVM pods ran through all three phases:

- Quarkus 3.15.7, default timeout (10 s): jobs every 20, 30 and 60 s;
- Quarkus 3.15.7, `traces.timeout=65s`: jobs every 20, 30 and 60 s;
- Quarkus 3.40.1 with the patch: jobs every 20 and 60 s.

Expected (written before the run):
- default timeout: copies at 20 s and 30 s in all phases, and at 60 s in B and C;
- 65 s timeout and patch: none at 20 s;
- open question: what happens when the server's close coincides with an export (30 s in A, 60 s in B).

**Result** (batches resent / batches; every resend followed a FIN from the app):

| client, job | A: idle 30 s | B: idle 60 s | C: no idle |
|---|---|---|---|
| 3.15.7 default, 20 s | 51/99 | 56/99 | 57/99 |
| 3.15.7 default, 30 s | **0/65** | 22/66 | 20/66 |
| 3.15.7 default, 60 s | 0/33 | 0/33 | 1/33 |
| 3.15.7, timeout 65 s (20, 30, 60 s) | 0/197 | 0/198 | 0/198 |
| 3.40.1 patched (20, 60 s) | 0/132 | 0/132 | 0/132 |

- **With the client fixed, the server's idle setting does not matter.** The 65 s timeout and the patch gave 0 in all
  three phases.
- **Without the fix, a 30 s server idle only removes copies at 30 s.** The server closes the connection at 30 s, so
  an export at 30 s, or after a longer pause, starts on a fresh connection. Copies at 20 s stay. Raising the server
  idle above 60 s is the same as not setting it (phase C).
- **The prediction for 60 s was wrong.** In this app the pool's 60 s keep-alive removes the idle connection before
  the export picks it up, so 60 s rarely hits (1/99). In E1 it hit 5/16; that difference is not explained.

The patch, in full:

```diff
         var httpClientOptions = new HttpClientOptions()
                 .setHttp2ClearTextUpgrade(false) // needed otherwise connections get closed immediately
-                .setReadIdleTimeout((int) timeout.getSeconds())
                 .setTracingPolicy(TracingPolicy.IGNORE); // needed to avoid tracing the calls from this gRPC client
...
-                request.send(buffer).onSuccess(new Handler<>() {
+                request.send(buffer).timeout(exportTimeout.toMillis(), MILLISECONDS).onSuccess(new Handler<>() {
```

It is a test patch, not a finished fix. The timeout on the response future fails the attempt, but it does not reset
the stream.
