# CPU duty trace v1 — virtual-clock worker simulation

9/9 traces PASS. Each submits 11 requests: 6 engine admissions, 4 denials
(including 1 queue expiry), 3 cancelled engine calls, 2 OK replies, 1 failed
load and 1 replaced pending request. Categories overlap as defined in PROTOCOL.md.

| Language | Candidates | Simulated CPU ms | Simulated wall ms | Ready by 1000 ms boundary |
| --- | --- | --- | --- | --- |
| EN | 2 | 11079 | 276024 | 1/1 |
| EN | 4 | 12687 | 276448 | 1/1 |
| EN | 8 | 16623 | 277518 | 0/1 |
| ES | 2 | 11899 | 276248 | 1/1 |
| ES | 4 | 14759 | 277044 | 1/1 |
| ES | 8 | 19881 | 278374 | 0/1 |
| RU | 2 | 13631 | 276710 | 1/1 |
| RU | 4 | 17229 | 277662 | 0/1 |
| RU | 8 | 24667 | 279636 | 0/1 |

Each exhaustion probe ends at -7450 credit units (-496.667 CPU ms). Its
100 CPU ms / 25 wall ms cancellation tail is injected, not measured.

Only five of nine configured warm-cost boundary probes finish within 1000 ms.
This motivates nonblocking fallback; it does not estimate production coverage.
Real CPU/time, Binder tracing, idle unload timing, physical battery, quality
and the complete device trace experiment remain unqualified.
