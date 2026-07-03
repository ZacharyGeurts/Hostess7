/**
 * KILROY Universal Terminal — delegates to Queen GNU Terminal (optimized, side scrollbar).
 * Keeps KilroyUniversalTerminal API for embeds and queen-os.js.
 */
(function (global) {
  "use strict";

  function gnuReady() {
    var g = global.QueenGnuTerminal;
    return g && typeof g.mount === "function" && g.mount !== shimMount;
  }

  function shimMount(host, opts) {
    opts = opts || {};
    if (!host) return Promise.reject(new Error("no host"));
    if (gnuReady()) {
      host.dataset.kutMounted = "1";
      return Promise.resolve(global.QueenGnuTerminal.mount(host, {
        cwd: opts.cwd,
        quiet: false,
        miniview: opts.miniview !== false,
        minibrowser: opts.minibrowser !== false,
        layout: opts.layout || "tabs",
        embedClass: opts.embedClass || "kut-embed qgt-embed",
      })).then(function () {
        if (opts.cwd) return global.QueenGnuTerminal.runCommand("cd " + opts.cwd.replace(/"/g, '\\"'));
      });
    }
    return loadGnu().then(function () {
      return shimMount(host, opts);
    });
  }

  function shimExec(cmd) {
    if (gnuReady()) return global.QueenGnuTerminal.runCommand(cmd);
    return loadGnu().then(function () {
      return global.QueenGnuTerminal.runCommand(cmd);
    });
  }

  function shimClear() {
    if (gnuReady() && global.QueenGnuTerminal.clearTerminal) {
      global.QueenGnuTerminal.clearTerminal();
      return;
    }
    var sess = global.QueenGnuTerminal?.activeSession?.();
    if (sess?.out) sess.out.innerHTML = "";
  }

  var loadPromise = null;

  function loadGnu() {
    if (gnuReady()) return Promise.resolve();
    if (loadPromise) return loadPromise;
    loadPromise = new Promise(function (resolve, reject) {
      function loadOne(href, isCss) {
        return new Promise(function (res, rej) {
          var sel = isCss ? 'link[href*="' + href + '"]' : 'script[src*="' + href + '"]';
          if (document.querySelector(sel)) {
            res();
            return;
          }
          if (isCss) {
            var link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            link.onload = function () {
              res();
            };
            link.onerror = function () {
              rej(new Error(href + " load failed"));
            };
            document.head.appendChild(link);
            return;
          }
          var s = document.createElement("script");
          s.src = href;
          s.defer = true;
          s.onload = function () {
            res();
          };
          s.onerror = function () {
            rej(new Error(href + " load failed"));
          };
          document.body.appendChild(s);
        });
      }
      var base = "queen-gnu-terminal";
      loadOne(base + ".css", true)
        .then(function () {
          return loadOne("kilroy-universal-shell.js", false);
        })
        .then(function () {
          return loadOne(base + ".js", false);
        })
        .then(resolve)
        .catch(reject);
    });
    return loadPromise;
  }

  function shimInit() {
    var host =
      document.getElementById("kut-mount") ||
      document.getElementById("qgt-embed-root") ||
      document.getElementById("qgt-shell");
    if (host && !host.dataset.kutMounted) {
      return shimMount(host);
    }
    if (gnuReady()) return Promise.resolve(global.QueenGnuTerminal);
    return loadGnu();
  }

  global.KilroyUniversalTerminal = {
    mount: shimMount,
    init: shimInit,
    exec: shimExec,
    clear: shimClear,
    state: { mode: "gnu" },
  };
})(typeof window !== "undefined" ? window : globalThis);