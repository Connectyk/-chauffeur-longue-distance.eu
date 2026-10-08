"""Générateur du site. Usage : python generator/build.py"""
import json, os, shutil, sys, datetime
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "generator"))
import model, content, images  # noqa: E402

cfg = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, cfg["dossier_sortie"])
PFX = ("/" + cfg["prefixe_langue"].strip("/")) if cfg.get("prefixe_langue") else ""
BASE = cfg["url_site"].rstrip("/")
TODAY = datetime.date.today().isoformat()

data = model.charger(os.path.join(ROOT, cfg["fichier_donnees"]), cfg["phases_publiees"])
for e in data["erreurs"]:
    print("ATTENTION :", e)

PH = images.Photos(ROOT, OUT, PFX)
VAN = PH.groupe("groupe")
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=select_autoescape(["html"]))
pages = []  # (url, priorité sitemap)


def u(path):
    return PFX + path


def write(url, html, prio="0.6"):
    path = os.path.join(OUT, url.strip("/"), "index.html") if url.endswith("/") else os.path.join(OUT, url.strip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    pages.append((url, prio))


ORG_ID = BASE + "/#organisation"
ORG = {"@type": "Organization", "@id": ORG_ID, "name": cfg["nom_marque"], "url": BASE + "/",
       "telephone": cfg["telephone_lien"], "email": cfg["email"], "areaServed": ["France", "Suisse", "Belgique"],
       "contactPoint": {"@type": "ContactPoint", "telephone": cfg["telephone_lien"], "contactType": "reservations",
                        "availableLanguage": ["fr"],
                        "hoursAvailable": {"@type": "OpeningHoursSpecification",
                                           "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                           "opens": "00:00", "closes": "23:59"}}}


def schemas(extra=None, crumbs=None, faq=None):
    out = [{"@context": "https://schema.org", **ORG}]
    if cfg.get("adresse_entreprise"):
        out.append({"@context": "https://schema.org", "@type": "LocalBusiness", "name": cfg["nom_marque"],
                    "telephone": cfg["telephone_lien"], "address": cfg["adresse_entreprise"], "parentOrganization": {"@id": ORG_ID}})
    if crumbs:
        out.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": BASE + url} for i, (n, url) in enumerate(crumbs, 1)]})
    if faq:
        out.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    if extra:
        out.append({"@context": "https://schema.org", **extra})
    return out


def render(tpl, url, prio="0.6", **kw):
    kw.setdefault("crumbs", [])
    kw.setdefault("photo", None)
    kw.setdefault("van", None)
    kw.setdefault("base_url", BASE)
    html = env.get_template(tpl).render(cfg=cfg, u=u, url=url, canonical=BASE + url, **kw)
    write(url, html, prio)


# ---------------------------------------------------------------- URLs
lieux = data["lieux"]
trajets = data["trajets"]
pub = [t for t in trajets if t.publie]
for t in pub:
    if t.dep.categorie == "Ville" and t.dest.categorie == "Ville":
        t.url = u(f"/chauffeur-prive/{t.dep.slug}-{t.dest.slug}/")
    else:
        t.url = u(f"/chauffeur-prive/{t.dep.slug}/{t.dest.slug}/")
    t.dep.trajets_depart.append(t)
    t.dest.trajets_arrivee.append(t)
pair = {(t.dep.cle, t.dest.cle): t for t in pub}


def strip(slug, prefix):
    return slug[len(prefix):] if slug.startswith(prefix) else slug


SECTION = {"Ville": ("villes", "Villes"), "Aéroport": ("aeroports", "Aéroports"), "Gare": ("gares", "Gares")}
for l in lieux.values():
    if l.trajets_depart or l.trajets_arrivee:
        rep = SECTION[l.categorie][0]
        l.url = u(f"/{rep}/{strip(strip(l.slug, 'aeroport-'), 'gare-')}/")

villes_avec_page = {l.cle: l for l in lieux.values() if l.categorie == "Ville" and l.url}
hotels_par_ville = defaultdict(list)
for h in data["hotels"]:
    hotels_par_ville[h["ville"]].append(h)
hotel_url = {v: u(f"/hotels/{villes_avec_page[v].slug}/") for v in hotels_par_ville if v in villes_avec_page}
quartiers = [q for q in data["quartiers"] if q["ville"] in villes_avec_page]
for q in quartiers:
    q["url"] = u(f"/quartiers-affaires/{q['slug']}/")
quartiers_par_ville = defaultdict(list)
for q in quartiers:
    quartiers_par_ville[q["ville"]].append(q)


def top(lst, n, exclude=()):
    lst = [t for t in lst if t not in exclude]
    return sorted(lst, key=lambda t: (-t.score, t.distance))[:n]


def infra_de_ville(ville):
    return sorted([l for l in lieux.values() if l.url and l.categorie != "Ville" and l.ville == ville],
                  key=lambda l: (l.categorie, l.titre))


def groupe(lst, attr):
    g = defaultdict(list)
    for t in sorted(lst, key=lambda t: (-t.score, t.distance)):
        g[getattr(t, attr).categorie].append(t)
    ordre = [("Ville", "Villes"), ("Aéroport", "Aéroports"), ("Gare", "Gares")]
    return [(lab, g[k]) for k, lab in ordre if g[k]]


# ---------------------------------------------------------------- Services
VILLES_AFFAIRES = frozenset(q["ville"] for q in data["quartiers"])
COURT = {"chauffeur-vtc-longue-distance": "De porte à porte, d'une ville à l'autre, sans correspondance.",
         "navette-aeroport": "Accueil au hall des arrivées, horaire calé sur votre vol.",
         "transfert-gare": "Le relais du TGV jusqu'à votre destination finale.",
         "voyage-affaires": "Rendez-vous, séminaires, salons, congrès et délégations.",
         "rapatriement": "Vol annulé, grève, train supprimé : on vous ramène par la route.",
         "mise-a-disposition": "Un chauffeur à l'heure ou à la journée.",
         "chauffeur-evenement": "Mariages, galas, festivals et soirées.",
         "chauffeur-tourisme": "Musées, châteaux, vignobles, stations et Riviera.",
         "van-avec-chauffeur": "Jusqu'à 7 places pour les familles et les groupes."}
SVC = {}
for s in content.SERVICES:
    SVC[s["slug"]] = dict(s, url=u(f"/{s['slug']}/"), court=COURT.get(s["slug"], ""))
PHOTO_SVC = {"chauffeur-vtc-longue-distance": "berline-route-soir", "navette-aeroport": "avion-atterrissage",
             "transfert-gare": "gare-bordeaux-saint-jean", "voyage-affaires": "quartier-affaires-soir",
             "rapatriement": "autoroute-nuit", "mise-a-disposition": "chauffeur-portiere",
             "chauffeur-evenement": "main-poignee", "chauffeur-tourisme": "corniche-mer", "van-avec-chauffeur": "van-porte-ouverte"}
EXEMPLES = {"navette-aeroport": lambda t: "Aéroport" in (t.dep.categorie, t.dest.categorie),
            "transfert-gare": lambda t: "Gare" in (t.dep.categorie, t.dest.categorie),
            "voyage-affaires": lambda t: t.dest.ville in VILLES_AFFAIRES and t.dest.categorie == "Ville",
            "rapatriement": lambda t: t.type == "Aéroport → Aéroport",
            "chauffeur-tourisme": lambda t: t.dest.bonus == "Premium",
            "chauffeur-vtc-longue-distance": lambda t: t.segment == "Très longue distance"}


# ---------------------------------------------------------------- Trajets
for t in pub:
    retour = pair.get((t.dest.cle, t.dep.cle))
    c = content.trajet(t, cfg, retour, VILLES_AFFAIRES)
    svc_liens = [SVC[s] for s in content.services_lies(t, c['ctx'])]
    title = f"Chauffeur privé {t.dep.titre} → {t.dest.titre}"
    if len(title) + 9 <= 60:
        title += " | 24h/24"
    meta = (f"Chauffeur privé {t.dep.forme_de} vers {t.dest.forme_vers} : {content.distance_txt(t)}, {t.duree} de route. "
            "Devis personnalisé, standard 24h/24 et 7j/7.")
    crumbs = [("Accueil", u("/")), ("Trajets", u("/chauffeur-prive/")), (f"{t.dep.titre} → {t.dest.titre}", t.url)]
    ville_dest = t.dest.ville
    liens_infra = [l for l in (t.dep, t.dest) if l.url]
    service = {"@type": "Service", "serviceType": "Chauffeur privé", "name": title, "description": meta,
               "provider": {"@id": ORG_ID},
               "areaServed": [{"@type": "Place", "name": t.dep.titre}, {"@type": "Place", "name": t.dest.titre}]}
    render("trajet.html", t.url, "0.8", photo=PH.pour_trajet(t), van=VAN, svc_liens=svc_liens, t=t, c=c, title=title, meta=meta, retour=retour, crumbs=crumbs,
           autres_depuis=top(t.dep.trajets_depart, 8, (t,)), autres_vers=top(t.dest.trajets_arrivee, 6, (t, retour)),
           liens_infra=liens_infra, hotels_url=hotel_url.get(ville_dest), ville_dest=ville_dest,
           quartiers=quartiers_par_ville.get(ville_dest, []),
           schemas=schemas(service, crumbs, c["faq"]), page_type="trajet")

# ---------------------------------------------------------------- Lieux
for l in lieux.values():
    if not l.url:
        continue
    sec, lab = SECTION[l.categorie]
    crumbs = [("Accueil", u("/")), (lab, u(f"/{sec}/")), (l.titre, l.url)]
    ville = l.ville
    title = f"Chauffeur privé {l.titre} | Standard 24h/24"
    if len(title) > 60:
        title = f"Chauffeur privé {l.titre}"
    meta = (f"Chauffeur privé {l.forme_de if l.categorie != 'Ville' else 'à ' + l.cle} : transferts longue distance, "
            f"{len(l.trajets_depart)} destinations au départ. Devis personnalisé, standard 24h/24.")
    render("lieu.html", l.url, "0.7", photo=PH.pour_lieu(l), svc_liens=[SVC[x] for x in ({'Aéroport': ['navette-aeroport', 'rapatriement', 'chauffeur-vtc-longue-distance'], 'Gare': ['transfert-gare', 'rapatriement', 'chauffeur-vtc-longue-distance']}.get(l.categorie) or (['voyage-affaires', 'chauffeur-vtc-longue-distance', 'mise-a-disposition'] if l.cle in VILLES_AFFAIRES else ['chauffeur-vtc-longue-distance', 'chauffeur-tourisme', 'van-avec-chauffeur']))], l=l, title=title, meta=meta, intro=content.lieu_intro(l), crumbs=crumbs,
           departs=groupe(l.trajets_depart, "dest"), arrivees=groupe(l.trajets_arrivee, "dep"),
           infra=[x for x in infra_de_ville(ville) if x is not l],
           ville_page=villes_avec_page.get(ville) if l.categorie != "Ville" else None,
           quartiers=quartiers_par_ville.get(ville, []), hotels_url=hotel_url.get(ville),
           schemas=schemas(None, crumbs), page_type=l.categorie.lower())

# ---------------------------------------------------------------- Quartiers d'affaires
for q in quartiers:
    v = villes_avec_page[q["ville"]]
    crumbs = [("Accueil", u("/")), ("Quartiers d'affaires", u("/quartiers-affaires/")), (q["nom"], q["url"])]
    render("quartier.html", q["url"], "0.6", photo=PH._preparer("quartier-affaires-soir") if ("Défense" in q["nom"] or q["ville"] == "Paris") else PH.groupe("affaires", q["nom"]), q=q, v=v, crumbs=crumbs,
           title=f"Chauffeur privé {q['nom']} ({q['ville']})"[:70],
           meta=f"Chauffeur privé pour vos rendez-vous, séminaires et conférences à {q['nom']}, {q['ville']}. "
                "Transferts depuis les aéroports et les gares, standard 24h/24.",
           arrivees=top(v.trajets_arrivee, 10), infra=infra_de_ville(q["ville"]), hotels_url=hotel_url.get(q["ville"]),
           schemas=schemas(None, crumbs), page_type="quartier")

# ---------------------------------------------------------------- Hôtels (une page par ville)
for ville, url in hotel_url.items():
    v = villes_avec_page[ville]
    crumbs = [("Accueil", u("/")), ("Hôtels", u("/hotels/")), (ville, url)]
    infra = infra_de_ville(ville)
    render("hotels.html", url, "0.6", photo=PH.groupe("hotels"), ville=ville, v=v, hotels=hotels_par_ville[ville], infra=infra, crumbs=crumbs,
           title=f"Chauffeur privé hôtels {ville} | Transferts 24h/24",
           meta=f"Transferts en chauffeur privé entre les hôtels de {ville} et les aéroports, gares et villes voisines. Devis personnalisé.",
           arrivees=top(v.trajets_arrivee, 8), schemas=schemas(None, crumbs), page_type="hotels")

for s in SVC.values():
    crumbs = [("Accueil", u("/")), ("Services", u("/services/")), (s["nav"], s["url"])]
    f = EXEMPLES.get(s["slug"])
    ex = top([t for t in pub if f(t)], 8) if f else []
    render("service.html", s["url"], "0.8", s=s, photo=PH._preparer(PHOTO_SVC[s["slug"]]), crumbs=crumbs,
           title=s["title"], meta=s["meta"], exemples=ex, autres=[o for o in SVC.values() if o is not s],
           schemas=schemas({"@type": "Service", "serviceType": s["nav"], "name": s["h1"], "description": s["meta"],
                            "provider": {"@id": ORG_ID}, "areaServed": ["France", "Suisse", "Belgique"]}, crumbs, s["faq"]),
           page_type="service")
crumbs = [("Accueil", u("/")), ("Services", u("/services/"))]
render("index_services.html", u("/services/"), "0.8", services=list(SVC.values()), crumbs=crumbs,
       title="Nos services de chauffeur privé et VTC", meta="Chauffeur privé, VTC longue distance, navette aéroport, transfert gare, voyages d'affaires, rapatriement, mise à disposition, événements, tourisme.",
       schemas=schemas(None, crumbs), page_type="index")

# ---------------------------------------------------------------- Index
def par_pays(items, key):
    g = defaultdict(list)
    for it in items:
        g[key(it)].append(it)
    return [(p, g[p]) for p in ("France", "Suisse", "Belgique") if g[p]]


for cat, (sec, lab) in SECTION.items():
    items = sorted([l for l in lieux.values() if l.categorie == cat and l.url], key=lambda l: l.titre)
    crumbs = [("Accueil", u("/")), (lab, u(f"/{sec}/"))]
    render("index_lieux.html", u(f"/{sec}/"), "0.7", label=lab, groupes=par_pays(items, lambda l: l.pays), crumbs=crumbs,
           title=f"{lab} desservis en chauffeur privé", meta=f"{lab} desservis par notre service de chauffeur privé longue distance en France, Suisse et Belgique.",
           schemas=schemas(None, crumbs), page_type="index")

crumbs = [("Accueil", u("/")), ("Trajets", u("/chauffeur-prive/"))]
dep_groups = defaultdict(list)
for t in pub:
    dep_groups[t.dep].append(t)
render("index_trajets.html", u("/chauffeur-prive/"), "0.8", crumbs=crumbs,
       groupes=[(l, sorted(ts, key=lambda t: t.dest.titre)) for l, ts in sorted(dep_groups.items(), key=lambda kv: kv[0].titre)],
       title="Tous nos trajets en chauffeur privé", meta="Trajets longue distance, transferts aéroports et gares en chauffeur privé : France, Suisse et Belgique.",
       schemas=schemas(None, crumbs), page_type="index")

crumbs = [("Accueil", u("/")), ("Quartiers d'affaires", u("/quartiers-affaires/"))]
render("index_simple.html", u("/quartiers-affaires/"), "0.6", crumbs=crumbs, label="Quartiers d'affaires",
       groupes=par_pays(quartiers, lambda q: q["pays"]), kind="quartier",
       title="Quartiers d'affaires desservis en chauffeur privé", meta="Chauffeur privé vers les quartiers d'affaires de France, Suisse et Belgique.",
       schemas=schemas(None, crumbs), page_type="index")
crumbs = [("Accueil", u("/")), ("Hôtels", u("/hotels/"))]
render("index_simple.html", u("/hotels/"), "0.6", crumbs=crumbs, label="Hôtels par ville",
       groupes=par_pays([dict(nom=v, url=x, pays=villes_avec_page[v].pays) for v, x in sorted(hotel_url.items())], lambda d: d["pays"]),
       kind="hotel", title="Transferts hôtels en chauffeur privé", meta="Chauffeur privé entre votre hôtel et les aéroports, gares et villes : France, Suisse, Belgique.",
       schemas=schemas(None, crumbs), page_type="index")

# ---------------------------------------------------------------- Pages fixes
vv = [t for t in pub if t.type == "Ville → Ville"]
panneau, vus = [], set()
for t in top(vv, 40):
    k = frozenset((t.dep.cle, t.dest.cle))
    if k not in vus:
        vus.add(k); panneau.append(t)
panneau = panneau[:5]
aeroports_cles = sorted([l for l in lieux.values() if l.categorie == "Aéroport" and l.url and l.bonus == "Hub"], key=lambda l: l.titre)
villes_cles = sorted([l for l in villes_avec_page.values() if l.priorite == 1], key=lambda l: -len(l.trajets_depart))[:16]
render("home.html", u("/"), "1.0", photo=PH.groupe("accueil"), van=VAN, title=f"{cfg['nom_marque']} | Chauffeur privé France, Suisse & Belgique 24h/24",
       meta="Chauffeur privé pour vos trajets longue distance, transferts aéroports et gares, déplacements professionnels. Standard 24h/24 et 7j/7, devis personnalisé.",
       panneau=panneau, services=list(SVC.values()), aeroports=aeroports_cles, villes=villes_cles, nb_trajets=len(pub),
       schemas=schemas({"@type": "WebSite", "name": cfg["nom_marque"], "url": BASE + "/"}), page_type="accueil")

for slug, tpl, title, meta in [
    ("/chauffeur-prive-urgence/", "urgence.html", "Chauffeur privé urgence et dernière minute | 24h/24",
     "Besoin d'un chauffeur maintenant ? Notre standard répond 24h/24 pour les départs immédiats, les urgences aéroport et les longues distances de dernière minute."),
    ("/chauffeur-prive-24h-24/", "h24.html", "Chauffeur privé 24h/24 et de nuit | Longue distance",
     "Chauffeur privé disponible 24h/24 et 7j/7 : transferts aéroport de nuit, longues distances, départs tôt le matin. Appelez le standard."),
    ("/devis/", "devis.html", "Demander un devis chauffeur privé", "Demandez votre devis de chauffeur privé : départ, destination, date et passagers. Réponse rapide, standard 24h/24."),
    ("/contact/", "contact.html", "Contact | Standard chauffeur privé 24h/24", "Joignez notre standard 24h/24 par téléphone ou envoyez une demande de devis."),
    ("/mentions-legales/", "mentions.html", "Mentions légales", "Mentions légales du site."),
    ("/conditions-generales/", "cgv.html", "Conditions générales de vente", "Conditions générales de vente des prestations de chauffeur privé."),
    ("/confidentialite/", "confidentialite.html", "Politique de confidentialité", "Politique de confidentialité et données personnelles."),
]:
    crumbs = [("Accueil", u("/")), (title.split(" |")[0], u(slug))]
    ph = {"urgence.html": "urgence", "h24.html": "h24", "devis.html": "devis", "contact.html": "devis"}.get(tpl)
    render(tpl, u(slug), "0.3" if tpl in ("mentions.html", "cgv.html", "confidentialite.html") else "0.8", date_maj=datetime.date.today().strftime("%d/%m/%Y"), photo=PH.groupe(ph) if ph else None, title=title, meta=meta, crumbs=crumbs,
           aeroports=aeroports_cles, svc=SVC, schemas=schemas(None, crumbs), page_type=slug.strip("/"))

# 404, statiques, sitemap, robots
html = env.get_template("404.html").render(cfg=cfg, u=u, url="/404.html", canonical=BASE + "/404.html", title="Page introuvable",
                                           meta="", crumbs=[], schemas=[], page_type="404")
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(html)
shutil.copytree(os.path.join(ROOT, "static"), os.path.join(OUT, "static"), dirs_exist_ok=True)
with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for url, prio in pages:
        if "mentions" in url:
            continue
        f.write(f"  <url><loc>{BASE}{url}</loc><lastmod>{TODAY}</lastmod><priority>{prio}</priority></url>\n")
    f.write("</urlset>\n")
open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
if cfg.get("domaine_cname"):
    open(os.path.join(OUT, "CNAME"), "w").write(cfg["domaine_cname"].strip() + "\n")
open(os.path.join(OUT, ".nojekyll"), "w").write("")

cnt = defaultdict(int)
for t in pub:
    cnt[t.type] += 1
print(f"{len(pages)} pages générées dans {cfg['dossier_sortie']}/ — {len(pub)} trajets publiés", dict(cnt))

# ---------------------------------------------------------------- Contrôle du champ lexical
import re as _re, html as _html
_lex = json.load(open(os.path.join(ROOT, "data", "lexique.json"), encoding="utf-8"))
_txt = []
for _r, _, _fs in os.walk(OUT):
    for _f in _fs:
        if _f.endswith(".html"):
            _txt.append(_html.unescape(_re.sub("<[^>]+>", " ", open(os.path.join(_r, _f), encoding="utf-8").read())).lower())
_tout = "\n".join(_txt)
_manque = [m for k, v in _lex.items() if not k.startswith("_") for m in v if m.lower() not in _tout]
_total = sum(len(v) for k, v in _lex.items() if not k.startswith("_"))
print(f"Champ lexical : {_total - len(_manque)}/{_total} expressions présentes sur le site")
if _manque:
    print("Absentes :", ", ".join(_manque))
