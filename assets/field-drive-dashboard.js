/**
 * Field Drive Dashboard — whole GUI interfaces with all mounted field drives.
 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function $(id) {
    return document.getElementById(id);
  }

  async function api(path, opts) {
    const res = await fetch(path, opts);
    return res.json();
  }

  function renderDriveHero(fd) {
    const title = $("outside-hero-title");
    const motto = $("outside-motto");
    if (title && fd.gui_on_drive) {
      title.innerHTML = '<span class="outside-hero-run">GUI ON DRIVE</span> Outside + Field Drives';
    }
    if (motto && fd.panel_url) {
      motto.textContent =
        (fd.whole_system === "gui" ? "Whole system = GUI on field drive. " : "") +
        "Talk outward through NEXUS firewall · switch drives for Library and corpora.";
    }
  }

  function renderDriveStrip(fd) {
    const el = $("outside-field-drives");
    if (!el) return;
    const drives = fd.drives || [];
    if (!drives.length) {
      el.innerHTML = '<div class="empty">No field drives discovered — plug TEAM NVMe or set HOSTESS7_TEAM_FIELD.</div>';
      return;
    }
    el.innerHTML = `
      <table class="outside-table">
        <thead><tr><th>Drive</th><th>Brain</th><th>GUI</th><th>H7</th><th></th></tr></thead>
        <tbody>${drives.map((d) => `
          <tr class="${d.selected ? "outside-row-selected" : ""}">
            <td><code>${esc(d.label)}</code><div class="meta">${esc(d.path.split("/").slice(-3).join("/"))}</div></td>
            <td>${d.has_brain ? "yes" : "—"}</td>
            <td>${d.has_gui_on_drive ? "on drive" : "host"}</td>
            <td>${esc(d.textbooks_h7 || 0)}</td>
            <td><button type="button" class="outside-btn outside-btn-drive" data-drive-path="${esc(d.path)}">${d.selected ? "Active" : "Use"}</button></td>
          </tr>`).join("")}
        </tbody>
      </table>
      <div class="outside-toolbar">
        <button type="button" id="outside-publish-gui" class="outside-btn outside-btn--primary">Publish GUI → active drive</button>
        <a class="outside-link" href="/field" id="outside-open-gui">Open full GUI →</a>
      </div>`;

    el.querySelectorAll("[data-drive-path]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const path = btn.getAttribute("data-drive-path");
        if (!path || btn.textContent === "Active") return;
        try {
          await api("/api/field-drive/talk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ op: "select_drive", path }),
          });
          const fresh = await api("/api/field-drive");
          renderFieldDrive(fresh);
          if (global.renderOutsideTalk && global.lastOutsideDoc) {
            global.renderOutsideTalk(global.lastOutsideDoc);
          }
        } catch (e) {
          console.warn("select drive", e);
        }
      });
    });

    $("outside-publish-gui")?.addEventListener("click", async () => {
      try {
        const j = await api("/api/field-drive/talk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ op: "publish", full: true }),
        });
        const term = $("outside-terminal");
        if (term) {
          term.insertAdjacentHTML("beforeend", `<div class="outside-line outside-line--ok">GUI published: ${esc(j.gui?.gui_files || "—")} files</div>`);
        }
        const fresh = await api("/api/field-drive");
        renderFieldDrive(fresh);
      } catch (e) {
        console.warn("publish gui", e);
      }
    });
  }

  function renderFieldDrive(fd) {
    if (!fd) return;
    renderDriveHero(fd);
    renderDriveStrip(fd);
  }

  global.renderFieldDrive = renderFieldDrive;
})(typeof window !== "undefined" ? window : globalThis);