/** Tab Beacon client hook — marks cards with a live pulse dot on each refresh. */
(function () {
  function hook(viewId, row, out) {
    const card = document.querySelector(
      `.nexus-plugin-card[data-plugin="tab-beacon"][data-view="${viewId}"]`
    );
    if (!card || card.querySelector(".nexus-beacon-pulse")) return;
    const pulse = document.createElement("span");
    pulse.className = "nexus-beacon-pulse";
    pulse.title = "Tab Beacon live";
    const head = card.querySelector(".nexus-plugin-card-head");
    if (head) head.appendChild(pulse);
  }
  function register() {
    if (window.NexusPlugins) window.NexusPlugins.registerClientHook("tab-beacon", hook);
  }
  register();
  document.addEventListener("DOMContentLoaded", register);
})();