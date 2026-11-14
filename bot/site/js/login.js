(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;

  function initLogin() {
    if (site.body.dataset.page !== "login") return;
    var status = document.querySelector("[data-login-status]");
    var connect = document.querySelector("[data-login-discord]");
    var params = new URLSearchParams(window.location.search);
    var oauthStatus = params.get("oauth");
    if (oauthStatus) {
      params.delete("oauth");
      window.history.replaceState({}, document.title, window.location.pathname + (params.toString() ? "?" + params.toString() : "") + window.location.hash);
    }

    function show(message, tone) {
      var paragraph = status && status.querySelector("p");
      if (paragraph) paragraph.textContent = message;
      if (status) { status.hidden = false; status.dataset.state = tone || "pending"; }
    }

    if (oauthStatus === "cancelled") show("A conexão foi cancelada. Você pode tentar novamente.", "pending");
    if (oauthStatus === "unavailable" || oauthStatus === "not-configured") show("A conexão com Discord está temporariamente indisponível.", "error");
    if (oauthStatus === "issuer-error" || oauthStatus === "identity-error") show("Não foi possível confirmar a identidade retornada pelo Discord.", "error");

    site.getDiscordSession().then(function (session) {
      if (!session) return;
      var server = session.server || {};
      show(server.is_peace_member === true ? "Discord confirmado. Abrindo o painel Peace…" : "Discord confirmado. Abrindo seu próximo passo…", "success");
      window.setTimeout(function () {
        window.location.replace(server.is_peace_member === true ? "/area/" : "/meu-processo/");
      }, 180);
    });
    if (connect) connect.href = "/api/auth/discord/start?return_to=" + encodeURIComponent("/acessar/");
  }

  site.initLogin = initLogin;
})(window);
