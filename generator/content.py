"""Textes des pages, construits à partir des données de chaque trajet / lieu.

Les prestations sont réalisées par des chauffeurs VTC partenaires : le site les
présente comme des options « sur demande » (pancarte, suivi de vol, relais de
chauffeurs, siège enfant…), confirmées par le chauffeur dans son devis.
"""
import zlib

ALPES = {"Courchevel", "Megève", "Chamonix-Mont-Blanc", "Verbier", "Crans-Montana", "Saint-Moritz", "Davos", "Évian-les-Bains"}
RIVIERA = {"Nice", "Cannes", "Monaco", "Saint-Tropez", "Antibes", "Menton"}


def choix(cle, options):
    return options[zlib.crc32(cle.encode()) % len(options)]


def distance_txt(t):
    return f"{t.distance} km" if t.distance_reelle else f"environ {t.distance} km"


def ou_prise_en_charge(l):
    if l.categorie == "Ville":
        return f"à l'adresse de votre choix à {l.cle}"
    if l.categorie == "Quartier":
        return f"à l'adresse de votre bureau ou de votre hôtel ({l.titre})"
    return "à " + l.forme_vers


def ou_depose(l):
    if l.categorie == "Ville":
        return f"l'adresse de votre choix à {l.cle}"
    if l.categorie == "Quartier":
        return f"l'adresse exacte de votre rendez-vous ({l.titre})"
    return l.forme_vers


def pays_txt(a, b):
    return " et la ".join(sorted({a, b})) if a != b else a


def contexte(t, villes_affaires):
    villes = {t.dep.ville, t.dest.ville, t.dep.cle, t.dest.cle}
    if t.type == "Aéroport → Aéroport":
        return "aeroports"
    if "Quartier" in (t.dep.categorie, t.dest.categorie):
        return "affaires"
    if villes & (ALPES | RIVIERA) or "Premium" in (t.dep.bonus, t.dest.bonus):
        return "loisirs"
    if villes & villes_affaires:
        return "affaires"
    return "mixte"


