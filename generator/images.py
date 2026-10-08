"""Préparation des photos (recadrage 3:2, WebP + JPEG) et choix de la photo de chaque page.

Pour ajouter une photo : déposez-la dans photos/ (nom-simple.jpg), puis ajoutez-la
dans data/photos.json (texte alternatif, cadrage, groupe).
"""
import json, os, zlib
from PIL import Image, ImageOps

RATIO = 3 / 2
LARGEURS = (800, 1600)


class Photos:
    def __init__(self, root, out, prefix):
        self.cfg = json.load(open(os.path.join(root, "data", "photos.json"), encoding="utf-8"))
        self.src = os.path.join(root, "photos")
        self.out = os.path.join(out, "static", "img")
        self.prefix = prefix
        self.faites = {}
        os.makedirs(self.out, exist_ok=True)

    def _preparer(self, cle):
        if cle in self.faites:
            return self.faites[cle]
        info = self.cfg["photos"][cle]
        im = ImageOps.exif_transpose(Image.open(os.path.join(self.src, cle + ".jpg"))).convert("RGB")
        fx, fy = info.get("cadrage", [0.5, 0.5])
        w, h = im.size
        if w / h > RATIO:
            nw = int(h * RATIO); x = int(min(max(fx * w - nw / 2, 0), w - nw)); im = im.crop((x, 0, x + nw, h))
        else:
            nh = int(w / RATIO); y = int(min(max(fy * h - nh / 2, 0), h - nh)); im = im.crop((0, y, w, y + nh))
        for lw in LARGEURS:
            v = im.resize((lw, int(lw / RATIO)), Image.LANCZOS)
            v.save(os.path.join(self.out, f"{cle}-{lw}.webp"), quality=74, method=5)
        im.resize((1200, 800), Image.LANCZOS).save(os.path.join(self.out, f"{cle}-1200.jpg"), quality=80, optimize=True, progressive=True)
        p = self.prefix + "/static/img/" + cle
        d = dict(cle=cle, alt=info["alt"], webp=f"{p}-800.webp 800w, {p}-1600.webp 1600w", jpg=f"{p}-1200.jpg",
                 largeur=1600, hauteur=int(1600 / RATIO))
        self.faites[cle] = d
        return d

    def groupe(self, nom, graine=""):
        lst = self.cfg["groupes"].get(nom) or self.cfg["groupes"]["defaut"]
        return self._preparer(lst[zlib.crc32(graine.encode()) % len(lst)])

    def zone(self, *noms):
        for z, membres in self.cfg["zones"].items():
            if any(n in membres for n in noms):
                return z
        return None

    def pour_lieu(self, l):
        if l.cle in self.cfg["lieux"]:
            return self._preparer(self.cfg["lieux"][l.cle])
        z = self.zone(l.cle)
        if z:
            return self.groupe(z, l.cle)
        if l.categorie == "Aéroport":
            return self.groupe("aeroport", l.cle)
        if l.categorie == "Gare":
            return self.groupe("gare", l.cle)
        return self.groupe("defaut", l.cle)

    def pour_trajet(self, t):
        g = t.dep.cle + t.dest.cle
        z = self.zone(t.dest.cle) or self.zone(t.dep.cle)
        if z:
            return self.groupe(z, g)
        if t.segment == "Très longue distance":
            return self.groupe("nuit", g)
        if "Aéroport" in (t.dep.categorie, t.dest.categorie):
            return self.groupe("aeroport", g)
        if "Gare" in (t.dep.categorie, t.dest.categorie):
            return self.groupe("gare", g)
        return self.groupe("defaut", g)
