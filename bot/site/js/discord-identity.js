(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site) return;

  var identityCounter = 0;
  var localSession = null;

  function text(node, value) {
    if (node) node.textContent = value == null ? "" : String(value);
  }

  function returnTo() {
    var value = window.location.pathname + window.location.search + window.location.hash;
    return value.length <= 220 && value.charAt(0) === "/" && value.indexOf("//") !== 0 ? value : "/meu-processo/";
  }

  function currentName(session) {
    var identity = session && session.identity ? session.identity : {};
    return identity.global_name || identity.display_name || identity.username || "Discord";
  }

  function username(session) {
    var identity = session && session.identity ? session.identity : {};
    return identity.username ? "@" + identity.username : currentName(session);
  }

  function initials(session) {
    var value = currentName(session).replace(/^@/, "").trim();
    var parts = value.split(/\s+/).filter(Boolean);
    return (parts.length > 1 ? parts[0].charAt(0) + parts[parts.length - 1].charAt(0) : value.slice(0, 2)).toUpperCase() || "D";
  }

  function createElement(tag, className, content) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (content != null) node.textContent = content;
    return node;
  }

  function headerHost(header) {
    if (!header) return null;
    var host = header.querySelector(".discord-identity-host");
    if (host) return host;

    var actions = header.querySelector(".header-actions, .flow-header-actions, .member-header-actions");
    if (!actions) {
      var directCta = Array.prototype.slice.call(header.children).find(function (child) {
        return child.classList && child.classList.contains("flow-header-cta");
      });
      if (directCta) {
        actions = createElement("div", "flow-header-actions");
        directCta.replaceWith(actions);
        actions.appendChild(directCta);
      } else {
        var directLogout = Array.prototype.slice.call(header.children).find(function (child) {
          return child.hasAttribute && child.hasAttribute("data-manager-logout");
        });
        actions = createElement("div", "flow-header-actions");
        if (directLogout) {
          directLogout.replaceWith(actions);
          actions.appendChild(directLogout);
        }
        else header.appendChild(actions);
      }
    }

    Array.prototype.slice.call(actions.children).forEach(function (child) {
      // Keep contextual navigation such as "Acessar", "Entrar para Peace"
      // and "Site público". Only remove controls that this shared identity
      // component replaces, so a page does not lose its next action.
      var replacesIdentity = child.hasAttribute("data-discord-connect")
        || child.hasAttribute("data-manager-connect")
        || child.hasAttribute("data-member-discord-connect")
        || child.classList.contains("member-header-discord");
      if (replacesIdentity) child.remove();
    });
    host = createElement("div", "discord-identity-host");
    actions.appendChild(host);
    return host;
  }

  function allHeaderHosts() {
    return Array.prototype.slice.call(document.querySelectorAll(".site-header, .flow-header, .member-header"))
      .map(headerHost)
      .filter(Boolean);
  }

  function connectLink(host) {
    var link = createElement("a", "button button--outline flow-header-cta discord-connect-action");
    link.href = "/api/auth/discord/start?return_to=" + encodeURIComponent(returnTo());
    link.setAttribute("data-discord-connect", "");
    link.setAttribute("aria-label", "Conectar Discord");
    var icon = document.createElement("img");
    icon.className = "discord-icon discord-identity-icon";
    icon.src = "/assets/discord.svg";
    icon.alt = "";
    icon.setAttribute("aria-hidden", "true");
    icon.width = 20;
    icon.height = 16;
    link.appendChild(icon);
    link.appendChild(createElement("span", "discord-connect-copy", "Conectar Discord"));
    link.appendChild(createElement("span", "button-icon", "↗"));
    if (host.classList.contains("member-header-actions")) link.className = "button button--outline member-header-discord discord-connect-action";
    host.appendChild(link);
    return link;
  }

  function setConnectionState(state) {
    document.body.dataset.discordState = state;
    var controls = document.querySelectorAll("[data-discord-connect], [data-manager-connect], [data-login-discord], [data-member-discord-connect]");
    controls.forEach(function (node) {
      if (node.closest(".discord-identity-host")) return;
      if (state === "loading" || state === "connected") node.hidden = true;
      else node.hidden = false;
    });
  }

  function renderLoading(host) {
    host.textContent = "";
    host.setAttribute("aria-busy", "true");
    var loading = createElement("span", "discord-identity-loading");
    loading.setAttribute("role", "status");
    loading.setAttribute("aria-live", "polite");
    loading.appendChild(createElement("span", "discord-identity-loading-avatar"));
    loading.appendChild(createElement("span", "discord-identity-loading-copy", "Validando Discord…"));
    host.appendChild(loading);
  }

  function menuLink(menu, label, href) {
    var link = createElement("a", "discord-identity-menu-link", label);
    link.href = href;
    link.setAttribute("role", "menuitem");
    menu.appendChild(link);
  }

  function renderConnected(host, session) {
    host.textContent = "";
    host.removeAttribute("aria-busy");
    var wrapper = createElement("div", "discord-identity");
    var id = "peace-discord-menu-" + (++identityCounter);
    var trigger = createElement("button", "discord-identity-trigger");
    trigger.type = "button";
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-controls", id);
    trigger.setAttribute("aria-haspopup", "menu");
    var name = createElement("span", "discord-identity-name", username(session));
    var avatar = document.createElement("img");
    avatar.className = "discord-identity-avatar";
    avatar.width = 32;
    avatar.height = 32;
    avatar.alt = "Avatar de " + username(session);
    var fallback = createElement("span", "discord-identity-fallback", initials(session));
    fallback.hidden = true;
    function showFallback() {
      avatar.hidden = true;
      fallback.hidden = false;
    }
    avatar.addEventListener("error", showFallback);
    if (session.identity && session.identity.avatar_url) {
      avatar.src = session.identity.avatar_url;
    } else {
      showFallback();
    }
    var arrow = createElement("span", "discord-identity-arrow", "⌄");
    trigger.appendChild(name);
    trigger.appendChild(avatar);
    trigger.appendChild(fallback);
    trigger.appendChild(arrow);

    var menu = createElement("div", "discord-identity-menu");
    menu.id = id;
    menu.setAttribute("role", "menu");
    menu.hidden = true;
    var menuHeading = createElement("div", "discord-identity-menu-heading");
    text(menuHeading, "Conta conectada");
    var menuIdentity = createElement("strong", "discord-identity-menu-user", username(session));
    menuHeading.appendChild(menuIdentity);
    menu.appendChild(menuHeading);
    menuLink(menu, "Estudos", "/estudos/");
    menuLink(menu, "Meu processo", "/meu-processo/");

    var server = session.server || {};
    if (server.is_peace_member === true) menuLink(menu, "Painel Peace", "/area/");
    else if (server.state === "member" || server.state === "not_member") menuLink(menu, "Solicitar setagem", "/entrar/");
    else menuLink(menu, "Verificar status", "/meu-processo/");
    if (server.is_manager === true) menuLink(menu, "Gerenciar provas", "/gerencia/provas/");
    menuLink(menu, "Entrar no Discord", "/discord");
    var logout = createElement("button", "discord-identity-menu-logout", "Sair");
    logout.type = "button";
    logout.setAttribute("role", "menuitem");
    menu.appendChild(logout);

    function close() {
      trigger.setAttribute("aria-expanded", "false");
      menu.hidden = true;
      wrapper.classList.remove("is-open");
    }
    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      var open = menu.hidden;
      menu.hidden = !open;
      trigger.setAttribute("aria-expanded", String(open));
      wrapper.classList.toggle("is-open", open);
      if (open) {
        var firstItem = menu.querySelector('[role="menuitem"]');
        if (firstItem) firstItem.focus();
      }
    });
    menu.addEventListener("keydown", function (event) {
      var items = Array.prototype.slice.call(menu.querySelectorAll('[role="menuitem"]'));
      var currentItem = document.activeElement;
      var currentIndex = items.indexOf(currentItem);
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        trigger.focus();
        return;
      }
      if (!items.length || !["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      var nextIndex = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (currentIndex + (event.key === "ArrowUp" ? -1 : 1) + items.length) % items.length;
      items[nextIndex].focus();
    });
    menu.addEventListener("click", function (event) {
      if (event.target.closest && event.target.closest("a")) close();
    });
    logout.addEventListener("click", function () {
      logout.disabled = true;
      site.attemptEndpoint("/api/auth/discord/logout", {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: "{}"
      }, 10000).then(function () {
        window.location.reload();
      }).catch(function () {
        logout.disabled = false;
      });
    });
    wrapper.appendChild(trigger);
    wrapper.appendChild(menu);
    host.appendChild(wrapper);
    setConnectionState("connected");
    document.body.dataset.discordConnected = "true";
    document.body.dataset.discordId = session.identity && session.identity.discord_id ? session.identity.discord_id : "";
    document.body.dataset.peaceMember = server.is_peace_member === true ? "true" : "false";
    document.body.dataset.manager = server.is_manager === true ? "true" : "false";
  }

  function renderDisconnected(host) {
    host.textContent = "";
    host.removeAttribute("aria-busy");
    connectLink(host);
    setConnectionState("disconnected");
    document.body.dataset.discordConnected = "false";
    document.body.dataset.discordId = "";
    document.body.dataset.peaceMember = "false";
    document.body.dataset.manager = "false";
  }

  function hideConnectedDuplicates(connected, state) {
    document.querySelectorAll("[data-discord-connect], [data-manager-connect], [data-login-discord], [data-member-discord-connect]").forEach(function (node) {
      if (node.closest(".discord-identity-host")) return;
      node.hidden = connected || state === "loading";
    });
  }

  function render(session) {
    localSession = session;
    var hosts = allHeaderHosts();
    hosts.forEach(function (host) {
      if (session) renderConnected(host, session);
      else renderDisconnected(host);
    });
    hideConnectedDuplicates(Boolean(session), document.body.dataset.discordState);
  }

  function renderPending() {
    setConnectionState("loading");
    document.body.dataset.discordConnected = "pending";
    document.body.dataset.peaceMember = "pending";
    document.body.dataset.manager = "pending";
    allHeaderHosts().forEach(renderLoading);
    hideConnectedDuplicates(false, "loading");
  }

  document.addEventListener("click", function (event) {
    if (event.target.closest && event.target.closest(".discord-identity")) return;
    document.querySelectorAll(".discord-identity.is-open").forEach(function (wrapper) {
      wrapper.classList.remove("is-open");
      var trigger = wrapper.querySelector(".discord-identity-trigger");
      var menu = wrapper.querySelector(".discord-identity-menu");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
      if (menu) menu.hidden = true;
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    document.querySelectorAll(".discord-identity.is-open").forEach(function (wrapper) {
      wrapper.classList.remove("is-open");
      var trigger = wrapper.querySelector(".discord-identity-trigger");
      var menu = wrapper.querySelector(".discord-identity-menu");
      if (trigger) { trigger.setAttribute("aria-expanded", "false"); trigger.focus(); }
      if (menu) menu.hidden = true;
    });
  });

  // Keep every Discord action in a non-interactive skeleton until the
  // HttpOnly session and the live guild profile have been resolved. Showing a
  // second "Conectar" action during this window makes an already-connected
  // person restart OAuth unnecessarily.
  renderPending();

  function requestDiscordSession() {
    renderPending();
    site.discordSessionError = null;
    return site.attemptEndpoint("/api/auth/discord/session", {
      headers: { Accept: "application/json" }
    }, 9000).then(function (response) {
      return response.json();
    }).then(function (payload) {
      render(payload && payload.ok ? payload : null);
      return payload && payload.ok ? payload : null;
    }).catch(function (error) {
      site.discordSessionError = error;
      render(null);
      return null;
    });
  }
  site.discordSessionError = null;
  site.discordSessionPromise = requestDiscordSession();
  site.getDiscordSession = function () { return site.discordSessionPromise; };
  site.refreshDiscordSession = function () {
    site.discordSessionPromise = requestDiscordSession();
    return site.discordSessionPromise;
  };
})(window);
