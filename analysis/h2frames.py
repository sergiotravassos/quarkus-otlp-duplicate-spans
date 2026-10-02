#!/usr/bin/env python3
"""List TCP flags and HTTP/2 control frames from a `tcpdump -nn -tttt -s 200 -x` capture of port 4317.

Only the first 200 bytes of each segment are captured, so frames in the middle of large segments are missed. Control
frames travel in small segments, which is enough here.

  python3 h2frames.py capture.txt ips.txt
"""
import re, sys

TYPES = {0: "DATA", 1: "HEADERS", 3: "RST_STREAM", 4: "SETTINGS", 6: "PING", 7: "GOAWAY", 8: "WINDOW_UPDATE"}
pods = {}
for line in open(sys.argv[2]):
    pod, ip = line.split()[:2]
    pods[ip] = pod

packets, cur = [], None
for line in open(sys.argv[1], errors="replace"):
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) \S+ +\S+ +IP (\S+)\.(\d+) > (\S+)\.(\d+): Flags \[([^\]]+)\]", line)
    if m:
        cur = {"t": m.group(1)[11:], "src": m.group(2), "sport": m.group(3), "dst": m.group(4), "dport": m.group(5),
               "flags": m.group(6), "hex": ""}
        packets.append(cur)
        continue
    m = re.match(r"\s+0x[0-9a-f]+:\s+((?:[0-9a-f]{4}\s?)+)", line)
    if m and cur is not None:
        cur["hex"] += m.group(1).replace(" ", "")

seen = set()
for p in packets:
    b = bytes.fromhex(p["hex"]) if p["hex"] else b""
    if len(b) < 40:
        continue
    ihl = (b[0] & 0x0F) * 4
    doff = (b[ihl + 12] >> 4) * 4
    seq = int.from_bytes(b[ihl + 4:ihl + 8], "big")
    payload = b[ihl + doff:]
    to_collector = p["dport"] == "4317"
    app, port = (p["src"], p["sport"]) if to_collector else (p["dst"], p["dport"])
    key = (port, to_collector, seq, p["flags"])
    if key in seen:
        continue
    seen.add(key)
    out = []
    if any(f in p["flags"] for f in "SFR"):
        out.append("TCP[%s]" % p["flags"])
    i = 0
    if payload[:24] == b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n":
        out.append("PREFACE")
        i = 24
    while i + 9 <= len(payload):
        length = int.from_bytes(payload[i:i + 3], "big")
        ftype, fflags = payload[i + 3], payload[i + 4]
        stream = int.from_bytes(payload[i + 5:i + 9], "big") & 0x7FFFFFFF
        if ftype not in TYPES or length > 65536:
            break
        if ftype == 7 and i + 17 <= len(payload):
            out.append("GOAWAY(last=%d,err=%d)" % (int.from_bytes(payload[i + 9:i + 13], "big") & 0x7FFFFFFF,
                                                  int.from_bytes(payload[i + 13:i + 17], "big")))
        elif ftype == 3 and i + 13 <= len(payload):
            out.append("RST_STREAM(s=%d,err=%d)" % (stream, int.from_bytes(payload[i + 9:i + 13], "big")))
        elif ftype in (1, 4, 6):
            out.append("%s%s(s=%d)" % (TYPES[ftype], "+ACK" if fflags & 1 and ftype in (4, 6) else "", stream))
        i += 9 + length
    if out:
        print("%s %-40s %-9s %s" % (p["t"], "%s:%s" % (pods.get(app, app), port),
                                    "app" if to_collector else "collector", " ".join(out)))
