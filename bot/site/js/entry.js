(function (global) {
  "use strict";

  var site = global.PeaceSite;
  if (!site || site.body.dataset.page !== "entry") return;

  site.getDiscordSession().then(function (session) {
    if (!session) return;
    var server = session.server || {};
    window.location.replace(server.is_peace_member === true ? "/area/" : "/candidatura/");
  });
})(window);
