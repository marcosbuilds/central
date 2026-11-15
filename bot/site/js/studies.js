(function () {
  "use strict";

  if (!document.body || document.body.dataset.page !== "studies") return;

  var input = document.querySelector("[data-study-search]");
  var items = Array.prototype.slice.call(document.querySelectorAll("[data-study-item]"));
  var count = document.querySelector("[data-study-count]");
  var empty = document.querySelector("[data-study-empty]");
  if (!input || !items.length) return;

  var initialQuery = new URL(window.location.href).searchParams.get("q") || "";
  input.value = initialQuery;

  function normalize(value) {
    return String(value || "").toLocaleLowerCase("pt-BR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function render() {
    var query = normalize(input.value).trim();
    var visible = 0;
    items.forEach(function (item) {
      var matches = !query || normalize(item.dataset.studySearch).indexOf(query) >= 0;
      item.hidden = !matches;
      if (matches) visible += 1;
    });
    if (count) count.textContent = visible + (visible === 1 ? " material" : " materiais");
    if (empty) empty.hidden = visible > 0;
    var url = new URL(window.location.href);
    if (input.value.trim()) url.searchParams.set("q", input.value.trim());
    else url.searchParams.delete("q");
    window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : "") + url.hash);
  }

  input.addEventListener("input", render);
  render();
})();
