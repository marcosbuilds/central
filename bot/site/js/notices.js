(function () {
  "use strict";

  var site = window.PeaceSite;
  var list = document.querySelector("[data-notices-list]");
  var source = document.querySelector("[data-notices-source]");
  var bell = document.querySelector("[data-notices-bell]");
  var badge = bell && bell.querySelector("[data-notices-badge]");
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

  var seenStorageKey = "peace.notices.seen.v1";

  function noticeKey(item) {
    return String(
      item && (item.id || item.message_id || item.url)
        || (item && item.published_at || "") + "|" + (item && item.text || "")
    ).slice(0, 240);
  }

  function readSeenNoticeKeys() {
    try {
      var raw = window.localStorage.getItem(seenStorageKey);
      var parsed = raw ? JSON.parse(raw) : null;
      return Array.isArray(parsed) ? parsed.filter(function (value) { return typeof value === "string"; }) : null;
    } catch (error) {
      return null;
    }
  }

  function announceNewNotices(items, sourceState) {
    if (sourceState !== "ready" || !items.length) {
      if (bell) bell.setAttribute("aria-label", "Nenhum aviso novo");
      if (badge) badge.hidden = true;
      return;
    }
    var keys = items.map(noticeKey).filter(Boolean);
    var previous = readSeenNoticeKeys();
    var merged = Array.from(new Set((previous || []).concat(keys))).slice(-120);
    try { window.localStorage.setItem(seenStorageKey, JSON.stringify(merged)); } catch (error) { /* optional */ }
    if (!previous || !site.showToast) {
      if (bell) bell.setAttribute("aria-label", "Avisos públicos disponíveis");
      return;
    }
    var fresh = keys.filter(function (key) { return previous.indexOf(key) < 0; });
    if (!fresh.length) {
      if (bell) bell.setAttribute("aria-label", "Nenhum aviso novo");
      if (badge) badge.hidden = true;
      return;
    }
    if (bell) {
      bell.classList.add("is-new");
      bell.setAttribute("aria-label", fresh.length === 1 ? "1 aviso novo" : fresh.length + " avisos novos");
    }
    if (badge) {
      badge.textContent = fresh.length > 9 ? "9+" : String(fresh.length);
      badge.hidden = false;
    }
    var first = items.find(function (item) { return fresh.indexOf(noticeKey(item)) >= 0; });
    var preview = first && first.text ? String(first.text).replace(/\s+/g, " ").trim().slice(0, 72) : "Confira o mural público.";
    site.showToast(fresh.length === 1 ? "Novo aviso: " + preview : fresh.length + " novos avisos no mural.", "info");
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
      announceNewNotices(items, sourceState);
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
