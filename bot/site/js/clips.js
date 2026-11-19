(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;

  function initClips(root) {
  var scope = root && typeof root.querySelector === "function" ? root : document;
  var list = scope.querySelector("[data-clips-list]");
  var empty = scope.querySelector("[data-clips-empty]");
  var status = scope.querySelector("[data-clips-status]");
  var form = scope.querySelector("[data-clips-search]");
  var input = form && form.querySelector("[data-clips-query]");
  var submit = form && form.querySelector("[data-clips-submit]");
  var retry = scope.querySelector("[data-clips-retry]");
  var filterButtons = Array.prototype.slice.call(scope.querySelectorAll("[data-clips-filter]"));
  var loading = false;
  var activeFilter = "all";
  var currentItems = [];
  var currentViewerId = String(global.PeaceSite && global.PeaceSite.body && global.PeaceSite.body.dataset.discordId || "");
  var videoObserver = null;

  function isActiveView() {
    var view = form && form.closest && form.closest("[data-member-view]");
    return !view || !view.hidden;
  }

  if (!list) return;
  if (list.dataset.clipsReady === "true") {
    if (typeof list.__peaceClipsLoad === "function") list.__peaceClipsLoad();
    return;
  }
  list.dataset.clipsReady = "true";

  function node(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (typeof text === "string") element.textContent = text;
    return element;
  }

  function cleanText(value) {
    return String(value || "")
      .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
      .replace(/\[([^\]]+)\]\(([^)]*)\)/g, function (match, label, url) {
        return String(url || "").trim() ? label : "";
      })
      .replace(/(\*\*|__)(.*?)\1/g, "$2")
      .replace(/[\*_~]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function titleFor(item) {
    return cleanText(item && (item.caption || item.provider_title || item.provider_author))
      || "Clip compartilhado na comunidade";
  }

  function dateFor(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Data não informada";
    return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).replace(/\./g, "");
  }

  function safeUrl(value) {
    var raw = String(value || "").trim();
    if (!raw) return "";
    try {
      var parsed = new URL(raw, window.location.href);
      var hosts = [
        "cdn.discordapp.com", "media.discordapp.net", "images-ext-1.discordapp.net",
        "cdn.medal.tv", "medal.tv", "streamable.com", "youtube.com",
        "www.youtube.com", "youtube-nocookie.com", "youtu.be", "twitch.tv",
        "clips.twitch.tv", "gyazo.com", "i.gyazo.com", "imgur.com",
        "i.imgur.com", "outplayed.tv", "tiktok.com", "www.tiktok.com",
        "vt.tiktok.com", "vm.tiktok.com"
      ];
      if (parsed.protocol !== "https:" || hosts.indexOf(parsed.hostname.toLowerCase()) < 0) return "";
      return parsed.href;
    } catch (error) {
      return "";
    }
  }

  function mediaType(item) {
    // TikTok player links can expire or require a provider session inside an
    // iframe. A truthful source card is more useful than a broken player and
    // keeps the public feed free of provider-console noise.
    if (item && String(item.provider || "").toLowerCase() === "tiktok") return "source";
    if (item && item.kind === "embed" && item.embed_url) return "embed";
    if (item && item.kind === "direct" && item.type === "video") return "video";
    if (item && item.kind === "direct" && item.type === "image") return "image";
    return "source";
  }

  function mediaVisual(item) {
    var visual = node("div", "clip-card-visual");
    var kind = mediaType(item);
    var url = safeUrl(item && item.url);
    var thumbnail = safeUrl(item && item.thumbnail_url);
    if (kind === "embed") {
      var iframe = node("iframe", "clip-card-embed");
      iframe.src = safeUrl(item.embed_url);
      iframe.loading = "lazy";
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      iframe.allowFullscreen = true;
      iframe.title = titleFor(item);
      visual.appendChild(iframe);
    } else if (kind === "video" && url) {
      var placeholder = node("div", "clip-card-video-placeholder");
      placeholder.dataset.videoUrl = url;
      placeholder.dataset.videoTitle = titleFor(item);
      if (thumbnail) placeholder.dataset.videoPoster = thumbnail;
      placeholder.setAttribute("role", "img");
      placeholder.setAttribute("aria-label", "Vídeo: " + titleFor(item));
      visual.appendChild(placeholder);
    } else if (kind === "image" && url) {
      var image = node("img", "clip-card-image");
      image.src = url;
      image.alt = titleFor(item);
      image.width = 640;
      image.height = 360;
      image.loading = "lazy";
      image.decoding = "async";
      visual.appendChild(image);
    } else {
      if (thumbnail) {
        var preview = node("img", "clip-card-image");
        preview.src = thumbnail;
        preview.alt = "";
        preview.width = 640;
        preview.height = 360;
        preview.loading = "lazy";
        preview.decoding = "async";
        visual.appendChild(preview);
      }
      var fallback = node("div", "clip-card-source");
      fallback.appendChild(node("span", "clip-card-source-provider", item && item.provider || "Mídia"));
      fallback.appendChild(node("strong", "", titleFor(item)));
      var source = safeUrl(item && (item.fallback_url || item.source_url || item.url));
      if (source) {
        var sourceLink = node("a", "text-link", "Abrir origem ↗");
        sourceLink.href = source;
        sourceLink.target = "_blank";
        sourceLink.rel = "noopener noreferrer";
        fallback.appendChild(sourceLink);
      }
      visual.appendChild(fallback);
    }
    var badge = node("span", "clip-card-badge", item && item.provider || "Clip");
    badge.setAttribute("aria-hidden", "true");
    visual.appendChild(badge);
    return visual;
  }

  function makeCard(item) {
    var card = node("article", "clip-card");
    card.setAttribute("role", "listitem");
    card.dataset.mediaId = String(item.id || "");
    card.appendChild(mediaVisual(item));
    var copy = node("div", "clip-card-copy");
    var author = item.author || {};
    var authorRow = node("div", "clip-card-author");
    var avatar = node("span", "clip-card-author-avatar");
    var avatarUrl = safeUrl(author.avatar_url);
    if (avatarUrl) {
      var avatarImage = node("img", "", "");
      avatarImage.src = avatarUrl;
      avatarImage.alt = "";
      avatarImage.width = 32;
      avatarImage.height = 32;
      avatarImage.loading = "lazy";
      avatar.appendChild(avatarImage);
    } else {
      avatar.textContent = String(author.display_name || "M").charAt(0).toUpperCase();
    }
    authorRow.appendChild(avatar);
    var authorCopy = node("span", "clip-card-author-copy");
    authorCopy.appendChild(node("strong", "", author.display_name || author.username || "Membro"));
    authorCopy.appendChild(node("small", "", dateFor(item.created_at) + " · " + (item.provider || "Mídia")));
    authorRow.appendChild(authorCopy);
    copy.appendChild(authorRow);
    copy.appendChild(node("h2", "clip-card-title", titleFor(item)));
    if (item.provider_description && item.provider_description !== item.caption) {
      copy.appendChild(node("p", "clip-card-description", cleanText(item.provider_description)));
    }

    card.appendChild(copy);
    return card;
  }

  function hydrateVideoCard(card) {
    var placeholder = card && card.querySelector("[data-video-url]");
    if (!placeholder || placeholder.dataset.hydrated === "true") return;
    placeholder.dataset.hydrated = "true";
    var video = node("video", "clip-card-video");
    video.src = placeholder.dataset.videoUrl;
    video.controls = true;
    video.preload = "metadata";
    video.playsInline = true;
    if (placeholder.dataset.videoPoster) video.poster = placeholder.dataset.videoPoster;
    video.setAttribute("aria-label", "Reproduzir " + (placeholder.dataset.videoTitle || "clipe"));
    placeholder.replaceWith(video);
  }

  function observeVideoCards() {
    if (videoObserver) videoObserver.disconnect();
    var cards = Array.prototype.slice.call(list.querySelectorAll(".clip-card"));
    if (!cards.length) return;
    if (typeof IntersectionObserver !== "function") {
      cards.forEach(hydrateVideoCard);
      return;
    }
    videoObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        hydrateVideoCard(entry.target);
        videoObserver.unobserve(entry.target);
      });
    }, { rootMargin: "280px 0px" });
    cards.forEach(function (card) {
      if (card.querySelector("[data-video-url]")) videoObserver.observe(card);
    });
  }

  function renderSkeleton() {
    if (!list.querySelector(".clip-card")) {
      list.replaceChildren();
      for (var index = 0; index < 3; index += 1) {
        var skeleton = node("article", "clip-skeleton");
        skeleton.setAttribute("aria-hidden", "true");
        skeleton.appendChild(node("span", "clip-skeleton-visual"));
        skeleton.appendChild(node("span", "clip-skeleton-line"));
        skeleton.appendChild(node("span", "clip-skeleton-line clip-skeleton-line--short"));
        list.appendChild(skeleton);
      }
    } else {
      list.classList.add("is-refreshing");
    }
    list.setAttribute("aria-busy", "true");
    if (empty) empty.hidden = true;
    if (retry) retry.hidden = true;
  }

  function render(payload) {
    currentItems = Array.isArray(payload.clips) ? payload.clips.slice() : [];
    var items = currentItems.slice();
    if (activeFilter === "mine") items = items.filter(function (item) { return currentViewerId && item && item.author && String(item.author.discord_id || "") === currentViewerId; });
    if (activeFilter === "engagement") items.sort(function (a, b) { return Number((b && b.engagement) || 0) - Number((a && a.engagement) || 0); });
    if (activeFilter === "least_engagement") items.sort(function (a, b) { return Number((a && a.engagement) || 0) - Number((b && b.engagement) || 0); });
    if (activeFilter === "recent") items.sort(function (a, b) { return new Date(b && b.created_at || 0).getTime() - new Date(a && a.created_at || 0).getTime(); });
    if (activeFilter === "oldest") items.sort(function (a, b) { return new Date(a && a.created_at || 0).getTime() - new Date(b && b.created_at || 0).getTime(); });
    list.replaceChildren();
    list.classList.remove("is-refreshing");
    list.setAttribute("aria-busy", "false");
    if (retry) retry.hidden = true;
    if (!items.length) {
      if (empty) {
        empty.hidden = false;
        empty.textContent = payload.source && payload.source.state === "unavailable"
          ? "A fonte de clipes está indisponível agora. Tente novamente em instantes."
          : payload.total === 0 && input && input.value.trim()
            ? "Nenhum clipe corresponde à sua busca."
            : "Ainda não há clipes publicados pela comunidade.";
      }
    } else {
      if (empty) empty.hidden = true;
      items.forEach(function (item) { list.appendChild(makeCard(item)); });
      observeVideoCards();
    }
    var total = Number(payload.total || items.length);
    if (status) status.textContent = total
      ? total + (total === 1 ? " clip encontrado." : " clipes encontrados.") + (payload.updated_at ? " Fonte atualizada." : "")
      : "A busca está pronta.";
    if (typeof window.CustomEvent === "function") {
      window.dispatchEvent(new CustomEvent("peace:clips-loaded", { detail: { count: total } }));
    }
  }

  function fallbackFromMedia(query) {
    return site.attemptEndpoint("/api/media", { headers: { Accept: "application/json" } }, 15000)
      .then(function (response) { return response.json(); })
      .then(function (media) {
        var items = Array.isArray(media && media.clips) ? media.clips : [];
        var term = cleanText(query || "").toLowerCase();
        if (term) {
          items = items.filter(function (item) {
            var author = item && item.author ? item.author : {};
            var haystack = [
              item && item.caption,
              item && item.provider_title,
              item && item.provider_description,
              item && item.provider,
              item && item.url,
              author.display_name,
              author.username
            ].map(cleanText).join(" ").toLowerCase();
            return haystack.indexOf(term) >= 0;
          });
        }
        return {
          ok: true,
          clips: items,
          total: items.length,
          updated_at: media && media.updated_at,
          source: media && media.sources && media.sources.clips
            ? media.sources.clips
            : { state: "ready", available: true, stale: false },
          fallback: "media"
        };
      });
  }

  function requestClips(query) {
    var params = new URLSearchParams();
    params.set("limit", "60");
    if (query) params.set("q", query);
    return site.attemptEndpoint("/api/clips?" + params.toString(), { headers: { Accept: "application/json" } }, 15000)
      .then(function (response) { return response.json(); })
      .catch(function (error) {
        // Older/local proxies expose the bounded media contract before the
        // dedicated clips route. Keep the page usable while that route is
        // being rolled out, but only fall back for a confirmed 404.
        if (error && Number(error.status) === 404) return fallbackFromMedia(query);
        throw error;
      });
  }

  function load() {
    if (!isActiveView()) return;
    if (loading) return;
    loading = true;
    var hadCards = Boolean(list.querySelector(".clip-card"));
    renderSkeleton();
    if (status) status.textContent = "Carregando clipes…";
    if (submit) submit.disabled = true;
    var query = input ? input.value.trim() : "";
    if (!currentViewerId && typeof site.getDiscordSession === "function") {
      site.getDiscordSession().then(function (session) {
        currentViewerId = String(session && session.identity && session.identity.discord_id || "");
        if (activeFilter === "mine" && currentItems.length) render({ clips: currentItems, total: currentItems.length, source: { state: "ready" } });
      }).catch(function () {});
    }
    requestClips(query)
      .then(function (payload) {
        if (!payload || payload.ok !== true) throw new Error("Não consegui carregar os clipes.");
        render(payload);
      })
      .catch(function (error) {
        list.classList.remove("is-refreshing");
        if (!hadCards) list.replaceChildren();
        list.setAttribute("aria-busy", "false");
        if (empty) {
          empty.hidden = hadCards;
          empty.textContent = hadCards
            ? "Não foi possível atualizar. A lista anterior continua visível."
            : error.message || "Não consegui carregar os clipes agora.";
        }
        if (retry) retry.hidden = false;
        if (status) status.textContent = hadCards ? "Atualização indisponível." : "Tente novamente em instantes.";
        if (typeof window.CustomEvent === "function") {
          window.dispatchEvent(new CustomEvent("peace:clips-loaded", { detail: { count: hadCards ? list.querySelectorAll(".clip-card").length : 0 } }));
        }
      })
      .finally(function () {
        loading = false;
        if (submit) submit.disabled = false;
      });
  }

  list.__peaceClipsLoad = load;

  if (form) form.addEventListener("submit", function (event) {
    if (!isActiveView()) return;
    event.preventDefault();
    var query = input ? input.value.trim() : "";
    var url = new URL(window.location.href);
    if (site.body.dataset.page === "member") {
      url.pathname = "/area/";
      url.searchParams.set("view", "clips");
    }
    if (query) url.searchParams.set("q", query);
    else url.searchParams.delete("q");
    window.history.replaceState({}, "", url.pathname + (url.search || ""));
    load();
  });
  if (retry) retry.addEventListener("click", load);
  filterButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      activeFilter = button.dataset.clipsFilter || "all";
      filterButtons.forEach(function (candidate) { var selected = candidate === button; candidate.classList.toggle("is-active", selected); candidate.setAttribute("aria-pressed", String(selected)); });
      render({ clips: currentItems, total: currentItems.length, source: { state: "ready" } });
    });
  });

  var initialQuery = new URL(window.location.href).searchParams.get("q") || "";
  if (input) input.value = initialQuery;
  window.addEventListener("popstate", function () {
    if (!isActiveView()) return;
    if (input) input.value = new URL(window.location.href).searchParams.get("q") || "";
    load();
  });
  load();
  }

  site.initClips = initClips;
  if (site.body.dataset.page === "clips") initClips(document);
})(window);
