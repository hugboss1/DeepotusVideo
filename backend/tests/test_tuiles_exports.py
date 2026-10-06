# -*- coding: utf-8 -*-
"""Tuiles — exports Tiled `.tsx`, LDtk `.ldtk`, Godot `.tres` (plan 2026-09-03-plan-tuiles T3-T5, tâche t114).

BANC-MIROIR : chaque fichier ÉCRIT est relu comme son consommateur le lirait — le `.tsx` par `xml.etree`, le
`.ldtk` contre le SCHÉMA OFFICIEL de LDtk (copie datée `ldtk_schema_1.5.3.json`, téléchargée le 06/10/2026 de
https://ldtk.io/files/JSON_SCHEMA.json), le `.tres` ligne à ligne. Jamais le code qui prétend les produire.

TROIS ÉCARTS AU PLAN (03/09), mesurés le 06/10 avant d'écrire :
  * TILED : le plan n'écrivait pas `type` sur <wangset> (la doc TMX ne le liste pas). Le CODE de Tiled, lui, l'écrit
    toujours, et le lit `mixed` quand il manque (`wangSetTypeFromString`, wangset.cpp). Juste pour blob47 par
    chance ; FAUX pour blob16, dont les coins « fond » dans un jeu lu « mixed » ne correspondraient plus à rien au
    milieu d'un terrain. Ici : `mixed` (blob47) ou `edge` (blob16, coins à 0 = inutilisés).
  * LDTK : la liste de champs requis du plan était périmée — le schéma 1.5.3 exige désormais `tileRandomX/YMin/Max`
    et `tileX/YOffset` sur chaque règle, et ne requiert plus `tileIds` (déprécié). D'où la validation contre le
    schéma lui-même plutôt qu'une liste recopiée. Et blob16 : 16 règles, coins ignorés (le plan figeait 47).
  * GODOT : blob16 = `MATCH_SIDES` (mode 2), pas `MATCH_CORNERS_AND_SIDES` (0) que le plan figeait.

Run: python tests/test_tuiles_exports.py   (depuis backend/ ; un processus par fichier)
"""
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

