(function () {
  "use strict";

  var site = window.PeaceSite;
  if (!site) return;

  var authPanel = document.querySelector("[data-exam-auth]");
  var assignmentPanel = document.querySelector("[data-exam-assignment]");
  var formPanel = document.querySelector("[data-exam-form-panel]");
  var resultPanel = document.querySelector("[data-exam-result]");
  var messageNode = document.querySelector("[data-exam-message]");
  var submitMessageNode = document.querySelector("[data-exam-submit-message]");
  var questionsNode = document.querySelector("[data-exam-questions]");
  var form = document.querySelector("[data-exam-form]");
  var startButton = document.querySelector("[data-exam-start]");
  var submitButton = document.querySelector("[data-exam-submit]");
  var assignmentState = null;
  var countdownTimer = null;
  var accessStorageKey = "peace.exam.access.v1";

  function setText(node, value) { if (node) node.textContent = value; }

  function request(url, options) {
    return site.attemptEndpoint(url, Object.assign({ headers: { Accept: "application/json" } }, options || {}), 15000)
      .then(function (response) { return response.json(); });
  }

  function readAccessToken() {
    var url = new URL(window.location.href);
    var fromUrl = url.searchParams.get("access");
    if (fromUrl) {
      try { sessionStorage.setItem(accessStorageKey, fromUrl); } catch (error) { /* optional */ }
      url.searchParams.delete("access");
      window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : "") + url.hash);
      return fromUrl;
    }
    try { return sessionStorage.getItem(accessStorageKey) || ""; } catch (error) { return ""; }
  }

  function formatDate(value) {
    try { return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); } catch (error) { return value || "—"; }
  }

  function showMessage(message, tone) {
    setText(messageNode, message || "");
    if (messageNode) messageNode.dataset.state = tone || "pending";
  }

  function showSubmitMessage(message, tone) {
    setText(submitMessageNode, message || "");
    if (submitMessageNode) submitMessageNode.dataset.state = tone || "pending";
  }

  function showConnectedAwaitingAssignment() {
    var title = document.querySelector("#exam-auth-title");
    var copy = authPanel && authPanel.querySelector("p:not(.eyebrow):not(.form-status)");
    var connect = authPanel && authPanel.querySelector("[data-discord-connect]");
    if (title) title.textContent = "Discord identificado.";
    if (copy) copy.textContent = "Sua conta está conectada. Abra o link individual enviado pela Gerência para consultar a prova atribuída.";
    if (connect) connect.hidden = true;
    showMessage("Nenhuma atribuição foi aberta nesta página. Use o link individual da Gerência.", "success");
  }

  function cleanOAuthStatus() {
    var url = new URL(window.location.href);
    var status = url.searchParams.get("oauth");
    if (!status) return;
    url.searchParams.delete("oauth");
    window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : "") + url.hash);
    if (status === "connected") showMessage("Discord conectado. Consultando sua atribuição…", "success");
    if (status === "cancelled") showMessage("A conexão foi cancelada. Você pode tentar novamente.", "pending");
    if (status === "unavailable") showMessage("A conexão com Discord está temporariamente indisponível.", "error");
    if (status === "not-configured") showMessage("A conexão com Discord ainda não foi configurada neste ambiente.", "error");
    if (status === "issuer-error" || status === "identity-error") showMessage("Não foi possível confirmar a identidade no Discord. Tente conectar novamente.", "error");
  }

  function statusLabel(assignment) {
    if (assignment.status === "submitted") return assignment.passed ? "Aprovado" : "Não aprovado";
    if (assignment.status === "in_progress") return "Em andamento";
    return "Aguardando início";
  }

  function renderAssignment(assignment) {
    assignmentState = assignment;
    if (authPanel) authPanel.hidden = true;
    if (resultPanel) resultPanel.hidden = true;
    if (formPanel) formPanel.hidden = true;
    if (assignmentPanel) assignmentPanel.hidden = false;
    setText(document.querySelector("[data-exam-version]"), assignment.question_bank_version || "—");
    setText(document.querySelector("[data-exam-passing]"), (assignment.passing_score || 0) + "/100");
    setText(document.querySelector("[data-exam-deadline]"), formatDate(assignment.deadline_at));
    setText(document.querySelector("[data-exam-status]"), statusLabel(assignment));
    if (assignment.status === "submitted") {
      showResult({ score: assignment.score, scale: 100, passing_score: assignment.passing_score, correct_count: assignment.correct_count, total_questions: 10, passed: assignment.passed, submitted_at: assignment.submitted_at });
      return;
    }
    if (startButton) {
      startButton.hidden = false;
      startButton.disabled = false;
      startButton.textContent = assignment.status === "in_progress" ? "Continuar prova →" : "Iniciar prova →";
    }
  }

  function renderQuestions(questions) {
    if (!questionsNode) return;
    questionsNode.textContent = "";
    questions.forEach(function (question, questionIndex) {
      var fieldset = document.createElement("fieldset");
      fieldset.className = "exam-question";
      var legend = document.createElement("legend");
      legend.textContent = (questionIndex + 1) + ". " + question.prompt;
      fieldset.appendChild(legend);
      if (question.context) {
        var context = document.createElement("p");
        context.className = "exam-question-context";
        context.textContent = question.context;
        fieldset.appendChild(context);
      }
      var options = document.createElement("div");
      options.className = "exam-options";
      question.options.forEach(function (option, optionIndex) {
        var label = document.createElement("label");
        label.className = "exam-option";
        var input = document.createElement("input");
        input.type = "radio";
        input.name = question.id;
        input.value = String(optionIndex);
        input.required = true;
        var text = document.createElement("span");
        text.textContent = option;
        label.appendChild(input);
        label.appendChild(text);
        options.appendChild(label);
      });
      fieldset.appendChild(options);
      questionsNode.appendChild(fieldset);
    });
  }

  function startCountdown(deadline) {
    if (countdownTimer) window.clearInterval(countdownTimer);
    var clock = document.querySelector("[data-exam-clock]");
    function update() {
      var remaining = new Date(deadline).getTime() - Date.now();
      if (!Number.isFinite(remaining) || remaining <= 0) {
        setText(clock, "Prazo encerrado");
        if (submitButton) submitButton.disabled = true;
        showSubmitMessage("O prazo terminou. O servidor recusará qualquer envio depois do limite.", "error");
        return;
      }
      var minutes = Math.floor(remaining / 60000);
      var hours = Math.floor(minutes / 60);
      minutes %= 60;
      setText(clock, "Prazo: " + (hours ? hours + "h " : "") + minutes + "min");
    }
    update();
    countdownTimer = window.setInterval(update, 30000);
  }

  function openAttempt(payload) {
    if (assignmentPanel) assignmentPanel.hidden = true;
    if (formPanel) formPanel.hidden = false;
    renderQuestions(payload.attempt.questions || []);
    startCountdown(payload.assignment.deadline_at);
    if (submitButton) submitButton.disabled = false;
  }

  function showResult(result, deliveryStatus) {
    if (assignmentPanel) assignmentPanel.hidden = true;
    if (formPanel) formPanel.hidden = true;
    if (resultPanel) resultPanel.hidden = false;
    var score = result && result.score !== null && result.score !== undefined ? result.score : "—";
    setText(document.querySelector("[data-exam-score]"), score + "/100");
    var deliveryCopy = deliveryStatus === "sent"
      ? " O resultado também foi enviado uma única vez ao gerente que criou a atribuição."
      : " O resultado foi registrado, mas a entrega ao gerente precisa ser revisada pela equipe.";
    setText(document.querySelector("[data-exam-result-copy]"), result && result.passed
      ? "Você atingiu a nota mínima de " + result.passing_score + "." + deliveryCopy
      : "A nota mínima era " + (result ? result.passing_score : "a configurada pela equipe") + "." + deliveryCopy + " Esta prova não pode ser refeita.");
  }

  function loadExistingResult(assignmentId) {
    return request("/api/exams/process").then(function (process) {
      var assignment = (process.assignments || []).find(function (item) { return Number(item.id) === Number(assignmentId); });
      if (assignment) showResult({ score: assignment.score, passing_score: assignment.passing_score, passed: assignment.passed });
    });
  }

  if (startButton) {
    startButton.addEventListener("click", function () {
      var accessToken = readAccessToken();
      if (!accessToken) { showMessage("O link individual da prova não está nesta sessão.", "error"); return; }
      startButton.disabled = true;
      startButton.textContent = "Abrindo prova…";
      request("/api/exams/start", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify({ access_token: accessToken }) })
        .then(openAttempt)
        .catch(function (error) {
          startButton.disabled = false;
          startButton.textContent = "Iniciar prova →";
          if (error && error.code === "EXAM_ALREADY_SUBMITTED") { loadExistingResult(assignmentState && assignmentState.id); return; }
          showMessage(error.message || "Não consegui abrir a prova.", "error");
        });
    });
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!assignmentState || !submitButton) return;
      var answers = {};
      var unanswered = null;
      Array.prototype.forEach.call(form.querySelectorAll("fieldset"), function (fieldset) {
        var selected = fieldset.querySelector("input:checked");
        var firstInput = fieldset.querySelector("input");
        if (!selected && !unanswered) unanswered = firstInput;
        if (selected) answers[selected.name] = Number(selected.value);
      });
      if (unanswered) {
        showSubmitMessage("Responda todas as questões antes do envio definitivo.", "error");
        unanswered.focus();
        return;
      }
      if (!window.confirm("O envio é definitivo e não permite refazer. Deseja enviar agora?")) return;
      submitButton.disabled = true;
      showSubmitMessage("Corrigindo a tentativa no servidor…", "pending");
      request("/api/exams/submit", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify({ assignment_id: assignmentState.id, answers: answers }) })
        .then(function (payload) { showResult(payload.result, payload.manager_delivery); })
        .catch(function (error) {
          submitButton.disabled = false;
          showSubmitMessage(error.message || "Não consegui enviar a prova.", "error");
        });
    });
  }

  cleanOAuthStatus();
  var accessToken = readAccessToken();
  request("/api/auth/discord/session")
    .then(function () {
      if (!accessToken) {
        showConnectedAwaitingAssignment();
        return null;
      }
      return request("/api/exams/access", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify({ access_token: accessToken }) });
    })
    .then(function (payload) { if (payload && payload.assignment) renderAssignment(payload.assignment); })
    .catch(function (error) {
      if (error && error.status === 401) {
        if (authPanel) authPanel.hidden = false;
        showMessage(accessToken ? "Conecte o Discord para confirmar que este link pertence a você." : "Abra o link individual enviado pela Gerência.", "pending");
        return;
      }
      showMessage(error.message || "Não consegui consultar esta atribuição.", "error");
    });
})();
