#!/usr/bin/env bash
# Same count as count-duplicates.sh, reading the collector's debug exporter output (verbosity: detailed).
# Usage: oc logs deploy/repro-collector -n otlp-repro | ./count-duplicates-from-logs.sh
set -euo pipefail
python3 -c '
import collections, re, sys

seen = collections.defaultdict(collections.Counter)
service, trace = "?", None
for line in sys.stdin:
    m = re.search(r"service\.name: Str\((.*)\)", line)
    if m:
        service = m.group(1)
    m = re.match(r"\s*Trace ID\s*:\s*([0-9a-f]+)", line)
    if m:
        trace = m.group(1)
    m = re.match(r"\s*ID\s*:\s*([0-9a-f]+)", line)
    if m and trace:
        seen[service][(trace, m.group(1))] += 1

for service, counts in sorted(seen.items()):
    dup = sum(1 for n in counts.values() if n > 1)
    print(f"{service}: {len(counts)} spans, {dup} received more than once")
'
