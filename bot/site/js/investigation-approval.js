(function () {
  "use strict";

  var app = document.querySelector("[data-approval-app]");
  if (!app) return;
  var loading = app.querySelector("[data-approval-loading]");
  var gate = app.querySelector("[data-approval-gate]");
  var content = app.querySelector("[data-approval-content]");
  var errorView = app.querySelector("[data-approval-error]");
  var errorTitle = app.querySelector("[data-approval-error-title]");
  var errorMessage = app.querySelector("[data-approval-error-message]");
  var connect = app.querySelector("[data-approval-connect]");
  var title = app.querySelector("[data-approval-case-title]");
  var summary = app.querySelector("[data-approval-case-summary]");
  var expectation = app.querySelector("[data-approval-expectation]");
  var evidence = app.querySelector("[data-approval-evidence]");
  var evaluator = app.querySelector("[data-approval-evaluator]");
  var form = app.querySelector("[data-approval-form]");
  var acknowledge = form && form.elements.acknowledge;
  var note = form && form.elements.note;
  var submit = app.querySelector("[data-approval-submit]");
  var status = app.querySelector("[data-approval-status]");
  var decision = "";
  var token = new URL(window.location.href).searchParams.get("token") || "";

  function setStatus(message, state) {
    if (!status) return;
    status.textContent = message || "";
    status.dataset.state = state || "";
  }

  function showError(code, message) {
    if (loading) loading.hidden = true;
    if (gate) gate.hidden = true;
    if (content) content.hidden = true;
    if (errorView) errorView.hidden = false;
    if (errorTitle) errorTitle.textContent = code === "APPROVAL_EVALUATOR_MISMATCH" ? "Este link não pertence a esta conta." : "Link indisponível";
    if (errorMessage) errorMessage.textContent = message || "Não foi possível carregar esta aprovação.";
    if (app) app.setAttribute("aria-busy", "false");
  }

  function showGate(message) {
    if (loading) loading.hidden = true;
    if (gate) gate.hidden = false;
    if (content) content.hidden = true;
    if (errorView) errorView.hidden = true;
    if (connect) {
      var returnTo = window.location.pathname + window.location.search;
      connect.href = "/acessar/?return_to=" + encodeURIComponent(returnTo);
    }
    if (status) status.textContent = message || "Conecte sua conta Discord para continuar.";
    if (app) app.setAttribute("aria-busy", "false");
  }

  function renderEvidence(items) {
    if (!evidence) return;
    evidence.textContent = "";
    if (!Array.isArray(items) || !items.length) {
      var empty = document.createElement("li");
      empty.textContent = "Nenhuma evidência adicional foi anexada.";
      evidence.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      var row = document.createElement("li");
      var heading = document.createElement("strong");
      heading.textContent = item.title || "Referência investigativa";
      var copy = document.createElement("small");
      copy.textContent = (item.note || "Sem observação") + " · " + (item.classification === "confirmed" ? "comprovado" : "referência");
      row.appendChild(heading);
      row.appendChild(copy);
      if (/^https:\/\//i.test(String(item.source_url || ""))) {
        var link = document.createElement("a");
        link.className = "text-link";
        link.href = item.source_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Abrir origem ↗";
        row.appendChild(link);
      }
      evidence.appendChild(row);
    });
  }

  function renderPayload(payload) {
    var caseRecord = payload && payload.case ? payload.case : {};
    var approval = payload && payload.approval ? payload.approval : {};
    if (loading) loading.hidden = true;
    if (gate) gate.hidden = true;
    if (errorView) errorView.hidden = true;
    if (content) content.hidden = false;
    if (title) title.textContent = caseRecord.title || "Caso investigativo";
    if (summary) summary.textContent = caseRecord.summary || "Sem resumo informado.";
    if (expectation) expectation.textContent = approval.expected_outcome || "A expectativa não foi informada.";
    if (evaluator) evaluator.textContent = "Avaliador " + String(approval.evaluator_discord_user_id || "autorizado");
    renderEvidence(caseRecord.evidence);
    if (approval.status === "approved" || approval.status === "rejected") {
      setStatus(approval.status === "approved" ? "Sua decisão foi registrada como aprovada." : "Sua decisão foi registrada como reprovada.", approval.status === "approved" ? "success" : "error");
      if (form) form.hidden = true;
    } else if (form) {
      form.hidden = false;
      if (acknowledge) acknowledge.checked = false;
      if (note) note.value = "";
      updateSubmit();
    }
    if (app) app.setAttribute("aria-busy", "false");
  }

  function updateSubmit() {
    if (submit) submit.disabled = !(decision && acknowledge && acknowledge.checked && note && note.value.trim().length >= 2);
  }

  function setDecision(value) {
    decision = value;
    app.querySelectorAll("[data-approval-decision]").forEach(function (button) {
      button.classList.toggle("is-selected", button.dataset.approvalDecision === value);
      button.setAttribute("aria-pressed", String(button.dataset.approvalDecision === value));
    });
    updateSubmit();
  }

  function request(url, options) {
    return fetch(url, Object.assign({ credentials: "include", headers: { Accept: "application/json" } }, options || {})).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        payload.status = response.status;
        return payload;
      });
    });
  }

  if (!token || !/^[A-Za-z0-9_-]{32,128}$/.test(token)) {
    showError("INVALID_APPROVAL_LINK", "O token deste link está ausente ou malformado.");
    return;
  }

  app.querySelectorAll("[data-approval-decision]").forEach(function (button) {
    button.addEventListener("click", function () { setDecision(button.dataset.approvalDecision || ""); });
  });
  if (acknowledge) acknowledge.addEventListener("change", updateSubmit);
  if (note) note.addEventListener("input", updateSubmit);
  if (form) form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!decision || !acknowledge || !acknowledge.checked || !note || note.value.trim().length < 2) {
      setStatus("Confirme a ciência da expectativa, escolha uma decisão e escreva uma observação.", "error");
      updateSubmit();
      return;
    }
    if (submit) submit.disabled = true;
    setStatus("Registrando sua decisão…", "pending");
    request("/api/investigation-approvals/" + encodeURIComponent(token), {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ acknowledge: true, decision: decision, note: note.value.trim() })
    }).then(function (payload) {
      if (!payload || payload.ok !== true) {
        var error = new Error(payload && payload.message || "Não foi possível registrar a decisão.");
        error.code = payload && payload.code;
        throw error;
      }
      renderPayload(payload);
      setStatus(payload.case && ["approved", "rejected"].indexOf(payload.case.status) >= 0 ? "O caso recebeu a decisão final deste fluxo." : "Decisão registrada. O caso continua aguardando os demais avaliadores.", "success");
    }).catch(function (error) {
      if (submit) submit.disabled = false;
      setStatus(error.message || "Não foi possível registrar a decisão.", "error");
    });
  });

  request("/api/investigation-approvals/" + encodeURIComponent(token)).then(function (payload) {
    if (payload && payload.ok === true) {
      renderPayload(payload);
      return;
    }
    if (payload && payload.status === 401) {
      showGate(payload.message);
      return;
    }
    showError(payload && payload.code, payload && payload.message);
  }).catch(function () { showError("APPROVAL_UNAVAILABLE", "O serviço de aprovação está indisponível. Tente novamente mais tarde."); });
})();
