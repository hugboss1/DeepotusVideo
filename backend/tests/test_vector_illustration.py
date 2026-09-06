"""Vectorlab — l'illustration IA : moteurs, modèles, et SVG rendu ÉDITABLE.

Trois remontées du 07/09/2026 : les moteurs doivent refléter TOUTES les clés
de l'utilisateur (ollama compris) ; le modèle doit se choisir ; l'illustration
doit être éditable et manipulable comme toute autre forme — ce qui exige que
les chemins sortent en M/L/C/Q/Z ABSOLUS (le `chemin_parser` du client ne lit
que cela) et que les autres balises deviennent des objets typés.

Aucun appel réseau : `tirer`, `catalogue` et `httpx` sont bouchonnés par
attribut de module. Le banc COMPTE les appels — un repli muet vers un autre
moteur se verrait.

Run: python -m pytest tests/test_vector_illustration.py -q
"""
import math
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import vector_illustration as VI  # noqa: E402


# ── la normalisation des chemins : ce qui rend l'illustration ÉDITABLE ──

def _cmds(d):
    return [t for t in d.split() if t.isalpha()]


def test_normalise_les_relatives_en_absolu():
    # `m` puis `h`/`v` : ce que les modèles écrivent le plus souvent
    assert VI.normaliser_chemin("m10 10 h20 v20 z") == "M 10 10 L 30 10 L 30 30 Z"
    # deux sous-chemins : le `z` ramène au départ du sous-chemin courant
    d = VI.normaliser_chemin("m0 0 l10 0 z m50 50 l10 0 z")
    assert d == "M 0 0 L 10 0 Z M 50 50 L 60 50 Z", d


def test_normalise_les_implicites_et_les_virgules():
    # après un M, les paires suivantes sont des L implicites (spec SVG)
    assert VI.normaliser_chemin("M0,0 10,0 10,10Z") == "M 0 0 L 10 0 L 10 10 Z"


def test_S_et_T_deviennent_C_et_Q_avec_le_bon_reflet():
    # S reflète le DERNIER point de contrôle : C1 1 2 2 3 3 → reflet de (2,2)
    # autour de (3,3) = (4,4)
    d = VI.normaliser_chemin("M0 0 C1 1 2 2 3 3 S4 4 5 5")
    assert d == "M 0 0 C 1 1 2 2 3 3 C 4 4 4 4 5 5", d
    # T reflète la poignée du Q précédent
    d2 = VI.normaliser_chemin("M0 0 Q2 2 4 0 T8 0")
    assert _cmds(d2) == ["M", "Q", "Q"], d2
    assert "6 -2" in d2, d2      # reflet de (2,2) autour de (4,0)


def test_les_arcs_deviennent_des_cubiques_qui_passent_par_le_bon_point():
    d = VI.normaliser_chemin("M50 10 A20 20 0 0 1 50 50 Z")
    assert _cmds(d) == ["M", "C", "C", "Z"], d
    # le dernier point du dernier C est l'arrivée demandée
    nb = [float(x) for x in d.replace("M", "").replace("C", "")
          .replace("Z", "").split()]
    assert abs(nb[-2] - 50) < 0.05 and abs(nb[-1] - 50) < 0.05, nb[-2:]
    # et le milieu de l'arc passe bien à droite (x = 70) : un demi-cercle,
    # pas une corde
    assert max(nb[0::2]) >= 69.5, d


def test_normalise_refuse_ce_qui_n_est_pas_un_chemin():
    for mauvais in ("", "pas un chemin", "L10 10", "   ", "42 42"):
        assert VI.normaliser_chemin(mauvais) == "", mauvais


def test_le_client_relit_ce_que_la_normalisation_ecrit():
    # invariant de couplage : la sortie n'emploie QUE M/L/C/Q/Z absolus,
    # le seul vocabulaire de `chemin_parser` (mod-doc.js)
    for src in ("m10 10 h20 v20 z", "M0 0 C1 1 2 2 3 3 S4 4 5 5",
                "M50 10 A20 20 0 0 1 50 50 Z", "M0 0 Q2 2 4 0 T8 0",
                "M0,0 10,0 10,10Z"):
        d = VI.normaliser_chemin(src)
        assert set(_cmds(d)) <= {"M", "L", "C", "Q", "Z"}, (src, d)
        assert d == d.strip() and "  " not in d, d


