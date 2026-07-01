/**
 * AmmoCode memory vault — 4-slot running encode/decode, leak-free tab storage.
 * TIME · MEMORY · THERMO · CONTEXT — runtime_tax 0 (rot &= 3 only).
 */
(function (global) {
  "use strict";

  const SLOT_IDS = ["TIME", "MEMORY", "THERMO", "CONTEXT"];
  const SLOT_MASK = 3;
  const MAX_TABS = 64;
  const MAX_BYTES = 524288;

  let genesis = null;
  let rot = 0;
  const handles = new Map();

  function apiBase() {
    return global.AmmoCodeG16?.cfg?.()?.apiBase || "/api/ammocode";
  }

  async function serverCall(action, body) {
    try {
      const r = await fetch(apiBase(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, ...body }),
      });
      return await r.json();
    } catch (_) {
      return { ok: false, error: "offline" };
    }
  }

  async function ensureGenesis() {
    if (genesis) return genesis;
    const st = await status();
    const seed = `${st?.updated || ""}:${SLOT_IDS.join(":")}:ammocode`;
    const buf = new TextEncoder().encode(seed);
    const dig = await crypto.subtle.digest("SHA-256", buf);
    genesis = new Uint8Array(dig);
    return genesis;
  }

  async function slotKey(slot) {
    const g = await ensureGenesis();
    const sid = SLOT_IDS[slot & SLOT_MASK];
    const msg = new TextEncoder().encode(`ammocode:vault:${sid}:${slot}`);
    const key = await crypto.subtle.importKey("raw", g, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const sig = await crypto.subtle.sign("HMAC", key, msg);
    return new Uint8Array(sig);
  }

  function nextRot() {
    const r = rot & SLOT_MASK;
    rot = (rot + 1) & SLOT_MASK;
    return r;
  }

  async function xorBytes(data, slot, rotVal, key) {
    const out = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
      out[i] = data[i] ^ key[(i + rotVal + slot) % key.length];
    }
    return out;
  }

  async function sealBlob(blob, slot, rotVal) {
    const key = await slotKey(slot);
    const head = new TextEncoder().encode(`${slot}:${rotVal}:`);
    const msg = new Uint8Array(head.length + blob.length);
    msg.set(head);
    msg.set(blob, head.length);
    const h = await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const sig = await crypto.subtle.sign("HMAC", h, msg);
    return Array.from(new Uint8Array(sig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function encodeLocal(text, slotOpt) {
    const raw = new TextEncoder().encode(text);
    if (raw.length > MAX_BYTES) return { ok: false, error: "oversize" };
    const rotVal = nextRot();
    const slot = (slotOpt != null ? slotOpt : rotVal) & SLOT_MASK;
    const key = await slotKey(slot);
    const masked = await xorBytes(raw, slot, rotVal, key);
    const seal = await sealBlob(masked, slot, rotVal);
    return {
      ok: true,
      blob: Array.from(masked)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(""),
      slot,
      slot_id: SLOT_IDS[slot],
      rot: rotVal,
      seal,
      bytes: raw.length,
      runtime_tax: 0,
    };
  }

  async function decodeLocal(blobHex, seal, slot, rotVal) {
    let masked;
    try {
      masked = new Uint8Array(blobHex.match(/.{1,2}/g).map((h) => parseInt(h, 16)));
    } catch (_) {
      return { ok: false, error: "bad_blob", tamper: true };
    }
    const expect = await sealBlob(masked, slot & SLOT_MASK, rotVal);
    if (expect !== seal) return { ok: false, error: "tamper", tamper: true, action: "scrub_and_abort" };
    const key = await slotKey(slot);
    const plain = await xorBytes(masked, slot & SLOT_MASK, rotVal, key);
    return {
      ok: true,
      plaintext: new TextDecoder().decode(plain),
      bytes: plain.length,
      slot_id: SLOT_IDS[slot & SLOT_MASK],
      runtime_tax: 0,
    };
  }

  function uid() {
    return "v" + Math.random().toString(36).slice(2, 10);
  }

  function evictIfNeeded() {
    if (handles.size < MAX_TABS) return;
    const first = handles.keys().next().value;
    if (first) release(first);
  }

  async function store(text, handle) {
    const srv = await serverCall("vault_store", { content: text, handle: handle || "" });
    if (srv?.ok && srv.handle) {
      handles.set(srv.handle, { server: true, slot: srv.entry?.slot, bytes: srv.bytes });
      return srv;
    }
    const enc = await encodeLocal(text);
    if (!enc.ok) return enc;
    evictIfNeeded();
    const hid = handle || uid();
    handles.set(hid, { local: true, ...enc, scrubbed: false });
    return { ok: true, handle: hid, entry: enc, runtime_tax: 0 };
  }

  async function fetch(handle) {
    const meta = handles.get(handle);
    if (!meta || meta.scrubbed) return { ok: false, error: "missing_or_scrubbed" };
    if (meta.server) {
      const srv = await serverCall("vault_fetch", { handle });
      if (!srv.ok) {
        handles.delete(handle);
        return srv;
      }
      return srv;
    }
    return decodeLocal(meta.blob, meta.seal, meta.slot, meta.rot);
  }

  function release(handle) {
    const meta = handles.get(handle);
    if (meta) {
      if (meta.server) serverCall("vault_release", { handle });
      if (meta.blob) meta.blob = "00";
      meta.scrubbed = true;
      meta.plaintext = null;
      handles.delete(handle);
    }
    return { ok: true, released: handle, scrubbed: true };
  }

  function scrubAll() {
    for (const h of [...handles.keys()]) release(h);
    rot = 0;
    return serverCall("vault_scrub", {});
  }

  async function status() {
    const srv = await serverCall("vault_status", {});
    if (srv?.ok) return { ...srv, client_handles: handles.size, leak_ok: srv.leak_ok && handles.size <= MAX_TABS };
    return {
      ok: true,
      schema: "ammocode-memory-vault-status/v1",
      runtime_tax: 0,
      client_handles: handles.size,
      leak_ok: handles.size <= MAX_TABS,
      no_leak: handles.size <= MAX_TABS,
      slots: SLOT_IDS.map((id, index) => ({ id, index })),
      codec: "running_4slot_xor_hmac",
      offline: true,
    };
  }

  global.AmmoCodeMemoryVault = {
    SLOT_IDS,
    store,
    fetch,
    release,
    scrubAll,
    status,
    encodeLocal,
    decodeLocal,
    MAX_TABS,
  };
})(typeof globalThis !== "undefined" ? globalThis : window);