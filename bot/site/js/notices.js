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

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function inlineMarkdown(value) {
    var html = escapeHtml(value)
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
      .replace(/__([^_\n]+)__/g, "<strong>$1</strong>")
      .replace(/~~([^~\n]+)~~/g, "<del>$1</del>")
      .replace(/(^|\s)\*([^*\n]+)\*(?=\s|$)/g, "$1<em>$2</em>")
      .replace(/(^|\s)_([^_\n]+)_(?=\s|$)/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/(^|[^\w])(@[\w.-]{2,32})/g, '$1<span class="notice-mention">$2</span>');
    return html;
  }

  function renderMarkdown(container, value) {
    var lines = String(value || "Comunicado sem texto.").replace(/\r\n?/g, "\n").split("\n");
    var fragment = document.createDocumentFragment();
    var list = null;
    var code = false;
    var codeLines = [];
    function closeList() { if (list) { fragment.appendChild(list); list = null; } }
    lines.forEach(function (line) {
      if (/^\s*```/.test(line)) {
        if (code) {
          var pre = document.createElement("pre");
          var codeNode = document.createElement("code");
          codeNode.textContent = codeLines.join("\n");
          pre.appendChild(codeNode); fragment.appendChild(pre);
          codeLines = []; code = false;
        } else { closeList(); code = true; }
        return;
      }
      if (code) { codeLines.push(line); return; }
      var heading = line.match(/^\s*(#{1,3})\s+(.+)$/);
      var bullet = line.match(/^\s*[-*+]\s+(.+)$/);
      if (bullet) {
        if (!list) { list = document.createElement("ul"); }
        var li = document.createElement("li"); li.innerHTML = inlineMarkdown(bullet[1]); list.appendChild(li); return;
      }
      closeList();
      if (!line.trim()) return;
      var block = document.createElement(heading ? "h" + Math.min(3, heading[1].length) : /^\s*>/.test(line) ? "blockquote" : "p");
      block.innerHTML = inlineMarkdown(heading ? heading[2] : line.replace(/^\s*>\s?/, ""));
      fragment.appendChild(block);
    });
    if (code) {
      var trailing = document.createElement("pre"); var trailingCode = document.createElement("code");
      trailingCode.textContent = codeLines.join("\n"); trailing.appendChild(trailingCode); fragment.appendChild(trailing);
    }
    closeList();
    container.replaceChildren(fragment);
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
      var empty = document.createElement("div"); empty.className = "notice-chat-empty";
      var icon = document.createElement("span"); icon.className = "notice-chat-empty-icon"; icon.textContent = sourceState === "unavailable" ? "!" : "—";
      var title = document.createElement("strong"); title.textContent = sourceState === "unavailable" ? "Avisos indisponíveis agora" : "Nenhum aviso publicado";
      var copy = document.createElement("p"); copy.textContent = sourceState === "unavailable" ? "A fonte pública não respondeu. Tente novamente em instantes." : "Quando a equipe publicar, o comunicado aparece aqui.";
      empty.append(icon, title, copy); list.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var article = document.createElement("article");
      article.className = "notice-chat-message";
      var avatar = document.createElement("div"); avatar.className = "notice-chat-avatar";
      if (item.avatar_url) { var image = document.createElement("img"); image.src = item.avatar_url; image.alt = ""; image.width = 40; image.height = 40; image.loading = "lazy"; image.addEventListener("error", function () { image.remove(); avatar.textContent = String(item.author || "P").slice(0, 1).toUpperCase(); }); avatar.appendChild(image); }
      else avatar.textContent = String(item.author || "P").slice(0, 1).toUpperCase();
      var body = document.createElement("div"); body.className = "notice-chat-message-body";
      var meta = document.createElement("div"); meta.className = "notice-chat-message-meta";
      var author = document.createElement("strong"); author.textContent = item.author || "Peace";
      var time = document.createElement("time"); time.dateTime = item.published_at || ""; time.textContent = formatDate(item.published_at); meta.append(author, time);
      body.appendChild(meta);
      if (item.title) { var title = document.createElement("h2"); title.textContent = item.title; body.appendChild(title); }
      var copy = document.createElement("div"); copy.className = "notice-chat-markdown"; renderMarkdown(copy, item.text); body.appendChild(copy);
      if (item.image_url) { var asset = document.createElement("img"); asset.className = "notice-chat-asset"; asset.src = item.image_url; asset.alt = "Imagem do aviso"; asset.loading = "lazy"; body.appendChild(asset); }
      article.append(avatar, body);
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
