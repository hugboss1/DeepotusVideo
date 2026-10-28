# -*- coding: utf-8 -*-
"""t312 (tâche 7) — mesure de la lecture locale d'un scan sur 10 pages test FABRIQUÉES (décision utilisateur du 28/10).

Fabrique avec Pillow (polices de C:/Windows/Fonts) 10 cas de test, 5 FR + 5 EN, chacun avec son texte de référence
(prose originale écrite pour ce banc), puis les lit par le MÊME chemin que les routes `/api/scan/lire`
(`scan_pages.charger` -> `scan_lecture._lire_ocr` : OCR Windows.Media.Ocr + nettoyage) et mesure :
- CER / WER (distance de Levenshtein ; blancs normalisés, apostrophes ’ ‘ ramenées à ') ;
- mots marqués incertains contre mots réellement faux (précision / rappel ; un mot est « faux » si son cœur, sans la
  ponctuation collée, diffère du mot de référence aligné, ou s'il est en trop) ;
- durée de lecture par page (s) ; et, en second passage, le mode « auto » (langue retenue, CER).

Les pages générées vont dans le dossier `--sortie` (hors dépôt) ; seul ce script et le rapport sont versionnés.

    python scripts/scan_mesure.py --sortie <dossier> [--json resultats.json] [--cas fr1,en3] [--sans-auto]
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import time

from PIL import Image, ImageDraw, ImageFont

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend"))

POLICES = pathlib.Path("C:/Windows/Fonts")
DPI = 150
A5 = (874, 1240)      # 148 × 210 mm à 150 dpi
A4 = (1240, 1754)     # 210 × 297 mm à 150 dpi


def pt(points: float) -> int:
    """Corps typographique en points -> pixels à 150 dpi."""
    return round(points / 72 * DPI)


# ------------------------------------------------------------------------------------------------- textes de référence
# Prose originale écrite pour ce banc (aucun texte tiré d'une œuvre). Paragraphes séparés par une ligne vide.
TEXTES = {
    "fr1": """Le gardien du phare de Kerlan montait chaque soir les cent douze marches de la tour. Il comptait à voix basse, par habitude plus que par besoin, car il connaissait chaque pierre et chaque fissure du mur.

En haut, il essuyait la grande lentille avec un chiffon de laine, puis il allumait la lampe. La lumière tournait lentement au-dessus de la mer, et les bateaux qui rentraient au port saluaient d'un coup de corne.

Un soir de novembre, la tempête arracha une fenêtre de la lanterne. Le vent s'engouffra dans la pièce, fit voler les papiers et renversa la bouilloire. Le gardien boucha le trou avec une planche et passa la nuit assis près de la lampe, à surveiller la flamme.

