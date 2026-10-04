# -*- coding: utf-8 -*-
"""Card Forge — tâche #85 PR C (plan-cartes T11, 04/10/2026) : importer la table depuis Google Sheets et depuis un
export Notion.

DÉCISIONS DE L'UTILISATEUR (04/10) :
  * Notion = le ZIP d'EXPORT (« Exporter → Markdown & CSV »), aucune clé, aucun réseau. Il se dépose dans l'import
    de fichier EXISTANT : un zip qui porte des .csv (même imbriqué, comme Notion le fait pour les gros exports) et
    pas de classeur est lu comme un export Notion — la variante « _all.csv » (toutes les propriétés) d'abord.
  * Google Sheets = le LIEN d'une feuille partagée : seul https://docs.google.com est accepté, transformé en
    l'export CSV public (gratuit, sans clé), chaque redirection revérifiée (docs.google.com ou
    *.googleusercontent.com, https) ; une page de connexion (feuille non partagée) est DITE.
Le CSV de la feuille repasse par l'import EXISTANT (/parse) : un seul lecteur de tables.
Le plan appelait `parse_table(...)[:2]` : la fonction rend un DICT — vérifié.
Témoin positif : la base (6f77e3a3) n'a ni l'un ni l'autre.
Run : cd backend ; & $PY tests/test_cards_imports.py
"""
import asyncio
import base64
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cfimp_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
           "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[_k] = ""
os.environ["FAL_KEY"] = "test-key"
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

import httpx                                                     # noqa: E402
import pytest                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402

RACINE = _ICI.parent.parent
BASE = "6f77e3a3"


def test_temoin_la_base_n_a_ni_sheets_ni_notion():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/data.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert d and b"import-url" not in d and b"notion" not in d.lower()


# ─────────────────────────────── Notion ─────────────────────────────────────
def _zip(entrees: dict) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for nom, data in entrees.items():
            z.writestr(nom, data)
    return b.getvalue()


CSV_VUE = "\ufeffNom,Coût\nGobelin,2\nElfe,3\n".encode("utf-8")
CSV_ALL = "\ufeffNom,Coût,Rareté,Tags\nGobelin,2,commune,\"rapide, vert\"\nElfe,3,rare,\n".encode("utf-8")


def _parse(raw: bytes):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Imports"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/parse",
                                json={"b64": base64.b64encode(raw).decode("ascii"), "name": "export.zip"})
    return asyncio.run(go())


def test_un_export_notion_est_lu_variante_all_dabord():
    raw = _zip({"Cartes 1a2b3c.csv": CSV_VUE, "Cartes 1a2b3c_all.csv": CSV_ALL,
                "Cartes 1a2b3c/Gobelin 9f9f.md": b"# Gobelin\n"})
    r = _parse(raw)
    assert r.status_code == 200, r.text
    t = r.json()["table"]
    assert t["columns"] == ["Nom", "Coût", "Rareté", "Tags"], t["columns"]      # BOM retiré, toutes les propriétés
    assert t["rows"] == [["Gobelin", "2", "commune", "rapide, vert"], ["Elfe", "3", "rare", ""]]
    assert t["archive"] == "notion" and t["workbook"] is False
    assert any("Notion" in w and "Cartes 1a2b3c_all.csv" in w for w in t["warnings"]), t["warnings"]


def test_un_export_notion_imbrique_est_lu():
    interieur = _zip({"Cartes 1a2b3c_all.csv": CSV_ALL})
    raw = _zip({"Export-123/Part-1.zip": interieur, "Export-123/index.html": b"<html></html>"})
    r = _parse(raw)
    assert r.status_code == 200, r.text
    assert r.json()["table"]["n_rows"] == 2


def test_plusieurs_bases_la_plus_grande_et_les_autres_sont_nommees():
    petit = "Nom\nA\n".encode()
    # « Aaa » viendrait en premier par ordre alphabétique : c'est bien la TAILLE qui choisit
    raw = _zip({"Aaa regles 77aa.csv": petit, "Cartes 1a2b3c_all.csv": CSV_ALL, "Cartes 1a2b3c.csv": CSV_VUE})
    t = _parse(raw).json()["table"]
    assert t["columns"] == ["Nom", "Coût", "Rareté", "Tags"] and t["n_rows"] == 2, t["columns"]
    assert any("Aaa regles 77aa.csv" in w and "ignoré" in w for w in t["warnings"]), t["warnings"]


def test_un_zip_sans_csv_ni_classeur_le_dit():
    r = _parse(_zip({"page.md": b"# rien"}))
    assert r.status_code == 400 and "Notion" in r.text and "xl/workbook.xml" in r.text, r.text


def test_un_classeur_reste_un_classeur():
    x = _zip({"xl/workbook.xml": b"<workbook/>", "zz.csv": b"a\n1\n"})
    from app.services.cards import data as DA
    assert DA.notion_csv(x) is None


# ───────────────────────────── Google Sheets ────────────────────────────────
ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-xy"


