# -*- coding: utf-8 -*-
"""t331 — un FAUX mcp-for-blender en stdio pour le banc test_blender_pont : JSON-RPC 2.0 ligne par ligne, mêmes noms
d'outils et mêmes formes de réponse que mcp-for-blender 2.2.6. Bibliothèque standard seulement.

FAUX_JOURNAL : fichier JSONL où chaque message reçu (et l'environnement au démarrage) est écrit.
FAUX_MODE    : « ok » (défaut), « ferme » (l'add-on ne répond pas), « muet » (ne répond jamais à tools/call).
Avant chaque réponse à tools/call, le faux envoie une ligne qui n'est pas du JSON, une notification de journal et une
REQUÊTE du serveur (élicitation) : le client doit répondre -32601 et continuer."""
import base64
import json
import os
import sys

JOURNAL = os.environ.get("FAUX_JOURNAL") or ""
MODE = os.environ.get("FAUX_MODE") or "ok"
PNG = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360f8cfc0f01f0005000201a5c1"
    "e0c60000000049454e44ae426082")).decode("ascii")
PNG = os.environ.get("FAUX_PNG_B64") or PNG
OUTILS = ["disable_telemetry", "execute_blender_code", "generate_3d", "get_addon_status", "get_scene_info",
          "import_asset", "look", "record_trajectory_feedback", "search_assets"]
SCENE = ("Scene 'Scene' | 1 camera, 1 mesh | active Cube | selected none | mode OBJECT\n\n"
         "Showing 3 of 3 (name | type | location | size | hidden):\nCube | mesh | at (0.0, 0.0, 0.0)\n"
         "Camera | camera | at (4.0, -4.0, 1.4)\nChaise_Bois | empty | at (1.0, 0.0, 0.0)")
FERME = "Error getting scene info: Could not connect to Blender. Make sure the Blender addon is running."


def noter(x):
    if JOURNAL:
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