_tmp = tempfile.mkdtemp(prefix="dztuilesx_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
BASE = "94ca301d"
SCHEMA = json.loads((ICI / "ldtk_schema_1.5.3.json").read_text("utf-8"))


def test_temoin_la_base_n_a_ni_module_ni_route():
    assert subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/tile_export.py"],
                          capture_output=True, cwd=str(RACINE)).returncode != 0
    r = subprocess.run(["git", "show", f"{BASE}:backend/app/services/tiles_api.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert r and b"/export" not in r


# ── le jeu et sa méta, tels que creer_jeu les range ─────────────────────────────────────────────────────────────────
def _matiere(seed):
    im = Image.new("RGB", (64, 64), (30 + 40 * seed, 60, 90))
    ImageDraw.Draw(im).ellipse([8, 8, 40, 40], fill=(200, 30 * seed % 255, 40))
    return im


def _meta(jeu_nom="blob47", variantes=1, cote=32):
    from app.services import tile_ops as TO
    jeu = TO.assembler_jeu(_matiere(1), _matiere(2), jeu_nom, cote, variantes)
    _img, colonnes, rangees = TO.atlas(jeu)
    return {"nom": "banc", "jeu": jeu_nom, "cles": jeu["cles"], "cote": cote, "variantes": jeu["variantes"],
            "tuiles": len(jeu["tuiles"]), "vide": jeu["vide"], "colonnes": colonnes, "rangees": rangees}


def _dossier():
    return pathlib.Path(tempfile.mkdtemp(dir=_tmp))


# ── TILED ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_tsx_blob47_relu_par_xml_etree():
    from app.services import tile_export as TE
    from app.services import tile_ops as TO
    meta = _meta("blob47", variantes=2)
    p = TE.ecrire_tsx(_dossier(), meta)
    assert p.name == "tileset.tsx"
    r = ET.parse(p).getroot()
    assert r.tag == "tileset" and r.get("firstgid") is None, "un .tsx externe n'a pas de firstgid"
    assert (r.get("tilewidth"), r.get("tileheight"), r.get("tilecount"), r.get("columns")) == ("32", "32", "95", "8")
    img = r.find("image")
    assert (img.get("source"), img.get("width"), img.get("height")) == ("atlas.png", "256", str(meta["rangees"] * 32))
    assert r.find("grid") is None, "pas de <grid> pour un jeu carré"
    ws = r.find("wangsets/wangset")
    assert ws is not None and ws.get("type") == "mixed", "le type que Tiled ÉCRIT, et qu'il lit « mixed » s'il manque"
    assert [c.get("name") for c in ws.findall("wangcolor")] == ["terrain", "fond"]
    par_id = {int(t.get("tileid")): t.get("wangid") for t in ws.findall("wangtile")}
    assert set(par_id) == set(range(95))
    for i, m in enumerate(meta["cles"]):              # l'ordre du wangid = la numérotation du plan, bit à bit
        attendu = ",".join("1" if m & b else "2" for b in TO.BITS)
        assert par_id[2 * i] == par_id[2 * i + 1] == attendu, m
    assert par_id[meta["vide"]] == "2,2,2,2,2,2,2,2"
    assert par_id[2 * meta["cles"].index(255)] == "1,1,1,1,1,1,1,1"
    proba = {int(t.get("id")): t.get("probability") for t in r.findall("tile")}
    assert len(proba) == 94 and set(proba.values()) == {"0.5"}, "les variantes d'un voisinage se partagent le tirage"


def test_tsx_blob16_est_un_jeu_d_ARETES_aux_coins_inutilises():
    from app.services import tile_export as TE
    from app.services import tile_ops as TO
    meta = _meta("blob16")
    r = ET.parse(TE.ecrire_tsx(_dossier(), meta)).getroot()
    ws = r.find("wangsets/wangset")
    assert ws.get("type") == "edge"
    par_id = {int(t.get("tileid")): t.get("wangid").split(",") for t in ws.findall("wangtile")}
    assert len(par_id) == 17 and r.get("columns") == "4"
    for i, m in enumerate(meta["cles"]):
        w = par_id[i]
        assert [w[k] for k in (1, 3, 5, 7)] == ["0"] * 4, "les coins d'un jeu d'arêtes valent 0"
        assert [w[k] for k in (0, 2, 4, 6)] == ["1" if m & b else "2" for b in (TO.N, TO.E, TO.S, TO.W)]
    assert {t.get("probability") for t in r.findall("tile")} == {"1"}


# ── LDTK ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _valider(valeur, schema, chemin="$"):
    """Validateur JSON Schema réduit aux mots-clés QUE le schéma LDtk emploie (relevé le 06/10 : type, properties,
    required, additionalProperties, items, enum, $ref, oneOf) — `jsonschema` n'est pas dans le runtime embarqué."""
    if "$ref" in schema:
        cible = SCHEMA
        for part in schema["$ref"].lstrip("#/").split("/"):
            cible = cible[part]
        return _valider(valeur, cible, chemin)
    if "oneOf" in schema:
        erreurs = [e for s in schema["oneOf"] for e in [_valider(valeur, s, chemin)]]
        return [] if any(not e for e in erreurs) else [f"{chemin} : aucune branche de oneOf"]
    out = []
    types = schema.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        ok = {"object": isinstance(valeur, dict), "array": isinstance(valeur, list),
              "string": isinstance(valeur, str), "boolean": isinstance(valeur, bool), "null": valeur is None,
              "integer": isinstance(valeur, int) and not isinstance(valeur, bool),
              "number": isinstance(valeur, (int, float)) and not isinstance(valeur, bool)}
        if not any(ok.get(t, False) for t in types):
            return [f"{chemin} : type {type(valeur).__name__}, attendu {types}"]
    if "enum" in schema and valeur not in schema["enum"]:
        out.append(f"{chemin} : {valeur!r} hors {schema['enum']}")
    if isinstance(valeur, dict):
        props = schema.get("properties", {})
        out += [f"{chemin} : champ requis absent « {k} »" for k in schema.get("required", []) if k not in valeur]
        for k, v in valeur.items():
            if k in props:
                out += _valider(v, props[k], f"{chemin}.{k}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{chemin} : champ inconnu « {k} »")
    if isinstance(valeur, list) and "items" in schema:
        for i, v in enumerate(valeur):
            out += _valider(v, schema["items"], f"{chemin}[{i}]")
    return out


def test_le_validateur_du_banc_mord_temoins():
    assert _valider({"a": 1}, {"type": ["object"], "required": ["a", "b"]}) == ["$ : champ requis absent « b »"]
    assert _valider("x", {"type": ["integer"]}) and _valider(True, {"type": ["integer"]})
    assert _valider("Nope", {"enum": ["None", "Horizontal"]})
    assert _valider([1, "x"], {"items": {"type": ["integer"]}}) == ["$[1] : type str, attendu ['integer']"]
    assert not _valider(None, {"type": ["integer", "null"]})


@pytest.mark.parametrize("jeu_nom,variantes", [("blob47", 3), ("blob16", 1)])
def test_le_ldtk_ecrit_est_VALIDE_contre_le_schema_officiel(jeu_nom, variantes):
    from app.services import tile_export as TE
    meta = _meta(jeu_nom, variantes, cote=16)
    p = TE.ecrire_ldtk(_dossier(), meta)
    assert p.name == "projet.ldtk"
    doc = json.loads(p.read_text("utf-8"))
    assert _valider(doc, SCHEMA) == []
    assert doc["jsonVersion"] == SCHEMA["version"] == "1.5.3"
    ts = doc["defs"]["tilesets"][0]
    assert (ts["relPath"], ts["identifier"], ts["tileGridSize"], ts["__cWid"], ts["__cHei"], ts["pxWid"]) == (
        "atlas.png", "Banc", 16, meta["colonnes"], meta["rangees"], meta["colonnes"] * 16)
    couche = doc["defs"]["layers"][0]
    assert couche["__type"] == couche["type"] == "IntGrid" and couche["tilesetDefUid"] == ts["uid"]
    assert [v["value"] for v in couche["intGridValues"]] == [1]
    regles = couche["autoRuleGroups"][0]["rules"]
    assert len(regles) == len(meta["cles"]) and len({r["uid"] for r in regles}) == len(regles)
    for r in regles:
        assert r["size"] == 3 and r["pattern"][4] == 1 and r["tileMode"] == "Single" and r["breakOnMatch"] is True
        assert len(r["tileRectsIds"]) == variantes and all(len(x) == 1 for x in r["tileRectsIds"])


@pytest.mark.parametrize("jeu_nom", ["blob47", "blob16"])
def test_chaque_voisinage_satisfait_EXACTEMENT_une_regle_et_la_bonne(jeu_nom):
    """Sémantique CITÉE du code de LDtk (AutoLayerRuleDef.hx) : 0 ignore la case, v exige v, −v exclut v. Éprouvée sur
    les 256 voisinages d'une case pleine."""
    from app.services import tile_export as TE
    from app.services import tile_ops as TO
    meta = _meta(jeu_nom, cote=16)
    regles = json.loads(TE.ecrire_ldtk(_dossier(), meta).read_text("utf-8"))["defs"]["layers"][0][
        "autoRuleGroups"][0]["rules"]
    ordre = ((0, TO.NW), (1, TO.N), (2, TO.NE), (3, TO.W), (5, TO.E), (6, TO.SW), (7, TO.S), (8, TO.SE))

    def satisfait(motif, vois):
        for i, bit in ordre:
            v, a = (1 if vois & bit else 0), motif[i]
            if (a > 0 and v != a) or (a < 0 and v == -a):
                return False
        return motif[4] == 1

    for vois in range(256):
        gagnantes = [r for r in regles if satisfait(r["pattern"], vois)]
        assert len(gagnantes) == 1, (vois, len(gagnantes))
        assert gagnantes[0]["tileRectsIds"][0][0] == TO.index_de(vois, jeu_nom), vois


# ── GODOT ────────────────────────────────────────────────────────────────────────────────────────────────────────────
NOMS_GODOT = ("top_side", "top_right_corner", "right_side", "bottom_right_corner", "bottom_side",
              "bottom_left_corner", "left_side", "top_left_corner")


def _lignes(p):
    return [l.rstrip() for l in p.read_text("utf-8").splitlines()]


def test_tres_blob47_relu_ligne_a_ligne():
    from app.services import tile_export as TE
    from app.services import tile_ops as TO
    meta = _meta("blob47", variantes=2)
    p = TE.ecrire_tres(_dossier(), meta)
    assert p.name == "tileset.tres"
    L = _lignes(p)
    assert L[0] == '[gd_resource type="TileSet" format=3]'
    for attendu in ('[ext_resource type="Texture2D" path="res://atlas.png" id="1"]',
                    '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_dz0"]',
                    'texture = ExtResource("1")', "texture_region_size = Vector2i(32, 32)", "[resource]",
                    "tile_size = Vector2i(32, 32)", "terrain_set_0/mode = 0", 'terrain_set_0/terrain_0/name = "terrain"',
                    'sources/0 = SubResource("TileSetAtlasSource_dz0")'):
        assert attendu in L, attendu
    assert "tile_shape" not in "\n".join(L), "carré : tile_shape par défaut"
    col = meta["colonnes"]
    for i, m in enumerate(meta["cles"]):
        for k in range(2):
            n = 2 * i + k
            x, y = n % col, n // col
            assert f"{x}:{y}/0 = 0" in L and f"{x}:{y}/0/terrain = 0" in L
            for bit, nom in zip(TO.BITS, NOMS_GODOT):
                assert (f"{x}:{y}/0/terrains_peering_bit/{nom} = 0" in L) == bool(m & bit), (m, nom)
    xv, yv = meta["vide"] % col, meta["vide"] // col
    assert f"{xv}:{yv}/0 = 0" in L and f"{xv}:{yv}/0/terrain = 0" not in L, "la VIDE : sans terrain (absent = -1)"
    assert len([l for l in L if l.endswith("/0 = 0")]) == meta["tuiles"]


def test_tres_blob16_assortit_les_COTES_seulement():
    from app.services import tile_export as TE
    meta = _meta("blob16")
    L = _lignes(TE.ecrire_tres(_dossier(), meta))
    assert "terrain_set_0/mode = 2" in L, "MATCH_SIDES"
    assert not [l for l in L if "_corner = " in l], "aucun bit de coin dans un jeu d'arêtes"
    assert len([l for l in L if l.endswith("/0 = 0")]) == 17


# ── FORMES (t115, plan T8) ───────────────────────────────────────────────────────────────────────────────────────────
def _meta_forme(forme):
    from app.services import tile_ops as TO
    jeu = TO.assembler_forme(_matiere(1), forme, 64 if forme == "iso" else 32)
    return {"nom": forme, "jeu": "forme", "forme": forme, "cles": [255], "cote": jeu["cote"],
            "largeur": jeu["largeur"], "hauteur": jeu["hauteur"], "variantes": 1, "tuiles": 1, "vide": None,
            "colonnes": 1, "rangees": 1}


def test_exports_de_forme_disent_ce_qu_ils_portent():
    from app.services import tile_export as TE
    meta_iso = _meta_forme("iso")
    r = ET.parse(TE.ecrire_tsx(_dossier(), meta_iso)).getroot()
    g = r.find("grid")
    assert g is not None and g.get("orientation") == "isometric"
    assert g.get("width") == "128" and g.get("height") == "64"
    assert r.get("tilewidth") == "128" and r.get("tileheight") == "64" and r.get("tilecount") == "1"
    assert r.find("image").get("width") == "128" and r.find("image").get("height") == "64"
    # UNE tuile, sans jeu Wang : aucun identifiant ne sort de l'atlas d'une case
    assert r.find("wangsets") is None
    assert all(t.get("id") == "0" for t in r.iter("tile"))
    L = _lignes(TE.ecrire_tres(_dossier(), meta_iso))
    assert "tile_shape = 1" in L and "tile_layout = 5" in L
    assert "tile_size = Vector2i(128, 64)" in L and "texture_region_size = Vector2i(128, 64)" in L
    assert [l for l in L if l.endswith("/0 = 0")] == ["0:0/0 = 0"], "une seule tuile, dans l'atlas"
    assert not [l for l in L if "terrain" in l], "pas de terrain pour une tuile seule"

    meta_hex = _meta_forme("hex")
    r2 = ET.parse(TE.ecrire_tsx(_dossier(), meta_hex)).getroot()
    # l'orientation hexagonale est un attribut de <map>, PAS de <tileset>
    assert r2.find("grid") is None
    assert r2.get("tilewidth") == "64" and r2.get("tileheight") == "56"
    L2 = _lignes(TE.ecrire_tres(_dossier(), meta_hex))
    assert "tile_shape = 3" in L2 and "tile_offset_axis = 1" in L2
    assert "tile_size = Vector2i(64, 56)" in L2
    assert not [l for l in L2 if l.startswith("tile_layout")]
    assert [l for l in L2 if l.endswith("/0 = 0")] == ["0:0/0 = 0"]

    for meta in (meta_iso, meta_hex):
        with pytest.raises(ValueError, match="(?i)orthogonal"):
            TE.ecrire_ldtk(_dossier(), meta)


def test_un_jeu_carre_ne_porte_toujours_ni_grid_ni_tile_shape():
    """Témoin de non-régression : la branche de forme ne déborde pas sur le carré."""
    from app.services import tile_export as TE
    meta = _meta("blob47")
    r = ET.parse(TE.ecrire_tsx(_dossier(), meta)).getroot()
    assert r.find("grid") is None and r.find("wangsets") is not None
    L = _lignes(TE.ecrire_tres(_dossier(), meta))
    assert not [l for l in L if l.startswith(("tile_shape", "tile_layout", "tile_offset_axis"))]


# ── LA ROUTE ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _appels(requetes):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db

    async def main():
        await init_db()
        out = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            for m, p, corps in requetes:
                r = await c.request(m, p, json=corps)
                out.append((r.status_code, r.json() if r.headers.get("content-type", "").startswith(
                    "application/json") else r.content))
        return out
    return asyncio.run(main())


def test_la_route_ecrit_les_trois_fichiers_dans_le_dossier_du_jeu_et_les_sert():
    from app.config import settings
    from app.services import tile_store as TS
    for n, s in (("mat_a.png", 1), ("mat_b.png", 2)):
        _matiere(s).save(settings.images_path / n)
    (s, meta), = _appels([("POST", "/api/tiles/jeu", {"matiere_a": {"image": "mat_a.png"},
                                                      "matiere_b": {"image": "mat_b.png"}, "cote": 32})])
    assert s == 200, meta
    tid = meta["tid"]
    r = _appels([("POST", f"/api/tiles/{tid}/export", {"format": f}) for f in ("tiled", "ldtk", "godot")]
                + [("GET", f"/api/tiles/{tid}/fichier/projet.ldtk", None)])
    assert [x[0] for x in r] == [200, 200, 200, 200], r
    assert [x[1]["fichier"] for x in r[:3]] == ["tileset.tsx", "projet.ldtk", "tileset.tres"]
    for x in r[:3]:
        p = TS.tileset_dir(tid) / x[1]["fichier"]
        assert p.is_file() and x[1]["octets"] == p.stat().st_size and x[1]["url"].endswith(x[1]["fichier"])
    assert _valider(json.loads(r[3][1]), SCHEMA) == [], "le fichier SERVI est valide"
    refus = _appels([("POST", f"/api/tiles/{tid}/export", {"format": "unity"}),
                     ("POST", f"/api/tiles/{tid}/export", {}),
                     ("POST", "/api/tiles/tile_00000000/export", {"format": "tiled"}),
                     ("POST", "/api/tiles/..%2Fx/export", {"format": "tiled"})])
    # `..%2Fx` ne correspond même pas à la route (405) : un refus, et rien n'est écrit hors du dossier du jeu
    assert [x[0] for x in refus][:3] == [400, 400, 404] and refus[3][0] in (400, 404, 405), refus
    assert sorted(p.name for p in TS.tilesets_root().rglob("*.tsx")) == ["tileset.tsx"]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
