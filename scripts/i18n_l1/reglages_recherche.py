"""t141 — la recherche des Réglages (DzSettingsSearch) : le serveur rend, pour chaque résultat, sa section (`section`,
identifiant stable) et un libellé de rubrique (`rubrique`) écrit contre l'ancien bundle, mélange de français et
d'anglais. L'écran montre désormais le libellé de la BARRE dans la langue affichée, tiré de la section ; le libellé du
serveur ne sert plus que de repli (section inconnue). La recherche elle-même (mots fr et en de l'index) ne change pas."""
from outils import S

_CARTE = ("var dzRubriques={diag:dzT(\"reglages.onglet.diag\"),coffre:dzT(\"reglages.onglet.coffre\"),"
          "appareils:dzT(\"reglages.onglet.appareils\"),keys:dzT(\"reglages.onglet.cles\"),"
          "accounts:dzT(\"reglages.onglet.comptes\"),personas:dzT(\"reglages.onglet.personas\"),"
          "branding:dzT(\"reglages.onglet.marque\"),pack:dzT(\"reglages.onglet.pack\"),"
          "defaults:dzT(\"reglages.onglet.defauts\"),paths:dzT(\"reglages.onglet.chemins\"),"
          "news:dzT(\"reglages.onglet.news\"),appearance:dzT(\"reglages.onglet.apparence\"),"
          "pricing:dzT(\"reglages.onglet.tarifs\"),transfert:dzT(\"reglages.onglet.transfert\")};"
          "return(e&&dzRubriques[e.section])||(e&&e.rubrique)||\"\"")

ENTREES = [
    S(650760, "function DzSettingsSearch(", "function dzRubrique(e){" + _CARTE + "}function DzSettingsSearch(", {}),
    S(652016, "title:e.libelle+' → '+e.rubrique", "title:e.libelle+' → '+dzRubrique(e)", {}),
    S(652333, "'→ '+e.rubrique})", "'→ '+dzRubrique(e)})", {}),
]
