(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;
  var body = site.body;
  var setButtonBusy = site.setButtonBusy;
  var attemptEndpoint = site.attemptEndpoint;

  function initPublicMedia() {
    if (body.dataset.page !== "home") return;

    var lists = {
      moments: document.querySelector('[data-media-list="moments"]'),
      clips: document.querySelector('[data-media-list="clips"]')
    };
    var emptyStates = {
      moments: document.querySelector('[data-media-empty="moments"]'),
      clips: document.querySelector('[data-media-empty="clips"]')
    };
    var updated = document.querySelector("[data-media-updated]");
    var status = document.querySelector("[data-media-status]");
    var refreshButton = document.querySelector("[data-media-refresh]");
    var lightbox = document.querySelector("[data-media-lightbox]");
    var lightboxContent = lightbox && lightbox.querySelector("[data-media-lightbox-content]");
    var lightboxTitle = lightbox && lightbox.querySelector("[data-media-lightbox-title]");
    var lightboxMeta = lightbox && lightbox.querySelector("[data-media-lightbox-meta]");
    var lightboxClose = lightbox && lightbox.querySelector("[data-media-lightbox-close]");
    var mediaTimer = null;
    var mediaLoading = false;
    var hasRendered = false;
    var lastValidItems = { moments: null, clips: null };
    var lastLoadAt = 0;
    var seed = readMediaSeed();
    var lightboxPreviousFocus = null;

    function readMediaSeed() {
      try {
        var stored = Number(window.localStorage.getItem("peace.media.seed.v1"));
        if (Number.isFinite(stored) && stored >= 0) return Math.floor(stored) % (2 ** 32);
      } catch (error) { /* optional */ }
      var value = Date.now() % (2 ** 32);
      try {
        if (window.crypto && window.crypto.getRandomValues) {
          var buffer = new Uint32Array(1);
          window.crypto.getRandomValues(buffer);
          value = buffer[0];
        }
        window.localStorage.setItem("peace.media.seed.v1", String(value));
      } catch (error) { /* optional */ }
      return value;
    }

    function saveMediaSeed() {
      try { window.localStorage.setItem("peace.media.seed.v1", String(seed)); } catch (error) { /* optional */ }
    }

    function mediaDate(value) {
      var parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) return "Agora";
      return parsed.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).replace(/\./g, "");
    }

    function makeNode(tagName, className, text) {
      var node = document.createElement(tagName);
      if (className) node.className = className;
      if (typeof text === "string") node.textContent = text;
      return node;
    }

    function configureExternalLink(link, url) {
      if (!link || !url) return;
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }

    function mediaKind(item) {
      if (item && item.kind === "embed") return "embed";
      if (item && item.kind === "direct") return "direct";
      if (item && item.kind === "link") return "link";
      if (item && item.embed_url) return "embed";
      var candidate = String(item && item.url || item && item.source_url || "");
      try {
        var parsed = new URL(candidate, window.location.href);
        if (parsed.hostname === "cdn.discordapp.com" || parsed.hostname === "media.discordapp.net" || /\.(?:avif|gif|jpe?g|m4v|mov|mp4|png|webm|webp)$/i.test(parsed.pathname)) return "direct";
      } catch (error) { /* the source-only fallback remains safe */ }
      return "link";
    }

    function cleanMediaText(value) {
      var text = String(value || "")
        .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
        .replace(/\[([^\]]+)\]\(([^)]*)\)/g, function (match, label, url) {
          // Empty Markdown links are common in imported Discord/Medal text.
          // Keep useful labels only when the source actually has a URL.
          return String(url || "").trim() ? label : "";
        })
        .replace(/(\*\*|__)(.*?)\1/g, "$2")
        .replace(/[\*_`~]/g, "")
        .replace(/\s+/g, " ")
        .trim();
      return text;
    }

    function mediaDisplayText(item) {
      var fallback = item && item.type === "video"
        ? "Um clip compartilhado na comunidade."
        : "Um momento compartilhado na comunidade.";
      var raw = item && (item.caption || item.provider_title || item.provider_author);
      return cleanMediaText(raw) || fallback;
    }

    function mediaSourceLabel(item) {
      return "Abrir origem" + (item && item.provider ? " · " + item.provider : "") + " ↗";
    }

    function mediaThumbnailUrl(item) {
      var candidate = String(item && item.thumbnail_url || "");
      if (!candidate) return "";
      try {
        var parsed = new URL(candidate, window.location.href);
        if (parsed.protocol !== "https:") return "";
        if (!["cdn.discordapp.com", "media.discordapp.net", "images-ext-1.discordapp.net", "cdn.medal.tv"].includes(parsed.hostname)) return "";
        return parsed.href;
      } catch (error) {
        return "";
      }
    }

    function canEmbedMedia(item) {
      return Boolean(item && item.embed_url && item.provider !== "Medal");
    }

    function mediaSourceFallback(item, className, options) {
      options = options || {};
      var wrapper = makeNode("div", className || "media-source-fallback");
      var thumbnailUrl = mediaThumbnailUrl(item);
      if (thumbnailUrl) {
        var thumbnail = makeNode("img", "media-source-fallback-image");
        thumbnail.src = thumbnailUrl;
        thumbnail.alt = "";
        thumbnail.width = 320;
        thumbnail.height = 200;
        thumbnail.loading = "lazy";
        thumbnail.decoding = "async";
        thumbnail.addEventListener("error", function () { thumbnail.remove(); }, { once: true });
        wrapper.appendChild(thumbnail);
      }
      var copy = makeNode("div", "media-source-fallback-copy");
      var label = makeNode("span", "media-source-fallback-provider", item && item.provider ? item.provider : "Mídia");
      var link = makeNode("a", "media-source-fallback-link", mediaSourceLabel(item));
      configureExternalLink(link, item && (item.fallback_url || item.source_url || item.url));
      copy.appendChild(label);
      if (options.showTitle !== false) {
        copy.appendChild(makeNode("strong", "media-source-fallback-title", mediaDisplayText(item)));
      }
      copy.appendChild(link);
      wrapper.appendChild(copy);
      return wrapper;
    }

    function mediaPlayer(item, className) {
      var node;
      var kind = mediaKind(item);
      if (kind === "embed" && canEmbedMedia(item)) {
        node = makeNode("iframe", className || "media-card-embed");
        node.src = item.embed_url;
        node.loading = "lazy";
        node.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
        node.referrerPolicy = "strict-origin-when-cross-origin";
        node.allowFullscreen = true;
        node.title = mediaDisplayText(item);
        node.dataset.provider = item.provider || "";
        return node;
      }
      if (kind === "direct" && item.type === "video") {
        node = makeNode("video", className || "media-card-video");
        node.controls = true;
        node.preload = "metadata";
        node.playsInline = true;
        node.setAttribute("aria-label", "Reproduzir clip da Peace");
        node.src = item.url || "";
        var poster = mediaThumbnailUrl(item);
        if (poster) node.poster = poster;
        node.dataset.provider = item.provider || "";
        node.addEventListener("error", function () {
          node.replaceWith(mediaSourceFallback(item, className === "media-lightbox-media" ? "media-lightbox-fallback" : "media-source-fallback", { showTitle: className === "media-lightbox-media" }));
        }, { once: true });
        return node;
      }
      if (kind === "direct" && item.type === "image") {
        node = makeNode("img", className || "media-card-image");
        node.loading = "lazy";
        node.decoding = "async";
        node.width = 16;
        node.height = 10;
        node.alt = mediaDisplayText(item);
        node.src = item.url || item.thumbnail_url || "";
        node.dataset.provider = item.provider || "";
        node.addEventListener("error", function () {
          node.replaceWith(mediaSourceFallback(item, className === "media-lightbox-media" ? "media-lightbox-fallback" : "media-source-fallback", { showTitle: className === "media-lightbox-media" }));
        }, { once: true });
        return node;
      }
      return mediaSourceFallback(item, className === "media-lightbox-media" ? "media-lightbox-fallback" : "media-source-fallback");
    }

    function openMediaViewer(item) {
      if (!lightbox || !lightboxContent) return;
      lightboxPreviousFocus = document.activeElement;
      lightboxContent.replaceChildren();
      if (lightboxTitle) lightboxTitle.textContent = mediaDisplayText(item);
      if (lightboxMeta) {
        lightboxMeta.replaceChildren();
        var metaText = mediaDate(item.created_at) + (item.engagement > 0 ? " · " + item.engagement + " reações" : "");
        lightboxMeta.appendChild(makeNode("span", "media-lightbox-date", metaText));
        if (item.author) lightboxMeta.appendChild(makeNode("span", "media-lightbox-author", item.author.display_name || item.author.username || "Membro"));
        if (item.provider_title && item.caption) lightboxMeta.appendChild(makeNode("span", "media-lightbox-provider-title", item.provider_title));
      }
      lightboxContent.dataset.provider = item.provider || "";
      lightboxContent.appendChild(mediaPlayer(item, "media-lightbox-media"));
      if (typeof lightbox.showModal === "function") lightbox.showModal();
      else lightbox.hidden = false;
      if (lightboxClose) lightboxClose.focus();
    }

    function closeMediaViewer() {
      if (!lightbox) return;
      if (typeof lightbox.close === "function" && lightbox.open) lightbox.close();
      else lightbox.hidden = true;
      if (lightboxPreviousFocus && typeof lightboxPreviousFocus.focus === "function") lightboxPreviousFocus.focus();
      lightboxPreviousFocus = null;
    }

    function addExpandButton(visual, item) {
      var expand = makeNode("button", "media-card-expand", "Ampliar");
      expand.type = "button";
      expand.addEventListener("click", function () { openMediaViewer(item); });
      visual.appendChild(expand);
    }

    function mediaCard(item) {
      var article = makeNode("article", "media-card");
      article.setAttribute("role", "listitem");
      var visual = makeNode("div", "media-card-visual");
      visual.dataset.provider = item.provider || "";
      if (mediaKind(item) === "embed" && canEmbedMedia(item)) {
        visual.appendChild(mediaPlayer(item, "media-card-embed"));
        addExpandButton(visual, item);
      } else if (mediaKind(item) === "direct" && item.type === "video") {
        visual.appendChild(mediaPlayer(item, "media-card-video"));
        addExpandButton(visual, item);
      } else if (mediaKind(item) === "direct" && item.type === "image") {
        var imageButton = makeNode("button", "media-card-media-button");
        imageButton.type = "button";
        imageButton.setAttribute("aria-label", "Ampliar imagem");
        imageButton.appendChild(mediaPlayer(item, "media-card-image"));
        imageButton.addEventListener("click", function () { openMediaViewer(item); });
        visual.appendChild(imageButton);
      } else {
        // The card copy already contains the message text and provider title.
        // Keep the visual fallback to a compact provider/origin action so a
        // long Medal title cannot collide with the badge or repeat below.
        visual.appendChild(mediaSourceFallback(item, "media-card-source-preview", { showTitle: false }));
      }
      var hasPlayableVisual = mediaKind(item) === "direct" || (mediaKind(item) === "embed" && canEmbedMedia(item));
      if (hasPlayableVisual) {
        var badge = makeNode("span", "media-card-badge", item.type === "video" ? (item.provider || "Clip") : "Momento");
        badge.setAttribute("aria-hidden", "true");
        visual.appendChild(badge);
      }
      article.appendChild(visual);

      var copy = makeNode("div", "media-card-copy");
      var engagement = Number(item.engagement || 0);
      var metaText = mediaDate(item.created_at) + (engagement > 0 ? " · " + engagement + " reações" : "");
      copy.appendChild(makeNode("p", "media-card-meta", metaText));
      copy.appendChild(makeNode("p", "media-card-caption", mediaDisplayText(item)));
      if (item.caption && item.provider_title && item.provider_title !== item.caption) copy.appendChild(makeNode("p", "media-card-provider-title", item.provider_title));
      if (item.author) {
        var authorRow = makeNode("div", "media-card-author");
        var avatar = makeNode("span", "media-card-author-avatar");
        if (item.author.avatar_url) {
          var avatarImage = makeNode("img", "media-card-author-image");
          avatarImage.src = item.author.avatar_url;
          avatarImage.alt = "";
          avatarImage.width = 32;
          avatarImage.height = 32;
          avatarImage.loading = "lazy";
          avatarImage.decoding = "async";
          avatar.appendChild(avatarImage);
        } else {
          avatar.textContent = String(item.author.display_name || "M").charAt(0).toUpperCase();
        }
        authorRow.appendChild(avatar);
        authorRow.appendChild(makeNode("span", "media-card-author-name", item.author.display_name || item.author.username || "Membro"));
        if (item.author.username && item.author.username !== item.author.display_name) authorRow.appendChild(makeNode("span", "media-card-author-handle", "@" + item.author.username));
        copy.appendChild(authorRow);
      }
      if (mediaKind(item) !== "link" && (item.fallback_url || item.source_url || item.url) && item.provider && item.provider !== "Discord") {
        var source = makeNode("a", "media-card-source", mediaSourceLabel(item));
        configureExternalLink(source, item.fallback_url || item.source_url || item.url);
        copy.appendChild(source);
      }
      article.appendChild(copy);
      return article;
    }

    if (lightbox) {
      if (lightboxClose) lightboxClose.addEventListener("click", closeMediaViewer);
      lightbox.addEventListener("click", function (event) {
        if (event.target === lightbox) closeMediaViewer();
      });
      lightbox.addEventListener("cancel", function (event) {
        event.preventDefault();
        closeMediaViewer();
      });
    }

    function renderList(kind, items, source) {
      var list = lists[kind];
      var empty = emptyStates[kind];
      if (!list) return 0;
      var sourceUnavailable = source && source.state === "unavailable";
      if (sourceUnavailable && Array.isArray(lastValidItems[kind])) {
        items = lastValidItems[kind];
      } else if (!sourceUnavailable && Array.isArray(items) && items.length) {
        lastValidItems[kind] = items.slice();
      }
      list.replaceChildren();
      list.setAttribute("aria-busy", "false");
      if (!Array.isArray(items) || !items.length) {
        if (empty) {
          empty.textContent = source && source.state === "unavailable"
            ? "Esta fonte está indisponível agora. Tente atualizar em instantes."
            : (kind === "clips"
              ? "Os clipes entram aqui quando forem publicados pela comunidade."
              : "Os próximos momentos aparecem aqui quando a comunidade compartilhar algo novo.");
          empty.hidden = false;
        }
        return 0;
      }
      if (empty) empty.hidden = true;
      items.forEach(function (item) { list.appendChild(mediaCard(item)); });
      return items.length;
    }

    function parseMediaResponse(response) {
      return response.text().then(function (raw) {
        var payload = null;
        try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
        if (!payload || payload.ok !== true) throw new Error("media unavailable");
        return payload;
      });
    }

    function scheduleMediaRefresh(seconds) {
      window.clearTimeout(mediaTimer);
      mediaTimer = window.setTimeout(function () {
        if (document.visibilityState === "visible") loadMedia(false);
        else scheduleMediaRefresh(120);
      }, Math.max(60, Number(seconds) || 300) * 1000);
    }

    function loadMedia(showBusy) {
      if (mediaLoading) return Promise.resolve();
      mediaLoading = true;
      if (showBusy) setButtonBusy(refreshButton, true, "Atualizando…");
      if (!hasRendered) {
        Object.keys(lists).forEach(function (kind) {
          if (lists[kind]) lists[kind].setAttribute("aria-busy", "true");
        });
        if (updated) updated.textContent = "Carregando momentos…";
      }
      return attemptEndpoint("/api/media?seed=" + encodeURIComponent(String(seed)), { headers: { Accept: "application/json" } }, 12000)
        .then(parseMediaResponse)
        .then(function (payload) {
          var sources = payload.sources || {};
          var momentsCount = renderList("moments", payload.moments || [], sources.moments);
          var clipsCount = renderList("clips", payload.clips || [], sources.clips);
          var count = momentsCount + clipsCount;
          var stale = Boolean(sources.moments && sources.moments.stale) || Boolean(sources.clips && sources.clips.stale);
          if (updated) updated.textContent = count
            ? (stale ? "Última leitura · uma fonte está desatualizada" : "Atualizado agora · registros do Discord")
            : "A comunidade continua em movimento no Discord.";
          if (status) status.textContent = count
            ? (stale ? "A última leitura continua disponível." : "Momentos atualizados.")
            : "Os próximos registros aparecem aqui quando forem publicados.";
          lastLoadAt = Date.now();
          hasRendered = true;
          scheduleMediaRefresh(payload.refresh_after);
        })
        .catch(function () {
          if (!hasRendered) {
            renderList("moments", []);
            renderList("clips", []);
            if (updated) updated.textContent = "Não consegui carregar os registros agora.";
          } else if (updated) updated.textContent = "Não consegui atualizar agora · mostrando a última leitura.";
          if (status) status.textContent = hasRendered ? "A última leitura continua disponível." : "Tente atualizar novamente em instantes.";
          lastLoadAt = Date.now();
          hasRendered = true;
          scheduleMediaRefresh(300);
        })
        .finally(function () {
          mediaLoading = false;
          if (showBusy) setButtonBusy(refreshButton, false);
        });
    }

    if (refreshButton) refreshButton.addEventListener("click", function () {
      seed = (seed + 1) % (2 ** 32);
      saveMediaSeed();
      loadMedia(true);
    });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible" && Date.now() - lastLoadAt > 120000) loadMedia(false);
    });
    loadMedia(false);
  }


  site.initPublicMedia = initPublicMedia;
})(window);
