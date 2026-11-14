(function () {
  "use strict";

  var site = window.PeaceSite;
  if (!site) return;
  var gate = document.querySelector("[data-manager-gate]");
  var workspace = document.querySelector("[data-manager-workspace]");
  var message = document.querySelector("[data-manager-message]");
  var formMessage = document.querySelector("[data-manager-form-message]");
  var form = document.querySelector("[data-manager-form]");
  var submitButton = document.querySelector("[data-manager-submit]");
  var list = document.querySelector("[data-manager-list]");
  var generated = document.querySelector("[data-manager-generated]");
  var generatedLink = document.querySelector("[data-manager-generated-link]");
  var logoutButton = document.querySelector("[data-manager-logout]");

  function setText(node, value) { if (node) node.textContent = value; }
  function request(url, options) {
    return site.attemptEndpoint(url, Object.assign({ headers: { Accept: "application/json" } }, options || {}), 15000)
      .then(function (response) { return response.json(); });
  }
  function setMessage(node, text, tone) { setText(node, text || ""); if (node) node.dataset.state = tone || "pending"; }
  function showGate(messageText) {
    if (gate) gate.hidden = false;
    if (workspace) workspace.hidden = true;
    setMessage(message, messageText, "error");
    var connect = gate && gate.querySelector("[data-manager-connect]");
    if (connect) connect.hidden = true;
    var title = gate && gate.querySelector("h2");
    if (title) title.textContent = "Discord conectado; cargo de Gerência necessário.";
  }
  function date(value) {
    try { return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); } catch (error) { return value || "—"; }
  }
  function statusLabel(item) {
    if (item.status === "submitted") return item.passed ? "Aprovado" : "Não aprovado";
    if (item.status === "in_progress") return "Em andamento";
    if (item.status === "expired") return "Prazo encerrado";
    return "Aguardando candidato";
  }
  function renderList(assignments) {
    if (!list) return;
    list.textContent = "";
    if (!assignments.length) {
      var empty = document.createElement("p");
      empty.className = "field-note";
      empty.textContent = "Nenhuma atribuição criada por esta conta ainda.";
      list.appendChild(empty);
      return;
    }
    assignments.forEach(function (item) {
      var row = document.createElement("article");
      row.className = "manager-assignment";
      var copy = document.createElement("div");
      var heading = document.createElement("h3");
      heading.textContent = "#" + item.id + " · " + item.candidate_username;
      var detail = document.createElement("p");
      detail.textContent = "Discord ID " + (item.candidate_discord_user_id || "—") + " · Prazo " + date(item.deadline_at) + " · " + (item.score === null ? "sem resultado" : "nota " + item.score + "/100");
      copy.appendChild(heading);
      copy.appendChild(detail);
      var badge = document.createElement("span");
      badge.className = "status-tag " + (item.status === "submitted" && item.passed ? "status-tag--ready" : "status-tag--planned");
      badge.textContent = statusLabel(item);
      row.appendChild(copy);
      row.appendChild(badge);
      list.appendChild(row);
    });
  }
  function cleanStatus() {
    var url = new URL(window.location.href);
    var status = url.searchParams.get("oauth");
    if (!status) return;
    url.searchParams.delete("oauth");
    window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : "") + url.hash);
    if (status === "connected") setMessage(message, "Discord conectado. Verificando Gerência…", "success");
    if (status === "cancelled") setMessage(message, "A conexão foi cancelada.", "pending");
    if (status === "unavailable") setMessage(message, "A conexão com Discord está temporariamente indisponível.", "error");
    if (status === "not-configured") setMessage(message, "A conexão com Discord ainda não foi configurada neste ambiente.", "error");
    if (status === "issuer-error" || status === "identity-error") setMessage(message, "Não foi possível confirmar a identidade no Discord. Tente conectar novamente.", "error");
  }
  function openWorkspace() {
    if (gate) gate.hidden = true;
    if (workspace) workspace.hidden = false;
    if (logoutButton) logoutButton.hidden = false;
    return request("/api/exams/assignments").then(function (payload) { renderList(payload.assignments || []); });
  }

  if (form) {
    var deadlineInput = form.elements.deadline_at;
    if (deadlineInput) {
      var initial = new Date(Date.now() + 24 * 60 * 60 * 1000);
      initial.setSeconds(0, 0);
      deadlineInput.value = new Date(initial.getTime() - initial.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var formData = new FormData(form);
      var deadlineDate = new Date(String(formData.get("deadline_at") || ""));
      if (!formData.get("candidate_discord_user_id") || !formData.get("candidate_username") || !Number.isFinite(deadlineDate.getTime())) {
        setMessage(formMessage, "Preencha o ID, o username e o prazo.", "error");
        return;
      }
      submitButton.disabled = true;
      setMessage(formMessage, "Gerando atribuição…", "pending");
      request("/api/exams/assignments", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify({ candidate_discord_user_id: String(formData.get("candidate_discord_user_id")), candidate_username: String(formData.get("candidate_username")), deadline_at: deadlineDate.toISOString() }) })
        .then(function (payload) {
          setMessage(formMessage, "Atribuição criada. Copie o link antes de sair.", "success");
          if (generated) generated.hidden = false;
          setText(generatedLink, payload.access_url || "");
          return request("/api/exams/assignments").then(function (updated) { renderList(updated.assignments || []); });
        })
        .catch(function (error) { setMessage(formMessage, error.message || "Não consegui gerar a prova.", "error"); })
        .then(function () { submitButton.disabled = false; });
    });
  }
  if (logoutButton) {
    logoutButton.addEventListener("click", function () {
      logoutButton.disabled = true;
      request("/api/auth/discord/logout", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" }).then(function () { window.location.reload(); }).catch(function () { logoutButton.disabled = false; setMessage(formMessage, "Não consegui encerrar a sessão agora.", "error"); });
    });
  }
  cleanStatus();
  request("/api/auth/discord/session")
    .then(function (session) {
      if (!session || !session.server || session.server.is_manager !== true) {
        showGate("Sua conta Discord está identificada, mas o cargo de Gerência não foi confirmado.");
        return null;
      }
      return openWorkspace();
    })
    .catch(function (error) {
      if (error && error.status === 403) showGate("Sua conta Discord está identificada, mas o cargo de Gerência não foi confirmado.");
      else if (error && error.status === 401) {
        if (gate) gate.hidden = false;
        if (workspace) workspace.hidden = true;
        setMessage(message, "Conecte uma conta Discord para continuar.", "pending");
      }
      else if (error && error.code === "EXAM_NOT_CONFIGURED") setMessage(message, "O gabarito protegido ainda não está configurado neste ambiente.", "error");
      else setMessage(message, error.message || "Não consegui verificar a gerência agora.", "error");
    });
})();
