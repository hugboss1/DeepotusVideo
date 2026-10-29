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
    "avatar_live": RACINE / "api" / "avatar_live_routes.py",   # t161 : le Direct (Decart Lucy 2.5)
    "photolab": RACINE / "api" / "photolab_routes.py",   # t191 : calque IA et détourage du Photolab (fal, OpenAI)
    "agent": RACINE / "api" / "agent_routes.py",   # A6 : la lecture de l'assistant (ElevenLabs, ou Voicebox gratuit)
    "audio_graph": RACINE / "api" / "audio_graph_routes.py",   # t272 : les nœuds IA de l'Atelier sonore (fal)
    "post": RACINE / "api" / "post_routes.py",   # t277 : les générateurs IA de la pile de post-traitement
    "agent_campagnes": RACINE / "api" / "agent_campagnes_routes.py",   # t285a : le message de l'agent Campagnes (Anthropic)
    "scan": RACINE / "api" / "scan_routes.py",   # t312 : le secours Claude vision de la boîte Scan (Anthropic)
    "inspiration": RACINE / "api" / "inspiration_routes.py",   # t313 : matière, angles et rédaction d'une inspiration (Anthropic)
    "schema": RACINE / "api" / "schema_routes.py",   # t314 : le détourage fal d'un schéma (calques du Vectorlab)
    "comparatif3d": RACINE / "api" / "comparatif3d_routes.py",   # t344 : N moteurs image → 3D en un clic (fal)
    "mouvement": RACINE / "api" / "mouvement_routes.py",   # t343 : vidéo → mouvement sur le rig (Uthana)
    "blender": RACINE / "api" / "blender_routes.py",   # t331 : generate_3d de mcp-for-blender (clés ou abonnement de l'add-on)
    "parallaxe": RACINE / "api" / "parallaxe_routes.py",   # t341 : décor en calques de parallaxe (Qwen-Image-Layered / Seedream Layerize, fal)
    "pose3d": RACINE / "api" / "pose3d_routes.py",   # t376 : la classification vision de la source 3D (Anthropic)
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
    "separer_stems", "isoler_voix",   # T100 : Demucs (fal) et l'isolation de voix (ElevenLabs)
    "generer_sfx",   # t187 : le registre des bruitages (fal) — texte (/audio/sfx avec modele) et vidéo (/audio/sfx-video)
    "appliquer_vfx",   # t188 : le registre des VFX IA (fal) — POST /vfx-ia
    "reconstruire",   # t189 : le storyboard 3D (SAM 3 objets / corps, fal) — POST /shots/{shot_id}/objets3d
    "video_vers_mouvement",   # t343 : vidéo → mouvement (Uthana) — POST /api/etabli/mouvement/video
    "tirer_previs",   # t335 : previs → plan (Seedance 2.5 reference-to-video / Veo 3.1 références, fal) — POST /shots/{shot_id}/previs
    "detourer",   # T103 : le matte vidéo BiRefNet (fal)
    "detourer_image",   # t186 : le registre unique du détourage (fal, ou local gratuit ; la vidéo passe par MT.detourer)
    "appliquer_maillon",   # t277 : un maillon IA de la pile de post-traitement (fal, Decart par fal, ElevenLabs)
    "AC.tour",   # t285a : la boucle de l'agent Campagnes (agent_campagnes.tour -> moteurs_texte.converser, Anthropic)
    "WE.envoyer",   # t310 : l'envoi WhatsApp (Kapso -> Meta, facturé par message ; whatsapp_echanges.envoyer)
    "AW.rediger",   # t311 : la boucle de l'agent WhatsApp (agent_whatsapp.rediger -> moteurs_texte.converser, Anthropic)
    "AW.envoyer_brouillon",   # t311 : l'envoi d'un brouillon de l'agent (agent_whatsapp.envoyer_brouillon -> WE.envoyer)
    "WV.envoyer_validation",   # t311 : la demande de validation au client (whatsapp_validation.envoyer_validation -> WE.envoyer)
    "SV.lire",   # t312 : le secours Claude vision du Scan (scan_vision.lire -> moteurs_texte.tirer_garde, Anthropic)
    "I.analyser", "I.rediger",   # t313 : l'inspiration (inspiration.analyser / rediger -> moteurs_texte.tirer_garde, Anthropic)
    "RV.noter",   # t337 : l'avis « directeur artistique » de la revue d'un plan (revue_plan.noter -> moteurs_texte.tirer_garde, Anthropic)
    "P.classer_image",   # t376 : personnage ou non pour la pose 3D (pose3d.classer_image -> moteurs_texte.tirer_garde, Anthropic)
    "WD.lancer",   # t328 : le lancement d'une diffusion WhatsApp (whatsapp_diffusions.lancer -> kapso.envoyer_broadcast)
    "generer_ia",   # t272 : les nœuds IA de l'Atelier sonore (prolonger, régénérer, variation, SFX sur une plage ; fal)
    # transcription
    "transcribe",
    # vidéo / HeyGen (`pipeline.run` en nom pointé : `run` seul attraperait subprocess.run)
    "pipeline.run", "pipeline.render_template", "run_heygen", "run_heygen_image", "run_heygen_cinematic", "run_composition", "run_episode", "run_batch",
    "create_photo_avatar",
    # 3D
    "proxy_request", "texturer_asset3d", "generate_asset3d", "refine_asset3d", "_run_mesh3d",
    "rigger_asset3d",   # T104 : rig + animations Meshy d'un job fal
    "preparer_vues", "rejouer_vue", "detourer_vue", "tirer_vues",   # T106 : les vues avant le tir (Seedream, rembg, moteur)
    "segmenter_par_ia",   # t342 : Tripo Segmentation (fal) — les pièces mobiles soudées
    "decomposer_par_ia",   # t341 : décor en calques de parallaxe (fal) — POST /api/parallaxe/decouper
    "generer_3d",   # t331 : generate_3d dans le Blender ouvert (blender_mcp.generer_3d) — POST /api/blender/generer
    "convertir_par_meshy",   # T105 : fbx/usdz/blend par Meshy convert (1 crédit par tâche)
    "_run_manuscript_job", "_run_adapt_job", "_run_bible_model3d",
    "ouvrir_session_direct",   # t161 : le jeton client Decart (le Direct, facturé à la seconde)
    "relayer_fal",   # t168f : le relais du Direct par fal (le WebSocket fal tenu par le serveur, facturé à la seconde)
    "lancer_recast",
    "lancer_voix",
    "decrire_decor",   # t168e : la consigne de décor proposée par le LLM de vision
    "apercu_detourage",   # t168d : l'aperçu du détourage (BiRefNet image, fal), avant le décor vidéo
    "lancer_decor",   # t164 : le décor différé (BiRefNet vidéo, fal)
      # t163 : voix -> voix (ElevenLabs Voice Changer)
      # t162 : le Recast différé (Wan Animate, Kling Motion Control, Lucy Edit — fal)
}
GARDES = {"_plafond", "_PLAF.verifier",   # `verifier` nu est ambigu (cards/face : `sw.verifier` de la fiche de style)
          "AC.tour",   # t285a : la garde vit DANS la boucle, avant CHAQUE appel du modèle (un tour = une garde) ;
                       # test_plafonds_garde A2d vérifie dans le source que plafonds.verifier y précède MT.converser
          "WE.envoyer",   # t310 : la garde vit DANS whatsapp_echanges.envoyer, sous le verrou du compte ;
                          # test_plafonds_garde A2e vérifie dans le source que plafonds.verifier y précède kapso.envoyer
          "AW.rediger",   # t311 : la garde vit DANS la boucle de l'agent WhatsApp, avant CHAQUE appel du modèle ;
                          # test_plafonds_garde A2f vérifie dans le source que plafonds.verifier y précède MT.converser
          "AW.envoyer_brouillon",   # t311 : délègue à WE.envoyer (garde A2e) ; test_plafonds_garde A2g le vérifie
          "WV.envoyer_validation",   # t311 tâche 6 : délègue à WE.envoyer (garde A2e) ; test_plafonds_garde A2h le vérifie
          "SV.lire",   # t312 : la garde vit DANS scan_vision.lire (tirer_garde avant CHAQUE lot) ; test_plafonds_garde A2i
          "I.analyser", "I.rediger",   # t313 : la garde vit DANS inspiration (tirer_garde après l'accord) ; test_plafonds_garde A2j
          "RV.noter",   # t337 : la garde vit DANS revue_plan.noter (tirer_garde après l'accord) ; test_plafonds_garde A2m
          "P.classer_image",   # t376 : la garde vit DANS pose3d.classer_image (tirer_garde après l'accord) ; test_plafonds_garde A2n
          "WD.lancer"}   # t328 : la garde vit DANS whatsapp_diffusions._lancer_sous_verrou (plafonds.verifier avant le send) ;
                         # test_plafonds_garde A2k le vérifie, A2l que lancer y mène (A2i/A2j de t328 renommés à la fusion t320)


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
    # t168f : une route WebSocket se recense aussi (méthode « WS ») — le relais du Direct par fal y dépense
    if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "websocket"
            and dec.args and isinstance(dec.args[0], ast.Constant)):
        return "WS", dec.args[0].value
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
