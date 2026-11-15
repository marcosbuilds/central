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
  var toast = scope.querySelector("[data-clips-toast]");
  var toastTimer = null;
  var viewer = { state: "anonymous", can_interact: false };
  var loading = false;

  function isActiveView() {
    var view = form && form.closest && form.closest("[data-member-view]");
    return !view || !view.hidden;
  }

  if (!list || list.dataset.clipsReady === "true") return;
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
      var video = node("video", "clip-card-video");
      video.src = url;
      video.controls = true;
      video.preload = "metadata";
      video.playsInline = true;
      if (thumbnail) video.poster = thumbnail;
      video.setAttribute("aria-label", "Reproduzir " + titleFor(item));
      visual.appendChild(video);
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

  function icon(name) {
    var paths = {
      heart: '<path d="M20.8 8.8c0 5.1-8.8 10.1-8.8 10.1S3.2 13.9 3.2 8.8A4.7 4.7 0 0 1 12 6.3a4.7 4.7 0 0 1 8.8 2.5Z"></path>',
      comment: '<path d="M20 11.5a7.6 7.6 0 0 1-8 7.1 8.8 8.8 0 0 1-3.8-.8L4 19l1.1-3.2A6.9 6.9 0 0 1 4 11.5a7.6 7.6 0 0 1 8-7.1 7.6 7.6 0 0 1 8 7.1Z"></path><path d="M8 11.7h.1M12 11.7h.1M16 11.7h.1"></path>'
    };
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.6");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = paths[name] || "";
    return svg;
  }

  function showToast(message, tone) {
    if (!toast) return;
    toast.textContent = message;
    toast.dataset.state = tone || "info";
    toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(function () { toast.hidden = true; }, 4800);
  }

  function interactionHint() {
    if (viewer.state === "peace_member") return "";
    if (viewer.state === "peace_required") return "Solicite a setagem para interagir.";
    if (viewer.state === "not_member") return "Entre na Peace para interagir.";
    if (viewer.state === "unavailable") return "A conexão precisa ser validada novamente.";
    return "Conecte o Discord para interagir.";
  }

  function openInteraction() {
    var returnTo = encodeURIComponent(window.location.pathname + window.location.search);
    if (viewer.state === "peace_required" || viewer.state === "not_member") {
      window.location.assign("/entrar/");
      return;
    }
    window.location.assign("/acessar/?return_to=" + returnTo);
  }

  function updateSocial(card, item) {
    var social = item.social || {};
    var like = card.querySelector("[data-clip-like]");
    var count = card.querySelector("[data-clip-like-count]");
    var commentsCount = card.querySelector("[data-clip-comment-count]");
    if (count) count.textContent = String(Number(social.like_count || 0));
    if (commentsCount) commentsCount.textContent = String(Number(social.comment_count || 0));
    if (like) {
      like.classList.toggle("is-active", social.liked === true);
      like.setAttribute("aria-pressed", String(social.liked === true));
      like.setAttribute("aria-label", social.liked === true ? "Descurtir clip" : "Curtir clip");
    }
  }

  function renderComments(card, item) {
    var comments = card.querySelector("[data-clip-comments]");
    if (!comments) return;
    comments.replaceChildren();
    var values = Array.isArray(item.comments) ? item.comments : [];
    if (!values.length) {
      comments.appendChild(node("p", "clip-comments-empty", "Ainda não há comentários."));
      return;
    }
    values.forEach(function (comment) {
      var row = node("article", "clip-comment");
      var avatar = node("span", "clip-comment-avatar");
      var avatarUrl = safeUrl(comment.author_avatar_url);
      if (avatarUrl) {
        var image = node("img", "", "");
        image.src = avatarUrl;
        image.alt = "";
        image.width = 28;
        image.height = 28;
        image.loading = "lazy";
        avatar.appendChild(image);
      } else {
        avatar.textContent = String(comment.author_name || "M").charAt(0).toUpperCase();
      }
      var copy = node("div", "clip-comment-copy");
      copy.appendChild(node("strong", "", comment.author_name || "Membro"));
      copy.appendChild(node("p", "", comment.body || ""));
      row.appendChild(avatar);
      row.appendChild(copy);
      comments.appendChild(row);
    });
  }

  function requestAction(payload) {
    return site.attemptEndpoint("/api/clips", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }, 12000).then(function (response) { return response.json(); });
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

    var actions = node("div", "clip-card-actions");
    var like = node("button", "clip-action", "");
    like.type = "button";
    like.setAttribute("data-clip-like", "");
    like.setAttribute("aria-pressed", "false");
    like.appendChild(icon("heart"));
    like.appendChild(node("span", "", "Curtir"));
    var likeCount = node("strong", "clip-action-count", "0");
    likeCount.setAttribute("data-clip-like-count", "");
    like.appendChild(likeCount);
    like.addEventListener("click", function () {
      if (!viewer.can_interact) {
        showToast(interactionHint(), "warning");
        openInteraction();
        return;
      }
      like.disabled = true;
      requestAction({ action: "like", media_id: item.id })
        .then(function (payload) {
          item.social = item.social || {};
          item.social.liked = payload.liked === true;
          item.social.like_count = payload.like_count || 0;
          updateSocial(card, item);
        })
        .catch(function (error) {
          showToast(error.message || "Não consegui registrar a curtida.", "error");
        })
        .finally(function () { like.disabled = false; });
    });
    actions.appendChild(like);

    var commentToggle = node("button", "clip-action", "");
    commentToggle.type = "button";
    commentToggle.setAttribute("aria-expanded", "false");
    var commentPanelId = "clip-comments-" + String(item.id || Math.random().toString(36).slice(2)).replace(/[^a-z0-9_-]/gi, "-");
    commentToggle.setAttribute("aria-controls", commentPanelId);
    commentToggle.appendChild(icon("comment"));
    commentToggle.appendChild(node("span", "", "Comentários"));
    var commentCount = node("strong", "clip-action-count", "0");
    commentCount.setAttribute("data-clip-comment-count", "");
    commentToggle.appendChild(commentCount);
    actions.appendChild(commentToggle);
    copy.appendChild(actions);

    var commentPanel = node("div", "clip-comment-panel");
    commentPanel.id = commentPanelId;
    commentPanel.hidden = true;
    var comments = node("div", "clip-comments");
    comments.setAttribute("data-clip-comments", "");
    commentPanel.appendChild(comments);
    var commentForm = node("form", "clip-comment-form");
    var label = node("label", "", "Escreva um comentário");
    var textarea = node("textarea", "", "");
    textarea.name = "comment";
    textarea.maxLength = 500;
    textarea.rows = 2;
    textarea.placeholder = viewer.can_interact ? "Compartilhe uma observação…" : "Conecte o Discord para comentar";
    textarea.disabled = !viewer.can_interact;
    var send = node("button", "button button--outline", "Publicar");
    send.type = "submit";
    send.disabled = !viewer.can_interact;
    label.appendChild(textarea);
    commentForm.appendChild(label);
    commentForm.appendChild(send);
    commentForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!viewer.can_interact) {
        showToast(interactionHint(), "warning");
        openInteraction();
        return;
      }
      var text = textarea.value.trim();
      if (!text) {
        textarea.focus();
        return;
      }
      send.disabled = true;
      requestAction({ action: "comment", media_id: item.id, text: text })
        .then(function (payload) {
          item.comments = (item.comments || []).concat(payload.comment || []);
          item.social = item.social || {};
          item.social.comment_count = Number(item.social.comment_count || 0) + 1;
          textarea.value = "";
          renderComments(card, item);
          updateSocial(card, item);
          showToast("Comentário publicado.", "success");
        })
        .catch(function (error) {
          showToast(error.message || "Não consegui publicar o comentário.", "error");
        })
        .finally(function () { send.disabled = false; });
    });
    commentPanel.appendChild(commentForm);
    copy.appendChild(commentPanel);
    commentToggle.addEventListener("click", function () {
      commentPanel.hidden = !commentPanel.hidden;
      commentToggle.setAttribute("aria-expanded", String(!commentPanel.hidden));
      if (!commentPanel.hidden && viewer.can_interact) textarea.focus();
    });
    card.appendChild(copy);
    renderComments(card, item);
    updateSocial(card, item);
    return card;
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
    var items = Array.isArray(payload.clips) ? payload.clips : [];
    viewer = payload.viewer || { state: "anonymous", can_interact: false };
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
    }
    var total = Number(payload.total || items.length);
    if (status) status.textContent = total
      ? total + (total === 1 ? " clip encontrado." : " clipes encontrados.") + (payload.updated_at ? " Fonte atualizada." : "")
      : "A busca está pronta.";
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
    var params = new URLSearchParams();
    params.set("limit", "60");
    if (query) params.set("q", query);
    site.attemptEndpoint("/api/clips?" + params.toString(), { headers: { Accept: "application/json" } }, 15000)
      .then(function (response) { return response.json(); })
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
      })
      .finally(function () {
        loading = false;
        if (submit) submit.disabled = false;
      });
  }

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