Au matin, la mer était calme. Il descendit les marches une à une, ouvrit la porte et regarda longtemps l'horizon, comme on regarde un vieil ami qui a enfin fini de crier.""",

    "fr2": """Le marché de Saint-Aubin ouvre ses portes le samedi à sept heures. Les marchands arrivent bien avant l'aube pour monter leurs étals sous la halle de fer et de verre construite par le grand-père du maire actuel.

On y trouve des fromages de chèvre roulés dans la cendre, des pommes ridées qui sentent le grenier, du pain au levain cuit dans un four à bois et des bouquets de fleurs des champs liés avec du raphia.

Madame Lebrun vend des œufs depuis quarante ans. Elle connaît le prénom de chaque client et le nom de chacune de ses poules. Elle affirme que les œufs pondus un jour de pluie ont meilleur goût, mais personne n'a jamais pu le vérifier.

Vers midi, la halle se vide peu à peu. Les enfants ramassent les cagettes abandonnées pour construire des cabanes, et le balayeur municipal pousse devant lui une montagne de feuilles de salade et de papiers froissés.

Le dimanche, la halle reste fermée. Les pigeons en profitent pour picorer les miettes oubliées entre les pavés, sous le regard indifférent du chat de la boulangerie voisine.""",

    "fr3": """L'administration départementale annonça solennellement la réhabilitation intégrale de l'ancienne bibliothèque municipale. Les architectes proposèrent immédiatement plusieurs aménagements particulièrement ambitieux : une verrière contemporaine, des rayonnages entièrement modulables et un auditorium souterrain.

Les habitants, initialement enthousiastes, découvrirent progressivement les conséquences budgétaires de ces transformations extraordinaires. Plusieurs associations demandèrent publiquement des explications supplémentaires sur le financement prévisionnel.

Finalement, le conseil municipal adopta une solution intermédiaire, nettement moins spectaculaire mais considérablement plus raisonnable, qui permit de rouvrir les salles de lecture dès le printemps suivant.""",

    "fr4": """La barque glissait sur l'eau brune du fleuve, poussée par un courant si lent qu'on aurait dit que la rivière hésitait à rejoindre la mer. Sur la rive gauche, des saules penchaient leurs branches jusqu'à toucher la surface, et des hérons immobiles guettaient les poissons entre les roseaux.

Mathilde tenait la rame d'une main distraite. Elle pensait à la lettre qu'elle avait reçue la veille, une lettre sans signature, écrite à l'encre violette sur un papier qui sentait la lavande. Quelqu'un lui donnait rendez-vous au vieux moulin, le soir de la Saint-Jean, sans dire pourquoi.

Elle avait d'abord cru à une plaisanterie de son frère, puis à une erreur du facteur. Mais l'écriture penchée lui rappelait quelque chose, un souvenir d'école ou de vacances, qu'elle n'arrivait pas à saisir tout à fait.

Le moulin apparut au détour d'un méandre. Sa roue ne tournait plus depuis longtemps, et le lierre avait couvert la moitié de la façade. Une lumière tremblait pourtant derrière l'unique fenêtre de l'étage, comme si quelqu'un l'attendait déjà.

Mathilde rangea la rame au fond de la barque et laissa le courant la porter vers la berge. Le cœur battant, elle sauta sur le ponton de bois vermoulu, qui craqua sous son poids, et s'avança vers la porte entrouverte.

À l'intérieur, l'odeur de farine ancienne se mêlait à celle de la cire. Sur une table, une bougie neuve brûlait à côté d'une boîte en fer-blanc, de celles où l'on gardait autrefois les biscuits du dimanche.""",

    "fr5": """— Tu as vu l'heure ? demanda Paul en posant son sac sur la chaise.

— Je sais, répondit Claire sans lever les yeux de son livre. Le train avait du retard.

— Encore ? C'est la troisième fois cette semaine.

— La quatrième, corrigea-t-elle. Mais qui compte ?

Paul haussa les épaules et ouvrit le réfrigérateur. Il resta un long moment devant la porte ouverte, comme s'il espérait qu'un repas complet allait apparaître par magie.

— Il reste des pâtes d'hier, dit Claire.

— Avec quoi ?

— Avec de la patience et un peu de fromage râpé.

Il éclata de rire, sortit la casserole et alluma le gaz. Dehors, la pluie recommençait à tomber sur les toits de la ville.""",

    "en1": """The old observatory stood on the hill above the village, its copper dome turned green by a century of rain. Nobody had looked through the great telescope since the last astronomer retired, and the key to the door hung forgotten on a nail in the post office.

One autumn evening, a girl named Ada borrowed the key without asking. She climbed the spiral stairs with a torch in one hand and a notebook in the other, and she pushed open the heavy shutters of the dome.

The sky was clear and very dark. Ada found the eyepiece by touch, turned the brass wheels as she had seen in an old photograph, and waited for her eyes to adjust. Slowly, a soft grey smudge appeared among the stars.

She drew it carefully in her notebook, together with the date and the time. Years later, that page would hang framed on the wall of a university library, labelled as the first sketch of a comet that now carries her name.""",

    "en2": """The committee met on the first Tuesday of every month in the back room of the public library. Its members included a retired teacher, two farmers, the owner of the hardware store and a young engineer who had recently moved to the town with her family.

Their task was simple in principle and difficult in practice: to decide how the small annual budget for the river path should be spent. Some wanted new benches, others wanted better lighting, and a few insisted that the money should go to repairing the wooden bridge near the mill before anything else.

The engineer listened to every argument and took careful notes. At the end of the third meeting she unfolded a large map on the table and showed, section by section, where the path flooded each spring, where the bridge planks had rotted and where the old lamps no longer worked.

Her proposal was to repair the bridge first, raise the lowest part of the path by thirty centimetres, and install solar lamps only where people actually walked after dark. The benches could wait another year.

The committee voted in favour by six votes to one. The only member who disagreed was the hardware store owner, who had hoped to sell the benches himself, but even he admitted that the plan made sense.

By the following summer the bridge was solid again, the path stayed dry through the April rains, and families from the new houses on the east side began to use it every evening.""",

    "en3": """Every morning at six, the baker on Mill Street opened the shutters of his shop and set out a small table on the pavement. On it he placed a basket of yesterday's bread, a jar for coins and a handwritten sign that said simply: take what you need.

For years the jar was never full and never empty. Students took a roll on their way to the station, a night nurse took half a loaf after her shift, and an old man with a dog always left more coins than the bread was worth.

When the baker fell ill one winter, his neighbours noticed the empty table at once. Within a week they had organised a rota: the florist baked scones, the schoolteacher brought muffins, and the man with the dog painted a new sign.

The baker returned in the spring, thinner and a little slower, to find the table already set and the jar overflowing. He stood in the doorway for a long time before he could trust himself to speak.""",

    "en4": """The lighthouse keeper's daughter learned to read by the light of the lamp itself. Her father had no money for books, so he wrote stories for her on the backs of old weather reports, one page each night, and pinned them to the wall beside her bed.

The stories were about a fox who sailed around the world in a teapot, meeting kings, pirates and talking whales. Each page ended with a question, and she had to guess the answer before the next page appeared.

When she grew up and left the island, she took the pages with her in a tin box. She never published them, although many people asked her to. She said that some stories belong to the people who first heard them, and that a fox in a teapot would not survive the cold air of a printing house.""",

    "en5": """The expedition left the base camp at 5:45 am on 14 March 2025 with 6 climbers, 3 guides and 210 kg of equipment. The temperature at the start was -12 °C, and the wind reached 45 km/h on the upper ridge.

They covered 8.5 km on the first day and climbed 1,240 m. Each climber drank about 3.2 L of water and burned roughly 5,800 kcal. The second camp was set at an altitude of 4,870 m, on a flat shelf 30 m wide.

On day 3 the weather improved: visibility rose to 20 km, and the wind dropped below 15 km/h. The team reached the summit (5,642 m) at 11:20 am, spent 25 minutes there, and returned to the second camp by 4 pm.

The whole trip cost about 18,500 euros, or roughly 2,055 euros per person. Batteries lasted 72 hours at 80 % charge, and the satellite phone used 340 MB of data.""",
}

