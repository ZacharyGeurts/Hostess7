/**
 * Queen Page Agent — injected into tab surfaces.
 * Right-click block · ad-space fingerprints · element picker · structural selectors.
 */
(function () {
  "use strict";

  if (window.__QUEEN_PAGE_AGENT__) return;
  window.__QUEEN_PAGE_AGENT__ = true;

  const API = "/api/queen-page-shields";
  const RANDOM_RE = /^[a-z]{0,3}[0-9a-f]{5,}$|^[0-9a-f]{8,}$|^[a-z]{1,2}[0-9]{4,}$/i;
  const AD_HOST_RE =
    /doubleclick|googlesyndication|googleadservices|adservice\.google|taboola|outbrain|adnxs|amazon-adsystem|moatads|criteo|pubmatic|rubiconproject|openx\.net|media\.net/i;
  const AD_CLASS_RE =
    /(^|[^a-z])(ads?|advert|sponsor|promo|banner|taboola|outbrain|adsbygoogle|ad-slot|ad-container|ad-wrapper|commercial)([^a-z]|$)/i;

  const state = {
    rules: [],
    adHosts: [],
    picker: false,
    hoverEl: null,
    menu: null,
    styleEl: null,
    host: location.hostname.toLowerCase(),
    pageUrl: location.href,
  };

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function isRandomToken(tok) {
    return !tok || RANDOM_RE.test(tok) || /^[a-z]{2,4}-[a-z0-9]{6,}$/i.test(tok);
  }

  function stableClasses(el) {
    return [...(el.classList || [])].filter((c) => !isRandomToken(c)).slice(0, 6);
  }

  function cssPath(el) {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.documentElement && parts.length < 10) {
      const tag = node.tagName.toLowerCase();
      let bit = tag;
      if (node.id && !isRandomToken(node.id)) bit += `#${CSS.escape(node.id)}`;
      else {
        const sc = stableClasses(node).slice(0, 2);
        if (sc.length) bit += sc.map((c) => `.${CSS.escape(c)}`).join("");
      }
      const parent = node.parentElement;
      if (parent) {
        const idx = [...parent.children].indexOf(node) + 1;
        bit += `:nth-child(${idx})`;
      }
      parts.unshift(bit);
      node = parent;
    }
    return parts.join(" > ");
  }

  function adSignals(el) {
    const sig = [];
    const blob = `${el.id || ""} ${[...(el.classList || [])].join(" ")} ${el.getAttribute("role") || ""} ${
      el.getAttribute("aria-label") || ""
    }`.toLowerCase();
    if (AD_CLASS_RE.test(blob)) sig.push("class_id");
    if (el.tagName === "IFRAME") {
      const src = el.getAttribute("src") || "";
      if (AD_HOST_RE.test(src)) sig.push("iframe_ad_host");
    }
    const rect = el.getBoundingClientRect();
    const sizes = [
      [300, 250],
      [728, 90],
      [160, 600],
      [320, 50],
      [970, 250],
      [336, 280],
    ];
    for (const [w, h] of sizes) {
      if (Math.abs(rect.width - w) < 18 && Math.abs(rect.height - h) < 18) sig.push(`size_${w}x${h}`);
    }
    if (el.querySelector?.("iframe[src*='doubleclick'], iframe[src*='googlesyndication']")) {
      sig.push("nested_ad_iframe");
    }
    return sig;
  }

  function isAdLike(el) {
    if (!el || el.nodeType !== 1) return false;
    return adSignals(el).length > 0;
  }

  function findAdContainer(el) {
    let node = el;
    let best = el;
    let score = adSignals(el).length;
    for (let i = 0; i < 6 && node; i++) {
      const s = adSignals(node).length;
      if (s > score) {
        score = s;
        best = node;
      }
      if (node.getAttribute?.("data-ad") || node.getAttribute?.("data-ad-slot")) return node;
      node = node.parentElement;
    }
    return best;
  }

  function fingerprint(el) {
    const rect = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || "",
      stable_classes: stableClasses(el),
      structural_path: cssPath(el),
      width_bucket: Math.round(rect.width / 10) * 10,
      height_bucket: Math.round(rect.height / 10) * 10,
      role: el.getAttribute("role") || "",
      ad_signals: adSignals(el),
      text_sample: (el.innerText || "").trim().slice(0, 80),
    };
  }

  function selectorFor(el) {
    if (el.id && !isRandomToken(el.id)) return `#${CSS.escape(el.id)}`;
    const sc = stableClasses(el);
    if (sc.length) return `${el.tagName.toLowerCase()}${sc.map((c) => `.${CSS.escape(c)}`).join("")}`;
    return cssPath(el);
  }

  async function shieldsApi(body) {
    try {
      const r = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return await r.json();
    } catch (e) {
      return { ok: false, error: String(e.message || e) };
    }
  }

  function applyCss(css) {
    if (!css) return;
    if (!state.styleEl) {
      state.styleEl = document.createElement("style");
      state.styleEl.id = "queen-page-shields-css";
      document.documentElement.appendChild(state.styleEl);
    }
    state.styleEl.textContent = css;
  }

  function hideElement(el) {
    if (!el) return;
    el.setAttribute("data-queen-shielded", "1");
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("visibility", "hidden", "important");
    el.style.setProperty("height", "0", "important");
    el.style.setProperty("overflow", "hidden", "important");
    el.style.setProperty("pointer-events", "none", "important");
  }

  function applyRulesLocal() {
    for (const rule of state.rules) {
      const sel = rule.selector || rule.fingerprint?.structural_path;
      if (!sel) continue;
      try {
        document.querySelectorAll(sel).forEach(hideElement);
      } catch (_) {
        /* invalid selector */
      }
    }
    document.querySelectorAll("iframe").forEach((frame) => {
      const src = frame.getAttribute("src") || "";
      if (AD_HOST_RE.test(src) || state.adHosts.some((h) => src.includes(h))) hideElement(frame);
    });
    scanRandomAdSlots();
  }

  function isXHost() {
    const h = state.host || "";
    return h === "x.com" || h.endsWith(".x.com") || h === "twitter.com" || h.endsWith(".twitter.com");
  }

  function isXJetfuelSurface(el) {
    if (!el || el.nodeType !== 1) return false;
    return !!el.closest?.(
      '[data-testid="mask"], [role="dialog"][aria-modal="true"], .jetfuel-style-root, .jf-element',
    );
  }

  function xJetfuelSsoLooksEmpty(dialog) {
    if (!dialog) return false;
    const root = dialog.querySelector(".jetfuel-style-root, .jf-element");
    if (!root) return false;
    const interactive = dialog.querySelector(
      "button, iframe, input, textarea, select, form, a[href], [data-testid]",
    );
    if (interactive) return false;
    const text = (root.innerText || "").replace(/\s+/g, "").trim();
    return text.length < 8;
  }

  function isXLoginSurface() {
    const path = (location.pathname || "").toLowerCase();
    return (
      /\/onboarding\/web\/sso/i.test(path) ||
      /\/i\/jf\/onboarding/i.test(path) ||
      /\/i\/onboarding/i.test(path) ||
      /\/i\/flow\/login/i.test(path) ||
      (/onboarding/i.test(path) && /mode=sso|provider=google/i.test(location.search))
    );
  }

  function xLoginFormVisible() {
    const body = document.body?.innerText || "";
    return /continue with (google|apple|phone)|email or username|sign up/i.test(body);
  }

  function killXLoginOverlay(el) {
    if (!el?.parentNode) return;
    el.setAttribute("data-x-overlay-killed", "1");
    el.style.setProperty("display", "none", "important");
    el.style.setProperty("pointer-events", "none", "important");
    el.style.setProperty("opacity", "0", "important");
    try { el.remove(); } catch (_) {}
  }

  function repairXJetfuelSsoModal() {
    if (!isXHost() || !isXLoginSurface()) return false;
    let killed = 0;
    document.querySelectorAll('[data-testid="mask"]').forEach((m) => {
      killXLoginOverlay(m);
      killed++;
    });
    document.querySelectorAll('[role="dialog"][aria-modal="true"]').forEach((dlg) => {
      const hasLogin = dlg.querySelector("button, input, iframe, form, a[href]");
      const empty = (dlg.innerText || "").replace(/\s+/g, "").length < 12 && !hasLogin;
      const jetfuel = dlg.querySelector(".jetfuel-style-root, .jf-element");
      if (empty || (jetfuel && !hasLogin) || (xLoginFormVisible() && !dlg.querySelector("button"))) {
        killXLoginOverlay(dlg);
        killed++;
      }
    });
    const vw = window.innerWidth || 800;
    const vh = window.innerHeight || 600;
    document.querySelectorAll("div").forEach((el) => {
      if (el.getAttribute("data-x-overlay-killed")) return;
      const st = getComputedStyle(el);
      if (st.position !== "fixed" && st.position !== "absolute") return;
      const r = el.getBoundingClientRect();
      if (r.width < vw * 0.35 || r.height < vh * 0.35) return;
      const dark = /rgba?\(\s*0\s*,\s*0\s*,\s*0|rgb\(\s*0\s*,\s*0\s*,\s*0/i.test(st.backgroundColor || "");
      const noInteract = !el.querySelector("button, input, iframe, a[href], form");
      if (dark && noInteract && (el.classList.contains("jf-element") || el.querySelector(".jf-element"))) {
        killXLoginOverlay(el);
        killed++;
      }
    });
    if (killed > 0) {
      document.documentElement.setAttribute("data-x-login-killed", "1");
      document.body?.style.setProperty("overflow", "auto", "important");
      document.body?.style.setProperty("pointer-events", "auto", "important");
      notifyParent({ type: "queen:x-login", action: "overlay_killed", count: killed });
    }
    document.querySelectorAll('iframe[src*="accounts.google"], iframe[src*="googleapis"]').forEach((f) => {
      f.style.setProperty("display", "block", "important");
      f.style.setProperty("visibility", "visible", "important");
      f.style.setProperty("pointer-events", "auto", "important");
    });
    if (xLoginFormVisible()) return killed > 0;
    const broken = /\/onboarding\/web\/sso|\/i\/jf\/onboarding\/web\/sso/i.test(location.pathname);
    if (broken && !sessionStorage.getItem("queen:x-login-fallback")) {
      sessionStorage.setItem("queen:x-login-fallback", "1");
      location.replace("/i/flow/login");
      return true;
    }
    return killed > 0;
  }

  function scanRandomAdSlots() {
    document.querySelectorAll("div, aside, section, ins").forEach((el) => {
      if (el.getAttribute("data-queen-shielded")) return;
      if (isXHost() && isXJetfuelSurface(el)) return;
      const rect = el.getBoundingClientRect();
      if (rect.width < 40 || rect.height < 40) return;
      const classes = [...el.classList];
      const randomOnly =
        classes.length > 0 && classes.every((c) => isRandomToken(c)) && !el.id && !el.getAttribute("role");
      const hasAdIframe = el.querySelector?.("iframe[src*='doubleclick'], iframe[src*='googlesyndication']");
      if ((randomOnly && hasAdIframe) || (randomOnly && adSignals(el).includes("nested_ad_iframe"))) {
        hideElement(el);
      }
    });
  }

  async function loadShields() {
    const out = await shieldsApi({ action: "match", url: state.pageUrl, host: state.host });
    if (!out.ok) return out;
    state.rules = out.rules || [];
    state.adHosts = out.ad_hosts || [];
    applyCss(out.css);
    applyRulesLocal();
    notifyParent({ type: "queen:shields", action: "loaded", count: state.rules.length });
    return out;
  }

  function notifyParent(msg) {
    try {
      window.parent?.postMessage?.({ ...msg, source: "queen-page-agent", host: state.host, url: state.pageUrl }, "*");
    } catch (_) {}
  }

  function closeMenu() {
    if (state.menu) {
      state.menu.remove();
      state.menu = null;
    }
  }

  function menuItem(label, action, extra) {
    return `<button type="button" class="qpa-menu-item" data-action="${esc(action)}" ${
      extra || ""
    }>${esc(label)}</button>`;
  }

  function showMenu(x, y, el) {
    closeMenu();
    const ad = isAdLike(el);
    const adContainer = findAdContainer(el);
    const fp = fingerprint(el);
    const adFp = fingerprint(adContainer);
    state.menu = document.createElement("div");
    state.menu.className = "qpa-context-menu";
    state.menu.innerHTML = [
      `<div class="qpa-menu-head">${esc(el.tagName.toLowerCase())}${ad ? " · ad signal" : ""}</div>`,
      menuItem("Inspect element", "inspect"),
      menuItem("Copy selector", "copy_selector"),
      menuItem("Remove this section", "remove_once"),
      menuItem("Never see this again", "never_again"),
      ad
        ? menuItem("Never see ad space here again", "never_ad", 'data-ad="1"')
        : menuItem("Block as ad space (fingerprint)", "never_ad", ""),
      menuItem("Block similar on this site", "block_site"),
      menuItem("Pull out parent section", "pull_parent"),
    ].join("");
    state.menu.style.left = `${Math.min(x, window.innerWidth - 240)}px`;
    state.menu.style.top = `${Math.min(y, window.innerHeight - 280)}px`;
    state.menu.dataset.selector = selectorFor(el);
    state.menu._target = el;
    state.menu._fp = fp;
    state.menu._adFp = adFp;
    state.menu._adTarget = adContainer;
    document.documentElement.appendChild(state.menu);
    state.menu.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        await runMenuAction(btn.dataset.action, el, adContainer);
        closeMenu();
      });
    });
  }

  async function runMenuAction(action, el, adContainer) {
    const target = action === "never_ad" || action === "pull_parent" ? adContainer : el;
    const fp = fingerprint(target);
    const sel = selectorFor(target);
    if (action === "inspect") {
      notifyParent({
        type: "queen:inspector",
        action: "select",
        selector: sel,
        fingerprint: fp,
        html: target.outerHTML?.slice(0, 4000),
        rect: (() => {
          const r = target.getBoundingClientRect();
          return { x: r.x, y: r.y, width: r.width, height: r.height };
        })(),
      });
      highlight(target);
      return;
    }
    if (action === "copy_selector") {
      try {
        await navigator.clipboard.writeText(sel);
      } catch (_) {
        /* clipboard blocked */
      }
      notifyParent({ type: "queen:inspector", action: "copied", selector: sel });
      return;
    }
    if (action === "remove_once") {
      hideElement(target);
      notifyParent({ type: "queen:shields", action: "removed_once", selector: sel });
      return;
    }
    if (action === "never_again") {
      hideElement(target);
      const out = await shieldsApi({
        action: "block",
        url: state.pageUrl,
        host: state.host,
        selector: sel,
        fingerprint: fp,
        label: `Blocked ${fp.tag} on ${state.host}`,
      });
      if (out.ok) await loadShields();
      notifyParent({ type: "queen:shields", action: "blocked", rule: out.rule, selector: sel });
      return;
    }
    if (action === "never_ad") {
      hideElement(adContainer);
      const kids = adContainer.querySelectorAll?.("iframe, ins, [data-ad], [data-ad-slot]") || [];
      kids.forEach(hideElement);
      const out = await shieldsApi({
        action: "block_ad_space",
        url: state.pageUrl,
        host: state.host,
        selector: selectorFor(adContainer),
        fingerprint: fingerprint(adContainer),
        label: `Ad space on ${state.host}`,
        ad_space: true,
      });
      if (out.ok) await loadShields();
      notifyParent({ type: "queen:shields", action: "ad_blocked", rule: out.rule });
      return;
    }
    if (action === "block_site") {
      hideElement(target);
      await shieldsApi({
        action: "block",
        url: state.pageUrl,
        host: state.host,
        selector: sel,
        fingerprint: fp,
        scope: "site",
        label: `Site block ${sel}`,
      });
      await loadShields();
      return;
    }
    if (action === "pull_parent") {
      let parent = target.parentElement;
      while (parent && parent !== document.body) {
        const r = parent.getBoundingClientRect();
        if (r.width > 80 && r.height > 80) {
          hideElement(parent);
          await shieldsApi({
            action: "block",
            url: state.pageUrl,
            host: state.host,
            selector: selectorFor(parent),
            fingerprint: fingerprint(parent),
            label: `Pulled section on ${state.host}`,
          });
          await loadShields();
          notifyParent({ type: "queen:shields", action: "pulled_section" });
          return;
        }
        parent = parent.parentElement;
      }
    }
  }

  function highlight(el) {
    document.querySelectorAll(".qpa-highlight").forEach((n) => n.classList.remove("qpa-highlight"));
    if (el) el.classList.add("qpa-highlight");
  }

  function injectStyles() {
    if (document.getElementById("qpa-agent-style")) return;
    const st = document.createElement("style");
    st.id = "qpa-agent-style";
    st.textContent = `
      .qpa-context-menu{position:fixed;z-index:2147483646;min-width:220px;max-width:280px;
        background:#0a120e;border:1px solid rgba(34,197,94,.45);border-radius:8px;
        box-shadow:0 8px 28px rgba(0,0,0,.55);font:12px/1.35 system-ui,sans-serif;color:#e8f2ea;padding:4px 0;}
      .qpa-menu-head{padding:6px 10px;font-size:10px;color:#6b9a7a;border-bottom:1px solid rgba(255,255,255,.06);}
      .qpa-menu-item{display:block;width:100%;text-align:left;padding:7px 10px;border:0;background:transparent;
        color:#e8f2ea;cursor:pointer;font:inherit;}
      .qpa-menu-item:hover,.qpa-menu-item[data-ad="1"]{background:rgba(244,114,182,.12);color:#f472b6;}
      .qpa-menu-item[data-ad="1"]{font-weight:600;}
      .qpa-highlight{outline:2px solid #f472b6!important;outline-offset:2px!important;}
      .qpa-picker *{cursor:crosshair!important;}
      .qpa-picker .qpa-hover{outline:2px dashed #22c55e!important;outline-offset:1px!important;}
      html[data-x-login-killed="1"] [data-testid="mask"],
      html[data-x-login-killed="1"] [role="dialog"][aria-modal="true"]:not(:has(button,input,iframe)),
      html[data-x-login-killed="1"] [data-x-overlay-killed="1"],
      html[data-x-login-killed="1"] .jetfuel-style-root:empty {
        display:none!important;pointer-events:none!important;opacity:0!important;visibility:hidden!important;
      }
      html[data-x-login-killed="1"] body{overflow:auto!important;pointer-events:auto!important;}
      iframe[src*="accounts.google"],iframe[src*="googleapis"]{display:block!important;visibility:visible!important;pointer-events:auto!important;}
    `;
    document.documentElement.appendChild(st);
  }

  function setPicker(on) {
    state.picker = !!on;
    document.documentElement.classList.toggle("qpa-picker", state.picker);
    notifyParent({ type: "queen:inspector", action: "picker", enabled: state.picker });
  }

  function onMessage(ev) {
    const d = ev.data || {};
    if (d.type !== "queen:page-agent") return;
    if (d.action === "picker") setPicker(d.enabled);
    if (d.action === "reload_shields") loadShields();
    if (d.action === "highlight" && d.selector) {
      try {
        highlight(document.querySelector(d.selector));
      } catch (_) {}
    }
  }

  function bind() {
    injectStyles();
    document.addEventListener(
      "contextmenu",
      (e) => {
        if (state.picker) {
          e.preventDefault();
          return;
        }
        const t = e.target;
        if (!t || t.closest?.(".qpa-context-menu")) return;
        if (t.closest?.("#queen-page-inspector-root")) return;
        e.preventDefault();
        showMenu(e.clientX, e.clientY, t);
      },
      true,
    );
    document.addEventListener("click", () => closeMenu(), true);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeMenu();
        setPicker(false);
      }
    });
    document.addEventListener("mousemove", (e) => {
      if (!state.picker) return;
      const el = document.elementFromPoint(e.clientX, e.clientY);
      if (state.hoverEl && state.hoverEl !== el) state.hoverEl.classList.remove("qpa-hover");
      state.hoverEl = el;
      if (el) el.classList.add("qpa-hover");
    });
    document.addEventListener(
      "click",
      (e) => {
        if (!state.picker) return;
        e.preventDefault();
        e.stopPropagation();
        const el = document.elementFromPoint(e.clientX, e.clientY);
        if (!el) return;
        setPicker(false);
        highlight(el);
        notifyParent({
          type: "queen:inspector",
          action: "select",
          selector: selectorFor(el),
          fingerprint: fingerprint(el),
          html: el.outerHTML?.slice(0, 4000),
        });
        runMenuAction("inspect", el, findAdContainer(el));
      },
      true,
    );
    window.addEventListener("message", onMessage);
    const obs = new MutationObserver(() => {
      applyRulesLocal();
      if (isXHost()) repairXJetfuelSsoModal();
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
    loadShields();
    if (isXHost()) {
      repairXJetfuelSsoModal();
      window.setInterval(repairXJetfuelSsoModal, 1200);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();