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
  var setLink = document.querySelector("[data-process-set-link]");
  var scorePanel = document.querySelector("[data-process-score]");
  var scoreValueNode = document.querySelector("[data-process-score-value]");
  var scoreCopyNode = document.querySelector("[data-process-score-copy]");
  var logoutButton = document.querySelector("[data-discord-logout]");
  var resultsPanel = document.querySelector("[data-process-results]");
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
    if (assignment.status === "submitted") return assignment.passed ? "Aprovado" : "Não aprovado";
    if (assignment.status === "in_progress") return "Em andamento";
    if (assignment.status === "expired") return "Prazo encerrado";
    if (assignment.status === "revoked") return "Revogada";
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
      heading.textContent = "Apostila Civil · atribuição #" + assignment.id;
      var description = document.createElement("p");
      description.textContent = "Prazo: " + formatDate(assignment.deadline_at) + " · versão " + assignment.question_bank_version;
      var meta = document.createElement("div");
      meta.className = "process-assignment-meta";
      meta.innerHTML = "<span>" + statusLabel(assignment) + "</span><span>" + (assignment.correct_count === null ? "tentativa única" : assignment.correct_count + "/10 acertos") + "</span>";
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

  function updateSteps(assignments) {
    var hasAssignment = assignments.length > 0;
    var hasResult = assignments.some(function (item) { return item.status === "submitted"; });
    setText(stepNodes.identity, "Identidade confirmada");
    setText(stepNodes.exam, hasAssignment ? "Atribuição registrada" : "Aguardando atribuição");
    setText(stepNodes.result, hasResult ? "Resultado disponível" : "Aguardando envio");
  }

  function renderProcess(data) {
    var identity = data.identity || {};
    var assignments = Array.isArray(data.assignments) ? data.assignments : [];
    var membership = data.server || {};
    var profile = data.profile || {};
    setText(kickerNode, "Identidade confirmada");
    setText(titleNode, assignments.length ? "Seu processo está vinculado." : "Conta conectada; aguardando atribuição.");
    setText(copyNode, assignments.length ? "O histórico abaixo pertence ao Discord ID conectado. Abra a prova pelo link enviado pela Gerência." : "A Gerência ainda não atribuiu uma prova a esta conta. Você pode continuar estudando enquanto aguarda.");
    setText(idNode, identity.discord_id || "—");
    setText(usernameNode, identity.username ? "@" + identity.username : "—");
    if (membershipNode) {
      setText(membershipNode, membership.state === "peace" ? "Sim, cargo Peace confirmado." : membership.state === "member" ? "Está no servidor; cargo Peace ainda não confirmado." : membership.state === "not_member" ? "Ainda não está no servidor." : "Confirmação do servidor indisponível agora.");
    }
    if (membershipNoteNode) {
      var membershipCopy = membership.state === "peace"
        ? "Sua conta já está vinculada ao servidor Peace. O painel público pode mostrar o processo e a prova atribuída."
        : membership.state === "member"
          ? "Sua conta está no servidor, mas o cargo Peace ainda não foi localizado. Use o fluxo de entrada para pedir set quando a Gerência orientar."
          : membership.state === "not_member"
            ? "Sua conta Discord foi identificada, mas ainda não está no servidor. Entre pelo fluxo de entrada para pedir set."
            : "A conta está conectada, mas o Discord não respondeu a confirmação de servidor agora.";
      setText(membershipNoteNode, membershipCopy);
      membershipNoteNode.dataset.state = membership.state || "unavailable";
    }
    if (setLink) setLink.hidden = membership.state === "peace";
    if (scorePanel) scorePanel.hidden = false;
    if (scoreValueNode) setText(scoreValueNode, profile.score === null || profile.score === undefined ? "—" : profile.score + "/" + (profile.score_scale || 100));
    if (scoreCopyNode) setText(scoreCopyNode, profile.score === null || profile.score === undefined ? "Nenhuma prova enviada ainda." : (profile.passed ? "Aprovado na última prova registrada." : "Não aprovado na última prova registrada."));
    if (logoutButton) logoutButton.hidden = false;
    renderAssignments(assignments);
    updateSteps(assignments);
  }

  function showDisconnected(message) {
    setText(kickerNode, "Identidade ainda não conectada");
    setText(titleNode, "Conecte o Discord para abrir seu processo.");
    setText(copyNode, "O site confirmará a conta pela autorização oficial do Discord e mostrará somente os registros pertencentes ao seu Discord ID.");
    setText(idNode, "Aguardando conexão.");
    setText(usernameNode, "Identificação visual.");
    setText(membershipNode, "Será confirmado pelo servidor.");
    setText(membershipNoteNode, "Conecte o Discord para confirmar se sua conta está no servidor e qual é o próximo passo.");
    if (membershipNoteNode) membershipNoteNode.dataset.state = "pending";
    if (setLink) setLink.hidden = true;
    if (scorePanel) scorePanel.hidden = true;
    if (logoutButton) logoutButton.hidden = true;
    if (resultsPanel) resultsPanel.hidden = true;
    showStatus(message || "Conecte sua conta Discord para continuar.", "pending");
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

  cleanOAuthStatus();
  request("/api/auth/discord/session")
    .then(function (session) {
      return request("/api/exams/process").then(function (process) {
        renderProcess(process);
      });
    })
    .catch(function (error) {
      if (error && error.status === 401) {
        showDisconnected();
        return;
      }
      showDisconnected("A consulta do processo está temporariamente indisponível. Tente novamente em instantes.");
    });
})();
