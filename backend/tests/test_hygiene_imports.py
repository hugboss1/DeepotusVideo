"""Hygiène des imports — le NameError qui a coûté trois rendus seedance.

Le 27/08, `pipeline.run()` plantait à l'étape merge sur
`name 'asyncio' is not defined` : la passe sécurité/perf 43961b5 (06/08)
avait posé des `await asyncio.to_thread(...)` dans run() en s'appuyant sur
un import de module qui n'existait pas — quatre AUTRES méthodes portaient
un `import asyncio` LOCAL, ce qui masquait le trou. fal rendait et
facturait ; l'app marquait « failed » APRÈS téléchargement.

Ce banc parcourt tout backend/app à l'AST : chaque usage du nom `asyncio`
doit être couvert par un import de module OU un import local d'une
fonction englobante. Zéro faux positif possible : personne ne nomme une
variable `asyncio`.

Run: pytest tests/test_hygiene_imports.py -q
"""
import ast
import pathlib

RACINE = pathlib.Path(__file__).resolve().parent.parent / "app"


def _importe_asyncio(corps) -> bool:
    for n in corps:
        if isinstance(n, ast.Import) and any(a.name == "asyncio"
                                             for a in n.names):
            return True
        if isinstance(n, ast.ImportFrom) and n.module == "asyncio":
            return True
    return False


def test_tout_usage_d_asyncio_est_couvert_par_un_import():
    fautes = []
    for f in sorted(RACINE.rglob("*.py")):
        src = f.read_text("utf-8")
        if "asyncio" not in src:
            continue
        arbre = ast.parse(src, filename=str(f))
        module_ok = _importe_asyncio(arbre.body)

        class Visiteur(ast.NodeVisitor):
            def __init__(self):
                self.pile = [module_ok]

            def _fonction(self, n):
                self.pile.append(self.pile[-1] or _importe_asyncio(n.body))
                self.generic_visit(n)
                self.pile.pop()

            visit_FunctionDef = _fonction
            visit_AsyncFunctionDef = _fonction

            def visit_Name(self, n):
                if (n.id == "asyncio" and isinstance(n.ctx, ast.Load)
                        and not self.pile[-1]):
                    fautes.append(
                        f"{f.relative_to(RACINE.parent)}:{n.lineno}")

        Visiteur().visit(arbre)
    assert not fautes, ("usage d'asyncio SANS import couvrant (le NameError "
                        "du 27/08) : " + ", ".join(fautes[:12]))