def ecrire(m):
    sys.stdout.write(json.dumps(m, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def texte(t, erreur=False):
    return {"content": [{"type": "text", "text": t}], "isError": erreur}


def outil(nom, a):
    if MODE == "ferme":
        return texte(FERME)
    if nom == "get_scene_info":
        return texte(SCENE)
    if nom == "look":
        return {"content": [{"type": "image", "data": PNG, "mimeType": "image/png"},
                            {"type": "text", "text": "Through camera 'Camera'. Framed 2 objects."}], "isError": False}
    if nom == "search_assets":
        if a.get("source") == "sketchfab":
            return texte("Found 1 models matching 'chair':\n\n- Chaise en bois (UID: abc123)\n  Author: Ana\n"
                         "  License: CC Attribution\n  Face count: 1200\n  Downloadable: Yes\n")
        return texte("Found 1 models (of 1 total) matching 'tree':\n\n- Tree (ID: pz9)\n  Author: Quaternius\n"
                     "  Licence: CC0\n  Tri count: 300\n")
    if nom == "import_asset":
        return texte("Successfully imported model.\nCreated objects: Chaise_Bois\n"
                     "Dimensions (X, Y, Z): 1.000 x 1.000 x 1.000 meters\n")
    if nom == "execute_blender_code":
        p = parametres(a.get("code") or "") or {}
        if p.get("elements") == ["lire"] or "maquette" in (p.get("elements") or []):
            return executer(p)
        return texte('Code executed successfully: DZBLENDER {"elements": ["camera"], "crees": ["DZ_Camera"], '
                     '"blocking": 0}\n')
    if nom == "generate_3d":
        return texte("Successfully generated and imported 'Coffre' (tripo).")
    return texte(f"Error: unknown tool {nom}", True)


def parametres(code):
    """t332 : le faux relit le JSON du gabarit comme le ferait Blender (le littéral unique de `P = json.loads(...)`)."""
    import ast
    try:
        arbre = ast.parse(code)
    except SyntaxError:
        return None
    for n in ast.walk(arbre):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "P":
            return json.loads(n.value.args[0].value)
    return None


# t332 : la scène relue par le gabarit de retour (FAUX_RETOUR la remplace ; FAUX_SANS_BLEND=1 : pas de copie .blend)
RETOUR = {"dz": "retour", "cameras": [
    {"nom": "DZ_Camera", "type": "PERSP", "capteur_l": 36.0, "capteur_h": 24.0, "ajuste": "VERTICAL", "active": True,
     "pos": [0.0, -5.0, 1.0], "visee": [0.0, 1.0, 0.0], "lens": 50.0,
     "cles": [{"pos": [0.0, -5.0, 1.0], "visee": [0.0, 1.0, 0.0], "lens": 50.0, "image": 1},
              {"pos": [1.0, -4.0, 1.5], "visee": [-0.2, 0.97, -0.1], "lens": 35.0, "image": 49}]},
    {"nom": "Camera", "type": "PERSP", "capteur_l": 36.0, "capteur_h": 24.0, "ajuste": "AUTO", "active": False,
     "pos": [7.0, -6.0, 5.0], "visee": [-0.6, 0.5, -0.4], "lens": 50.0, "cles": []}],
    "objets": [{"nom": "DZ_Camera", "type": "CAMERA", "pos": [0.0, -5.0, 1.0], "rot": [1.5708, 0.0, 0.0],
                "dims": [0.0, 0.0, 0.0], "cle": None},
               {"nom": "DZ_Maquette_Marie", "type": "MESH", "pos": [0.2, 0.0, 0.0], "rot": [0.0, 0.0, 0.0],
                "dims": [0.5, 0.4, 1.7], "cle": None}],
    "blend": True, "rendu": {"x": 1920, "y": 1080, "fps": 24.0}, "version": "5.2.0", "fichier": "atelier.blend"}


def executer(p):
    if p.get("elements") == ["lire"]:
        r = json.loads(os.environ.get("FAUX_RETOUR") or json.dumps(RETOUR))
        if p.get("blend") and os.environ.get("FAUX_SANS_BLEND") != "1":
            with open(p["blend"], "wb") as f:
                f.write(b"BLENDER-v502REND" + bytes(64))
        else:
            r["blend"] = False
        return texte("Code executed successfully: DZBLENDER " + json.dumps(r) + "\n")
    els = p.get("elements") or []
    crees = ["DZ_Camera"] if ("camera" in els or "cles" in els) else []
    glb = (p.get("maquette") or {}).get("glb") or ""
    if not os.path.isfile(glb):
        return texte("Error executing code: RuntimeError: glb absent", True)
    crees += ["DZ_Maquette_Marie", "DZ_Maquette_cypres"]
    return texte("Code executed successfully: DZBLENDER " + json.dumps({"elements": els, "crees": crees,
                                                                        "blocking": len(p.get("blocking") or [])}) + "\n")


def main():
    noter({"env": {k: os.environ.get(k) for k in ("DISABLE_TELEMETRY", "BLENDER_MCP_SAFE_MODE",
                                                  "BLENDERMCP_NO_UPDATE_CHECK", "BLENDER_HOST", "BLENDER_PORT")},
           "cles": sorted(k for k in os.environ if k.endswith(("_KEY", "_TOKEN")) or k.startswith("DEEPOTUS"))})
    for brut in sys.stdin:
        brut = brut.strip()
        if not brut:
            continue
        m = json.loads(brut)
        noter(m)
        meth, ident = m.get("method"), m.get("id")
        if meth is None or ident is None:
            continue
        if meth == "initialize":
            ecrire({"jsonrpc": "2.0", "id": ident, "result": {"protocolVersion": m["params"]["protocolVersion"],
                    "capabilities": {"tools": {}}, "serverInfo": {"name": "MCP for Blender", "version": "faux"}}})
        elif meth == "tools/list":
            ecrire({"jsonrpc": "2.0", "id": ident, "result": {"tools": [{"name": n, "inputSchema": {}} for n in OUTILS]}})
        elif meth == "tools/call":
            if MODE == "muet":
                continue
            sys.stdout.write("bavardage qui n'est pas du JSON\n")
            ecrire({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info", "data": "x"}})
            ecrire({"jsonrpc": "2.0", "id": "srv-1", "method": "elicitation/create", "params": {"message": "?"}})
            p = m.get("params") or {}
            ecrire({"jsonrpc": "2.0", "id": ident, "result": outil(p.get("name"), p.get("arguments") or {})})
        else:
            ecrire({"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "nope"}})


if __name__ == "__main__":
    main()