TITRE_COURANT = "LES CARNETS DU FLEUVE"


# ------------------------------------------------------------------------------------------------- rendu
def police(nom: str, taille_pt: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(POLICES / nom), pt(taille_pt))


def _largeur(dessin: ImageDraw.ImageDraw, texte: str, f) -> float:
    return dessin.textlength(texte, font=f)


def _couper_mot(dessin, mot: str, f, reste: float):
    """Césure d'un mot pour tenir dans `reste` px : (début avec tiret, suite) ou None. ≥ 3 lettres de chaque côté,
    jamais dans un mot qui porte déjà un tiret ou une apostrophe."""
    if len(mot) < 7 or any(c in mot for c in "-'’"):
        return None
    coeur = mot.rstrip(".,;:!?")
    for i in range(len(coeur) - 3, 2, -1):
        debut = mot[:i] + "-"
        if not mot[:i].isalpha():
            continue
        if _largeur(dessin, debut, f) <= reste:
            return debut, mot[i:]
    return None


def composer(dessin, paragraphe: str, f, largeur: float, cesure: bool = False) -> list[list[str]]:
    """Un paragraphe -> lignes (listes de mots) qui tiennent dans `largeur`."""
    lignes, cur = [], []
    esp = _largeur(dessin, " ", f)
    mots = paragraphe.split()
    i = 0
    while i < len(mots):
        mot = mots[i]
        essai = " ".join(cur + [mot])
        if not cur or _largeur(dessin, essai, f) <= largeur:
            cur.append(mot)
            i += 1
            continue
        if cesure:
            reste = largeur - _largeur(dessin, " ".join(cur), f) - esp
            c = _couper_mot(dessin, mot, f, reste)
            if c:
                cur.append(c[0])
                mots[i] = c[1]
        lignes.append(cur)
        cur = []
    if cur:
        lignes.append(cur)
    return lignes


