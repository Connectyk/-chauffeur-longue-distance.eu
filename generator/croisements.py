"""Pages croisées : quartiers d'affaires et gares au départ et à l'arrivée.

La matrice Excel couvre les trajets ville / aéroport / gare. Ce module ajoute,
selon les réglages « croisements » de config.json :
  - quartier d'affaires <-> aéroports proches        (ex. CDG -> La Défense)
  - quartier d'affaires <-> gares de la même ville   (ex. Gare de Lyon -> La Défense)
  - villes publiées      <-> quartier d'affaires      (ex. Lyon -> La Défense)
  - grandes gares        <-> destinations publiées de leur ville et aéroports proches
                                                       (ex. Gare Part-Dieu -> Genève)
Un trajet déjà présent dans la matrice n'est jamais dupliqué.
"""
import json, os
from collections import defaultdict
import model

DEFAUTS = {
    "actif": True,
    "distance_min_km": 3,
    "quartier_aeroports": 3,
    "rayon_aeroports_km": 60,
    "quartier_gares": 3,
    "quartier_villes": 8,
    "gares_par_ville": 3,
    "gare_destinations": 8,
    "types_gares": ["Grande gare", "Gare TGV", "Gare TGV/aéroport"],
}


def reglages(cfg):
    return dict(DEFAUTS, **(cfg.get("croisements") or {}))


def quartiers_comme_lieux(root, quartiers):
    """Transforme chaque quartier d'affaires en point de départ / d'arrivée."""
    chemin = os.path.join(root, "data", "quartiers.json")
    coords = json.load(open(chemin, encoding="utf-8")) if os.path.exists(chemin) else {}
    out, manquants = {}, []
    for q in quartiers:
        c = coords.get(q["slug"], {})
        lat, lon = q.get("lat") or c.get("lat"), q.get("lon") or c.get("lon")
        if lat is None or lon is None:
            manquants.append(q["nom"])
            continue
        l = model.Lieu(cle=f"{q['nom']} ({q['ville']})", categorie="Quartier", pays=q["pays"], priorite=q["priorite"],
                       slug=q["slug"], lat=lat, lon=lon, bonus="", rayon=0,
                       titre=c.get("titre") or q["nom"], forme_de=c.get("de") or f"du quartier {q['nom']}",
                       forme_vers=c.get("vers") or f"le quartier {q['nom']}", ville=q["ville"], type_detail=q["type"])
        q["lieu"] = l
        out[l.cle] = l
    return out, manquants


def generer(lieux, quartiers_l, pub, P, cfg):
    R = reglages(cfg)
    if not R["actif"]:
        return []
    existants = {(t.dep.cle, t.dest.cle) for t in pub}
    nouveaux = []

    def ajouter(dep, dest):
        if dep is dest or (dep.cle, dest.cle) in existants:
            return
        t = model.calculer(dep, dest, f"{dep.categorie} → {dest.categorie}", P, source="Croisement")
        if t.distance < R["distance_min_km"]:
            return
        t.publie = True
        existants.add((dep.cle, dest.cle))
        nouveaux.append(t)

    def proches(l, candidats, n, rayon=None):
        c = [(model.haversine(l, x), x) for x in candidats if x is not l]
        c = [(d, x) for d, x in c if rayon is None or d <= rayon]
        return [x for _, x in sorted(c, key=lambda dx: (dx[0], dx[1].cle))][:n]

    aeroports = [l for l in lieux.values() if l.categorie == "Aéroport"]
    gares = [l for l in lieux.values() if l.categorie == "Gare"]
    par_score = lambda ts: sorted(ts, key=lambda t: (-t.score, t.distance))

    # Trajets publiés au départ / à l'arrivée de chaque ville
    vv_vers, depuis_ville = defaultdict(list), defaultdict(list)
    for t in pub:
        if t.dep.categorie == "Ville" and t.dest.categorie == "Ville":
            vv_vers[t.dest.cle].append(t)
        if t.dep.categorie == "Ville" and t.dest.categorie in ("Ville", "Aéroport") and t.dest.ville != t.dep.cle:
            depuis_ville[t.dep.cle].append(t)
    pub_paires = {(t.dep.cle, t.dest.cle) for t in pub}

    # Quartiers d'affaires
    for q in quartiers_l.values():
        for a in proches(q, aeroports, R["quartier_aeroports"], R["rayon_aeroports_km"]):
            ajouter(a, q); ajouter(q, a)
        for g in proches(q, [g for g in gares if g.ville == q.ville and g.priorite == 1], R["quartier_gares"]):
            ajouter(g, q); ajouter(q, g)
        for t in par_score(vv_vers[q.ville])[:R["quartier_villes"]]:
            ajouter(t.dep, q)
            if (q.ville, t.dep.cle) in pub_paires:
                ajouter(q, t.dep)

    # Grandes gares : relais du train vers les destinations de la ville et les aéroports proches
    gares_ville = defaultdict(list)
    for g in gares:
        if g.priorite == 1 and g.type_detail in R["types_gares"]:
            gares_ville[g.ville].append(g)
    for ville, gs in gares_ville.items():
        for g in gs[:R["gares_par_ville"]]:
            for a in proches(g, aeroports, R["quartier_aeroports"], R["rayon_aeroports_km"]):
                ajouter(g, a); ajouter(a, g)
            for t in par_score(depuis_ville[ville])[:R["gare_destinations"]]:
                ajouter(g, t.dest); ajouter(t.dest, g)
    return nouveaux
