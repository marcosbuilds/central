(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;

  function initMemberArea() {
    if (site.body.dataset.page !== "member") return;
    var gate = document.querySelector("[data-member-gate]");
    var workspace = document.querySelector("[data-member-workspace]");
    var content = workspace && workspace.querySelector("[data-member-workspace-content]");
    var skeleton = workspace && workspace.querySelector("[data-member-workspace-skeleton]");
    var overview = workspace && workspace.querySelector("[data-member-overview]");
    var shell = workspace && workspace.querySelector("[data-member-shell]");
    var sidebar = workspace && workspace.querySelector("[data-member-sidebar]");
    var workspaceMain = workspace && workspace.querySelector(".member-workspace-main");
    var sidebarToggle = workspace && workspace.querySelector("[data-member-sidebar-toggle]");
    var sidebarToggleIcon = workspace && workspace.querySelector("[data-member-sidebar-toggle-icon]");
    var sidebarClose = workspace && workspace.querySelector("[data-member-sidebar-close]");
    var sidebarScrim = workspace && workspace.querySelector("[data-member-sidebar-scrim]");
    var loadingStatus = workspace && workspace.querySelector("[data-member-loading-status]");
    var sidebarLinks = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-nav-link]")) : [];
    var memberViews = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-view]")) : [];
    var memberContextTitle = workspace && workspace.querySelector("[data-member-context-title]");
    var sidebarName = workspace && workspace.querySelector("[data-member-sidebar-name]");
    var sidebarUsername = workspace && workspace.querySelector("[data-member-sidebar-username]");
    var sidebarState = workspace && workspace.querySelector("[data-member-sidebar-state]");
    var sidebarAvatar = workspace && workspace.querySelector("[data-member-sidebar-avatar]");
    var sidebarAvatarFallback = workspace && workspace.querySelector("[data-member-sidebar-avatar-fallback]");
    var memberName = workspace && workspace.querySelector("[data-member-name]");
    var memberUsername = workspace && workspace.querySelector("[data-member-username]");
    var memberRoles = workspace && workspace.querySelector("[data-member-roles]");
    var memberAvatar = workspace && workspace.querySelector("[data-member-avatar]");
    var memberAvatarFallback = workspace && workspace.querySelector("[data-member-avatar-fallback]");
    var connection = workspace && workspace.querySelector("[data-member-connection]");
    var notificationTrigger = workspace && workspace.querySelector("[data-member-notifications]");
    var notificationPanel = workspace && workspace.querySelector("[data-member-notification-panel]");
    var notificationClose = workspace && workspace.querySelector("[data-member-notifications-close]");
    var notificationList = workspace && workspace.querySelector("[data-member-notification-list]");
    var notificationBadge = workspace && workspace.querySelector("[data-member-notification-badge]");
    var logout = workspace && workspace.querySelector("[data-member-logout]");
    var retry = gate && gate.querySelector("[data-member-retry]");
    var gateAction = gate && gate.querySelector("[data-member-discord-connect]");
    var loading = false;
    var notificationsLoading = false;
    var notificationsLoaded = false;
    var currentView = "overview";
    var shellReadyStorageKey = "peace.member.shell-ready.v1";
    var viewTitles = {
      overview: "Visão geral",
      library: "Área de estudo / Biblioteca",
      clips: "Clipes"
    };

    function request(url, options) {
      return site.attemptEndpoint(url, Object.assign({ headers: { Accept: "application/json" } }, options || {}), 5000).then(function (response) { return response.json(); });
    }
    function setConnection(message, tone) {
      if (!connection) return;
      connection.textContent = message || "";
      connection.dataset.state = tone || "ready";
      connection.hidden = !message;
    }
    function setLoadingStatus(message) {
      if (loadingStatus) loadingStatus.textContent = message || "";
    }
    function date(value) {
      if (!value) return "—";
      try { return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); } catch (error) { return value; }
    }
    function statusLabel(item) {
      if (item.status === "submitted") return item.passed ? "Aprovado" : "Não aprovado";
      if (item.status === "in_progress") return "Em andamento";
      if (item.status === "expired") return "Prazo encerrado";
      return "Aguardando início";
    }
    function initials(identity) {
      var value = (identity && (identity.global_name || identity.display_name || identity.username) || "Discord").replace(/^@/, "").trim();
      var parts = value.split(/\s+/).filter(Boolean);
      return (parts.length > 1 ? parts[0].charAt(0) + parts[parts.length - 1].charAt(0) : value.slice(0, 2)).toUpperCase() || "D";
    }
    function renderAvatarNode(imageNode, fallbackNode, identity) {
      if (!imageNode) return;
      var profile = identity || {};
      var fallback = function () {
        imageNode.hidden = true;
        if (fallbackNode) {
          fallbackNode.textContent = initials(profile);
          fallbackNode.hidden = false;
        }
      };
      imageNode.hidden = true;
      if (fallbackNode) fallbackNode.hidden = true;
      imageNode.alt = "Avatar de @" + (profile.username || "membro");
      imageNode.onerror = fallback;
      if (!profile.avatar_url) { fallback(); return; }
      imageNode.src = profile.avatar_url;
      imageNode.hidden = false;
    }

    function renderAvatar(identity) {
      renderAvatarNode(memberAvatar, memberAvatarFallback, identity);
      renderAvatarNode(sidebarAvatar, sidebarAvatarFallback, identity);
    }

    function renderSidebarProfile(identity) {
      var profile = identity || {};
      if (sidebarName) sidebarName.textContent = profile.global_name || profile.display_name || profile.username || "membro";
      if (sidebarUsername) sidebarUsername.textContent = profile.username ? "@" + profile.username : "@discord";
      if (sidebarState) sidebarState.textContent = "Membro Peace confirmado";
      renderAvatarNode(sidebarAvatar, sidebarAvatarFallback, profile);
    }

    function renderRoles(server) {
      if (!memberRoles) return;
      var labels = [];
      if (server && server.is_peace_member === true) labels.push("Membro Peace");
      if (server && server.is_manager === true) labels.push("Gerência");
      memberRoles.textContent = "";
      labels.forEach(function (label) {
        var chip = document.createElement("span");
        chip.className = "member-role-chip";
        chip.textContent = label;
        memberRoles.appendChild(chip);
      });
      memberRoles.hidden = labels.length === 0;
    }

    function renderNotifications(payload) {
      if (!notificationList) return;
      var items = payload && Array.isArray(payload.notices) ? payload.notices : [];
      var sourceState = payload && payload.source ? payload.source.state : "unavailable";
      notificationList.textContent = "";

      if (notificationBadge) {
        notificationBadge.textContent = items.length > 9 ? "9+" : String(items.length);
        notificationBadge.hidden = items.length === 0;
      }
      if (notificationTrigger) {
        notificationTrigger.setAttribute(
          "aria-label",
          items.length ? (items.length === 1 ? "1 aviso público. Abrir avisos" : items.length + " avisos públicos. Abrir avisos") : "Abrir avisos"
        );
      }

      if (!items.length) {
        var empty = document.createElement("p");
        empty.className = "member-notification-state";
        var unavailable = sourceState === "unavailable";
        empty.textContent = unavailable
          ? "A fonte pública está indisponível. Tente abrir novamente em instantes."
          : "Nenhum comunicado público foi publicado ainda.";
        notificationList.appendChild(empty);
        if (unavailable) {
          var retryButton = document.createElement("button");
          retryButton.className = "text-button";
          retryButton.type = "button";
          retryButton.textContent = "Tentar novamente";
          retryButton.addEventListener("click", function () {
            notificationsLoaded = false;
            loadNotifications();
          });
          notificationList.appendChild(retryButton);
        }
        return;
      }

      items.slice(0, 4).forEach(function (item) {
        var article = document.createElement("article");
        article.className = "member-notification-item";
        var meta = document.createElement("p");
        meta.className = "eyebrow";
        meta.textContent = date(item.published_at) + " · " + (item.author || "Peace");
        var copy = document.createElement("p");
        copy.textContent = item.text || "Comunicado sem texto.";
        article.appendChild(meta);
        article.appendChild(copy);
        if (/^https?:\/\//i.test(String(item.url || ""))) {
          var link = document.createElement("a");
          link.className = "text-link";
          link.href = String(item.url);
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = "Abrir origem ↗";
          article.appendChild(link);
        }
        notificationList.appendChild(article);
      });
    }

    function loadNotifications() {
      if (!notificationList || notificationsLoading || notificationsLoaded) return;
      notificationsLoading = true;
      notificationList.textContent = "";
      var loadingState = document.createElement("p");
      loadingState.className = "member-notification-state";
      loadingState.textContent = "Consultando avisos públicos…";
      notificationList.appendChild(loadingState);
      request("/api/notices")
        .then(function (payload) {
          notificationsLoaded = true;
          renderNotifications(payload);
        })
        .catch(function () {
          renderNotifications({ notices: [], source: { state: "unavailable" } });
        })
        .finally(function () { notificationsLoading = false; });
    }

    function setNotificationsOpen(open, moveFocus) {
      if (!notificationPanel || !notificationTrigger) return;
      var nextOpen = Boolean(open);
      if (nextOpen && shell && shell.dataset.sidebarOpen === "true" && window.matchMedia && window.matchMedia("(max-width: 900px)").matches) {
        setSidebarOpen(false, false);
      }
      notificationPanel.hidden = !nextOpen;
      notificationTrigger.setAttribute("aria-expanded", String(nextOpen));
      if (nextOpen) {
        loadNotifications();
        if (moveFocus && notificationClose) notificationClose.focus();
      } else if (moveFocus) {
        notificationTrigger.focus();
      }
    }

    function hasReusableShell() {
      try { return window.sessionStorage.getItem(shellReadyStorageKey) === "1"; } catch (error) { return false; }
    }
    function markShellReady() {
      try { window.sessionStorage.setItem(shellReadyStorageKey, "1"); } catch (error) { /* optional */ }
    }
    function clearShellReady() {
      try { window.sessionStorage.removeItem(shellReadyStorageKey); } catch (error) { /* optional */ }
    }

    function resetReusableSurface() {
      if (memberName) memberName.textContent = "membro";
      if (memberUsername) memberUsername.textContent = "@discord";
      if (memberRoles) {
        memberRoles.textContent = "";
        memberRoles.hidden = true;
      }
      if (memberAvatar) memberAvatar.hidden = true;
      if (memberAvatarFallback) memberAvatarFallback.hidden = true;
      if (sidebarName) sidebarName.textContent = "membro";
      if (sidebarUsername) sidebarUsername.textContent = "@discord";
      if (sidebarState) sidebarState.textContent = "Validando conta…";
      if (sidebarAvatar) sidebarAvatar.hidden = true;
      if (sidebarAvatarFallback) sidebarAvatarFallback.hidden = true;
      var managerLink = workspace && workspace.querySelector("[data-member-manager]");
      if (managerLink) managerLink.hidden = true;
      if (overview) overview.textContent = "";
    }

    function setSidebarOpen(open, moveFocus) {
      if (!shell || !sidebar) return;
      var compact = window.matchMedia && window.matchMedia("(max-width: 900px)").matches;
      var nextOpen = compact ? Boolean(open) : true;
      shell.dataset.sidebarOpen = String(nextOpen);
      sidebarToggle && sidebarToggle.setAttribute("aria-expanded", String(nextOpen));
      if (sidebarToggle) sidebarToggle.setAttribute("aria-label", "Abrir menu");
      if (sidebarToggleIcon) sidebarToggleIcon.textContent = "☰";
      if (compact && nextOpen && notificationPanel && !notificationPanel.hidden) setNotificationsOpen(false, false);
      document.documentElement.classList.toggle("member-menu-open", compact && nextOpen);
      document.body.classList.toggle("member-menu-open", compact && nextOpen);
      if (workspaceMain) {
        if (compact && nextOpen) workspaceMain.setAttribute("inert", "");
        else workspaceMain.removeAttribute("inert");
      }
      if (nextOpen) {
        sidebar.removeAttribute("inert");
        if (moveFocus && compact) {
          var first = sidebar.querySelector("[data-member-sidebar-close], .member-nav a");
          if (first) first.focus();
        }
      } else {
        sidebar.setAttribute("inert", "");
        if (moveFocus && sidebarToggle) sidebarToggle.focus();
      }
    }

    function requestedView() {
      var path = window.location.pathname.replace(/\/+$/, "/") || "/";
      if (path !== "/area/") return "overview";
      var view = new URL(window.location.href).searchParams.get("view");
      return Object.prototype.hasOwnProperty.call(viewTitles, view) ? view : "overview";
    }

    function syncSidebarLocation() {
      sidebarLinks.forEach(function (link) {
        var href = link.getAttribute("href") || "";
        var linkView = link.dataset.memberViewLink;
        var active = linkView ? linkView === currentView : (currentView === "overview" && href.replace(/\/+$/, "/") === "/area/");
        if (active) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
    }

    function setMemberView(view, replace, moveFocus) {
      var nextView = Object.prototype.hasOwnProperty.call(viewTitles, view) ? view : "overview";
      var url = new URL(window.location.href);
      if (url.pathname.replace(/\/+$/, "/") !== "/area/") url.pathname = "/area/";
      if (nextView === "overview") url.searchParams.delete("view");
      else url.searchParams.set("view", nextView);
      if (nextView !== "library" && nextView !== "clips") url.searchParams.delete("q");
      var nextUrl = url.pathname + (url.search ? "?" + url.searchParams.toString() : "") + url.hash;
      if (replace) window.history.replaceState({}, document.title, nextUrl);
      else if (nextUrl !== window.location.pathname + window.location.search + window.location.hash) window.history.pushState({}, document.title, nextUrl);

      currentView = nextView;
      if (notificationPanel && !notificationPanel.hidden) setNotificationsOpen(false, false);
      memberViews.forEach(function (node) { node.hidden = node.dataset.memberView !== nextView; });
      if (memberContextTitle) memberContextTitle.textContent = viewTitles[nextView];
      syncSidebarLocation();

      var activeView = memberViews.find(function (node) { return node.dataset.memberView === nextView; });
      if (nextView === "library" && activeView && typeof site.initStudies === "function") site.initStudies(activeView);
      if (nextView === "clips" && activeView && typeof site.initClips === "function") site.initClips(activeView);
      if (moveFocus && activeView) {
        var target = activeView.querySelector("[data-member-view-focus], input, a, button");
        if (!target) {
          target = activeView.querySelector("h1, h2");
          if (target) target.setAttribute("tabindex", "-1");
        }
        if (target) target.focus({ preventScroll: false });
      }
    }

    function identityIsReady(identity) {
      return Boolean(
        identity
        && /^[0-9]{15,25}$/.test(String(identity.discord_id || ""))
        && identity.avatar_url
      );
    }

    function processIsReady(payload) {
      var server = payload && payload.server ? payload.server : null;
      return Boolean(
        payload && payload.ok === true
        && identityIsReady(payload.identity)
        && payload.profile
        && Array.isArray(payload.assignments)
        && server
        && server.state
        && server.state !== "unavailable"
        && server.is_peace_member === true
        && typeof server.is_manager === "boolean"
      );
    }

    function renderOverview(session, process) {
      if (!overview) return;
      var data = process || {};
      var identity = data.identity || (session && session.identity) || {};
      var profile = data.profile || {};
      var assignments = Array.isArray(data.assignments) ? data.assignments : [];
      overview.textContent = "";

      var progress = document.createElement("section");
      progress.className = "member-progress-card member-data-block--wide";
      progress.id = "member-process";
      progress.setAttribute("aria-label", "Seu andamento");
      var summary = document.createElement("div");
      summary.className = "member-progress-grid";
      [["Pontuação", profile.score == null ? "—" : profile.score + "/" + (profile.score_scale || 100)], ["Provas", String(assignments.length)], ["Status", profile.passed ? "Aprovado" : assignments.length ? "Em andamento" : "Sem prova"]].forEach(function (entry) {
        var item = document.createElement("div");
        var label = document.createElement("small");
        label.textContent = entry[0];
        var value = document.createElement("strong");
        value.textContent = entry[1];
        item.appendChild(label);
        item.appendChild(value);
        summary.appendChild(item);
      });
      progress.appendChild(summary);
      overview.appendChild(progress);

      var assignmentsBlock = document.createElement("section");
      assignmentsBlock.className = "member-data-block member-data-block--wide";
      assignmentsBlock.id = "member-results";
      assignmentsBlock.innerHTML = "<div class=\"member-data-heading\"><h2 id=\"member-results-title\">Atribuições</h2></div>";
      if (!assignments.length) {
        var empty = document.createElement("p");
        empty.className = "member-block-state";
        empty.textContent = "A Gerência ainda não criou uma atribuição para esta conta.";
        assignmentsBlock.appendChild(empty);
      } else {
        var list = document.createElement("div");
        list.className = "member-assignment-list";
        assignments.forEach(function (assignment) {
          var row = document.createElement("article");
          row.className = "member-assignment-row";
          var title = document.createElement("strong");
          title.textContent = "Apostila Civil · atribuição #" + assignment.id;
          var detail = document.createElement("p");
          detail.textContent = statusLabel(assignment) + " · prazo " + date(assignment.deadline_at) + " · " + (assignment.score == null ? "nota pendente" : "nota " + assignment.score + "/100");
          row.appendChild(title);
          row.appendChild(detail);
          list.appendChild(row);
        });
        assignmentsBlock.appendChild(list);
      }
      overview.appendChild(assignmentsBlock);

      var managerLink = document.querySelector("[data-member-manager]");
      if (managerLink) managerLink.hidden = !(data.server && data.server.is_manager === true);
      if (memberName) memberName.textContent = identity.global_name || identity.display_name || identity.username || "membro";
      if (memberUsername) memberUsername.textContent = identity.username ? "@" + identity.username : "@discord";
      renderRoles(data.server);
      renderAvatar(identity);
      renderSidebarProfile(identity);
      syncSidebarLocation();
      setConnection("", "ready");
    }

    function configureGate(mode, message) {
      clearShellReady();
      setLoadingStatus("");
      if (workspace) workspace.hidden = true;
      if (gate) gate.hidden = false;
      var gateText = gate && gate.querySelector("[data-member-gate-message]");
      if (gateText && message) gateText.textContent = message;
      if (gateAction) {
        gateAction.hidden = mode !== "connect" && mode !== "set";
        if (mode === "set") {
          gateAction.href = "../entrar/";
          gateAction.innerHTML = "Solicitar setagem <span class=\"button-icon\" aria-hidden=\"true\">→</span>";
          gateAction.removeAttribute("data-member-discord-connect");
        } else if (mode === "connect") {
          gateAction.href = "../acessar/?return_to=%2Farea%2F";
          gateAction.innerHTML = "Conectar Discord <span class=\"button-icon\" aria-hidden=\"true\">→</span>";
          gateAction.setAttribute("data-member-discord-connect", "");
        }
      }
      if (retry) retry.hidden = mode !== "retry";
    }
    function showDisconnected(message) {
      configureGate("connect", message || "Conecte uma conta Discord com cargo Peace para abrir o painel. Se você ainda não tem o cargo, siga para Meu processo.");
    }
    function showConnectedNonMember() {
      configureGate("set", "Discord conectado, mas esta conta ainda não tem cargo Peace. Continue pelo processo público para solicitar a setagem.");
    }
    function showUnavailable() {
      configureGate("retry", "Não foi possível confirmar a conexão com Discord agora. O painel continua bloqueado até a verificação terminar; tente novamente em instantes.");
    }
    function showWorkspaceLoading() {
      if (gate) gate.hidden = true;
      if (workspace) { workspace.hidden = false; workspace.setAttribute("aria-busy", "true"); }
      setLoadingStatus("Validando sessão, cargo Peace e processo…");
      if (hasReusableShell()) {
        resetReusableSurface();
        if (skeleton) skeleton.hidden = true;
        if (content) content.hidden = false;
        setSidebarOpen(false, false);
        setMemberView(requestedView(), true, false);
      } else {
        if (skeleton) skeleton.hidden = false;
        if (content) content.hidden = true;
      }
      setConnection("Validando sessão, cargo Peace e processo…", "pending");
    }
    function showWorkspace() {
      if (gate) gate.hidden = true;
      if (workspace) { workspace.hidden = false; workspace.setAttribute("aria-busy", "false"); }
      if (skeleton) skeleton.hidden = true;
      if (content) content.hidden = false;
      setLoadingStatus("");
      markShellReady();
      setSidebarOpen(false, false);
      setMemberView(requestedView(), true, false);
    }

    function load() {
      if (loading) return;
      loading = true;
      showWorkspaceLoading();
      request("/api/peace/process")
        .then(function (process) {
          var processServer = process && process.server ? process.server : {};
          if (!processIsReady(process)) {
            if (processServer.state === "member" || processServer.state === "not_member" || processServer.is_peace_member === false) {
              showConnectedNonMember();
            } else {
              showUnavailable();
            }
            return;
          }
          renderOverview(null, process);
          showWorkspace();
        })
        .catch(function (error) {
          if (error && error.status === 401) showDisconnected("Sua sessão Discord expirou. Conecte novamente para continuar.");
          else if (error && error.status === 403) showConnectedNonMember();
          else showUnavailable();
        })
        .finally(function () { loading = false; });
    }

    if (retry) retry.addEventListener("click", load);
    if (sidebarToggle) sidebarToggle.addEventListener("click", function () {
      var open = shell && shell.dataset.sidebarOpen === "true";
      setSidebarOpen(!open, true);
    });
    if (sidebarClose) sidebarClose.addEventListener("click", function () { setSidebarOpen(false, true); });
    if (sidebarScrim) sidebarScrim.addEventListener("click", function () { setSidebarOpen(false, true); });
    if (notificationTrigger) notificationTrigger.addEventListener("click", function () {
      var open = notificationTrigger.getAttribute("aria-expanded") === "true";
      setNotificationsOpen(!open, true);
    });
    if (notificationClose) notificationClose.addEventListener("click", function () { setNotificationsOpen(false, true); });
    if (workspace) workspace.addEventListener("click", function (event) {
      var target = event.target && event.target.closest ? event.target.closest("[data-member-view-link]") : null;
      if (!target || !workspace.contains(target)) return;
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      setSidebarOpen(false, false);
      setMemberView(target.dataset.memberViewLink, false, true);
    }, true);
    window.addEventListener("popstate", function () { setMemberView(requestedView(), true, true); });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Tab" && shell && shell.dataset.sidebarOpen === "true" && window.matchMedia("(max-width: 900px)").matches && sidebar && sidebar.contains(document.activeElement)) {
        var focusable = Array.prototype.filter.call(sidebar.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex=\"-1\"])") , function (node) {
          return !node.hidden && node.getClientRects().length > 0;
        });
        if (focusable.length) {
          var firstFocusable = focusable[0];
          var lastFocusable = focusable[focusable.length - 1];
          if (event.shiftKey && document.activeElement === firstFocusable) {
            event.preventDefault();
            lastFocusable.focus();
          } else if (!event.shiftKey && document.activeElement === lastFocusable) {
            event.preventDefault();
            firstFocusable.focus();
          }
        }
        return;
      }
      if (event.key !== "Escape") return;
      if (notificationPanel && !notificationPanel.hidden) {
        event.preventDefault();
        setNotificationsOpen(false, true);
        return;
      }
      if (shell && shell.dataset.sidebarOpen === "true" && window.matchMedia("(max-width: 900px)").matches) {
        event.preventDefault();
        setSidebarOpen(false, true);
      }
    });
    document.addEventListener("click", function (event) {
      if (!notificationPanel || notificationPanel.hidden) return;
      if (notificationPanel.contains(event.target) || notificationTrigger.contains(event.target)) return;
      setNotificationsOpen(false, false);
    });
    if (window.matchMedia) {
      var sidebarMedia = window.matchMedia("(max-width: 900px)");
      var syncSidebarMode = function () {
        if (sidebarMedia.matches) {
          var focusInsideSidebar = sidebar && sidebar.contains(document.activeElement);
          setSidebarOpen(false, focusInsideSidebar);
        } else {
          setSidebarOpen(true, false);
        }
      };
      if (sidebarMedia.addEventListener) sidebarMedia.addEventListener("change", syncSidebarMode);
      else if (sidebarMedia.addListener) sidebarMedia.addListener(syncSidebarMode);
    }
    if (logout) logout.addEventListener("click", function () {
      if (!window.confirm("Sair da conta Discord e fechar o Painel Peace?")) return;
      clearShellReady();
      logout.disabled = true;
      request("/api/auth/discord/logout", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" })
        .then(function () { window.location.replace("/acessar/?status=logged-out"); })
        .catch(function () { logout.disabled = false; });
    });
    load();
  }

  site.initMemberArea = initMemberArea;
})(window);