def dessiner_bloc(dessin, paragraphes: list[str], f, x: float, y: float, largeur: float, *, interligne=1.35,
                  ecart_para=0.6, retrait=0.0, justifie=False, cesure=False, encre=(20, 20, 20), y_max=None,
                  suite=False):
    """Dessine des paragraphes dans une colonne ; rend (y final, reste à dessiner). Un paragraphe coupé par le bas de
    la colonne revient en tête du reste sous la forme (\"suite\", texte) : il reprend sans retrait. `suite` : le
    premier paragraphe est une suite (pas de retrait)."""
    asc, desc = f.getmetrics()
    h = (asc + desc) * interligne
    esp = _largeur(dessin, " ", f)
    for ip, para in enumerate(paragraphes):
        r = 0.0 if (suite and ip == 0) else retrait
        lignes = composer(dessin, para, f, largeur - r, cesure)
        for il, mots in enumerate(lignes):
            if y_max is not None and y + h > y_max:
                if il == 0:
                    return y, paragraphes[ip:], (suite and ip == 0)
                return y, [" ".join(w for ws in lignes[il:] for w in ws)] + paragraphes[ip + 1:], True
            x0 = x + (r if il == 0 else 0)
            dispo = largeur - (r if il == 0 else 0)
            derniere = il == len(lignes) - 1
            if justifie and not derniere and len(mots) > 1:
                total = sum(_largeur(dessin, m, f) for m in mots)
                pas = (dispo - total) / (len(mots) - 1)
                cx = x0
                for m in mots:
                    dessin.text((cx, y), m, font=f, fill=encre)
                    cx += _largeur(dessin, m, f) + pas
            else:
                dessin.text((x0, y), " ".join(mots), font=f, fill=encre)
            y += h
        y += h * ecart_para
    return y, [], False


def page_vierge(taille, fond=(255, 255, 255)) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", taille, fond)
    return im, ImageDraw.Draw(im)


def _png(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, format="PNG", dpi=(DPI, DPI))
    return b.getvalue()


def paras(cle: str) -> list[str]:
    return [p.strip() for p in TEXTES[cle].split("\n\n") if p.strip()]


def rendre(cle: str) -> list[Image.Image]:
    """Les images du cas `cle` (une seule, sauf fr4 : deux pages)."""
    marge = 90
    if cle == "fr1":     # une colonne simple
        im, d = page_vierge(A5)
        dessiner_bloc(d, paras(cle), police("georgia.ttf", 11), marge, 110, A5[0] - 2 * marge)
        return [im]
    if cle == "fr2":     # deux colonnes
        im, d = page_vierge(A4)
        f = police("times.ttf", 11)
        gout = 60
        lc = (A4[0] - 2 * marge - gout) / 2
        _, reste, suite = dessiner_bloc(d, paras(cle), f, marge, 120, lc, retrait=30, ecart_para=0.3, y_max=660)
        # le reste coule dans la colonne de droite (le paragraphe coupé y continue sans retrait)
        if reste:
            dessiner_bloc(d, reste, f, marge + lc + gout, 120, lc, retrait=30, ecart_para=0.3, suite=suite)
        return [im]
    if cle == "fr3":     # césures en fin de ligne (colonne étroite)
        im, d = page_vierge(A5)
        dessiner_bloc(d, paras(cle), police("times.ttf", 12), 150, 120, A5[0] - 300, cesure=True, retrait=28,
                      ecart_para=0.2)
        return [im]
    if cle == "fr4":     # folios + titre courant, deux pages
        f = police("GARA.TTF", 12.5)
        ft = police("GARA.TTF", 9)
        pages, reste, folio, suite = [], paras(cle), 42, False
        while reste and len(pages) < 2:
            im, d = page_vierge(A5)
            lt = _largeur(d, TITRE_COURANT, ft)
            d.text(((A5[0] - lt) / 2, 60), TITRE_COURANT, font=ft, fill=(40, 40, 40))
            _, reste, suite = dessiner_bloc(d, reste, f, marge, 130, A5[0] - 2 * marge, retrait=30,
                                            ecart_para=0.0, y_max=A5[1] - 130, suite=suite)
            lf = _largeur(d, str(folio), ft)
            d.text(((A5[0] - lf) / 2, A5[1] - 80), str(folio), font=ft, fill=(40, 40, 40))
            pages.append(im)
            folio += 1
        if reste:
            raise RuntimeError("fr4 : le texte déborde des deux pages")
        return pages
    if cle == "fr5":     # dialogues à tirets
        im, d = page_vierge(A5)
        dessiner_bloc(d, paras(cle), police("times.ttf", 12), marge, 110, A5[0] - 2 * marge, retrait=25,
                      ecart_para=0.1)
        return [im]
    if cle == "en1":     # faible contraste : gris clair sur blanc cassé
        im, d = page_vierge(A5, fond=(246, 243, 234))
        dessiner_bloc(d, paras(cle), police("arial.ttf", 10.5), marge, 110, A5[0] - 2 * marge,
                      encre=(168, 166, 160))
        return [im]
    if cle == "en2":     # petite police : 9 pt à 150 dpi
        im, d = page_vierge(A4)
        dessiner_bloc(d, paras(cle), police("times.ttf", 9), 120, 140, A4[0] - 240, retrait=25, ecart_para=0.4)
        return [im]
    if cle == "en3":     # légère rotation (1°)
        im, d = page_vierge(A5)
        dessiner_bloc(d, paras(cle), police("georgia.ttf", 11), marge, 110, A5[0] - 2 * marge)
        return [im.rotate(1.0, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))]
    if cle == "en4":     # texte justifié
        im, d = page_vierge(A5)
        dessiner_bloc(d, paras(cle), police("times.ttf", 12), marge, 110, A5[0] - 2 * marge, justifie=True,
                      retrait=28, ecart_para=0.0)
        return [im]
    if cle == "en5":     # chiffres et unités
        im, d = page_vierge(A5)
        dessiner_bloc(d, paras(cle), police("arial.ttf", 10.5), marge, 110, A5[0] - 2 * marge)
        return [im]
    raise KeyError(cle)


