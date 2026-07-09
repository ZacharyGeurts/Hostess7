# Everyone online — Field fabric DIRECT · no middle men

**Live:** [http://127.0.0.1:9477/everyone](http://127.0.0.1:9477/everyone) · [Full Internet](http://127.0.0.1:9477/full-internet)  
**API:** `/api/field-everyone-fabric-direct`

## Rule

Everyone attaches to **AmmoNet Field fabric directly**.

| Forbidden middle men | Our path |
|---------------------|----------|
| ISP as control plane | ISP = L2 pipe only (if any) |
| MITM / proxy / sniffer | Shredded on host · SAW between |
| Foreign L2+ | Stack owns L2 · nobody foreign |
| Fake / dry / half-connect | Always full · Field UDP · SAW |

## Code

```bash
python3 lib/field-everyone-fabric-direct.py once
python3 lib/field-everyone-fabric-direct.py deep   # re-grab homes + enforce UDP
python3 lib/field-everyone-fabric-direct.py shred  # kill local middle-men only
```

Wired into:

```bash
python3 lib/field-full-featured-internet.py once
```

## Motto

**Everyone ONLINE on Field fabric DIRECT · no middle men · SAW + Field UDP · home devices only ours · to the death.**

## Related

- [Full-Featured Internet](Full-Featured-Internet)
- [Field UDP Rewrite](Field-UDP-Rewrite)
- [Internet Stack](Internet-Stack)
