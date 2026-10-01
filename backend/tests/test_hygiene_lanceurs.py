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
