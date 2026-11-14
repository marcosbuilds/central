(function () {
  "use strict";

  var site = window.PeaceSite;
  var list = document.querySelector("[data-notices-list]");
  var source = document.querySelector("[data-notices-source]");
  if (!site || !list) return;

  function setText(node, value) { if (node) node.textContent = value; }

  function setStatus(value) {
    document.querySelectorAll("[data-notices-status]").forEach(function (node) {
      setText(node, value);
    });
  }

  function formatDate(value) {
    try {
      return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
    } catch (error) {
      return value || "Data não informada";
    }
  }

  function render(items, sourceState) {
    list.textContent = "";
    if (!items.length) {
      var empty = document.createElement("p");
      empty.className = "notice-live-empty";
      empty.textContent = sourceState === "unavailable"
        ? "A fonte pública está temporariamente indisponível. Tente novamente em instantes."
        : "Nenhum comunicado público foi publicado no canal configurado.";
      list.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var article = document.createElement("article");
      article.className = "notice-live-item";
      var meta = document.createElement("p");
      meta.className = "eyebrow";
      meta.textContent = formatDate(item.published_at) + " · " + (item.author || "Peace");
      var copy = document.createElement("p");
      copy.textContent = item.text || "Comunicado sem texto.";
      article.appendChild(meta);
      article.appendChild(copy);
      if (item.url) {
        var link = document.createElement("a");
        link.className = "text-link";
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Abrir origem ↗";
        article.appendChild(link);
      }
      list.appendChild(article);
    });
  }

  site.attemptEndpoint("/api/notices", { headers: { Accept: "application/json" } }, 12000)
    .then(function (response) { return response.json(); })
    .then(function (payload) {
      var items = Array.isArray(payload.notices) ? payload.notices : [];
      var sourceState = payload.source && payload.source.state;
      render(items, sourceState);
      setStatus(items.length
        ? "Comunicados públicos da Peace."
        : sourceState === "unavailable"
          ? "Fonte pública indisponível."
          : "Sem comunicados para exibir.");
      setText(source, sourceState === "unavailable" ? "Fonte pública não disponível" : "Fonte pública conectada");
    })
    .catch(function (error) {
      render([], "unavailable");
      setStatus("Fonte pública indisponível. Tente novamente em instantes.");
      setText(source, "Fonte pública indisponível");
    });
})();
