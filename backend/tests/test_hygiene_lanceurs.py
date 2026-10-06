"""Hygiène des lanceurs de bancs (01/10/2026).

Constat du jour : 47 fichiers tests/test_*.py de style pytest n'avaient pas de
lanceur `if __name__ == "__main__"`. Lancés en autonome (`python tests/x.py`),
ils sortaient 0 SANS EXÉCUTER UN SEUL TEST, et la série par fichier les voyait
verts — trois bancs y ont dérivé en silence depuis le 20/09. À l'inverse, onze
scripts appelaient leurs tests en tête de module : sous pytest, la collecte les
exécutait une première fois, pytest une seconde (UNIQUE, réglages mutés), et
leurs `async def test_` y étaient rouges faute de greffon asyncio.

La règle, vérifiée par AST sur CHAQUE fichier qui définit un `test_` au niveau
module :
  1. un bloc `if __name__ == "__main__":` existe (le mode autonome exécute) ;
  2. aucun `async def test_` au niveau module (pytest ne sait pas l'attendre) ;
  3. aucun appel de test, d'`asyncio.run`, de `main()` ni de sortie au niveau
     module hors de ce bloc (pas de double exécution à la collecte).

Chaque règle a son témoin : `_fautes` est éprouvée sur des sources fautives
qui DOIVENT être relevées, et un vrai sous-processus prouve qu'un test rouge
fait sortir le lanceur non-zéro.
"""
import ast
import pathlib
import subprocess
import sys
import tempfile
import textwrap

TESTS = pathlib.Path(__file__).resolve().parent


def _est_main(n):
    return isinstance(n, ast.If) and "__main__" in ast.unparse(n.test)


def _tests_du_module(t):
    return [n for n in t.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("test_")]


def _fautes(src):
    t = ast.parse(src)
    defs = _tests_du_module(t)
    if not defs:
        return []
    fautes = []
    if not any(_est_main(n) for n in t.body):
        fautes.append("pas de lanceur if __name__ == '__main__'")
    for n in defs:
        if isinstance(n, ast.AsyncFunctionDef):
            fautes.append(f"async def {n.name} au niveau module")
    for n in t.body:
        if isinstance(n, ast.Raise):
            fautes.append(f"sortie au niveau module l.{n.lineno}")
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
            f = ast.unparse(n.value.func)
            if (f.startswith("test_") or f in ("asyncio.run", "main",
                                              "sys.exit", "exit")):
                fautes.append(f"appel {f}() au niveau module l.{n.lineno}")
    return fautes


def test_chaque_banc_pytest_a_son_lanceur_et_rien_en_tete_de_module():
    vus, fautifs = 0, {}
    for p in sorted(TESTS.glob("test_*.py")):
        src = p.read_text("utf-8")
        if not _tests_du_module(ast.parse(src)):
            continue
        vus += 1
        f = _fautes(src)
        if f:
            fautifs[p.name] = f
    assert fautifs == {}
    # témoin positif : la règle a bien porté sur la population du 01/10
    # (37 pytest purs + 12 scripts convertis + 20 déjà lancés + celui-ci = 70)
    assert vus >= 70, vus


def test_la_regle_releve_chaque_faute_temoins():
    assert _fautes("x = 1\n") == []                     # pas de test : hors champ
    sain = ("import asyncio\n"
            "async def _s():\n    pass\n"
            "def test_a():\n    asyncio.run(_s())\n"
            "if __name__ == '__main__':\n    test_a()\n")
    assert _fautes(sain) == []
    assert _fautes("def test_a():\n    pass\n") == [
        "pas de lanceur if __name__ == '__main__'"]
    assert _fautes(sain + "async def test_b():\n    pass\n") == [
        "async def test_b au niveau module"]
    assert _fautes(sain + "test_a()\n") == ["appel test_a() au niveau module l.8"]
    assert _fautes(sain + "asyncio.run(_s())\n") == [
        "appel asyncio.run() au niveau module l.8"]
    assert _fautes(sain + "import sys\nsys.exit(0)\n") == [
        "appel sys.exit() au niveau module l.9"]
    assert _fautes(sain + "raise SystemExit(0)\n") == [
        "sortie au niveau module l.8"]


# ── règle 4 (06/10/2026) : le chemin du backend AVANT `import app` ──────────
# Constat du jour : test_material_truth.py passait sous pytest (21 verts) et
# mourait en autonome sur `ModuleNotFoundError: No module named 'app'` à sa
# ligne 43. Sous pytest, backend/conftest.py pose le dossier backend dans
# sys.path avant la collecte ; en autonome, le python embarqué ignore
# PYTHONPATH et son ._pth n'ajoute pas le dossier du script : le module
# s'exécute de haut en bas comme __main__ et l'import `app` de tête casse
# avant d'atteindre le lanceur. Les règles 1-3 ne regardaient que le lanceur.
#
# La règle : si une instruction de niveau module importe `app` (hors corps de
# fonction, que pytest n'exécute qu'après conftest), une instruction de niveau
# module ANTÉRIEURE pose un chemin dans sys.path (insert, append ou [:0]).

