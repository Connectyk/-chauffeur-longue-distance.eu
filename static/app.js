/* Suivi des appels et des demandes de devis + envoi du formulaire.
   Les événements partent dans dataLayer (Google Tag Manager) et dans gtag (GA4) si présents. */
(function () {
  var SITE = window.SITE || {};
  var body = document.body;

  function suivre(nom, params) {
    var p = Object.assign({
      page_path: location.pathname,
      type_page: body.dataset.type || "",
      trajet: body.dataset.trajet || ""
    }, params || {});
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(Object.assign({ event: nom }, p));
    if (typeof window.gtag === "function") window.gtag("event", nom, p);
  }

  // Consentement aux cookies : Google Analytics n'est chargé qu'après « Accepter » (choix gardé 6 mois)
  var CLE = "consentement_cookies", SIX_MOIS = 182 * 24 * 3600 * 1000;
  function lireChoix() {
    try {
      var c = JSON.parse(localStorage.getItem(CLE) || "null");
      return c && Date.now() - c.date < SIX_MOIS ? c.choix : null;
    } catch (e) { return null; }
  }
  function chargerGA() {
    if (!SITE.ga4 || window.gtag) return;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", SITE.ga4);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(SITE.ga4);
    document.head.appendChild(s);
  }
  var bandeau = document.querySelector(".cookies");
  if (SITE.ga4 && bandeau) {
    var choix = lireChoix();
    if (choix === "accepter") chargerGA();
    else if (!choix) bandeau.hidden = false;
    document.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("[data-cookies]");
      if (!b) return;
      var action = b.dataset.cookies;
      if (action === "ouvrir") { bandeau.hidden = false; return; }
      try { localStorage.setItem(CLE, JSON.stringify({ choix: action, date: Date.now() })); } catch (err) {}
      bandeau.hidden = true;
      if (action === "accepter") chargerGA();
      else if (window.gtag) location.reload();
    });
  }

  // Provenance : page d'entrée, référent, UTM, gclid (conservés pendant la visite)
  var prov = {};
  try {
    prov = JSON.parse(sessionStorage.getItem("provenance") || "null") || { entree: location.pathname, referent: document.referrer || "direct" };
    var q = new URLSearchParams(location.search);
    ["utm_source", "utm_medium", "utm_campaign", "utm_term", "gclid"].forEach(function (k) { if (q.get(k)) prov[k] = q.get(k); });
    sessionStorage.setItem("provenance", JSON.stringify(prov));
  } catch (e) { prov = { entree: location.pathname }; }

  // Clics sur les numéros de téléphone
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest('a[href^="tel:"]');
    if (a) suivre("clic_appel", { emplacement: a.dataset.emplacement || "", entree: prov.entree || "" });
  });

  // Formulaires de devis
  var aujourdhui = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  document.querySelectorAll("form.devis").forEach(function (f) {
    var d = f.querySelector('input[type="date"]');
    if (d) d.min = aujourdhui;
    f.querySelector('[name="page"]').value = location.pathname;
    f.querySelector('[name="provenance"]').value = JSON.stringify(prov);
    var statut = f.querySelector(".form-statut");

    f.addEventListener("submit", function (e) {
      e.preventDefault();
      statut.className = "form-statut";
      if (!f.checkValidity()) {
        var champ = f.querySelector(":invalid");
        statut.textContent = "Complétez le champ « " + champ.closest("label").firstChild.textContent.trim() + " » pour envoyer la demande.";
        statut.classList.add("erreur");
        champ.focus();
        return;
      }
      if (!SITE.endpoint) {
        statut.textContent = "L'envoi en ligne n'est pas encore activé. Appelez le " + SITE.tel + " : le standard répond 24h/24.";
        statut.classList.add("erreur");
        return;
      }
      var bouton = f.querySelector('button[type="submit"]');
      bouton.disabled = true;
      statut.textContent = "Envoi de votre demande…";
      // Formspree répond en JSON ; les autres services (Make…) sont appelés sans lecture de la réponse,
      // pour ne pas afficher d'erreur au visiteur quand la demande est bien partie.
      var formspree = SITE.endpoint.indexOf("formspree.io") !== -1;
      var options = formspree ? { method: "POST", body: new FormData(f), headers: { Accept: "application/json" } }
                              : { method: "POST", body: new FormData(f), mode: "no-cors" };
      fetch(SITE.endpoint, options)
        .then(function (r) {
          if (r.type !== "opaque" && !r.ok) throw new Error();
          suivre("demande_devis", { depart: f.depart.value, destination: f.destination.value, entree: prov.entree || "" });
          f.reset();
          f.querySelector('[name="page"]').value = location.pathname;
          f.querySelector('[name="provenance"]').value = JSON.stringify(prov);
          statut.textContent = "Demande envoyée. Le standard vous rappelle rapidement.";
          statut.classList.add("ok");
        })
        .catch(function () {
          statut.textContent = "La demande n'est pas partie. Réessayez ou appelez le " + SITE.tel + ".";
          statut.classList.add("erreur");
        })
        .finally(function () { bouton.disabled = false; });
    });
  });
})();
