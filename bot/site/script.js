(function () {
  "use strict";

  var body = document.body;
  var header = document.querySelector(".site-header");
  var menuButton = document.querySelector(".menu-toggle");
  var navigation = document.querySelector("#site-nav");
  var revealItems = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var mobileNavigation = window.matchMedia("(max-width: 840px)");
  var memberSessionStorageKey = "peace.member.session.v1";

  function readMemberSessionToken() {
    try {
      var persistent = window.localStorage.getItem(memberSessionStorageKey) || "";
      if (persistent) return persistent;
    } catch (error) { /* optional */ }
    try {
      return window.sessionStorage.getItem(memberSessionStorageKey) || "";
    } catch (error) {
      return "";
    }
  }

  function storeMemberSessionToken(token, keepConnected) {
    try {
      if (keepConnected) window.localStorage.setItem(memberSessionStorageKey, token);
      else window.localStorage.removeItem(memberSessionStorageKey);
    } catch (error) { /* optional */ }
    try {
      if (keepConnected) window.sessionStorage.removeItem(memberSessionStorageKey);
      else window.sessionStorage.setItem(memberSessionStorageKey, token);
    } catch (error) { /* optional */ }
  }

  function clearMemberSessionToken() {
    try { window.localStorage.removeItem(memberSessionStorageKey); } catch (error) { /* optional */ }
    try { window.sessionStorage.removeItem(memberSessionStorageKey); } catch (error) { /* optional */ }
  }

  document.documentElement.classList.add("js-ready");

  // Discord destinations always open outside the Peace flow so the current
  // page remains available for status, return navigation, and retry actions.
  document.querySelectorAll('a[href^="/discord"], a[href^="../discord"]').forEach(function (link) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  });

  document.querySelectorAll("a[href]").forEach(function (link) {
    link.addEventListener("click", function (event) {
      if (reducedMotion || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (link.target === "_blank" || link.hasAttribute("download") || link.getAttribute("href").charAt(0) === "#") return;
      var destination;
      try { destination = new URL(link.href, window.location.href); } catch (error) { return; }
      if (destination.origin !== window.location.origin || destination.href === window.location.href) return;
      event.preventDefault();
      document.body.classList.add("is-leaving");
      window.setTimeout(function () { window.location.assign(destination.href); }, 150);
    });
  });

  window.addEventListener("pageshow", function () { document.body.classList.remove("is-leaving"); });

  function syncNavigationInteraction(isOpen) {
    if (!navigation) return;
    var shouldDisable = mobileNavigation.matches && !isOpen;
    navigation.inert = shouldDisable;
    navigation.setAttribute("aria-hidden", String(shouldDisable));
  }

  function closeMenu(restoreFocus) {
    if (!header || !menuButton) return;
    header.classList.remove("menu-open");
    menuButton.setAttribute("aria-expanded", "false");
    syncNavigationInteraction(false);
    if (restoreFocus) menuButton.focus();
  }

  if (menuButton && navigation && header) {
    syncNavigationInteraction(false);

    menuButton.addEventListener("click", function () {
      var isOpen = header.classList.toggle("menu-open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
      syncNavigationInteraction(isOpen);
    });

    navigation.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { closeMenu(false); });
    });

    document.addEventListener("click", function (event) {
      if (header.classList.contains("menu-open") && !header.contains(event.target)) closeMenu(true);
    });

    mobileNavigation.addEventListener("change", function () { closeMenu(false); });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && header && header.classList.contains("menu-open")) closeMenu(true);
  });

  function reveal(element) { element.classList.add("is-visible"); }

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach(reveal);
  } else {
    var observer = new IntersectionObserver(function (entries, currentObserver) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        reveal(entry.target);
        currentObserver.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });

    revealItems.forEach(function (element) { observer.observe(element); });
  }

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

    function mediaDisplayText(item) {
      if (item && item.caption) return item.caption;
      if (item && item.provider_title) return item.provider_title;
      if (item && item.provider_author) return item.provider_author;
      return item && item.type === "video" ? "Um clip compartilhado na comunidade." : "Um momento compartilhado na comunidade.";
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

    function mediaSourceFallback(item, className) {
      var wrapper = makeNode("div", className || "media-source-fallback");
      var thumbnailUrl = mediaThumbnailUrl(item);
      if (thumbnailUrl) {
        var thumbnail = makeNode("img", "media-source-fallback-image");
        thumbnail.src = thumbnailUrl;
        thumbnail.alt = "";
        thumbnail.loading = "lazy";
        thumbnail.decoding = "async";
        thumbnail.addEventListener("error", function () { thumbnail.remove(); }, { once: true });
        wrapper.appendChild(thumbnail);
      }
      var copy = makeNode("div", "media-source-fallback-copy");
      var label = makeNode("span", "media-source-fallback-provider", item && item.provider ? item.provider : "Mídia");
      var title = makeNode("strong", "media-source-fallback-title", mediaDisplayText(item));
      var link = makeNode("a", "media-source-fallback-link", mediaSourceLabel(item));
      configureExternalLink(link, item && (item.fallback_url || item.source_url || item.url));
      copy.appendChild(label);
      copy.appendChild(title);
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
          node.replaceWith(mediaSourceFallback(item, className === "media-lightbox-media" ? "media-lightbox-fallback" : "media-source-fallback"));
        }, { once: true });
        return node;
      }
      if (kind === "direct" && item.type === "image") {
        node = makeNode("img", className || "media-card-image");
        node.loading = "lazy";
        node.decoding = "async";
        node.alt = mediaDisplayText(item);
        node.src = item.url || item.thumbnail_url || "";
        node.dataset.provider = item.provider || "";
        node.addEventListener("error", function () {
          node.replaceWith(mediaSourceFallback(item, className === "media-lightbox-media" ? "media-lightbox-fallback" : "media-source-fallback"));
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
        visual.appendChild(mediaSourceFallback(item, "media-card-source-preview"));
      }
      var badge = makeNode("span", "media-card-badge", item.type === "video" ? (item.provider || "Clip") : "Momento");
      badge.setAttribute("aria-hidden", "true");
      visual.appendChild(badge);
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
          avatar.appendChild(avatarImage);
        } else {
          avatar.textContent = String(item.author.display_name || "M").charAt(0).toUpperCase();
        }
        authorRow.appendChild(avatar);
        authorRow.appendChild(makeNode("span", "media-card-author-name", item.author.display_name || item.author.username || "Membro"));
        if (item.author.username && item.author.username !== item.author.display_name) authorRow.appendChild(makeNode("span", "media-card-author-handle", "@" + item.author.username));
        copy.appendChild(authorRow);
      }
      if ((item.fallback_url || item.source_url || item.url) && item.provider && item.provider !== "Discord") {
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

    function renderList(kind, items) {
      var list = lists[kind];
      var empty = emptyStates[kind];
      if (!list) return;
      list.replaceChildren();
      list.setAttribute("aria-busy", "false");
      if (!Array.isArray(items) || !items.length) {
        if (empty) empty.hidden = false;
        return;
      }
      if (empty) empty.hidden = true;
      items.forEach(function (item) { list.appendChild(mediaCard(item)); });
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
          renderList("moments", payload.moments || []);
          renderList("clips", payload.clips || []);
          var count = (payload.moments || []).length + (payload.clips || []).length;
          if (updated) updated.textContent = count ? "Atualizado agora · registros do Discord" : "A comunidade continua em movimento no Discord.";
          if (status) status.textContent = count ? "Momentos atualizados." : "Os próximos registros aparecem aqui quando forem publicados.";
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

  function copyAllowedFrom(node) {
    var element = node && node.nodeType === 1 ? node : node && node.parentElement;
    return Boolean(element && element.closest("[data-copyable], code, pre, input, textarea, [contenteditable=\"true\"]"));
  }

  document.addEventListener("copy", function (event) {
    var selection = window.getSelection();
    if (!selection || (!copyAllowedFrom(selection.anchorNode) && !copyAllowedFrom(selection.focusNode))) {
      event.preventDefault();
    }
  });

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () { return true; });
    }

    var fallback = document.createElement("textarea");
    fallback.value = text;
    fallback.setAttribute("readonly", "");
    fallback.style.position = "fixed";
    fallback.style.top = "-9999px";
    document.body.appendChild(fallback);
    fallback.select();
    var copied = false;
    try { copied = document.execCommand("copy"); } catch (error) { copied = false; }
    document.body.removeChild(fallback);
    return Promise.resolve(copied);
  }

  document.querySelectorAll("[data-copy-target]").forEach(function (button) {
    button.addEventListener("click", function () {
      var target = document.querySelector(button.dataset.copyTarget);
      var status = button.closest(".discord-copy") && button.closest(".discord-copy").querySelector("[data-copy-status], .copy-status");
      if (!target || !status) return;

      copyText(target.textContent.trim())
        .then(function (copied) {
          status.textContent = copied ? "Link copiado." : "Não foi possível copiar aqui.";
          window.setTimeout(function () { status.textContent = ""; }, 3500);
        })
        .catch(function () {
          status.textContent = "Não foi possível copiar aqui.";
        });
    });
  });

  function setStatusMessage(node, title, message, tone) {
    if (!node) return;
    node.hidden = false;
    var strong = node.querySelector("strong");
    var paragraph = node.querySelector("p");
    if (strong) strong.textContent = title;
    if (paragraph) paragraph.textContent = message;
    node.dataset.state = tone || "pending";
  }

  function setButtonLabel(button, label) {
    if (!button) return;
    var labelNode = button.querySelector("[data-button-label]");
    if (labelNode) labelNode.textContent = label;
    button.dataset.idleLabel = label;
  }

  function setButtonBusy(button, isBusy, loadingLabel) {
    if (!button) return;
    var labelNode = button.querySelector("[data-button-label]");
    if (isBusy) {
      if (!button.dataset.idleLabel && labelNode) button.dataset.idleLabel = labelNode.textContent;
      if (labelNode) labelNode.textContent = loadingLabel || "Processando…";
      button.classList.add("is-loading");
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      return;
    }

    if (labelNode && button.dataset.idleLabel) labelNode.textContent = button.dataset.idleLabel;
    button.classList.remove("is-loading");
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }

  function userFacingEndpointMessage(payload, status, fallback) {
    var code = payload && typeof payload.code === "string" ? payload.code : "";
    var knownMessages = {
      DISCORD_NOT_READY: "O Peace Tools está conectando ao Discord. Tente novamente em instantes.",
      VERIFY_CHANNEL_UNAVAILABLE: "O canal de verificação está temporariamente indisponível. Tente novamente em instantes.",
      INVITE_UNAVAILABLE: "Não consegui gerar seu convite agora. Tente novamente em instantes.",
      INVITE_INVALID: "Não consegui preparar seu convite agora. Tente novamente em instantes.",
      ENTRY_SESSION_NOT_FOUND: "Este convite expirou. Gere um novo link para continuar.",
      INVALID_SESSION: "A conexão anterior não está mais disponível. Gere um novo convite.",
      NOT_JOINED: "Ainda estou aguardando a confirmação automática da sua entrada na Peace.",
      ROLE_NOT_CONFIGURED: "A equipe precisa ajustar o cargo de entrada antes de continuar.",
      ROLE_HIERARCHY: "A equipe precisa ajustar a hierarquia de cargos antes de continuar.",
      ROLE_UPDATE_FAILED: "Não consegui corrigir o cargo de entrada agora. Tente novamente em instantes.",
      MEMBER_UNAVAILABLE: "Ainda não consegui localizar sua entrada. Tente novamente em instantes.",
      REPAIR_THROTTLED: "Aguarde alguns segundos e tente novamente.",
      DISCORD_ID_MISMATCH: "O ID informado não corresponde à conta identificada pelo convite.",
      INVALID_DISCORD_ID: "O ID do Discord deve conter somente números.",
      FIELD_TOO_LONG: "Revise os campos informados e tente novamente.",
      INVALID_PEACE_ID: "O ID Peace deve conter somente números.",
      AUTH_DENIED: "Não foi possível validar esse ID Peace. Confira os números e tente novamente.",
      AUTH_THROTTLED: "Aguarde alguns minutos antes de solicitar outro código.",
      DM_UNAVAILABLE: "Não consegui enviar a mensagem privada. Abra suas DMs no Discord e tente novamente.",
      INVALID_CODE: "O código não confere ou já expirou. Confira a DM e tente novamente.",
      AUTH_SESSION_INVALID: "Sua sessão expirou. Entre novamente.",
      AUTH_SESSION_UNAVAILABLE: "Não foi possível concluir o acesso agora. Tente novamente.",
      MEMBER_NOT_FOUND: "Não encontrei essa conta no servidor. Revise o username e tente novamente.",
      MEMBER_AMBIGUOUS: "Encontrei mais de uma conta com esse username. Informe também o ID ou o link do perfil.",
      INVALID_DISCORD_PROFILE: "Informe um link de perfil válido do Discord.",
      MEMBER_IDENTITY_MISMATCH: "O username, o ID e o link informado não pertencem à mesma conta.",
      ENTRY_MEMBER_NOT_FOUND: "Não encontrei sua conta no servidor. Revise os dados e tente novamente."
    };

    if (knownMessages[code]) return knownMessages[code];
    if (status === 404) return "O serviço de entrada está sendo atualizado. Tente novamente em instantes.";
    if (status === 429) return "Aguarde alguns segundos e tente novamente.";
    if (status >= 500) return "O Peace Tools está terminando uma atualização. Tente novamente em instantes.";
    return fallback || "Não foi possível continuar agora. Tente novamente.";
  }

  function friendlyError(payload, status, fallback) {
    var error = new Error(userFacingEndpointMessage(payload, status, fallback));
    error.code = payload && payload.code ? payload.code : "";
    error.status = status || 0;
    return error;
  }

  function responseFailure(response, fallback) {
    return response.text().then(function (raw) {
      var payload = null;
      try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
      throw friendlyError(payload, response.status, fallback);
    });
  }

  function attemptEndpoint(url, options, timeoutMs) {
    if (!window.fetch) {
      var browserError = new Error("A conexão não está disponível neste navegador. Tente novamente.");
      browserError.code = "BROWSER_NETWORK";
      return Promise.reject(browserError);
    }
    var requestOptions = Object.assign({}, options || { headers: { Accept: "application/json" } });
    var controller = typeof window.AbortController === "function" ? new window.AbortController() : null;
    var timeoutId;
    var duration = Number(timeoutMs) > 0 ? Number(timeoutMs) : 60000;

    if (controller) requestOptions.signal = controller.signal;

    var request = window.fetch(url, requestOptions).then(function (response) {
      return response.ok ? response : responseFailure(response, "Não foi possível continuar agora. Tente novamente.");
    });

    var timeout = new Promise(function (_, reject) {
      timeoutId = window.setTimeout(function () {
        if (controller) controller.abort();
        var error = new Error("A conexão demorou mais do que o esperado. Tente novamente.");
        error.code = "TIMEOUT";
        reject(error);
      }, duration);
    });

    return Promise.race([request, timeout]).then(function (response) {
      window.clearTimeout(timeoutId);
      return response;
    }, function (error) {
      window.clearTimeout(timeoutId);
      throw error;
    });
  }

  function initCandidature() {
    if (body.dataset.page !== "candidatura") return;

    var stageButtons = Array.prototype.slice.call(document.querySelectorAll("[data-stage-preview]"));
    var stages = Array.prototype.slice.call(document.querySelectorAll("[data-entry-stage]"));
    var wizard = document.querySelector("[data-wizard]");
    var wizardPanels = wizard ? Array.prototype.slice.call(wizard.querySelectorAll("[data-wizard-panel]")) : [];
    var wizardNext = wizard && wizard.querySelector("[data-wizard-next]");
    var wizardBack = wizard && wizard.querySelector("[data-wizard-back]");
    var wizardLabel = wizard && wizard.querySelector("[data-wizard-label]");
    var wizardPercent = wizard && wizard.querySelector("[data-wizard-progress]");
    var wizardTrack = wizard && wizard.querySelector("[data-wizard-track]");
    var connectButton = document.querySelector("[data-entry-connect]");
    var connectResult = document.querySelector("[data-entry-result]");
    var sessionNote = document.querySelector("[data-entry-session-note]");
    var invitePanel = document.querySelector("[data-entry-invite-panel]");
    var inviteLink = document.querySelector("[data-entry-invite-link]");
    var inviteOpenLink = document.querySelector("[data-entry-invite-open]");
    var inviteUrlText = document.querySelector("[data-entry-invite-url]");
    var inviteWaiting = document.querySelector("[data-entry-invite-waiting]");
    var inviteWaitingTitle = document.querySelector("[data-entry-invite-status-title]");
    var inviteWaitingMessage = document.querySelector("[data-entry-invite-status-message]");
    var entryUser = document.querySelector("[data-entry-user]");
    var verificationState = document.querySelector("[data-entry-verification-state]");
    var verificationTitle = document.querySelector("[data-entry-status-title]");
    var verificationMessage = document.querySelector("[data-entry-status-message]");
    var refreshButton = document.querySelector("[data-entry-refresh]");
    var refreshResult = document.querySelector("[data-entry-refresh-result]");
    var helpToggle = document.querySelector("[data-entry-help-toggle]");
    var helpPanel = document.querySelector("[data-entry-help]");
    var repairForm = document.querySelector("[data-entry-repair]");
    var repairSubmit = document.querySelector("[data-entry-repair-submit]");
    var repairResult = document.querySelector("[data-entry-repair-result]");
    var existingToggle = document.querySelector("[data-entry-existing-toggle]");
    var existingPanel = document.querySelector("[data-entry-existing-panel]");
    var existingClose = existingPanel && existingPanel.querySelector("[data-entry-existing-close]");
    var existingForm = document.querySelector("[data-entry-existing]");
    var existingSubmit = document.querySelector("[data-entry-existing-submit]");
    var existingResult = document.querySelector("[data-entry-existing-result]");
    var manualEntryNote = document.querySelector("[data-entry-manual-note]");
    var memberResult = document.querySelector("[data-entry-member-result]");
    var stageContext = document.querySelector("[data-entry-stage-context]");
    var storageKey = "peace.candidature.v2";
    var entryStorageKey = "peace.entry.v1";
    var entryMetaStorageKey = "peace.entry.meta.v1";
    var manualEntryStorageKey = "peace.entry.manual.v1";
    var currentStage = 1;
    var wizardStep = 1;
    var restoring = true;
    var entrySession = null;
    var entryPollTimer = null;
    var entryStartPromise = null;
    var entryStatusPromise = null;
    var entryRecoveryPromise = null;
    var inviteOpened = false;
    var manualEntryIdentity = null;
    var existingPreviousFocus = null;
    var entryInviteWindowName = "peace-discord-invite";

    function readDraft() {
      try {
        var raw = window.localStorage.getItem(storageKey);
        if (!raw) return null;
        var draft = JSON.parse(raw);
        return draft && draft.version === 2 ? draft : null;
      } catch (error) {
        return null;
      }
    }

    function getField(name) {
      return wizard && wizard.querySelector('[name="' + name + '"]');
    }

    function readEntryToken() {
      try {
        var token = window.localStorage.getItem(entryStorageKey);
        return token && /^[A-Za-z0-9_-]{32,128}$/.test(token) ? token : "";
      } catch (error) {
        return "";
      }
    }

    function saveEntryToken(token) {
      try {
        if (token) window.localStorage.setItem(entryStorageKey, token);
      } catch (error) {
        // Session continuity is optional; the current tab remains usable.
      }
    }

    function clearEntryToken() {
      try { window.localStorage.removeItem(entryStorageKey); } catch (error) { /* optional */ }
    }

    function readManualEntry() {
      try {
        var raw = window.localStorage.getItem(manualEntryStorageKey);
        if (!raw) return null;
        var identity = JSON.parse(raw);
        return identity && identity.version === 1 && identity.discord_username ? identity : null;
      } catch (error) {
        return null;
      }
    }

    function saveManualEntry(identity) {
      manualEntryIdentity = identity;
      try { window.localStorage.setItem(manualEntryStorageKey, JSON.stringify({ version: 1, ...identity })); } catch (error) { /* optional */ }
    }

    function setManualEntryFields(identity) {
      if (!existingForm || !identity) return;
      ["discord_username", "discord_id", "discord_profile_url"].forEach(function (name) {
        var field = existingForm.querySelector('[name="' + name + '"]');
        if (field && typeof identity[name] === "string") field.value = identity[name];
      });
    }

    function readEntryMeta(token) {
      try {
        var raw = window.localStorage.getItem(entryMetaStorageKey);
        if (!raw) return false;
        var meta = JSON.parse(raw);
        return Boolean(meta && meta.version === 1 && meta.session_token === token && meta.invite_opened === true);
      } catch (error) {
        return false;
      }
    }

    function markInviteOpened(token) {
      inviteOpened = true;
      try {
        window.localStorage.setItem(entryMetaStorageKey, JSON.stringify({
          version: 1,
          session_token: token,
          invite_opened: true,
          opened_at: Date.now()
        }));
      } catch (error) {
        // The current tab remains usable when storage is unavailable.
      }
    }

    function clearInviteMeta() {
      inviteOpened = false;
      try { window.localStorage.removeItem(entryMetaStorageKey); } catch (error) { /* optional */ }
    }

    function reserveEntryInviteWindow() {
      try {
        return window.open("about:blank", entryInviteWindowName, "popup,width=520,height=760");
      } catch (error) {
        return null;
      }
    }

    function openEntryInvite(url, token, reservedPopup) {
      if (!url) return null;
      var popup = reservedPopup || null;
      try {
        if (!popup || popup.closed) popup = window.open(url, entryInviteWindowName);
        else popup.location.replace(url);
        if (popup) {
          try { popup.opener = null; } catch (error) { /* browser-controlled */ }
          try { popup.focus(); } catch (error) { /* browser-controlled */ }
          markInviteOpened(token);
        }
      } catch (error) {
        popup = null;
      }
      return popup;
    }

    function inviteLabel(url) {
      try {
        var parsed = new URL(url, window.location.href);
        return parsed.host + parsed.pathname;
      } catch (error) {
        return String(url || "").replace(/^https?:\/\//i, "");
      }
    }

    function setInviteLinks(url, token, keepPanel) {
      var hasInvite = Boolean(url);
      var showPanel = hasInvite || Boolean(keepPanel);
      if (invitePanel) invitePanel.hidden = !showPanel;

      // The Discord action is one control in every state. The invite-ready
      // state changes its label and URL instead of rendering a second button.
      if (connectButton) {
        connectButton.hidden = false;
        if (hasInvite) {
          connectButton.dataset.inviteUrl = url;
          connectButton.dataset.sessionToken = token || "";
          setButtonLabel(connectButton, "Abrir convite do Discord");
        } else {
          delete connectButton.dataset.inviteUrl;
          delete connectButton.dataset.sessionToken;
          setButtonLabel(connectButton, "Conectar no Discord");
        }
      }
      if (inviteOpenLink && inviteOpenLink !== connectButton) {
        inviteOpenLink.hidden = true;
        inviteOpenLink.removeAttribute("href");
      }
      if (inviteLink) {
        inviteLink.textContent = hasInvite ? inviteLabel(url) : "";
        inviteLink.hidden = !hasInvite;
        if (hasInvite) {
          inviteLink.href = url;
          inviteLink.dataset.sessionToken = token || "";
          inviteLink.target = entryInviteWindowName;
        } else {
          inviteLink.removeAttribute("href");
          delete inviteLink.dataset.sessionToken;
        }
      }
      if (inviteUrlText) inviteUrlText.textContent = hasInvite ? inviteLabel(url) : "";
    }

    function setVerificationState(state, title, message) {
      if (verificationState) verificationState.dataset.state = state || "pending";
      if (verificationTitle) verificationTitle.textContent = title || "Acompanhando sua entrada";
      if (verificationMessage) verificationMessage.textContent = message || "Aguarde alguns instantes.";
    }

    function setInviteWaiting(state, title, message) {
      if (!inviteWaiting) return;
      inviteWaiting.hidden = false;
      inviteWaiting.dataset.state = state || "pending";
       if (inviteWaitingTitle) inviteWaitingTitle.textContent = title || "Aguardando sua entrada";
      if (inviteWaitingMessage) inviteWaitingMessage.textContent = message || "Aguarde a confirmação da sua entrada.";
    }

    function isInviteRecoveryStatus(status) {
      return status === "invite_unavailable" || status === "expired";
    }

    function showInviteRecoveryState() {
      setInviteLinks("", "", true);
      setInviteWaiting(
        "pending",
        "Gerando um novo convite…",
        "O convite anterior deixou de estar disponível. Aguarde enquanto preparamos outro link válido."
      );
      if (connectResult) connectResult.textContent = "Preparando um novo convite individual…";
      if (sessionNote) sessionNote.textContent = "O link anterior não está mais disponível. Estamos preparando outro automaticamente.";
    }

    function setEntryUser(user) {
      if (entryUser) entryUser.textContent = user && user.mention ? user.mention : "@usuário";
    }

    function applyExistingMember(payload) {
      if (!payload) return;
      closeExistingPanel(false);
      setEntryUser(payload.discord_user);
      if (payload.status === "peace_member") {
        var peaceMessage = payload.message || "Você já é membro da Peace. Não é necessário pedir setagem.";
        try { window.sessionStorage.setItem("peace.member.toast.v1", peaceMessage); } catch (error) { /* optional */ }
        window.location.assign("/acessar/?status=already-member");
        return;
      }

      if (payload.status === "visitor_member") {
        if (memberResult) memberResult.textContent = payload.message || "Sua entrada como Visitor foi confirmada. Continue a entrevista.";
        setStage(3, false);
        updateWizard(wizardStep, false);
        return;
      }

      if (payload.status === "verification_pending") {
        setVerificationState("pending", "Verificação pendente", payload.message || "Abra o canal #verify e conclua a verificação humana.");
        if (manualEntryNote) manualEntryNote.textContent = "Conta encontrada. Assim que você concluir o #verify, atualize o acompanhamento aqui.";
        if (refreshResult) refreshResult.textContent = "Aguardando sua verificação no #verify.";
        setStage(2, false);
        return;
      }

      setVerificationState("warning", "Cargo de entrada ausente", payload.message || "Não encontrei um cargo de entrada nesta conta.");
      if (manualEntryNote) manualEntryNote.textContent = "Conta encontrada, mas o cargo de entrada não apareceu. Abra Estou com problemas para tentar corrigir.";
      if (helpPanel) helpPanel.hidden = false;
      if (helpToggle) helpToggle.setAttribute("aria-expanded", "true");
      setStage(2, false);
    }

    function identifyExistingMember(showBusy, identityOverride) {
      var identity = identityOverride || manualEntryIdentity;
      if (!identity && existingForm) {
        var formData = new FormData(existingForm);
        identity = {
          discord_username: String(formData.get("discord_username") || "").trim(),
          discord_id: String(formData.get("discord_id") || "").replace(/\D/g, "").slice(0, 22),
          discord_profile_url: String(formData.get("discord_profile_url") || "").trim()
        };
      }
      if (!identity || !identity.discord_username) return Promise.reject(new Error("Informe seu username do Discord."));
      saveManualEntry(identity);
      if (showBusy) setButtonBusy(existingSubmit, true, "Localizando…");
      return attemptEndpoint("/api/entry/identify", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(identity)
      }, 60000)
        .then(parseEntryResponse)
        .then(function (payload) {
          applyExistingMember(payload);
          return payload;
        })
        .catch(function (error) {
          if (existingResult) existingResult.textContent = error.message || "Não foi possível encontrar sua conta agora.";
          throw error;
        })
        .finally(function () { if (showBusy) setButtonBusy(existingSubmit, false); });
    }

    function stopEntryPolling() {
      if (entryPollTimer) window.clearInterval(entryPollTimer);
      entryPollTimer = null;
    }

    function startEntryPolling() {
      if (
        entryPollTimer
        || !entrySession
        || currentStage >= 3
        || !["waiting_invite", "verification_pending", "role_missing"].includes(entrySession.status)
      ) return;
      entryPollTimer = window.setInterval(function () {
        if (document.visibilityState && document.visibilityState !== "visible") return;
        fetchEntryStatus(false).catch(function () { /* keep the current state quiet and retry on the next visible poll */ });
      }, 4000);
    }

    function stageForEntryStatus(status) {
      if (status === "verified") return 3;
      if (status === "verification_pending" || status === "role_missing") return 2;
      return 1;
    }

    function applyEntryPayload(payload) {
      if (!payload) return;

      if (isInviteRecoveryStatus(payload.status)) {
        entrySession = null;
        clearEntryToken();
        clearInviteMeta();
        stopEntryPolling();
        showInviteRecoveryState();
        return;
      }

      entrySession = payload;
      saveEntryToken(payload.session_token);
      inviteOpened = readEntryMeta(payload.session_token);
      setEntryUser(payload.discord_user);

      setInviteLinks(payload.invite_url, payload.session_token);

      if (
        payload.invite_url
        && payload.status === "waiting_invite"
        && connectResult
        && (!connectResult.textContent.trim() || /preparando|novo convite|anterior deixou/i.test(connectResult.textContent))
      ) {
        connectResult.textContent = inviteOpened
          ? "Convite aberto. Entre na Peace por ele; esta página acompanha sua entrada."
          : "Convite gerado. Abra o Discord no painel abaixo para continuar.";
      }

      if (payload.status === "verified") {
        stopEntryPolling();
        if (inviteWaiting) inviteWaiting.hidden = true;
        setVerificationState("success", "Verificação concluída", "Tudo certo. Continuando para a entrevista.");
        if (connectResult) connectResult.textContent = "Entrada e verificação confirmadas.";
        if (sessionNote) sessionNote.textContent = "Entrada confirmada. A entrevista está liberada.";
        if (refreshResult) refreshResult.textContent = "Verificação concluída. A entrevista está liberada.";
        setStage(3, false);
        return;
      }

      if (payload.status === "verification_pending") {
        setInviteWaiting("success", "Entrada identificada", "O bot confirmou sua entrada na Peace. Agora acompanhe a verificação nesta página.");
        setVerificationState("pending", "Verificação pendente", "Você já está na Peace. Abra o canal #verify, clique em Iniciar verificação e responda ao CAPTCHA.");
        if (connectResult) connectResult.textContent = "Entrada confirmada. O próximo passo está nesta página.";
        if (sessionNote) sessionNote.textContent = "Entrada identificada. Acompanhe a verificação nesta página.";
        setStage(2, false);
        startEntryPolling();
        return;
      }

      if (payload.status === "role_missing") {
        setInviteWaiting("success", "Entrada identificada", "O bot confirmou sua entrada. Estamos aguardando o cargo de verificação.");
        setVerificationState("warning", "Cargo de entrada ausente", "Não encontrei Not Verified nesta conta. Abra Estou com problemas para tentar corrigir.");
        if (connectResult) connectResult.textContent = "Entrada confirmada. O cargo de verificação precisa de atenção.";
        if (helpPanel) helpPanel.hidden = false;
        if (helpToggle) helpToggle.setAttribute("aria-expanded", "true");
        setStage(2, false);
        startEntryPolling();
        return;
      }

      setStage(stageForEntryStatus(payload.status), false);
      setInviteWaiting("pending", "Aguardando sua entrada", inviteOpened
        ? "O convite foi aberto. Assim que você aceitar, a Peace confirma sua entrada aqui."
        : "Abra o convite pelo botão acima. Assim que você aceitar, a Peace confirma sua entrada aqui.");
      if (sessionNote && payload.expires_in) sessionNote.textContent = "Convite ativo por aproximadamente " + Math.ceil(payload.expires_in / 60) + " minutos. Ele abre em uma nova guia.";
      startEntryPolling();
    }

    function parseEntryResponse(response) {
      return response.text().then(function (raw) {
        var payload = null;
        try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
        if (!payload || payload.ok !== true) throw friendlyError(payload, response.status, "Não foi possível acompanhar a entrada.");
        return payload;
      });
    }

    function startEntrySession(forceNew) {
      if (entryStartPromise) return entryStartPromise;
      var replacing = Boolean(forceNew);
      if (replacing) {
        clearEntryToken();
        clearInviteMeta();
        entrySession = null;
        stopEntryPolling();
        showInviteRecoveryState();
      }
      var token = replacing ? "" : readEntryToken();
      var requestBody = token ? { session_token: token } : {};
      var requestPromise = attemptEndpoint("/api/entry/start", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(requestBody) }, 60000)
        .then(parseEntryResponse)
        .then(function (payload) { applyEntryPayload(payload); return payload; });
      entryStartPromise = requestPromise;
      requestPromise.then(function () {
        if (entryStartPromise === requestPromise) entryStartPromise = null;
      }, function () {
        if (entryStartPromise === requestPromise) entryStartPromise = null;
      });
      return requestPromise;
    }

    function recoverEntrySession() {
      if (entryRecoveryPromise) return entryRecoveryPromise;
      showInviteRecoveryState();
      setStage(1, false);
      var requestPromise = startEntrySession(true)
        .catch(function (error) {
          setInviteLinks("", "", false);
          if (connectButton) {
            connectButton.hidden = false;
            setButtonLabel(connectButton, "Tentar gerar convite");
          }
          if (connectResult) connectResult.textContent = error.message || "Não foi possível gerar um novo convite agora.";
          throw error;
        });
      entryRecoveryPromise = requestPromise;
      requestPromise.then(function () {
        if (entryRecoveryPromise === requestPromise) entryRecoveryPromise = null;
      }, function () {
        if (entryRecoveryPromise === requestPromise) entryRecoveryPromise = null;
      });
      return requestPromise;
    }

    function maybeRecoverEntrySession(payload) {
      return isInviteRecoveryStatus(payload && payload.status)
        ? recoverEntrySession()
        : Promise.resolve(payload);
    }

    function fetchEntryStatus(showBusy) {
      var token = (entrySession && entrySession.session_token) || readEntryToken();
      if (!token) return Promise.resolve(null);
      if (showBusy) setButtonBusy(refreshButton, true, "Atualizando…");
      if (entryStatusPromise) {
        return entryStatusPromise.finally(function () {
          if (showBusy) setButtonBusy(refreshButton, false);
        });
      }

      var requestPromise = attemptEndpoint("/api/entry/status", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ session_token: token }) }, 60000)
        .then(parseEntryResponse)
        .then(function (payload) {
          applyEntryPayload(payload);
          if (refreshResult && payload.status === "verification_pending") refreshResult.textContent = "Ainda aguardando a conclusão no #verify.";
          return maybeRecoverEntrySession(payload);
        })
        .catch(function (error) {
          if (error.code === "ENTRY_SESSION_NOT_FOUND" || error.code === "INVALID_SESSION") {
            return recoverEntrySession();
          }
          if (refreshResult) refreshResult.textContent = error.message || "Não foi possível atualizar agora.";
          throw error;
        });
      entryStatusPromise = requestPromise;
      return requestPromise.finally(function () {
          if (showBusy) setButtonBusy(refreshButton, false);
        if (entryStatusPromise === requestPromise) entryStatusPromise = null;
        });
    }

    function saveDraft() {
      if (!wizard) return;
      var draft = {
        version: 2,
        stage: currentStage,
        wizardStep: wizardStep,
        values: {
          nickname: getField("nickname") ? getField("nickname").value : "",
          discovery: getField("discovery") ? getField("discovery").value : "",
          motivation: getField("motivation") ? getField("motivation").value : ""
        },
        terms: {
          city: Boolean(getField("terms-city") && getField("terms-city").checked),
          discord: Boolean(getField("terms-discord") && getField("terms-discord").checked),
          conduct: Boolean(getField("terms-conduct") && getField("terms-conduct").checked)
        },
        savedAt: Date.now()
      };

      try {
        window.localStorage.setItem(storageKey, JSON.stringify(draft));
      } catch (error) {
        // Local storage is optional; the form remains usable without it.
      }
    }

    function setStage(stage, isPreview) {
      var previousStage = currentStage;
      currentStage = Math.min(4, Math.max(1, Number(stage) || 1));
      if (stageContext) {
        stageContext.textContent = ["Entrada", "Verificação", "Entrevista", "Revisão"][currentStage - 1] || "Entrada";
      }
      stages.forEach(function (item) {
        var active = Number(item.dataset.entryStage) === currentStage;
        item.hidden = !active;
        item.classList.toggle("is-active", active);
      });
      stageButtons.forEach(function (button) {
        var stageNumber = Number(button.dataset.stagePreview);
        var active = stageNumber === currentStage;
        button.classList.toggle("is-current", active);
        button.classList.toggle("is-preview", Boolean(isPreview && active && currentStage > 1));
        button.disabled = stageNumber > currentStage;
        button.setAttribute("aria-disabled", String(stageNumber > currentStage));
        if (active) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
      });
      if (!restoring && previousStage !== currentStage) {
        var activeStage = stages.find(function (item) { return Number(item.dataset.entryStage) === currentStage; });
        var activeHeading = activeStage && activeStage.querySelector("h1, h2");
        if (activeHeading && typeof activeHeading.focus === "function") activeHeading.focus({ preventScroll: true });
      }
      if (!restoring) saveDraft();
    }

    stageButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        if (button.disabled) return;
        setStage(Number(button.dataset.stagePreview), true);
      });
    });

    if (connectButton) {
      connectButton.addEventListener("click", function () {
        if (connectButton.dataset.inviteUrl) {
          var existingPopup = openEntryInvite(connectButton.dataset.inviteUrl, connectButton.dataset.sessionToken || (entrySession && entrySession.session_token));
          if (connectResult) connectResult.textContent = existingPopup
            ? "Convite aberto. Entre na Peace por ele e volte para acompanhar."
            : "Permita novas guias no navegador para abrir o convite.";
          setInviteWaiting("pending", "Aguardando sua entrada", "Entre no servidor pelo convite e volte quando terminar.");
          startEntryPolling();
          return;
        }
        var reservedPopup = reserveEntryInviteWindow();
        if (connectResult) connectResult.textContent = "Preparando seu convite…";
        setButtonBusy(connectButton, true, "Gerando convite…");
        startEntrySession().then(maybeRecoverEntrySession).then(function (payload) {
          var popup = openEntryInvite(payload.invite_url, payload.session_token, reservedPopup);
          setButtonBusy(connectButton, false);
          if (connectResult) connectResult.textContent = popup ? "Convite aberto. Entre na Peace por ele e volte para acompanhar." : "Convite pronto. Abra o Discord pelo botão acima.";
          startEntryPolling();
        }).catch(function (error) {
          if (reservedPopup && !reservedPopup.closed) {
            try { reservedPopup.close(); } catch (closeError) { /* browser-controlled */ }
          }
          setButtonBusy(connectButton, false);
          setInviteLinks("", "", false);
          setButtonLabel(connectButton, "Tentar novamente");
          if (connectResult) connectResult.textContent = error.message || "Não foi possível gerar o convite agora.";
        });
      });
    }

    function closeExistingPanel(restoreFocus) {
      if (!existingPanel || existingPanel.hidden) return;
      existingPanel.hidden = true;
      document.body.classList.remove("dialog-open");
      document.querySelectorAll(".flow-header, .flow-main, .flow-footer").forEach(function (background) { background.inert = false; });
      if (existingToggle) existingToggle.setAttribute("aria-expanded", "false");
      if (restoreFocus && existingPreviousFocus && typeof existingPreviousFocus.focus === "function") existingPreviousFocus.focus();
      existingPreviousFocus = null;
    }

    if (existingToggle && existingPanel) {
      existingToggle.addEventListener("click", function () {
        existingPreviousFocus = document.activeElement;
        existingPanel.hidden = false;
        document.body.classList.add("dialog-open");
        document.querySelectorAll(".flow-header, .flow-main, .flow-footer").forEach(function (background) { background.inert = true; });
        existingToggle.setAttribute("aria-expanded", "true");
        if (existingClose) existingClose.focus();
        else {
          var usernameField = existingPanel.querySelector('[name="discord_username"]');
          if (usernameField) usernameField.focus();
        }
      });
      if (existingClose) existingClose.addEventListener("click", function () { closeExistingPanel(true); });
      existingPanel.addEventListener("click", function (event) {
        if (event.target === existingPanel) closeExistingPanel(true);
      });
      document.addEventListener("keydown", function (event) {
        if (!existingPanel || existingPanel.hidden) return;
        if (event.key === "Escape") {
          closeExistingPanel(true);
          return;
        }
        if (event.key !== "Tab") return;
        var focusable = Array.prototype.slice.call(existingPanel.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex=\"-1\"])"))
          .filter(function (node) { return node.offsetParent !== null; });
        if (!focusable.length) return;
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      });
    }

    if (existingForm) existingForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!existingForm.checkValidity()) {
        existingForm.reportValidity();
        return;
      }
      identifyExistingMember(true).catch(function () { /* message is visible in the live region */ });
    });

    if (inviteLink) inviteLink.addEventListener("click", function (event) {
      var url = inviteLink.getAttribute("href");
      var popup = openEntryInvite(url, inviteLink.dataset.sessionToken || (entrySession && entrySession.session_token) || readEntryToken());
      if (!popup) {
        markInviteOpened(inviteLink.dataset.sessionToken || (entrySession && entrySession.session_token) || readEntryToken());
        setInviteWaiting("pending", "Aguardando sua entrada", "Se o navegador bloqueou a janela, use este link novamente para abrir o mesmo convite.");
        if (connectResult) connectResult.textContent = "A janela foi bloqueada. Use o link do convite novamente para abrir a mesma sessão.";
        startEntryPolling();
        return;
      }
      event.preventDefault();
      setInviteWaiting("pending", "Aguardando sua entrada", "O convite foi aberto. Assim que você aceitar, a Peace confirma sua entrada aqui.");
      if (connectResult) connectResult.textContent = "Convite aberto em uma única janela. Volte para acompanhar a confirmação.";
      startEntryPolling();
    });

    if (refreshButton) {
      refreshButton.addEventListener("click", function () {
        if (refreshResult) refreshResult.textContent = "";
        if (!entrySession && manualEntryIdentity) {
          identifyExistingMember(true).catch(function () { /* message is visible in the live region */ });
          return;
        }
        fetchEntryStatus(true).catch(function () { /* message is visible in the live region */ });
      });
    }

    if (helpToggle && helpPanel) {
      helpToggle.addEventListener("click", function () {
        var open = helpPanel.hidden;
        helpPanel.hidden = !open;
        helpToggle.setAttribute("aria-expanded", String(open));
        if (open) {
          var firstField = helpPanel.querySelector("input");
          if (firstField) firstField.focus();
        }
      });
      var helpClose = helpPanel.querySelector("[data-entry-help-close]");
      if (helpClose) helpClose.addEventListener("click", function () {
        helpPanel.hidden = true;
        helpToggle.setAttribute("aria-expanded", "false");
        helpToggle.focus();
      });
    }

    if (repairForm) repairForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var token = (entrySession && entrySession.session_token) || readEntryToken();
      if (!token) {
        if (repairResult) repairResult.textContent = "Conecte seu Discord primeiro para liberar o diagnóstico.";
        return;
      }
      var formData = new FormData(repairForm);
      var payload = {
        session_token: token,
        discord_username: String(formData.get("discord_username") || "").trim(),
        discord_id: String(formData.get("discord_id") || "").replace(/\D/g, "").slice(0, 22),
        discord_profile_url: String(formData.get("discord_profile_url") || "").trim()
      };
      if (repairResult) repairResult.textContent = "";
      setButtonBusy(repairSubmit, true, "Verificando…");
      attemptEndpoint("/api/entry/repair", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) }, 60000)
        .then(parseEntryResponse)
        .then(function (response) {
          applyEntryPayload(response);
          if (repairResult) repairResult.textContent = response.message || "Diagnóstico concluído. Acompanhe o #verify.";
        })
        .catch(function (error) {
          if (repairResult) repairResult.textContent = error.message || "Não foi possível concluir o diagnóstico agora.";
        })
        .finally(function () { setButtonBusy(repairSubmit, false); });
    });

    function updateWizard(step, moveFocus) {
      if (!wizard) return;
      wizardStep = Math.min(4, Math.max(1, Number(step) || 1));
      wizardPanels.forEach(function (panel) {
        var active = Number(panel.dataset.wizardPanel) === wizardStep;
        panel.hidden = !active;
        panel.classList.toggle("is-active", active);
      });
      if (wizardLabel) wizardLabel.textContent = "Passo " + wizardStep + " de 4";
      if (wizardPercent) wizardPercent.textContent = String(Math.round((wizardStep / 4) * 100)) + "%";
      if (wizardTrack) wizardTrack.style.width = String((wizardStep / 4) * 100) + "%";
      if (wizardBack) wizardBack.hidden = wizardStep === 1;
      if (wizardNext) wizardNext.hidden = wizardStep === 4;
      if (moveFocus) {
        var heading = wizard.querySelector('[data-wizard-panel="' + wizardStep + '"] h3');
        if (heading) heading.focus({ preventScroll: true });
      }
      if (!restoring) saveDraft();
    }

    function updateReview() {
      var nickname = wizard.querySelector('[name="nickname"]');
      var discovery = wizard.querySelector('[name="discovery"]');
      var motivation = wizard.querySelector('[name="motivation"]');
      var reviewNickname = wizard.querySelector("[data-review-nickname]");
      var reviewDiscovery = wizard.querySelector("[data-review-discovery]");
      var reviewMotivation = wizard.querySelector("[data-review-motivation]");
      if (reviewNickname) reviewNickname.textContent = nickname && nickname.value.trim() ? nickname.value.trim() : "Ainda não preenchido.";
      if (reviewDiscovery) reviewDiscovery.textContent = discovery && discovery.value.trim() ? discovery.value.trim() : "Ainda não preenchido.";
      if (reviewMotivation) reviewMotivation.textContent = motivation && motivation.value.trim() ? motivation.value.trim().slice(0, 140) + (motivation.value.trim().length > 140 ? "…" : "") : "Ainda não preenchida.";
    }

    if (!wizard) {
      setStage(currentStage, false);
      restoring = false;
      return;
    }

    wizard.querySelectorAll("[data-character-count-for]").forEach(function (counter) {
      var field = wizard.querySelector('[name="' + counter.dataset.characterCountFor + '"]');
      if (!field) return;
      function syncCounter() { counter.textContent = String(field.value.length); }
      field.addEventListener("input", syncCounter);
      syncCounter();
    });

    wizard.querySelectorAll("input, textarea").forEach(function (field) {
      field.addEventListener("input", function () { saveDraft(); });
      field.addEventListener("change", function () { saveDraft(); });
    });

    if (wizardNext) wizardNext.addEventListener("click", function () {
      if (wizardStep < 4) {
        var currentPanel = wizard.querySelector('[data-wizard-panel="' + wizardStep + '"]');
        var invalidField = currentPanel && Array.prototype.slice.call(currentPanel.querySelectorAll("input, textarea")).find(function (field) {
          return !field.checkValidity();
        });
        if (invalidField) {
          invalidField.reportValidity();
          return;
        }
        if (wizardStep === 3) updateReview();
        updateWizard(wizardStep + 1, true);
      }
    });
    if (wizardBack) wizardBack.addEventListener("click", function () {
      if (wizardStep > 1) updateWizard(wizardStep - 1, true);
    });

    var submitButton = wizard.querySelector("[data-application-submit]");
    var result = wizard.querySelector("[data-application-result]");
    if (submitButton) submitButton.addEventListener("click", function () {
      var missingTerm = Array.prototype.slice.call(wizard.querySelectorAll('[name^="terms-"]')).find(function (term) {
        return !term.checked;
      });
      if (missingTerm) {
        if (result) result.textContent = "Aceite os três termos para enviar.";
        missingTerm.focus();
        return;
      }
      saveDraft();
      if (result) result.textContent = "Candidatura pronta para revisão.";
      setStage(4, false);
    });

    window.addEventListener("pagehide", function () { saveDraft(); });

    var draft = readDraft();
    var draftValues = draft && draft.values ? draft.values : {};
    var draftTerms = draft && draft.terms ? draft.terms : {};
    if (typeof draftValues.nickname === "string") getField("nickname").value = draftValues.nickname;
    if (typeof draftValues.discovery === "string") getField("discovery").value = draftValues.discovery;
    if (typeof draftValues.motivation === "string") getField("motivation").value = draftValues.motivation;
    if (getField("terms-city")) getField("terms-city").checked = draftTerms.city === true;
    if (getField("terms-discord")) getField("terms-discord").checked = draftTerms.discord === true;
    if (getField("terms-conduct")) getField("terms-conduct").checked = draftTerms.conduct === true;
    wizard.querySelectorAll("[data-character-count-for]").forEach(function (counter) {
      var field = wizard.querySelector('[name="' + counter.dataset.characterCountFor + '"]');
      if (field) counter.textContent = String(field.value.length);
    });
    updateReview();
    updateWizard(draft && draft.wizardStep ? draft.wizardStep : 1, false);
    setStage(draft && draft.stage ? draft.stage : 1, false);
    restoring = false;

    manualEntryIdentity = readManualEntry();
    setManualEntryFields(manualEntryIdentity);

    if (readEntryToken()) {
      startEntrySession().then(maybeRecoverEntrySession).catch(function () {
        if (sessionNote) sessionNote.textContent = "Não consegui retomar o convite agora. Tente abrir um novo link.";
      });
    } else if (manualEntryIdentity) {
      identifyExistingMember(false, manualEntryIdentity).catch(function () { /* draft remains available for a manual retry */ });
    }

    function refreshEntryAfterReturn() {
      if (document.visibilityState && document.visibilityState !== "visible") return;
      if ((entrySession && entrySession.session_token) || readEntryToken()) {
        fetchEntryStatus(false).catch(function () { /* the current state remains visible */ });
      }
    }

    window.addEventListener("focus", refreshEntryAfterReturn);
    window.addEventListener("pageshow", refreshEntryAfterReturn);
    document.addEventListener("visibilitychange", refreshEntryAfterReturn);
  }

  function initLogin() {
    if (body.dataset.page !== "login") return;

    var requestForm = document.querySelector("[data-login-request]");
    var verifyForm = document.querySelector("[data-login-verify]");
    var status = document.querySelector("[data-login-status]");
    var requestButton = requestForm && requestForm.querySelector("button[type=submit]");
    var verifyButton = verifyForm && verifyForm.querySelector("button[type=submit]");
    var result = verifyForm && verifyForm.querySelector("[data-login-result]");
    var idInput = requestForm && requestForm.querySelector('[name="peace-id"]');
    var keepConnected = requestForm && requestForm.querySelector('[name="keep-connected"]');
    var codeInput = verifyForm && verifyForm.querySelector('[name="access-code"]');
    var requestedPeaceId = "";

    function parseLoginResponse(response) {
      return response.text().then(function (raw) {
        var payload = null;
        try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
        if (!payload || payload.ok !== true) throw friendlyError(payload, response.status, "Não foi possível continuar o acesso.");
        return payload;
      });
    }

    function syncCodeCells() {
      if (!codeInput) return;
      var value = codeInput.value.replace(/\D/g, "").slice(0, 6);
      codeInput.value = value;
      document.querySelectorAll("[data-code-cell]").forEach(function (cell, index) {
        cell.textContent = value.charAt(index) || "";
      });
    }

    if (idInput) {
      idInput.addEventListener("input", function () {
        idInput.value = idInput.value.replace(/\D/g, "").slice(0, 19);
        idInput.setCustomValidity("");
      });
    }

    if (requestForm) requestForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!idInput || !/^\d{1,19}$/.test(idInput.value.trim())) {
        if (idInput) { idInput.setCustomValidity("Use somente números, com até 19 dígitos."); idInput.reportValidity(); idInput.setCustomValidity(""); }
        return;
      }
      requestedPeaceId = idInput.value.trim();
      if (result) result.textContent = "";
      setButtonBusy(requestButton, true, "Enviando código…");
      attemptEndpoint("/api/member/auth/request", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ peace_id: requestedPeaceId })
      }, 60000)
        .then(parseLoginResponse)
        .then(function (payload) {
          var memberName = payload.member_name ? " para " + payload.member_name : "";
          setStatusMessage(status, "Código enviado", "Enviamos um código de 6 números para sua DM no Discord" + memberName + ".", "success");
          if (verifyForm) verifyForm.hidden = false;
          if (codeInput) codeInput.focus();
        })
        .catch(function (error) {
          setStatusMessage(status, "Não foi possível continuar", error.message || "Tente novamente.", "warning");
        })
        .finally(function () { setButtonBusy(requestButton, false); });
    });

    if (codeInput) {
      codeInput.addEventListener("input", syncCodeCells);
      codeInput.addEventListener("paste", function () { window.setTimeout(syncCodeCells, 0); });
      syncCodeCells();
    }

    if (verifyForm) verifyForm.addEventListener("submit", function (event) {
      event.preventDefault();
      syncCodeCells();
      if (!/^\d{6}$/.test(codeInput ? codeInput.value : "") || !/^\d{1,19}$/.test(requestedPeaceId)) {
        if (codeInput) { codeInput.setCustomValidity("Digite os 6 números recebidos no Discord."); codeInput.reportValidity(); codeInput.setCustomValidity(""); }
        return;
      }
      setButtonBusy(verifyButton, true, "Validando…");
      if (result) result.textContent = "";
      attemptEndpoint("/api/member/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ peace_id: requestedPeaceId, code: codeInput.value })
      }, 60000)
        .then(parseLoginResponse)
        .then(function (payload) {
          storeMemberSessionToken(payload.session.token, Boolean(keepConnected && keepConnected.checked));
          setStatusMessage(status, "Acesso confirmado", "Abrindo sua área da Peace…", "success");
          window.setTimeout(function () { window.location.assign("/area/"); }, 260);
        })
        .catch(function (error) {
          if (result) result.textContent = error.message || "Não foi possível validar o código.";
        })
        .finally(function () { setButtonBusy(verifyButton, false); });
    });

    var params = new URLSearchParams(window.location.search);
    if (params.get("status") === "already-member") {
      setStatusMessage(status, "Você já é membro", "Não é necessário pedir setagem. Entre com seu ID Peace para continuar.", "success");
    }
  }

  function initMemberArea() {
    if (body.dataset.page !== "member") return;

    var gate = document.querySelector("[data-member-gate]");
    var authenticated = document.querySelector("[data-member-authenticated]");
    var authSkeleton = document.querySelector("[data-member-auth-skeleton]");
    var authContent = authenticated && authenticated.querySelector("[data-member-auth-content]");
    var memberName = authenticated && authenticated.querySelector("[data-member-name]");
    var memberId = authenticated && authenticated.querySelector("[data-member-id]");
    var logoutButton = authenticated && authenticated.querySelector("[data-member-logout]");

    function loadMemberSession() {
      var token = readMemberSessionToken();
      if (!token || !authenticated) return;

      authenticated.hidden = false;
      authenticated.classList.add("is-visible");
      if (authSkeleton) authSkeleton.hidden = false;
      if (authContent) authContent.hidden = true;
      attemptEndpoint("/api/member/auth/session", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: "Bearer " + token },
        body: "{}"
      }, 60000)
        .then(function (response) {
          return response.text().then(function (raw) {
            var payload = null;
            try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
            if (!payload || payload.ok !== true) throw friendlyError(payload, response.status, "Não foi possível validar sua sessão.");
            return payload;
          });
        })
        .then(function (payload) {
          if (gate) gate.hidden = true;
          if (authSkeleton) authSkeleton.hidden = true;
          if (authContent) authContent.hidden = false;
          if (memberName) memberName.textContent = payload.session.member_name || "membro.";
          if (memberId) memberId.textContent = payload.session.peace_id === null || payload.session.peace_id === undefined
            ? "—"
            : String(payload.session.peace_id);
        })
        .catch(function () {
          clearMemberSessionToken();
          if (authenticated) authenticated.hidden = true;
        });
    }

    if (logoutButton) logoutButton.addEventListener("click", function () {
      clearMemberSessionToken();
      if (authenticated) authenticated.hidden = true;
      if (gate) gate.hidden = false;
    });
    loadMemberSession();
  }

  initPublicMedia();
  initMemberArea();
  initCandidature();
  initLogin();
})();
