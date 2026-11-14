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
    var memberName = workspace && workspace.querySelector("[data-member-name]");
    var memberAvatar = workspace && workspace.querySelector("[data-member-avatar]");
    var memberAvatarFallback = workspace && workspace.querySelector("[data-member-avatar-fallback]");
    var connection = workspace && workspace.querySelector("[data-member-connection]");
    var nextAction = workspace && workspace.querySelector("[data-member-next-action]");
    var logout = workspace && workspace.querySelector("[data-member-logout]");
    var refresh = workspace && workspace.querySelector("[data-member-refresh]");
    var retry = gate && gate.querySelector("[data-member-retry]");
    var gateAction = gate && gate.querySelector("[data-member-discord-connect]");
    var loading = false;

    function request(url, options) {
      return site.attemptEndpoint(url, Object.assign({ headers: { Accept: "application/json" } }, options || {}), 15000).then(function (response) { return response.json(); });
    }
    function getDiscordSession() {
      if (site.discordSessionError && typeof site.refreshDiscordSession === "function") return site.refreshDiscordSession();
      if (typeof site.getDiscordSession === "function") return site.getDiscordSession();
      return request("/api/auth/discord/session");
    }
    function setConnection(message, tone) {
      if (connection) { connection.textContent = message; connection.dataset.state = tone || "ready"; }
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
    function renderAvatar(identity) {
      if (!memberAvatar) return;
      var profile = identity || {};
      var fallback = function () {
        memberAvatar.hidden = true;
        if (memberAvatarFallback) {
          memberAvatarFallback.textContent = initials(profile);
          memberAvatarFallback.hidden = false;
        }
      };
      memberAvatar.hidden = true;
      if (memberAvatarFallback) memberAvatarFallback.hidden = true;
      memberAvatar.alt = "Avatar de @" + (profile.username || "membro");
      memberAvatar.onerror = fallback;
      if (!profile.avatar_url) { fallback(); return; }
      memberAvatar.src = profile.avatar_url;
      memberAvatar.hidden = false;
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
      var identity = data.identity || session.identity || {};
      var profile = data.profile || {};
      var updatedAt = data.updated_at || null;
      var assignments = Array.isArray(data.assignments) ? data.assignments : [];
      overview.textContent = "";

      var progress = document.createElement("section");
      progress.className = "member-progress-card member-data-block--wide";
      progress.id = "member-progress";
      progress.innerHTML = "<p class=\"eyebrow\">Meu progresso</p><h3>Seu processo, em um só lugar.</h3>";
      var summary = document.createElement("div");
      summary.className = "member-progress-grid";
      [["Pontuação", profile.score == null ? "—" : profile.score + "/" + (profile.score_scale || 100)], ["Provas", String(assignments.length)], ["Identidade", "Discord confirmado"]].forEach(function (entry) {
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
      assignmentsBlock.innerHTML = "<p class=\"eyebrow\">Provas e resultados</p><h3>Histórico do processo.</h3>";
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
      materials.innerHTML = "<p class=\"eyebrow\">Materiais públicos</p><h3>Continue sua preparação.</h3><p>As duas apostilas estão abertas para leitura, sem depender do painel.</p>";
      var materialCovers = document.createElement("div");
      materialCovers.className = "member-material-covers";
      [
        { href: "/estudos/civil/", src: "/assets/studies/civil/civil-cover-01.png", alt: "Capa da Apostila Civil", kicker: "01 / Civil", title: "Apostila Civil", description: "Investigação, patrulhamento e preparação.", meta: "18 páginas · leitura pública" },
        { href: "/estudos/peace/", src: "/assets/studies/peace/a-peace-cover-1.png", alt: "Capa do manual A Peace", kicker: "02 / Convivência", title: "Manual da Peace", description: "Paz, respeito e responsabilidade.", meta: "8 páginas · leitura pública" }
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
      renderAvatar(identity);
      if (updatedAt) setConnection("Atualizado em " + date(updatedAt), "ready");
      else setConnection("Sessão e processo confirmados pelo Discord", "ready");
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
          gateAction.href = "../acessar/";
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
    }

    function load() {
      if (loading) return;
      loading = true;
      showWorkspaceLoading();
      getDiscordSession()
        .then(function (session) {
          var sessionError = site.discordSessionError;
          if (!session) {
            if (sessionError && sessionError.status !== 401) showUnavailable();
            else showDisconnected();
            return null;
          }
          var server = session.server || {};
          if (server.state === "unavailable" || server.is_peace_member == null) {
            showUnavailable();
            return null;
          }
          if (server.is_peace_member !== true) {
            showConnectedNonMember();
            return null;
          }
          return request("/api/peace/process").then(function (process) {
            var processServer = process && process.server ? process.server : {};
            if (!processIsReady(process)) {
              if (processServer.state === "member" || processServer.state === "not_member" || processServer.is_peace_member === false) {
                showConnectedNonMember();
              } else {
                showUnavailable();
              }
              return;
            }
            renderOverview(session, process);
            showWorkspace();
          }).catch(function (error) {
            if (error && error.status === 401) showDisconnected("Sua sessão Discord expirou. Conecte novamente para continuar.");
            else if (error && error.status === 403) showConnectedNonMember();
            else showUnavailable();
          });
        })
        .catch(function () { showUnavailable(); })
        .finally(function () { loading = false; });
    }

    if (refresh) refresh.addEventListener("click", load);
    if (retry) retry.addEventListener("click", load);
    if (logout) logout.addEventListener("click", function () {
      logout.disabled = true;
      request("/api/auth/discord/logout", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" })
        .then(function () { window.location.replace("/acessar/?status=logged-out"); })
        .catch(function () { logout.disabled = false; });
    });
    load();
  }

  site.initMemberArea = initMemberArea;
})(window);
