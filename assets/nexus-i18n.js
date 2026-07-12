/**
 * NEXUS panel i18n — language dropdown, IP-detected default, remembered preference.
 * Packs live at data/i18n/messages/ (see panel_language.paths in /api/field).
 */
(function (global) {
  "use strict";

  const STORAGE_KEY = "nexus_panel_lang";
  const DEFAULT = "en-US";
  let catalog = null;
  let messages = {};
  let active = { code: DEFAULT, rtl: false, source: "unset", user_set: false };

  function t(key, fallback) {
    if (messages[key] != null) return messages[key];
    if (fallback != null) return fallback;
    return key;
  }

  function applyRtl(rtl) {
    document.documentElement.lang = active.code || DEFAULT;
    document.documentElement.dir = rtl ? "rtl" : "ltr";
    document.documentElement.classList.toggle("nexus-rtl", !!rtl);
  }

  function applyToDom() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const attr = el.getAttribute("data-i18n-attr");
      const val = t(key, el.textContent);
      if (attr) {
        el.setAttribute(attr, val);
      } else if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
        if (el.hasAttribute("placeholder")) el.placeholder = val;
        else el.value = val;
      } else {
        el.textContent = val;
      }
    });
    const sel = document.getElementById("nexus-lang-select");
    if (sel && active.code) sel.value = active.code;
    const hint = document.getElementById("nexus-lang-hint");
    if (hint) {
      const parts = [];
      if (active.user_set) parts.push(t("lang.user_set", "Your choice"));
      else if (active.source === "detected") {
        const geo = [active.city, active.country].filter(Boolean).join(", ");
        parts.push(t("lang.detected", "Detected from your region") + (geo ? ` · ${geo}` : ""));
      }
      if (catalog?.paths?.messages_dir) {
        parts.push(t("lang.path", "Packs: data/i18n/messages/"));
      }
      hint.textContent = parts.join(" · ");
    }
    applyRtl(!!active.rtl);
  }

  function sortLanguages(langs) {
    const list = Array.isArray(langs) ? langs.slice() : [];
    const en = list.filter((x) => x.code === DEFAULT);
    const rest = list.filter((x) => x.code !== DEFAULT).sort((a, b) =>
      String(a.name || a.code).localeCompare(String(b.name || b.code), undefined, { sensitivity: "base" })
    );
    return en.concat(rest);
  }

  function fillDropdown(langs) {
    const sel = document.getElementById("nexus-lang-select");
    if (!sel || sel.options.length > 1) return;
    sortLanguages(langs).forEach((row) => {
      const opt = document.createElement("option");
      opt.value = row.code;
      opt.textContent = row.code === DEFAULT
        ? `${row.name || row.code} ★`
        : `${row.name || row.code} — ${row.native || ""}`.trim();
      sel.appendChild(opt);
    });
  }

  async function saveLanguage(code, remember) {
    const res = await fetch("/api/panel-language", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, remember: remember !== false }),
      cache: "no-store",
    });
    if (!res.ok) throw new Error("save failed");
    return res.json();
  }

  function bindDropdown() {
    const sel = document.getElementById("nexus-lang-select");
    const remember = document.getElementById("nexus-lang-remember");
    if (!sel || sel.dataset.bound) return;
    sel.dataset.bound = "1";
    sel.addEventListener("change", async () => {
      const code = sel.value;
      try {
        const doc = await saveLanguage(code, remember?.checked !== false);
        ingest(doc);
        applyToDom();
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify({ code, user_set: true, remember: true }));
        } catch (_) {}
      } catch (_) {
        sel.value = active.code || DEFAULT;
      }
    });
  }

  function ingest(doc) {
    if (!doc) return;
    if (doc.active) {
      catalog = doc;
      active = { ...doc.active, code: doc.active.code || DEFAULT };
      messages = doc.messages || {};
      if (doc.languages) fillDropdown(doc.languages);
    } else if (doc.code) {
      active = {
        code: doc.code,
        source: doc.source || "user",
        user_set: !!doc.user_set,
        remember: doc.remember !== false,
        rtl: !!doc.rtl,
        country: doc.country || "",
        city: doc.city || "",
        name: doc.name,
        native: doc.native,
      };
      messages = doc.messages || {};
    }
    bindDropdown();
  }

  async function bootstrapFromApi() {
    try {
      const res = await fetch("/api/panel-language", { cache: "no-store" });
      if (res.ok) ingest(await res.json());
    } catch (_) {}
    if (!catalog) {
      try {
        const cached = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
        if (cached?.code && !cached.user_set) {
          active.code = cached.code;
        }
      } catch (_) {}
    }
    applyToDom();
  }

  function mergeFromPanel(data) {
    const pl = data?.panel_language;
    if (!pl) return;
    if (pl.active?.user_set) {
      ingest(pl);
      applyToDom();
      return;
    }
    if (!active.user_set && pl.active?.code) {
      ingest(pl);
      applyToDom();
    } else if (pl.messages) {
      messages = { ...messages, ...pl.messages };
      applyToDom();
    }
  }

  global.NexusI18n = {
    t,
    apply: applyToDom,
    bootstrap: bootstrapFromApi,
    mergeFromPanel,
    active: () => ({ ...active }),
    paths: () => catalog?.paths || {},
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => bootstrapFromApi());
  } else {
    bootstrapFromApi();
  }
})(window);