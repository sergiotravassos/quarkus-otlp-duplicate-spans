# E9: on a laptop, macOS host vs Linux container

**Question.** Does the README path reproduce it outside OpenShift?

**Setup.** macOS 27 (arm64), Colima 0.10.1, Docker 29.2.1, collector `otel/opentelemetry-collector-contrib:0.144.0`
with a file exporter, and Quarkus 3.40.1 (Java 21).
1. JVM on the macOS host, collector in Docker, 35 minutes: jobs every 20 s, every 25 s, and every 20 s with
   `traces.timeout=65s`.
2. The same jar in `ubi9/openjdk-21-runtime` containers, in the same Compose project as the collector, 30 minutes.

**Result.**

| | every 20 s | every 25 s | every 20 s, timeout 65 s |
|---|---|---|---|
| JVM on the macOS host | 1/106 | 0/85 | 0/101 |
| Linux container | 38/92 | 0/74 | 0/92 |

The likely reason, not measured: on the macOS host the idle check almost always runs before the export, finds no active
stream, and does nothing. In a Linux container the export is often written first. Either way, the outcome depends
on the order of two timers that fire milliseconds apart, so the README runs the application in Compose.
