"""Traduction L10 (t150, 12/10/2026) : les messages d'erreur du backend -> backend/app/i18n/erreurs.json.

  python scripts/i18n_l10_erreurs.py              réécrit erreurs.json depuis les sources + les traductions
  python scripts/i18n_l10_erreurs.py --check      code 1 si erreurs.json n'est pas à jour ou s'il manque une traduction
  python scripts/i18n_l10_erreurs.py --manquants F écrit dans F (JSON) les gabarits sources encore sans traduction

Décision de l'utilisateur (12/10) : traduire À LA SORTIE, sources intactes. Le générateur relit par AST tous les
modules de backend/app et prend le texte de chaque `HTTPException(code, detail)` et de chaque
`raise ValueError/RuntimeError/FileNotFoundError/PermissionError/LookupError/TimeoutError(message)` (ceux-là
remontent par `str(e)` dans un `detail`). Un littéral, une f-string ou une concaténation « texte » + expr devient un
GABARIT : les morceaux d'expression y sont des variables `{nom}` (« Source image not found: {fname} »).

Les traductions vivent dans scripts/i18n_l10_traductions.json, une entrée par gabarit SOURCE :
{"<gabarit tel qu'écrit dans le code>": {"fr": …, "en": …}} — l'un des deux côtés est le gabarit source lui-même
(c'est ce qui dit la langue du code), l'autre est la traduction, avec les MÊMES variables. erreurs.json en est le
produit : {"erreur.<sha1 10>": {"fr", "en", "src"}} trié par clé, lu par app/i18n/erreurs.py au moment de répondre.

Une traduction ORPHELINE (son gabarit n'est plus dans le code) fait échouer --check : elle se retire du fichier.
C'est le cas d'un message passé depuis par une clé de messages.json (`Message`/`Refus`, t192 G10, routes
`_msg_g`/`_txt_g`) : il n'est plus un littéral, il est rendu dans la langue de la requête AVANT ce gestionnaire,
et un seul mécanisme le traduit. Un gabarit sans texte fixe (f"{e}") ne se traduit pas et n'est pas retenu. EXEMPTS : les messages que le front
reconnaît à leur texte (atelier.js teste /Chapter not found/) — ils restent dans la langue du code.
Lancé avec le python embarqué ou n'importe quel Python 3.10+ (aucun import de l'application).
"""
import ast
import hashlib
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
APP = RACINE / "backend" / "app"
SORTIE = APP / "i18n" / "erreurs.json"
TRADUCTIONS = RACINE / "scripts" / "i18n_l10_traductions.json"
ERREURS = {"ValueError", "RuntimeError", "FileNotFoundError", "PermissionError", "LookupError", "TimeoutError",
           "ConflitClient", "FluxCoupe", "CoffreVerrouille"}   # t306 : ConflitClient = ValueError dédié (409 de POST /espaces/{id}) ;
                                       # L4.1 T3 : FluxCoupe = RuntimeError (flux Anthropic coupé)
EXEMPTS = {
    "Chapter not found",        # frontend/atelier/atelier.js : /Chapter not found/i.test(e.message) -> recrée le chapitre
    "Complete",                 # étape finale d'un job : le bundle (épisodes) teste current_step!=="Complete"
}
_VAR = re.compile(r"\{(\w+)\}")


def _nom_var(expr) -> str:
    """Un nom lisible pour la variable d'un morceau d'expression : fname, e, model… sinon v."""
    while isinstance(expr, ast.Call) and getattr(expr.func, "id", "") in ("str", "repr", "int", "float", "len",
                                                                          "round", "list", "sorted") and expr.args:
        expr = expr.args[0]
    if isinstance(expr, ast.Name):
        n = expr.id
    elif isinstance(expr, ast.Attribute):
        n = expr.attr
    elif isinstance(expr, ast.Subscript) and isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, str):
        n = expr.slice.value
    else:
        n = "v"
    n = re.sub(r"\W", "_", n.encode("ascii", "ignore").decode()).strip("_") or "v"
    return ("v_" + n) if n[0].isdigit() else n


def _morceaux(n):
    """Liste de morceaux ("t", texte) / ("v", expr) d'une expression de message, ou None si elle n'en est pas une."""
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return [("t", n.value)]
    if isinstance(n, ast.JoinedStr):
        out = []
        for v in n.values:
            if isinstance(v, ast.Constant):
                out.append(("t", str(v.value)))
            else:
                out.append(("v", v.value))
        return out
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        g, d = _morceaux(n.left), _morceaux(n.right)
        if g is None and d is None:
            return None
        return (g if g is not None else [("v", n.left)]) + (d if d is not None else [("v", n.right)])
    return None


def gabarit(n) -> str | None:
    ms = _morceaux(n)
    if ms is None:
        return None
    s, vus = "", {}
    for k, x in ms:
        if k == "t":
            s += x
        else:
            nom = _nom_var(x)
            vus[nom] = vus.get(nom, 0) + 1
            s += "{" + (nom if vus[nom] == 1 else f"{nom}{vus[nom]}") + "}"
    fixe = _VAR.sub("", s)
    if len(re.findall(r"[A-Za-zÀ-ÿ]", fixe)) < 4:
        return None
    return s


