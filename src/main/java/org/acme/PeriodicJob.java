package org.acme;

import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import io.quarkus.scheduler.Scheduled;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

@ApplicationScoped
public class PeriodicJob {

    @Inject
    Tracer tracer;

    // A multiple of 10s lines the export up with the client's read idle check (exporter timeout, 10s by default).
    @Scheduled(every = "${job.every:20s}", delayed = "5s")
    void run() {
        Span span = tracer.spanBuilder("periodic-job").startSpan();
        span.end();
    }
}
