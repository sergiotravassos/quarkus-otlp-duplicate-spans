#!/usr/bin/env bash
# Counts spans that reached the collector more than once (same traceId + spanId), per service.
set -euo pipefail
file="${1:-out/spans.json}"
python3 - "$file" <<'PY'
import collections, json, sys

seen = collections.defaultdict(collections.Counter)
for line in open(sys.argv[1]):
    line = line.strip()
    if not line:
        continue
    for rs in json.loads(line).get("resourceSpans", []):
        attrs = {a["key"]: next(iter(a["value"].values())) for a in rs["resource"].get("attributes", [])}
        service = attrs.get("service.name", "?")
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                seen[service][(span["traceId"], span["spanId"])] += 1

for service, counts in sorted(seen.items()):
    dup = sum(1 for n in counts.values() if n > 1)
    print(f"{service}: {len(counts)} spans, {dup} received more than once")
PY
