(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;

  function initStudies(root) {
    var scope = root && typeof root.querySelectorAll === "function" ? root : document;
    var input = scope.querySelector("[data-study-search]");
    var items = Array.prototype.slice.call(scope.querySelectorAll("[data-study-item]"));
    var count = scope.querySelector("[data-study-count]");
    var empty = scope.querySelector("[data-study-empty]");
    if (!input || !items.length || input.dataset.studyReady === "true") return;

    input.dataset.studyReady = "true";
    var initialQuery = new URL(window.location.href).searchParams.get("q") || "";
    input.value = initialQuery;

    function isActiveView() {
      var view = input.closest && input.closest("[data-member-view]");
      return !view || !view.hidden;
    }

    function normalize(value) {
      return String(value || "").toLocaleLowerCase("pt-BR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }

    function render() {
      if (!isActiveView()) return;
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
      if (site.body.dataset.page === "member") {
        url.pathname = "/area/";
        url.searchParams.set("view", "library");
      }
      if (input.value.trim()) url.searchParams.set("q", input.value.trim());
      else url.searchParams.delete("q");
      window.history.replaceState({}, document.title, url.pathname + (url.search ? "?" + url.searchParams.toString() : "") + url.hash);
    }

    input.addEventListener("input", render);
    window.addEventListener("popstate", function () {
      if (!isActiveView()) return;
      input.value = new URL(window.location.href).searchParams.get("q") || "";
      render();
    });
    render();
  }

  site.initStudies = initStudies;
  if (site.body.dataset.page === "studies") initStudies(document);
})(window);
