# Chauffeur Longue Distance — générateur du site

Le site est fabriqué automatiquement à partir du fichier `data/master_seo.xlsx`.
Vous modifiez le fichier, vous l'envoyez sur GitHub : le site se reconstruit et se publie tout seul (2 à 3 minutes).

## Mise en route (une seule fois)

1. Créez un dépôt GitHub (par exemple `chauffeur-prive`) et envoyez-y tout le contenu de ce dossier.
   Sur iPad, l'app **Working Copy** est la plus simple pour envoyer un dossier complet.
2. Dans le dépôt : **Settings → Pages → Source : GitHub Actions**.
3. Ouvrez `config.json` et remplacez les valeurs provisoires :
   - `nom_marque`, `url_site`, `email`
   - `telephone_affiche` (ex. `+33 3 80 00 00 00`) et `telephone_lien` (même numéro sans espaces : `+33380000000`)
   - `domaine_cname` : votre domaine (ex. `www.votre-domaine.fr`) si vous en branchez un. Côté OVH, même principe que pour vos autres sites GitHub Pages.
   - `formulaire_endpoint` : l'adresse fournie par Formspree (voir plus bas)
   - `ga4_id` : l'identifiant Google Analytics 4 (`G-XXXXXXX`). Un bandeau cookies s'affiche alors automatiquement : GA4 ne se charge qu'après « Accepter ».
   - `entreprise` → `declaration_centrale` et `assurance_rc` : numéro de déclaration de centrale de réservation et assureur RC pro. Ils s'affichent dans les mentions légales dès qu'ils sont remplis.
4. Envoyez les modifications : la publication démarre (onglet **Actions** pour suivre).

## Ajouter ou modifier des pages

Tout se fait dans `data/master_seo.xlsx`, puis on remplace le fichier sur GitHub.

| Je veux… | Je fais… |
|---|---|
| Publier plus ou moins de trajets | `config.json` → `phases_publiees` (ex. `["Phase 1", "Phase 2"]`), ou le seuil dans l'onglet 00_Parametres |
| Forcer un trajet précis en ligne | Matrice, colonne **Forcer** : `Publier` |
| Retirer un trajet | Matrice, colonne **Forcer** : `Masquer` |
| Afficher la vraie distance | Matrice, colonne **Distance réelle (km)** — la durée est recalculée |
| Afficher l'itinéraire | Matrice, colonne **Axes routiers** (ex. `A6 puis A40`) |
| Ajouter une ville / un aéroport / une gare | Une ligne dans **10_Lieux** (nom, catégorie, pays, priorité, slug, coordonnées GPS), puis les trajets dans la matrice |
| Ajouter un hôtel ou un quartier d'affaires | Une ligne dans l'onglet 05 ou 04, avec un slug |

Le générateur recalcule lui-même distances, scores et phases avec les paramètres de 00_Parametres : pas besoin que le fichier soit recalculé par Excel.

## Important : toujours partir de la dernière version

Le zip envoyé **remplace** tout le site (un fichier absent du zip est supprimé du dépôt).
Avant de modifier quoi que ce soit, téléchargez la version actuelle du dépôt (bouton **Code → Download ZIP** sur GitHub), sinon vous écraserez les dernières améliorations.
Seul `data/itineraires.json` (les distances routières déjà calculées) est toujours conservé.

## Pages croisées : gares et quartiers d'affaires

En plus des trajets de la matrice, le générateur crée automatiquement (réglages `croisements` dans `config.json`) :

| Réglage | Effet |
|---|---|
| `quartier_aeroports` / `rayon_aeroports_km` | Aéroports proches ↔ chaque quartier d'affaires (ex. CDG → La Défense) |
| `quartier_gares` | Grandes gares de la ville ↔ quartier (ex. Gare de Lyon → La Défense) |
| `quartier_villes` | Villes qui ont un trajet publié vers la ville du quartier ↔ quartier (ex. Lyon → La Défense) |
| `gares_par_ville` / `gare_destinations` | Grandes gares ↔ destinations publiées de leur ville et aéroports proches (ex. Gare Part-Dieu → Genève) |
| `actif` | `false` pour tout désactiver |

