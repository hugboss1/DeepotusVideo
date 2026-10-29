"""Angles vifs et finitions de la COQUE (t374, 29/10/2026, lot A « Finitions esthétiques »).

La coque ne peut pas réécrire ses rayons à la source : le bundle est prébâti (ses styles React en ligne et les chaînes
CSS de ses couches sont figés par les maillons et leurs bancs) et les feuilles du Montage / Son & VFX sont figées
par `test_montage_bundle`. Ce script GÉNÈRE donc `frontend/shared/dz-bords.css` (copie identique dans
`frontend/dist/shared/`), liée EN DERNIER par `frontend/dist/index.html`, qui ramène à `var(--radius)` (0) :
  [A] chaque règle CSS de la coque qui écrit un rayon littéral > 0 (feuilles servies ET chaînes CSS du bundle), par
      son propre sélecteur ;
  [B] chaque rayon en ligne de React (`borderRadius:6` → attribut `style="…border-radius: 6px…"`), par sélecteur
      d'attribut ;
  [C] les classes Tailwind `rounded*` (hors `rounded-full`).
Un rond reste rond : les exceptions du cliquet (`50%`, `99px`, ≥ 100 px, `var(--r-pill)`) ne sont jamais visées, ni
une règle dont la boîte carrée fait un disque (`width` = `height` en px, rayon ≥ moitié).
Suivent les FINITIONS écrites à la main (bloc `FINITIONS` ci-dessous) : typographie et gris de la charte, sélecteur
de modèle sur une ligne, coin d'ascenseur.

Usage : python scripts/charte_bords.py [--check]   (`--check` : sort en 1 si la feuille n'est pas à jour)
Banc : backend/tests/test_charte_bords.py. Aucune dépendance hors bibliothèque standard (python embarqué).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charte_releve  # noqa: E402

RACINE = charte_releve.RACINE
SORTIE = RACINE / "frontend" / "shared" / "dz-bords.css"
COPIE = RACINE / "frontend" / "dist" / "shared" / "dz-bords.css"

# Une règle CSS : sélecteur { déclarations } — sans imbrication. Guillemets admis (polices nommées, sélecteurs
# d'attribut) : dans le bundle, on ne lit que l'intérieur des littéraux de chaîne.
_REGLE = re.compile(r"([^{};]+)\{([^{}]*)\}")
_RAYON = re.compile(r"(?<![\w-])border(?:-(?:top|bottom)-(?:left|right))?-radius\s*:\s*([^;}]+)")
# Un sélecteur : commence par . # [ : * ou un nom de balise ; `=` et guillemets seulement dans un [attribut].
_SEL_OK = re.compile(r"^[.#\[:*a-zA-Z][\w\s.#\-\[\]=\":>,*+~()^$|%]*$")
_HORS_ATTR = re.compile(r"\[[^\]]*\]")
# React : borderRadius:6 / borderRadius:"3px 0 0 3px"
_INLINE_NB = re.compile(r"(?<![\w$-])borderRadius:(\d+(?:\.\d+)?)(?![\d.\w])")
_INLINE_STR = re.compile(r"(?<![\w$-])borderRadius:\"([^\"]+)\"")


def _px(regle: str, prop: str) -> float | None:
    m = re.search(r"(?<![\w-])" + prop + r"\s*:\s*([\d.]+)px", regle)
    return float(m.group(1)) if m else None


def _disque(corps: str, val: str) -> bool:
    m = re.fullmatch(r"([\d.]+)px", val)
    w, h = _px(corps, "width"), _px(corps, "height")
    return bool(m and w and h and abs(w - h) < 0.01 and float(m.group(1)) * 2 >= w - 0.01)


def _nettoyer_sel(sel: str) -> str | None:
    sel = re.sub(r"/\*.*?\*/", "", sel, flags=re.S)
    # ce qui précède le sélecteur dans une feuille minifiée : fin d'@media, @charset…
    sel = re.sub(r"^.*@media[^{]*$", "", sel).strip()
    sel = re.sub(r"\s+", " ", sel)
    if not sel or sel.startswith("@") or not _SEL_OK.match(sel) or "${" in sel:
        return None
    if re.search(r"^(from|to|\d+%)(\s*,\s*(from|to|\d+%))*$", sel):   # étapes d'@keyframes
        return None
    if sel.endswith(" :focus-visible"):                  # tout élément focalisé, ronds compris : laissé
        return None
    if sel.count("[") != sel.count("]") or sel.count("(") != sel.count(")"):
        return None
    if re.search(r"[=\"]", _HORS_ATTR.sub("", sel)):        # du code, pas un sélecteur
        return None
    return sel


def _sel_dans_js(brut: str) -> str:
    """Dans du code, le sélecteur commence après le dernier délimiteur de chaîne ou de concaténation
    (`st.textContent='.dz-tip{…` → `.dz-tip`) ; il doit alors commencer comme une classe, un id, un attribut ou un
    pseudo (un nom de balise nu ne se distingue pas du code : laissé)."""
    sel = re.split(r"['\"`;+]", brut)[-1].strip()
    return sel if sel[:1] in (".", "#", "[", ":", "*") else ""


def selecteurs_css(texte: str, js: bool = False, html: bool = False) -> set[str]:
    res = set()
    if html:
        # une page : ses blocs <style> (CSS), puis ses scripts (CSS posé dans des chaînes)
        sources = [(s, False) for s in re.findall(r"<style[^>]*>(.*?)</style>", texte, flags=re.S | re.I)]
        sources += [(s, True) for s in re.findall(r"<script[^>]*>(.*?)</script>", texte, flags=re.S | re.I)]
    else:
        sources = [(texte, js)]
    for src, code in sources:
        if not code:
            src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        for m in _REGLE.finditer(src):
            corps = m.group(2)
            vals = [charte_releve._normal(v) for v in _RAYON.findall(corps)]
            if not any(charte_releve.rayon_compte(v) and not _disque(corps, v) for v in vals):
                continue
            sel = _nettoyer_sel(_sel_dans_js(m.group(1)) if code else m.group(1))
            if sel:
                res.update(s.strip() for s in sel.split(",") if s.strip())
    return res


def _serialise(val: str) -> str:
    """Ce que le navigateur écrit dans l'attribut style pour une valeur React."""
    return " ".join(p if not re.fullmatch(r"\d+(\.\d+)?", p) else p + "px" for p in val.split())