def extraire(app=APP) -> dict:
    """{gabarit source: [fichier:ligne, …]} pour tout le backend."""
    out: dict = {}
    for f in sorted(pathlib.Path(app).rglob("*.py")):
        try:
            arbre = ast.parse(f.read_text("utf-8"))
        except SyntaxError:
            continue
        rel = f.relative_to(RACINE).as_posix()
        for n in ast.walk(arbre):
            d = None
            if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) == "HTTPException":
                d = n.args[1] if len(n.args) > 1 else next((k.value for k in n.keywords if k.arg == "detail"), None)
            elif isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and n.exc.args and \
                    getattr(n.exc.func, "id", getattr(n.exc.func, "attr", "")) in ERREURS:
                d = n.exc.args[0]
            elif isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) == "_ignore" and n.args:
                d = n.args[0]   # t308 : une raison d'import (espaces_paquet._ignore) : gabarit `{variable}` déjà écrit
            if d is None:
                for d in etapes(n):
                    g = gabarit(d)
                    if g is not None and g not in EXEMPTS:
                        out.setdefault(g, []).append(f"{rel}:{n.lineno}")
                continue
            g = gabarit(d)
            if g is None or g in EXEMPTS:
                continue
            out.setdefault(g, []).append(f"{rel}:{n.lineno}")
    return out


def _branches(v):
    """Les deux branches d'un `a if c else b` (récursivement), sinon l'expression elle-même."""
    if isinstance(v, ast.IfExp):
        return _branches(v.body) + _branches(v.orelse)
    return [v]


def etapes(n) -> list:
    """Les expressions écrites dans `current_step` d'un job (décision G10 : l'étape est traduite avec L10) :
    `current_step=…` (appel), `x.current_step = …` (y compris `x.current_step, x.progress = …, …`) et
    `{"current_step": …}`. Une étape passée par une variable (le `label` d'un rappel de progression) n'est pas vue."""
    vals = []
    if isinstance(n, ast.Call):
        vals = [k.value for k in n.keywords if k.arg == "current_step"]
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Attribute) and t.attr == "current_step":
                vals.append(n.value)
            elif isinstance(t, ast.Tuple) and isinstance(n.value, ast.Tuple) and len(t.elts) == len(n.value.elts):
                vals += [v for c, v in zip(t.elts, n.value.elts)
                         if isinstance(c, ast.Attribute) and c.attr == "current_step"]
    elif isinstance(n, ast.Dict):
        vals = [v for k, v in zip(n.keys, n.values) if isinstance(k, ast.Constant) and k.value == "current_step"]
    return [b for v in vals for b in _branches(v)]


def cle(g: str) -> str:
    return "erreur." + hashlib.sha1(g.encode("utf-8")).hexdigest()[:10]


def produire(sources: dict, trad: dict) -> tuple[dict, list, list]:
    """(erreurs.json, gabarits sans traduction, traductions fautives)."""
    dico, manquants, fautes = {}, [], []
    for g in sources:
        t = trad.get(g)
        if not t or not t.get("fr") or not t.get("en"):
            manquants.append(g)
            continue
        if g not in (t["fr"], t["en"]):
            fautes.append((g, "aucun côté n'est le gabarit source"))
            continue
        if set(_VAR.findall(t["fr"])) != set(_VAR.findall(t["en"])):
            fautes.append((g, "variables différentes entre fr et en"))
            continue
        src = "fr" if t["fr"] == g else "en"
        dico[cle(g)] = {"fr": t["fr"], "en": t["en"], "src": src}
    return dict(sorted(dico.items())), manquants, fautes


def octets(dico: dict) -> bytes:
    lignes = [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in dico.items()]
    return ("{\n" + ",\n".join(lignes) + "\n}\n").encode("utf-8")


def main(argv):
    sources = extraire()
    trad = json.loads(TRADUCTIONS.read_text("utf-8")) if TRADUCTIONS.is_file() else {}
    dico, manquants, fautes = produire(sources, trad)
    if "--manquants" in argv:
        dest = pathlib.Path(argv[argv.index("--manquants") + 1])
        dest.write_text(json.dumps({g: sources[g][:3] for g in manquants}, ensure_ascii=False, indent=1), "utf-8")
        print(f"{len(manquants)} gabarit(s) sans traduction -> {dest}")
        return 0
    for g, pourquoi in fautes:
        print(f"FAUTE {pourquoi} : {g!r}")
    orphelins = sorted(set(trad) - set(sources))
    print(f"{len(sources)} gabarits, {len(dico)} traduits, {len(manquants)} sans traduction, "
          f"{len(fautes)} fautif(s), {len(orphelins)} traduction(s) orpheline(s)")
    attendu = octets(dico)
    if "--check" in argv:
        # core.autocrlf=true : une extraction réécrit erreurs.json en CRLF — la comparaison ignore les fins de ligne
        ok = not manquants and not fautes and not orphelins and SORTIE.is_file() \
            and SORTIE.read_bytes().replace(b"\r\n", b"\n") == attendu
        print("à jour" if ok else "PAS à jour")
        return 0 if ok else 1
    SORTIE.write_bytes(attendu)
    print(f"écrit {SORTIE.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
