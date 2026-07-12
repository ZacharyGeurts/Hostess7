/**
 * Final Eye · library text polish — running lines for humans, clean copy for AI.
 */
(function (global) {
  "use strict";

  const DEWEY_SHORT = {
    "000": "Computer science & general works",
    "004": "Data processing & computer science",
    "005": "Computer programming",
    "020": "Library & information sciences",
    "133": "Parapsychology & occult",
    "300": "Social sciences",
    "355": "Military science",
    "370": "Education",
    "400": "Language",
    "500": "Science",
    "510": "Mathematics",
    "540": "Chemistry",
    "570": "Biology",
    "600": "Technology",
    "629": "Vehicle engineering",
    "700": "Arts & recreation",
    "800": "Literature",
    "900": "History & geography",
    "910": "Geography",
    "920": "Biography",
  };

  function polish(text) {
    return String(text ?? "")
      .replace(/\s+/g, " ")
      .replace(/\s*—\s*/g, " — ")
      .replace(/\s*–\s*/g, " – ")
      .replace(/[\u201c\u201d]/g, '"')
      .replace(/[\u2018\u2019]/g, "'")
      .replace(/\.{4,}/g, "…")
      .replace(/\s+([,.;:!?])/g, "$1")
      .trim();
  }

  function friendlyShelf(book) {
    if (!book) return "";
    const shelf = String(book.shelf || "").trim();
    const dewey = String(book.dewey || "").trim();
    const deweyLabel = polish(book.dewey_label || "");
    const shelfTitle = polish(book.shelf_title || "");
    const main = dewey.replace(/[^0-9].*/, "").slice(0, 3);
    const short = DEWEY_SHORT[main] || DEWEY_SHORT[dewey.slice(0, 3)] || "";

    if (shelf.includes("/")) {
      let leaf = shelf.split("/").pop().replace(/-/g, " ").replace(/_/g, " ").trim();
      const parent = shelf.split("/")[0];
      if (leaf === "explaining" || leaf === "exploring" || leaf === "card-catalog") leaf = "";
      if (leaf && leaf.length <= 36) return leaf.replace(/\b\w/g, (c) => c.toUpperCase());
      const slugTail = parent.split("-").slice(1).join(" ");
      if (slugTail && slugTail.length <= 36) {
        return slugTail.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      }
    }

    if (short && short.length <= 44) return short;
    if (shelfTitle && shelfTitle.length <= 44) return shelfTitle;
    if (deweyLabel && deweyLabel.length <= 44) return deweyLabel;
    if (shelf) {
      const slugTail = shelf.split("/")[0].split("-").slice(1).join(" ");
      if (slugTail) return slugTail.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
    return short || (dewey ? "Dewey " + dewey : "");
  }

  function humanLine(book) {
    if (!book) return "";
    if (book.human_line) return polish(book.human_line);
    const title = polish(book.title || book.id || "Untitled");
    const author = polish(book.author || "");
    const shelf = friendlyShelf(book);
    const tags = (book.tags || []).slice(0, 4).map((t) => String(t).replace(/-/g, " "));
    const bits = [title];
    if (author && !/hostess\s*7/i.test(author)) bits.push("by " + author);
    if (shelf) bits.push("— " + shelf);
    if (tags.length) bits.push("· " + tags.join(", "));
    return polish(bits.join(" "));
  }

  function aiLine(book) {
    if (!book) return "";
    if (book.ai_line) return polish(book.ai_line);
    return polish(
      "book_id=" +
        (book.id || "") +
        " title=" +
        (book.title || "") +
        " dewey=" +
        (book.dewey || "") +
        " shelf=" +
        (book.shelf || "") +
        " ready=" +
        !!book.ready
    );
  }

  function runningLines(books, limit) {
    const n = limit || 80;
    return (books || [])
      .slice(0, n)
      .map(humanLine)
      .filter(Boolean);
  }

  function mountTicker(host, lines, opts) {
    if (!host || !lines || !lines.length) return;
    opts = opts || {};
    const sep = opts.separator || "   ◆   ";
    const text = lines.map(polish).join(sep) + sep + lines.map(polish).join(sep);
    host.innerHTML =
      '<div class="fle-ticker" role="marquee" aria-live="off">' +
      '<div class="fle-ticker-track">' +
      '<span class="fle-ticker-text">' +
      escapeHtml(text) +
      "</span></div></div>";
    if (global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      host.querySelector(".fle-ticker-track").style.animation = "none";
      host.querySelector(".fle-ticker-text").style.whiteSpace = "normal";
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  global.FieldLibraryEye = {
    polish: polish,
    friendlyShelf: friendlyShelf,
    humanLine: humanLine,
    aiLine: aiLine,
    runningLines: runningLines,
    mountTicker: mountTicker,
  };
})(typeof window !== "undefined" ? window : globalThis);