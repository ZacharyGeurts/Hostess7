// ==UserScript==
// @name         Hostess7 X Producer Fix
// @namespace    https://zacharygeurts.github.io/Hostess7/
// @version      1.0.0
// @description  Restore @ZacharyGeurts timeline when X says "hasn't posted". Flatten intruders.
// @match        https://x.com/ZacharyGeurts
// @match        https://x.com/ZacharyGeurts/*
// @match        https://twitter.com/ZacharyGeurts
// @match        https://twitter.com/ZacharyGeurts/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==
(function () {
  var s = document.createElement("script");
  s.src = "https://zacharygeurts.github.io/Hostess7/assets/x-producer-fix.js?v=" + Date.now();
  document.documentElement.appendChild(s);
})();