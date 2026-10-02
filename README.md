# Quarkus OTLP gRPC exporter: batches sent twice

The Quarkus OTLP gRPC exporter (`VertxGrpcSender`) sometimes sends the same export request twice. The collector
receives both, and the backend stores every span in that batch twice: same traceId, same spanId, same content,
milliseconds apart. OTLP has no deduplication, so anything built on spans counts them twice (span metrics, service
graphs, trace search).

It happens to applications that export in bursts with pauses of 10, 20, 30, 40, 50 or 60 s between exports, not to
applications with constant traffic.

## What happens

1. `VertxGrpcSender` creates its HTTP client with `setReadIdleTimeout(timeout)`, where `timeout` is the exporter
   timeout (10 s by default).
2. Netty's `IdleStateHandler` fires a reader idle event 10 s after the last read, and again every 10 s while nothing
   is read.
3. Vert.x `Http2ClientConnection.handleIdle` ignores the event when no stream is active, and closes the connection
   when one is.
4. The `BatchSpanProcessor` schedules the next export 5 s after the previous one completed, the same instant Netty
   records as the last read. After a pause that is a multiple of 10 s, the export and the idle check fall within
   milliseconds of each other.
5. When the export is written first, the idle check finds its stream active and closes the connection. The
   collector already has the whole request and accepts it. The client sees the stream closed without a response,
   and `VertxGrpcSender` retries on a new connection, without logging anything.

From a packet capture (E4), for a connection that last read something 20 s earlier:

```
36.704258  app -> collector  request written (HEADERS + DATA)
36.704370  app -> collector  FIN (no GOAWAY)
36.738     app -> collector  SYN, new connection
36.742     app -> collector  same request again
```

With `io.vertx.core.net.impl` at DEBUG, every resend comes right after `The connection will be closed due to
timeout` (27 of 27 in E8).

## Results

| | batches | sent twice |
|---|---|---|
| Quarkus 3.40.1, span every 20 s | 131 | 85 (65%) |
| Quarkus 3.15.7, span every 20 s | 131 | 81 (62%) |
| either version, span every 25 s | 210 | 0 |
| either version, every 20 s, `quarkus.otel.exporter.otlp.traces.timeout=65s` | 250 | 0 |
| 3.40.1 with `patch/` (no read idle timeout, timeout on the response) | 396 | 0 |

The OpenShift runs used the Red Hat build of OpenTelemetry collector 0.158. Details, including runs with three real
services and a collector idle timeout of 30 s and 60 s, are in [docs/experiments](docs/experiments/README.md).

## Workaround

Set the exporter timeout above the 60 s HTTP/2 keep-alive of the Vert.x client:

```
quarkus.otel.exporter.otlp.traces.timeout=65s
```

An idle connection is then removed from the pool before the idle check fires. With traffic, there is always
something to read within the 5 s batch delay. The collector's `max_connection_idle` makes no difference once this is
set (E7). The cost: a connection that stops answering is only dropped by this check after 65 s. The
`BatchSpanProcessor` still gives up on each export after its own 30 s.

## Run it

Requires Java 17+, Maven and Docker.

```
mvn -q package -Dquarkus.platform.version=3.40.1
docker compose up -d --build
```

This starts the collector and three copies of the application in Linux containers:
- `every-20s`: the bug;
- `every-25s`: exports fall between the idle checks (control);
- `every-20s-timeout-65s`: the workaround.

Wait 30 minutes, then run `./count-duplicates.sh`. The collector writes `out/spans.json`, and the script counts
the spans that appear more than once. Use `-Dquarkus.platform.version=3.15.7` to build an older version.

Run the application inside Linux. Started directly on macOS (JVM on the host, collector in Docker), it gave 1 duplicate in
106 at 20 s; the same jar in a container gave 38 in 92. Whether a resend happens depends on which of two timers runs first, and
that differs between operating systems.

[openshift/](openshift/README.md) has the same setup for OpenShift, with a TCP capture on the node.

## Layout

```
src/                    the application: one span every job.every
collector/, docker-compose.yml
count-duplicates.sh     duplicates in the file exporter output
count-duplicates-from-logs.sh   duplicates in the debug exporter output
analysis/resends.py     resent requests per service, matched with FINs from a TCP capture
analysis/h2frames.py    HTTP/2 control frames from a tcpdump -x capture
openshift/              manifests for E5, E6 and E7
patch/                  the VertxGrpcSender change tested in E7
docs/experiments/       one file per experiment
```
