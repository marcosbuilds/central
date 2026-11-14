/* Stable public entrypoint. Detailed behavior lives in js/. */
(function () {
  "use strict";

  var currentScript = document.currentScript;
  var baseUrl = new URL("./", currentScript ? currentScript.src : document.baseURI);
  var assetVersion = "20261114-02";
  var pageModules = {
    home: ["js/public-media.js"],
    notices: ["js/notices.js"],
    candidatura: ["js/candidature.js"],
    login: ["js/login.js"],
    member: ["js/member-area.js"],
    process: ["js/process.js"],
    exam: ["js/exam.js"],
    manager: ["js/manager-exams.js"],
    reader: ["js/reader.js"]
  };
  var modules = ["js/site-core.js", "js/discord-identity.js"].concat(pageModules[document.body.dataset.page] || []);

  function loadModule(path) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = new URL(path + "?v=" + assetVersion, baseUrl).href;
      script.async = false;
      script.onload = resolve;
      script.onerror = function () { reject(new Error("Peace site module failed: " + path)); };
      document.head.appendChild(script);
    });
  }

  modules.reduce(function (chain, path) {
    return chain.then(function () { return loadModule(path); });
  }, Promise.resolve()).then(function () {
    var site = window.PeaceSite;
    if (!site) return;
    if (site.initPublicMedia) site.initPublicMedia();
    if (site.initMemberArea) site.initMemberArea();
    if (site.initCandidature) site.initCandidature();
    if (site.initLogin) site.initLogin();
  }).catch(function (error) {
    // Keep the public shell visible if a non-critical module is unavailable.
    if (window.console && console.error) console.error(error);
  });
})();
