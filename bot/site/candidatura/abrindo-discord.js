(function () {
  "use strict";

  if (new URLSearchParams(window.location.search).get("state") !== "error") return;
  var title = document.querySelector("[data-title]");
  var message = document.querySelector("[data-message]");
  var loader = document.querySelector("[data-loader]");
  if (title) title.textContent = "Não foi possível gerar o convite.";
  if (message) message.textContent = "Volte para a guia da Peace e tente novamente em alguns instantes.";
  if (loader) loader.hidden = true;
}());
