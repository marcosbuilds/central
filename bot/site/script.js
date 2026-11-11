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

  function attemptEndpoint(url, options, timeoutMs) {
    if (!window.fetch) return Promise.reject(new Error("fetch unavailable"));
    var requestOptions = Object.assign({}, options || { headers: { Accept: "application/json" } });
    var controller = typeof window.AbortController === "function" ? new window.AbortController() : null;
    var timeoutId;
    var duration = Number(timeoutMs) > 0 ? Number(timeoutMs) : 60000;

    if (controller) requestOptions.signal = controller.signal;

    var request = window.fetch(url, requestOptions).then(function (response) {
      if (!response.ok) throw new Error("endpoint unavailable");
      return response;
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
    var saveStatus = document.querySelector("[data-candidature-save-status]");
    var wizard = document.querySelector("[data-wizard]");
    var wizardPanels = wizard ? Array.prototype.slice.call(wizard.querySelectorAll("[data-wizard-panel]")) : [];
    var wizardNext = wizard && wizard.querySelector("[data-wizard-next]");
    var wizardBack = wizard && wizard.querySelector("[data-wizard-back]");
    var wizardLabel = wizard && wizard.querySelector("[data-wizard-label]");
    var wizardPercent = wizard && wizard.querySelector("[data-wizard-progress]");
    var wizardTrack = wizard && wizard.querySelector("[data-wizard-track]");
    var storageKey = "peace.candidature.v2";
    var currentStage = 1;
    var wizardStep = 1;
    var restoring = true;

    function setSaveStatus(message) {
      if (!saveStatus) return;
      saveStatus.textContent = message;
      saveStatus.hidden = !message;
    }

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

    function saveDraft(message) {
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
        setSaveStatus(message || "Progresso salvo neste navegador.");
      } catch (error) {
        setSaveStatus("");
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
        var active = Number(button.dataset.stagePreview) === currentStage;
        button.classList.toggle("is-current", active);
        button.classList.toggle("is-preview", Boolean(isPreview && active && currentStage > 1));
        if (active) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
      });
      if (!restoring) saveDraft();
    }

    stageButtons.forEach(function (button) {
      button.addEventListener("click", function () { setStage(Number(button.dataset.stagePreview), true); });
    });

    var connectButton = document.querySelector("[data-entry-connect]");
    var connectResult = document.querySelector("[data-entry-result]");
    if (connectButton) {
      connectButton.addEventListener("click", function () {
        if (connectResult) connectResult.textContent = "";
        setButtonBusy(connectButton, true, "Conectando…");
        attemptEndpoint("/api/entry/start", { method: "POST", headers: { Accept: "application/json" } }, 60000).then(function () {
          setButtonBusy(connectButton, false);
          setButtonLabel(connectButton, "Discord conectado");
          setStage(2, false);
        }).catch(function () {
          setButtonBusy(connectButton, false);
          setButtonLabel(connectButton, "Tentar novamente");
          if (connectResult) connectResult.textContent = "Não foi possível conectar agora. Tente novamente.";
          window.setTimeout(function () {
            if (!connectButton.disabled) setButtonLabel(connectButton, "Conectar Discord");
          }, 3500);
        });
      });
    }

    var refreshButton = document.querySelector("[data-entry-refresh]");
    var refreshResult = document.querySelector("[data-entry-refresh-result]");
    if (refreshButton) {
      refreshButton.addEventListener("click", function () {
        if (refreshResult) refreshResult.textContent = "";
        setButtonBusy(refreshButton, true, "Atualizando…");
        attemptEndpoint("/api/entry/status", null, 60000).then(function () {
          setButtonBusy(refreshButton, false);
          setButtonLabel(refreshButton, "Atualizado");
          if (refreshResult) refreshResult.textContent = "Status atualizado.";
          window.setTimeout(function () {
            if (!refreshButton.disabled) setButtonLabel(refreshButton, "Atualizar status");
          }, 2500);
        }).catch(function () {
          setButtonBusy(refreshButton, false);
          setButtonLabel(refreshButton, "Tentar novamente");
          if (refreshResult) refreshResult.textContent = "Não foi possível atualizar agora. Tente novamente.";
          window.setTimeout(function () {
            if (!refreshButton.disabled) setButtonLabel(refreshButton, "Atualizar status");
          }, 3500);
        });
      });
    }

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
      saveDraft("Revisão salva neste navegador.");
      if (result) result.textContent = "Candidatura salva neste navegador. Você pode voltar e continuar a qualquer momento.";
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
    if (draft) {
      setSaveStatus(currentStage === 4 || (currentStage === 3 && wizardStep === 4) ? "Revisão restaurada neste navegador." : "Progresso restaurado neste navegador.");
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
