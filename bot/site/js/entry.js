(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site || site.body.dataset.page !== "entry") return;

  var startLink = document.querySelector("[data-entry-start]");
  var sessionState = document.querySelector("[data-entry-session-state]");
  var params = new URLSearchParams(window.location.search);

  function showSessionState(message, tone) {
    if (!sessionState) return;
    sessionState.hidden = false;
    sessionState.dataset.state = tone || "pending";
    var copy = sessionState.querySelector("[data-entry-session-copy]");
    if (copy) copy.textContent = message;
  }

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
    }
    if (params.get("from") === "candidature") {
      showSessionState("Você voltou da candidatura. Seu rascunho continua salvo nesta sessão.", "pending");
    }
  });
})(window);
