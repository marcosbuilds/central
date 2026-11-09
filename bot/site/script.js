(function () {
  "use strict";

  var body = document.body;
  var header = document.querySelector(".site-header");
  var menuButton = document.querySelector(".menu-toggle");
  var navigation = document.querySelector("#site-nav");
  var revealItems = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var backendStatus = document.querySelector("[data-backend-status]");
  var backendStatusLabel = backendStatus && backendStatus.querySelector("[data-backend-status-label]");
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setBackendStatus(state, label) {
    if (!backendStatus || !backendStatusLabel) return;
    backendStatus.dataset.state = state;
    backendStatusLabel.textContent = label;
  }

  function refreshBackendStatus() {
    if (!backendStatus || !backendStatusLabel || !window.fetch) return;

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
      setBackendStatus(
        connected ? "online" : "checking",
        connected ? "Peace Tools online" : "Sincronizando Peace Tools..."
      );
    }).catch(function () {
      setBackendStatus("offline", "Peace Tools indisponível no momento");
    });
  }

  refreshBackendStatus();

  function closeMenu() {
    if (!header || !menuButton) return;
    header.classList.remove("menu-open");
    menuButton.setAttribute("aria-expanded", "false");
  }

  if (menuButton && navigation && header) {
    menuButton.addEventListener("click", function () {
      var isOpen = header.classList.toggle("menu-open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
    });

    navigation.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeMenu();
    });

    document.addEventListener("click", function (event) {
      if (header.classList.contains("menu-open") && !header.contains(event.target)) {
        closeMenu();
      }
    });
  }

  function reveal(element, delay) {
    if (reducedMotion) {
      element.classList.add("is-visible");
      return;
    }

    if (window.gsap) {
      window.gsap.to(element, {
        autoAlpha: 1,
        y: 0,
        filter: "blur(0px)",
        duration: 0.85,
        delay: delay || 0,
        ease: "power3.out",
        overwrite: "auto"
      });
      return;
    }

    element.classList.add("is-visible");
  }

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach(function (element) {
      reveal(element, 0);
    });
    return;
  }

  var observer = new IntersectionObserver(function (entries, currentObserver) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var index = revealItems.indexOf(entry.target);
      reveal(entry.target, index > -1 ? Math.min(index * 0.035, 0.28) : 0);
      currentObserver.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });

  revealItems.forEach(function (element) {
    observer.observe(element);
  });
})();
