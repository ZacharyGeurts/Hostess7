# AmmoCode 4.9.0 upload — distro 5.0.0

**Upload track:** v4.9.0 (GitHub)  
**Public stack:** Grok16-5.0.0 · belt_2_0

AmmoCode is **THE compiler GUI for 2027** on the Grok16 5.0 stack. This release uploads as **4.9.0** for final review; product identity stays **5.0**.

## Highlights

- Hardened security — transparent vuln scan, combinatorics rewrite, DDoS guard
- Invite-only collab — WebSocket room, IP friends, voice, cursor personas
- Network mesh — polite LAN discovery, friend/block lists, threat ratings, HTTP tunnel
- MITM pins — beacon fingerprints, session proofs, frame MAC on screen share
- Permitted screen share — host-grant GUI capture only (no ambient getDisplayMedia)
- ZNetwork shield — attach-only if running; defield SG/Grok16 on boot when fielded
- AI primer — per-language copy-paste tutorials on language switch
- Tab aging, clipboard icons, Settings/Help menus

## Run

```bash
cd AmmoCode && npm start
# GUI  http://127.0.0.1:9555/
# Tab  http://127.0.0.1:9555/tab.html
# API  http://127.0.0.1:9555/api/ammocode
# WS   ws://127.0.0.1:9556 (invite-only)
```

## Review gate

See [REVIEW_PREP.md](REVIEW_PREP.md) for reviewer checklist.