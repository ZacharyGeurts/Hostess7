# Distributed Cloud Center — H7r at 125,000

**Live:** [http://127.0.0.1:9477/cloud](http://127.0.0.1:9477/cloud) · API `/api/field-h7r-capacity-fleet`

H7r is the **datacenter bird**: pure capacity, redundant stripes, object/block/archive/big_data, local AV on every rack. Scaled to **match the fleet: 125,000**.

## Layout

```
fieldstorage/h7r-capacity/distributed-cloud-center/
  shard-0000/h7r-cloud-000000 …
  shard-0124/h7r-cloud-124999
```

Plus hot regional racks (`h7r-dc-*`, `h7r-cap-*`) and archive plane — **separate from** the 2,500 qemu internet racks.

## Scale command

```bash
python3 lib/field-h7r-capacity-fleet.py scale --target=125000
# or full build (includes scale):
python3 lib/field-h7r-capacity-fleet.py build --no-restripe
```

Env: `NEXUS_H7R_CAPACITY_TARGET=125000`

## Doctrine flags on every capacity rack

- `distributed_cloud_center: true`
- local built-in AV · always autopilot · self-governed · self-protected
- **no owners · planet whole**

## Stripe vs mass mesh

Mesh JSON does **not** dump 125k full node rows (would crush the panel). Authority count is **125,000**; detail mesh keeps hot racks + scale summary + sample shards for live stripe fabric.

## Related

- [Internet Stack](Internet-Stack)
- [Field UDP Rewrite](Field-UDP-Rewrite)
- API sitrep cloud row via `/cloud` panel
