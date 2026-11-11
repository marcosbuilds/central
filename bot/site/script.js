(function () {
  "use strict";

  var body = document.body;
  var header = document.querySelector(".site-header");
  var menuButton = document.querySelector(".menu-toggle");
  var navigation = document.querySelector("#site-nav");
  var revealItems = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var mobileNavigation = window.matchMedia("(max-width: 840px)");

  document.documentElement.classList.add("js-ready");

  // Discord destinations always open outside the Peace flow so the current
  // page remains available for status, return navigation, and retry actions.
  document.querySelectorAll('a[href^="/discord"], a[href^="../discord"]').forEach(function (link) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  });

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

  function setServiceStatus(state, label) {
    var status = document.querySelector("[data-service-status]");
    var statusLabel = status && status.querySelector("[data-service-status-label]");
    if (!status || !statusLabel) return;
    status.dataset.state = state;
    statusLabel.textContent = label;
    status.hidden = state !== "online";
  }

  function refreshServiceStatus() {
    if (body.dataset.page !== "home" || !window.fetch) return;

    var localPreview = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";

    window.fetch("/api/status", { headers: { Accept: "application/json" }, cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("status unavailable");
        return response.json();
      })
      .then(function (payload) {
        var connected = Boolean(payload && payload.discord && payload.discord.connected === true && payload.status === "ok");
        setServiceStatus(connected ? "online" : "checking", connected ? "Peace Tools conectado" : "");
      })
      .catch(function () {
        setServiceStatus(localPreview ? "preview" : "offline", "");
      });
  }

  refreshServiceStatus();

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
      NOT_JOINED: "Ainda não identifiquei sua entrada na Peace. Abra o convite e tente novamente.",
      ROLE_NOT_CONFIGURED: "A equipe precisa ajustar o cargo de entrada antes de continuar.",
      ROLE_HIERARCHY: "A equipe precisa ajustar a hierarquia de cargos antes de continuar.",
      ROLE_UPDATE_FAILED: "Não consegui corrigir o cargo de entrada agora. Tente novamente em instantes.",
      MEMBER_UNAVAILABLE: "Ainda não consegui localizar sua entrada. Tente novamente em instantes.",
      REPAIR_THROTTLED: "Aguarde alguns segundos e tente novamente.",
      DISCORD_ID_MISMATCH: "O ID informado não corresponde à conta identificada pelo convite.",
      INVALID_DISCORD_ID: "O ID do Discord deve conter somente números.",
      FIELD_TOO_LONG: "Revise os campos informados e tente novamente."
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
    if (!window.fetch) return Promise.reject(new Error("fetch unavailable"));
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
        var error = new Error("request timeout");
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
    var storageKey = "peace.candidature.v2";
    var entryStorageKey = "peace.entry.v1";
    var currentStage = 1;
    var wizardStep = 1;
    var restoring = true;
    var entrySession = null;
    var entryPollTimer = null;

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

    function setVerificationState(state, title, message) {
      if (verificationState) verificationState.dataset.state = state || "pending";
      if (verificationTitle) verificationTitle.textContent = title || "Acompanhando sua entrada";
      if (verificationMessage) verificationMessage.textContent = message || "Aguarde alguns instantes.";
    }

    function setEntryUser(user) {
      if (entryUser) entryUser.textContent = user && user.mention ? user.mention : "@usuário";
    }

    function stopEntryPolling() {
      if (entryPollTimer) window.clearInterval(entryPollTimer);
      entryPollTimer = null;
    }

    function startEntryPolling() {
      if (entryPollTimer || !entrySession || currentStage >= 3) return;
      entryPollTimer = window.setInterval(function () { fetchEntryStatus(false); }, 4000);
    }

    function stageForEntryStatus(status) {
      if (status === "verified") return 3;
      if (status === "verification_pending" || status === "role_missing") return 2;
      return 1;
    }

    function applyEntryPayload(payload) {
      if (!payload) return;
      entrySession = payload;
      saveEntryToken(payload.session_token);
      setEntryUser(payload.discord_user);

      if (connectButton && payload.invite_url) {
        setButtonLabel(connectButton, "Abrir convite novamente");
        connectButton.dataset.inviteUrl = payload.invite_url;
      }

      if (payload.status === "verified") {
        stopEntryPolling();
        setVerificationState("success", "Verificação concluída", "Tudo certo. Continuando para a entrevista.");
        if (refreshResult) refreshResult.textContent = "Verificação concluída. A entrevista está liberada.";
        setStage(3, false);
        return;
      }

      if (payload.status === "verification_pending") {
        setVerificationState("pending", "Verificação pendente", "Você já está na Peace. Abra o canal #verify, clique em Iniciar verificação e responda ao CAPTCHA.");
        if (sessionNote) sessionNote.textContent = "Entrada identificada. Acompanhe a verificação nesta página.";
        setStage(2, false);
        startEntryPolling();
        return;
      }

      if (payload.status === "role_missing") {
        setVerificationState("warning", "Cargo de entrada ausente", "Não encontrei Not Verified nesta conta. Abra Estou com problemas para tentar corrigir.");
        if (helpPanel) helpPanel.hidden = false;
        if (helpToggle) helpToggle.setAttribute("aria-expanded", "true");
        setStage(2, false);
        startEntryPolling();
        return;
      }

      setStage(stageForEntryStatus(payload.status), false);
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

    function startEntrySession() {
      var token = readEntryToken();
      var requestBody = token ? { session_token: token } : {};
      return attemptEndpoint("/api/entry/start", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(requestBody) }, 60000)
        .then(parseEntryResponse)
        .then(function (payload) { applyEntryPayload(payload); return payload; });
    }

    function fetchEntryStatus(showBusy) {
      var token = (entrySession && entrySession.session_token) || readEntryToken();
      if (!token) return Promise.resolve(null);
      if (showBusy) setButtonBusy(refreshButton, true, "Atualizando…");
      return attemptEndpoint("/api/entry/status", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ session_token: token }) }, 60000)
        .then(parseEntryResponse)
        .then(function (payload) {
          applyEntryPayload(payload);
          if (refreshResult && payload.status === "verification_pending") refreshResult.textContent = "Ainda aguardando a conclusão no #verify.";
          return payload;
        })
        .catch(function (error) {
          if (/expirou|inválida/i.test(error.message || "")) {
            clearEntryToken();
            entrySession = null;
            stopEntryPolling();
            setStage(1, false);
          }
          if (refreshResult) refreshResult.textContent = error.message || "Não foi possível atualizar agora.";
          throw error;
        })
        .finally(function () {
          if (showBusy) setButtonBusy(refreshButton, false);
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
      currentStage = Math.min(4, Math.max(1, Number(stage) || 1));
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
        var popup = null;
        var inviteLink = document.querySelector("[data-entry-invite-link]");
        if (connectButton.dataset.inviteUrl) {
          popup = window.open(connectButton.dataset.inviteUrl, "_blank", "noopener,noreferrer");
          if (!popup && connectResult) connectResult.textContent = "O navegador bloqueou a nova guia. Permita pop-ups para abrir o Discord.";
          startEntryPolling();
          return;
        }
        popup = window.open("/candidatura/abrindo-discord.html", "_blank");
        if (popup) popup.opener = null;
        if (connectResult) connectResult.textContent = "Gerando seu convite individual…";
        setButtonBusy(connectButton, true, "Gerando convite…");
        startEntrySession().then(function (payload) {
          if (inviteLink && payload.invite_url) {
            inviteLink.href = payload.invite_url;
            inviteLink.hidden = false;
          }
          if (popup && !popup.closed && payload.invite_url) popup.location.replace(payload.invite_url);
          else if (payload.invite_url) popup = window.open(payload.invite_url, "_blank", "noopener,noreferrer");
          setButtonBusy(connectButton, false);
          setButtonLabel(connectButton, "Abrir convite novamente");
          if (connectResult) connectResult.textContent = popup ? "Convite aberto em uma nova guia. Entre na Peace por ele e volte para acompanhar." : "Convite pronto. Abra pelo link abaixo e volte para acompanhar.";
          startEntryPolling();
        }).catch(function (error) {
          setButtonBusy(connectButton, false);
          if (popup && !popup.closed) popup.location.replace("/candidatura/abrindo-discord.html?state=error");
          setButtonLabel(connectButton, "Tentar gerar convite");
          if (connectResult) connectResult.textContent = error.message || "Não foi possível gerar o convite agora.";
        });
      });
    }

    if (refreshButton) {
      refreshButton.addEventListener("click", function () {
        if (refreshResult) refreshResult.textContent = "";
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
    setStage(1, false);
    restoring = false;

    if (readEntryToken()) {
      startEntrySession().catch(function () {
        if (sessionNote) sessionNote.textContent = "Não consegui retomar o convite agora. Tente abrir um novo link.";
      });
    }
  }

  function initLogin() {
    if (body.dataset.page !== "login") return;

    var requestForm = document.querySelector("[data-login-request]");
    var verifyForm = document.querySelector("[data-login-verify]");
    var status = document.querySelector("[data-login-status]");
    var result = document.querySelector("[data-login-result]");
    var codeInput = document.querySelector("[name=\"access-code\"]");
    var cells = Array.prototype.slice.call(document.querySelectorAll("[data-code-cell]"));
    var idInput = requestForm && requestForm.querySelector('[name="peace-id"]');

    if (idInput) {
      idInput.addEventListener("input", function () {
        idInput.value = idInput.value.replace(/\D/g, "").slice(0, 19);
        idInput.setCustomValidity("");
      });
    }

    function syncCodeCells() {
      var value = codeInput ? codeInput.value : "";
      cells.forEach(function (cell, index) { cell.textContent = value.charAt(index) || ""; });
    }

    if (codeInput) {
      codeInput.addEventListener("input", function () {
        codeInput.value = codeInput.value.replace(/\D/g, "").slice(0, 6);
        syncCodeCells();
      });
    }

    if (requestForm) requestForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!idInput || !/^\d{1,19}$/.test(idInput.value.trim())) {
        if (idInput) { idInput.setCustomValidity("Use somente números, de 1 a 19 dígitos."); idInput.reportValidity(); idInput.setCustomValidity(""); }
        return;
      }
      var submit = requestForm.querySelector("button[type=submit]");
      if (status) status.hidden = true;
      setButtonBusy(submit, true, "Enviando código…");
      attemptEndpoint("/api/auth/code/request", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ peace_id: idInput.value.trim() }) }, 60000).then(function () {
        setButtonBusy(submit, false);
        setButtonLabel(submit, "Reenviar código");
        setStatusMessage(status, "Código enviado", "Confira sua DM.", "success");
        if (verifyForm) {
          verifyForm.hidden = false;
          if (codeInput) codeInput.focus();
        }
      }).catch(function () {
        setButtonBusy(submit, false);
        setStatusMessage(status, "Não foi possível enviar", "Tente novamente.", "offline");
      });
    });

    if (verifyForm) verifyForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!codeInput || !/^\d{6}$/.test(codeInput.value)) {
        if (result) result.textContent = "Digite os seis dígitos do código para continuar.";
        if (codeInput) codeInput.focus();
        return;
      }
      var verifyButton = verifyForm.querySelector("button[type=submit]");
      if (result) result.textContent = "";
      setButtonBusy(verifyButton, true, "Validando…");
      attemptEndpoint("/api/auth/code/verify", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ code: codeInput.value }) }, 60000).then(function () {
        setButtonBusy(verifyButton, false);
        if (result) result.textContent = "Código confirmado.";
      }).catch(function () {
        setButtonBusy(verifyButton, false);
        if (result) result.textContent = "Não foi possível validar agora. Tente novamente.";
      });
    });
  }

  function setMemberTab(name, moveFocus) {
    var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-member-tab]"));
    var panels = Array.prototype.slice.call(document.querySelectorAll("[data-member-panel]"));
    if (!tabs.length || !panels.length) return;

    tabs.forEach(function (tab) {
      var active = tab.dataset.memberTab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && moveFocus) tab.focus();
    });

    panels.forEach(function (panel) {
      var active = panel.dataset.memberPanel === name;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    });
  }

  function initMemberArea() {
    if (body.dataset.page !== "member") return;

    var gate = document.querySelector("[data-member-gate]");
    var preview = document.querySelector("[data-member-preview]");
    var previewOpeners = document.querySelectorAll("[data-preview-toggle]");
    var previewCloser = document.querySelector("[data-preview-close]");
    var query = new URLSearchParams(window.location.search);
    var urlPreview = query.get("preview") === "member";
    var requestedPreview = query.get("preview") === "investigativa" ? "investigativa" : "workspace";
    var lastPreviewOpener = null;
    var workspaceShell = document.querySelector("[data-workspace-shell]");
    var workspaceSidebar = document.querySelector("[data-workspace-sidebar]");
    var workspaceMenu = document.querySelector("[data-workspace-menu]");
    var previewFeedback = document.querySelector("[data-preview-feedback]");
    var feedbackTimer;

    function showPreviewFeedback(message) {
      if (!previewFeedback) return;
      previewFeedback.textContent = message;
      previewFeedback.hidden = false;
      window.clearTimeout(feedbackTimer);
      feedbackTimer = window.setTimeout(function () { previewFeedback.hidden = true; }, 5200);
    }

    function setPreviewScreen(name, moveFocus) {
      var screens = Array.prototype.slice.call(document.querySelectorAll("[data-preview-screen]"));
      if (!screens.length) return;

      screens.forEach(function (screen) {
        var active = screen.dataset.previewScreen === name;
        screen.classList.toggle("is-active", active);
        screen.hidden = !active;
      });

      var activeNav = document.querySelector('[data-preview-screen-target="' + name + '"]');
      document.querySelectorAll("[data-preview-screen-target]").forEach(function (item) { item.classList.remove("is-active"); });
      if (activeNav) activeNav.classList.add("is-active");

      if (moveFocus) {
        window.setTimeout(function () {
          var heading = name === "investigativa" ? document.querySelector("#investigative-title") : document.querySelector("#preview-title");
          if (heading) heading.focus({ preventScroll: true });
        }, 0);
      }
    }

    function syncWorkspaceMenu(isOpen, restoreFocus) {
      if (!workspaceShell || !workspaceMenu) return;
      workspaceShell.classList.toggle("menu-open", isOpen);
      workspaceMenu.setAttribute("aria-expanded", String(isOpen));
      if (workspaceSidebar) {
        var sidebarHidden = mobileNavigation.matches && !isOpen;
        workspaceSidebar.inert = sidebarHidden;
        workspaceSidebar.setAttribute("aria-hidden", String(sidebarHidden));
      }
      if (!isOpen && restoreFocus) workspaceMenu.focus();
    }

    function openPreview(event, mode) {
      if (!preview) return;
      lastPreviewOpener = event && event.currentTarget ? event.currentTarget : lastPreviewOpener;
      preview.hidden = false;
      preview.setAttribute("data-preview-state", "open");
      if (gate) gate.setAttribute("data-preview-state", "open");
      setPreviewScreen(mode || "workspace", true);
      window.setTimeout(function () {
        var heading = (mode || "workspace") === "investigativa" ? document.querySelector("#investigative-title") : document.querySelector("#preview-title");
        if (heading) heading.focus({ preventScroll: true });
      }, 0);
    }

    function closePreview() {
      if (!preview) return;
      preview.hidden = true;
      preview.removeAttribute("data-preview-state");
      if (gate) gate.removeAttribute("data-preview-state");
      syncWorkspaceMenu(false, false);
      if (lastPreviewOpener) {
        lastPreviewOpener.focus();
        lastPreviewOpener = null;
      }
    }

    previewOpeners.forEach(function (opener) { opener.addEventListener("click", openPreview); });
    if (previewCloser) previewCloser.addEventListener("click", closePreview);

    document.querySelectorAll("[data-preview-screen-target]").forEach(function (item) {
      item.addEventListener("click", function () {
        setPreviewScreen(item.dataset.previewScreenTarget, true);
        syncWorkspaceMenu(false, false);
        if (item.dataset.previewMessage) showPreviewFeedback(item.dataset.previewMessage);
      });
    });

    document.querySelectorAll("[data-preview-message]").forEach(function (item) {
      item.addEventListener("click", function () { showPreviewFeedback(item.dataset.previewMessage); });
    });

    if (workspaceMenu) {
      workspaceMenu.addEventListener("click", function () {
        syncWorkspaceMenu(!workspaceShell.classList.contains("menu-open"), false);
      });
    }

    mobileNavigation.addEventListener("change", function () { syncWorkspaceMenu(false, false); });

    document.querySelectorAll("[data-member-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () { setMemberTab(tab.dataset.memberTab, false); });
      tab.addEventListener("keydown", function (event) {
        var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-member-tab]"));
        var index = tabs.indexOf(tab);
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        var nextIndex = event.key === "ArrowRight" ? index + 1 : index - 1;
        if (nextIndex < 0) nextIndex = tabs.length - 1;
        if (nextIndex >= tabs.length) nextIndex = 0;
        setMemberTab(tabs[nextIndex].dataset.memberTab, true);
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        syncWorkspaceMenu(false, true);
        if (header && header.classList.contains("menu-open")) closeMenu(true);
      }
    });

    document.addEventListener("click", function (event) {
      if (workspaceShell && workspaceShell.classList.contains("menu-open") && !workspaceShell.contains(event.target)) syncWorkspaceMenu(false, true);
    });

    syncWorkspaceMenu(false, false);

    if (urlPreview || query.get("preview") === "investigativa") {
      openPreview(null, requestedPreview);
      window.setTimeout(function () {
        if (preview) preview.scrollIntoView({ block: "start" });
      }, 0);
    }
  }

  initMemberArea();
  initCandidature();
  initLogin();
})();
