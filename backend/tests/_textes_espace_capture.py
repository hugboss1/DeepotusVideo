# -*- coding: utf-8 -*-
"""t208 : capture les sorties de marque touchées par t208 (scripts, légendes, News, storyboard, paroles) pour un
espace. A figé tests/textes_espace_deepotus.json sur la base aa61fa8f (python tests/_textes_espace_capture.py <json>,
depuis backend/) ; importé par test_espaces_textes.py."""
import asyncio, json, os, pathlib, random, sys, tempfile


def preparer():
    _tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt208_"))
    os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
    for d in ("images", "outputs"):
        (_tmp / d).mkdir(exist_ok=True)
    os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
    os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
              "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY"):
        os.environ[k] = ""
    sys.path.insert(0, os.getcwd())


ITEMS = [{"title": "Central bank holds rates steady - Reuters", "essence": "The central bank kept rates unchanged."},
         {"title": "Solana network sees record activity", "summary": "Activity hit a record high this week."},
         {"title": "Court rules on token case | CoinDesk"}]
INTENTS = ["a glowing coin rising", "Les profondeurs s'ouvrent. Une pièce monte", "x"]
MODES = [None, "oracle", "alpha", "zen", "memer", "prophet"]


def capturer(eid="deepotus") -> dict:
    from app.services import espaces as ES, summarizer as SUM, news_rank as NR, music_service as MU
    from app.services import prompt_engine as PE
    from app.models.schemas import Language, VoiceMode
    out = {}
    vu = {}
    vrai_rw, vrai_chat = SUM.rewrite_script, SUM._chat_dispatch

    def faux_rw(script, voice_desc="", language="EN", max_words=60):
        vu.setdefault("voice_desc", []).append(voice_desc)
        return None, ""

    def faux_chat(prompt, system, n):
        vu.setdefault("system", []).append(system)
        vu.setdefault("prompt", []).append(prompt)
        return None, ""
    SUM.rewrite_script, SUM._chat_dispatch = faux_rw, faux_chat
    try:
        with ES.sous_espace(eid):
            e = PE.PromptEngine()
            for L in (Language.EN, Language.FR):
                out[f"generic_{L.value}"] = e._generic_caption(L)
                for it in INTENTS:
                    out[f"cap_{L.value}_{it}"] = e._suggest_caption_from_intent(it, L, None)
                    out[f"vo_{L.value}_{it}"] = e._suggest_voiceover_from_intent(it, L)
                    for m in MODES:
                        for mw in (24, 60):
                            vm = VoiceMode(m) if m and m in VoiceMode._value2member_map_ else None
                            r = e.generate_script_from_intent(it, voice_mode=vm, language=L, max_words=mw,
                                                              inject_persona=(mw == 60))
                            out[f"script_{L.value}_{it}_{m}_{mw}"] = r.model_dump()
                for m in MODES:
                    vm = VoiceMode(m) if m and m in VoiceMode._value2member_map_ else None
                    for angle in (None, "rates matter"):
                        for mw in (40, 90):
                            r = e.generate_news_script(ITEMS, voice_mode=vm, language=L, max_words=mw, angle=angle,
                                                       polir=False)
                            out[f"news_{L.value}_{m}_{angle}_{mw}"] = r.model_dump()
                    vu.clear()
                    e.polish_news_script("Hello world.", voice_mode=vm, language=L)
                    out[f"polish_desc_{L.value}_{m}"] = vu.get("voice_desc")
                r = e.generate_news_script([], language=L, polir=False)
                out[f"news_vide_{L.value}"] = r.model_dump()
            from app.services.pipeline import Pipeline
            p = Pipeline()
            for m in MODES:
                vm = VoiceMode(m) if m and m in VoiceMode._value2member_map_ else None
                out[f"heygen_cap_{m}"] = p._heygen_caption_from_script("Hello there. Second.", vm)
            vu.clear()
            NR.classer([{"id": "a", "title": "Solana record"}], brief="", llm=True)
            NR.classer([{"id": "a", "title": "Solana record"}], brief="solana", llm=True)
            out["rank_system"] = vu.get("system")
            out["rank_prompt"] = vu.get("prompt")
            vu.clear()
            from app.api import routes as RT
            RT._ai_scenes("One. Two. Three.", "en", False)
            RT._ai_scenes("One. Two. Three.", "fr", True)
            out["story_system"] = vu.get("system")
            out["story_prompt"] = vu.get("prompt")
            out["lyrics"] = MU.lyrics_skeleton(None, "")
            out["lyrics_theme"] = MU.lyrics_skeleton(None, "tides")
            from app.services import news_chain as NC, marketing as MK
            vrai_mat = MK.materialize_plan
            vu.clear()

            async def faux_mat(plan, **kw):
                vu["plan"] = plan
                raise RuntimeError("arrêt du banc")
            MK.materialize_plan = faux_mat
            try:
                for arts in ([{"title": "Hello"}], [{"title": "x", "url": "u"}]):
                    lot = {"articles": arts, "creneau": "2030-01-01T10:00:00+00:00"}
                    try:
                        asyncio.run(NC.valider(lot))
                    except RuntimeError:
                        pass
                    out.setdefault("chain_titre", []).append(vu.get("plan", [{}])[0].get("title"))
            finally:
                MK.materialize_plan = vrai_mat
    finally:
        SUM.rewrite_script, SUM._chat_dispatch = vrai_rw, vrai_chat
    return out


if __name__ == "__main__":
    preparer()
    from loguru import logger
    logger.remove()
    from app.services import espaces as ES
    ES.lire()
    d = capturer()
    pathlib.Path(sys.argv[1]).write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(len(d), "clés")
