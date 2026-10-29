"""t337 (A7 + C4 du lot Scenario, 29/10/2026) — « Revue du plan » et comparateur commun sur la carte d'un plan, posés
APRÈS L8 (même mécanisme que t335.py : une édition S() par ancre de la BASE 1515d67b).
- un bouton « Revue du plan » (act-revue, glyphe dz-etat-note) en fin des actions de la carte, après « Previs → plan » :
  il ouvre window.__dzRevuePlan (/shared/dz-revue-plan.js, textes revueplan.*) — mesures gratuites (dérive, structure,
  identité) et avis payant du directeur artistique sur devis ;
- un bouton « Comparer » (act-derive-cmp, glyphe dz-action-comparer) sous l'image de production : l'image de
  production contre la vue de référence de l'entité la plus en dérive (GET /shots/{id}/derive, gratuit), dans le
  comparateur commun window.__dzComparateur (/shared/dz-comparateur.js, textes comparateur.*) ;
- leurs écouteurs, juste après celui de « Mesurer la dérive ».
"""
from outils import S

_AT = "atelier/atelier.js"


def C(t: str) -> str:
    """Les sources sont en CRLF : le code ci-dessous est écrit en LF puis converti."""
    return t.replace("\r\n", "\n").replace("\n", "\r\n")


REVUE_AV = "      </div>"
REVUE_AP = C('''        <button class="btn ghost act-revue" title="${dzT("atelier.t337_revue.bouton_t")}" aria-label="${dzT("atelier.t337_revue.bouton")}">${ico("dz-etat-note")}</button>
      </div>''')

CMP_AV = '<div class="shot-derive"></div>'
CMP_AP = ('<div class="shot-derive"></div>\r\n        <button class="btn ghost act-derive-cmp" '
          'title="${dzT("atelier.t337_cmp.bouton_t")}" aria-label="${dzT("atelier.t337_cmp.bouton")}">'
          '${ico("dz-action-comparer")}</button>')

ECOUTE_AV = '    card.querySelector(".act-derive")?.addEventListener("click", () => deriveProduction(id, card));'
ECOUTE_AP = C(ECOUTE_AV + '''
    // t337 : la revue chiffrée du dernier rendu « Previs → plan » (boîte /shared/dz-revue-plan.js)
    card.querySelector(".act-revue").addEventListener("click", () => {
      if (!window.__dzRevuePlan) { toast(dzT("atelier.t337_revue.absent"), true); return; }
      const s = sh();
      window.__dzRevuePlan.ouvrir({ shot: s, numero: (s.idx || 0) + 1, toast });
    });
    // t337 (C4) : l'image de production contre la vue de l'entité la plus en dérive, dans le comparateur commun
    card.querySelector(".act-derive-cmp")?.addEventListener("click", async () => {
      if (!window.__dzComparateur) { toast(dzT("atelier.t337_cmp.absent"), true); return; }
      try {
        const d = await api.get(`/shots/${encodeURIComponent(id)}/derive`);
        const vues = (d.entites || []).filter(e => e.vue != null && e.fichier);
        if (!vues.length) { toast(dzT("atelier.t337_cmp.sans_vue"), true); return; }
        const e = vues.slice().sort((x, y) => (y.verdict === "derive") - (x.verdict === "derive")
          || y.ecart_couleur - x.ecart_couleur)[0];
        window.__dzComparateur.ouvrir({
          a: { src: "/api/images/" + encodeURIComponent(e.fichier), type: "image", libelle: dzT("atelier.t337_cmp.reference", { nom: e.name }) },
          b: { src: "/api/images/" + encodeURIComponent(d.image), type: "image", libelle: dzT("atelier.t337_cmp.production") },
          titre: dzT("atelier.t337_cmp.titre", { nom: e.name }) });
      } catch (err) { toast(dzT("atelier.t337_cmp.ko", { msg: err.message }), true); }
    });''')

DICO = {
    "atelier.t337_revue.bouton": ("Revue du plan", "Shot review"),
    "atelier.t337_revue.bouton_t": ("Revue du plan : le dernier rendu Previs → plan contre sa previs — dérive en images, "
                                    "structure, identité (gratuit), avis du directeur artistique (payant, sur devis), "
                                    "comparateur",
                                    "Shot review: the last Previs → shot render against its previs — drift in frames, "
                                    "structure, identity (free), art director's opinion (paid, quoted first), comparer"),
    "atelier.t337_revue.absent": ("La boîte Revue du plan n'est pas chargée : recharge la page.",
                                  "The Shot review box is not loaded: reload the page."),
}
DICO_CMP = {
    "atelier.t337_cmp.bouton": ("Comparer à la référence", "Compare with the reference"),
    "atelier.t337_cmp.bouton_t": ("Comparer l'image de production à la vue de référence de l'entité la plus en dérive "
                                  "(rideau glissant, O : l'original, C : comparer) — gratuit",
                                  "Compare the production image with the reference view of the entity that drifts "
                                  "most (sliding curtain, O: the original, C: compare) — free"),
    "atelier.t337_cmp.absent": ("Le comparateur n'est pas chargé : recharge la page.",
                                "The comparer is not loaded: reload the page."),
    "atelier.t337_cmp.sans_vue": ("Aucune entité de ce plan n'a de vue de référence à comparer.",
                                  "No entity of this shot has a reference view to compare."),
    "atelier.t337_cmp.reference": ("Référence · {nom}", "Reference · {nom}"),
    "atelier.t337_cmp.production": ("Production", "Production"),
    "atelier.t337_cmp.titre": ("Image de production / référence de {nom}", "Production image / {nom}'s reference"),
    "atelier.t337_cmp.ko": ("Comparaison impossible : {msg}", "Comparison failed: {msg}"),
}

ENTREES = [
    S(_AT, 823, REVUE_AV, REVUE_AP, DICO),
    S(_AT, 827, CMP_AV, CMP_AP, DICO_CMP),
    S(_AT, 894, ECOUTE_AV, ECOUTE_AP, {}),
]
