#!/usr/bin/env python3
"""Find export requests that the collector received twice.

Reads the collector's debug exporter output (verbosity: detailed). Every "ResourceSpans #0" line starts one export
request. A request counts as a resend when every span in it had already been received.

With a tcpdump capture of SYN/FIN/RST on port 4317 (see openshift/README) and a "pod ip" file, each resend is matched
with the FIN sent by the same application just before it.

  python3 resends.py collector.log [--tcp tcp-4317.txt --ips ips.txt] [--from EPOCH --to EPOCH]
"""
import argparse, calendar, collections, datetime, re


def epoch(text, fmt):
    d = datetime.datetime.strptime(text[:26], fmt)
    return calendar.timegm(d.timetuple()) + d.microsecond / 1e6


def requests(path):
    out, cur = [], None
    for line in open(path, errors="replace"):
        m = re.match(r"(\S+)Z\s+info\s+ResourceSpans #0", line)
        if m:
            cur = {"t": epoch(m.group(1), "%Y-%m-%dT%H:%M:%S.%f"), "service": None, "host": None, "spans": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        m = re.search(r"-> service\.name: Str\((.*)\)", line)
        if m and cur["service"] is None:
            cur["service"] = m.group(1)
        m = re.search(r"-> host\.name: Str\((.*)\)", line)
        if m and cur["host"] is None:
            cur["host"] = m.group(1)
        m = re.match(r"\s*ID\s*:\s*([0-9a-f]+)", line)
        if m:
            cur["spans"].append(m.group(1))
    seen = {}
    for r in out:
        r["resend"] = bool(r["spans"]) and all(s in seen for s in r["spans"])
        if r["resend"]:
            r["delay"] = r["t"] - seen[r["spans"][0]]["t"]
        else:
            for s in r["spans"]:
                seen.setdefault(s, r)
    return out


def tcp_events(path, ips):
    pods = {}
    for line in open(ips):
        pod, ip = line.split()[:2]
        pods[ip] = pod
    events, last = [], {}
    pattern = (r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) \S+ +\S+ +IP (\S+)\.(\d+) > (\S+)\.(\d+): "
               r"Flags \[([^\]]+)\](?:, seq (\d+))?")
    for line in open(path, errors="replace"):
        m = re.match(pattern, line)
        if not m:
            continue
        t = epoch(m.group(1), "%Y-%m-%d %H:%M:%S.%f")
        src, sport, dst, dport, flags, seq = m.groups()[1:]
        to_collector = dport == "4317"
        app_ip, app_port = (src, sport) if to_collector else (dst, dport)
        key = (app_port, flags, seq)  # the same packet shows up on the service IP and on the pod IP
        if key in last and t - last[key] < 0.05:
            continue
        last[key] = t
        events.append({"t": t, "pod": pods.get(app_ip, app_ip), "by": "app" if to_collector else "collector",
                       "flags": flags})
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--tcp")
    ap.add_argument("--ips")
    ap.add_argument("--from", dest="start", type=float)
    ap.add_argument("--to", dest="end", type=float)
    a = ap.parse_args()
    reqs = [r for r in requests(a.log) if (a.start is None or r["t"] >= a.start) and (a.end is None or r["t"] <= a.end)]
    events = tcp_events(a.tcp, a.ips) if a.tcp else []
    print("%-36s %9s %9s %14s" % ("service", "batches", "resent", "FIN just before"))
    for svc in sorted({r["service"] for r in reqs}):
        mine = [r for r in reqs if r["service"] == svc]
        resent = [r for r in mine if r["resend"]]
        with_fin = 0
        for r in resent:
            near = [e for e in events if e["by"] == "app" and "F" in e["flags"] and -1 <= e["t"] - r["t"] <= 0.2]
            with_fin += any(e["pod"] == r["host"] for e in near)
        print("%-36s %9d %9d %14s" % (svc, len(mine) - len(resent), len(resent), with_fin if events else "-"))


if __name__ == "__main__":
    main()
