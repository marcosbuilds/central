(function () {
  "use strict";

  var site = window.PeaceSite;
  if (!site) return;

  var statusNode = document.querySelector("[data-process-status]");
  var titleNode = document.querySelector("[data-process-title]");
  var copyNode = document.querySelector("[data-process-copy]");
  var kickerNode = document.querySelector("[data-process-kicker]");
  var idNode = document.querySelector("[data-process-discord-id]");
  var usernameNode = document.querySelector("[data-process-username]");
  var membershipNode = document.querySelector("[data-process-membership]");
  var membershipNoteNode = document.querySelector("[data-process-membership-note]");
  var connectLink = document.querySelector("[data-process-connect]");
  var setLink = document.querySelector("[data-process-set-link]");
  var scorePanel = document.querySelector("[data-process-score]");
  var scoreValueNode = document.querySelector("[data-process-score-value]");
  var scoreCopyNode = document.querySelector("[data-process-score-copy]");
  var logoutButton = document.querySelector("[data-discord-logout]");
  var retryButton = document.querySelector("[data-process-retry]");
  var resultsPanel = document.querySelector("[data-process-results]");
  var connectionPanel = document.querySelector("#conexao");
  var processDetails = document.querySelector(".process-details");
  var setRequestPanel = document.querySelector("[data-process-set]");
  var assignmentList = document.querySelector("[data-process-assignment-list]");
  var stepNodes = {
    identity: document.querySelector('[data-process-step="identity"]'),
    exam: document.querySelector('[data-process-step="exam"]'),
    result: document.querySelector('[data-process-step="result"]')
  };

  function setText(node, value) { if (node) node.textContent = value; }

  function showStatus(message, tone) {
    setText(statusNode, message || "");
    if (statusNode) statusNode.dataset.state = tone || "pending";
  }

  function request(url, options) {
    return site.attemptEndpoint(url, Object.assign({ headers: { Accept: "application/json" } }, options || {}), 12000)
      .then(function (response) { return response.json(); });
  }

  function formatDate(value) {
    try {
      return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
    } catch (error) {
      return value || "—";
    }
  }

  function statusLabel(assignment) {
    if (assignment.status === "pending_approval") return "Resultado enviado · aguarda aprovação";
    if (assignment.status === "approved") return "Aprovado";
    if (assignment.status === "submitted") return assignment.passed ? "Aprovado" : "Não aprovado";
    if (assignment.status === "in_progress") return "Em andamento";
    if (assignment.status === "expired") return "Prazo encerrado";
    if (assignment.status === "revoked" || assignment.status === "rejected") return "Reprovado";
    return "Aguardando início";
  }

  function renderAssignments(assignments) {
    if (!assignmentList || !resultsPanel) return;
    assignmentList.textContent = "";
    if (!assignments.length) {
      resultsPanel.hidden = true;
      return;
    }
    resultsPanel.hidden = false;
    assignments.forEach(function (assignment) {
      var item = document.createElement("article");
      item.className = "process-assignment";
      var main = document.createElement("div");
      var heading = document.createElement("h3");
      heading.textContent = (assignment.exam_type_label || "Prova teórica — Civil") + " · atribuição #" + assignment.id;
      var description = document.createElement("p");
      description.textContent = assignment.deadline_at ? "Termina em " + formatDate(assignment.deadline_at) : "Tempo de " + (assignment.duration_hours || 24) + "h após iniciar";
      var meta = document.createElement("div");
      meta.className = "process-assignment-meta";
      meta.innerHTML = "<span>" + statusLabel(assignment) + "</span><span>" + (assignment.correct_count === null ? "ainda não realizada" : assignment.correct_count + "/" + (assignment.question_count || "—") + " acertos") + "</span>";
      main.appendChild(heading);
      main.appendChild(description);
      main.appendChild(meta);
      var result = document.createElement("div");
      result.className = "process-assignment-result";
      if (assignment.score === null) {
        result.innerHTML = "<small>Nota</small><strong>—</strong>";
      } else {
        result.innerHTML = "<small>Nota</small><strong>" + assignment.score + "/100</strong>";
      }
      item.appendChild(main);
      item.appendChild(result);
      assignmentList.appendChild(item);
    });
  }

  function renderSetRequests(items) {
    if (!setRequestPanel) return;
    setRequestPanel.replaceChildren();
    if (!Array.isArray(items) || !items.length) { setRequestPanel.hidden = true; return; }
    setRequestPanel.hidden = false;
    items.slice(0, 3).forEach(function (item) {
      var row = document.createElement("article"); row.className = "process-set-row";
      var heading = document.createElement("div"); heading.className = "process-set-row-heading";
      var title = document.createElement("strong"); title.textContent = "Setagem · " + (item.in_game_username || "processo");
      var tag = document.createElement("span"); tag.className = "status-tag status-tag--" + (item.status === "approved" ? "ready" : item.status === "rejected" ? "error" : "pending"); tag.textContent = item.status === "approved" ? "Aprovada" : item.status === "rejected" ? "Reprovada" : "Pendente";
      heading.append(title, tag);
      var copy = document.createElement("p"); copy.textContent = "Solicitada em " + formatDate(item.created_at) + (item.source ? " · origem " + item.source : "");
      row.append(heading, copy); setRequestPanel.appendChild(row);
    });
  }

  function updateSteps(assignments) {
    var hasAssignment = assignments.length > 0;
    var hasResult = assignments.some(function (item) { return ["submitted", "pending_approval", "approved", "rejected"].includes(item.status); });
    setText(stepNodes.identity, "Identidade confirmada");
    setText(stepNodes.exam, hasAssignment ? "Atribuição registrada" : "Aguardando atribuição");
     setText(stepNodes.result, hasResult ? "Resultado enviado" : "Aguardando envio");
  }

  function renderProcess(data) {
    var identity = data.identity || {};
    var assignments = Array.isArray(data.assignments) ? data.assignments : [];
    var membership = data.server || {};
    var profile = data.profile || {};
    setText(kickerNode, "Identidade confirmada");
    setText(titleNode, assignments.length ? "Seu processo está vinculado." : "Conta conectada; aguardando atribuição.");
    setText(copyNode, assignments.length ? "Confira suas etapas abaixo e abra a prova pelo link enviado pela Gerência." : "A Gerência ainda não atribuiu uma prova a esta conta. Você pode continuar estudando enquanto aguarda.");
    setText(idNode, identity.discord_id || "—");
    setText(usernameNode, identity.username ? "@" + identity.username : "—");
    if (membershipNode) {
      setText(membershipNode, membership.state === "peace" ? "Sim, cargo Peace confirmado." : membership.state === "member" ? "Conta encontrada; cargo Peace ainda não confirmado." : membership.state === "not_member" ? "Ainda não possui vínculo com a Peace." : "Confirmação do cargo indisponível agora.");
    }
    if (membershipNoteNode) {
      membershipNoteNode.hidden = false;
      var membershipCopy = membership.state === "peace"
        ? "Sua conta já tem o cargo Peace. A área de membros pode mostrar o processo e a prova atribuída."
        : membership.state === "member"
          ? "Sua conta foi encontrada, mas o cargo Peace ainda não foi localizado. Use o fluxo de entrada quando a Gerência orientar."
          : membership.state === "not_member"
            ? "Sua conta Discord foi identificada, mas ainda não possui vínculo com a Peace. Entre pelo fluxo de entrada para pedir set."
            : "A conta está conectada, mas a confirmação do cargo ainda não respondeu.";
      setText(membershipNoteNode, membershipCopy);
      membershipNoteNode.dataset.state = membership.state || "unavailable";
    }
    if (setLink) setLink.hidden = membership.state === "peace";
    if (connectLink) connectLink.hidden = true;
    if (connectionPanel) connectionPanel.classList.add("is-process-ready");
    if (processDetails) processDetails.hidden = true;
    document.querySelectorAll(".process-identity-actions, [data-process-membership-note], .process-identity-list").forEach(function (node) { node.hidden = true; });
    if (scorePanel) scorePanel.hidden = false;
    if (scoreValueNode) setText(scoreValueNode, profile.score === null || profile.score === undefined ? "—" : profile.score + "/" + (profile.score_scale || 100));
    if (scoreCopyNode) setText(scoreCopyNode, profile.score === null || profile.score === undefined ? "Nenhuma avaliação concluída ainda." : "Média das avaliações concluídas.");
    if (logoutButton) logoutButton.hidden = false;
    renderAssignments(assignments);
    renderSetRequests(data.set_requests);
    if (resultsPanel && Array.isArray(data.set_requests) && data.set_requests.length) resultsPanel.hidden = false;
    updateSteps(assignments);
    showStatus("", "ready");
  }

  function showDisconnected(message) {
    setText(kickerNode, "Identidade ainda não conectada");
    setText(titleNode, "Conecte o Discord para abrir seu processo.");
    setText(copyNode, "O site mostrará somente as etapas vinculadas à conta conectada.");
    setText(idNode, "Aguardando conexão.");
    setText(usernameNode, "Identificação visual.");
    setText(membershipNode, "Será confirmado.");
    if (membershipNoteNode) {
      membershipNoteNode.textContent = "";
      membershipNoteNode.hidden = true;
      membershipNoteNode.dataset.state = "pending";
    }
    if (setLink) setLink.hidden = true;
    if (connectLink) connectLink.hidden = false;
    if (scorePanel) scorePanel.hidden = true;
    if (logoutButton) logoutButton.hidden = true;
    if (resultsPanel) resultsPanel.hidden = true;
    if (retryButton) retryButton.hidden = true;
    showStatus(message || "Conecte sua conta Discord para continuar.", "pending");
  }

  function showUnavailable(message) {
    setText(kickerNode, "Verificação temporariamente indisponível");
    setText(titleNode, "O processo continua protegido.");
    setText(copyNode, "Não foi possível validar sua sessão ou consultar o processo agora. Tente novamente sem iniciar outro login.");
    setText(idNode, "Aguardando nova validação.");
    setText(usernameNode, "A identidade não foi liberada.");
    setText(membershipNode, "Confirmação pendente.");
    if (membershipNoteNode) {
      membershipNoteNode.textContent = "A área permanece fechada até a confirmação completa da conta.";
      membershipNoteNode.hidden = false;
      membershipNoteNode.dataset.state = "unavailable";
    }
    if (setLink) setLink.hidden = true;
    if (connectLink) connectLink.hidden = true;
    if (retryButton) { retryButton.hidden = false; retryButton.disabled = false; }
    if (scorePanel) scorePanel.hidden = true;
    if (logoutButton) logoutButton.hidden = true;
    if (resultsPanel) resultsPanel.hidden = true;
    showStatus(message || "A conexão está temporariamente indisponível. Tente validar novamente em instantes.", "error");
  }

  function cleanOAuthStatus() {
    var url = new URL(window.location.href);
    var status = url.searchParams.get("oauth");
    if (!status) return;
    url.searchParams.delete("oauth");
    window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : "") + url.hash);
    if (status === "connected") showStatus("Discord conectado. Consultando seu processo…", "success");
    if (status === "cancelled") showStatus("A conexão foi cancelada. Você pode tentar novamente.", "pending");
    if (status === "unavailable") showStatus("A conexão com Discord está temporariamente indisponível.", "error");
    if (status === "not-configured") showStatus("A conexão com Discord ainda não foi configurada neste ambiente.", "error");
    if (status === "issuer-error" || status === "identity-error") showStatus("Não consegui confirmar a resposta do Discord.", "error");
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", function () {
      logoutButton.disabled = true;
      request("/api/auth/discord/logout", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" })
        .then(function () { window.location.reload(); })
        .catch(function () { logoutButton.disabled = false; showStatus("Não consegui encerrar a sessão agora.", "error"); });
    });
  }

  function loadProcess() {
    if (retryButton) { retryButton.disabled = true; retryButton.hidden = true; }
    showStatus("Validando sessão e processo…", "pending");
    var sessionRequest = typeof site.getDiscordSession === "function"
      ? site.getDiscordSession()
      : request("/api/auth/discord/session");
    sessionRequest
      .then(function (session) {
        if (!session || session.ok !== true || !session.identity) {
          var sharedError = site.discordSessionError || new Error("Sessão Discord inválida.");
          if (!sharedError.status) sharedError.status = 401;
          throw sharedError;
        }
        return request("/api/exams/process").then(function (process) {
          if (!process || process.ok !== true || !process.identity || !Array.isArray(process.assignments)) {
            var processError = new Error("Processo indisponível.");
            processError.status = 503;
            throw processError;
          }
          renderProcess(process);
        });
      })
      .catch(function (error) {
        if (error && error.status === 401) {
          showDisconnected();
          return;
        }
        showUnavailable("A consulta do processo está temporariamente indisponível. Tente validar novamente em instantes.");
      });
  }

  if (retryButton) retryButton.addEventListener("click", loadProcess);
  cleanOAuthStatus();
  loadProcess();
})();
