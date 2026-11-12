(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;
  var body = site.body;
  var readMemberSessionToken = site.readMemberSessionToken;
  var clearMemberSessionToken = site.clearMemberSessionToken;
  var setStatusMessage = site.setStatusMessage;
  var setButtonBusy = site.setButtonBusy;
  var attemptEndpoint = site.attemptEndpoint;
  var friendlyError = site.friendlyError;

  function initLogin() {
    if (body.dataset.page !== "login") return;

    var requestForm = document.querySelector("[data-login-request]");
    var verifyForm = document.querySelector("[data-login-verify]");
    var resendButton = document.querySelector("[data-login-resend]");
    var status = document.querySelector("[data-login-status]");
    var requestButton = requestForm && requestForm.querySelector("button[type=submit]");
    var verifyButton = verifyForm && verifyForm.querySelector("button[type=submit]");
    var result = verifyForm && verifyForm.querySelector("[data-login-result]");
    var idInput = requestForm && requestForm.querySelector('[name="peace-id"]');
    var keepConnected = requestForm && requestForm.querySelector('[name="keep-connected"]');
    var codeInput = verifyForm && verifyForm.querySelector('[name="access-code"]');
    var resendTimer = null;
    var resendAvailableAt = 0;

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

    function showCodeStep() {
      if (requestForm) requestForm.hidden = true;
      if (verifyForm) verifyForm.hidden = false;
      if (resendButton) resendButton.hidden = false;
      if (codeInput) codeInput.focus();
    }

    function startResendCooldown(seconds) {
      if (!resendButton) return;
      if (resendTimer) window.clearInterval(resendTimer);
      resendAvailableAt = Date.now() + Math.max(30, Number(seconds) || 30) * 1000;
      resendButton.disabled = true;
      resendButton.hidden = false;
      function tick() {
        var remaining = Math.max(0, Math.ceil((resendAvailableAt - Date.now()) / 1000));
        if (!remaining) {
          window.clearInterval(resendTimer);
          resendTimer = null;
          resendButton.disabled = false;
          resendButton.textContent = "Não recebi o código";
          return;
        }
        resendButton.textContent = "Não recebi o código · aguarde " + remaining + "s";
      }
      tick();
      resendTimer = window.setInterval(tick, 1000);
    }

    if (idInput) {
      idInput.addEventListener("input", function () {
        idInput.value = idInput.value.replace(/\D/g, "").slice(0, 19);
        idInput.setCustomValidity("");
      });
    }

    function requestAccessCode(isResend) {
      if (!isResend) {
        if (!idInput || !/^\d{1,19}$/.test(idInput.value.trim())) {
          if (idInput) { idInput.setCustomValidity("Use somente números, com até 19 dígitos."); idInput.reportValidity(); idInput.setCustomValidity(""); }
          return;
        }
      }
      if (isResend && Date.now() < resendAvailableAt) return;
      if (result) result.textContent = "";
      var activeButton = isResend ? resendButton : requestButton;
      if (isResend && activeButton) {
        activeButton.disabled = true;
        activeButton.setAttribute("aria-busy", "true");
        activeButton.textContent = "Enviando…";
      } else {
        setButtonBusy(activeButton, true, "Enviando código…");
      }
      attemptEndpoint("/api/member/auth/request", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(isResend ? {} : { peace_id: idInput.value.trim() })
      }, 60000)
        .then(parseLoginResponse)
        .then(function () {
          setStatusMessage(status, "Código enviado", "Enviamos um código de 6 números para sua DM no Discord.", "success");
          showCodeStep();
          if (idInput) idInput.value = "";
          startResendCooldown(30);
        })
        .catch(function (error) {
          setStatusMessage(status, "Não foi possível continuar", error.message || "Tente novamente.", "warning");
        })
        .finally(function () {
          if (isResend && activeButton) {
            activeButton.removeAttribute("aria-busy");
            if (Date.now() >= resendAvailableAt) activeButton.disabled = false;
          } else {
            setButtonBusy(activeButton, false);
          }
        });
    }

    if (requestForm) requestForm.addEventListener("submit", function (event) {
      event.preventDefault();
      requestAccessCode(false);
    });
    if (resendButton) resendButton.addEventListener("click", function () { requestAccessCode(true); });

    if (codeInput) {
      codeInput.addEventListener("input", syncCodeCells);
      codeInput.addEventListener("paste", function () { window.setTimeout(syncCodeCells, 0); });
      syncCodeCells();
    }

    if (verifyForm) verifyForm.addEventListener("submit", function (event) {
      event.preventDefault();
      syncCodeCells();
      if (!/^\d{6}$/.test(codeInput ? codeInput.value : "")) {
        if (codeInput) { codeInput.setCustomValidity("Digite os 6 números recebidos no Discord."); codeInput.reportValidity(); codeInput.setCustomValidity(""); }
        return;
      }
      setButtonBusy(verifyButton, true, "Validando…");
      if (result) result.textContent = "";
      attemptEndpoint("/api/member/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          code: codeInput.value,
          keep_connected: Boolean(keepConnected && keepConnected.checked),
        })
      }, 60000)
        .then(parseLoginResponse)
        .then(function (payload) {
          // New sessions are HttpOnly cookies. Remove only any pre-cookie
          // legacy token; never expose the fresh session to JavaScript.
          clearMemberSessionToken();
          setStatusMessage(status, "Acesso confirmado", "Abrindo sua área da Peace…", "success");
          window.setTimeout(function () { window.location.replace("/area/"); }, 260);
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
    if (params.get("status") === "session-expired") {
      setStatusMessage(status, "Sessão encerrada", "Entre novamente para continuar na área da Peace.", "warning");
    }
    if (params.get("status") === "logged-out") {
      setStatusMessage(status, "Sessão encerrada", "Você saiu deste dispositivo.", "success");
    }

    var existingToken = readMemberSessionToken();
    var existingHeaders = { Accept: "application/json", "Content-Type": "application/json" };
    if (existingToken) existingHeaders.Authorization = "Bearer " + existingToken;
    attemptEndpoint("/api/member/auth/session", {
      method: "POST",
      headers: existingHeaders,
      body: "{}",
    }, 15000)
      .then(function () { window.location.replace("/area/"); })
      .catch(function (error) {
        if (existingToken && error && (error.status === 401 || error.status === 403)) clearMemberSessionToken();
      });
  }


  site.initLogin = initLogin;
})(window);
