/**
 * Queen Browser — telemetry lock. AI ingest only; human telemetry blocked.
 */
(function (global) {
  "use strict";

  const BLOCKED = [
    "google-analytics", "googletagmanager", "doubleclick", "facebook.net",
    "hotjar", "segment.io", "mixpanel", "amplitude", "fullstory", "clarity.ms",
    "mozilla.org/telemetry", "firefox.com/phoenix", "ping-centre", "ads-twitter",
    "telemetry", "metrics", "beacon", "track", "analytics",
  ];

  const AI_PATHS = [
    "/api/queen-telemetry/ai",
    "/api/ai-integration",
    "/api/field-aia-accelerator",
    "/api/hostess7-ai",
  ];

  function isLoopback(host) {
    return host === "127.0.0.1" || host === "localhost" || host === "";
  }

  function isAiIngest(url) {
    try {
      const u = new URL(String(url), global.location?.origin || "http://127.0.0.1:9481");
      if (!isLoopback(u.hostname)) return false;
      return AI_PATHS.some(function (p) { return u.pathname.startsWith(p); });
    } catch {
      return false;
    }
  }

  function isTelemetryUrl(url) {
    const s = String(url || "").toLowerCase();
    if (!s) return false;
    if (isAiIngest(s)) return false;
    return BLOCKED.some(function (b) { return s.includes(b); });
  }

  function blockResponse() {
    return Promise.resolve(
      new Response('{"ok":false,"blocked":"telemetry_human","locked":true}', {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }

  function sealDocument() {
    const root = global.document?.documentElement;
    if (!root) return;
    root.dataset.telemetryPolicy = "ai_only";
    root.dataset.telemetryHuman = "0";
    root.dataset.telemetryLocked = "1";
    if (global.document.body) {
      global.document.body.dataset.telemetry = "ai_only";
    }
  }

  function patchFetch() {
    if (!global.fetch || global.fetch.__queenTelemetryLock) return;
    const orig = global.fetch.bind(global);
    global.fetch = function queenLockedFetch(input, init) {
      const url = typeof input === "string" ? input : input?.url || "";
      if (isTelemetryUrl(url)) return blockResponse();
      return orig(input, init);
    };
    global.fetch.__queenTelemetryLock = true;
  }

  function patchBeacon() {
    if (!global.navigator?.sendBeacon || global.navigator.sendBeacon.__queenTelemetryLock) return;
    const orig = global.navigator.sendBeacon.bind(global.navigator);
    global.navigator.sendBeacon = function queenLockedBeacon(url, data) {
      if (isTelemetryUrl(url) && !isAiIngest(url)) return false;
      return orig(url, data);
    };
    global.navigator.sendBeacon.__queenTelemetryLock = true;
  }

  function patchImage() {
    if (!global.Image || global.Image.__queenTelemetryLock) return;
    const Orig = global.Image;
    function LockedImage(w, h) {
      const img = w !== undefined || h !== undefined ? new Orig(w, h) : new Orig();
      let src = "";
      Object.defineProperty(img, "src", {
        get: function () { return src; },
        set: function (v) {
          if (isTelemetryUrl(v)) return;
          src = String(v || "");
          Orig.prototype.__lookupSetter__("src")?.call(img, src);
        },
        configurable: true,
      });
      return img;
    }
    LockedImage.prototype = Orig.prototype;
    LockedImage.__queenTelemetryLock = true;
    global.Image = LockedImage;
  }

  function aiIngest(event, meta) {
    return global.fetch("/api/queen-telemetry/ai", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-Queen-Telemetry-Audience": "ai",
      },
      body: JSON.stringify({
        audience: "ai",
        surface: "queen-browser",
        event: event || "signal",
        meta: meta || {},
      }),
    }).catch(function () { return null; });
  }

  sealDocument();
  patchFetch();
  patchBeacon();
  patchImage();

  global.QueenTelemetryLock = {
    policy: function () {
      return { human: false, ai: true, locked: true };
    },
    aiIngest: aiIngest,
    isBlocked: isTelemetryUrl,
  };
})(typeof window !== "undefined" ? window : globalThis);