CAS = [
    ("fr1", "fr", "Une colonne simple (Georgia 11 pt, A5)"),
    ("fr2", "fr", "Deux colonnes (Times 11 pt, A4)"),
    ("fr3", "fr", "Césures en fin de ligne (Times 12 pt, colonne étroite)"),
    ("fr4", "fr", "Folios + titre courant, 2 pages (Garamond 12,5 pt)"),
    ("fr5", "fr", "Dialogues à tirets cadratins (Times 12 pt)"),
    ("en1", "en", "Faible contraste, gris clair sur blanc cassé (Arial 10,5 pt)"),
    ("en2", "en", "Petite police 9 pt (Times, A4)"),
    ("en3", "en", "Rotation de 1° (Georgia 11 pt)"),
    ("en4", "en", "Texte justifié (Times 12 pt)"),
    ("en5", "en", "Chiffres et unités (Arial 10,5 pt)"),
]


# ------------------------------------------------------------------------------------------------- mesures
_APOS = str.maketrans({"’": "'", "‘": "'", "\u00a0": " ", "\u202f": " "})


def normaliser(t: str) -> str:
    return " ".join((t or "").translate(_APOS).split())


def levenshtein(a, b) -> int:
    if len(a) < len(b):
        a, b = b, a
    prec = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prec[j] + 1, cur[j - 1] + 1, prec[j - 1] + (x != y)))
        prec = cur
    return prec[-1]


