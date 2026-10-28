"""t335 (A5 du lot Scenario, 28/10/2026) — « Previs → plan » sur la carte d'un plan du storyboard, posé APRÈS L8.

La table réversible L8 (scripts/i18n_l8_paires.json) exige : source du poste == base 1515d67b + éditions. Une
modification du code d'après L8 passe donc par ici, comme une édition S() (même mécanisme que t189.py / t312.py) :
- un bouton « Previs → plan » (act-previs, glyphe dz-media-film) JUSTE APRÈS « Plateau 3D » dans les actions de la
  carte : le clip de previs (@Video1) + des style frames (@Image1…) → la vidéo du plan (Seedance 2.5
  reference-to-video), ou les style frames seules (Veo 3.1 références) ;
- son écouteur, juste après celui du Plateau : il ouvre la boîte window.__dzPrevisPlan (/shared/dz-previs-plan.js,
  textes previs.* dans frontend/shared/i18n/previs.json) avec la carte du plan ; au lancement réussi, la liste des
  plans est relue (loadShots) : la vignette vidéo de la carte suit alors le nouveau job, comme pour act-video.
Le devis, la confirmation, le 409 et le 402 (dz-plafonds.js) vivent dans la boîte.
"""
from outils import S

_AT = "atelier/atelier.js"


def C(t: str) -> str:
    """Les sources sont en CRLF : le code ci-dessous est écrit en LF puis converti."""
    return t.replace("\r\n", "\n").replace("\n", "\r\n")


BOUTON_AV = '${ico("dz-nav-plateau")}</button>'
BOUTON_AP = C('''${ico("dz-nav-plateau")}</button>
        <button class="btn ghost act-previs" title="${dzT("atelier.t335_previs.bouton_t")}" aria-label="${dzT("atelier.t335_previs.bouton")}">${ico("dz-media-film")}</button>''')

ECOUTE_AV = ('    card.querySelector(".act-plateau").addEventListener("click", () => { location.href = "/plateau/?shot=" '
             '+ encodeURIComponent(id); });')
ECOUTE_AP = C(ECOUTE_AV + '''
    // t335 : « Previs → plan » — clip de previs + style frames → la vidéo du plan (boîte /shared/dz-previs-plan.js)
    card.querySelector(".act-previs").addEventListener("click", () => {
      if (!window.__dzPrevisPlan) { toast(dzT("atelier.t335_previs.absent"), true); return; }
      const s = sh();
      window.__dzPrevisPlan.ouvrir({ shot: s, numero: (s.idx || 0) + 1, toast, apres: () => loadShots(true) });
    });''')

DICO = {
    "atelier.t335_previs.bouton": ("Previs → plan", "Previs → shot"),
    "atelier.t335_previs.bouton_t": ("Previs → plan : votre clip de previs (mouvement, caméra) rendu avec le look de "
                                     "style frames — Seedance 2.5 video-to-video, coût affiché et confirmé avant",
                                     "Previs → shot: your previs clip (motion, camera) rendered with the look of style "
                                     "frames — Seedance 2.5 video-to-video, cost shown and confirmed first"),
    "atelier.t335_previs.absent": ("La boîte Previs → plan n'est pas chargée : recharge la page.",
                                   "The Previs → shot box is not loaded: reload the page."),
}

ENTREES = [
    S(_AT, 822, BOUTON_AV, BOUTON_AP, DICO),
    S(_AT, 893, ECOUTE_AV, ECOUTE_AP, {}),
]