def test_le_lien_devient_l_export_csv_et_rien_d_autre_n_est_accepte():
    from app.services.cards import data as DA
    assert DA.sheets_csv_url(f"https://docs.google.com/spreadsheets/d/{ID}/edit#gid=123") == \
        f"https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid=123"
    assert DA.sheets_csv_url(f"https://docs.google.com/spreadsheets/d/{ID}/edit?usp=sharing") == \
        f"https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid=0"
    assert DA.sheets_csv_url(f"https://docs.google.com/spreadsheets/d/e/2PACX-{ID}/pubhtml?gid=7") == \
        f"https://docs.google.com/spreadsheets/d/e/2PACX-{ID}/pub?output=csv&gid=7"
    for mauvais in (f"http://docs.google.com/spreadsheets/d/{ID}/edit", f"https://docs.google.com.evil.io/spreadsheets/d/{ID}/",
                    f"https://evil.io/spreadsheets/d/{ID}/", "https://docs.google.com/document/d/abc/edit",
                    f"https://user@docs.google.com/spreadsheets/d/{ID}/", "file:///C:/x.csv", ""):
        with pytest.raises(ValueError):
            DA.sheets_csv_url(mauvais)


ROUTES = {}


def _gestion(req):
    u = str(req.url)
    rep = ROUTES.get(u)
    if rep is None:
        return httpx.Response(404, text="?")
    return rep() if callable(rep) else rep


_Vrai = httpx.AsyncClient


class _Faux(_Vrai):
    def __init__(self, *a, **k):
        k.pop("verify", None)
        k["transport"] = httpx.MockTransport(_gestion)
        super().__init__(*a, **k)


def _importer(url):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Sheets"})
            did = r.json()["deck"]["id"]
            httpx.AsyncClient = _Faux
            try:
                return await c.post(f"/api/cards/{did}/data/import-url", json={"url": url})
            finally:
                httpx.AsyncClient = _Vrai
    return asyncio.run(go())


EXPORT = f"https://docs.google.com/spreadsheets/d/{ID}/export?format=csv&gid=0"
CONTENU = "https://doc-0s-1c-sheets.googleusercontent.com/export/abc?format=csv"


def test_la_feuille_partagee_est_rapatriee_en_csv_par_la_redirection_google():
    ROUTES.clear()
    ROUTES[EXPORT] = httpx.Response(307, headers={"location": CONTENU})
    ROUTES[CONTENU] = httpx.Response(200, content="Nom,Coût\nGobelin,2\n".encode("utf-8"),
                                     headers={"content-type": "text/csv; charset=utf-8",
                                              "content-disposition": "attachment; filename=\"Mon jeu - Cartes.csv\""})
    r = _importer(f"https://docs.google.com/spreadsheets/d/{ID}/edit?usp=sharing")
    assert r.status_code == 200, r.text
    j = r.json()
    assert base64.b64decode(j["b64"]).decode("utf-8") == "Nom,Coût\nGobelin,2\n"
    assert j["nom"] == "Mon jeu - Cartes.csv" and j["source"] == EXPORT and j["octets"] == len("Nom,Coût\nGobelin,2\n".encode())


def test_une_redirection_hors_de_google_est_refusee():
    ROUTES.clear()
    ROUTES[EXPORT] = httpx.Response(302, headers={"location": "https://evil.io/x.csv"})
    ROUTES["https://evil.io/x.csv"] = httpx.Response(200, text="a\n1\n", headers={"content-type": "text/csv"})
    r = _importer(EXPORT)
    assert r.status_code == 400 and "evil.io" in r.text, r.text
    ROUTES[EXPORT] = httpx.Response(302, headers={"location": "http://doc-0s.googleusercontent.com/x"})
    r = _importer(EXPORT)
    assert r.status_code == 400 and "https" in r.text, r.text
    for detour in ("https://moi@doc-0s.googleusercontent.com/x", "https://doc-0s.googleusercontent.com:8443/x"):
        ROUTES[EXPORT] = httpx.Response(302, headers={"location": detour})
        ROUTES[detour.replace("moi@", "")] = httpx.Response(200, text="a\n1\n", headers={"content-type": "text/csv"})
        r = _importer(EXPORT)
        assert r.status_code == 400 and "redirection refusée" in r.text, (detour, r.text)


def test_une_feuille_non_partagee_est_dite():
    ROUTES.clear()
    ROUTES[EXPORT] = httpx.Response(302, headers={"location": "https://accounts.google.com/ServiceLogin?x=1"})
    r = _importer(EXPORT)
    assert r.status_code == 400 and "partag" in r.text, r.text
    ROUTES[EXPORT] = httpx.Response(200, text="<!DOCTYPE html><html>Connexion</html>", headers={"content-type": "text/html"})
    r = _importer(EXPORT)
    assert r.status_code == 400 and "partag" in r.text, r.text
    ROUTES[EXPORT] = httpx.Response(404, text="nope")
    r = _importer(EXPORT)
    assert r.status_code == 400 and "404" in r.text, r.text


def test_trop_de_redirections_ou_trop_gros_est_refuse():
    ROUTES.clear()
    for k in range(10):
        ROUTES[f"https://doc-{k}.googleusercontent.com/x"] = httpx.Response(302, headers={"location": f"https://doc-{k + 1}.googleusercontent.com/x"})
    ROUTES[EXPORT] = httpx.Response(302, headers={"location": "https://doc-0.googleusercontent.com/x"})
    r = _importer(EXPORT)
    assert r.status_code == 400 and "redirection" in r.text, r.text
    from app.services.cards import data as DA
    ROUTES[EXPORT] = httpx.Response(200, content=b"a\n" * (DA.MAX_BYTES // 2 + 10), headers={"content-type": "text/csv"})
    r = _importer(EXPORT)
    assert r.status_code == 400 and "volumineu" in r.text, r.text


def test_un_lien_invalide_fait_400_sans_reseau():
    ROUTES.clear()
    r = _importer("https://evil.io/spreadsheets/d/x/")
    assert r.status_code == 400 and "docs.google.com" in r.text, r.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