def trajet(t, cfg, retour, villes_affaires=frozenset()):
    d, a = t.dep, t.dest
    k = d.cle + "|" + a.cle
    ctx = contexte(t, villes_affaires)
    intro = choix(k, [
        f"Votre chauffeur privé vous prend en charge {ou_prise_en_charge(d)} et vous conduit jusqu'à {ou_depose(a)}. ",
        f"Un chauffeur VTC professionnel vient vous chercher {ou_prise_en_charge(d)} et vous emmène directement jusqu'à {ou_depose(a)}. ",
        f"Votre voiture avec chauffeur vous attend {ou_prise_en_charge(d)} pour vous déposer à {ou_depose(a)}, de porte à porte. ",
    ]) + f"Le trajet représente {distance_txt(t)}, soit {t.duree} de route selon le trafic."
    sections = []

    if d.categorie == "Aéroport":
        p = [choix(k + "ae", [
            "Indiquez votre numéro de vol à la réservation : le chauffeur peut suivre l'arrivée réelle de l'avion et caler l'heure de prise en charge. "
            "Accueil au point de rendez-vous convenu ou dans le hall des arrivées, avec une pancarte à votre nom sur demande.",
            "Donnez votre numéro de vol en réservant : en cas de retard, la prise en charge est décalée avec l'arrivée de l'avion. "
            "Sur demande, le chauffeur vous accueille dans le hall avec une pancarte à votre nom et vous aide avec les valises.",
        ])]
        if "affaires" in d.type_detail.lower():
            p.append("Pour un vol en jet privé, précisez le terminal d'aviation d'affaires : la prise en charge s'organise directement avec l'assistance aéroportuaire.")
    elif d.categorie == "Gare":
        p = ["Donnez le numéro et l'heure d'arrivée de votre train. Le chauffeur vous attend à la sortie convenue lors de la réservation, "
             "et l'horaire est ajusté en cas de retard de train. Accueil sur le quai avec pancarte possible sur demande."]
        if d.type_detail:
            p.append(f"{d.titre} ({d.type_detail.lower()}) : une prise en charge à la descente du train permet de continuer sans attendre "
                     f"une correspondance vers {a.forme_vers}.")
    elif d.categorie == "Quartier":
        p = [f"Prise en charge devant votre bureau, votre hôtel ou le centre de congrès {d.forme_de}, à l'heure de fin de votre réunion. "
             "Si la réunion se prolonge, prévenez le standard : l'horaire est décalé."]
    else:
        p = [choix(k + "pc", [
            f"Prise en charge à votre domicile, à votre hôtel, à votre bureau ou sur un lieu de rendez-vous à {d.cle}.",
            f"Le chauffeur vient vous récupérer où vous le souhaitez à {d.cle} : domicile, hôtel, siège de votre entreprise ou lieu d'événement.",
        ])]
    sections.append(("Prise en charge", p))

    if a.categorie == "Aéroport":
        p = ["Le standard vous aide à fixer l'heure de départ en fonction de votre vol, de l'enregistrement et des contrôles, avec une marge pour le trafic. "
             "Le chauffeur vous dépose devant le bon terminal."]
    elif a.categorie == "Gare":
        p = ["Dépose au plus près de l'entrée de la gare, avec le temps nécessaire pour rejoindre votre train sans courir."]
    elif a.categorie == "Quartier":
        p = [f"Dépose au pied de l'immeuble de votre rendez-vous, {a.forme_vers} : siège social, tour de bureaux, hôtel ou centre de congrès. "
             "Donnez l'heure à laquelle vous devez être en réunion : la prise en charge est calculée avec une marge pour la circulation."]
    else:
        p = [f"Dépose à l'adresse exacte que vous indiquez à {a.cle} : hôtel, entreprise, domicile ou lieu d'événement."]
    sections.append(("Dépose", p))

    p = []
    if t.axes:
        p.append(f"Itinéraire principal : {t.axes}.")
    if t.type == "Aéroport → Aéroport":
        p.append("Un transfert direct d'aéroport à aéroport : correspondance manquée, vol détourné ou repositionnement d'équipage, "
                 "le chauffeur part dès que vous êtes prêt.")
    if t.segment == "Très longue distance":
        p.append(f"Sur {distance_txt(t)}, le trajet se fait avec des pauses régulières. Pour un départ de nuit ou un horaire serré, "
                 "un relais de chauffeurs peut être organisé sur demande.")
    elif t.segment == "Longue distance":
        p.append(choix(k + "ld", [
            "Un trajet direct, sans correspondance ni attente : vous travaillez, téléphonez ou vous reposez pendant la route.",
            "Pas de changement de train ni d'attente en gare : la route se fait d'une traite, à votre rythme.",
            "Plus simple qu'un trajet en train avec correspondance : vous montez une fois, vous descendez à destination.",
        ]))
    elif t.distance < 60:
        p.append(choix(k + "ur", [
            "Un transfert direct, sans changement de transport en commun ni attente de taxi, avec une marge prévue pour les heures de pointe.",
            "Pas de RER, de métro ni de navette avec vos bagages : le chauffeur vous emmène directement, en tenant compte de la circulation.",
        ]))
    else:
        p.append("Un transfert rapide, utile quand un train ou une navette ne correspond pas à votre horaire.")
    if t.transfrontalier:
        p.append(f"Ce trajet transfrontalier relie la {pays_txt(d.pays, a.pays)}. Prévoyez une pièce d'identité valide pour chaque passager.")
    if a.cle in ALPES or d.cle in ALPES:
        p.append("En hiver, signalez vos skis et votre équipement : l'accès aux stations de ski peut demander plus de temps que l'estimation.")
    sections.append(("Le trajet", p))

    if ctx == "affaires":
        sections.append(("Pour vos déplacements professionnels", [
            choix(k + "af", [
                f"Rendez-vous client, réunion, séminaire ou salon professionnel à {a.ville or a.cle} : vous arrivez à l'heure, reposé, et pouvez préparer votre rendez-vous d'affaires pendant le trajet.",
                f"Pour un voyage d'affaires vers {a.ville or a.cle}, le chauffeur vous dépose devant le siège social, l'hôtel ou le centre de congrès, et peut vous attendre pour le retour.",
                f"Dirigeants, cadres, collaborateurs ou délégations : chaque course vers {a.ville or a.cle} donne lieu à une facture du chauffeur, pratique pour la note de frais.",
            ])]))
    elif ctx == "loisirs":
        sections.append(("Pour votre séjour", [
            choix(k + "lo", [
                f"Séjour à l'hôtel, location de chalet ou de villa : votre chauffeur vous dépose à la porte avec vos bagages, et peut revenir vous chercher pour une excursion ou le trajet retour.",
                f"Vacances en famille, week-end ou séjour de loisirs à {a.ville or a.cle} : un trajet confortable de porte à porte, sans valises à porter dans les correspondances.",
                "Pour un mariage, une soirée, un festival ou une journée découverte, le chauffeur vous emmène et vous raccompagne, même tard le soir.",
            ])]))
    elif ctx == "aeroports":
        sections.append(("Équipages et voyageurs en correspondance", [
            "Pilotes, personnel navigant à repositionner, passagers bloqués par un vol annulé : ce transfert est aussi une solution de rapatriement par la route, de jour comme de nuit."]))

    sections.append(("Bagages et véhicule", [
        choix(k + "bv", [
            "Berline pour un à trois passagers, van pour les groupes ou les bagages volumineux. "
            "Indiquez le nombre de valises et tout équipement particulier (siège enfant, skis, matériel) lors de votre demande.",
            "Berline premium pour voyager seul ou à deux, van 7 places pour une famille ou une équipe. "
            "Précisez vos bagages et vos besoins (rehausseur, skis, matériel) au moment de réserver.",
        ])]))

    sections.append(("Demandes particulières", [
        choix(k + "dp", [
            "Pancarte à votre nom, siège enfant ou rehausseur, véhicule précis, arrêt en route, animal, bagages hors format, attente sur place : "
            "toute demande particulière est étudiée. Précisez-la à la réservation, le chauffeur partenaire la confirme dans son devis.",
            "Un modèle de véhicule, une bouteille d'eau, un arrêt pour récupérer un collègue, un trajet retour le soir même, un horaire inhabituel : "
            "dites-nous ce dont vous avez besoin, nous trouvons le chauffeur qui peut le faire.",
            "Rien n'est figé : accueil avec pancarte, siège bébé, skis, matériel professionnel, animal de compagnie ou étape imprévue. "
            "Indiquez vos demandes à la réservation, elles figurent ensuite sur le devis du chauffeur.",
        ])]))

    sections.append(("Réservation 24h/24", [
        "Le standard répond jour et nuit, 7j/7, week-end et jours fériés compris. Pour un départ dans les prochaines heures, appelez directement : "
        "c'est le moyen le plus rapide. Pour un trajet planifié, demandez un devis gratuit : le prix est fixé à l'avance par le chauffeur partenaire."]))

    faq = [
        (f"Combien de temps dure le trajet {d.titre} – {a.titre} en chauffeur privé ?",
         f"Comptez {t.duree} pour {distance_txt(t)}, hors pauses et selon le trafic." if not t.distance_reelle
         else f"Comptez {t.duree} environ pour {t.distance} km, hors pauses et selon le trafic."),
        ("Comment connaître le prix ?",
         "Chaque trajet fait l'objet d'un devis personnalisé et gratuit selon la date, l'horaire, le nombre de passagers et le véhicule. "
         "Appelez le standard ou envoyez une demande : vous recevez une réponse rapidement."),
    ]
    if d.categorie == "Aéroport":
        faq.append(("Que se passe-t-il si mon vol a du retard ou est annulé ?",
                    "Donnez votre numéro de vol : en cas de retard, la prise en charge suit l'heure d'arrivée réelle de l'avion. En cas de vol annulé, appelez le standard pour adapter la réservation."))
    if d.categorie == "Gare":
        faq.append(("Où le chauffeur m'attend-il ?",
                    "À la sortie convenue lors de la réservation. Son numéro vous est transmis avant votre arrivée."))
    if a.categorie == "Quartier":
        faq.append(("Combien de temps prévoir aux heures de pointe ?",
                    f"L'estimation de {t.duree} correspond à une circulation normale. Aux heures de pointe, le standard prévoit une marge "
                    "pour que vous soyez à l'heure à votre rendez-vous."))
    if t.transfrontalier:
        faq.append(("Le chauffeur peut-il passer la frontière ?",
                    "Oui. Les trajets entre la France, la Suisse et la Belgique sont assurés de porte à porte, sans changement de véhicule."))
    faq.append(choix(k + "fq", [
        ("Peut-on réserver de nuit ou au dernier moment ?",
         f"Oui, le standard répond 24h/24. Pour un départ immédiat, appelez le {cfg['telephone_affiche']}."),
        ("Êtes-vous un service de VTC ?",
         "Nous organisons votre trajet et vous mettons en relation avec un chauffeur VTC professionnel partenaire, dont nous vérifions la carte professionnelle. "
         "Il travaille uniquement sur réservation, avec un prix fixé à l'avance dans son devis."),
        ("Le chauffeur peut-il m'attendre sur place ?",
         "Oui, avec une mise à disposition : le chauffeur reste avec vous le temps de votre rendez-vous ou de votre visite, puis vous raccompagne."),
    ]))
    if retour:
        faq.append(("Peut-on réserver le retour en même temps ?",
                    "Oui. Indiquez la date et l'heure du retour dans votre demande : l'aller-retour est confirmé en une seule fois."))
    return dict(intro=intro, sections=sections, faq=faq, ctx=ctx)


