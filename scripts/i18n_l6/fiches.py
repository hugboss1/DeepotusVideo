"""t146 — fiches : les fiches didactiques (aide/index.json) dans la langue de l'interface.

Une fiche peut porter titre_en, phrase_en et fichier_en (animation recapturée sur l'interface anglaise, skill
didacticiel-option). fiche_langue(f, langue) — pure, bancable node — rend la vue de la fiche dans la langue (les champs
anglais quand ils existent, sinon la fiche telle quelle : Spritelab, Tilelab et Photolab, qui importent ce module,
n'ont pas encore de fiches anglaises). L'index est passé par elle au chargement : l'encart et le « ? » (« Aide : … »)
lisent la vue.
"""
from outils import S

DI = "js/mod-didact.js"

ENTREES = [
    S(DI, 42, 'export function didact_html(f, aide = "aide/") {',
      '// la vue d\'une fiche dans la langue de l\'interface : titre_en / phrase_en / fichier_en quand la fiche les porte\r\n'
      'export function fiche_langue(f, langue) {\r\n'
      '  if (!f || langue !== "en" || !f.titre_en || !f.phrase_en || !f.fichier_en) return f;\r\n'
      '  return { ...f, titre: f.titre_en, phrase: f.phrase_en, fichier: f.fichier_en };\r\n'
      '}\r\n'
      'const langue_page = () => (typeof window !== "undefined" && typeof window.dzLang === "function" ? window.dzLang() : "fr");\r\n'
      '\r\n'
      'export function didact_html(f, aide = "aide/") {', {}),
    S(DI, 149, 'index = Array.isArray(j) ? j.filter((f) => valider_fiche(f).length === 0) : [];',
      'index = Array.isArray(j) ? j.map((f) => fiche_langue(f, langue_page())).filter((f) => valider_fiche(f).length === 0) : [];', {}),
]
