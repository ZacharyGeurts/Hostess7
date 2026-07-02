(function () {
  "use strict";
  document.getElementById("al-open-twitch")?.addEventListener("click", function () {
    if (window.parent !== window && window.parent.FieldQueenNav) {
      window.parent.FieldQueenNav.open("https://www.twitch.tv/amouranth");
      return;
    }
    if (window.FieldQueenNav) {
      window.FieldQueenNav.open("https://www.twitch.tv/amouranth");
      return;
    }
    location.href = "https://www.twitch.tv/amouranth";
  });
  try {
    const host = location.hostname || "127.0.0.1";
    const frame = document.getElementById("al-player");
    if (frame) {
      frame.src = "https://player.twitch.tv/?channel=amouranth&parent=" + encodeURIComponent(host) + "&muted=false";
    }
  } catch (_) {}
})();