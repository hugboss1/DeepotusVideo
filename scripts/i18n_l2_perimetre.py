"""Traduction L2 (t142) : le PÉRIMÈTRE du lot et le contrôle « plus de texte en dur ».

`restes(bundle, couche, gardes, groupes=None)` rend, pour les composants du lot (bundle hors couche, et couche
montage.js), les littéraux qui ressemblent encore à du texte d'interface : ni argument d'un dzT(…), ni littéral
GARDÉ (saisie X ou fragment de gabarit gardé), ni bruit technique. Utilisé par backend/tests/test_i18n_l2.py et par
scripts/i18n_l2_generer.py --seul G --restes.

Le découpage lexical (chaînes, morceaux de gabarits, regex et commentaires sautés) est celui de L1
(scripts/i18n_l1_perimetre.py). Composants relevés le 08/10/2026 sur main 419caf63 : vues routées par la coque
(s==="quick" → um, "studio" → Lh, "templates" → fm, "news" → pm, "scheduler" → Lm, "episodes" → DzChapitres), leur
fermeture dans le bundle, les composants de la couche qu'elles appellent (recette, import de graphe, duel, épingles du
Studio ; réagencement, masque, échantillon, animation, composants, export, Figma, éditeur de texte des Templates ;
fournisseur de voix de Quick et du nœud Voix) et les constantes de module du Studio (catalogue des nœuds Me,
catégories Qr). Exclus : composants du Montage (L3), du Son & VFX (L4), sous-titres et dialogues (L5), l'Atelier
Chapitre (/atelier, L8), et ceux de L1 (dont zm, la page News des Réglages).
"""
import re

from i18n_l1_perimetre import TECHNIQUES as TECHNIQUES_L1, fin_fonction, litteraux, segment, texte_visible

# groupes de saisie -> composants (fonctions, ou constantes de module « nom={…} ») ; cible : bundle ou couche
GROUPES = {
    "quick": "um DzQuickEst DzQuickVoice DzVoTuning DzVoicePicker __dzQuickGallery DzQuickStage DzQuickDrop Lu em",
    "studio_a": "Lh Mh Ah $h Gh Oh Fh dzGraphResume Kh Qh Jh DzOpenGraph Nh Rh Ih DzStudioEst dzCompose Hh Bh Vh Uh "
                "DzHgFormat DzComposePreview dzPreviewModel DzImgModelSel",
    "studio_b": "Yh DzAvatarPick DzAnimation DzImageGenPanel DzTextAI DzEffectsPanel DzNewsScript DzNewsIllust DzNewsPick "
                "DzPromptAI DzAudioPicker DzEmojiPicker DzImgProcPanel DzVoiceNodePanel DzFontPicker DzStickerEditor "
                "DzColorPicker",
    "studio_c": "Th =Qr =Me",
    "templates": "fm hm dzRegionFace dzDupTemplate dzDelTemplate",
    "news": "pm __dzNewsChaine",
    "scheduler": "Lm dm Um Wm Mm Dm __dzSchedPanel __dzSchedCreneaux __dzSchedComptes __dzSchedAnalytics "
                 "__dzSchedCampagne __dzSchedSeries __dzSchedBrief __dzSchedRecycler __dzSchedValider __dzSchedSuite "
                 "Bm DzBrief Am Fm $m na",
    "episodes": "DzChapitres DzEpisodes assembleEpisode DzEpSeedance genIllustration DzEpDevis sendEpisodeToScheduler "
                "genScenes DzEpBar",
    # couche frontend/patches/montage.js
    "studio_couche": "DzRecetteBtn dzRecCapturer dzRecRefus dzRecVerrou DzImportGraph dzImpListe DzDuelPanel DzPinPanel "
                     "DzPinHist DzVoFournisseur dzVoFournisseurOptions DzScrub",
    "templates_couche": "DzReflowBar DzMaskEditor DzEchantillon DzAnimEditor DzComposantBar DzComposantEditor "
                        "dzComposantFace DzExportImage DzExportFigma DzFigmaImport DzTexteEditor DzTplVignette",
}
CIBLE = {g: ("couche" if g.endswith("_couche") else "bundle") for g in GROUPES}

# littéraux techniques du périmètre qui ressemblent à du texte (classes CSS composées, polices, touches…)
TECHNIQUES = set(TECHNIQUES_L1)


def composants(groupes=None, cible=None):
    return [n for g, s in GROUPES.items() if (groupes is None or g in groupes) and (cible is None or CIBLE[g] == cible)
            for n in s.split()]


def portee(s, nom):
    """(début, fin) d'une fonction `nom`, ou d'une constante de module si `nom` commence par « = »."""
    if not nom.startswith("="):
        return segment(s, nom)
    m = re.search(r"(?:,|const |let |var )" + re.escape(nom[1:]) + r"=\{", s)
    if not m:
        return None
    i = m.end() - 1
    return i, fin_fonction(s, i)


def _restes(s, noms, gardes_txt):
    out, vus = [], set()
    for nom in noms:
        r = portee(s, nom)
        if not r or r[1] < 0:
            out.append(f"{nom} : composant introuvable")
            continue
        for d, e, t, q in litteraux(s, *r):
            if (d, e) in vus:
                continue
            vus.add((d, e))
            if s[max(0, d - 4):d] == "dzT(":
                continue
            if t in gardes_txt or t in TECHNIQUES or not texte_visible(t):
                continue
            out.append(f"{nom}@{d} {t[:90]!r}")
    return out


def restes(bundle, couche, gardes, groupes=None):
    gb = {g["texte"][1:-1] for g in gardes if g.get("cible", "bundle") == "bundle"}
    gc = {g["texte"][1:-1] for g in gardes if g.get("cible") == "couche"}
    return (_restes(bundle, composants(groupes, "bundle"), gb)
            + [f"[couche] {r}" for r in _restes(couche, composants(groupes, "couche"), gc)])
