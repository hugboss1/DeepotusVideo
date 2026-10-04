# -*- coding: utf-8 -*-
"""Recensement AST des routes qui DÉPENSENT (tâche #16, 29/09/2026) — partagé par test_plafonds_garde.

Une route « atteint un puits » quand son corps, ou une fonction du MÊME module qu'il appelle (fermeture transitive,
fonctions imbriquées comprises), appelle un des PUITS : les points de sortie vers un fournisseur payant, relevés le
29/09 dans le code (fal, OpenAI/Anthropic, ElevenLabs, HeyGen, Meshy, transcription). Une route « est gardée » quand
la même fermeture appelle `_plafond(...)` ou `<plafonds>.verifier(...)`.
Les puits sont des NOMS d'appel (dernier attribut) : grossier mais sans faux négatif sur les idiomes du dépôt."""
import ast
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[1] / "app"

MODULES = {
    "routes": RACINE / "api" / "routes.py",
    "dictation": RACINE / "services" / "dictation_service.py",
    "montage": RACINE / "services" / "montage_service.py",
    "face": RACINE / "services" / "cards" / "face.py",
    "capture": RACINE / "services" / "cards" / "capture.py",
    "forge3d": RACINE / "services" / "cards" / "forge3d.py",
    "data": RACINE / "services" / "cards" / "data.py",   # tâche #86 : la traduction des cartes (LLM)
}

PUITS = {
    # images / fal
    "_flux_generate", "subscribe_async", "_generate_image_core", "_process_image_core", "_tirer_banana_pro",
    "_rembg_fal", "upload_image",
    "_tirer_lot",   # cards/data : l'art du deck en lot -> image_providers.generate (tâche #87)
    # LLM
    "_chat_dispatch", "generate_script_from_intent", "generate_composition_from_intent", "propose_styles",
    "generate_plan", "plan_from_document", "_ai_scenes", "_ai_shots", "summarize_items", "build_news_script",
    "tirer", "translate", "identite", "enrich_items",
    "classer",   # news_rank.classer(llm=True) -> _chat_dispatch (tâche #33)
    "polir",     # news_chain.polir -> rewrite_script, le polissage LLM (tâche #35)
    "run_extend",   # pipeline.run_extend -> fal Veo 3.1 extend (tâche #51)
    # voix / son
    "generate_music", "generate_sfx", "_generate_scene_vo", "generate_long", "generate_sprites",
    # transcription
    "transcribe",
    # vidéo / HeyGen (`pipeline.run` en nom pointé : `run` seul attraperait subprocess.run)
    "pipeline.run", "pipeline.render_template", "run_heygen", "run_heygen_image", "run_heygen_cinematic", "run_composition", "run_episode", "run_batch",
    "create_photo_avatar",
    # 3D
    "proxy_request", "texturer_asset3d", "generate_asset3d", "refine_asset3d", "_run_mesh3d",
    "_run_manuscript_job", "_run_adapt_job", "_run_bible_model3d",
}
GARDES = {"_plafond", "_PLAF.verifier"}   # `verifier` nu est ambigu (cards/face : `sw.verifier` de la fiche de style)


def _nom_appel(n: ast.Call) -> str:
    f = n.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _pointe(n: ast.Call) -> str:
    f = n.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f.value.id + "." + f.attr
    return ""


def _chemin(dec) -> tuple | None:
    if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in
            ("post", "put", "patch", "delete", "api_route") and dec.args and isinstance(dec.args[0], ast.Constant)):
        if dec.func.attr == "api_route":      # le proxy Meshy : GET/POST/DELETE sur une seule fonction
            return "ROUTE", dec.args[0].value
        return dec.func.attr.upper(), dec.args[0].value
    return None


def _appels(noeud) -> set:
    """Noms appelés dans le noeud ; les fonctions PASSÉES en argument (to_thread(f), add_task(f)) comptent aussi."""
    out = set()
    for n in ast.walk(noeud):
        if isinstance(n, ast.Call):
            out.add(_nom_appel(n))
            out.add(_pointe(n))
            for a in list(n.args) + [k.value for k in n.keywords]:
                if isinstance(a, ast.Name):
                    out.add(a.id)
                elif isinstance(a, ast.Attribute):
                    out.add(a.attr)
    return out


def analyser(cle: str, source: str | None = None) -> dict:
    """{(MÉTHODE, chemin): {"fonction", "puits": set, "garde": bool}} pour un module."""
    arbre = ast.parse(source if source is not None else MODULES[cle].read_text(encoding="utf-8"))
    fonctions = {n.name: n for n in arbre.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    appels = {nom: _appels(f) for nom, f in fonctions.items()}

    def fermeture(nom):
        vus, pile, noms = {nom}, [nom], set()
        while pile:
            for a in appels.get(pile.pop(), ()):
                noms.add(a)
                if a in fonctions and a not in vus:
                    vus.add(a)
                    pile.append(a)
        return noms

    out = {}
    for nom, f in fonctions.items():
        for dec in f.decorator_list:
            c = _chemin(dec)
            if c:
                ferme = fermeture(nom)
                out[c] = {"fonction": nom, "puits": ferme & PUITS, "garde": bool(ferme & GARDES)}
    return out


def recenser(sources: dict | None = None) -> dict:
    """{(module, MÉTHODE, chemin): info} sur tous les modules."""
    out = {}
    for cle in MODULES:
        for (m, p), info in analyser(cle, (sources or {}).get(cle)).items():
            out[(cle, m, p)] = info
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for k, v in sorted(recenser().items()):
        if v["puits"] or v["garde"]:
            print(("G " if v["garde"] else "- ") + " ".join(k), sorted(v["puits"]))