Un trajet déjà présent dans la matrice n'est jamais dupliqué. Les coordonnées des quartiers sont dans `data/quartiers.json`
(ou dans des colonnes `Latitude` / `Longitude` ajoutées à l'onglet 04, prioritaires).
Pour ajouter un quartier : une ligne dans l'onglet 04, puis ses coordonnées et formulations dans `data/quartiers.json`.

## Distances routières réelles

À chaque publication sur GitHub, le générateur demande au calculateur d'itinéraires d'OpenStreetMap (OSRM) la vraie distance, la durée
et les autoroutes empruntées (« A6, A46 puis A7 ») pour 2 000 trajets au plus par publication, puis les garde dans `data/itineraires.json`.
Les nouveaux trajets sont calculés automatiquement à la publication suivante.
Une valeur saisie dans la colonne « Distance réelle (km) » ou « Axes routiers » de la matrice reste prioritaire.
Pour désactiver : `config.json` → `itineraires` → `actif: false`. Le service OSRM public est gratuit mais limité : si les pages se multiplient,
un service payant ou auto-hébergé peut le remplacer (champ `service`).

## Pages générées

- `/chauffeur-prive/{depart}-{destination}/` pour les trajets ville → ville
- `/chauffeur-prive/{depart}/{destination}/` pour les trajets avec aéroport ou gare
- `/villes/…`, `/aeroports/…`, `/gares/…` : une page par lieu ayant au moins un trajet publié
- `/chauffeur-prive/{depart}/{destination}/` aussi pour les croisements gares / quartiers d'affaires
- `/quartiers-affaires/…` et `/hotels/{ville}/`
- `/chauffeur-prive-urgence/`, `/chauffeur-prive-24h-24/`, `/devis/`, `/contact/`, `/mentions-legales/`
- `sitemap.xml`, `robots.txt`, page 404

Chaque page porte ses données structurées (Organization, BreadcrumbList, Service, FAQPage lorsque la FAQ est affichée).
LocalBusiness n'est ajouté que si `adresse_entreprise` est renseignée dans `config.json`.

## Champ lexical

`data/lexique.json` liste les 214 expressions du métier (chauffeur privé, VTC, navette, rapatriement, voyage d'affaires, hôtels, tourisme, événements…).
À chaque publication, le générateur vérifie que chacune apparaît sur le site et affiche les absentes dans les logs de l'onglet Actions.
Les textes sont dans `generator/content.py` : les pages trajets alternent plusieurs formulations pour ne pas être identiques entre elles,
et neuf pages de services ciblent chacune une famille de recherches.

## Photos

Les photos sont dans `photos/` et décrites dans `data/photos.json`. À chaque publication, le site les recadre (format 3:2), les compresse en WebP et en JPEG, et choisit la bonne photo selon la page :
stations alpines → photos de montagne, Côte d'Azur → photos de mer, très longue distance → autoroute de nuit,
trajets avec aéroport → photos d'aéroport, et ainsi de suite.

Pour ajouter une photo : déposez `nom-simple.jpg` dans `photos/`, ajoutez une ligne dans `data/photos.json`
(texte alternatif qui décrit ce qu'on voit, point de cadrage), puis ajoutez son nom dans un groupe.
Pour imposer une photo à un lieu précis, utilisez la rubrique `lieux` (ex. `"Bordeaux Saint-Jean": "gare-bordeaux-saint-jean"`).

Les photos viennent de Pexels : usage commercial autorisé, sans mention obligatoire.
Dès que possible, remplacez-les par des photos de vos propres véhicules.

## Formulaire de devis

GitHub Pages n'envoie pas d'emails : le formulaire passe par **Formspree** (formspree.io).
Créez un formulaire, copiez l'adresse `https://formspree.io/f/xxxxxx` dans `formulaire_endpoint`.
Chaque demande contient la page d'origine, la page d'entrée, le référent et les paramètres UTM / gclid.
Tant que l'adresse est vide, le formulaire invite à appeler le standard.

## Suivi des appels

Deux événements sont envoyés à GA4 / Google Tag Manager :
- `clic_appel` : clic sur un numéro, avec l'emplacement du bouton (`entete`, `barre-mobile`, `trajet-haut`…), la page et le trajet
- `demande_devis` : formulaire envoyé, avec départ et destination

Dans GA4, marquez ces deux événements comme **événements clés**.
Un clic n'est pas un appel abouti : pour mesurer les appels réels par page et par mot-clé, il faudra un service de numéros de suivi (call tracking) ou les extensions d'appel Google Ads.

## Modèle juridique affiché sur le site

Le site présente le service comme une **mise en relation** : les trajets sont réalisés, chiffrés et facturés par des chauffeurs VTC partenaires,
et l'éditeur est rémunéré par commission (conditions générales, mentions légales, confidentialité, pied de page).
Les options (pancarte, suivi de vol, relais de chauffeurs, siège enfant…) sont présentées « sur demande » et confirmées dans le devis du chauffeur.

## Avant la mise en ligne

- Faire valider le statut d'intermédiaire (déclaration de centrale de réservation, art. L3142-1 du Code des transports) et remplir `declaration_centrale` / `assurance_rc`.
- Vérifier la carte VTC et l'assurance de chaque chauffeur partenaire (les conditions générales l'annoncent).
- Remplir la colonne « Distance réelle » au moins pour les trajets les plus importants.
- Déclarer le site dans Google Search Console et envoyer `sitemap.xml`.

## Tester sur un ordinateur (facultatif)

```
pip install -r requirements.txt
python generator/build.py
python -m http.server --directory _site
```
