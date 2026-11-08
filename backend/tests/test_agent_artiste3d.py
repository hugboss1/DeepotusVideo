# -*- coding: utf-8 -*-
"""t441 (lot M8 « Méthodes », 08/11/2026) — l'agent métier ARTISTE 3D DE JEU et le rapport de poids web (« web3d »).

[W] rapport     GLB synthétiques (JSON + binaire, construits ici) : un petit modèle compressé (meshopt, WebP) dans le
                budget, sans conseil ; un lourd (6 Mo de texture PNG, 150 000 triangles, rien de compressé) hors
                budget avec les cinq conseils (poids, triangles, géométrie, part des textures, PNG) ;
                triangles MESURÉS dans les accesseurs ; budget personnalisé ; refus : pas un .glb, budget invalide, GLB
                illisible, hors données ;
[B] boîtes      l'Artiste 3D voit web3d, la boîte assets3d (pièces, budgets, comparatif, mouvement), méthodes et briques
                — exactement, lecture ; mcp garde assets3d et ne gagne pas web3d ; registre sain ;
[A] agent       disponible, « moteurs3d », rôle (un concept par objet, triangles mesurés, pièces nommées, poids web),
                ses méthodes ; un tour scripté appelle rapport_web_glb ; dépense « moteurs3d ».
Run : & $PY tests/test_agent_artiste3d.py   (depuis backend/)
"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import struct
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzart3d441_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def refus(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def glb(dest, triangles, image_octets=0, mime="image/png", extensions=()):
    """Un GLB minimal : un maillage de `triangles` triangles indexés, une image embarquée de `image_octets`."""
    n_idx, n_pos = triangles * 3, max(3, triangles + 2)
    idx_len, pos_len = n_idx * 4, n_pos * 12
    vues = [{"buffer": 0, "byteOffset": 0, "byteLength": idx_len},
            {"buffer": 0, "byteOffset": idx_len, "byteLength": pos_len}]
    doc = {"asset": {"version": "2.0", "generator": "banc t441"},
           "accessors": [{"bufferView": 0, "componentType": 5125, "count": n_idx, "type": "SCALAR"},
                         {"bufferView": 1, "componentType": 5126, "count": n_pos, "type": "VEC3",
                          "min": [0, 0, 0], "max": [1, 1, 1]}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0, "material": 0}]}],
           "materials": [{"pbrMetallicRoughness": {}}], "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}],
           "bufferViews": vues}
    total = idx_len + pos_len
    if image_octets:
        vues.append({"buffer": 0, "byteOffset": total, "byteLength": image_octets})
        doc["images"] = [{"bufferView": 2, "mimeType": mime}]
        doc["textures"] = [{"source": 0}]
        doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
        total += image_octets
    if extensions:
        doc["extensionsUsed"] = list(extensions)
    doc["buffers"] = [{"byteLength": total}]
    js = json.dumps(doc).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    binaire = bytes(total) + bytes((4 - total % 4) % 4)
    corps = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binaire), 0x004E4942) + binaire
    pathlib.Path(dest).write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + len(corps)) + corps)


def main():
    R = pathlib.Path(_tmp)
    M = R / "medias"
    M.mkdir()
    glb(M / "petit.glb", 2000, 50_000, "image/webp", ("EXT_meshopt_compression", "EXT_texture_webp"))
    glb(M / "lourd.glb", 150_000, 6_000_000, "image/png")
    (M / "faux.glb").write_bytes(b"pas un glb du tout, vraiment pas")
    (M / "x.obj").write_text("v 0 0 0", "utf-8")
    dehors = pathlib.Path(tempfile.mkdtemp(prefix="dzdehors_")) / "d.glb"
    glb(dehors, 10)
    from app.services import web3d_qc as W

    print("[W] rapport")
    r = W.rapport("medias/petit.glb")
    check("W1 petit compressé : 2 000 triangles mesurés, meshopt + WebP vus, dans le budget, aucun conseil",
          r["triangles"] == 2000 and r["compression_geometrie"] == ["EXT_meshopt_compression"]
          and r["compression_textures"] == ["EXT_texture_webp"] and r["dans_le_budget"] and not r["conseils"], r)
    r = W.rapport("medias/lourd.glb")
    c = " | ".join(r["conseils"])
    check("W2 lourd : hors budget, cinq conseils (poids, triangles, géométrie, part des textures, PNG), textures 62 %",
          not r["dans_le_budget"] and r["triangles"] == 150_000 and "Mo > budget" in c and "triangles > budget" in c
          and "meshopt" in c and "PNG" in c and "WebP ou KTX2" in c and len(r["conseils"]) == 5
          and abs(r["part_textures"] - 0.625) < 0.01 and r["textures"] == 1, r["conseils"])
    r = W.rapport("medias/lourd.glb", 20, 200_000)
    check("W3 budget personnalisé (20 Mo, 200 000) : dans le budget, restent les conseils de compression",
          r["dans_le_budget"] and not any("budget" in x for x in r["conseils"]) and r["conseils"], r["conseils"])
    check("W4 refus : pas un .glb, budget invalide, GLB illisible, hors données",
          refus(W.rapport, "medias/x.obj") and refus(W.rapport, "medias/petit.glb", -1)
          and refus(W.rapport, "medias/petit.glb", "beaucoup") and refus(W.rapport, "medias/faux.glb")
          and refus(W.rapport, str(dehors)))

    print("\n[B] boîtes")
    from app.services import agent_boites as B
    from app.services import agent_outils as ao
    from app.services import agent_metier as AM
    o = set(B.outils_pour("artiste_3d"))
    attendu = {"rapport_web_glb", "pieces_analyser", "budgets_triangles", "comparatif3d_lire", "mouvement_lire",
               "methodes_lire", "mesurer_sortie", "comparer_sorties", "ancres_lire", "ancre_verifier", "registre_lire", "arbitrer_sorties"}
    check("B1 web3d + assets3d + méthodes + briques — exactement, lecture", o == attendu
          and all(ao.OUTILS[x]["nature"] == "lecture" for x in o), sorted(o ^ attendu))
    check("B2 mcp garde assets3d et ne gagne pas web3d ; registre sain", "pieces_analyser" in B.outils_pour("mcp")
          and "rapport_web_glb" not in B.outils_pour("mcp") and B.verifier() == [], B.verifier())

    print("\n[A] agent")
    from app.config import settings
    from app.services import moteurs_texte as MT
    s = AM.systeme("artiste_3d")
    ag = {x["id"]: x for x in AM.agents()}
    check("A1 disponible, « moteurs3d », rôle, ses méthodes (mech-bay, little-lights), pas celles des autres",
          ag["artiste_3d"]["disponible"] and AM.ACTIFS["artiste_3d"]["categorie"] == "moteurs3d"
          and "**mesurés**" in s and "pièces nommées" in s and "mech-bay" in s and "little-lights" in s
          and "iso-cycles" not in s)
    settings.ANTHROPIC_API_KEY = "sk-ant-cle-de-banc"
    SCRIPT = [{"blocs": [{"type": "tool_use", "id": "t1", "name": "rapport_web_glb",
                          "input": {"chemin": "medias/lourd.glb"}}], "arret": "tool_use", "in_tok": 300, "out_tok": 30},
              {"blocs": [{"type": "text", "text": "Passe les textures en WebP et compresse avec meshopt."}],
               "arret": "end_turn", "in_tok": 500, "out_tok": 20}]
    MT.converser = lambda *a, **k: SCRIPT.pop(0)
    conv = AM.creer("artiste_3d", "", "little-lights")
    loop = asyncio.new_event_loop()
    r = loop.run_until_complete(AM.message("artiste_3d", conv["id"], "Mon modèle est-il assez léger ?", max_usd=1))
    loop.close()
    check("A2 rapport_web_glb exécuté (hors budget), réponse rangée", r["outils"][0]["ok"]
          and "hors budget" in r["outils"][0]["resume"] and "WebP" in r["texte"], r)
    dep = sqlite3.connect(str(R / "t.db")).execute("SELECT DISTINCT categorie FROM depenses").fetchall()
    check("A3 dépenses dans la catégorie « moteurs3d »", dep == [("moteurs3d",)], dep)

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if code else 0)