def _importe_app(n):
    if isinstance(n, ast.Import):
        return any(a.name == "app" or a.name.startswith("app.") for a in n.names)
    if isinstance(n, ast.ImportFrom):
        m = n.module or ""
        return n.level == 0 and (m == "app" or m.startswith("app."))
    return False


def _hors_fonctions(n):
    """Les nœuds exécutés à l'import : on ne descend pas dans def/lambda."""
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return
    pile = [n]
    while pile:
        x = pile.pop()
        yield x
        pile.extend(c for c in ast.iter_child_nodes(x)
                    if not isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.Lambda)))


def _lignes_chemin(n):
    return [x.lineno for x in _hors_fonctions(n)
            if isinstance(x, (ast.Call, ast.Assign))
            and any(k in ast.unparse(x)
                    for k in ("path.insert", "path.append", "path[:0]"))]


def _fautes_chemin(src):
    pose = False
    for n in ast.parse(src).body:
        if _est_main(n):
            continue                        # le lanceur s'exécute en dernier
        chemins = _lignes_chemin(n)
        imports = [x.lineno for x in _hors_fonctions(n) if _importe_app(x)]
        # dans une même instruction (try: insert ; import), l'ordre des lignes
        # tranche : test_montage_edition.py l.1593 pose puis importe
        if imports and not pose and not (chemins and min(chemins) < min(imports)):
            return [f"import app l.{min(imports)} avant sys.path.insert"]
        pose = pose or bool(chemins)
    return []


def test_chaque_banc_pose_le_chemin_du_backend_avant_import_app():
    vus, fautifs = 0, {}
    for p in sorted(TESTS.glob("test_*.py")):
        src = p.read_text("utf-8")
        if any(_importe_app(x) for n in ast.parse(src).body
               if not _est_main(n) for x in _hors_fonctions(n)):
            vus += 1
        f = _fautes_chemin(src)
        if f:
            fautifs[p.name] = f
    assert fautifs == {}
    # témoin positif : la règle a porté sur les bancs qui importent app en tête
    # (212 sur 308 fichiers le 06/10)
    assert vus >= 200, vus


def test_la_regle_du_chemin_releve_chaque_faute_temoins():
    pose = "import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\n"
    assert _fautes_chemin("import json\n") == []          # pas d'app : hors champ
    assert _fautes_chemin(pose + "import app.services.x as X\n") == []
    assert _fautes_chemin(pose + "from app.main import app\n") == []
    assert _fautes_chemin("import sys\nsys.path.append('..')\nimport app\n") == []
    assert _fautes_chemin("import sys\nsys.path[:0] = ['..']\nimport app\n") == []
    # le cas du 06/10 : import de tête sans chemin
    assert _fautes_chemin("import json\nimport app.services.x as X\n") == [
        "import app l.2 avant sys.path.insert"]
    assert _fautes_chemin("from app.services import y\n") == [
        "import app l.1 avant sys.path.insert"]
    # le chemin posé APRÈS l'import ne rattrape rien
    assert _fautes_chemin("import app\n" + pose) == [
        "import app l.1 avant sys.path.insert"]
    # import de tête caché dans un try : exécuté à l'import, donc relevé
    assert _fautes_chemin("try:\n    import app\nexcept ImportError:\n    pass\n") == [
        "import app l.2 avant sys.path.insert"]
    # même instruction, chemin posé d'abord (forme de test_montage_edition.py)
    assert _fautes_chemin("import sys\ntry:\n    sys.path.insert(0, '..')\n"
                          "    import app\nexcept ImportError:\n    pass\n") == []
    # un chemin posé dans une fonction ne s'exécute pas à l'import
    assert _fautes_chemin("import sys\ndef f():\n    sys.path.insert(0, '..')\n"
                          "import app\n") == ["import app l.4 avant sys.path.insert"]
    # hors champ : import dans une fonction (conftest l'a précédé sous pytest),
    # dans le lanceur, homonymes (`apply`, `.app` relatif)
    assert _fautes_chemin("def test_a():\n    import app\n") == []
    assert _fautes_chemin("if __name__ == '__main__':\n    import app\n") == []
    assert _fautes_chemin("import apply\nfrom .app import x\n") == []


def _lancer(corps):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d, "test_temoin.py")
        p.write_text(textwrap.dedent(corps) + textwrap.dedent('''
            if __name__ == "__main__":
                import pytest
                raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
            '''), "utf-8")
        return subprocess.run([sys.executable, str(p)], cwd=d,
                              capture_output=True, text=True).returncode


def test_le_lanceur_sort_non_zero_quand_un_banc_rougit():
    assert _lancer("def test_vert():\n    assert True\n") == 0
    assert _lancer("def test_rouge():\n    assert 1 == 2\n") == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
