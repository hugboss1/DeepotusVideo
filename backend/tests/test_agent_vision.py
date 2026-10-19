# -*- coding: utf-8 -*-
"""A5 (spec 2026-10-19-agent-aide-design.md § 2 « Vision en secours ») — l'assistant regarde l'écran : balises
[VOIR] et [POINT:x,y:libellé], devis gratuit, second appel avec capture et montant accepté, routes /api/agent.
Run : & $PY tests/test_agent_vision.py   (depuis backend/)"""
import asyncio, base64, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagentvue_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402
from app.services import moteurs_texte as MT                                # noqa: E402

JPG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()
IMAGE = {"mime": "image/jpeg", "b64": JPG, "largeur": 1280, "hauteur": 720}


def test_voir_devient_une_action():
    texte, actions, rejets = A.analyser("Je ne connais pas ce bouton.\n[VOIR]")
    assert texte == "Je ne connais pas ce bouton." and rejets == 0
    assert actions == [{"type": "voir", "cible": "ecran"}]
    assert A.analyser("[VOIR:quoi]")[1] == [] and A.analyser("[VOIR:quoi]")[2] == 1    # VOIR ne prend pas de cible


def test_point_xy_seulement_avec_une_capture():
    dims = {"largeur": 1280, "hauteur": 720}
    _, actions, rejets = A.analyser("Ici.\n[POINT:640,360:Générer]", dims)
    assert rejets == 0 and actions == [{"type": "point_xy", "cible": "640,360", "x": 640, "y": 360,
                                        "largeur": 1280, "hauteur": 720, "libelle": "Générer"}]
    assert A.analyser("[POINT:640,360:Générer]") == ("", [], 1)              # sans capture : refusé
    assert A.analyser("[POINT:1280,10:x]", dims)[2] == 1                     # hors de la capture (bornes strictes)
    assert A.analyser("[POINT:1279,719:x]", dims)[2] == 0
    assert A.analyser("[POINT:10, 20]", dims)[1][0]["libelle"] == ""         # libellé facultatif, espaces tolérés
    assert A.analyser("[POINT:reglages.cles]", dims)[1][0]["type"] == "point"   # une ancre reste une ancre
    assert A.analyser("[VOIR]", dims) == ("", [], 1)                         # pas de seconde capture en boucle


def test_point_xy_libelle_borne_et_sans_code():
    dims = {"largeur": 1280, "hauteur": 720}
    a = A.analyser("[POINT:1,2:" + "<b>x</b>\t" * 8 + "]", dims)[1][0]   # 76 car. : sous la borne de 80 de BALISE
    assert len(a["libelle"]) <= 60 and "\t" not in a["libelle"]
    b = A.analyser("[POINT:1,2:Gé\u202enérer\u200b]", dims)[1][0]
    assert b["libelle"] == "Générer"                                     # contrôle et format Unicode retirés


def _moteur(monkeypatch, voit=True):
    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "anthropic")
    monkeypatch.setattr(A, "_espace", lambda: "")
    monkeypatch.setattr(MT, "vision", lambda m, mod=None: voit)


def test_devis_gratuit_et_stable(monkeypatch):
    _moteur(monkeypatch)
    corps = {"question": "Où est le bouton qui exporte ?", "lang": "fr", "moteur": "anthropic"}
    d1 = A.estimer_vue(corps)
    assert d1["moteur"] == "anthropic" and d1["vision"] is True and d1["cout"] == "payant" and d1["usd"] > 0
    d2 = A.estimer_vue(dict(corps, image=IMAGE))            # une image jointe au devis est ignorée
    assert d2["usd"] == d1["usd"]


def test_devis_sans_moteur(monkeypatch):
    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "")
    assert A.estimer_vue({"question": "q"}) == {"moteur": "", "nom": "", "usd": 0.0, "cout": "", "vision": False}


