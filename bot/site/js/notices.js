(function () {
  "use strict";

  var site = window.PeaceSite;
  var list = document.querySelector("[data-notices-list]");
  var status = document.querySelector("[data-notices-status]");
  var source = document.querySelector("[data-notices-source]");
  if (!site || !list) return;

  function setText(node, value) { if (node) node.textContent = value; }

  function formatDate(value) {
    try {
      return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
    } catch (error) {
      return value || "Data não informada";
    }
  }

  function render(items) {
    list.textContent = "";
    if (!items.length) {
      var empty = document.createElement("p");
      empty.className = "notice-live-empty";
      empty.textContent = "Nenhum comunicado público foi publicado no canal configurado.";
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
      render(items);
      var sourceState = payload.source && payload.source.state;
      setText(status, items.length ? "Comunicados públicos da Peace." : "Sem comunicados para exibir.");
      setText(source, sourceState === "unavailable" ? "Fonte pública não disponível" : "Fonte pública conectada");
    })
    .catch(function (error) {
      render([]);
      setText(status, error.message || "Não consegui consultar os avisos agora.");
      setText(source, "Fonte pública indisponível");
    });
})();