# ── les formes du SVG : pas seulement des <path> ──

def test_toutes_les_balises_du_9_deviennent_des_objets_types():
    svg = ('<svg viewBox="0 0 200 100">'
           '<path d="m5 5 h10 v10 z" fill="#1e56c8"/>'
           '<rect x="1" y="2" width="30" height="40" rx="3" fill="#c0202f"/>'
           '<circle cx="50" cy="50" r="20" fill="#1f7a3a"/>'
           '<ellipse cx="10" cy="20" rx="5" ry="8" fill="#d8b12a"/>'
           '<polygon points="0,0 10,0 10,10" fill="#7b3f9d"/>'
           '<path d="M0 0 L1 1" fill="none"/>'          # écarté : sans fond
           '<text x="0" y="0">bonjour</text>'           # écarté : hors liste
           '</svg>')
    formes, vb = VI.formes_du_svg(svg)
    assert vb == [0.0, 0.0, 200.0, 100.0], vb
    assert [f["type"] for f in formes] == \
        ["path", "rect", "ellipse", "ellipse", "path"], formes
    # le path relatif est sorti ABSOLU
    assert formes[0]["d"] == "M 5 5 L 15 5 L 15 15 Z", formes[0]
    # le rect garde son rayon, le cercle devient une ellipse ronde
    assert formes[1]["rx"] == 3 and formes[1]["w"] == 30
    assert formes[2]["rx"] == formes[2]["ry"] == 20
    # le polygone devient un chemin FERMÉ
    assert formes[4]["d"].endswith(" Z"), formes[4]
    # aucun contour, aucun style brut ne franchit le service
    assert all(set(f["style"]) <= {"fond", "contour", "epaisseur"}
               for f in formes), formes


def test_les_couleurs_hors_hexa_ne_sont_pas_devinees():
    svg = ('<svg viewBox="0 0 100 100">'
           '<path d="M0 0 L1 1 Z" fill="#ABC"/>'          # court → étendu
           '<path d="M0 0 L2 2 Z" style="fill:#123456"/>'  # dans le style
           '<path d="M0 0 L3 3 Z" fill="red"/>'            # nommée → défaut
           '<path d="M0 0 L4 4 Z"/>'                       # absente → défaut
           '</svg>')
    formes, _ = VI.formes_du_svg(svg)
    assert [f["style"]["fond"] for f in formes] == \
        ["#aabbcc", "#123456", VI.FOND_DEFAUT, VI.FOND_DEFAUT], formes


def test_le_svg_illisible_ou_vide_ne_rend_rien():
    # sans viewBox lisible, le repli documenté est 0 0 100 100
    for mauvais in ("", "je ne sais pas dessiner", "<svg><g></g></svg>"):
        formes, vb = VI.formes_du_svg(mauvais)
        assert formes == [], mauvais
        assert vb == [0.0, 0.0, 100.0, 100.0], mauvais
    # un viewBox VALIDE est rendu même si aucune forme n'est exploitable :
    # c'est le `d` qui est mauvais, pas le cadre
    formes, vb = VI.formes_du_svg("<svg viewBox='0 0 1 1'><path d='zz'/></svg>")
    assert formes == [] and vb == [0.0, 0.0, 1.0, 1.0], vb


def test_le_repli_par_expression_reguliere_quand_le_svg_est_tronque():
    # le modèle a bavardé et coupé la fermeture : le repli du §9 doit mordre
    txt = ('voici votre illustration :\n'
           '<path d="m0 0 h10 v10 z" fill="#1e56c8"/>\n'
           '<path d="M5 5 L9 9" fill="#c0202f"/>')
    formes, _ = VI.formes_du_svg(txt)
    assert [f["d"] for f in formes] == \
        ["M 0 0 L 10 0 L 10 10 Z", "M 5 5 L 9 9"], formes


def test_le_nombre_de_formes_est_borne():
    corps = "".join(f'<path d="M{i} 0 L1 1 Z" fill="#111111"/>'
                    for i in range(200))
    formes, _ = VI.formes_du_svg(f'<svg viewBox="0 0 10 10">{corps}</svg>')
    assert len(formes) == VI.MAX_FORMES, len(formes)


