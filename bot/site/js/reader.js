(function () {
  "use strict";

  var shell = document.querySelector("[data-reader-shell]");
  if (!shell) return;

  // This is a light copy-deterrent for the visual reader, not a security
  // promise. Visible content can never be protected from screenshots or OCR.
  shell.addEventListener("contextmenu", function (event) { event.preventDefault(); });
  shell.addEventListener("dragstart", function (event) {
    if (event.target && event.target.tagName === "IMG") event.preventDefault();
  });
  shell.addEventListener("selectstart", function (event) {
    if (event.target && event.target.closest && event.target.closest(".reader-page")) event.preventDefault();
  });
})();
