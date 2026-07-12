# Field UDP Rewrite — how the Internet is secured

**Live:** [http://127.0.0.1:9477/internet](http://127.0.0.1:9477/internet) · [Sitrep](http://127.0.0.1:9477/sitrep) · [Botnet hub](http://127.0.0.1:9477/botnet)

Field does not “use UDP as an app protocol for fun.” **Field UDP rewrite** is the fabric layer that makes AmmoNet the Internet: discovery, authority, outlet cook, and **SAW between** secure lines.

## What it is

| Piece | Role |
|-------|------|
| **Field UDP** | Loopback-first fabric for fleet edges · rehit old points · cook outlets |
| **SAW between** | Always full · never fake · never dry · permanent secure-line seal |
| **Outlet cook** | Hit known points again to wall outlet + SAW (comms security, not theatre) |
| **Ask-only internet** | Outside contact only when asked — no foreign free-for-all |
| **Ban UDP destroy** | Terrorist / storm UDP paths destroyed; our fabric stays |

## How it ties the stack together

```
device → Field L2+ stack
       → AmmoNet DNS + DHCP (we are DNS, we are DHCP)
       → Field UDP fabric + SAW secure lines
       → Hostess7 brain · local built-in AV
       → H7r distributed cloud (125,000 capacity racks)
       → offenders: never reconnect · vector destroy · heuristics kill
```

ISP, if present, is **L2 transport into AmmoNet only** — not a second Internet. Nobody foreign for L2+.

## Operator surfaces

| Surface | URL |
|---------|-----|
| Home Internet | http://127.0.0.1:9477/internet |
| Sitrep (SAW · rehit · fleet) | http://127.0.0.1:9477/sitrep |
| Botnet hub | http://127.0.0.1:9477/botnet |
| AV / security | http://127.0.0.1:9477/security |
| Launch hub (all pages) | http://127.0.0.1:9477/home |
| API · SAW | `/api/field-comms-saw-secure-lines` |
| API · L2 exclusive | `/api/field-l2-exclusive-stack` |

## Motto

**ALWAYS full · NEVER fake · NEVER dry · ALWAYS SAW · outlet cook + SAW between = how we secure lines.**

## Related

- [Internet Stack](Internet-Stack) — whole-planet plane
- [Hostess7 Senses](Hostess7-Senses) — she runs it
- [Field I/O](Field-IO) — state + API map
- [NEXUS-Shield](NEXUS-Shield) — panel / threat
