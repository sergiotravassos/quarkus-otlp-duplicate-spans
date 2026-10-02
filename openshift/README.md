# Running on OpenShift

Tested on OpenShift Local 2.62 (OpenShift 4.22.1).

```
oc apply -f 01-operator.yaml        # Red Hat build of OpenTelemetry operator
oc apply -f 02-collector.yaml       # namespace otlp-repro and collector "repro" (OTLP gRPC, debug exporter)
oc project otlp-repro

mvn -q package -Dquarkus.platform.version=3.40.1
mkdir -p /tmp/ctx && cp Dockerfile.jvm /tmp/ctx/Dockerfile && cp -R ../target/quarkus-app /tmp/ctx/
oc new-build --binary --strategy=docker --name repro-jvm-3401
oc start-build repro-jvm-3401 --from-dir=/tmp/ctx --follow
```

Build `repro-jvm-3157` the same way with `-Dquarkus.platform.version=3.15.7`. Then apply the pods of the experiment
you want: `04-app-jvm.yaml` (E5), `05-app-jvm-timeout65.yaml` (E6), `06-e7.yaml` (E7). The image used by E7 for the
patched sender is built from `../patch`: compile the patched `VertxGrpcSender` against the application's `lib/`
and replace the classes in `lib/main/io.quarkus.quarkus-opentelemetry-3.40.1.jar`.

Collector log and pod IPs:

```
oc logs -f deploy/repro-collector > collector.log
oc get pods -o wide --no-headers | awk '{print $1, $6}' > ips.txt
```

TCP capture on the node (the debug image has `tcpdump`):

```
oc debug node/<node> -q -- sh -c 'tcpdump -i any -nn -tttt -l "tcp port 4317 and (tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-rst) != 0)"' > tcp-4317.txt
```

Then `python3 ../analysis/resends.py collector.log --tcp tcp-4317.txt --ips ips.txt`.

To set the collector's idle timeout, as in E7:

```
oc patch otelcol repro --type=merge -p '{"spec":{"config":{"receivers":{"otlp":{"protocols":{"grpc":{"keepalive":{"server_parameters":{"max_connection_idle":"30s"}}}}}}}}}'
```
