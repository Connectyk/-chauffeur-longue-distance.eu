"""Lecture du fichier master (xlsx) et calcul des trajets.

Le site ne dépend PAS des valeurs calculées par Excel : distances, scores et
phases sont recalculés ici avec les mêmes règles et les paramètres de l'onglet
00_Parametres. On peut donc modifier le fichier sur iPad (Numbers, Excel) sans
risque.
"""
import math
from dataclasses import dataclass, field
import openpyxl


def _rows(wb, sheet):
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    header = [h for h in next(it)]
    out = []
    for r in it:
        if r is None or all(v is None for v in r):
            continue
        out.append({h: v for h, v in zip(header, r) if h})
    return out


def _txt(v):
    return "" if v is None else str(v).strip()


def _num(v):
    try:
        return float(str(v).replace(",", ".").replace(" ", "")) if v not in (None, "") else None
    except ValueError:
        return None


@dataclass(eq=False)
class Lieu:
    cle: str
    categorie: str          # Ville / Aéroport / Gare
    pays: str
    priorite: int
    slug: str
    lat: float
    lon: float
    bonus: str
    rayon: float
    titre: str
    forme_de: str
    forme_vers: str
    ville: str = ""         # ville de rattachement (pour aéroports / gares)
    type_detail: str = ""   # ex. « Aviation d'affaires », « Gare TGV »
    code: str = ""          # IATA
    url: str = ""           # page entité, si générée
    trajets_depart: list = field(default_factory=list)
    trajets_arrivee: list = field(default_factory=list)


@dataclass(eq=False)
class Trajet:
    dep: Lieu
    dest: Lieu
    type: str
    intention: str
    mot_cle: str
    source: str
    distance: int
    distance_reelle: bool
    minutes: int
    score: int
    phase: str
    segment: str
    axes: str
    forcer: str
    url: str = ""
    publie: bool = False

    @property
    def transfrontalier(self):
        return self.dep.pays != self.dest.pays

    @property
    def duree(self):
        m = self.minutes
        if m < 60:
            return f"{m} min"
        h, r = divmod(m, 60)
        return f"{h} h" + (f" {r:02d}" if r else "")


def haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a.lat, a.lon, b.lat, b.lon])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def minutes_route(d, P):
    """Durée de route estimée, arrondie au quart d'heure. En dessous de 60 km, la vitesse
    moyenne urbaine (p_vit_urbaine, 45 km/h par défaut) reflète mieux la circulation."""
    if d < (P.get("p_seuil_urbain") or 60):
        vit = P.get("p_vit_urbaine") or 45
    else:
        vit = P["p_vit_lente"] if d < P["p_seuil_vitesse"] else P["p_vit_rapide"]
    return int(round(d / vit * 60 / 15)) * 15 or 15


def calculer(dep, dest, typ, P, reelle=None, intention="", mot_cle="", source="", axes="", forcer=""):
    """Distance, durée, score, phase et segment d'un trajet (mêmes règles que la matrice Excel)."""
    d = int(round(reelle)) if reelle else int(round(haversine(dep, dest) * P["p_facteur"]))
    minutes = minutes_route(d, P)
    if d < P["p_local"]:
        score = 0
    else:
        R = max([l.rayon for l in (dep, dest) if l.categorie != "Ville"] or [0])
        if typ == "Aéroport → Aéroport":
            s = P["p_pts_plein"]
        elif R:
            s = P["p_pts_plein"] if d <= R else P["p_pts_moyen"] if d <= P["p_mult2"] * R else P["p_pts_r3"]
        else:
            s = P["p_pts_plein"] if d >= P["p_vv_min"] else P["p_pts_moyen"] if d >= P["p_vv_moy"] else P["p_pts_court"]
        s += sum(P["p_prio1"] if l.priorite == 1 else P["p_prio2"] for l in (dep, dest))
        s += P["p_tf"] if dep.pays != dest.pays else 0
        s += P["p_hub"] * [dep.bonus, dest.bonus].count("Hub")
        s += P["p_prem"] if "Premium" in (dep.bonus, dest.bonus) else 0
        score = int(s)
    if d < P["p_local"]:
        phase = "Local → page infra"
    else:
        phase = "Phase 1" if score >= P["p_ph1"] else "Phase 2" if score >= P["p_ph2"] else "Phase 3"
    segment = ("Local" if d < P["p_local"] else "Courte distance" if d < P["p_vv_min"]
               else "Longue distance" if d < P["p_tres_long"] else "Très longue distance")
    return Trajet(dep, dest, typ, intention, mot_cle, source, d, bool(reelle), minutes, score, phase, segment, axes, forcer)


