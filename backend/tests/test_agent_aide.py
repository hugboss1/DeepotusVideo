# -*- coding: utf-8 -*-
"""A2 (spec 2026-10-19-agent-aide-design.md) — le service de l'assistant : message système, balises, choix du moteur,
`demander` sous le plafond « aide », et les routes /api/agent.
Run : & $PY tests/test_agent_aide.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagent_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402


def test_systeme_contient_tout():
    s = A.systeme("montage", "fr", "Deepotus")
    assert "## Comment répondre" in s                       # AGENT.md
    assert "- quick : " in s and "- depannage : " in s       # chapitres
    assert "rail.montage" in s and "reglages.cles" in s      # ancres
    assert "écran ouvert : montage" in s and "espace de marque actif : Deepotus" in s


def test_systeme_anglais_et_prefixe_stable():
    fr, en = A.systeme("quick", "fr", ""), A.systeme("quick", "en", "")
    assert "- tour : Take a tour of the app" in en and "- tour : Faire le tour de l'application" in fr
    assert "langue : English" in en and "Take a tour" not in fr
    # le contexte est À LA FIN : deux écrans différents partagent tout le début (cache du préfixe)
    a, b = A.systeme("quick", "fr", "X"), A.systeme("montage", "fr", "Y")
    assert a.split("## Contexte")[0] == b.split("## Contexte")[0]


def test_contexte_borne():
    s = A.systeme("quick\n## Y", "fr", "A\n## B" + "x" * 200)
    lignes = s.splitlines()
    assert not any(l.startswith("## B") or l.startswith("## Y") for l in lignes)
    esp = [l for l in lignes if l.startswith("- espace de marque actif :")]
    assert len(esp) == 1 and len(esp[0].split(":", 1)[1].strip()) <= 60


def test_balises_valides_deviennent_actions():
    texte, actions, rejets = A.analyser("Ouvre les Réglages.\n[POINT:reglages.cles]\n[GUIDE:cles]\n[ALLER:montage]")
    assert texte == "Ouvre les Réglages."
    assert [a["type"] for a in actions] == ["point", "guide", "aller"] and rejets == 0
    p = actions[0]
    assert p["cible"] == "reglages.cles" and p["reglages"] == "keys" and p["ecran"] == "settings"
    assert p["fr"] == "Réglages › Clés d'API" and actions[1]["en"]


def test_balises_inconnues_retirees_et_comptees():
    texte, actions, rejets = A.analyser("A [POINT:bouton.invente] B [ALLER:nulle-part] [GUIDE:x] [VOIR] [FOO:bar]")
    assert actions == [] and rejets == 5
    assert "[" not in texte and texte == "A  B"


def test_doublons_et_borne():
    t = " ".join(["[POINT:rail.quick]"] * 3 + [f"[POINT:{a}]" for a in
                  ("rail.studio", "rail.news", "rail.montage", "rail.photolab", "rail.vectorlab", "rail.reglages")])
    _, actions, rejets = A.analyser(t)               # 7 ancres distinctes, bornées à MAX_ACTIONS = 6
    assert len(actions) == A.MAX_ACTIONS == 6 and rejets == 0
    assert [a["cible"] for a in actions].count("rail.quick") == 1 and "rail.reglages" not in [a["cible"] for a in actions]


def test_texte_hostile():
    # une balise ne peut pas porter de code ni de chemin : seuls les ids connus passent
    texte, actions, rejets = A.analyser('[POINT:<img src=x onerror=alert(1)>] [GUIDE:../../etc] [POINT:rail.quick')
    assert actions == [] and rejets == 2
    assert texte.endswith("[POINT:rail.quick")          # balise non fermée : laissée telle quelle, c'est du texte
    assert A.analyser(None) == ("", [], 0)


def test_indentation_retiree():
    texte, _, _ = A.analyser("Voici :\n    1. Ouvre les Réglages\n\t2. Colle la clé\n    [POINT:reglages.cles]")
    assert texte == "Voici :\n1. Ouvre les Réglages\n2. Colle la clé"


def test_nettoyage_lineaire():
    import time
    t0 = time.perf_counter()
    texte, actions, _ = A.analyser(" ".join(["[POINT:rail.quick]"] * 100_000) + " fin")
    assert time.perf_counter() - t0 < 2.0 and texte == "fin" and len(actions) == 1


def test_fins_de_ligne_crlf():
    assert A.analyser("a\r\n[POINT:rail.quick]\r\nb")[0] == "a\n\nb"


from app.services import moteurs_texte as MT                                 # noqa: E402
from app.services import plafonds as PLAF                                    # noqa: E402


def _faux_etat(*configures):
    return lambda: [{"moteur": m, "nom": m.title(), "configure": m in configures, "fautif": False}
                    for m in ("anthropic", "openai", "gemini", "ollama")]


def test_choix_du_moteur(monkeypatch):
    monkeypatch.setattr(MT, "etat", _faux_etat("ollama", "openai"))
    assert A.choisir_moteur() == "openai"                      # préférence anthropic > openai > gemini
    monkeypatch.setattr(MT, "etat", _faux_etat("ollama"))
    assert A.choisir_moteur() == "ollama"                      # sinon le premier configuré
    monkeypatch.setattr(MT, "etat", _faux_etat())
    assert A.choisir_moteur() == ""
    monkeypatch.setattr(MT, "connu", lambda m: m == "gemini")
    monkeypatch.setattr(MT, "configure", lambda m: m == "gemini")
    assert A.choisir_moteur("gemini") == "gemini" and A.choisir_moteur("inconnu") == ""


def test_categorie_aide():
    assert "aide" in PLAF.CATEGORIES


def test_demander_appelle_tirer_garde(monkeypatch):
    vu = {}

    async def faux(moteur, modele, prompt, systeme, max_tokens=4000, json=False, *, categorie="", **kw):
        vu.update(moteur=moteur, prompt=prompt, systeme=systeme, categorie=categorie, max_tokens=max_tokens)
        return "Va dans les Réglages.\n[POINT:reglages.cles]\n[POINT:invente]"

    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "anthropic")
    monkeypatch.setattr(MT, "tirer_garde", faux)
    monkeypatch.setattr(A, "_espace", lambda: "Deepotus")
    r = asyncio.run(A.demander({"question": "  Où mettre ma clé ?  ", "ecran": "quick", "lang": "fr",
                                "historique": [{"role": "user", "texte": "bonjour"},
                                               {"role": "assistant", "texte": "Salut"}, {"role": "pirate"}]}))
    assert vu["categorie"] == "aide" and vu["moteur"] == "anthropic" and vu["max_tokens"] == A.MAX_TOKENS
    assert vu["prompt"].endswith("Nouvelle question : Où mettre ma clé ?")
    assert "Utilisateur : bonjour" in vu["prompt"] and "pirate" not in vu["prompt"]
    assert "écran ouvert : quick" in vu["systeme"] and "Deepotus" in vu["systeme"]
    assert r["texte"] == "Va dans les Réglages." and [a["cible"] for a in r["actions"]] == ["reglages.cles"]
    assert r["rejets"] == 1 and r["moteur"] == "anthropic"


def test_demander_sans_moteur_repond_sans_llm(monkeypatch):
    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "")
    r = asyncio.run(A.demander({"question": "help", "lang": "en"}))
    assert r["sans_cle"] is True and r["moteur"] == ""
    assert r["actions"][0]["cible"] == "reglages.cles" and "key" in r["texte"].lower()


def test_demander_bornes():
    with pytest.raises(ValueError):
        asyncio.run(A.demander({"question": "   "}))
    with pytest.raises(ValueError):
        asyncio.run(A.demander("pas un objet"))