# ── les moteurs : TOUS ceux dont l'utilisateur a la clé ──

def test_les_quatre_moteurs_de_l_application_sont_connus():
    # ollama était absent de la première version (mesuré) alors que le reste
    # de l'application le connaît (marketing._PLAN_PRIORITY)
    assert VI.MOTEURS == ("anthropic", "openai", "gemini", "ollama")
    from app.services.marketing import _PLAN_PRIORITY
    assert list(VI.MOTEURS) == list(_PLAN_PRIORITY), _PLAN_PRIORITY


def test_le_catalogue_interroge_chaque_moteur_configure(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k-a", raising=False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "llama3", raising=False)
    monkeypatch.setattr(settings, "ANTHROPIC_MODEL", "claude-haiku-4-5",
                        raising=False)
    vus = []

    class Rep:
        status_code = 200

        def __init__(self, data):
            self._d = data

        def json(self):
            return self._d

    def faux_get(url, **kw):
        vus.append(url)
        if "anthropic" in url:
            return Rep({"data": [{"id": "claude-opus-5"},
                                 {"id": "claude-haiku-4-5"},
                                 {"id": "text-embedding-truc"}]})
        return Rep({"models": [{"name": "llama3"}, {"name": "mistral"}]})

    monkeypatch.setattr(VI.httpx, "get", faux_get)
    VI._CATALOGUE.clear()
    cat = VI.catalogue()
    assert [c["moteur"] for c in cat] == ["anthropic", "ollama"], cat
    # le modèle des Réglages est EN TÊTE, et les plongements sont écartés
    assert cat[0]["modeles"] == ["claude-haiku-4-5", "claude-opus-5"], cat[0]
    assert cat[1]["modeles"][0] == "llama3", cat[1]
    assert len(vus) == 2, vus            # un appel par moteur configuré, pas plus
    VI._CATALOGUE.clear()


def test_le_catalogue_survit_a_un_reseau_muet(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k-a", raising=False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "", raising=False)
    monkeypatch.setattr(settings, "ANTHROPIC_MODEL", "claude-haiku-4-5",
                        raising=False)

    def qui_leve(url, **kw):
        raise OSError("hors ligne")

    monkeypatch.setattr(VI.httpx, "get", qui_leve)
    VI._CATALOGUE.clear()
    cat = VI.catalogue()
    # l'écran reste utilisable : le modèle des Réglages, seul
    assert cat == [{"moteur": "anthropic", "modeles": ["claude-haiku-4-5"],
                    "defaut": "claude-haiku-4-5"}], cat
    VI._CATALOGUE.clear()


def test_tirer_vise_le_modele_demande_et_ne_se_replie_pas(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k-a", raising=False)
    envoye = {}

    class Rep:
        status_code = 200

        def json(self):
            return {"content": [{"type": "text", "text": "<svg/>"}]}

    def faux_post(url, **kw):
        envoye["url"] = url
        envoye["model"] = kw["json"]["model"]
        return Rep()

    monkeypatch.setattr(VI.httpx, "post", faux_post)
    out = VI.tirer("anthropic", "claude-opus-5", "dessine", "systeme")
    assert out == "<svg/>"
    assert envoye["model"] == "claude-opus-5", envoye
    assert "api.anthropic.com" in envoye["url"]

    # une réponse non-200 LÈVE avec la cause : pas de repli silencieux
    class Rate:
        status_code = 429
        text = "rate limited"

    monkeypatch.setattr(VI.httpx, "post", lambda url, **kw: Rate())
    try:
        VI.tirer("anthropic", "claude-opus-5", "dessine", "systeme")
        raise AssertionError("aurait dû lever")
    except RuntimeError as e:
        assert "429" in str(e), e


def test_la_consigne_redit_le_sujet_et_garde_le_format_du_handoff():
    c = VI.consigne("un poulpe stylisé")
    assert c.count("un poulpe stylisé") == 2, c      # au début ET à la fin
    assert 'viewBox="0 0 100 100"' in c
    assert "de 5 à 22 tracés" in c
    assert "RECONNAISSABLE" in c