def valeurs_en_ligne(texte: str) -> set[str]:
    vals = {v + "px" for v in _INLINE_NB.findall(texte) if float(v) > 0}
    for v in _INLINE_STR.findall(texte):
        if charte_releve.rayon_compte(v):
            vals.add(_serialise(v))
    return {v for v in vals if charte_releve.rayon_compte(v)}


FINITIONS = """\
/* ── finitions écrites à la main (t374) ────────────────────────────────────── */
/* Typographie : les gris Tailwind du bundle rejoignent les quatre encres de la charte. */
.text-slate-100{color:var(--fg-1)}
.text-slate-200,.text-slate-300{color:var(--fg-2)}
.text-slate-400,.text-slate-500{color:var(--fg-3)}
.text-slate-600{color:var(--fg-4)}
.font-mono{font-family:var(--font-mono)}
.font-sans{font-family:var(--font-ui)}
/* Sélecteur de modèle (Quick, Studio…) : UNE ligne, l'excédent en points de suspension (le bouton fait 30 px). */
button[data-dzselect]{gap:var(--pad-2);min-width:0}
button[data-dzselect]>span:first-child{flex:1 1 auto;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left}
/* Ascenseurs : le coin où se croisent les deux barres n'est plus le carré blanc par défaut du moteur. */
::-webkit-scrollbar-corner{background:transparent}
"""


def scripts_partages() -> list[Path]:
    """Les scripts /shared que la coque charge (index.html) : leur CSS injecté vit dans la page de la coque."""
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    dossier = RACINE / "frontend" / "dist" / "shared"
    a_lire = re.findall(r'src="/shared/([\w.-]+\.js)"', html)
    vus: list[str] = []
    while a_lire:                                        # les modules importés vivent dans la même page
        n = a_lire.pop(0)
        p = dossier / n
        if n in vus or not p.is_file():
            continue
        vus.append(n)
        a_lire += re.findall(r'''from\s+["']\./([\w.-]+\.js)["']''', p.read_text(encoding="utf-8", errors="replace"))
    return [dossier / n for n in vus if not charte_releve._EXCLUS.search((dossier / n).as_posix())]


def generer() -> str:
    fichiers = charte_releve.fichiers_zone("coque") + scripts_partages()
    sels: set[str] = set()
    vals: set[str] = set()
    for p in fichiers:
        if p.name == "dz-bords.css":
            continue
        t = p.read_text(encoding="utf-8", errors="replace")
        sels |= selecteurs_css(t, js=p.suffix == ".js", html=p.suffix == ".html")
        if p.suffix == ".js":
            vals |= valeurs_en_ligne(t)
    out = ["/* GÉNÉRÉ par scripts/charte_bords.py (t374) — ne pas éditer : relancer le script.",
           "   Angles vifs de la coque sans toucher au bundle prébâti ni aux feuilles figées du Montage.",
           "   Liée EN DERNIER par frontend/dist/index.html ; copie identique dans frontend/dist/shared/. */",
           "/* [A] règles de la coque qui écrivaient un rayon littéral — UNE règle par sélecteur : un sélecteur que le",
           "   navigateur refuserait n'emporte que la sienne */"]
    out += [s + "{border-radius:var(--radius)!important}" for s in sorted(sels)]
    out.append("/* [B] rayons en ligne de React (attribut style) */")
    attrs = [f'[style*="border-radius: {v}"]' for v in sorted(vals, key=lambda v: (len(v), v))]
    out.append(",\n".join(attrs) + "{border-radius:var(--radius)!important}")
    out.append("/* [C] classes Tailwind (rounded-full reste rond) */")
    out.append(".rounded,.rounded-sm,.rounded-md,.rounded-lg,.rounded-xl,.rounded-2xl"
               "{border-radius:var(--radius)!important}")
    return "\n".join(out) + "\n" + FINITIONS


def main() -> None:
    neuf = generer().encode("utf-8")
    if "--check" in sys.argv:
        # fins de ligne : celles du dépôt (core.autocrlf), comparées sans en tenir compte
        ok = all(p.is_file() and p.read_bytes().replace(b"\r\n", b"\n") == neuf for p in (SORTIE, COPIE))
        print("dz-bords.css à jour" if ok else "dz-bords.css PÉRIMÉE : relancer scripts/charte_bords.py")
        sys.exit(0 if ok else 1)
    for p in (SORTIE, COPIE):
        p.write_bytes(neuf.replace(b"\n", b"\r\n"))          # CRLF, comme les autres feuilles de /shared
    lignes = neuf.count(b"\n")
    print(f"écrit {SORTIE.relative_to(RACINE).as_posix()} (+ copie dist) : {lignes} lignes")


if __name__ == "__main__":
    main()
