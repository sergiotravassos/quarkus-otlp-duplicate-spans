# E6: exporter timeout above the keep-alive

**Idea.** The read idle timeout of the connection is the exporter timeout. If it is longer than the 60 s HTTP/2
keep-alive, an idle connection is taken out of the pool before the check fires. With traffic there is always
something to read within the 5 s batch delay.

**Setup.** Two more pods next to E5, both with a 20 s job (3.15.7 and 3.40.1), and with
`QUARKUS_OTEL_EXPORTER_OTLP_TRACES_TIMEOUT=65s` and `QUARKUS_OTEL_EXPORTER_OTLP_TIMEOUT=65s`.

**Expected.** 0 resends.

**Result.**

| pod | batches | resent |
|---|---|---|
| 3.15.7, every 20 s, timeout 65 s | 125 | 0 |
| 3.40.1, every 20 s, timeout 65 s | 125 | 0 |

**Cost.** A connection that stops answering is only dropped by this check after 65 s. The `BatchSpanProcessor`
still gives up on each export after its own 30 s (`otel.bsp.export.timeout`).
