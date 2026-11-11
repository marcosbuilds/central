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
        setServiceStatus(connected ? "online" : "checking", connected ? "Peace Tools conectado" : "Peace Tools iniciando");
      })
      .catch(function () {
        setServiceStatus(localPreview ? "preview" : "offline", localPreview ? "Prévia local · API não conectada" : "Peace Tools indisponível no momento");
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

  function setIntegrationMessage(node, title, message, tone) {
    if (!node) return;
    var strong = node.querySelector("strong");
    var paragraph = node.querySelector("p");
    if (strong) strong.textContent = title;
    if (paragraph) paragraph.textContent = message;
    node.dataset.state = tone || "pending";
  }

  function attemptEndpoint(url, options) {
    if (!window.fetch) return Promise.reject(new Error("fetch unavailable"));
    return window.fetch(url, options || { headers: { Accept: "application/json" } }).then(function (response) {
      if (!response.ok) throw new Error("endpoint unavailable");
      return response;
    });
  }

  function initCandidature() {
    if (body.dataset.page !== "candidatura") return;

    var stageButtons = Array.prototype.slice.call(document.querySelectorAll("[data-stage-preview]"));
    var stages = Array.prototype.slice.call(document.querySelectorAll("[data-entry-stage]"));
    var integrationBanner = document.querySelector("[data-integration-status]");
    var currentStage = 1;

    function setStage(stage, isPreview) {
      currentStage = stage;
      stages.forEach(function (item) {
        var active = Number(item.dataset.entryStage) === stage;
        item.hidden = !active;
        item.classList.toggle("is-active", active);
      });
      stageButtons.forEach(function (button) {
        var active = Number(button.dataset.stagePreview) === stage;
        button.classList.toggle("is-current", active);
        button.classList.toggle("is-preview", Boolean(isPreview && active && stage > 1));
        if (active) button.setAttribute("aria-current", "step");
        else button.removeAttribute("aria-current");
      });
      if (isPreview && stage > 1) {
        setIntegrationMessage(integrationBanner, "Prévia de interface", "Esta etapa está visível para revisão visual. O backend ainda não autorizou o avanço real.", "preview");
      }
    }

    stageButtons.forEach(function (button) {
      button.addEventListener("click", function () { setStage(Number(button.dataset.stagePreview), true); });
    });

    var connectButton = document.querySelector("[data-entry-connect]");
    if (connectButton) {
      connectButton.addEventListener("click", function () {
        connectButton.disabled = true;
        setIntegrationMessage(integrationBanner, "Conexão não disponível", "A rota /api/entry/start ainda não está conectada ao OAuth do Discord. Nenhuma sessão foi criada.", "offline");
        attemptEndpoint("/api/entry/start", { method: "POST", headers: { Accept: "application/json" } }).catch(function () {
          connectButton.disabled = false;
        });
      });
    }

    var refreshButton = document.querySelector("[data-entry-refresh]");
    if (refreshButton) {
      refreshButton.addEventListener("click", function () {
        refreshButton.disabled = true;
        setIntegrationMessage(integrationBanner, "Status não confirmado", "A rota /api/entry/status ainda não está disponível; a etapa continua aguardando o Discord.", "offline");
        attemptEndpoint("/api/entry/status").catch(function () {
          refreshButton.disabled = false;
        });
      });
    }

    var wizard = document.querySelector("[data-wizard]");
    if (!wizard) return;
    var wizardPanels = Array.prototype.slice.call(wizard.querySelectorAll("[data-wizard-panel]"));
    var wizardNext = wizard.querySelector("[data-wizard-next]");
    var wizardBack = wizard.querySelector("[data-wizard-back]");
    var wizardLabel = wizard.querySelector("[data-wizard-label]");
    var wizardPercent = wizard.querySelector("[data-wizard-progress]");
    var wizardTrack = wizard.querySelector("[data-wizard-track]");
    var wizardStep = 1;

    function updateWizard(step, moveFocus) {
      wizardStep = step;
      wizardPanels.forEach(function (panel) {
        var active = Number(panel.dataset.wizardPanel) === step;
        panel.hidden = !active;
        panel.classList.toggle("is-active", active);
      });
      if (wizardLabel) wizardLabel.textContent = "Passo " + step + " de 4";
      if (wizardPercent) wizardPercent.textContent = String(Math.round((step / 4) * 100)) + "%";
      if (wizardTrack) wizardTrack.style.width = String((step / 4) * 100) + "%";
      if (wizardBack) wizardBack.hidden = step === 1;
      if (wizardNext) wizardNext.hidden = step === 4;
      if (moveFocus) {
        var heading = wizard.querySelector('[data-wizard-panel="' + step + '"] h3');
        if (heading) heading.focus({ preventScroll: true });
      }
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

    wizard.querySelectorAll("[data-character-count-for]").forEach(function (counter) {
      var field = wizard.querySelector('[name="' + counter.dataset.characterCountFor + '"]');
      if (!field) return;
      function syncCounter() { counter.textContent = String(field.value.length); }
      field.addEventListener("input", syncCounter);
      syncCounter();
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
      if (result) result.textContent = "Envio indisponível nesta instalação: a API ainda não está conectada. Nenhuma candidatura foi criada.";
      setIntegrationMessage(integrationBanner, "Candidatura não enviada", "A API de candidatura ainda não está conectada a esta instalação.", "offline");
    });

    updateWizard(1, false);
    setStage(currentStage, false);
  }

  function initLogin() {
    if (body.dataset.page !== "login") return;

    var requestForm = document.querySelector("[data-login-request]");
    var verifyForm = document.querySelector("[data-login-verify]");
    var status = document.querySelector("[data-login-status]");
    var result = document.querySelector("[data-login-result]");
    var codeInput = document.querySelector("[name=\"access-code\"]");
    var cells = Array.prototype.slice.call(document.querySelectorAll("[data-code-cell]"));

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
      var idInput = requestForm.querySelector('[name="peace-id"]');
      if (!idInput || !idInput.value.trim()) {
        if (idInput) { idInput.setCustomValidity("Digite seu ID Peace."); idInput.reportValidity(); idInput.setCustomValidity(""); }
        return;
      }
      var submit = requestForm.querySelector("button[type=submit]");
      if (submit) submit.disabled = true;
      setIntegrationMessage(status, "Pedido preparado", "Se esse ID estiver ativo e vinculado, o código seria enviado por DM. A rota de emissão ainda não está conectada.", "offline");
      if (verifyForm) {
        verifyForm.hidden = false;
        if (codeInput) codeInput.focus();
      }
      attemptEndpoint("/api/auth/code/request", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ peace_id: idInput.value.trim() }) }).catch(function () {
        if (submit) submit.disabled = false;
      });
    });

    if (verifyForm) verifyForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!codeInput || !/^\d{6}$/.test(codeInput.value)) {
        if (result) result.textContent = "Digite os seis dígitos do código para continuar.";
        if (codeInput) codeInput.focus();
        return;
      }
      if (result) result.textContent = "Validação não disponível: /api/auth/code/verify ainda não está conectada. Nenhuma sessão foi criada.";
      attemptEndpoint("/api/auth/code/verify", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify({ code: codeInput.value }) }).catch(function () {});
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