def services_lies(t, ctx):
    """Pages de services à proposer en lien sur une page trajet."""
    s = ["chauffeur-vtc-longue-distance"]
    if "Aéroport" in (t.dep.categorie, t.dest.categorie):
        s.append("navette-aeroport")
    if "Gare" in (t.dep.categorie, t.dest.categorie):
        s.append("transfert-gare")
    s += {"affaires": ["voyage-affaires", "mise-a-disposition"], "loisirs": ["chauffeur-tourisme", "chauffeur-evenement"],
          "aeroports": ["rapatriement"], "mixte": ["van-avec-chauffeur"]}[ctx]
    s.append("van-avec-chauffeur") if "van-avec-chauffeur" not in s else None
    return s


def lieu_intro(l):
    if l.categorie == "Aéroport":
        base = f"Transferts en chauffeur privé depuis et vers {l.forme_vers}"
        if "affaires" in l.type_detail.lower():
            return base + ", y compris pour les vols en jet privé et l'aviation d'affaires. Prise en charge 24h/24, devis personnalisé."
        return base + " : navette aéroport privée, accueil au hall des arrivées, trajets longue distance vers les villes, les gares et les autres aéroports."
    if l.categorie == "Gare":
        return (f"Chauffeur privé au départ et à l'arrivée de {l.forme_vers} : le relais du TGV quand le train ne va pas jusqu'à "
                "votre destination finale, quand l'horaire ne convient pas ou en cas de train supprimé.")
    return (f"Chauffeur privé et VTC au départ et à destination de {l.cle} : trajets longue distance, transferts vers les aéroports "
            "et les gares, voyages d'affaires et séjours. Standard disponible 24h/24.")


