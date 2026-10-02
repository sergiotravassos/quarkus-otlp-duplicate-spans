# E8: who closes the connection

**Question.** Is the FIN before each resend sent by the read idle handler, and not by the pool or anything else?

**Setup.** One pod, Quarkus 3.15.7, job every 20 s, with `QUARKUS_LOG_CATEGORY__IO_VERTX_CORE_NET_IMPL__LEVEL=DEBUG`.
The category has to be the package: environment variables are lower-cased, so a category ending in
`ConnectionBase` does not match. Ran for 20 minutes next to E7 phase A, on its own connection. The collector's 30 s
idle setting plays no part with exports 20 s apart.

**Result.** 27 times `The connection will be closed due to timeout` (`ConnectionBase.handleIdle`, on the event
loop), and 27 resends out of 66 batches. They pair up one to one:
- each close is followed by a resend 11–27 ms later;
- each resend has a close right before it;
- the original request reaches the collector in the same millisecond as the close.

```
23:12:12.103 DEBUG [io.vertx.core.net.impl.ConnectionBase] (vert.x-eventloop-thread-1) The connection will be closed due to timeout
23:12:32.146 DEBUG [io.vertx.core.net.impl.ConnectionBase] (vert.x-eventloop-thread-1) The connection will be closed due to timeout
```

## Why the two timers meet so often

- `BatchSpanProcessor` (SDK 1.39.0) waits for the export result (`result.join(...)`), then sets the next export to
  now + 5 s. Its schedule starts from the moment the previous response arrived.
- Netty's `IdleStateHandler` records `lastReadTime` when that same response is read. The reader idle task fires
  10 s later and reschedules itself for another full 10 s while nothing is read.

Both timers start from the same instant, one with a 5 s period and one with 10 s. An export after a pause that is
a multiple of 10 s starts within milliseconds of an idle check. Whether it is duplicated depends on which of the two
runs first on the event loop. The `BatchSpanProcessor` only sets the timing; the resend comes from `VertxGrpcSender`,
which retries up to 3 times from the response's exception handler and logs nothing unless all attempts fail.
