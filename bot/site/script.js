(function () {
  "use strict";

  var body = document.body;
  var header = document.querySelector(".site-header");
  var menuButton = document.querySelector(".menu-toggle");
  var navigation = document.querySelector("#site-nav");
  var revealItems = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var mobileNavigation = window.matchMedia("(max-width: 760px)");

  document.documentElement.classList.add("js-ready");

  function syncNavigationInteraction(isOpen) {
    if (!navigation) return;
    var shouldDisable = mobileNavigation.matches && !isOpen;
    navigation.inert = shouldDisable;
    navigation.setAttribute("aria-hidden", String(shouldDisable));
  }

  function closeMenu(restoreFocus) {
    if (!header || !menuButton) return;
    header.classList.remove("menu-open");
    menuButton.setAttribute("aria-expanded", "false");
    syncNavigationInteraction(false);
    if (restoreFocus) menuButton.focus();
  }

  if (menuButton && navigation && header) {
    syncNavigationInteraction(false);

    menuButton.addEventListener("click", function () {
      var isOpen = header.classList.toggle("menu-open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
      syncNavigationInteraction(isOpen);
    });

    navigation.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        closeMenu(false);
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && header.classList.contains("menu-open")) closeMenu(true);
    });

    document.addEventListener("click", function (event) {
      if (header.classList.contains("menu-open") && !header.contains(event.target)) {
        closeMenu(true);
      }
    });

    mobileNavigation.addEventListener("change", function () {
      closeMenu(false);
    });
  }

  function reveal(element) {
    element.classList.add("is-visible");
  }

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach(reveal);
  } else {
    var observer = new IntersectionObserver(function (entries, currentObserver) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        reveal(entry.target);
        currentObserver.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });

    revealItems.forEach(function (element) {
      observer.observe(element);
    });
  }

  function setServiceStatus(state, label) {
    var status = document.querySelector("[data-service-status]");
    var statusLabel = status && status.querySelector("[data-service-status-label]");
    if (!status || !statusLabel) return;
    status.dataset.state = state;
    statusLabel.textContent = label;
  }

  function refreshServiceStatus() {
    if (body.dataset.page !== "home" || !window.fetch) return;

    var localPreview = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";

    window.fetch("/api/status", {
      headers: { Accept: "application/json" },
      cache: "no-store"
    }).then(function (response) {
      if (!response.ok) throw new Error("status unavailable");
      return response.json();
    }).then(function (payload) {
      var connected = Boolean(
        payload &&
        payload.discord &&
        payload.discord.connected === true &&
        payload.status === "ok"
      );
      setServiceStatus(
        connected ? "online" : "checking",
        connected ? "Peace Tools conectado" : "Peace Tools iniciando"
      );
    }).catch(function () {
      setServiceStatus(
        localPreview ? "preview" : "offline",
        localPreview ? "Prévia local · API não conectada" : "Peace Tools indisponível no momento"
      );
    });
  }

  refreshServiceStatus();

  function setMemberTab(name, moveFocus) {
    var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-member-tab]"));
    var panels = Array.prototype.slice.call(document.querySelectorAll("[data-member-panel]"));
    if (!tabs.length || !panels.length) return;

    tabs.forEach(function (tab) {
      var active = tab.dataset.memberTab === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && moveFocus) tab.focus();
    });

    panels.forEach(function (panel) {
      var active = panel.dataset.memberPanel === name;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    });
  }

  function initMemberArea() {
    if (body.dataset.page !== "member") return;

    var gate = document.querySelector("[data-member-gate]");
    var preview = document.querySelector("[data-member-preview]");
    var previewOpeners = document.querySelectorAll("[data-preview-toggle]");
    var previewCloser = document.querySelector("[data-preview-close]");
    var urlPreview = new URLSearchParams(window.location.search).get("preview") === "member";
    var lastPreviewOpener = null;

    function openPreview(event) {
      if (!preview) return;
      lastPreviewOpener = event && event.currentTarget ? event.currentTarget : lastPreviewOpener;
      preview.hidden = false;
      preview.setAttribute("data-preview-state", "open");
      if (gate) gate.setAttribute("data-preview-state", "open");
      window.setTimeout(function () {
        var heading = document.querySelector("#preview-title");
        if (heading) heading.focus({ preventScroll: true });
      }, 0);
    }

    function closePreview() {
      if (!preview) return;
      preview.hidden = true;
      preview.removeAttribute("data-preview-state");
      if (gate) gate.removeAttribute("data-preview-state");
      if (lastPreviewOpener) {
        lastPreviewOpener.focus();
        lastPreviewOpener = null;
      }
    }

    previewOpeners.forEach(function (opener) {
      opener.addEventListener("click", openPreview);
    });

    if (previewCloser) previewCloser.addEventListener("click", closePreview);
    if (urlPreview) openPreview();

    document.querySelectorAll("[data-member-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        setMemberTab(tab.dataset.memberTab, false);
      });

      tab.addEventListener("keydown", function (event) {
        var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-member-tab]"));
        var index = tabs.indexOf(tab);
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        var nextIndex = event.key === "ArrowRight" ? index + 1 : index - 1;
        if (nextIndex < 0) nextIndex = tabs.length - 1;
        if (nextIndex >= tabs.length) nextIndex = 0;
        setMemberTab(tabs[nextIndex].dataset.memberTab, true);
      });
    });
  }

  initMemberArea();
})();
