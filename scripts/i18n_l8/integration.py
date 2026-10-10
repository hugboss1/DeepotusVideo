"""t148 — integration : les jonctions entre groupes et ce que la surcouche ne voit pas.

- Les <option> fixes des pages : la surcouche n'entre pas dans <select> (dz-i18n.js, TEXTE_EXCLU) → une passe unique au
  chargement de chaque lab, comme core.js du Vectorlab (t146).
- Atelier : deux textes de la page à double sens, saisis en contexte par ath (la surcouche les ignore) — le bouton
  « Monter » de l'animatique (« Build », alors que « Monter » vaut « Move up » ailleurs) et l'option « Libre » du rôle
  vectoriel (« Free », « Liberal » ailleurs) — posés par dzT au chargement.
- Atelier : #daRefName affiche « aucune » (posé par dzT, at3) ; daApply le COMPARAIT au français en dur → en anglais,
  « none » serait parti au serveur comme image de référence. La comparaison passe par la même clé.
- Material Forge : chanOrder() traduisait le canal G du backend en V (vert) : en anglais on garde G.
- Atelier : le titre par défaut d'un chapitre neuf suit la langue ; le test « pas encore renommé » accepte les deux
  langues (un chapitre créé en français garde son comportement).
- Material Forge : les amorces d'invite (SEEDS, SEED_PROMPTS — puces cliquables qui remplissent l'invite) suivent la
  langue de l'interface (décision de l'utilisateur, 10/10) : en anglais, la puce ET l'invite envoyée sont anglaises.
Restes voulus : les nombres et dates formatés en fr-FR (comme L7), le contenu, les textes servis par le backend (L10).
"""
from outils import L, S

_MF = "materialforge/materialforge.js"
_AMORCES = {"fer rouillé": ("fer_rouille", "rusted iron"), "verre givré": ("verre_givre", "frosted glass"),
            "cristal alien": ("cristal_alien", "alien crystal"), "pierre moussue": ("pierre_moussue", "mossy stone"),
            "or martelé": ("or_martele", "hammered gold"), "béton brut": ("beton_brut", "raw concrete"),
            "écorce de bouleau": ("ecorce_bouleau", "birch bark"), "béton usé": ("beton_use", "worn concrete")}


def _amorces(ligne, mots):
    return [L(_MF, ligne, f'"{m}"', f"matiere.int_amorce.{_AMORCES[m][0]}", m, _AMORCES[m][1]) for m in mots]

_OPTIONS = ("\r\n/* t148 : la surcouche de traduction n'entre pas dans les <select> — les <option> fixes de la page sont"
            " traduites ici, une fois (window.__dzI18n.traduire ne rend rien en français). */\r\n"
            "for (const o of document.querySelectorAll(\"select option\")) { const t = window.__dzI18n"
            " && window.__dzI18n.traduire(o.textContent); if (t) o.textContent = t; }")
_ANCRE = "const $ = (s) => document.querySelector(s);"

ENTREES = [
    S("atelier/atelier.js", 5, _ANCRE, _ANCRE + _OPTIONS + "\r\n"
      "/* t148 : les textes de la page à double sens (la surcouche ignore les entrées « contexte ») — « Monter » (Build),\r\n"
      "   « Libre » (Free), « Décor(s) » (Set(s) ; « Setting » est le décor d'Avatar live) : leur dernier nœud texte par dzT */\r\n"
      "{ const poser = (sel, cle) => document.querySelectorAll(sel).forEach((el) => {\r\n"
      "    const n = el.lastChild; if (n && n.nodeType === 3) n.textContent = (/^\\s/.test(n.textContent) ? \" \" : \"\") + dzT(cle); });\r\n"
      "  poser('#vbRole option[value=\"libre\"]', \"atelier.ath_vec.libre\");\r\n"
      "  poser(\"#animGo\", \"atelier.ath_anim.monter\");\r\n"
      "  poser('.btn.k-decor, .chip.k-decor, #vpAddDecor, #vbRole option[value=\"decor\"]', \"atelier.ath_kind.decor\");\r\n"
      "  poser('.tab[data-kind=\"decor\"]', \"atelier.ath_bible.decors\"); }",
      {}),
    S("atelier/atelier.js", 1407, '$("#daRefName").textContent === "aucune"',
      '$("#daRefName").textContent === dzT("atelier.at3_da.aucune")', {}),
    S("materialforge/materialforge.js", 21, _ANCRE, _ANCRE + _OPTIONS, {}),
    S("etabli/etabli.js", 29, _ANCRE, _ANCRE + _OPTIONS, {}),
    S("materialforge/materialforge.js", 2915, 'found.push(mm[1].replace("G", "V") + " = " + mm[2])',
      'found.push((dzLang() === "en" ? mm[1] : mm[1].replace("G", "V")) + " = " + mm[2])', {}),
    S("materialforge/materialforge.js", 2917, '.toUpperCase().replace("G", "V");',
      '.toUpperCase().replace("G", dzLang() === "en" ? "G" : "V");', {}),
    S("atelier/atelier.js", 1760, '{ title: "Nouveau chapitre",', '{ title: dzT("atelier.int_chap.nouveau"),',
      {"atelier.int_chap.nouveau": ("Nouveau chapitre", "New chapter")}),
    S("atelier/atelier.js", 1791, 'chapter.title === "Nouveau chapitre"',
      '[dzT("atelier.int_chap.nouveau"), "Nouveau chapitre"].includes(chapter.title)', {}),
] + (_amorces(725, ["fer rouillé", "verre givré", "cristal alien"])
     + _amorces(726, ["pierre moussue", "or martelé", "béton brut"])
     + _amorces(1390, ["fer rouillé", "verre givré", "cristal alien"])
     + _amorces(1391, ["écorce de bouleau", "or martelé", "béton usé"]))
