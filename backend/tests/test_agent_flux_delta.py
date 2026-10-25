# -*- coding: utf-8 -*-
"""L4.1 T3 (25/10/2026) : la réponse de l'agent Campagnes arrive AU FIL DE L'EAU. `moteurs_texte.converser` envoie
`stream: true`, lit le flux SSE d'Anthropic et rend les deltas de texte à mesure ; la boucle les émet en évènements
`{"type":"delta","texte"}` AVANT l'évènement `texte` du bloc, qui reste émis en entier (l'écran du PC ne change pas).
- d1 trois `text_delta` → trois `delta`, puis un `texte` égal à leur concaténation ;
- d2 un `tool_use` dont l'entrée arrive en quatre `input_json_delta` s'exécute avec l'entrée recollée ;
- d3 l'usage noté = celui du flux (entrée de `message_start`, sortie de `message_delta`) ;
- d4 un flux coupé avant `message_stop` → `erreur{code:"moteur"}`, aucun outil exécuté ;
- d5 `ping` ignoré, évènement `error` du flux, statut HTTP, sortie tronquée ; d6 l'écran du PC ignore `delta`.
Le serveur Anthropic est un FAUX (flux SSE écrit à la main) : clé factice, aucun réseau, aucune dépense.
Run : & $PY tests/test_agent_flux_delta.py   (depuis la racine du dépôt ou backend/, PYTHONUTF8=1)."""
import asyncio, json, os, re, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="dzl41_flux_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
for _k in ("ANTHROPIC_MODEL", "AGENT_MODEL", "ANTHROPIC_API_KEY"):
    os.environ.pop(_k, None)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


from sqlalchemy import select                                        # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services import (agent_outils as ao, agent_store as st, espaces, moteurs_texte as MT, plafonds,  # noqa: E402
                          pricing)
from app.services.storage import init_db, Depense                    # noqa: E402
from app.services import agent_campagnes as AC                       # noqa: E402
from _faux_sse import evt, FluxRep                                   # noqa: E402

MODELE = "claude-banc"
pricing._PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
pricing._PRICING_FILE.write_text(json.dumps({"llm_claude_usd_per_mtok": {MODELE: {"in": 0.5, "out": 2.5}}}),
                                 encoding="utf-8")
settings.ANTHROPIC_API_KEY = "sk-ant-FACTICE-flux"
settings.AGENT_MODEL = MODELE


def cout(i, o):
    return pricing.estimate(MT.op_tour(MODELE, i, o))["total_usd"]


def debut(i):
    return evt("message_start", {"type": "message_start", "message": {
        "id": "msg_x", "type": "message", "role": "assistant", "content": [], "stop_reason": None,
        "usage": {"input_tokens": i, "output_tokens": 1}}})


def bloc_texte(idx, morceaux):
    L = evt("content_block_start", {"type": "content_block_start", "index": idx,
                                    "content_block": {"type": "text", "text": ""}})
    for m in morceaux:
        L += evt("content_block_delta", {"type": "content_block_delta", "index": idx,
                                         "delta": {"type": "text_delta", "text": m}})
    return L + evt("content_block_stop", {"type": "content_block_stop", "index": idx})


def bloc_outil(idx, nom, uid, morceaux):
    L = evt("content_block_start", {"type": "content_block_start", "index": idx, "content_block": {
        "type": "tool_use", "id": uid, "name": nom, "input": {}}})
    for m in morceaux:
        L += evt("content_block_delta", {"type": "content_block_delta", "index": idx,
                                         "delta": {"type": "input_json_delta", "partial_json": m}})
    return L + evt("content_block_stop", {"type": "content_block_stop", "index": idx})


def fin(arret, o):
    return (evt("message_delta", {"type": "message_delta", "delta": {"stop_reason": arret, "stop_sequence": None},
                                  "usage": {"output_tokens": o}})
            + evt("message_stop", {"type": "message_stop"}))


class Faux:
    """La couture `_POSTER` : un flux écrit à la main par appel."""
    def __init__(self, flux):
        self.flux, self.corps, self.kw, self.reps = list(flux), [], [], []
    def __call__(self, url, **kw):
        self.corps.append(json.loads(json.dumps(kw.get("json"))))
        self.kw.append(kw)
        if not self.flux:
            raise AssertionError("appel du modèle en trop")
        f = self.flux.pop(0)
        rep = f if isinstance(f, FluxRep) else FluxRep(f)
        self.reps.append(rep)
        return rep


