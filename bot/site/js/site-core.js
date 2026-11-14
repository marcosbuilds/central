(function () {
  "use strict";

  var body = document.body;
  var header = document.querySelector(".site-header, .flow-header");
  var menuButton = header && header.querySelector(".menu-toggle");
  var navigation = header && header.querySelector(".site-nav, .flow-header-nav");
  var revealItems = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var mobileNavigation = window.matchMedia("(max-width: 1080px)");
  var memberSessionStorageKey = "peace.member.session.v1";

  function readMemberSessionToken() {
    // The authenticated session is HttpOnly. Delete any token left by the
    // pre-cookie client and never read it into page JavaScript again.
    clearMemberSessionToken();
    return "";
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

  var navigationIcons = {
    peace: '<path d="M12 3.5c1.5 2.8 4.4 4.1 7.3 4.5-1.1 4.7-3.7 8.8-7.3 11-3.6-2.2-6.2-6.3-7.3-11 2.9-.4 5.8-1.7 7.3-4.5Z"></path><path d="M8.8 12.2h6.4M12 9v6"></path>',
    study: '<path d="M4.2 5.2c2.9-.8 5.4-.3 7.8 1.4v12c-2.4-1.7-4.9-2.2-7.8-1.4v-12ZM19.8 5.2c-2.9-.8-5.4-.3-7.8 1.4v12c2.4-1.7 4.9-2.2 7.8-1.4v-12Z"></path><path d="M12 6.6v12"></path>',
    process: '<circle cx="12" cy="12" r="8.5"></circle><path d="m8.3 12.3 2.4 2.4 4.9-5"></path>',
    notice: '<path d="M6.2 10.3a5.8 5.8 0 0 1 11.6 0c0 4 1.6 4.8 2.2 5.6H4c.6-.8 2.2-1.6 2.2-5.6Z"></path><path d="M9.8 19h4.4"></path>',
    partner: '<circle cx="8" cy="8.2" r="2.5"></circle><circle cx="16" cy="15.8" r="2.5"></circle><path d="m10 9.8 4 4.4"></path><path d="M5.5 15.5a3.6 3.6 0 0 1 5.1-1.8M13.4 10.3a3.6 3.6 0 0 1 5.1 1.8"></path>'
  };

  function navigationIconKey(link) {
    var href = link.getAttribute("href") || "";
    if (href === "/#sobre" || href === "#sobre") return "peace";
    if (href === "/estudos/" || href.indexOf("/estudos/civil/") === 0 || href.indexOf("/estudos/peace/") === 0) return "study";
    if (href === "/meu-processo/") return "process";
    if (href === "/avisos/") return "notice";
    if (href === "/parceiros/") return "partner";
    return null;
  }

  document.querySelectorAll(".site-nav a, .flow-header-nav a").forEach(function (link) {
    if (link.querySelector(".nav-option-icon")) return;
    var key = navigationIconKey(link);
    if (!key) return;
    var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.classList.add("nav-option-icon");
    icon.setAttribute("viewBox", "0 0 24 24");
    icon.setAttribute("aria-hidden", "true");
    icon.setAttribute("focusable", "false");
    icon.setAttribute("fill", "none");
    icon.setAttribute("stroke", "currentColor");
    icon.setAttribute("stroke-width", "1.6");
    icon.setAttribute("stroke-linecap", "round");
    icon.setAttribute("stroke-linejoin", "round");
    icon.innerHTML = navigationIcons[key];
    link.prepend(icon);
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
      if (isOpen) {
        var firstLink = navigation.querySelector("a:not([hidden])");
        if (firstLink) firstLink.focus();
      }
    });

    navigation.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { closeMenu(true); });
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
      AUTH_UNAVAILABLE: "O Discord ou a fonte de membros está temporariamente indisponível. Tente novamente em instantes.",
      DM_UNAVAILABLE: "Não consegui enviar a mensagem privada. Abra suas DMs no Discord e tente novamente.",
      INVALID_CODE: "O código não confere ou já expirou. Confira a DM e tente novamente.",
      AUTH_SESSION_INVALID: "Sua sessão expirou. Entre novamente.",
      AUTH_SESSION_UNAVAILABLE: "A sessão não pôde ser criada agora. Tente novamente em instantes.",
      MEMBER_NOT_FOUND: "Não encontrei essa conta no servidor. Revise o username e tente novamente.",
      MEMBER_AMBIGUOUS: "Encontrei mais de uma conta com esse username. Informe também o ID ou o link do perfil.",
      INVALID_DISCORD_PROFILE: "Informe um link de perfil válido do Discord.",
      MEMBER_IDENTITY_MISMATCH: "O username, o ID e o link informado não pertencem à mesma conta.",
      ENTRY_MEMBER_NOT_FOUND: "Não encontrei sua conta no servidor. Revise os dados e tente novamente.",
      OAUTH_NOT_CONFIGURED: "A conexão com Discord ainda não foi configurada neste ambiente.",
      OAUTH_UNAVAILABLE: "A conexão com Discord está temporariamente indisponível.",
      OAUTH_SESSION_INVALID: "Conecte sua conta Discord para continuar.",
      OAUTH_STATE_INVALID: "A conexão expirou. Inicie novamente.",
      OAUTH_STATE_EXPIRED: "A conexão expirou. Inicie novamente.",
      PROCESS_UNAVAILABLE: "Não consegui consultar seu processo agora. Tente novamente em instantes.",
      EXAM_LINK_NOT_FOUND: "Esse link de prova não existe ou expirou.",
      EXAM_IDENTITY_MISMATCH: "Este link pertence a outra conta Discord.",
      EXAM_UNAVAILABLE: "Esta atribuição não está mais disponível.",
      EXAM_EXPIRED: "O prazo desta prova terminou.",
      EXAM_ALREADY_SUBMITTED: "Esta prova já foi enviada e não pode ser refeita.",
      MANAGER_REQUIRED: "Somente Gerência pode acessar esta área.",
      INVALID_DEADLINE: "Escolha um prazo futuro para a prova.",
      DEADLINE_TOO_LONG: "O prazo escolhido ultrapassa o limite da equipe.",
      EXAM_ASSIGNMENT_UNAVAILABLE: "Não consegui gerar a prova agora.",
      CANDIDATE_IDENTITY_MISMATCH: "O username informado não corresponde ao Discord ID encontrado no servidor."
    };

    if (knownMessages[code]) return knownMessages[code];
    if (status === 404) return "Não encontrei este recurso. Revise o link e tente novamente.";
    if (status === 429) return "Aguarde alguns segundos e tente novamente.";
    if (status >= 500) return "O serviço está indisponível agora. Tente novamente em instantes.";
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
    if (!requestOptions.credentials) requestOptions.credentials = "same-origin";
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


  window.PeaceSite = {
    body: body,
    readMemberSessionToken: readMemberSessionToken,
    clearMemberSessionToken: clearMemberSessionToken,
    setStatusMessage: setStatusMessage,
    setButtonBusy: setButtonBusy,
    friendlyError: friendlyError,
    attemptEndpoint: attemptEndpoint
  };
})();
