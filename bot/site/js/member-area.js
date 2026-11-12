(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;
  var body = site.body;
  var readMemberSessionToken = site.readMemberSessionToken;
  var clearMemberSessionToken = site.clearMemberSessionToken;
  var attemptEndpoint = site.attemptEndpoint;
  var friendlyError = site.friendlyError;

  function initMemberArea() {
    if (body.dataset.page !== "member") return;

    var gate = document.querySelector("[data-member-gate]");
    var workspace = document.querySelector("[data-member-workspace]");
    var workspaceSkeleton = workspace && workspace.querySelector("[data-member-workspace-skeleton]");
    var workspaceContent = workspace && workspace.querySelector("[data-member-workspace-content]");
    var memberName = workspace && workspace.querySelector("[data-member-name]");
    var memberAvatar = workspace && workspace.querySelector("[data-member-avatar]");
    var logoutButton = workspace && workspace.querySelector("[data-member-logout]");
    var connection = workspace && workspace.querySelector("[data-member-connection]");
    var overview = workspace && workspace.querySelector("[data-member-overview]");
    var nextAction = workspace && workspace.querySelector("[data-member-next-action]");
    var refreshButton = workspace && workspace.querySelector("[data-member-refresh]");
    var loading = false;
    var memberPollTimer = null;
    var hasAuthenticatedWorkspace = false;
    var logoutPending = false;

    function renderMemberBlock(container, block, title) {
      if (!container || !block) return;
      container.textContent = "";
      var heading = document.createElement("h3");
      heading.textContent = title;
      container.appendChild(heading);
      if (block.items && block.items.length) {
        var list = document.createElement("ul");
        list.className = "member-block-list";
        block.items.forEach(function (item) {
          var row = document.createElement("li");
          var copy = document.createElement("div");
          copy.className = "member-block-copy";
          var label = document.createElement("strong");
          label.textContent = item.author || item.title || "Atualização";
          copy.appendChild(label);
          if (item.text) {
            var text = document.createElement("p");
            text.textContent = item.text;
            copy.appendChild(text);
          }
          if (item.published_at || item.started_at) {
            var date = document.createElement("small");
            date.textContent = new Date(item.published_at || item.started_at).toLocaleString("pt-BR");
            copy.appendChild(date);
          }
          if (item.url) {
            var link = document.createElement("a");
            link.href = item.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "Abrir no Discord ↗";
            copy.appendChild(link);
          }
          row.appendChild(copy);
          list.appendChild(row);
        });
        container.appendChild(list);
      } else {
        var empty = document.createElement("p");
        empty.className = "member-block-state";
        empty.textContent = block.message || "Sem dados disponíveis agora.";
        container.appendChild(empty);
      }
      var freshness = document.createElement("small");
      freshness.className = "member-block-freshness";
      freshness.textContent = block.stale ? "Desatualizado · tentando atualizar" : "Fonte: " + (block.source || "Peace");
      container.appendChild(freshness);
    }

    function renderOverview(payload) {
      var data = payload && payload.overview;
      if (!data || !overview) return;
      if (nextAction && data.next_action) {
        nextAction.textContent = "";
        var nextTitle = document.createElement("strong");
        nextTitle.textContent = data.next_action.title || "Próximo passo";
        var nextText = document.createElement("p");
        nextText.textContent = data.next_action.message || "Consulte o Discord para continuar.";
        nextAction.appendChild(nextTitle);
        nextAction.appendChild(nextText);
      }
      overview.querySelectorAll("[data-member-block]").forEach(function (node) {
        var key = node.getAttribute("data-member-block");
        var capability = node.getAttribute("data-member-capability");
        if (capability && (!data.capabilities || data.capabilities[capability] !== true)) {
          node.hidden = true;
          return;
        }
        node.hidden = false;
        renderMemberBlock(node, data[key], node.dataset.memberTitle || key);
      });
      document.querySelectorAll("[data-member-capability]").forEach(function (node) {
        var capability = node.getAttribute("data-member-capability");
        node.hidden = !data.capabilities || data.capabilities[capability] !== true;
      });
      if (connection) connection.textContent = "Atualizado agora · sessão validada pelo Discord";
    }

    function parseOverviewResponse(response) {
      return response.text().then(function (raw) {
        var payload = null;
        try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
        if (!payload || payload.ok !== true) throw friendlyError(payload, response.status, "Não foi possível atualizar a área.");
        return payload;
      });
    }

    function loadMemberSession(options) {
      options = options || {};
      var silent = options.silent === true;
      var token = readMemberSessionToken();
      if (!workspace || loading) return;

      loading = true;
      // Keep the authenticated workspace out of the document while the
      // cookie is being checked. A loading shell is useful after a valid
      // session is already established, but it must not look like a public
      // preview when the browser has no verified member session.
      if (hasAuthenticatedWorkspace) workspace.hidden = false;
      else workspace.hidden = true;
      if (!silent && hasAuthenticatedWorkspace) {
        if (workspaceSkeleton) workspaceSkeleton.hidden = false;
        if (workspaceContent) workspaceContent.hidden = true;
      }
      if (silent && connection) connection.textContent = "Atualizando…";
      var sessionHeaders = { Accept: "application/json", "Content-Type": "application/json" };
      if (token) sessionHeaders.Authorization = "Bearer " + token;
      attemptEndpoint("/api/member/auth/session", {
        method: "POST",
        headers: sessionHeaders,
        body: "{}"
      }, 60000)
        .then(function (response) {
          return response.text().then(function (raw) {
            var payload = null;
            try { payload = raw ? JSON.parse(raw) : null; } catch (error) { payload = null; }
            if (!payload || payload.ok !== true) throw friendlyError(payload, response.status, "Não foi possível validar sua sessão.");
            return payload;
          });
        })
        .then(function (payload) {
          hasAuthenticatedWorkspace = true;
          if (gate) gate.hidden = true;
          if (workspaceSkeleton) workspaceSkeleton.hidden = true;
          if (workspaceContent) workspaceContent.hidden = false;
          if (memberName) memberName.textContent = payload.session.member_name || "membro";
          if (memberAvatar && payload.session.avatar_url) {
            memberAvatar.src = payload.session.avatar_url;
            memberAvatar.hidden = false;
          }
          var overviewHeaders = { Accept: "application/json" };
          if (token) overviewHeaders.Authorization = "Bearer " + token;
          return attemptEndpoint("/api/member/overview", {
            method: "GET",
            headers: overviewHeaders,
          }, 30000).then(parseOverviewResponse).then(renderOverview);
        })
        .catch(function (error) {
          if ((token || hasAuthenticatedWorkspace) && error && (error.status === 401 || error.status === 403)) {
            clearMemberSessionToken();
            window.location.replace("/acessar/?status=session-expired");
            return;
          }
          if (!token && error && (error.status === 401 || error.status === 403)) {
            if (workspace) workspace.hidden = true;
            if (gate) gate.hidden = false;
            return;
          }
          if (!hasAuthenticatedWorkspace) {
            if (workspace) workspace.hidden = true;
            if (gate) gate.hidden = false;
            return;
          }
          if (connection) connection.textContent = "Não foi possível atualizar · tente novamente";
          if (!silent) {
            if (workspaceSkeleton) workspaceSkeleton.hidden = true;
            if (workspaceContent) workspaceContent.hidden = false;
          }
        })
        .finally(function () {
          loading = false;
        });
    }

    if (logoutButton) logoutButton.addEventListener("click", function () {
      if (logoutPending) return;
      logoutPending = true;
      logoutButton.disabled = true;
      logoutButton.setAttribute("aria-busy", "true");
      var token = readMemberSessionToken();
      var headers = { Accept: "application/json", "Content-Type": "application/json" };
      if (token) headers.Authorization = "Bearer " + token;
      attemptEndpoint("/api/member/auth/revoke", {
        method: "POST",
        headers: headers,
        body: "{}",
      }, 10000)
        .then(function () {
          clearMemberSessionToken();
          window.location.replace("/acessar/?status=logged-out");
        })
        .catch(function (error) {
          logoutPending = false;
          logoutButton.disabled = false;
          logoutButton.removeAttribute("aria-busy");
          if (connection) connection.textContent = (error && error.message) || "Não foi possível encerrar a sessão. Tente novamente.";
        });
    });
    if (refreshButton) refreshButton.addEventListener("click", function () { loadMemberSession({ silent: false }); });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible" && (readMemberSessionToken() || hasAuthenticatedWorkspace)) loadMemberSession({ silent: true });
    });
    loadMemberSession({ silent: false });
    memberPollTimer = window.setInterval(function () {
      if (document.visibilityState === "visible" && hasAuthenticatedWorkspace) loadMemberSession({ silent: true });
    }, 45000);
  }

  site.initMemberArea = initMemberArea;
})(window);
