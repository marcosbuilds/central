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
    var sidebarToggle = workspace && workspace.querySelector("[data-member-sidebar-toggle]");
    var sidebarToggleLabel = workspace && workspace.querySelector("[data-member-sidebar-toggle-label]");
    var sidebarClose = workspace && workspace.querySelector("[data-member-sidebar-close]");
    var sidebarLinks = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-nav-link]")) : [];
    var sidebarName = workspace && workspace.querySelector("[data-member-sidebar-name]");
    var sidebarUsername = workspace && workspace.querySelector("[data-member-sidebar-username]");
    var sidebarState = workspace && workspace.querySelector("[data-member-sidebar-state]");
    var sidebarAvatar = workspace && workspace.querySelector("[data-member-sidebar-avatar]");
    var sidebarAvatarFallback = workspace && workspace.querySelector("[data-member-sidebar-avatar-fallback]");
    var memberName = workspace && workspace.querySelector("[data-member-name]");
    var memberRoles = workspace && workspace.querySelector("[data-member-roles]");
    var memberAvatar = workspace && workspace.querySelector("[data-member-avatar]");
    var memberAvatarFallback = workspace && workspace.querySelector("[data-member-avatar-fallback]");
    var connection = workspace && workspace.querySelector("[data-member-connection]");
    var nextAction = workspace && workspace.querySelector("[data-member-next-action]");
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

    function request(url, options) {
      return site.attemptEndpoint(url, Object.assign({ headers: { Accept: "application/json" } }, options || {}), 5000).then(function (response) { return response.json(); });
    }
    function setConnection(message, tone) {
      if (!connection) return;
      connection.textContent = message || "";
      connection.dataset.state = tone || "ready";
      connection.hidden = !message;
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
      notificationPanel.hidden = !nextOpen;
      notificationTrigger.setAttribute("aria-expanded", String(nextOpen));
      if (nextOpen) {
        loadNotifications();
        if (moveFocus && notificationClose) notificationClose.focus();
      } else if (moveFocus) {
        notificationTrigger.focus();
      }
    }

    function setSidebarOpen(open, moveFocus) {
      if (!shell || !sidebar) return;
      var compact = window.matchMedia && window.matchMedia("(max-width: 900px)").matches;
      var nextOpen = compact ? Boolean(open) : true;
      shell.dataset.sidebarOpen = String(nextOpen);
      sidebarToggle && sidebarToggle.setAttribute("aria-expanded", String(nextOpen));
      if (sidebarToggleLabel) sidebarToggleLabel.textContent = nextOpen ? "Fechar menu" : "Abrir menu";
      if (nextOpen) {
        sidebar.removeAttribute("inert");
        if (moveFocus && compact) {
          var first = sidebar.querySelector(".member-sidebar-close, .member-nav a");
          if (first) first.focus();
        }
      } else {
        sidebar.setAttribute("inert", "");
        if (moveFocus && sidebarToggle) sidebarToggle.focus();
      }
    }

    function syncSidebarLocation() {
      var path = window.location.pathname.replace(/\/+$/, "/") || "/";
      sidebarLinks.forEach(function (link) {
        var href = link.getAttribute("href") || "";
        if (!href.startsWith("/")) return;
        if (href.replace(/\/+$/, "/") === path) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
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
      progress.innerHTML = "<div class=\"member-data-heading\"><p class=\"eyebrow\">Processo</p><h2 id=\"member-process-title\">Seu andamento</h2></div>";
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
      var copy = document.createElement("p");
      copy.className = "member-progress-copy";
      copy.textContent = assignments.length ? "Abaixo estão as atribuições vinculadas ao seu Discord ID." : "Nenhuma prova foi atribuída ainda. Continue estudando pelos materiais públicos.";
      progress.appendChild(copy);
      overview.appendChild(progress);

      var assignmentsBlock = document.createElement("section");
      assignmentsBlock.className = "member-data-block member-data-block--wide";
      assignmentsBlock.id = "member-results";
      assignmentsBlock.innerHTML = "<div class=\"member-data-heading\"><p class=\"eyebrow\">Provas</p><h2 id=\"member-results-title\">Suas atribuições</h2></div>";
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

      var materials = document.createElement("section");
      materials.className = "member-data-block member-data-block--wide member-materials-card";
      materials.id = "member-materials";
      materials.innerHTML = "<div class=\"member-data-heading\"><p class=\"eyebrow\">Biblioteca</p><h2 id=\"member-materials-title\">Materiais de estudo</h2></div><p>Leitura pública, sem depender do painel.</p>";
      var materialCovers = document.createElement("div");
      materialCovers.className = "member-material-covers";
      [
        { href: "/estudos/", src: "/assets/studies/civil/civil-cover-01.png", alt: "Capa da Apostila Civil", kicker: "01 / Civil", title: "Apostila Civil", description: "Investigação, patrulhamento e preparação.", meta: "18 páginas · biblioteca pública" },
        { href: "/estudos/", src: "/assets/studies/peace/a-peace-cover-1.png", alt: "Capa do manual A Peace", kicker: "02 / Convivência", title: "Manual da Peace", description: "Paz, respeito e responsabilidade.", meta: "8 páginas · biblioteca pública" }
      ].forEach(function (item) {
        var link = document.createElement("a");
        link.className = "member-material-card";
        link.href = item.href;
        link.setAttribute("aria-label", "Abrir " + item.title);
        var cover = document.createElement("div");
        cover.className = "material-cover material-cover--member";
        cover.setAttribute("data-material-cover", "");
        cover.setAttribute("aria-busy", "true");
        var image = document.createElement("img");
        image.className = "material-cover-image";
        image.src = item.src;
        image.alt = item.alt;
        image.width = 1240;
        image.height = 1754;
        image.loading = "lazy";
        var overlay = document.createElement("div");
        overlay.className = "material-cover-overlay";
        overlay.innerHTML = "<span class=\"material-cover-kicker\"></span><h4></h4><p></p><span class=\"material-cover-meta\"></span>";
        overlay.querySelector(".material-cover-kicker").textContent = item.kicker;
        overlay.querySelector("h4").textContent = item.title;
        overlay.querySelector("p").textContent = item.description;
        overlay.querySelector(".material-cover-meta").textContent = item.meta;
        cover.appendChild(image);
        cover.appendChild(overlay);
        link.appendChild(cover);
        materialCovers.appendChild(link);
      });
      materials.appendChild(materialCovers);
      overview.appendChild(materials);
      if (typeof site.initMaterialCovers === "function") site.initMaterialCovers(materials);

      if (nextAction) {
        nextAction.textContent = "";
        var nextTitle = document.createElement("strong");
        nextTitle.textContent = profile.passed ? "Você pode pedir a setagem." : "Próximo passo";
        var nextText = document.createElement("p");
        nextText.textContent = profile.passed ? "Use o Discord conectado para falar com a equipe e solicitar a entrada como aluno." : assignments.length ? "Conclua a prova atribuída e acompanhe o resultado aqui." : "Aguarde uma atribuição da Gerência ou continue estudando.";
        nextAction.appendChild(nextTitle);
        nextAction.appendChild(nextText);
      }
      var managerLink = document.querySelector("[data-member-manager]");
      if (managerLink) managerLink.hidden = !(data.server && data.server.is_manager === true);
      if (memberName) memberName.textContent = identity.global_name || identity.display_name || identity.username || "membro";
      renderRoles(data.server);
      renderAvatar(identity);
      renderSidebarProfile(identity);
      syncSidebarLocation();
      setConnection("", "ready");
    }

    function configureGate(mode, message) {
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
      if (skeleton) skeleton.hidden = false;
      if (content) content.hidden = true;
      setConnection("Validando sessão, cargo Peace e processo…", "pending");
    }
    function showWorkspace() {
      if (gate) gate.hidden = true;
      if (workspace) { workspace.hidden = false; workspace.setAttribute("aria-busy", "false"); }
      if (skeleton) skeleton.hidden = true;
      if (content) content.hidden = false;
      setSidebarOpen(false, false);
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
    if (notificationTrigger) notificationTrigger.addEventListener("click", function () {
      var open = notificationTrigger.getAttribute("aria-expanded") === "true";
      setNotificationsOpen(!open, true);
    });
    if (notificationClose) notificationClose.addEventListener("click", function () { setNotificationsOpen(false, true); });
    sidebarLinks.forEach(function (link) {
      link.addEventListener("click", function () {
        setSidebarOpen(false, false);
      });
    });
    document.addEventListener("keydown", function (event) {
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
      var syncSidebarMode = function () { setSidebarOpen(sidebarMedia.matches ? shell.dataset.sidebarOpen === "true" : true, false); };
      if (sidebarMedia.addEventListener) sidebarMedia.addEventListener("change", syncSidebarMode);
      else if (sidebarMedia.addListener) sidebarMedia.addListener(syncSidebarMode);
    }
    if (logout) logout.addEventListener("click", function () {
      if (!window.confirm("Sair da conta Discord e fechar o Painel Peace?")) return;
      logout.disabled = true;
      request("/api/auth/discord/logout", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" })
        .then(function () { window.location.replace("/acessar/?status=logged-out"); })
        .catch(function () { logout.disabled = false; });
    });
    load();
  }

  site.initMemberArea = initMemberArea;
})(window);
