/**
 * Field Host Desktop — six tool wall + fullscreen C2 programs + task manager bullet.
 */
(function () {
  "use strict";

  const state = { data: null, keysEngaged: false };

  function toast(msg) {
    const el = document.getElementById("hd-toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(function () { el.classList.remove("show"); }, 2600);
  }

  function engageKeyboardSovereign() {
    if (state.keysEngaged) return;
    fetch("/api/field-keyboard-sovereign/engage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      credentials: "same-origin",
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok !== false) state.keysEngaged = true;
      })
      .catch(function () {});
  }

  function releaseKeyboardSovereign(reason) {
    if (!state.keysEngaged) return;
    const body = JSON.stringify({ reason: reason || "pagehide" });
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/field-keyboard-sovereign/release", body);
    } else {
      fetch("/api/field-keyboard-sovereign/release", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
        credentials: "same-origin",
        keepalive: true,
      }).catch(function () {});
    }
    state.keysEngaged = false;
  }

  function fillViewport() {
    const root = document.documentElement;
    root.classList.add("nfs-fullscreen-desktop", "nfs-kiosk");
    try {
      if (!document.fullscreenElement && root.requestFullscreen) {
        root.requestFullscreen({ navigationUI: "hide" }).catch(function () {});
      }
    } catch (_) {}
  }

  async function refresh() {
    fillViewport();
    try {
      const res = await fetch("/api/field-host-desktop", { credentials: "same-origin" });
      if (!res.ok) throw new Error("desktop API " + res.status);
      state.data = await res.json();

      const mon = document.getElementById("hd-monitor");
      const policy = state.data?.policy || {};
      const showWall =
        policy.six_tool_wall !== false && policy.six_tool_wall_on_boot !== false;
      if (mon) {
        mon.classList.toggle("hd-monitor--hidden", !showWall);
        mon.innerHTML = "";
      }
      const dash = state.data?.monitor_dashboard || {};
      if (showWall && mon && window.FieldMonitorDashboard) {
        window.FieldMonitorDashboard.mount(mon, {
          ...dash,
          programs: state.data.programs || [],
          icon_dock: state.data.icon_dock || [],
        });
      }

      const sb = document.getElementById("fsb-mount");
      if (sb && window.FieldStartbar) {
        window.FieldStartbar.mount(sb, state.data);
      }

      if (window.FieldDesktopScale) {
        const shell = state.data?.shell?.settings || {};
        const policy = state.data?.policy || {};
        window.FieldDesktopScale.apply({
          ui_scale: shell.ui_scale || policy.desktop_ui_scale_default || 125,
          desktop_icon_size: shell.desktop_icon_size || policy.desktop_icon_size_default || 50,
        });
      }

      if (window.NexusFieldShell) {
        window.NexusFieldShell.mount(state.data);
      }

      const tm = document.getElementById("c2tm-mount");
      if (tm && window.FieldC2TaskManager) {
        window.FieldC2TaskManager.mount(tm);
      }

      engageKeyboardSovereign();
    } catch (e) {
      toast("Load failed: " + e.message);
    }
  }

  window.FieldHostDesktop = {
    refresh: refresh,
    toast: toast,
  };

  window.addEventListener("pagehide", function () {
    releaseKeyboardSovereign("pagehide");
  });
  window.addEventListener("beforeunload", function () {
    releaseKeyboardSovereign("beforeunload");
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", refresh);
  } else {
    refresh();
  }
})();