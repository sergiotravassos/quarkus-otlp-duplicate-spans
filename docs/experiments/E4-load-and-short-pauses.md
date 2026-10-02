# E4: load blocks, short pauses and a packet capture

**Question.** (a) Are there resends under constant traffic? (b) What is the shortest pause that causes one?
(c) Who closes the connection, the client or the server?

**Setup.** The services and collector of E3. 80 blocks in random order (seed 20261004): 30 s of load (1 or 5
requests/s) followed by a pause from {2, 5, 10, 15, 20, 30, 40, 50, 60, 70 s}, 4 repetitions per combination. The
first request after the pause is the probe. On the node, `tcpdump` captured SYN, FIN and RST on port 4317 for the
whole run. A second 8-minute capture with headers (`-s 200 -x`) shows the HTTP/2 frames.

The setup was written at the time the run started.

**Expected.** About 0 during load. Resends only after pauses of 60 s or less, none at 70 s. A connection close
right before each resend.

**Result.** 7280 requests, all 202, and 1688 export requests. There were 24 resends, all on the first export
after a pause and none during load.

| pause | 2 s | 5 s | 10 s | 15 s | 20 s | 30 s | 40 s | 50 s | 60 s | 70 s |
|---|---|---|---|---|---|---|---|---|---|---|
| probes with a resend (3 services) | 0/24 | 0/24 | 5/21 | 0/24 | 2/24 | 1/24 | 3/24 | 6/24 | 7/24 | 0/24 |

**24 of 24 resends follow a FIN sent by the application 5–40 ms earlier.** The application opens a new connection
right after and sends the same request again.

One of them, frame by frame (connection from service A, UTC):

```
20:58:16.697  collector -> app  HEADERS (response to the previous export)
              ... 20 s with nothing on this connection ...
20:58:36.704  app -> collector  HEADERS + DATA, ~19.6 KB (the export)
20:58:36.704  app -> collector  FIN, 11 µs after the last byte, no GOAWAY
20:58:36.705  collector -> app  FIN
20:58:36.738  app -> collector  SYN (new connection)
20:58:36.742  app -> collector  HEADERS stream 1: the same export again
```

The 2, 5 and 15 s pauses gave none: a 15 s pause puts the export halfway between two idle checks. Connections the
application closed after 60–70 s without traffic are the HTTP/2 keep-alive of the pool; those closes are clean and
cause no resend.

**Not explained.** Fifteen FINs from the application 10–55 s after its last export with no resend next to them. The
capture only has flags for those, so it does not say whether a request was on the wire.
