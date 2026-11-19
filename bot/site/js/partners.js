(function (global) {
  "use strict";
  var site = global.PeaceSite;
  var list = document.querySelector("[data-partners-list]");
  var status = document.querySelector("[data-partners-status]");
  if (!site || !list) return;

  function clear() { list.replaceChildren(); }
  function render(items, unavailable) {
    clear();
    if (!items.length) {
      var empty = document.createElement("div"); empty.className = "partners-empty-state";
      var icon = document.createElement("span"); icon.className = "partners-empty-icon"; icon.textContent = unavailable ? "!" : "—";
      var title = document.createElement("strong"); title.textContent = unavailable ? "Parceiros indisponíveis agora" : "Nenhuma parceria publicada";
      var copy = document.createElement("p"); copy.textContent = unavailable ? "A diretoria não respondeu. Tente novamente em instantes." : "Quando uma organização for publicada pela equipe, ela aparece aqui.";
      empty.append(icon, title, copy); list.appendChild(empty); return;
    }
    items.forEach(function (item) {
      var article = document.createElement("article"); article.className = "partner-feed-item";
      var mark = document.createElement("div"); mark.className = "partner-feed-mark";
      if (item.image_url) { var image = document.createElement("img"); image.src = item.image_url; image.alt = ""; image.loading = "lazy"; mark.appendChild(image); }
      else mark.textContent = String(item.title || "P").slice(0, 1).toUpperCase();
      var body = document.createElement("div"); body.className = "partner-feed-copy";
      var meta = document.createElement("p"); meta.className = "eyebrow"; meta.textContent = "Parceria Peace";
      var title = document.createElement("h2"); title.textContent = item.title || "Organização parceira";
      var description = document.createElement("p"); description.textContent = item.description || item.text || "";
      body.append(meta, title, description);
      if (item.url) { var link = document.createElement("a"); link.className = "text-link"; link.href = item.url; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "Visitar parceria ↗"; body.appendChild(link); }
      article.append(mark, body); list.appendChild(article);
    });
  }
  site.attemptEndpoint("/api/partners", { headers: { Accept: "application/json" } }, 12000)
    .then(function (response) { return response.json(); })
    .then(function (payload) {
      var items = Array.isArray(payload.partners) ? payload.partners : [];
      render(items, payload.source && payload.source.state === "unavailable");
      if (status) status.textContent = items.length ? items.length + (items.length === 1 ? " parceria" : " parcerias") : "Diretório atualizado";
    })
    .catch(function () { render([], true); if (status) status.textContent = "Fonte indisponível"; });
})(window);
