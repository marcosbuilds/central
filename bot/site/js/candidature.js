(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;
  var body = site.body;
  var setButtonBusy = site.setButtonBusy;
  var attemptEndpoint = site.attemptEndpoint;
  var friendlyError = site.friendlyError;

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
    var candidatureToast = document.querySelector("[data-candidature-toast]");
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
    var candidatureToastTimer = null;

    function showCandidatureToast(message) {
      if (!candidatureToast) return;
      window.clearTimeout(candidatureToastTimer);
      candidatureToast.textContent = message;
      candidatureToast.hidden = false;
      candidatureToast.classList.add("is-visible");
      candidatureToastTimer = window.setTimeout(function () {
        candidatureToast.classList.remove("is-visible");
        candidatureToastTimer = window.setTimeout(function () {
          candidatureToast.hidden = true;
        }, 220);
      }, 4200);
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
      setStage(4, false);
      showCandidatureToast("Candidatura enviada para análise.");
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

    function resumeConnectedFlow(session) {
      var server = session && session.server ? session.server : {};
      if (!session) return false;
      if (server.is_peace_member === true) {
        if (sessionNote) sessionNote.textContent = "Sua conta já possui o cargo Peace. Abrindo o painel para acompanhar o próximo passo.";
        window.location.replace("/area/");
        return true;
      }
      if (server.is_member === true) {
        var identity = session.identity || {};
        if (connectButton) connectButton.hidden = true;
        if (existingToggle) existingToggle.hidden = true;
        setEntryUser({ mention: "@" + (identity.username || "usuário") });
        if (memberResult) memberResult.textContent = "Sua entrada no servidor foi confirmada pela conta Discord conectada. A entrevista é o próximo passo.";
        if (manualEntryNote) manualEntryNote.textContent = "Não é necessário conectar novamente nem informar username ou ID. Esta conta já foi identificada pelo Discord.";
        if (sessionNote) sessionNote.textContent = "Conta identificada no servidor. Continue pela etapa de entrevista.";
        setStage(3, false);
        updateWizard(wizardStep, false);
        return true;
      }
      return false;
    }

    site.getDiscordSession().then(function (session) {
      if (resumeConnectedFlow(session)) return;
      if (readEntryToken()) {
        startEntrySession().then(maybeRecoverEntrySession).catch(function () {
          if (sessionNote) sessionNote.textContent = "Não consegui retomar o convite agora. Tente abrir um novo link.";
        });
      } else if (manualEntryIdentity) {
        identifyExistingMember(false, manualEntryIdentity).catch(function () { /* draft remains available for a manual retry */ });
      }
    });

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


  site.initCandidature = initCandidature;
})(window);
