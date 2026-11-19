(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site || site.body.dataset.page !== "entry") return;

  var startLink = document.querySelector("[data-entry-start]");
  var sessionState = document.querySelector("[data-entry-session-state]");
  var params = new URLSearchParams(window.location.search);
  var defaultStartLabel = (startLink && startLink.querySelector("[data-entry-start-label]") || {}).textContent || "Começar entrada";

  function setStartBusy(busy) {
    if (!startLink) return;
    startLink.classList.toggle("is-loading", busy);
    startLink.setAttribute("aria-disabled", busy ? "true" : "false");
    startLink.setAttribute("aria-busy", busy ? "true" : "false");
    if (busy) startLink.setAttribute("tabindex", "-1");
    else startLink.removeAttribute("tabindex");
    var label = startLink.querySelector("[data-entry-start-label]");
    if (label) label.textContent = busy ? "Conectando Discord…" : defaultStartLabel;
  }

  function showSessionState(message, tone) {
    if (!sessionState) return;
    sessionState.hidden = false;
    sessionState.dataset.state = tone || "pending";
    var copy = sessionState.querySelector("[data-entry-session-copy]");
    if (copy) copy.textContent = message;
  }

  setStartBusy(true);
  site.getDiscordSession().then(function (session) {
    if (!session) return;
    var server = session.server || {};
    document.body.dataset.entryDiscordConnected = "true";
    document.body.dataset.entryPeaceMember = server.is_peace_member === true ? "true" : "false";
    if (server.is_peace_member === true) {
      showSessionState("Sua conta já tem o cargo Peace. Abrindo a área de membros…", "success");
      window.location.replace("/area/");
      return;
    }
    if (server.is_member === true) {
      if (startLink) {
        startLink.href = "/candidatura/?connected=1";
        var label = startLink.querySelector("[data-entry-start-label]");
        if (label) label.textContent = server.is_verified === true ? "Continuar entrevista" : "Continuar verificação";
      }
      showSessionState(
        server.is_verified === true
          ? "Sua conta já participa da Peace. Continue pela entrevista; não é necessário gerar outro convite."
          : "Sua conta já participa da Peace. Conclua a verificação no Discord; não é necessário gerar outro convite.",
        server.is_verified === true ? "success" : "pending"
      );
      // A connected member should land directly in the current entry state;
      // the candidature page resolves verification versus interview from the
      // live server response and never grants a role from this redirect.
      window.setTimeout(function () { window.location.replace("/candidatura/?connected=1"); }, 220);
    }
    if (params.get("from") === "candidature") {
      showSessionState("Você voltou da candidatura. Seu rascunho continua salvo nesta sessão.", "pending");
    }
  }).finally(function () { setStartBusy(false); });
})(window);