async def derouler(cid, t, plafond=1.0):
    return [e async for e in AC.tour(cid, t, plafond, "fr")]


async def depenses(ref):
    async with plafonds._registre() as s:
        return list((await s.execute(select(Depense).where(Depense.ref == ref))).scalars().all())


APPELS: list = []
_exec0 = ao.executer
_poster0 = MT._POSTER


async def _espion(nom, args, ctx):
    APPELS.append((nom, json.loads(json.dumps(args))))
    return {"ok": True, "resume": "vu", "donnees": None}


async def main():
    await init_db()
    B = espaces.creer({"nom": "Bravo"})["id"]
    ao.executer = _espion

    print("[d1] trois text_delta")
    cid = (await st.creer("campagnes", B, "Flux"))["id"]
    f = Faux([debut(1500) + bloc_texte(0, ["Bon", "jour ", "à tous."]) + fin("end_turn", 40)]); MT._POSTER = f
    ev = await derouler(cid, "Salut.")
    types = [e["type"] for e in ev]
    ds = [e for e in ev if e["type"] == "delta"]
    ts = [e for e in ev if e["type"] == "texte"]
    check("d1 trois évènements delta, dans l'ordre", [e["texte"] for e in ds] == ["Bon", "jour ", "à tous."], str(ev))
    check("d1 puis UN texte égal à la concaténation", len(ts) == 1 and ts[0]["texte"] == "Bonjour à tous.", str(ev))
    check("d1 les delta précèdent le texte, la fin est 'reponse'",
          types == ["delta", "delta", "delta", "texte", "fin"] and ev[-1]["motif"] == "reponse", str(types))
    l = await st.lire(cid)
    check("d1 le message stocké porte le texte entier", l["messages"][-1]["blocs"][0]["texte"] == "Bonjour à tous.",
          str(l["messages"][-1]["blocs"]))
    check("d1c la réponse du flux est fermée après lecture", all(x.ferme for x in f.reps), str([x.ferme for x in f.reps]))
    check("d1b le corps part avec stream:true", f.corps[0].get("stream") is True, str(f.corps[0].keys()))

    print("[d2] input_json_delta recollés")
    APPELS.clear()
    cid = (await st.creer("campagnes", B, "Outil"))["id"]
    morceaux = ['{"ques', 'tion": "plan', 'ificateur ', 'brouillon"}']
    f = Faux([debut(1000) + bloc_texte(0, ["Je cherche."]) + bloc_outil(1, "chercher_app", "toolu_9", morceaux)
              + fin("tool_use", 60),
              debut(1200) + bloc_texte(0, ["Voilà."]) + fin("end_turn", 20)]); MT._POSTER = f
    ev = await derouler(cid, "Où est le planificateur ?")
    check("d2 l'outil est exécuté avec l'entrée recollée",
          APPELS == [("chercher_app", {"question": "planificateur brouillon"})], str(APPELS))
    msg = f.corps[1]["messages"][-2]
    check("d2 le tour suivant rejoue le tool_use entier (id, nom, entrée)",
          msg["role"] == "assistant" and msg["content"][-1] == {
              "type": "tool_use", "id": "toolu_9", "name": "chercher_app", "input": {"question": "planificateur brouillon"}}
          and msg["content"][0] == {"type": "text", "text": "Je cherche."}, str(msg)[:300])
    check("d2 aucun delta pour l'entrée de l'outil (le JSON n'est pas du texte)",
          [e["texte"] for e in ev if e["type"] == "delta"] == ["Je cherche.", "Voilà."], str(ev)[:300])
    check("d2 évènement outil puis fin", [e["type"] for e in ev if e["type"] in ("outil", "fin")] == ["outil", "fin"])

    print("[d3] l'usage noté est celui du flux")
    cid = (await st.creer("campagnes", B, "Usage"))["id"]
    f = Faux([debut(2345) + bloc_texte(0, ["a", "b"]) + fin("end_turn", 678)]); MT._POSTER = f
    ev = await derouler(cid, "Compte.")
    attendu = cout(2345, 678)
    lignes = await depenses(cid)
    check("d3 la ligne de dépense porte le réel du flux (entrée message_start, sortie message_delta)",
          len(lignes) == 1 and abs(lignes[0].reel_usd - attendu) < 1e-12, str([(x.estime_usd, x.reel_usd) for x in lignes]))
    check("d3 fin.cout_usd = ce réel", abs(ev[-1]["cout_usd"] - attendu) < 1e-12, str(ev[-1]))
    l = await st.lire(cid)
    check("d3 cout_paye du message agent", abs(l["messages"][-1]["cout_paye"] - attendu) < 1e-12)

    print("[d4] flux coupé avant message_stop")
    APPELS.clear()
    cid = (await st.creer("campagnes", B, "Coupe"))["id"]
    coupe = debut(900) + bloc_texte(0, ["Je cherche."]) + bloc_outil(1, "chercher_app", "toolu_c", ['{"question": "x"}'])
    f = Faux([coupe]); MT._POSTER = f
    ev = await derouler(cid, "Coupe.")
    check("d4 erreur{code:moteur} en dernier", ev[-1]["type"] == "erreur" and ev[-1].get("code") == "moteur", str(ev[-1]))
    check("d4 aucun outil exécuté", APPELS == [], str(APPELS))
    check("d4 pas d'évènement texte, ni outil, ni fin",
          not any(e["type"] in ("texte", "outil", "fin") for e in ev), str([e["type"] for e in ev]))
    l = await st.lire(cid)
    check("d4 aucun message d'agent écrit (rien d'à moitié)", [m["role"] for m in l["messages"]] == ["utilisateur"],
          str([m["role"] for m in l["messages"]]))
    check("d4 le verrou est rendu", not AC._VERROUS)
    lignes = await depenses(cid)
    check("d4b flux coupé : la réservation reste telle quelle (jamais un réel sous l'entrée facturée)",
          len(lignes) == 1 and lignes[0].reel_usd is None and lignes[0].estime_usd >= cout(900, 1) > 0,
          str([(x.estime_usd, x.reel_usd) for x in lignes]))
    check("d4c le flux coupé est fermé aussi", all(x.ferme for x in f.reps))

    print("[d4d] erreur réseau pendant la lecture du flux (après le 200)")
    import httpx

    class FluxQuiMeurt(FluxRep):
        def __init__(self, lignes, exc):
            super().__init__(lignes); self.exc = exc
        def iter_lines(self):
            yield from self._lignes
            raise self.exc

    for exc in (httpx.ReadError("connexion perdue sk-ant-FACTICE-flux"), httpx.RemoteProtocolError("coupé"),
                httpx.ReadTimeout("délai")):
        APPELS.clear()
        nom = type(exc).__name__
        cid = (await st.creer("campagnes", B, "Reseau " + nom))["id"]
        f = Faux([FluxQuiMeurt(debut(900) + bloc_texte(0, ["Je cherche."]), exc)]); MT._POSTER = f
        ev = await derouler(cid, "Coupe réseau.")
        check(f"d4d {nom} : erreur{{code:moteur}}, rien d'exécuté, clé ôtée",
              ev[-1]["type"] == "erreur" and ev[-1].get("code") == "moteur" and APPELS == []
              and "sk-ant-FACTICE" not in str(ev[-1]), str(ev[-1]))
        lignes = await depenses(cid)
        eff = [(x.reel_usd if x.reel_usd is not None else x.estime_usd) for x in lignes]
        check(f"d4d {nom} : le coût compté n'est jamais sous l'entrée facturée (pas 0)",
              len(lignes) == 1 and eff[0] >= cout(900, 1) > 0, str([(x.estime_usd, x.reel_usd) for x in lignes]))
        check(f"d4d {nom} : flux fermé, verrou rendu", all(x.ferme for x in f.reps) and not AC._VERROUS)

    print("[d5] lecture du flux")
    cid = (await st.creer("campagnes", B, "Lecture"))["id"]
    f = Faux([debut(500) + evt("ping", {"type": "ping"}) + bloc_texte(0, ["x"]) + evt("ping", {"type": "ping"})
              + fin("end_turn", 5)]); MT._POSTER = f
    ev = await derouler(cid, "Ping.")
    check("d5 ping ignorés", [e["type"] for e in ev] == ["delta", "texte", "fin"], str(ev))
    h = f.kw[0].get("headers", {})
    check("d5 clé dans l'en-tête, jamais dans le corps",
          h.get("x-api-key") == settings.ANTHROPIC_API_KEY and "FACTICE" not in json.dumps(f.corps[0]))
    cid = (await st.creer("campagnes", B, "Erreur"))["id"]
    err = debut(500) + bloc_texte(0, ["début"]) + evt("error", {"type": "error", "error": {
        "type": "overloaded_error", "message": "Overloaded " + settings.ANTHROPIC_API_KEY}})
    f = Faux([err]); MT._POSTER = f
    ev = await derouler(cid, "Surcharge.")
    check("d5b évènement error du flux → erreur moteur, clé ôtée, aucun texte entier",
          ev[-1]["type"] == "erreur" and ev[-1]["code"] == "moteur" and "Overloaded" in ev[-1]["message"]
          and "FACTICE" not in ev[-1]["message"] and not any(e["type"] == "texte" for e in ev), str(ev[-1]))
    cid = (await st.creer("campagnes", B, "Http"))["id"]
    f = Faux([FluxRep(status_code=529, text="surcharge " + settings.ANTHROPIC_API_KEY)]); MT._POSTER = f
    ev = await derouler(cid, "Http.")
    check("d5c statut ≠ 200 : erreur moteur, clé ôtée",
          ev[-1]["type"] == "erreur" and "529" in ev[-1]["message"] and "FACTICE" not in ev[-1]["message"], str(ev[-1]))
    cid = (await st.creer("campagnes", B, "Tronque"))["id"]
    f = Faux([debut(500) + bloc_texte(0, ["Je commence"]) + bloc_outil(1, "ecrire_dossier", "toolu_t", ['{"chemin": "a'])
              + fin("max_tokens", 2000),
              debut(600) + bloc_texte(0, ["Plus court."]) + fin("end_turn", 10)]); MT._POSTER = f
    APPELS.clear()
    ev = await derouler(cid, "Long.")
    check("d5d max_tokens avec entrée d'outil coupée : jamais exécuté, la boucle continue",
          APPELS == [] and ev[-1]["type"] == "fin" and any(e["type"] == "outil" and e["ok"] is False for e in ev),
          str(ev)[:300])

    cid = (await st.creer("campagnes", B, "Illisible"))["id"]
    f = Faux([debut(500) + bloc_outil(0, "chercher_app", "toolu_i", ['{"question": "x', ]) + fin("tool_use", 5)]); MT._POSTER = f
    APPELS.clear()
    ev = await derouler(cid, "Illisible.")
    check("d5e entrée d'outil illisible hors max_tokens : erreur moteur, rien d'exécuté",
          ev[-1]["type"] == "erreur" and ev[-1]["code"] == "moteur" and APPELS == [], str(ev)[:300])

    cid = (await st.creer("campagnes", B, "Bruit"))["id"]
    f = Faux([[": commentaire", "data: {pas du json", ""] + debut(500) + bloc_texte(0, ["ok"]) + ["data: [1, 2]", ""]
              + fin("end_turn", 5)]); MT._POSTER = f
    ev = await derouler(cid, "Bruit.")
    check("d5f lignes de commentaire, data illisible ou non objet : ignorées, le tour aboutit",
          [e["type"] for e in ev] == ["delta", "texte", "fin"], str(ev)[:300])

    print("[d6] l'écran du PC ignore delta")
    src = (_ICI.parent.parent / "frontend" / "shared" / "dz-campagnes.js").read_text(encoding="utf-8")
    i = src.index("function evenement(e)")
    corps = src[i:src.index("function compter", i)]
    check("d6 evenement() rend la main sur `delta` AVANT tout dessin (le fil n'est pas rebâti à chaque morceau)",
          bool(re.match(r'function evenement\(e\) \{\s*(//[^\n]*\n\s*)?if \(e\.type === "delta"\) return;', corps)), corps[:120])
    dist = (_ICI.parent.parent / "frontend" / "dist" / "shared" / "dz-campagnes.js").read_text(encoding="utf-8")
    check("d6 le dist porte la même garde (copie octet pour octet de la source)", dist == src)

    ao.executer = _exec0
    MT._POSTER = _poster0
    print(f"\n=== {ok} passed, {fail} failed ===")


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(1 if fail else 0)