def lire_parametres(wb):
    p = {}
    for name, dn in wb.defined_names.items():
        if name.startswith("p_"):
            for title, coord in dn.destinations:
                p[name] = _num(wb[title][coord.replace("$", "")].value)
    return p


def charger(path, phases_publiees):
    wb = openpyxl.load_workbook(path, data_only=True)
    P = lire_parametres(wb)

    lieux = {}
    for r in _rows(wb, "10_Lieux"):
        cle = _txt(r.get("Nom (clé)"))
        if not cle or _num(r.get("Latitude")) is None:
            continue
        lieux[cle] = Lieu(
            cle=cle, categorie=_txt(r.get("Catégorie")), pays=_txt(r.get("Pays")),
            priorite=int(_num(r.get("Priorité")) or 2), slug=_txt(r.get("Slug")),
            lat=_num(r.get("Latitude")), lon=_num(r.get("Longitude")),
            bonus=_txt(r.get("Bonus")), rayon=_num(r.get("Rayon (km)")) or 0,
            titre=_txt(r.get("Libellé titre")) or cle,
            forme_de=_txt(r.get("Forme « de »")) or f"de {cle}",
            forme_vers=_txt(r.get("Forme « vers »")) or cle,
        )
    for l in lieux.values():
        if l.categorie == "Ville":
            l.ville = l.cle
    by_slug = {l.slug: l for l in lieux.values()}

    # Infos complémentaires depuis les onglets entités
    for r in _rows(wb, "02_Aeroports"):
        l = by_slug.get(_txt(r.get("Slug")))
        if l:
            l.ville = l.ville or _txt(r.get("Ville"))
            l.type_detail = _txt(r.get("Type"))
            l.code = l.code or _txt(r.get("IATA"))
    for r in _rows(wb, "03_Gares"):
        l = by_slug.get(_txt(r.get("Slug")))
        if l:
            l.ville = _txt(r.get("Ville"))
            l.type_detail = _txt(r.get("Type"))

    quartiers = [dict(ville=_txt(r.get("Ville")), nom=_txt(r.get("Quartier / Pôle")), type=_txt(r.get("Type")),
                      pays=_txt(r.get("Pays")), slug=_txt(r.get("Slug")), priorite=int(_num(r.get("Priorité SEO")) or 2),
                      lat=_num(r.get("Latitude")), lon=_num(r.get("Longitude")))
                 for r in _rows(wb, "04_Quartiers_Affaires") if r.get("Slug")]
    hotels = [dict(ville=_txt(r.get("Ville")), nom=_txt(r.get("Hôtel")), categorie=_txt(r.get("Catégorie")),
                   zone=_txt(r.get("Zone")), pays=_txt(r.get("Pays")))
              for r in _rows(wb, "05_Hotels_Business_Luxe") if r.get("Hôtel")]

    trajets, erreurs = [], []
    for i, r in enumerate(_rows(wb, "06_Matrice_Trajets_SEO"), start=2):
        a, b = _txt(r.get("Départ")), _txt(r.get("Destination"))
        if not a or not b:
            continue
        if a not in lieux or b not in lieux:
            erreurs.append(f"Ligne {i} : « {a} » ou « {b} » absent de 10_Lieux")
            continue
        dep, dest = lieux[a], lieux[b]
        typ = _txt(r.get("Type"))
        reelle = _num(r.get("Distance réelle (km)"))
        forcer = _txt(r.get("Forcer (Publier / Masquer)")).lower()
        t = calculer(dep, dest, typ, P, reelle=reelle, intention=_txt(r.get("Intention")),
                     mot_cle=_txt(r.get("Mot-clé cible")), source=_txt(r.get("Source")),
                     axes=_txt(r.get("Axes routiers")), forcer=forcer)
        t.publie = forcer.startswith("publ") or (not forcer.startswith("masq") and t.phase in phases_publiees)
        trajets.append(t)
    return dict(params=P, lieux=lieux, quartiers=quartiers, hotels=hotels, trajets=trajets, erreurs=erreurs)
