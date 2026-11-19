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
    var sidebarCollapse = workspace && workspace.querySelector("[data-member-sidebar-collapse]");
    var sidebarScrim = workspace && workspace.querySelector("[data-member-sidebar-scrim]");
    var loadingStatus = workspace && workspace.querySelector("[data-member-loading-status]");
    var sidebarLinks = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-nav-link]")) : [];
    var memberViews = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-view]")) : [];
    var workspaceToolbar = workspace && workspace.querySelector(".member-workspace-toolbar");
    var memberContextTitle = workspace && workspace.querySelector("[data-member-context-title]");
    var toolbarClipsSearch = workspace && workspace.querySelector("[data-member-toolbar-clips-search]");
    var toolbarLibrarySearch = workspace && workspace.querySelector("[data-member-toolbar-library-search]");
    var toolbarAccount = workspace && workspace.querySelector("[data-member-toolbar-account]");
    var toolbarRefresh = workspace && workspace.querySelector("[data-member-view-refresh]");
    var toolbarAccountTrigger = workspace && workspace.querySelector("[data-member-toolbar-account-trigger]");
    var toolbarAccountMenu = workspace && workspace.querySelector("[data-member-toolbar-account-menu]");
    var toolbarAccountAvatar = workspace && workspace.querySelector("[data-member-toolbar-avatar]");
    var toolbarAccountAvatarFallback = workspace && workspace.querySelector("[data-member-toolbar-avatar-fallback]");
    var toolbarAccountName = workspace && workspace.querySelector("[data-member-toolbar-name]");
    var toolbarAccountUsername = workspace && workspace.querySelector("[data-member-toolbar-username]");
    var toolbarAccountLogout = workspace && workspace.querySelector("[data-member-toolbar-logout]");
    var sidebarName = workspace && workspace.querySelector("[data-member-sidebar-name]");
    var sidebarUsername = workspace && workspace.querySelector("[data-member-sidebar-username]");
    var sidebarAvatar = workspace && workspace.querySelector("[data-member-sidebar-avatar]");
    var sidebarAvatarFallback = workspace && workspace.querySelector("[data-member-sidebar-avatar-fallback]");
    var memberName = workspace && workspace.querySelector("[data-member-name]");
    var memberUsername = workspace && workspace.querySelector("[data-member-username]");
    var memberRoles = workspace && workspace.querySelector("[data-member-roles]");
    var memberScore = workspace && workspace.querySelector("[data-member-score]");
    var memberAssignmentCount = workspace && workspace.querySelector("[data-member-assignment-count]");
    var memberAvatar = workspace && workspace.querySelector("[data-member-avatar]");
    var memberAvatarFallback = workspace && workspace.querySelector("[data-member-avatar-fallback]");
    var connection = workspace && workspace.querySelector("[data-member-connection]");
    var notificationTrigger = workspace && workspace.querySelector("[data-member-notifications]");
    var notificationPanel = workspace && workspace.querySelector("[data-member-notification-panel]");
    var notificationClose = workspace && workspace.querySelector("[data-member-notifications-close]");
    var notificationList = workspace && workspace.querySelector("[data-member-notification-list]");
    var notificationBadge = workspace && workspace.querySelector("[data-member-notification-badge]");
    var noticesViewList = workspace && workspace.querySelector("[data-member-notices-view-list]");
    var partnerList = workspace && workspace.querySelector("[data-member-partners-list]");
    var navCounts = {
      clips: workspace && workspace.querySelector('[data-member-nav-count="clips"]'),
      proofs: workspace && workspace.querySelector('[data-member-nav-count="proofs"]'),
      notices: workspace && workspace.querySelector('[data-member-nav-count="notices"]')
    };
    var managementGroup = workspace && workspace.querySelector("[data-member-management-group]");
    var logout = workspace && workspace.querySelector("[data-member-logout]");
    var processSummary = workspace && workspace.querySelector("[data-member-process-summary]");
    var processStatus = workspace && workspace.querySelector("[data-member-process-status]");
    var processCount = workspace && workspace.querySelector("[data-member-process-count]");
    var processAssignments = workspace && workspace.querySelector("[data-member-process-assignments]");
    var managerList = workspace && workspace.querySelector("[data-member-manager-list]");
    var managerCount = workspace && workspace.querySelector("[data-member-manager-count]");
    var managerSearch = workspace && workspace.querySelector("[data-member-manager-search]");
    var managerFilterButtons = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-manager-filter]")) : [];
    var managerModal = document.querySelector("[data-member-manager-modal]");
    var managerForm = managerModal && managerModal.querySelector("[data-member-manager-form]");
    var managerFormStatus = managerModal && managerModal.querySelector("[data-member-manager-form-status]");
    var managerSubmit = managerModal && managerModal.querySelector("[data-member-manager-submit]");
    var managerGenerated = managerModal && managerModal.querySelector("[data-member-manager-generated]");
    var managerGeneratedLink = managerModal && managerModal.querySelector("[data-member-manager-generated-link]");
    var managerOpen = workspace && workspace.querySelector("[data-member-manager-open]");
    var managerClose = managerModal && managerModal.querySelector("[data-member-manager-close]");
    var managerCancel = managerModal && managerModal.querySelector("[data-member-manager-cancel]");
    var scanGroup = workspace && workspace.querySelector("[data-member-scan-group]");
    var investigationGroup = workspace && workspace.querySelector("[data-member-investigation-group]");
    var scanLinks = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-scan-link]")) : [];
    var scanList = workspace && workspace.querySelector("[data-member-scan-list]");
    var scanFilterButtons = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-scan-filter]")) : [];
    var investigationList = workspace && workspace.querySelector("[data-member-investigation-list]");
    var investigationCount = workspace && workspace.querySelector("[data-member-investigation-count]");
    var investigationOpen = workspace && workspace.querySelector("[data-member-investigation-open]");
    var investigationModal = document.querySelector("[data-member-investigation-modal]");
    var investigationForm = investigationModal && investigationModal.querySelector("[data-member-investigation-form]");
    var investigationFormStatus = investigationModal && investigationModal.querySelector("[data-member-investigation-form-status]");
    var investigationSubmit = investigationModal && investigationModal.querySelector("[data-member-investigation-submit]");
    var investigationClose = investigationModal && investigationModal.querySelector("[data-member-investigation-close]");
    var investigationCancel = investigationModal && investigationModal.querySelector("[data-member-investigation-cancel]");
    var evidenceModal = document.querySelector("[data-member-evidence-modal]");
    var evidenceForm = evidenceModal && evidenceModal.querySelector("[data-member-evidence-form]");
    var evidenceFormStatus = evidenceModal && evidenceModal.querySelector("[data-member-evidence-form-status]");
    var evidenceSubmit = evidenceModal && evidenceModal.querySelector("[data-member-evidence-submit]");
    var evidenceClose = evidenceModal && evidenceModal.querySelector("[data-member-evidence-close]");
    var evidenceCancel = evidenceModal && evidenceModal.querySelector("[data-member-evidence-cancel]");
    var approvalModal = document.querySelector("[data-member-approval-modal]");
    var approvalForm = approvalModal && approvalModal.querySelector("[data-member-approval-form]");
    var approvalFormStatus = approvalModal && approvalModal.querySelector("[data-member-approval-form-status]");
    var approvalSubmit = approvalModal && approvalModal.querySelector("[data-member-approval-submit]");
    var approvalGenerated = approvalModal && approvalModal.querySelector("[data-member-approval-generated]");
    var approvalClose = approvalModal && approvalModal.querySelector("[data-member-approval-close]");
    var approvalCancel = approvalModal && approvalModal.querySelector("[data-member-approval-cancel]");
    var noticeOpenButtons = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-notice-open], [data-member-notice-view-open]")) : [];
    var noticeModal = document.querySelector("[data-member-notice-modal]");
    var noticeForm = noticeModal && noticeModal.querySelector("[data-member-notice-form]");
    var noticeFormStatus = noticeModal && noticeModal.querySelector("[data-member-notice-form-status]");
    var noticeSubmit = noticeModal && noticeModal.querySelector("[data-member-notice-submit]");
    var noticeClose = noticeModal && noticeModal.querySelector("[data-member-notice-close]");
    var noticeCancel = noticeModal && noticeModal.querySelector("[data-member-notice-cancel]");
    var noticeAttachment = noticeModal && noticeModal.querySelector("[data-member-notice-attachment]");
    var noticeAttachmentPreview = noticeModal && noticeModal.querySelector("[data-member-notice-attachment-preview]");
    var noticeDropzone = noticeModal && noticeModal.querySelector("[data-member-notice-dropzone]");
    var partnerOpen = workspace && workspace.querySelector("[data-member-partner-open]");
    var partnerModal = document.querySelector("[data-member-partner-modal]");
    var partnerForm = partnerModal && partnerModal.querySelector("[data-member-partner-form]");
    var partnerFormStatus = partnerModal && partnerModal.querySelector("[data-member-partner-form-status]");
    var partnerSubmit = partnerModal && partnerModal.querySelector("[data-member-partner-submit]");
    var partnerClose = partnerModal && partnerModal.querySelector("[data-member-partner-close]");
    var partnerCancel = partnerModal && partnerModal.querySelector("[data-member-partner-cancel]");
    var partnerModalTitle = partnerModal && partnerModal.querySelector("#member-partner-modal-title");
    var logoutStatus = workspace && workspace.querySelector("[data-member-logout-status]");
    var retry = gate && gate.querySelector("[data-member-retry]");
    var gateAction = gate && gate.querySelector("[data-member-discord-connect]");
    var loading = false;
    var notificationsLoading = false;
    var notificationsLoaded = false;
    var clipsCountLoading = false;
    var managerAssignmentsLoading = false;
    var managerAssignments = [];
    var managerStatusFilter = "all";
    var managerPollingTimer = null;
    var scanLoading = false;
    var scanMessages = [];
    var scanStatusFilter = "all";
    var noticeAttachmentData = null;
    var managerPreviousFocus = null;
    var activeModal = null;
    var activeModalPreviousFocus = null;
    var investigationLoading = false;
    var investigationCases = [];
    var selectedInvestigationCaseId = null;
    var partnersLoading = false;
    var partnerItems = [];
    var currentProcess = null;
    var currentView = "overview";
    var editingPartnerId = null;
    var shellReadyStorageKey = "peace.member.shell-ready.v1";
    var sidebarCollapsedStorageKey = "peace.member.sidebar-collapsed.v1";
    var seenNoticeStorageKey = "peace.member.notices.seen.v1";
    var viewTitles = {
      overview: "Visão geral",
      library: "BIBLIOTECA",
      partners: "PARCEIROS",
      clips: "CLIPES",
      process: "PROCESSO E PROVAS",
      manager: "GERENCIAR PROVAS",
      scan: "SCAN-ONLY",
      investigation: "CASOS E OCORRÊNCIAS",
      notices: "AVISOS"
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
    function disclosureArrow() {
      var arrow = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      arrow.classList.add("disclosure-arrow");
      arrow.setAttribute("viewBox", "0 0 24 24");
      arrow.setAttribute("aria-hidden", "true");
      arrow.setAttribute("focusable", "false");
      arrow.innerHTML = '<path d="m6 9 6 6 6-6"></path>';
      return arrow;
    }
    function setNavCount(name, count) {
      var node = navCounts[name];
      if (!node) return;
      var value = Math.max(0, Number(count) || 0);
      node.textContent = value > 99 ? "99+" : String(value);
      node.hidden = value === 0;
    }
    function loadClipCount() {
      if (!navCounts.clips || clipsCountLoading) return;
      clipsCountLoading = true;
      request("/api/clips?limit=1")
        .then(function (payload) {
          if (!payload || payload.ok !== true) return;
          var total = payload.total != null ? payload.total : (Array.isArray(payload.clips) ? payload.clips.length : 0);
          setNavCount("clips", total);
        })
        .catch(function (error) {
          if (!error || Number(error.status) !== 404) return;
          return request("/api/media").then(function (payload) {
            var clips = payload && Array.isArray(payload.clips) ? payload.clips : [];
            setNavCount("clips", clips.length);
          });
        })
        .catch(function () { /* the menu keeps the count hidden when the source is unavailable */ })
        .finally(function () { clipsCountLoading = false; });
    }
    function noticeKey(item) {
      return String((item && (item.id || item.url)) || "") + "|" + String(item && item.published_at || "") + "|" + String(item && item.text || "");
    }
    function readSeenNoticeKeys() {
      try {
        var parsed = JSON.parse(window.localStorage.getItem(seenNoticeStorageKey) || "[]");
        return Array.isArray(parsed) ? parsed.filter(function (value) { return typeof value === "string"; }) : [];
      } catch (error) {
        return [];
      }
    }
    function writeSeenNoticeKeys(keys) {
      try { window.localStorage.setItem(seenNoticeStorageKey, JSON.stringify(keys.slice(-120))); } catch (error) { /* optional */ }
    }
    function markNoticesSeen(items) {
      var keys = readSeenNoticeKeys();
      items.forEach(function (item) {
        var key = noticeKey(item);
        if (key && keys.indexOf(key) < 0) keys.push(key);
      });
      writeSeenNoticeKeys(keys);
    }
    function memberState(message, mode) {
      var state = document.createElement("div");
      state.className = "member-block-state member-block-state--" + (mode || "empty");
      if (mode === "loading") {
        state.innerHTML = '<span class="peace-spinner" aria-hidden="true"></span><span></span>';
        state.lastElementChild.textContent = message;
        return state;
      }
      if (mode === "empty" || mode === "error") {
        var icon = document.createElement("span");
        icon.className = "member-state-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.innerHTML = mode === "error"
          ? '<svg viewBox="0 0 24 24"><path d="M12 4.5 20 19H4l8-14.5Z"></path><path d="M12 9v4M12 16.5h.01"></path></svg>'
          : '<svg viewBox="0 0 24 24"><path d="M5 7.5A2.5 2.5 0 0 1 7.5 5h9A2.5 2.5 0 0 1 19 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 5 16.5v-9Z"></path><path d="M8.5 12h7"></path></svg>';
        state.appendChild(icon);
      }
      var copy = document.createElement("span");
      copy.textContent = message;
      state.appendChild(copy);
      return state;
    }
    function renderPartners(payload) {
      if (!partnerList) return;
      var block = payload && payload.partners ? payload.partners : {};
      var items = Array.isArray(block) ? block : (Array.isArray(block.items) ? block.items : []);
      partnerItems = items.slice();
      var sourceState = payload && payload.source && payload.source.state
        ? payload.source.state
        : (block && block.state ? block.state : "");
      partnerList.textContent = "";
      if (!items.length) {
        var emptyMessage = sourceState === "unavailable"
          ? "A fonte de parceiros está indisponível agora. Tente novamente em instantes."
          : "Ainda não há parceiros publicados pela gestão.";
        partnerList.appendChild(memberState(emptyMessage, sourceState === "unavailable" ? "error" : "empty"));
        return;
      }
      items.forEach(function (item) {
        var article = document.createElement("article");
        article.className = "member-partner-item";
        article.setAttribute("role", "listitem");
        var coverUrl = safePartnerImageUrl(item.image_url);
        if (coverUrl) {
          var cover = document.createElement("img");
          cover.className = "member-partner-cover";
          cover.src = coverUrl;
          cover.alt = "Capa de " + (item.title || "parceiro");
          cover.loading = "lazy";
          article.appendChild(cover);
        }
        var heading = document.createElement("h2");
        heading.textContent = item.title || item.author || "Parceiro Peace";
        var copy = document.createElement("p");
        copy.textContent = item.description || item.text || "Organização parceira da Peace.";
        article.appendChild(heading);
        article.appendChild(copy);
        var links = document.createElement("div");
        links.className = "member-partner-links";
        if (/^https?:\/\//i.test(String(item.url || ""))) {
          var link = document.createElement("a");
          link.className = "partner-link-badge";
          link.href = String(item.url);
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = "Visitar ↗";
          links.appendChild(link);
        }
        if (links.childNodes.length) article.appendChild(links);
        if (currentCapabilities().partnersEdit) {
          var edit = document.createElement("button");
          edit.type = "button";
          edit.className = "member-partner-edit";
          edit.dataset.memberPartnerEdit = item.id || "";
          edit.setAttribute("aria-label", "Editar " + (item.title || "parceria"));
          edit.title = "Editar parceria";
          edit.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16.5-.7 3.7 3.7-.7L18.5 8a2.1 2.1 0 0 0-3-3L4 16.5Z"></path><path d="m14.5 6.5 3 3"></path></svg>';
          article.appendChild(edit);
        }
        partnerList.appendChild(article);
      });
    }

    function loadPartners() {
      if (!partnerList || partnersLoading) return;
      partnersLoading = true;
      partnerList.replaceChildren(memberState("Consultando parceiros publicados…", "loading"));
      request("/api/partners")
        .then(function (payload) {
          if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "Não consegui consultar as parcerias.");
          currentProcess = Object.assign({}, currentProcess || {}, payload);
          renderPartners(currentProcess);
        })
        .catch(function (error) {
          partnerList.replaceChildren(memberState(error.message || "Não consegui carregar as parcerias agora.", "error"));
        })
        .finally(function () { partnersLoading = false; });
    }

    function safePartnerImageUrl(value) {
      var raw = String(value || "").trim();
      if (!raw) return "";
      try {
        var parsed = new URL(raw, window.location.href);
        if (parsed.protocol !== "https:" || parsed.username || parsed.password) return "";
        return parsed.href;
      } catch (error) { return ""; }
    }
    function statusLabel(item) {
      if (item.status === "submitted") return item.passed ? "Aprovado" : "Não aprovado";
      if (item.status === "in_progress") return "Em andamento";
      if (item.status === "expired") return "Prazo encerrado";
      if (item.status === "rejected" || item.status === "revoked") return "Reprovado";
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
      renderAvatarNode(toolbarAccountAvatar, toolbarAccountAvatarFallback, identity);
    }

    function renderSidebarProfile(identity) {
      var profile = identity || {};
      if (sidebarName) sidebarName.textContent = profile.global_name || profile.display_name || profile.username || "membro";
      if (sidebarUsername) sidebarUsername.textContent = profile.username ? "@" + profile.username : "@discord";
      if (toolbarAccountName) toolbarAccountName.textContent = profile.global_name || profile.display_name || profile.username || "membro";
      if (toolbarAccountUsername) toolbarAccountUsername.textContent = profile.username ? "@" + profile.username : "@discord";
      renderAvatarNode(sidebarAvatar, sidebarAvatarFallback, profile);
      renderAvatarNode(toolbarAccountAvatar, toolbarAccountAvatarFallback, profile);
    }

    function renderRoles(server) {
      if (!memberRoles) return;
      var labels = [];
      if (server && server.is_peace_member === true) labels.push("Membro Peace");
      if (server && server.is_manager === true) labels.push("Gerência");
      if (server && server.is_staff === true && server.is_manager !== true) labels.push("Staff");
      if (server && server.is_investigator === true) labels.push("Investigador");
      memberRoles.textContent = "";
      labels.forEach(function (label) {
        var chip = document.createElement("span");
        chip.className = "member-role-chip";
        chip.textContent = label;
        memberRoles.appendChild(chip);
      });
      memberRoles.hidden = labels.length === 0;
    }

    function currentCapabilities() {
      var server = currentProcess && currentProcess.server ? currentProcess.server : {};
      return {
        manager: server.is_manager === true,
        staff: server.is_staff === true,
        investigator: server.is_investigator === true,
        scanOnly: server.is_scan_only === true,
        partnersEdit: server.can_edit_partners === true
      };
    }

    function applyCapabilityVisibility() {
      var capabilities = currentCapabilities();
      if (managementGroup) managementGroup.hidden = !(capabilities.manager || capabilities.scanOnly);
      var managerLinks = workspace ? Array.prototype.slice.call(workspace.querySelectorAll("[data-member-manager]")) : [];
      managerLinks.forEach(function (link) { link.hidden = !capabilities.manager; });
      if (scanGroup) scanGroup.hidden = !capabilities.scanOnly;
      if (investigationGroup) investigationGroup.hidden = !capabilities.investigator;
      if (managerOpen) managerOpen.hidden = !(capabilities.manager && currentView === "manager");
      if (investigationOpen) investigationOpen.hidden = !(capabilities.investigator && currentView === "investigation");
      noticeOpenButtons.forEach(function (button) { button.hidden = !(capabilities.staff || capabilities.manager); });
      if (partnerOpen) partnerOpen.hidden = !(capabilities.partnersEdit && currentView === "partners");
      var scanUrl = currentProcess && currentProcess.server && currentProcess.server.scan_only_url;
      scanLinks.forEach(function (link) {
        link.href = link.hasAttribute("data-member-scan")
          ? "/area/?view=scan"
          : (/^https:\/\//i.test(String(scanUrl || "")) ? scanUrl : "/discord/");
      });
    }

    function safeNoticeAssetUrl(value) {
      var raw = String(value || "").trim();
      if (!raw) return "";
      try {
        var parsed = new URL(raw, window.location.href);
        var allowed = ["cdn.discordapp.com", "media.discordapp.net", "images-ext-1.discordapp.net"];
        return parsed.protocol === "https:" && allowed.indexOf(parsed.hostname.toLowerCase()) >= 0 ? parsed.href : "";
      } catch (error) { return ""; }
    }

    function renderNoticeMarkdown(container, value) {
      if (!container) return;
      function escapeHtml(text) {
        return String(text == null ? "" : text)
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
          .replace(/\"/g, "&quot;").replace(/'/g, "&#39;");
      }
      function inline(text) {
        return escapeHtml(text)
          .replace(/`([^`\n]+)`/g, "<code>$1</code>")
          .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
          .replace(/__([^_\n]+)__/g, "<strong>$1</strong>")
          .replace(/~~([^~\n]+)~~/g, "<del>$1</del>")
          .replace(/(^|\s)\*([^*\n]+)\*(?=\s|$)/g, "$1<em>$2</em>")
          .replace(/(^|\s)_([^_\n]+)_(?=\s|$)/g, "$1<em>$2</em>")
          .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
          .replace(/(^|[^\w])(@[\w.-]{2,32})/g, '$1<span class="notice-mention">$2</span>');
      }
      var lines = String(value || "Comunicado sem texto.").replace(/\r\n?/g, "\n").split("\n");
      var fragment = document.createDocumentFragment();
      var list = null;
      var code = false;
      var codeLines = [];
      function closeList() { if (list) { fragment.appendChild(list); list = null; } }
      lines.forEach(function (line) {
        if (/^\s*```/.test(line)) {
          if (code) {
            var pre = document.createElement("pre");
            var codeNode = document.createElement("code");
            codeNode.textContent = codeLines.join("\n");
            pre.appendChild(codeNode); fragment.appendChild(pre);
            codeLines = []; code = false;
          } else { closeList(); code = true; }
          return;
        }
        if (code) { codeLines.push(line); return; }
        var heading = line.match(/^\s*(#{1,3})\s+(.+)$/);
        var bullet = line.match(/^\s*[-*+]\s+(.+)$/);
        if (bullet) {
          if (!list) list = document.createElement("ul");
          var li = document.createElement("li");
          li.innerHTML = inline(bullet[1]);
          list.appendChild(li);
          return;
        }
        closeList();
        if (!line.trim()) return;
        var block = document.createElement(heading ? "h" + Math.min(3, heading[1].length) : /^\s*>/.test(line) ? "blockquote" : "p");
        block.innerHTML = inline(heading ? heading[2] : line.replace(/^\s*>\s?/, ""));
        fragment.appendChild(block);
      });
      if (code) {
        var trailing = document.createElement("pre");
        var trailingCode = document.createElement("code");
        trailingCode.textContent = codeLines.join("\n");
        trailing.appendChild(trailingCode); fragment.appendChild(trailing);
      }
      closeList();
      container.replaceChildren(fragment);
    }

    function createNoticeArticle(item, className) {
      var article = document.createElement("article");
      article.className = className || "member-notice-item";
      var heading = document.createElement("div"); heading.className = "member-notice-author";
      var avatar = document.createElement("span"); avatar.className = "member-notice-avatar";
      var avatarUrl = safeNoticeAssetUrl(item && item.avatar_url);
      if (avatarUrl) { var image = document.createElement("img"); image.src = avatarUrl; image.alt = ""; image.width = 32; image.height = 32; image.loading = "lazy"; image.addEventListener("error", function () { image.remove(); avatar.textContent = String(item.author || "P").charAt(0).toUpperCase(); }); avatar.appendChild(image); }
      else avatar.textContent = String(item && item.author || "P").charAt(0).toUpperCase();
      var author = document.createElement("div"); var name = document.createElement("strong"); name.textContent = item && item.author || "Peace"; var meta = document.createElement("small"); meta.textContent = date(item && item.published_at); author.appendChild(name); author.appendChild(meta); heading.appendChild(avatar); heading.appendChild(author); article.appendChild(heading);
      if (item && item.title) { var title = document.createElement("h3"); title.textContent = item.title; article.appendChild(title); }
      var copy = document.createElement("div"); copy.className = "member-notice-markdown"; renderNoticeMarkdown(copy, item && item.text); article.appendChild(copy);
      var imageUrl = safeNoticeAssetUrl(item && item.image_url);
      if (imageUrl) { var asset = document.createElement("img"); asset.className = "member-notice-asset"; asset.src = imageUrl; asset.alt = item && item.title ? "Imagem do aviso: " + item.title : "Imagem do aviso"; asset.loading = "lazy"; article.appendChild(asset); }
      return article;
    }

    function renderNotifications(payload) {
      if (!notificationList) return;
      var items = payload && Array.isArray(payload.notices) ? payload.notices : [];
      var sourceState = payload && payload.source ? payload.source.state : "unavailable";
      notificationList.textContent = "";
      // Keep the full Avisos view in sync even when the source is empty or
      // temporarily unavailable; otherwise it is left on its skeleton text.
      renderNoticesView(payload);

      var seenKeys = readSeenNoticeKeys();
      var unreadCount = items.filter(function (item) { return seenKeys.indexOf(noticeKey(item)) < 0; }).length;
      setNavCount("notices", items.length);
      if (notificationBadge) {
        notificationBadge.textContent = unreadCount > 9 ? "9+" : String(unreadCount);
        notificationBadge.hidden = unreadCount === 0;
      }
      if (notificationTrigger) {
        notificationTrigger.setAttribute(
          "aria-label",
          unreadCount ? (unreadCount === 1 ? "1 aviso não visto. Abrir avisos" : unreadCount + " avisos não vistos. Abrir avisos") : "Abrir avisos"
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

      items.slice(0, 4).forEach(function (item) { notificationList.appendChild(createNoticeArticle(item, "member-notification-item")); });
      if (currentView === "notices") markNoticesSeen(items);
      if (notificationPanel && !notificationPanel.hidden) {
        markNoticesSeen(items);
        if (notificationBadge) notificationBadge.hidden = true;
        if (notificationTrigger) notificationTrigger.setAttribute("aria-label", "Abrir avisos");
      }
    }

    function renderNoticesView(payload) {
      if (!noticesViewList) return;
      var items = payload && Array.isArray(payload.notices) ? payload.notices : [];
      noticesViewList.textContent = "";
      if (!items.length) {
        var emptyMessage = payload && payload.source && payload.source.state === "unavailable"
          ? "A fonte pública está indisponível. Tente novamente em instantes."
          : "Nenhum comunicado público foi publicado ainda.";
        noticesViewList.appendChild(memberState(emptyMessage, "empty"));
        return;
      }
      items.forEach(function (item) { noticesViewList.appendChild(createNoticeArticle(item)); });
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
      currentProcess = null;
      if (memberName) memberName.textContent = "membro";
      if (memberUsername) memberUsername.textContent = "@discord";
      if (memberRoles) {
        memberRoles.textContent = "";
        memberRoles.hidden = true;
      }
      if (memberAvatar) memberAvatar.hidden = true;
      if (memberAvatarFallback) memberAvatarFallback.hidden = true;
      if (memberScore) memberScore.textContent = "—";
      if (memberAssignmentCount) memberAssignmentCount.textContent = "0";
      setNavCount("proofs", 0);
      setNavCount("clips", 0);
      if (managementGroup) managementGroup.hidden = true;
      if (scanGroup) scanGroup.hidden = true;
      if (investigationGroup) investigationGroup.hidden = true;
      if (managerOpen) managerOpen.hidden = true;
      if (investigationOpen) investigationOpen.hidden = true;
      noticeOpenButtons.forEach(function (button) { button.hidden = true; });
      if (partnerOpen) partnerOpen.hidden = true;
      if (investigationList) investigationList.textContent = "";
      if (investigationCount) investigationCount.textContent = "0 casos";
      if (partnerList) {
        partnerList.textContent = "";
        partnerList.appendChild(memberState("Consultando parceiros publicados…", "loading"));
      }
      if (sidebarName) sidebarName.textContent = "membro";
      if (sidebarUsername) sidebarUsername.textContent = "@discord";
      if (toolbarAccountName) toolbarAccountName.textContent = "membro";
      if (toolbarAccountUsername) toolbarAccountUsername.textContent = "@discord";
      if (sidebarAvatar) sidebarAvatar.hidden = true;
      if (sidebarAvatarFallback) sidebarAvatarFallback.hidden = true;
      if (toolbarAccountAvatar) toolbarAccountAvatar.hidden = true;
      if (toolbarAccountAvatarFallback) toolbarAccountAvatarFallback.hidden = true;
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
      if (sidebarToggle) sidebarToggle.setAttribute("aria-label", nextOpen ? "Fechar menu" : "Abrir menu");
      if (sidebarToggleIcon) {
        sidebarToggleIcon.innerHTML = nextOpen
          ? '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M10 4H6.5A1.5 1.5 0 0 0 5 5.5v13A1.5 1.5 0 0 0 6.5 20H10"></path><path d="m13 8 4 4-4 4M17 12H8"></path></svg>'
          : '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14 4h3.5A1.5 1.5 0 0 1 19 5.5v13a1.5 1.5 0 0 1-1.5 1.5H14"></path><path d="m11 8-4 4 4 4M7 12h9"></path></svg>';
      }
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
          var first = sidebar.querySelector(".member-nav a");
          if (first) first.focus();
        }
      } else {
        sidebar.setAttribute("inert", "");
        if (moveFocus && sidebarToggle) sidebarToggle.focus();
      }
    }

    function syncSidebarLinkNames(collapsed) {
      sidebarLinks.forEach(function (link) {
        var labelNode = link.querySelector(".member-nav-icon + span");
        var label = labelNode && labelNode.textContent ? labelNode.textContent.trim() : "Seção da área";
        if (collapsed) {
          link.setAttribute("aria-label", label);
          link.title = label;
        } else {
          link.removeAttribute("aria-label");
          link.removeAttribute("title");
        }
      });
    }

    function setSidebarCollapsed(collapsed) {
      if (!shell || !sidebarCollapse || (window.matchMedia && window.matchMedia("(max-width: 900px)").matches)) return;
      var next = Boolean(collapsed);
      shell.dataset.sidebarCollapsed = String(next);
      sidebarCollapse.setAttribute("aria-expanded", String(!next));
      sidebarCollapse.setAttribute("aria-label", next ? "Expandir menu" : "Minimizar menu");
      sidebarCollapse.innerHTML = next
        ? '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14 4h3.5A1.5 1.5 0 0 1 19 5.5v13a1.5 1.5 0 0 1-1.5 1.5H14"></path><path d="m11 8-4 4 4 4M7 12h9"></path></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M10 4H6.5A1.5 1.5 0 0 0 5 5.5v13A1.5 1.5 0 0 0 6.5 20H10"></path><path d="m13 8 4 4-4 4M17 12H8"></path></svg>';
      syncSidebarLinkNames(next);
      try { window.localStorage.setItem(sidebarCollapsedStorageKey, next ? "1" : "0"); } catch (error) { /* optional */ }
    }

    function readSidebarCollapsed() {
      try { return window.localStorage.getItem(sidebarCollapsedStorageKey) === "1"; } catch (error) { return false; }
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
      if (nextView === "manager" && (!currentProcess || !currentProcess.server || currentProcess.server.is_manager !== true)) {
        nextView = "overview";
      }
      if (nextView === "scan" && !currentCapabilities().scanOnly) nextView = "overview";
      if (nextView === "investigation" && !currentCapabilities().investigator) nextView = "overview";
      var url = new URL(window.location.href);
      if (url.pathname.replace(/\/+$/, "/") !== "/area/") url.pathname = "/area/";
      if (nextView === "overview") url.searchParams.delete("view");
      else url.searchParams.set("view", nextView);
      if (nextView !== "library" && nextView !== "clips") url.searchParams.delete("q");
      var nextUrl = url.pathname + (url.search ? "?" + url.searchParams.toString() : "") + url.hash;
      if (replace) window.history.replaceState({}, document.title, nextUrl);
      else if (nextUrl !== window.location.pathname + window.location.search + window.location.hash) window.history.pushState({}, document.title, nextUrl);

      currentView = nextView;
      if (workspaceToolbar) workspaceToolbar.dataset.memberToolbarView = nextView;
      if (notificationTrigger) notificationTrigger.hidden = nextView !== "overview";
      if (toolbarAccount) toolbarAccount.hidden = nextView === "overview" || nextView === "library";
      if (toolbarRefresh) toolbarRefresh.hidden = nextView === "overview";
      if (toolbarClipsSearch) toolbarClipsSearch.hidden = nextView !== "clips";
      if (toolbarLibrarySearch) toolbarLibrarySearch.hidden = nextView !== "library";
      if (notificationPanel && (!notificationPanel.hidden || nextView !== "overview")) setNotificationsOpen(false, false);
      memberViews.forEach(function (node) { node.hidden = node.dataset.memberView !== nextView; });
      if (memberContextTitle) {
        if (nextView === "overview") {
          memberContextTitle.innerHTML = "<span>VISÃO</span><span>GERAL</span>";
        } else {
          memberContextTitle.textContent = viewTitles[nextView];
        }
      }
      syncSidebarLocation();
      if (nextView === "overview") loadNotifications();

      var activeView = memberViews.find(function (node) { return node.dataset.memberView === nextView; });
      if (nextView === "library" && activeView && typeof site.initStudies === "function") site.initStudies(workspace || activeView);
      if (nextView === "partners" && activeView) loadPartners();
      if (nextView === "clips" && activeView && typeof site.initClips === "function") site.initClips(workspace || activeView);
      if (nextView === "process") renderProcessView(currentProcess || {});
      if (nextView === "manager") {
        loadManagerAssignments();
        scheduleManagerPolling();
      } else {
        stopManagerPolling();
      }
      if (nextView === "scan") applyCapabilityVisibility();
      if (nextView === "scan") loadScanMessages();
      if (nextView === "investigation") loadInvestigations();
      if (nextView === "notices") loadNotifications();
      applyCapabilityVisibility();
      if (moveFocus && activeView) {
        var target = activeView.querySelector("[data-member-view-focus], input, a, button");
        if (!target) {
          target = activeView.querySelector("h1, h2");
          if (target) target.setAttribute("tabindex", "-1");
        }
        if (target) target.focus({ preventScroll: false });
      }
    }

    function investigationStatusLabel(status) {
      return {
        open: "Aberto",
        under_review: "Em análise",
        pending_approval: "Aguardando aprovação",
        approved: "Aprovado",
        rejected: "Reprovado",
        archived: "Arquivado"
      }[status] || "Status desconhecido";
    }

    function investigationStatusTone(status) {
      if (status === "approved") return "ready";
      if (status === "rejected") return "error";
      if (status === "pending_approval") return "pending";
      return "planned";
    }

    function createInvestigationEvidence(item) {
      var article = document.createElement("article");
      article.className = "member-investigation-evidence";
      var heading = document.createElement("div");
      heading.className = "member-investigation-item-heading";
      var title = document.createElement("strong");
      title.textContent = item.title || "Evidência sem título";
      var tag = document.createElement("span");
      tag.className = "status-tag status-tag--" + (item.classification === "confirmed" ? "ready" : "planned");
      tag.textContent = item.classification === "confirmed" ? "Comprovado" : "Referência";
      heading.appendChild(title);
      heading.appendChild(tag);
      article.appendChild(heading);
      var meta = document.createElement("small");
      var typeLabels = { clip: "Clipe", image: "Imagem", document: "Documento", occurrence: "Relato", reference: "Referência", note: "Observação" };
      meta.textContent = (typeLabels[item.type] || "Referência") + " · " + date(item.created_at);
      article.appendChild(meta);
      var note = document.createElement("p");
      note.textContent = item.note || "Sem observação.";
      article.appendChild(note);
      if (/^https:\/\//i.test(String(item.source_url || ""))) {
        var source = document.createElement("a");
        source.className = "text-link";
        source.href = item.source_url;
        source.target = "_blank";
        source.rel = "noopener noreferrer";
        source.textContent = "Abrir origem ↗";
        article.appendChild(source);
      }
      return article;
    }

    function createInvestigationCase(caseRecord) {
      var details = document.createElement("details");
      details.className = "member-investigation-case";
      var summary = document.createElement("summary");
      var copy = document.createElement("span");
      var title = document.createElement("strong");
      title.textContent = (caseRecord.title || "Caso investigativo") + " · #" + String(caseRecord.id || "—");
      var subtitle = document.createElement("small");
      subtitle.textContent = investigationStatusLabel(caseRecord.status) + " · atualizado " + date(caseRecord.updated_at);
      copy.appendChild(title);
      copy.appendChild(subtitle);
      summary.appendChild(copy);
      summary.appendChild(disclosureArrow());
      var content = document.createElement("div");
      content.className = "member-investigation-case-content";
      var status = document.createElement("span");
      status.className = "status-tag status-tag--" + investigationStatusTone(caseRecord.status);
      status.textContent = investigationStatusLabel(caseRecord.status);
      content.appendChild(status);
      var summaryText = document.createElement("p");
      summaryText.className = "member-investigation-summary";
      summaryText.textContent = caseRecord.summary || "Sem resumo informado.";
      content.appendChild(summaryText);
      var actions = document.createElement("div");
      actions.className = "member-investigation-actions";
      if (currentCapabilities().investigator && !["approved", "archived"].includes(caseRecord.status)) {
        var evidenceButton = document.createElement("button");
        evidenceButton.type = "button";
        evidenceButton.className = "button button--outline";
        evidenceButton.dataset.memberCaseEvidence = "";
        evidenceButton.dataset.caseId = String(caseRecord.id);
        evidenceButton.textContent = "Adicionar evidência";
        actions.appendChild(evidenceButton);
      }
      if (currentCapabilities().investigator && ["open", "under_review"].includes(caseRecord.status)) {
        var approvalButton = document.createElement("button");
        approvalButton.type = "button";
        approvalButton.className = "button button--light";
        approvalButton.dataset.memberCaseApproval = "";
        approvalButton.dataset.caseId = String(caseRecord.id);
        approvalButton.textContent = "Solicitar aprovação";
        actions.appendChild(approvalButton);
      }
      if (currentCapabilities().investigator && caseRecord.status === "approved") {
        var archiveButton = document.createElement("button");
        archiveButton.type = "button";
        archiveButton.className = "button button--light";
        archiveButton.dataset.memberCaseArchive = "";
        archiveButton.dataset.caseId = String(caseRecord.id);
        archiveButton.textContent = "Concluir caso";
        actions.appendChild(archiveButton);
        var approvedNote = document.createElement("p");
        approvedNote.className = "member-investigation-summary member-investigation-summary--success";
        approvedNote.textContent = "Todos os avaliadores aprovaram. Conclua o caso para arquivar a investigação.";
        content.appendChild(approvedNote);
      }
      if (currentCapabilities().investigator && caseRecord.status === "rejected") {
        var reopenButton = document.createElement("button");
        reopenButton.type = "button";
        reopenButton.className = "button button--outline";
        reopenButton.dataset.memberCaseReopen = "";
        reopenButton.dataset.caseId = String(caseRecord.id);
        reopenButton.textContent = "Reabrir análise";
        actions.appendChild(reopenButton);
      }
      if (actions.childNodes.length) content.appendChild(actions);

      var evidenceSection = document.createElement("section");
      evidenceSection.className = "member-investigation-subsection";
      var evidenceHeading = document.createElement("h3");
      evidenceHeading.textContent = "Evidências e referências";
      evidenceSection.appendChild(evidenceHeading);
      var evidenceItems = Array.isArray(caseRecord.evidence) ? caseRecord.evidence : [];
      if (!evidenceItems.length) {
        var noEvidence = document.createElement("p");
        noEvidence.className = "member-block-state";
        noEvidence.textContent = "Nenhuma evidência foi registrada ainda.";
        evidenceSection.appendChild(noEvidence);
      } else {
        var evidenceList = document.createElement("div");
        evidenceList.className = "member-investigation-evidence-list";
        evidenceItems.forEach(function (item) { evidenceList.appendChild(createInvestigationEvidence(item)); });
        evidenceSection.appendChild(evidenceList);
      }
      content.appendChild(evidenceSection);

      var approvalItems = Array.isArray(caseRecord.approvals) ? caseRecord.approvals : [];
      if (approvalItems.length) {
        var approvalSection = document.createElement("section");
        approvalSection.className = "member-investigation-subsection";
        var approvalHeading = document.createElement("h3");
        approvalHeading.textContent = "Aprovação privada";
        approvalSection.appendChild(approvalHeading);
        approvalItems.forEach(function (approval) {
          var approvalRow = document.createElement("article");
          approvalRow.className = "member-investigation-approval";
          var approvalMeta = document.createElement("div");
          approvalMeta.className = "member-investigation-item-heading";
          var evaluator = document.createElement("strong");
          evaluator.textContent = "Avaliador da equipe";
          var approvalStatus = document.createElement("span");
          approvalStatus.className = "status-tag status-tag--" + (approval.status === "approved" ? "ready" : approval.status === "rejected" ? "error" : "pending");
          approvalStatus.textContent = approval.status === "approved" ? "Aprovou" : approval.status === "rejected" ? "Reprovou" : approval.status === "expired" ? "Expirado" : "Pendente";
          approvalMeta.appendChild(evaluator);
          approvalMeta.appendChild(approvalStatus);
          approvalRow.appendChild(approvalMeta);
          var expectation = document.createElement("p");
          expectation.textContent = "Expectativa: " + (approval.expected_outcome || "não informada");
          approvalRow.appendChild(expectation);
          if (approval.decision_note) {
            var decisionNote = document.createElement("small");
            decisionNote.textContent = "Observação: " + approval.decision_note;
            approvalRow.appendChild(decisionNote);
          }
          approvalSection.appendChild(approvalRow);
        });
        content.appendChild(approvalSection);
      }

      var eventItems = Array.isArray(caseRecord.events) ? caseRecord.events : [];
      if (eventItems.length) {
        var auditSection = document.createElement("section");
        auditSection.className = "member-investigation-subsection member-investigation-audit";
        var auditHeading = document.createElement("h3");
        auditHeading.textContent = "Auditoria";
        auditSection.appendChild(auditHeading);
        eventItems.slice(0, 8).forEach(function (event) {
          var line = document.createElement("p");
          line.textContent = date(event.created_at) + " · " + event.type;
          auditSection.appendChild(line);
        });
        content.appendChild(auditSection);
      }
      details.appendChild(summary);
      details.appendChild(content);
      return details;
    }

    function renderInvestigations(cases) {
      if (!investigationList) return;
      investigationCases = Array.isArray(cases) ? cases : [];
      investigationList.textContent = "";
      if (investigationCount) investigationCount.textContent = investigationCases.length + (investigationCases.length === 1 ? " caso" : " casos");
      if (!investigationCases.length) {
        investigationList.appendChild(memberState("Nenhum caso investigativo foi registrado ainda.", "empty"));
        return;
      }
      investigationCases.forEach(function (caseRecord) { investigationList.appendChild(createInvestigationCase(caseRecord)); });
    }

    function loadInvestigations() {
      if (!investigationList || investigationLoading || !currentCapabilities().investigator) return;
      investigationLoading = true;
      investigationList.textContent = "";
       var loadingState = document.createElement("div");
       loadingState.className = "member-block-state member-block-state--loading";
       loadingState.innerHTML = '<span class="peace-spinner" aria-hidden="true"></span><span>Consultando casos investigativos…</span>';
      investigationList.appendChild(loadingState);
      request("/api/investigations")
        .then(function (payload) {
          if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "Não consegui consultar os casos.");
          renderInvestigations(payload.cases);
        })
        .catch(function (error) {
          investigationList.textContent = "";
          investigationList.appendChild(memberState(error.message || "Não consegui carregar os casos agora.", "error"));
        })
        .finally(function () { investigationLoading = false; });
    }

    function scanStatusLabel(status) {
      return status === "approved" ? "Aprovado" : status === "rejected" ? "Reprovado" : status === "pending" ? "Pendente · aprovar/reprovar" : "Informativo";
    }

    function renderScanMessages() {
      if (!scanList) return;
      var items = scanMessages.filter(function (item) {
        return scanStatusFilter === "all" || String(item.status || "other") === scanStatusFilter;
      });
      scanList.textContent = "";
      if (!items.length) {
        scanList.appendChild(memberState(scanMessages.length ? "Nenhuma mensagem corresponde a este filtro." : "Nenhuma decisão foi encontrada no scan-only.", "empty"));
        return;
      }
      items.forEach(function (item) {
        var article = document.createElement("article");
        article.className = "member-scan-item";
        var heading = document.createElement("div");
        heading.className = "member-scan-item-heading";
        var title = document.createElement("h3");
        title.textContent = item.title || "Mensagem do scan-only";
        var tag = document.createElement("span");
        tag.className = "status-tag status-tag--" + (item.status === "approved" ? "ready" : item.status === "rejected" ? "error" : item.status === "pending" ? "pending" : "planned");
        tag.textContent = scanStatusLabel(item.status);
        heading.appendChild(title);
        heading.appendChild(tag);
        article.appendChild(heading);
        var meta = document.createElement("small");
        meta.textContent = (item.author || "Peace") + " · " + date(item.published_at);
        article.appendChild(meta);
         if (item.avatar_url) {
           var avatar = document.createElement("img");
           avatar.className = "member-scan-avatar"; avatar.src = item.avatar_url; avatar.alt = ""; avatar.width = 32; avatar.height = 32; avatar.loading = "lazy";
           article.insertBefore(avatar, heading);
         }
        if (item.text) {
           var copy = document.createElement("div");
           copy.className = "member-scan-markdown";
           renderNoticeMarkdown(copy, item.text);
          article.appendChild(copy);
        }
        if (safeNoticeAssetUrl(item.image_url)) {
          var asset = document.createElement("img");
          asset.className = "member-scan-asset";
          asset.src = safeNoticeAssetUrl(item.image_url);
          asset.alt = item.title ? "Imagem de " + item.title : "Imagem da mensagem";
          asset.loading = "lazy";
          article.appendChild(asset);
        }
         if (item.status === "pending" && item.request_id && currentCapabilities().scanOnly) {
           var actions = document.createElement("div"); actions.className = "member-scan-actions";
           var approve = document.createElement("button"); approve.type = "button"; approve.className = "button button--light button--small"; approve.dataset.scanDecision = "approve"; approve.dataset.requestId = item.request_id; approve.textContent = "Aprovar";
           var reject = document.createElement("button"); reject.type = "button"; reject.className = "button button--outline button--small"; reject.dataset.scanDecision = "reject"; reject.dataset.requestId = item.request_id; reject.textContent = "Reprovar";
           actions.append(approve, reject); article.appendChild(actions);
         }
        scanList.appendChild(article);
      });
    }

    function loadScanMessages() {
      if (!scanList || scanLoading || !currentCapabilities().scanOnly) return;
      scanLoading = true;
      scanList.textContent = "";
       var loadingState = document.createElement("div");
       loadingState.className = "member-block-state member-block-state--loading";
       loadingState.innerHTML = '<span class="peace-spinner" aria-hidden="true"></span><span>Consultando o scan-only…</span>';
      scanList.appendChild(loadingState);
      request("/api/scan-only")
        .then(function (payload) {
          if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "Não consegui consultar o scan-only.");
          scanMessages = Array.isArray(payload.messages) ? payload.messages : [];
          renderScanMessages();
        })
        .catch(function (error) {
          scanList.textContent = "";
          scanList.appendChild(memberState(error.message || "Não consegui carregar as mensagens do scan-only agora.", "error"));
        })
        .finally(function () { scanLoading = false; });
    }

    function openMemberModal(modal, form, statusNode) {
      if (!modal) return;
      activeModal = modal;
      activeModalPreviousFocus = document.activeElement;
      modal.hidden = false;
      document.body.classList.add("member-modal-open");
      if (workspace) workspace.setAttribute("inert", "");
      if (form) form.reset();
      if (statusNode) statusNode.textContent = "";
      if (modal === noticeModal) clearNoticeAttachment();
      var first = form && form.querySelector("input:not([type=hidden]), textarea, select");
      if (first) first.focus();
    }

    function closeMemberModal(modal, restoreFocus) {
      if (!modal || modal.hidden) return;
      modal.hidden = true;
      if (!document.querySelector(".member-modal:not([hidden])")) document.body.classList.remove("member-modal-open");
      if (workspace) workspace.removeAttribute("inert");
      if (restoreFocus && activeModalPreviousFocus && typeof activeModalPreviousFocus.focus === "function") activeModalPreviousFocus.focus();
      activeModal = null;
      activeModalPreviousFocus = null;
    }

    function clearNoticeAttachment() {
      noticeAttachmentData = null;
      if (noticeAttachment) noticeAttachment.value = "";
      if (noticeAttachmentPreview) {
        noticeAttachmentPreview.textContent = "";
        noticeAttachmentPreview.hidden = true;
      }
      if (noticeDropzone) noticeDropzone.classList.remove("is-dragover");
    }

    function readNoticeAttachment(file) {
      if (!file) return;
      var allowed = ["image/png", "image/jpeg", "image/gif", "image/webp"];
      if (allowed.indexOf(String(file.type || "").toLowerCase()) < 0 || file.size > 8 * 1024 * 1024) {
        if (noticeFormStatus) {
          noticeFormStatus.textContent = "Escolha uma imagem PNG, JPG, GIF ou WebP de até 8 MB.";
          noticeFormStatus.dataset.state = "error";
        }
        clearNoticeAttachment();
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        noticeAttachmentData = { data: String(reader.result || ""), name: String(file.name || "anexo"), type: String(file.type || "image/png") };
        if (noticeAttachmentPreview) {
          noticeAttachmentPreview.textContent = "";
          var image = document.createElement("img");
          image.src = noticeAttachmentData.data;
          image.alt = "Prévia do anexo";
          noticeAttachmentPreview.appendChild(image);
          noticeAttachmentPreview.hidden = false;
        }
        if (noticeFormStatus && noticeFormStatus.dataset.state === "error") noticeFormStatus.textContent = "";
      };
      reader.readAsDataURL(file);
    }

    function identityIsReady(identity) {
      return Boolean(
        identity
        && /^[0-9]{15,25}$/.test(String(identity.discord_id || ""))
        && String(identity.username || identity.global_name || identity.display_name || "").trim()
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
      currentProcess = data;
      var identity = data.identity || (session && session.identity) || {};
      document.body.dataset.discordId = String(identity.discord_id || "");
      var profile = data.profile || {};
      var assignments = Array.isArray(data.assignments) ? data.assignments : [];
      overview.textContent = "";
      if (memberScore) memberScore.textContent = profile.score == null ? "—" : String(profile.score) + "/" + String(profile.score_scale || 100);
      if (memberAssignmentCount) memberAssignmentCount.textContent = String(assignments.length);
      setNavCount("proofs", assignments.length);

      var assignmentsBlock = document.createElement("section");
      assignmentsBlock.className = "member-data-block member-data-block--wide";
      assignmentsBlock.id = "member-results";
      assignmentsBlock.innerHTML = "<div class=\"member-data-heading member-overview-process-heading\"><h2 id=\"member-results-title\">Processo e provas</h2><a class=\"text-link\" data-member-view-link=\"process\" href=\"/area/?view=process\">Ver detalhes ↗</a></div>";
      var pendingCount = assignments.filter(function (assignment) { return assignment.status === "assigned" || assignment.status === "in_progress"; }).length;
      var submittedCount = assignments.filter(function (assignment) { return assignment.status === "submitted"; }).length;
      var summary = document.createElement("p");
      summary.className = "member-overview-process-summary";
      summary.textContent = assignments.length
        ? assignments.length + (assignments.length === 1 ? " prova atribuída" : " provas atribuídas") + " · " + pendingCount + (pendingCount === 1 ? " pendente" : " pendentes") + " · " + submittedCount + (submittedCount === 1 ? " resultado" : " resultados")
        : "Nenhuma prova foi atribuída ainda. Seu processo aparece aqui quando a Gerência iniciar uma etapa.";
      assignmentsBlock.appendChild(summary);
      if (!assignments.length) {
        assignmentsBlock.appendChild(memberState("A Gerência ainda não criou uma atribuição para esta conta.", "empty"));
      } else {
        var list = document.createElement("div");
        list.className = "member-assignment-list";
        assignments.forEach(function (assignment) {
          list.appendChild(createCandidateAssignmentDisclosure(assignment));
        });
        assignmentsBlock.appendChild(list);
      }
      overview.appendChild(assignmentsBlock);
      renderPartners(data);

      var managerLink = document.querySelector("[data-member-manager]");
      if (managerLink) managerLink.hidden = !(data.server && data.server.is_manager === true);
      if (managementGroup) managementGroup.hidden = !(data.server && data.server.is_manager === true);
      if (currentView === "manager" && (!data.server || data.server.is_manager !== true)) {
        setMemberView("overview", true, false);
      }
      if (memberName) memberName.textContent = identity.global_name || identity.display_name || identity.username || "membro";
      if (memberUsername) memberUsername.textContent = identity.username ? "@" + identity.username : "@discord";
      renderRoles(data.server);
      renderAvatar(identity);
      renderSidebarProfile(identity);
      syncSidebarLocation();
      applyCapabilityVisibility();
      setConnection("", "ready");
    }

    function setProcessStatus(label, tone) {
      if (!processStatus) return;
      processStatus.textContent = label;
      processStatus.className = "status-tag status-tag--" + (tone || "planned");
    }

    function renderReviewItems(container, review) {
      if (!container) return;
      container.setAttribute("aria-busy", "false");
      container.textContent = "";
      if (!Array.isArray(review) || !review.length) {
        container.appendChild(memberState("Nenhuma resposta detalhada está disponível.", "empty"));
        return;
      }
      review.forEach(function (item) {
        var article = document.createElement("article");
        article.className = "member-review-item " + (item.is_correct ? "is-correct" : "is-wrong");
        var heading = document.createElement("strong");
        heading.textContent = "Questão " + String(item.number || "—") + " · " + (item.is_correct ? "correta" : "revisar");
        var prompt = document.createElement("p");
        prompt.textContent = item.prompt || "Questão sem enunciado.";
        var selected = document.createElement("p");
        selected.textContent = "Sua resposta: " + (item.selected_option || "não respondida");
        var correct = document.createElement("p");
        correct.textContent = "Resposta correta: " + (item.correct_option || "não disponível");
        article.appendChild(heading);
        article.appendChild(prompt);
        article.appendChild(selected);
        article.appendChild(correct);
        container.appendChild(article);
      });
    }

    function loadCandidateReview(assignment, container) {
      if (!assignment || assignment.status !== "submitted" || !container || container.dataset.loaded === "true" || container.dataset.loading === "true") return;
      container.dataset.loading = "true";
      container.setAttribute("aria-busy", "true");
      container.setAttribute("aria-live", "polite");
       var loading = document.createElement("div");
       loading.className = "member-block-state member-block-state--loading";
       loading.innerHTML = '<span class="peace-spinner" aria-hidden="true"></span><span>Consultando respostas…</span>';
      container.appendChild(loading);
      request("/api/exams/review", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ assignment_id: assignment.id })
      }).then(function (payload) {
        if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "A revisão ainda não está disponível.");
        renderReviewItems(container, payload.review);
        container.dataset.loaded = "true";
      }).catch(function (error) {
        container.setAttribute("aria-busy", "false");
        container.textContent = "";
        container.appendChild(memberState(error.message || "Não consegui carregar as respostas agora.", "error"));
      }).finally(function () {
        delete container.dataset.loading;
      });
    }

    function createCandidateAssignmentDisclosure(assignment) {
      var details = document.createElement("details");
      details.className = "member-assignment-disclosure";
      var summary = document.createElement("summary");
      var copy = document.createElement("span");
      var title = document.createElement("strong");
      title.textContent = (assignment.exam_type_label || "Prova") + " · atribuição #" + assignment.id;
      var subtitle = document.createElement("small");
      subtitle.textContent = statusLabel(assignment) + " · " + (assignment.deadline_at ? "termina " + date(assignment.deadline_at) : "tempo de " + (assignment.duration_hours || 24) + "h após iniciar");
      copy.appendChild(title);
      copy.appendChild(subtitle);
      summary.appendChild(copy);
      summary.appendChild(disclosureArrow());

      var content = document.createElement("div");
      content.className = "member-assignment-disclosure-content";
      var meta = document.createElement("div");
      meta.className = "member-assignment-meta";
      var scoreScale = assignment.score_scale || 100;
      var totalQuestions = assignment.question_count ? "/" + assignment.question_count : "";
      [["Status", statusLabel(assignment)], ["Nota", assignment.score == null ? "Pendente" : assignment.score + "/" + scoreScale], ["Acertos", assignment.correct_count == null ? "—" : String(assignment.correct_count) + totalQuestions]].forEach(function (pair) {
        var cell = document.createElement("div");
        var label = document.createElement("small");
        label.textContent = pair[0];
        var value = document.createElement("strong");
        value.textContent = pair[1];
        cell.appendChild(label);
        cell.appendChild(value);
        meta.appendChild(cell);
      });
      content.appendChild(meta);
      if (assignment.status === "submitted") {
        var review = document.createElement("div");
        review.className = "member-review-list";
        content.appendChild(review);
        details.addEventListener("toggle", function () {
          if (details.open) loadCandidateReview(assignment, review);
        });
      }
      details.appendChild(summary);
      details.appendChild(content);
      return details;
    }

    function renderProcessView(data) {
      if (!processAssignments || !processSummary) return;
      var assignments = data && Array.isArray(data.assignments) ? data.assignments : [];
      processAssignments.textContent = "";
      if (processCount) processCount.textContent = assignments.length + (assignments.length === 1 ? " prova" : " provas");
      if (!assignments.length) {
        setProcessStatus("Aguardando atribuição", "planned");
        processAssignments.appendChild(memberState("A Gerência ainda não criou uma atribuição para esta conta.", "empty"));
      } else {
        var hasResult = assignments.some(function (item) { return item.status === "submitted"; });
        setProcessStatus(hasResult ? "Resultado disponível" : "Em andamento", hasResult ? "ready" : "planned");
        assignments.forEach(function (assignment) {
          processAssignments.appendChild(createCandidateAssignmentDisclosure(assignment));
        });
      }
      processSummary.textContent = "";
      var setRequests = data && Array.isArray(data.set_requests) ? data.set_requests : [];
      if (setRequests.length) {
        var setHeading = document.createElement("p"); setHeading.className = "member-process-set-heading"; setHeading.textContent = "Setagem solicitada";
        processSummary.appendChild(setHeading);
        setRequests.slice(0, 3).forEach(function (item) {
          var setRow = document.createElement("div"); setRow.className = "member-process-set-row";
          var setTitle = document.createElement("strong"); setTitle.textContent = item.in_game_username || "Processo de entrada";
          var setStatus = document.createElement("span"); setStatus.className = "status-tag status-tag--" + (item.status === "approved" ? "ready" : item.status === "rejected" ? "error" : "pending"); setStatus.textContent = item.status === "approved" ? "Aprovada" : item.status === "rejected" ? "Reprovada" : "Pendente";
          setRow.append(setTitle, setStatus); processSummary.appendChild(setRow);
        });
      }
      if (assignments.length || setRequests.length) {
        var next = document.createElement("p");
        next.className = "member-block-state";
        next.textContent = assignments.length ? (assignments.some(function (item) { return item.status === "submitted"; }) ? "Confira o resultado e as respostas abrindo uma atribuição." : "Abra a prova pelo link enviado pela Gerência quando estiver pronta.") : "Acompanhe a decisão da equipe nesta mesma página.";
        processSummary.appendChild(next);
      }
    }

    function copyValue(value, statusNode) {
      var copyPromise = typeof site.copyText === "function"
        ? site.copyText(String(value))
        : navigator.clipboard && navigator.clipboard.writeText
          ? navigator.clipboard.writeText(String(value)).then(function () { return true; })
          : Promise.reject(new Error("clipboard unavailable"));
      copyPromise.then(function () { if (statusNode) statusNode.textContent = "ID copiado"; }).catch(function () { if (statusNode) statusNode.textContent = "Não foi possível copiar"; });
    }

    function renderManagerReview(container, payload) {
      if (!container) return;
      renderReviewItems(container, payload && payload.review);
    }

    function loadManagerReview(assignment, container) {
      if (!assignment || assignment.status !== "submitted" || !container || container.dataset.loaded === "true" || container.dataset.loading === "true") return;
      container.dataset.loading = "true";
      container.setAttribute("aria-busy", "true");
      container.setAttribute("aria-live", "polite");
       var loading = document.createElement("div");
       loading.className = "member-block-state member-block-state--loading";
       loading.innerHTML = '<span class="peace-spinner" aria-hidden="true"></span><span>Consultando respostas do candidato…</span>';
      container.appendChild(loading);
      request("/api/exams/assignments/" + encodeURIComponent(assignment.id) + "/review")
        .then(function (payload) {
          if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "A revisão ainda não está disponível.");
          renderManagerReview(container, payload);
          container.dataset.loaded = "true";
        })
        .catch(function (error) {
          container.setAttribute("aria-busy", "false");
          container.textContent = "";
          container.appendChild(memberState(error.message || "Não consegui carregar as respostas agora.", "error"));
        })
        .finally(function () {
          delete container.dataset.loading;
        });
    }

    function renderManagerAssignments(assignments) {
      if (!managerList) return;
      managerList.textContent = "";
      if (managerCount) managerCount.textContent = assignments.length + (assignments.length === 1 ? " registro" : " registros");
      if (!assignments.length) {
        managerList.appendChild(memberState("Nenhuma atribuição criada por esta conta ainda.", "empty"));
        return;
      }
      assignments.forEach(function (assignment) {
        var details = document.createElement("details");
        details.className = "member-assignment-disclosure manager-assignment-disclosure";
        var summary = document.createElement("summary");
        var candidate = document.createElement("span");
        var title = document.createElement("strong");
        title.textContent = (assignment.exam_type_label || "Prova") + " · #" + assignment.id;
        var subtitle = document.createElement("small");
        subtitle.textContent = statusLabel(assignment) + " · " + (assignment.deadline_at ? "termina " + date(assignment.deadline_at) : "tempo começa ao iniciar");
        candidate.appendChild(title);
        candidate.appendChild(subtitle);
        var arrow = disclosureArrow();
        summary.appendChild(candidate);
        summary.appendChild(arrow);
        var content = document.createElement("div");
        content.className = "member-assignment-disclosure-content";
        var identity = document.createElement("div");
        identity.className = "manager-candidate";
        var avatar = document.createElement("img");
        avatar.className = "manager-candidate-avatar";
        avatar.width = 48;
        avatar.height = 48;
        avatar.loading = "lazy";
        avatar.decoding = "async";
        avatar.alt = "Avatar de @" + (assignment.candidate_username || "candidato");
        avatar.src = assignment.candidate_avatar_url || "/assets/peace-bird.png";
        avatar.addEventListener("error", function () {
          avatar.onerror = null;
          avatar.src = "/assets/peace-bird.png";
        });
        var identityCopy = document.createElement("div");
        var candidateId = String(assignment.candidate_discord_user_id || "").trim();
        var profileLink = candidateId ? document.createElement("a") : document.createElement("span");
        if (candidateId) {
          profileLink.href = assignment.candidate_profile_url || ("https://discord.com/users/" + encodeURIComponent(candidateId));
          profileLink.target = "_blank";
          profileLink.rel = "noopener noreferrer";
          profileLink.setAttribute("aria-label", "Abrir perfil Discord de @" + (assignment.candidate_username || "candidato"));
          profileLink.title = "Abrir perfil Discord em nova guia";
        }
        profileLink.textContent = "@" + (assignment.candidate_username || "candidato");
        identityCopy.appendChild(profileLink);
        var candidateIdNote = document.createElement("small");
        candidateIdNote.className = "manager-candidate-id-note";
        candidateIdNote.textContent = candidateId ? "Identidade confirmada" : "Identidade indisponível";
        identityCopy.appendChild(candidateIdNote);
        identity.appendChild(avatar);
        identity.appendChild(identityCopy);
        content.appendChild(identity);
        var meta = document.createElement("div");
        meta.className = "manager-candidate-meta";
        var scoreScale = assignment.score_scale || 100;
        [["Status", statusLabel(assignment)], ["Nota", assignment.score == null ? "Pendente" : assignment.score + "/" + scoreScale], ["Criada", date(assignment.created_at)]].forEach(function (pair) {
          var cell = document.createElement("div");
          var label = document.createElement("small");
          label.textContent = pair[0];
          var value = document.createElement("strong");
          value.textContent = pair[1];
          cell.appendChild(label);
          cell.appendChild(value);
          meta.appendChild(cell);
        });
        content.appendChild(meta);
        if (assignment.status === "assigned" || assignment.status === "in_progress") {
          var rejectRow = document.createElement("div");
          rejectRow.className = "member-manager-inline-actions";
          var rejectButton = document.createElement("button");
          rejectButton.type = "button";
          rejectButton.className = "button button--danger button--small";
          rejectButton.textContent = "Reprovar candidato";
          rejectButton.addEventListener("click", function () {
            if (!window.confirm("Reprovar esta atribuição? O link deixará de funcionar imediatamente.")) return;
            rejectButton.disabled = true;
            rejectButton.textContent = "Atualizando…";
            request("/api/exams/assignments/" + encodeURIComponent(assignment.id) + "/reject", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" })
              .then(function (payload) {
                if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "Não consegui reprovar esta atribuição.");
                managerAssignments = managerAssignments.map(function (item) { return Number(item.id) === Number(assignment.id) ? payload.assignment : item; });
                refreshVisibleManagerAssignments();
              })
              .catch(function (error) {
                rejectButton.disabled = false;
                rejectButton.textContent = "Reprovar candidato";
                window.alert(error.message || "Não consegui reprovar esta atribuição agora.");
              });
          });
          rejectRow.appendChild(rejectButton);
          content.appendChild(rejectRow);
        }
        if (assignment.status === "submitted") {
          var review = document.createElement("div");
          review.className = "member-review-list";
          content.appendChild(review);
          details.addEventListener("toggle", function () { if (details.open) loadManagerReview(assignment, review); });
        }
        details.appendChild(summary);
        details.appendChild(content);
        managerList.appendChild(details);
      });
    }

    function visibleManagerAssignments() {
      var query = managerSearch ? managerSearch.value.trim().toLowerCase() : "";
      return managerAssignments.filter(function (assignment) {
        var matchesStatus = managerStatusFilter === "all" || String(assignment.status || "") === managerStatusFilter;
        var haystack = [assignment.candidate_username, assignment.candidate_discord_user_id, assignment.exam_type_label, statusLabel(assignment)].join(" ").toLowerCase();
        return matchesStatus && (!query || haystack.indexOf(query) >= 0);
      });
    }

    function refreshVisibleManagerAssignments() {
      renderManagerAssignments(visibleManagerAssignments());
    }

    function stopManagerPolling() {
      if (managerPollingTimer) window.clearTimeout(managerPollingTimer);
      managerPollingTimer = null;
    }

    function scheduleManagerPolling() {
      stopManagerPolling();
      if (currentView !== "manager" || document.hidden) return;
      managerPollingTimer = window.setTimeout(function () {
        managerPollingTimer = null;
        loadManagerAssignments(true);
      }, 15000);
    }

    function loadManagerAssignments(silent) {
      if (!managerList || managerAssignmentsLoading) return;
      managerAssignmentsLoading = true;
      if (!silent) {
        managerList.textContent = "";
         var loading = document.createElement("div");
         loading.className = "member-block-state member-block-state--loading";
         loading.innerHTML = '<span class="peace-spinner" aria-hidden="true"></span><span>Consultando atribuições da Gerência…</span>';
        managerList.appendChild(loading);
      }
      request("/api/exams/assignments")
        .then(function (payload) {
          if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "Não consegui consultar as atribuições.");
          managerAssignments = Array.isArray(payload.assignments) ? payload.assignments : [];
          refreshVisibleManagerAssignments();
        })
        .catch(function (error) {
          managerList.textContent = "";
          if (!silent || !managerList.children.length) managerList.appendChild(memberState(error.message || "Não consegui consultar as atribuições agora.", "error"));
        })
        .finally(function () { managerAssignmentsLoading = false; scheduleManagerPolling(); });
    }

    function closeManagerModal(restoreFocus) {
      if (!managerModal || managerModal.hidden) return;
      managerModal.hidden = true;
      document.body.classList.remove("member-modal-open");
      if (workspace) workspace.removeAttribute("inert");
      if (restoreFocus && managerPreviousFocus && typeof managerPreviousFocus.focus === "function") managerPreviousFocus.focus();
      managerPreviousFocus = null;
    }

    function openManagerModal() {
      if (!managerModal) return;
      managerPreviousFocus = document.activeElement;
      managerModal.hidden = false;
      document.body.classList.add("member-modal-open");
      if (workspace) workspace.setAttribute("inert", "");
      if (managerFormStatus) managerFormStatus.textContent = "";
      if (managerGenerated) managerGenerated.hidden = true;
      if (managerForm) managerForm.reset();
      var duration = managerForm && managerForm.elements.duration_hours;
      if (duration) duration.value = "24";
      var first = managerForm && managerForm.querySelector("input");
      if (first) first.focus();
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
      configureGate("connect", message || "Conecte uma conta Discord com cargo Peace para abrir a área de membros. Se você ainda não tem o cargo, siga para Meu processo.");
    }
    function showConnectedNonMember() {
      configureGate("set", "Discord conectado, mas esta conta ainda não tem cargo Peace. Continue pelo processo público para solicitar a setagem.");
    }
    function showUnavailable() {
      configureGate("retry", "Não foi possível confirmar a conexão com Discord agora. A área continua bloqueada até a verificação terminar; tente novamente em instantes.");
    }
    function showWorkspaceLoading() {
      if (gate) gate.hidden = true;
      if (workspace) { workspace.hidden = false; workspace.setAttribute("aria-busy", "true"); }
      setLoadingStatus("Validando sessão, cargo Peace e processo…");
      // Never reveal a cached authenticated shell before the live process
      // endpoint confirms both the member role and manager capability.
      resetReusableSurface();
      if (skeleton) skeleton.hidden = false;
      if (content) content.hidden = true;
      setConnection("Validando sessão, cargo Peace e processo…", "pending");
    }
    function showWorkspace() {
      if (gate) gate.hidden = true;
      if (workspace) { workspace.hidden = false; workspace.setAttribute("aria-busy", "false"); }
      if (skeleton) skeleton.hidden = true;
      if (content) content.hidden = false;
      setLoadingStatus("");
      markShellReady();
      setSidebarCollapsed(readSidebarCollapsed());
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
          loadClipCount();
        })
        .catch(function (error) {
          if (error && error.status === 401) showDisconnected("Sua sessão Discord expirou. Conecte novamente para continuar.");
          else if (error && error.status === 403) showConnectedNonMember();
          else showUnavailable();
        })
        .finally(function () { loading = false; });
    }

    if (retry) retry.addEventListener("click", load);
    if (sidebarCollapse) sidebarCollapse.addEventListener("click", function () {
      var collapsed = shell && shell.dataset.sidebarCollapsed === "true";
      setSidebarCollapsed(!collapsed);
    });
    if (sidebarToggle) sidebarToggle.addEventListener("click", function () {
      var open = shell && shell.dataset.sidebarOpen === "true";
      setSidebarOpen(!open, true);
    });
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
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stopManagerPolling();
      else if (currentView === "manager") scheduleManagerPolling();
    });
    document.addEventListener("keydown", function (event) {
      var openModal = managerModal && !managerModal.hidden ? managerModal : activeModal && !activeModal.hidden ? activeModal : null;
      if (event.key === "Escape" && openModal) {
        event.preventDefault();
        if (openModal === managerModal) closeManagerModal(true);
        else closeMemberModal(openModal, true);
        return;
      }
      if (event.key === "Tab" && openModal) {
        var modalFocusable = Array.prototype.filter.call(openModal.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex=\"-1\"])") , function (node) {
          return !node.hidden && node.getClientRects().length > 0;
        });
        if (modalFocusable.length) {
          var modalFirst = modalFocusable[0];
          var modalLast = modalFocusable[modalFocusable.length - 1];
          if (event.shiftKey && document.activeElement === modalFirst) {
            event.preventDefault();
            modalLast.focus();
          } else if (!event.shiftKey && document.activeElement === modalLast) {
            event.preventDefault();
            modalFirst.focus();
          }
        }
        return;
      }
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
      if (toolbarAccount && toolbarAccountMenu && !toolbarAccount.contains(event.target)) {
        toolbarAccountMenu.hidden = true;
        if (toolbarAccountTrigger) toolbarAccountTrigger.setAttribute("aria-expanded", "false");
      }
      if (!notificationPanel || notificationPanel.hidden) return;
      if (notificationPanel.contains(event.target) || notificationTrigger.contains(event.target)) return;
      setNotificationsOpen(false, false);
    });
    if (managerOpen) managerOpen.addEventListener("click", openManagerModal);
    if (managerSearch) managerSearch.addEventListener("input", refreshVisibleManagerAssignments);
    managerFilterButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        managerStatusFilter = button.dataset.memberManagerFilter || "all";
        managerFilterButtons.forEach(function (candidate) {
          var selected = candidate === button;
          candidate.classList.toggle("is-active", selected);
          candidate.setAttribute("aria-pressed", String(selected));
        });
        refreshVisibleManagerAssignments();
      });
    });
    if (managerClose) managerClose.addEventListener("click", function () { closeManagerModal(true); });
    if (managerCancel) managerCancel.addEventListener("click", function () { closeManagerModal(true); });
    if (managerModal) managerModal.addEventListener("click", function (event) {
      if (event.target === managerModal) closeManagerModal(true);
    });
    if (managerForm) managerForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!managerForm.checkValidity()) {
        managerForm.reportValidity();
        return;
      }
      var formData = new FormData(managerForm);
      var durationHours = Number(formData.get("duration_hours"));
      if (!Number.isInteger(durationHours) || durationHours < 1 || durationHours > 168) {
        if (managerFormStatus) managerFormStatus.textContent = "Informe entre 1 e 168 horas.";
        return;
      }
      var payload = {
        candidate_discord_user_id: String(formData.get("candidate_discord_user_id") || "").trim(),
        candidate_username: String(formData.get("candidate_username") || "").trim(),
        exam_type: String(formData.get("exam_type") || "theoretical_civil").trim(),
        duration_hours: durationHours
      };
      if (managerFormStatus) {
        managerFormStatus.textContent = "Gerando atribuição…";
        managerFormStatus.dataset.state = "pending";
      }
      if (managerGenerated) managerGenerated.hidden = true;
      site.setButtonBusy(managerSubmit, true, "Gerando…");
      request("/api/exams/assignments", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        if (!response || response.ok !== true || !response.access_url) throw site.friendlyError(response, 200, "Não consegui gerar a atribuição.");
        if (managerGeneratedLink) {
          managerGeneratedLink.href = response.access_url;
          managerGeneratedLink.textContent = response.access_url;
        }
        if (managerGenerated) managerGenerated.hidden = false;
        if (managerFormStatus) {
          managerFormStatus.textContent = "Atribuição criada. Envie este link ao candidato.";
          managerFormStatus.dataset.state = "success";
        }
        managerAssignmentsLoading = false;
        loadManagerAssignments();
      }).catch(function (error) {
        if (managerFormStatus) {
          managerFormStatus.textContent = error.message || "Não consegui gerar a atribuição agora.";
          managerFormStatus.dataset.state = "error";
        }
      }).finally(function () { site.setButtonBusy(managerSubmit, false); });
    });
    if (investigationOpen) investigationOpen.addEventListener("click", function () {
      openMemberModal(investigationModal, investigationForm, investigationFormStatus);
    });
    if (investigationClose) investigationClose.addEventListener("click", function () { closeMemberModal(investigationModal, true); });
    if (investigationCancel) investigationCancel.addEventListener("click", function () { closeMemberModal(investigationModal, true); });
    if (investigationModal) investigationModal.addEventListener("click", function (event) {
      if (event.target === investigationModal) closeMemberModal(investigationModal, true);
    });
    if (investigationForm) investigationForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!investigationForm.checkValidity()) {
        investigationForm.reportValidity();
        return;
      }
      var formData = new FormData(investigationForm);
      var occurredAt = String(formData.get("occurred_at") || "").trim();
      var occurredAtLabel = "";
      if (occurredAt) {
        try { occurredAtLabel = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(occurredAt)); } catch (error) { occurredAtLabel = occurredAt; }
      }
      var reportParts = [
        "Natureza: " + String(formData.get("nature") || "Outra ocorrência").trim(),
        "Data/hora aproximadas: " + (occurredAtLabel || "não informada"),
        "Local ou referência: " + (String(formData.get("location") || "").trim() || "não informado"),
        "Envolvidos ou organizações: " + (String(formData.get("involved") || "").trim() || "não informado"),
        "Relato:\n" + String(formData.get("report") || "").trim()
      ];
      var nextStep = String(formData.get("next_step") || "").trim();
      if (nextStep) reportParts.push("Próximo passo sugerido:\n" + nextStep);
      var payload = {
        title: String(formData.get("title") || "").trim(),
        summary: reportParts.join("\n\n").slice(0, 4000)
      };
      if (investigationFormStatus) {
        investigationFormStatus.textContent = "Registrando caso…";
        investigationFormStatus.dataset.state = "pending";
      }
      site.setButtonBusy(investigationSubmit, true, "Registrando…");
      request("/api/investigations", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        if (!response || response.ok !== true) throw site.friendlyError(response, 201, "Não consegui registrar o caso.");
        if (investigationFormStatus) {
          investigationFormStatus.textContent = "Caso registrado.";
          investigationFormStatus.dataset.state = "success";
        }
        loadInvestigations();
        window.setTimeout(function () { closeMemberModal(investigationModal, true); }, 350);
      }).catch(function (error) {
        if (investigationFormStatus) {
          investigationFormStatus.textContent = error.message || "Não consegui registrar o caso agora.";
          investigationFormStatus.dataset.state = "error";
        }
      }).finally(function () { site.setButtonBusy(investigationSubmit, false); });
    });
    if (investigationList) investigationList.addEventListener("click", function (event) {
      var evidenceButton = event.target.closest ? event.target.closest("[data-member-case-evidence]") : null;
      var approvalButton = event.target.closest ? event.target.closest("[data-member-case-approval]") : null;
      var archiveButton = event.target.closest ? event.target.closest("[data-member-case-archive]") : null;
      var reopenButton = event.target.closest ? event.target.closest("[data-member-case-reopen]") : null;
      if (evidenceButton) {
        selectedInvestigationCaseId = evidenceButton.dataset.caseId || null;
        if (evidenceForm) {
          evidenceForm.reset();
          if (evidenceForm.elements.case_id) evidenceForm.elements.case_id.value = selectedInvestigationCaseId || "";
        }
        openMemberModal(evidenceModal, evidenceForm, evidenceFormStatus);
      } else if (approvalButton) {
        selectedInvestigationCaseId = approvalButton.dataset.caseId || null;
        if (approvalForm) {
          approvalForm.reset();
          if (approvalForm.elements.case_id) approvalForm.elements.case_id.value = selectedInvestigationCaseId || "";
        }
        if (approvalGenerated) approvalGenerated.hidden = true;
        openMemberModal(approvalModal, approvalForm, approvalFormStatus);
      } else if (archiveButton) {
        var archiveCaseId = archiveButton.dataset.caseId || "";
        if (!archiveCaseId || !window.confirm("Concluir este caso? A investigação será arquivada e não poderá ser reaberta por este painel.")) return;
        archiveButton.disabled = true;
        archiveButton.textContent = "Concluindo…";
        request("/api/investigations/" + encodeURIComponent(archiveCaseId), {
          method: "PATCH",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({ status: "archived" })
        }).then(function (response) {
          if (!response || response.ok !== true) throw site.friendlyError(response, 200, "Não consegui concluir o caso.");
          loadInvestigations();
        }).catch(function (error) {
          archiveButton.disabled = false;
          archiveButton.textContent = "Concluir caso";
          window.alert(error.message || "Não consegui concluir o caso agora.");
        });
      } else if (reopenButton) {
        var reopenCaseId = reopenButton.dataset.caseId || "";
        if (!reopenCaseId || !window.confirm("Reabrir este caso para nova análise e aprovação?")) return;
        reopenButton.disabled = true;
        reopenButton.textContent = "Reabrindo…";
        request("/api/investigations/" + encodeURIComponent(reopenCaseId), {
          method: "PATCH",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({ status: "under_review" })
        }).then(function (response) {
          if (!response || response.ok !== true) throw site.friendlyError(response, 200, "Não consegui reabrir o caso.");
          loadInvestigations();
        }).catch(function (error) {
          reopenButton.disabled = false;
          reopenButton.textContent = "Reabrir análise";
          window.alert(error.message || "Não consegui reabrir o caso agora.");
        });
      }
    });
    if (evidenceClose) evidenceClose.addEventListener("click", function () { closeMemberModal(evidenceModal, true); });
    if (evidenceCancel) evidenceCancel.addEventListener("click", function () { closeMemberModal(evidenceModal, true); });
    if (evidenceModal) evidenceModal.addEventListener("click", function (event) {
      if (event.target === evidenceModal) closeMemberModal(evidenceModal, true);
    });
    if (evidenceForm) evidenceForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!evidenceForm.checkValidity()) {
        evidenceForm.reportValidity();
        return;
      }
      var formData = new FormData(evidenceForm);
      var caseId = String(formData.get("case_id") || selectedInvestigationCaseId || "").trim();
      var payload = {
        type: String(formData.get("type") || "reference").trim(),
        classification: String(formData.get("classification") || "reference").trim(),
        title: String(formData.get("title") || "").trim(),
        source_url: String(formData.get("source_url") || "").trim(),
        note: String(formData.get("note") || "").trim()
      };
      if (evidenceFormStatus) {
        evidenceFormStatus.textContent = "Adicionando evidência…";
        evidenceFormStatus.dataset.state = "pending";
      }
      site.setButtonBusy(evidenceSubmit, true, "Adicionando…");
      request("/api/investigations/" + encodeURIComponent(caseId) + "/evidence", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        if (!response || response.ok !== true) throw site.friendlyError(response, 201, "Não consegui adicionar a evidência.");
        if (evidenceFormStatus) {
          evidenceFormStatus.textContent = "Evidência adicionada.";
          evidenceFormStatus.dataset.state = "success";
        }
        loadInvestigations();
        window.setTimeout(function () { closeMemberModal(evidenceModal, true); }, 350);
      }).catch(function (error) {
        if (evidenceFormStatus) {
          evidenceFormStatus.textContent = error.message || "Não consegui adicionar a evidência agora.";
          evidenceFormStatus.dataset.state = "error";
        }
      }).finally(function () { site.setButtonBusy(evidenceSubmit, false); });
    });
    if (approvalClose) approvalClose.addEventListener("click", function () { closeMemberModal(approvalModal, true); });
    if (approvalCancel) approvalCancel.addEventListener("click", function () { closeMemberModal(approvalModal, true); });
    if (approvalModal) approvalModal.addEventListener("click", function (event) {
      if (event.target === approvalModal) closeMemberModal(approvalModal, true);
    });
    if (approvalForm) approvalForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!approvalForm.checkValidity()) {
        approvalForm.reportValidity();
        return;
      }
      var formData = new FormData(approvalForm);
      var caseId = String(formData.get("case_id") || selectedInvestigationCaseId || "").trim();
      var payload = {
        expected_outcome: String(formData.get("expected_outcome") || "").trim(),
        evaluator_discord_user_ids: String(formData.get("evaluator_discord_user_ids") || "").trim()
      };
      if (approvalFormStatus) {
        approvalFormStatus.textContent = "Gerando links privados…";
        approvalFormStatus.dataset.state = "pending";
      }
      if (approvalGenerated) approvalGenerated.hidden = true;
      site.setButtonBusy(approvalSubmit, true, "Gerando…");
      request("/api/investigations/" + encodeURIComponent(caseId) + "/approval-links", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        if (!response || response.ok !== true || !Array.isArray(response.links)) throw site.friendlyError(response, 201, "Não consegui gerar os links privados.");
        if (approvalGenerated) {
          approvalGenerated.textContent = "";
          var heading = document.createElement("strong");
          heading.textContent = "Links gerados — copie e envie individualmente";
          approvalGenerated.appendChild(heading);
          response.links.forEach(function (linkItem, index) {
            var row = document.createElement("div");
            row.className = "member-generated-link-row";
            var link = document.createElement("a");
            link.href = linkItem.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "Avaliador " + (index + 1);
            var copy = document.createElement("button");
            copy.type = "button";
            copy.className = "button button--outline member-generated-link-copy";
            copy.textContent = "Copiar link";
            var copyStatus = document.createElement("span");
            copyStatus.className = "sr-only";
            copyStatus.setAttribute("role", "status");
            copy.addEventListener("click", function () { copyValue(linkItem.url, copyStatus); });
            row.appendChild(link);
            row.appendChild(copy);
            row.appendChild(copyStatus);
            approvalGenerated.appendChild(row);
          });
          approvalGenerated.hidden = false;
        }
        if (approvalFormStatus) {
          approvalFormStatus.textContent = "Links criados. Eles expiram em 7 dias e só abrem para a conta autorizada.";
          approvalFormStatus.dataset.state = "success";
        }
        loadInvestigations();
      }).catch(function (error) {
        if (approvalFormStatus) {
          approvalFormStatus.textContent = error.message || "Não consegui gerar os links agora.";
          approvalFormStatus.dataset.state = "error";
        }
      }).finally(function () { site.setButtonBusy(approvalSubmit, false); });
    });
    noticeOpenButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        openMemberModal(noticeModal, noticeForm, noticeFormStatus);
      });
    });
    scanFilterButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        scanStatusFilter = button.dataset.memberScanFilter || "all";
        scanFilterButtons.forEach(function (candidate) {
          var selected = candidate === button;
          candidate.classList.toggle("is-active", selected);
          candidate.setAttribute("aria-pressed", String(selected));
        });
        renderScanMessages();
      });
    });
    if (scanList) scanList.addEventListener("click", function (event) {
      var button = event.target.closest ? event.target.closest("[data-scan-decision]") : null;
      if (!button || !button.dataset.requestId) return;
      var action = button.dataset.scanDecision;
      if (!window.confirm(action === "approve" ? "Aprovar esta setagem?" : "Reprovar esta setagem?")) return;
      var siblings = button.parentElement ? button.parentElement.querySelectorAll("button") : [];
      siblings.forEach(function (candidate) { candidate.disabled = true; });
      button.textContent = action === "approve" ? "Aprovando…" : "Reprovando…";
      request("/api/scan-only/" + encodeURIComponent(button.dataset.requestId) + "/" + action, {
        method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}"
      }).then(function (payload) {
        if (!payload || payload.ok !== true) throw site.friendlyError(payload, 200, "Não consegui registrar a decisão.");
        loadScanMessages();
      }).catch(function (error) {
        siblings.forEach(function (candidate) { candidate.disabled = false; });
        button.textContent = action === "approve" ? "Aprovar" : "Reprovar";
        window.alert(error.message || "Não consegui registrar a decisão agora.");
      });
    });
    if (noticeAttachment) noticeAttachment.addEventListener("change", function () { readNoticeAttachment(noticeAttachment.files && noticeAttachment.files[0]); });
    if (noticeDropzone) {
      ["dragenter", "dragover"].forEach(function (eventName) {
        noticeDropzone.addEventListener(eventName, function (event) {
          event.preventDefault();
          noticeDropzone.classList.add("is-dragover");
        });
      });
      ["dragleave", "drop"].forEach(function (eventName) {
        noticeDropzone.addEventListener(eventName, function (event) {
          event.preventDefault();
          noticeDropzone.classList.remove("is-dragover");
        });
      });
      noticeDropzone.addEventListener("drop", function (event) {
        var files = event.dataTransfer && event.dataTransfer.files;
        readNoticeAttachment(files && files[0]);
      });
    }
    if (noticeClose) noticeClose.addEventListener("click", function () { closeMemberModal(noticeModal, true); });
    if (noticeCancel) noticeCancel.addEventListener("click", function () { closeMemberModal(noticeModal, true); });
    if (noticeModal) noticeModal.addEventListener("click", function (event) {
      if (event.target === noticeModal) closeMemberModal(noticeModal, true);
    });
    if (noticeForm) noticeForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!noticeForm.checkValidity()) {
        noticeForm.reportValidity();
        return;
      }
      var formData = new FormData(noticeForm);
      var payload = {
        title: String(formData.get("title") || "").trim(),
        body: String(formData.get("body") || "").trim(),
        image_url: String(formData.get("image_url") || "").trim()
      };
      if (noticeAttachmentData) {
        payload.attachment_data = noticeAttachmentData.data;
        payload.attachment_name = noticeAttachmentData.name;
        payload.attachment_type = noticeAttachmentData.type;
      }
      if (noticeFormStatus) {
        noticeFormStatus.textContent = "Publicando aviso…";
        noticeFormStatus.dataset.state = "pending";
      }
      site.setButtonBusy(noticeSubmit, true, "Publicando…");
      request("/api/notices", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        if (!response || response.ok !== true) throw site.friendlyError(response, 201, "Não consegui publicar o aviso.");
        if (noticeFormStatus) {
          noticeFormStatus.textContent = "Aviso publicado no mural público.";
          noticeFormStatus.dataset.state = "success";
        }
        notificationsLoaded = false;
        loadNotifications();
        window.setTimeout(function () { closeMemberModal(noticeModal, true); }, 350);
      }).catch(function (error) {
        if (noticeFormStatus) {
          noticeFormStatus.textContent = error.message || "Não consegui publicar o aviso agora.";
          noticeFormStatus.dataset.state = "error";
        }
      }).finally(function () { site.setButtonBusy(noticeSubmit, false); });
    });
    if (partnerOpen) partnerOpen.addEventListener("click", function () {
      editingPartnerId = null;
      if (partnerModalTitle) partnerModalTitle.textContent = "Adicionar parceiro";
      if (partnerSubmit) { var label = partnerSubmit.querySelector("[data-button-label]"); if (label) label.textContent = "Adicionar parceiro"; }
      openMemberModal(partnerModal, partnerForm, partnerFormStatus);
    });
    if (partnerClose) partnerClose.addEventListener("click", function () { closeMemberModal(partnerModal, true); });
    if (partnerCancel) partnerCancel.addEventListener("click", function () { closeMemberModal(partnerModal, true); });
    if (partnerModal) partnerModal.addEventListener("click", function (event) {
      if (event.target === partnerModal) closeMemberModal(partnerModal, true);
    });
    if (partnerForm) partnerForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!partnerForm.checkValidity()) {
        partnerForm.reportValidity();
        return;
      }
      var formData = new FormData(partnerForm);
      var payload = {
        title: String(formData.get("title") || "").trim(),
        description: String(formData.get("description") || "").trim(),
        url: String(formData.get("url") || "").trim(),
        image_url: String(formData.get("image_url") || "").trim()
      };
      if (partnerFormStatus) {
        partnerFormStatus.textContent = "Salvando parceria…";
        partnerFormStatus.dataset.state = "pending";
      }
      site.setButtonBusy(partnerSubmit, true, "Salvando…");
      request(editingPartnerId ? "/api/partners/" + encodeURIComponent(editingPartnerId) : "/api/partners", {
        method: editingPartnerId ? "PATCH" : "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (response) {
        if (!response || response.ok !== true) throw site.friendlyError(response, 201, "Não consegui salvar a parceria.");
        if (partnerFormStatus) {
          partnerFormStatus.textContent = editingPartnerId ? "Parceria atualizada." : "Parceria publicada.";
          partnerFormStatus.dataset.state = "success";
        }
        request("/api/partners").then(function (fresh) {
          var merged = Object.assign({}, currentProcess || {}, fresh);
          currentProcess = merged;
          renderPartners(merged);
        }).catch(function () {});
        window.setTimeout(function () { closeMemberModal(partnerModal, true); }, 350);
      }).catch(function (error) {
        if (partnerFormStatus) {
          partnerFormStatus.textContent = error.message || "Não consegui salvar a parceria agora.";
          partnerFormStatus.dataset.state = "error";
        }
      }).finally(function () { site.setButtonBusy(partnerSubmit, false); editingPartnerId = null; });
    });
    if (partnerList) partnerList.addEventListener("click", function (event) {
      var button = event.target.closest ? event.target.closest("[data-member-partner-edit]") : null;
      if (!button || !partnerForm) return;
      var item = partnerItems.find(function (candidate) { return String(candidate.id) === String(button.dataset.memberPartnerEdit); });
      if (!item) return;
      editingPartnerId = item.id;
      openMemberModal(partnerModal, partnerForm, partnerFormStatus);
      partnerForm.reset();
      ["title", "description", "url", "image_url"].forEach(function (name) {
        if (partnerForm.elements[name]) partnerForm.elements[name].value = item[name] || "";
      });
      if (partnerModalTitle) partnerModalTitle.textContent = "Editar parceria";
      if (partnerSubmit) {
        var label = partnerSubmit.querySelector("[data-button-label]");
        if (label) label.textContent = "Salvar alterações";
      }
    });
    if (toolbarRefresh) toolbarRefresh.addEventListener("click", function () {
      if (toolbarRefresh.disabled) return;
      toolbarRefresh.disabled = true;
      toolbarRefresh.setAttribute("aria-busy", "true");
      window.location.reload();
    });
    if (window.matchMedia) {
      var sidebarMedia = window.matchMedia("(max-width: 900px)");
      var syncSidebarMode = function () {
        if (sidebarMedia.matches) {
          var focusInsideSidebar = sidebar && sidebar.contains(document.activeElement);
          setSidebarOpen(false, focusInsideSidebar);
        } else {
          setSidebarCollapsed(readSidebarCollapsed());
          setSidebarOpen(true, false);
        }
      };
      if (sidebarMedia.addEventListener) sidebarMedia.addEventListener("change", syncSidebarMode);
      else if (sidebarMedia.addListener) sidebarMedia.addListener(syncSidebarMode);
    }
    window.addEventListener("peace:clips-loaded", function (event) {
      var detail = event && event.detail ? event.detail : {};
      if (detail.count != null) setNavCount("clips", detail.count);
    });
    if (logout) logout.addEventListener("click", function () {
      if (!window.confirm("Sair da conta Discord e fechar a área de membros?")) return;
      clearShellReady();
      logout.disabled = true;
      if (logoutStatus) logoutStatus.textContent = "Saindo da conta…";
      request("/api/auth/discord/logout", { method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}" })
        .then(function () { window.location.replace("/acessar/?status=logged-out"); })
        .catch(function () {
          logout.disabled = false;
          if (logoutStatus) logoutStatus.textContent = "Não foi possível sair agora. Tente novamente.";
        });
    });
    function logoutFromToolbar() {
      if (logout) logout.click();
    }
    if (toolbarAccountTrigger) toolbarAccountTrigger.addEventListener("click", function () {
      var open = toolbarAccountMenu && !toolbarAccountMenu.hidden;
      if (toolbarAccountMenu) toolbarAccountMenu.hidden = open;
      toolbarAccountTrigger.setAttribute("aria-expanded", String(!open));
      if (!open && toolbarAccountMenu) {
        var first = toolbarAccountMenu.querySelector("a, button");
        if (first) first.focus();
      }
    });
    if (toolbarAccountLogout) toolbarAccountLogout.addEventListener("click", logoutFromToolbar);
    var toolbarProfile = workspace && workspace.querySelector("[data-member-toolbar-profile]");
    if (toolbarProfile) toolbarProfile.addEventListener("click", function () {
      if (toolbarAccountMenu) toolbarAccountMenu.hidden = true;
      if (toolbarAccountTrigger) toolbarAccountTrigger.setAttribute("aria-expanded", "false");
      setMemberView("overview", false, true);
    });
    load();
  }

  site.initMemberArea = initMemberArea;
})(window);