def test_demander_avec_capture(monkeypatch):
    _moteur(monkeypatch)
    vu = {}

    async def faux(moteur, modele, prompt, systeme, max_tokens=4000, json=False, *, categorie="", **kw):
        vu.update(prompt=prompt, systeme=systeme, images=kw.get("images"), categorie=categorie)
        return "C'est ce bouton.\n[POINT:100,50:Exporter]"
    monkeypatch.setattr(MT, "tirer_garde", faux)
    corps = {"question": "Où est le bouton qui exporte ?", "lang": "fr", "moteur": "anthropic"}
    usd = A.estimer_vue(corps)["usd"]
    r = asyncio.run(A.demander(dict(corps, image=IMAGE, max_usd=usd)))
    assert vu["images"] == [{"mime": "image/jpeg", "b64": JPG}] and vu["categorie"] == "aide"
    assert "1280×720" in vu["prompt"] and "[POINT:x,y:libellé]" in vu["prompt"]
    assert vu["systeme"] == A.systeme("", "fr", "")            # le préfixe système ne change pas (cache)
    assert r["actions"][0]["type"] == "point_xy" and r["actions"][0]["libelle"] == "Exporter"


def test_demander_capture_refusee(monkeypatch):
    _moteur(monkeypatch, voit=False)
    corps = {"question": "q", "image": IMAGE, "max_usd": 1.0}
    with pytest.raises(ValueError):
        asyncio.run(A.demander(corps))                        # moteur aveugle
    _moteur(monkeypatch)
    for mauvais in ({"max_usd": None}, {"max_usd": -1}, {"max_usd": float("nan")}, {"max_usd": True},
                     {"max_usd": 10 ** 400}):
        with pytest.raises(ValueError):
            asyncio.run(A.demander(dict(corps, **mauvais)))
    for image in ({**IMAGE, "largeur": 5000}, {**IMAGE, "mime": "image/gif"}, {**IMAGE, "b64": "%%%"}, "x"):
        with pytest.raises(ValueError):
            asyncio.run(A.demander(dict(corps, image=image)))
    with pytest.raises(A.CoutChange):
        asyncio.run(A.demander(dict(corps, max_usd=0.0)))      # coût recalculé > accepté : rien n'est envoyé


def test_etat_dit_quels_moteurs_voient(monkeypatch):
    monkeypatch.setattr(MT, "etat", lambda: [{"moteur": m, "nom": m, "configure": True, "fautif": False}
                                              for m in ("anthropic", "ollama")])
    monkeypatch.setattr(MT, "vision", lambda m, mod=None: m == "anthropic")
    j = A.etat()
    assert {m["moteur"]: m["vision"] for m in j["moteurs"]} == {"anthropic": True, "ollama": False}


from fastapi.testclient import TestClient                                   # noqa: E402


def _client():
    from app.main import app
    return TestClient(app)


def test_route_estimer(monkeypatch):
    monkeypatch.setattr(A, "estimer_vue", lambda corps, lang="fr": {"moteur": "x", "usd": 0.01, "lang": lang})
    c = _client()
    r = c.post("/api/agent/estimer", json={"question": "q"}, headers={"Accept-Language": "en"})
    assert r.status_code == 200 and r.json()["lang"] == "en"
    assert c.post("/api/agent/estimer", content="pas du json",
                  headers={"Content-Type": "application/json"}).status_code == 400


def test_route_demander_cout_change_409(monkeypatch):
    async def change(corps, lang="fr"):
        raise A.CoutChange()
    monkeypatch.setattr(A, "demander", change)
    r = _client().post("/api/agent/demander", json={"question": "q"})
    assert r.status_code == 409 and "accord" in r.json()["detail"]


def test_route_demander_trop_lourde():
    r = _client().post("/api/agent/demander", content=b"{" + b" " * 8_000_001 + b"}",
                       headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_messages_traduits():
    import json, subprocess
    racine = pathlib.Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, str(racine / "scripts" / "i18n_l10_erreurs.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(racine),
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-800:]
    t = json.loads((racine / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
    assert "Image jointe illisible." in t and "Demande trop lourde." in t


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
