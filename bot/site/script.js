(function () {
  "use strict";

  var body = document.body;
  var header = document.querySelector(".site-header");
  var menuButton = document.querySelector(".menu-toggle");
  var navigation = document.querySelector("#site-nav");
  var revealItems = Array.prototype.slice.call(document.querySelectorAll("[data-reveal]"));
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