def aligner(ref: list[str], hyp: list[str]) -> list[tuple[int | None, int | None]]:
    """Alignement mot à mot (Levenshtein avec retour arrière) : [(i_ref|None, j_hyp|None)]."""
    n, m = len(ref), len(hyp)
    D = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        D[i][0] = i
    for j in range(m + 1):
        D[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j] = min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, paires = n, m, []
    while i or j:
        if i and j and D[i][j] == D[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            paires.append((i - 1, j - 1)); i -= 1; j -= 1
        elif j and D[i][j] == D[i][j - 1] + 1:
            paires.append((None, j - 1)); j -= 1
        else:
            paires.append((i - 1, None)); i -= 1
    return paires[::-1]


def _coeur(mot: str) -> str:
    from app.services.scan_nettoyage import _coeur as c
    d, f = c(mot)
    return mot[d:f] if d < f else mot


def jetons_positions(texte: str) -> list[tuple[str, int, int]]:
    out, i, n = [], 0, len(texte)
    while i < n:
        if texte[i].isspace():
            i += 1
            continue
        j = i
        while j < n and not texte[j].isspace():
            j += 1
        out.append((texte[i:j], i, j))
        i = j
    return out


def mesurer(ref_texte: str, hyp_texte: str, incertains: list[dict]) -> dict:
    ref_n, hyp_n = normaliser(ref_texte), normaliser(hyp_texte)
    cer = levenshtein(ref_n, hyp_n) / max(1, len(ref_n))
    ref_m = ref_n.split()
    hyp_tok = jetons_positions(hyp_texte)
    hyp_m = [normaliser(t) for t, _, _ in hyp_tok]
    wer = levenshtein(ref_m, hyp_m) / max(1, len(ref_m))
    faux = set()
    exemples = []
    for i, j in aligner(ref_m, hyp_m):
        if j is None:
            continue
        if i is None or _coeur(ref_m[i]) != _coeur(hyp_m[j]):
            faux.add(j)
            if len(exemples) < 8:
                exemples.append(f"{ref_m[i] if i is not None else '∅'} → {hyp_m[j]}")
    marques = set()
    for inc in incertains or []:
        for j, (_t, d, f) in enumerate(hyp_tok):
            if d < inc["fin"] and inc["debut"] < f:
                marques.add(j)
    vrais = len(marques & faux)
    return {
        "cer": cer, "wer": wer, "mots_ref": len(ref_m), "mots_lus": len(hyp_m),
        "faux": len(faux), "marques": len(marques), "marques_justes": vrais,
        "precision": (vrais / len(marques)) if marques else None,
        "rappel": (vrais / len(faux)) if faux else None,
        "paras_ref": len([p for p in ref_texte.split("\n\n") if p.strip()]),
        "paras_lus": len([p for p in (hyp_texte or "").split("\n\n") if p.strip()]),
        "exemples": exemples,
    }


def lire(images: list[bytes], langue: str) -> tuple[dict, float]:
    """Le chemin des routes : charger les fichiers comme l'upload, puis la lecture locale partagée."""
    from app.services import scan_lecture, scan_pages
    plan = scan_pages.charger([(f"page{i + 1}.png", o) for i, o in enumerate(images)])
    t0 = time.perf_counter()
    r = scan_lecture._lire_ocr(plan, langue)
    return r, time.perf_counter() - t0


# ------------------------------------------------------------------------------------------------- programme
def principal() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sortie", required=True, help="dossier des pages générées et des textes lus (hors dépôt)")
    ap.add_argument("--json", help="fichier où écrire les résultats bruts")
    ap.add_argument("--cas", help="liste de cas à lancer, ex. fr1,en3")
    ap.add_argument("--sans-auto", action="store_true", help="ne pas refaire la lecture en mode auto")
    a = ap.parse_args()
    sortie = pathlib.Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    voulus = set(a.cas.split(",")) if a.cas else None

    from app.services import scan_ocr
    d = scan_ocr.disponible()
    if not d.get("ok"):
        print(f"OCR indisponible : {d.get('raison')}")
        return 2
    print(f"OCR Windows : langues {d.get('langues')}")

    resultats = []
    for cle, langue, titre in CAS:
        if voulus and cle not in voulus:
            continue
        images = rendre(cle)
        octets = [_png(im) for im in images]
        for k, o in enumerate(octets):
            (sortie / f"{cle}_{k + 1}.png").write_bytes(o)
        (sortie / f"{cle}_reference.txt").write_text(TEXTES[cle], encoding="utf-8")
        r, duree = lire(octets, langue)
        (sortie / f"{cle}_lu.txt").write_text(r["texte"], encoding="utf-8")
        m = mesurer(TEXTES[cle], r["texte"], r["incertains"])
        m.update({"cas": cle, "langue": langue, "titre": titre, "pages": len(octets),
                  "s_par_page": duree / len(octets), "stats": r.get("stats")})
        if not a.sans_auto:
            ra, da = lire(octets, "auto")
            ma = mesurer(TEXTES[cle], ra["texte"], ra["incertains"])
            m["auto"] = {"langue": ra.get("langue"), "cer": ma["cer"], "wer": ma["wer"],
                         "s_par_page": da / len(octets), "precision": ma["precision"], "rappel": ma["rappel"],
                         "marques": ma["marques"], "faux": ma["faux"]}
        resultats.append(m)
        aut = f" | auto {m['auto']['langue']} CER {m['auto']['cer']:.2%}" if "auto" in m else ""
        print(f"{cle} ({langue}) CER {m['cer']:.2%} WER {m['wer']:.2%} faux {m['faux']} marqués {m['marques']} "
              f"(justes {m['marques_justes']}) §{m['paras_lus']}/{m['paras_ref']} {m['s_par_page']:.2f} s/page{aut}")
        for e in m["exemples"]:
            print(f"    {e}")

    for lg in ("fr", "en"):
        rs = [r for r in resultats if r["langue"] == lg]
        if not rs:
            continue
        moy = lambda k: sum(r[k] for r in rs) / len(rs)
        print(f"Moyenne {lg.upper()} : CER {moy('cer'):.2%} WER {moy('wer'):.2%} {moy('s_par_page'):.2f} s/page")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