# ---------------------------------------------------------------------------
# Pages de services : chacune cible une famille de recherches.
# Les phrases restent naturelles : chaque expression apparaît là où elle a un sens.
# ---------------------------------------------------------------------------
SERVICES = [
 dict(slug="chauffeur-vtc-longue-distance", nav="Chauffeur VTC longue distance",
  title="Chauffeur VTC longue distance | Voiture avec chauffeur 24h/24",
  h1="Chauffeur VTC pour vos longues distances",
  meta="Chauffeur VTC pour vos grands trajets en France, Suisse et Belgique : porte à porte, sans correspondance, devis gratuit, standard 24h/24.",
  intro="Vous préférez ne pas conduire sur un long trajet ? Un chauffeur VTC professionnel vous conduit de porte à porte, d'une ville à l'autre, sans changement ni attente. C'est la voiture de transport avec chauffeur pensée pour la longue distance : un trajet interurbain, régional, national ou transfrontalier, réservé en un appel.",
  sections=[
   ("Une voiture avec chauffeur plutôt qu'un billet de train", [
     "Pas de trajet jusqu'à la gare, pas de correspondance, pas de valises à porter sur le quai : votre chauffeur privé vient vous chercher à l'adresse de départ et vous dépose à l'adresse exacte d'arrivée. Sur une grande distance, c'est souvent le moyen le plus simple de voyager à plusieurs ou avec beaucoup de bagages.",
     "Pour un professionnel, le trajet direct devient du temps utile : appels, préparation d'une réunion, travail sur ordinateur. Pour un particulier ou une famille, c'est un voyage sans stress, à son rythme."]),
   ("Chauffeur particulier, chauffeur de prestige : un seul service", [
     "Qu'on parle de chauffeur particulier, de chauffeur premium, de chauffeur haut de gamme ou de chauffeur de prestige, le service est le même : un chauffeur professionnel et une berline avec chauffeur réservés pour vous seul. C'est du transport privé : un transport de passagers réservé pour vous, pas un véhicule partagé.",
     "Vous souhaitez un véhicule récent avec intérieur cuir, ou un modèle particulier ? Précisez-le à la réservation : le standard vous propose le véhicule correspondant dans le réseau."]),
   ("Aller simple ou aller-retour", [
     "Pour un grand trajet, vous pouvez réserver un aller simple ou un aller-retour. Le tarif est fixé par le devis : un prix connu à l'avance, quel que soit le trafic."]),
   ("Une alternative au taxi sur les grands trajets", [
     "Un taxi fonctionne surtout en ville. Pour un transfert interville de plusieurs centaines de kilomètres, la location de voiture avec chauffeur est plus adaptée : le prix est connu à l'avance grâce au devis, sans compteur qui tourne et sans surprise à l'arrivée."]),
   ("Le service de chauffeur", [
     "Nos chauffeurs partenaires sont des conducteurs expérimentés du transport de personnes, ponctuels, discrets et courtois, en tenue correcte. La discrétion et la confidentialité vont de soi, que vous voyagiez pour un rendez-vous d'affaires ou pour un séjour privé.",
     "La réservation se fait par téléphone auprès de notre standard téléphonique, ou par le formulaire de devis : vous recevez un rappel rapide avec un devis personnalisé."]),
  ],
  faq=[("Quelle est la différence entre un chauffeur VTC et un chauffeur privé ?", "C'est le même métier : VTC signifie voiture de transport avec chauffeur. Le chauffeur VTC exerce avec une carte professionnelle et travaille uniquement sur réservation, ce qui permet de fixer le prix à l'avance. Nos chauffeurs partenaires sont des VTC professionnels."),
       ("Le devis est-il gratuit ?", "Oui, le devis est gratuit et sans engagement. Il précise le prix total du trajet et les modalités de paiement."),
       ("Pouvez-vous faire un trajet de plus de 1 000 km ?", "Oui. Sur les très longues distances, le trajet est organisé avec des pauses régulières, et un relais de chauffeurs peut être prévu sur demande.")]),

 dict(slug="navette-aeroport", nav="Navette aéroport privée",
  title="Navette aéroport privée | Transfert aéroport avec chauffeur",
  h1="Navette aéroport privée et transfert aéroport",
  meta="Navette privée vers et depuis les aéroports : accueil au hall des arrivées, pancarte et suivi de vol sur demande, transfert direct vers votre hôtel. 24h/24.",
  intro="Plus confortable qu'une navette partagée, plus fiable qu'un taxi trouvé à la sortie du terminal : votre transfert aéroport en voiture avec chauffeur vous emmène directement à destination, à n'importe quelle heure.",
  sections=[
   ("Accueil personnalisé à l'arrivée", [
     "Communiquez votre numéro de vol à la réservation : le chauffeur peut suivre l'heure d'arrivée réelle de l'avion et décaler la prise en charge en cas de retard de vol. Sur demande, il vous attend dans le hall des arrivées avec une pancarte à votre nom et prend en charge vos valises jusqu'au véhicule."]),
   ("Vers l'aéroport, sans stress", [
     "Pour un départ, le standard calcule l'heure à laquelle venir vous chercher selon votre vol, le temps d'enregistrement et la circulation. Le chauffeur vous dépose devant le bon terminal."]),
   ("Aviation d'affaires, jet privé et équipages", [
     "Pour un vol en jet privé, la prise en charge s'organise au terminal d'aviation d'affaires ou sur l'aérodrome. Nous assurons aussi le transport des équipages : pilote et personnel navigant à repositionner d'un aéroport à l'autre, même de nuit et sur une grande distance."]),
   ("D'un aéroport à l'autre", [
     "Correspondance manquée, vol détourné vers un autre aéroport, escale imprévue : un transfert direct d'aéroport à aéroport vous évite une nuit sur place ou un billet de dernière minute."]),
  ],
  faq=[("La navette aéroport est-elle partagée avec d'autres voyageurs ?", "Non. C'est une navette privée : le véhicule et le chauffeur sont réservés pour vous et vos passagers uniquement."),
       ("Que se passe-t-il si mon vol est annulé ?", "Appelez le standard : nous pouvons modifier la réservation ou organiser un rapatriement par la route vers votre destination.")]),

 dict(slug="transfert-gare", nav="Transfert gare et navette gare",
  title="Transfert gare TGV avec chauffeur | Navette gare privée",
  h1="Transfert gare et navette gare avec chauffeur",
  meta="Chauffeur privé à la descente du TGV ou pour rejoindre votre train : navette gare privée, accueil à la sortie, retard de train pris en compte. 24h/24.",
  intro="Le TGV vous amène vite d'une grande ville à l'autre, mais rarement jusqu'à la porte de votre hôtel, de votre client ou de votre chalet. Votre chauffeur prend le relais à la gare.",
  sections=[
   ("À l'arrivée du train", [
     "Indiquez le numéro et l'heure d'arrivée de votre train. Le chauffeur vous attend à la sortie convenue ou en bout de quai, et l'horaire suit un éventuel retard de train."]),
   ("Train supprimé, grève, dernière correspondance partie", [
     "En cas de grève ou de train supprimé, appelez le standard : un chauffeur peut vous emmener directement à destination par la route, depuis la gare où vous êtes bloqué."]),
  ],
  faq=[("Pouvez-vous venir me chercher dans une petite gare ?", "Oui, sur réservation : grande gare, gare TGV ou petite gare de campagne, en France, en Suisse et en Belgique."),
       ("Le chauffeur m'aide-t-il avec mes bagages ?", "Oui, il prend en charge les valises entre la gare et le véhicule.")]),

 dict(slug="voyage-affaires", nav="Voyages d'affaires",
  title="Chauffeur pour voyages d'affaires, séminaires et congrès",
  h1="Chauffeur privé pour vos voyages d'affaires",
  meta="Chauffeur privé pour déplacements professionnels : rendez-vous client, séminaire, salon, congrès. Ponctualité, discrétion, facture pour chaque course.",
  intro="Un déplacement professionnel réussi commence par un trajet sans imprévu. Votre chauffeur vous conduit à l'heure à votre rendez-vous d'affaires, à votre séminaire ou au centre de congrès, et vous ramène quand vous le souhaitez.",
  sections=[
   ("Pour tous vos rendez-vous", [
     "Rendez-vous client, réunion au siège social, comité de direction, assemblée générale, visite de site ou d'usine : le chauffeur connaît l'adresse et l'heure à tenir. Vous travaillez pendant le trajet, en toute confidentialité."]),
   ("Salons, congrès et conventions", [
     "Pendant un salon professionnel, un congrès, une conférence ou une convention, nous organisons les transferts entre l'aéroport, la gare, votre hôtel et le lieu de l'événement, pour une personne ou pour une délégation complète."]),
   ("Pour les entreprises", [
     "Dirigeant, cadre, collaborateur en mission ou client VIP à accueillir : le standard centralise vos réservations, pour un collaborateur ou toute une équipe, et un compte entreprise peut être ouvert sur demande. Chaque course fait l'objet d'une facture du chauffeur, à joindre à votre note de frais."]),
  ],
  faq=[("Pouvez-vous transporter une délégation entière ?", "Oui, avec plusieurs berlines ou un van, selon le nombre de passagers et de bagages."),
       ("Le chauffeur peut-il m'attendre pendant ma réunion ?", "Oui, c'est le principe de la mise à disposition : le chauffeur reste disponible le temps de votre rendez-vous, puis vous raccompagne.")]),

 dict(slug="rapatriement", nav="Rapatriement par la route",
  title="Rapatriement en voiture avec chauffeur | Vol annulé, grève",
  h1="Rapatriement par la route avec chauffeur",
  meta="Vol annulé, grève, train supprimé, correspondance manquée : rapatriement en voiture avec chauffeur jusqu'à chez vous, de jour comme de nuit. Standard 24h/24.",
  intro="Quand l'avion ou le train ne part plus, la route reste ouverte. Nous organisons votre rapatriement en voiture avec chauffeur, depuis un aéroport, une gare ou un hôtel, jusqu'à votre domicile ou votre prochaine destination.",
  sections=[
   ("Les situations courantes", [
     "Vol annulé ou détourné, correspondance manquée, grève des contrôleurs ou des cheminots, train supprimé, aéroport fermé par la météo : dans tous ces cas, un départ immédiat par la route évite d'attendre le lendemain."]),
   ("Pour les particuliers et les entreprises", [
     "Un voyageur seul, une famille avec enfants, un groupe de collaborateurs ou un équipage à rapatrier : nous adaptons le véhicule, de la berline au van 7 places. Pour une personne âgée ou une personne à mobilité réduite, précisez-le à l'appel : nous vérifions qu'un véhicule adapté est disponible."]),
  ],
  faq=[("Combien de temps faut-il pour trouver un chauffeur ?", "Appelez le standard : il recherche immédiatement un chauffeur disponible dans le réseau le plus proche de vous et vous confirme l'heure de prise en charge."),
       ("Pouvez-vous rapatrier plusieurs personnes ?", "Oui, avec un van ou plusieurs véhicules selon le nombre de passagers.")]),

 dict(slug="mise-a-disposition", nav="Mise à disposition",
  title="Mise à disposition d'un chauffeur à l'heure ou à la journée",
  h1="Mise à disposition de chauffeur",
  meta="Chauffeur à l'heure ou à la journée : un véhicule et son chauffeur à votre disposition pour enchaîner rendez-vous, visites et trajets. Devis personnalisé.",
  intro="Plusieurs rendez-vous dans la journée, une tournée de visites, un programme qui peut changer : avec la mise à disposition, un chauffeur et son véhicule restent avec vous le temps qu'il faut.",
  sections=[
   ("Chauffeur à l'heure ou à la journée", [
     "Vous réservez un chauffeur à l'heure pour une demi-journée de rendez-vous, ou un chauffeur à la journée pour un programme complet. Il vient vous prendre en charge le matin, vous attend entre chaque étape, s'adapte aux changements d'horaire et vient vous raccompagner le soir."]),
   ("Pour qui ?", [
     "Les entreprises qui reçoivent un client VIP, les dirigeants en tournée, les familles en séjour qui veulent visiter une région, les organisateurs d'événements qui doivent véhiculer leurs invités."]),
  ],
  faq=[("Comment est calculé le prix d'une mise à disposition ?", "Selon la durée, les kilomètres prévus et le véhicule. Le devis personnalisé vous donne le prix à l'avance.")]),

 dict(slug="chauffeur-evenement", nav="Événements et mariages",
  title="Chauffeur pour mariage, gala, festival et événement",
  h1="Chauffeur privé pour vos événements",
  meta="Voiture avec chauffeur pour mariage, gala, soirée, festival, concert, match ou Grand Prix : transferts des invités et des intervenants, de jour comme de nuit.",
  intro="Mariage, gala, soirée d'entreprise, cérémonie, festival, concert, spectacle, match ou Grand Prix : vos invités arrivent à l'heure et repartent en toute sécurité.",
  sections=[
   ("Transferts des invités", [
     "Nous assurons les navettes entre la gare, l'aéroport, les hôtels et le lieu de l'événement, puis le retour tard le soir. Pour un grand nombre de passagers, plusieurs véhicules sont coordonnés par le standard."]),
   ("Intervenants et personnalités", [
     "Artistes, conférenciers, personnalités : accueil personnalisé, discrétion et ponctualité sont la base de notre service de chauffeur."]),
  ],
  faq=[("Pouvez-vous gérer plusieurs véhicules le même jour ?", "Oui, le standard coordonne les chauffeurs et les horaires de chaque transfert.")]),

 dict(slug="chauffeur-tourisme", nav="Tourisme et loisirs",
  title="Chauffeur privé pour le tourisme et les loisirs",
  h1="Chauffeur privé pour vos séjours et visites",
  meta="Chauffeur privé pour touristes : musées, châteaux, vignobles, stations de ski, Riviera. Excursions à la journée et transferts vers votre hôtel.",
  intro="Pour un séjour réussi, laissez le volant : votre chauffeur vous emmène de l'aéroport à votre hôtel, puis vers les musées, les monuments et les plus beaux paysages de la région.",
  sections=[
   ("Excursions et journées découverte", [
     "Une journée découverte des châteaux, une dégustation dans un vignoble, une balade le long de la Côte d'Azur, une visite de musée ou de patrimoine, une après-midi shopping : le chauffeur vous attend à chaque étape et vous raccompagne à votre hôtel."]),
   ("Stations de ski et bord de mer", [
     "Que vous séjourniez dans une station de ski, un chalet ou une résidence des Alpes, ou dans une villa ou un hôtel de la Riviera, le chauffeur vient vous chercher et vous dépose à la porte, avec la place nécessaire pour les skis et les valises."]),
   ("Hôtels et conciergeries", [
     "Votre hôtel 4 étoiles, votre hôtel 5 étoiles ou votre palace peut réserver pour vous : la réception ou le concierge contacte notre standard pour un transfert le jour du check-in ou du check-out."]),
  ],
  faq=[("Le chauffeur peut-il servir de guide ?", "Le chauffeur connaît sa région et vous conseille volontiers, mais il n'est pas guide touristique. Pour une visite guidée, réservez un guide sur place."),
       ("Proposez-vous des circuits sur plusieurs jours ?", "Oui, sur devis : un même chauffeur peut vous accompagner pendant tout votre circuit.")]),

 dict(slug="van-avec-chauffeur", nav="Van et groupes",
  title="Van avec chauffeur pour groupes et familles | 7 places",
  h1="Van avec chauffeur pour groupes et familles",
  meta="Van ou minivan 7 places avec chauffeur pour familles, groupes et équipes : de la place pour les bagages, les skis et le matériel. Devis gratuit.",
  intro="Famille avec enfants, groupe d'amis, équipe en déplacement : un van avec chauffeur permet de voyager tous ensemble, avec les bagages, sur n'importe quelle distance.",
  sections=[
   ("Le véhicule", [
     "Van, minivan ou monospace jusqu'à 7 places, avec un grand coffre pour les valises, les skis ou le matériel. Siège enfant et rehausseur sur demande : indiquez l'âge des enfants à la réservation."]),
   ("Confort à bord", [
     "Véhicule haut de gamme, climatisation, espace pour les jambes : sur un long trajet, le confort de chaque passager compte autant que la ponctualité."]),
  ],
  faq=[("Combien de passagers peut-on transporter ?", "Jusqu'à 7 passagers par van. Au-delà, nous coordonnons plusieurs véhicules.")]),
]
