"""Distances routières réelles et autoroutes empruntées (OpenStreetMap / OSRM).

Les itinéraires sont gardés dans data/itineraires.json : chaque trajet n'est
demandé qu'une fois. La recherche ne se fait que si config.json l'active
(« itineraires » -> « actif ») ET que la variable d'environnement
ITINERAIRES=1 est présente (c'est le cas dans la publication GitHub).
Sans réseau, le site se construit normalement avec les distances estimées.
Une distance saisie dans la colonne « Distance réelle (km) » reste prioritaire.
"""
import json, os, time, urllib.request, urllib.error

DEFAUTS = {"actif": True, "service": "https://router.project-osrm.org", "max_par_publication": 400,
           "pause_secondes": 1.1, "marge_duree": 1.12}


def _cle(t):
    return f"{t.dep.lat:.4f},{t.dep.lon:.4f};{t.dest.lat:.4f},{t.dest.lon:.4f}"


def _axes(route):
    """Routes principales (A6, E25, N7…) parcourues sur plus de 15 km, dans l'ordre du trajet."""
    km, ordre = {}, []
    for leg in route.get("legs", []):
        for st in leg.get("steps", []):
            for ref in (st.get("ref") or "").split(";"):
                ref = ref.strip().replace(" ", "")
                if not ref or ref[0] not in "AENR" or not ref[1:2].isdigit():
                    continue
                if ref not in km:
                    km[ref] = 0
                    ordre.append(ref)
                km[ref] += st.get("distance", 0) / 1000
    garde = [r for r in ordre if km[r] >= 15]
    # Une autoroute (A) prime sur sa référence européenne (E) parcourue en même temps
    if any(r.startswith("A") for r in garde):
        garde = [r for r in garde if not r.startswith("E")]
    return garde[:5]


def lire_reponse(data, marge):
    r = data["routes"][0]
    return {"km": int(round(r["distance"] / 1000)), "min": int(round(r["duration"] / 60 * marge)), "axes": _axes(r)}


def _demander(service, t, marge):
    url = (f"{service.rstrip('/')}/route/v1/driving/{t.dep.lon},{t.dep.lat};{t.dest.lon},{t.dest.lat}"
           "?overview=false&steps=true")
    req = urllib.request.Request(url, headers={"User-Agent": "chauffeur-longue-distance-site-generator"})
    with urllib.request.urlopen(req, timeout=20) as rep:
        data = json.load(rep)
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError(data.get("code"))
    return lire_reponse(data, marge)


def formater_axes(axes):
    if not axes:
        return ""
    return axes[0] if len(axes) == 1 else ", ".join(axes[:-1]) + " puis " + axes[-1]


def appliquer(root, cfg, trajets):
    R = dict(DEFAUTS, **(cfg.get("itineraires") or {}))
    chemin = os.path.join(root, "data", "itineraires.json")
    cache = json.load(open(chemin, encoding="utf-8")) if os.path.exists(chemin) else {}
    reseau = R["actif"] and os.environ.get("ITINERAIRES") == "1"
    demandes, erreurs = 0, 0
    for t in sorted(trajets, key=lambda t: (-t.score, t.distance)):
        k = _cle(t)
        if k not in cache and reseau and demandes < R["max_par_publication"] and erreurs < 5:
            try:
                cache[k] = _demander(R["service"], t, R["marge_duree"])
                demandes += 1
                time.sleep(R["pause_secondes"])
            except (urllib.error.URLError, ValueError, KeyError, OSError, TimeoutError) as e:
                erreurs += 1
                print("Itinéraire indisponible :", t.dep.cle, "->", t.dest.cle, e)
        it = cache.get(k)
        if not it:
            continue
        if not t.distance_reelle:
            t.distance, t.distance_reelle = it["km"], True
            t.minutes = max(15, int(round(it["min"] / 15)) * 15)
        if not t.axes:
            t.axes = formater_axes(it["axes"])
    if demandes:
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)
    manquants = sum(1 for t in trajets if _cle(t) not in cache)
    print(f"Itinéraires : {demandes} nouveaux, {len(trajets) - manquants}/{len(trajets)} trajets avec distance réelle")
