# -*- coding: utf-8 -*-
"""t285a (23/10/2026) : la BOUCLE de l'agent Campagnes (`agent_campagnes`). C'est là que l'argent part : le banc
garde d'abord les règles de dépense (devis par message, arrêt net au plafond, garde par tour sous l'espace DE LA
CAMPAGNE, aucun message orphelin sur un refus).
Le modèle est SIMULÉ : `moteurs_texte._POSTER` rend des réponses scriptées. Clé factice, aucun appel payant, aucun
réseau. Le tarif du modèle de banc `claude-banc` est posé dans pricing.json (0,5 $ / 2,5 $ le million de jetons).
Run : & $PY tests/test_agent_boucle.py   (depuis backend/, PYTHONUTF8=1)."""
import asyncio, json, os, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="dzt285a_boucle_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
for _k in ("ANTHROPIC_MODEL", "AGENT_MODEL", "ANTHROPIC_API_KEY"):
    os.environ.pop(_k, None)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
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


from fastapi import HTTPException                                    # noqa: E402
from sqlalchemy import select                                        # noqa: E402
from app.config import settings                                      # noqa: E402
from app.services import (agent_outils as ao, agent_store as st, espaces, moteurs_texte as MT,   # noqa: E402
                          plafonds, pricing)
from app.services.storage import init_db, async_session_factory, ScheduledPost, Depense         # noqa: E402
from app.services import agent_campagnes as AC                       # noqa: E402

MODELE = "claude-banc"
pricing._PRICING_FILE.parent.mkdir(parents=True, exist_ok=True)
pricing._PRICING_FILE.write_text(json.dumps({"llm_claude_usd_per_mtok": {MODELE: {"in": 0.5, "out": 2.5}}}),
                                 encoding="utf-8")
settings.ANTHROPIC_API_KEY = "sk-ant-FACTICE-boucle"
settings.AGENT_MODEL = MODELE


def cout(i, o):
    return pricing.estimate(MT.op_tour(MODELE, i, o))["total_usd"]


class Rep:
    def __init__(self, d): self.status_code, self._d, self.text = 200, d, ""
    def json(self): return self._d


class Script:
    """Le faux modèle : une réponse scriptée par appel ; au-delà, l'appel est une faute du banc."""
    def __init__(self, reponses, boucle=None):
        self.reponses, self.boucle, self.corps = list(reponses), boucle, []
    def __call__(self, url, **kw):
        self.corps.append(json.loads(json.dumps(kw.get("json"))))
        if self.reponses:
            return Rep(self.reponses.pop(0))
        if self.boucle is not None:
            return Rep(self.boucle)
        raise AssertionError("appel du modèle en trop")


def outil(nom, args, i=2000, o=2000, uid=None, texte=None):
    c = ([{"type": "text", "text": texte}] if texte else []) + [
        {"type": "tool_use", "id": uid or f"toolu_{nom}", "name": nom, "input": args}]
    return {"content": c, "stop_reason": "tool_use", "usage": {"input_tokens": i, "output_tokens": o}}


def outils(appels, i=2000, o=2000):
    return {"content": [{"type": "tool_use", "id": f"toolu_{k}", "name": n, "input": a} for k, (n, a) in
                        enumerate(appels)], "stop_reason": "tool_use", "usage": {"input_tokens": i, "output_tokens": o}}


def texte(t, i=2000, o=500):
    return {"content": [{"type": "text", "text": t}], "stop_reason": "end_turn",
            "usage": {"input_tokens": i, "output_tokens": o}}


async def derouler(cid, t, plafond, lang="fr"):
    return [e async for e in AC.tour(cid, t, plafond, lang)]


async def depenses(ref):
    async with plafonds._registre() as s:
        return list((await s.execute(select(Depense).where(Depense.ref == ref))).scalars().all())


async def main():
    await init_db()
    A = espaces.creer({"nom": "Alpha"})["id"]
    B = espaces.creer({"nom": "Bravo"})["id"]
    D = espaces.creer({"nom": "Jeton bis"})["id"]
    espaces.activer(A)                                    # l'espace ACTIF n'est jamais celui de la campagne
    p = espaces.persona(B)
    p["ecran"] = {"banned": ["garanti", "100x"]}
    espaces.ecrire_persona(B, p)
    p = espaces.persona(D)
    p["crypto"] = True
    espaces.ecrire_persona(D, p)

    check("constantes du brief", AC.MAX_TOURS == 8 and AC.SORTIE_MAX == 2000)

    # ---- devis_message -------------------------------------------------------------------------------------------
    conv = await st.creer("campagnes", B, "Lancement")
    cid = conv["id"]
    d = AC.devis_message(await st.lire(cid), "Prépare la campagne de lancement.")
    check("devis_message : clés", set(d) == {"plafond_usd", "in_tok", "out_tok", "modele"}, str(d))
    check("devis_message : MAX_TOURS × SORTIE_MAX en sortie, MAX_TOURS × contexte en entrée",
          d["out_tok"] == AC.MAX_TOURS * AC.SORTIE_MAX and d["in_tok"] > 0 and d["in_tok"] % AC.MAX_TOURS == 0, str(d))
    check("devis_message : tarif du modèle de l'agent (modele_agent, à chaud)",
          d["modele"] == MODELE and abs(d["plafond_usd"] - cout(d["in_tok"], d["out_tok"])) < 1e-9, str(d))
    d2 = AC.devis_message(await st.lire(cid), "x" * 40_000)
    check("devis_message : un message plus long coûte plus", d2["plafond_usd"] > d["plafond_usd"])
    settings.ANTHROPIC_API_KEY = ""
    check("devis_message : rendu même sans clé (vigilance 2)",
          AC.devis_message(await st.lire(cid), "x")["plafond_usd"] > 0)

    # ---- sans clé : refus AVANT toute écriture -------------------------------------------------------------------
    s = Script([texte("jamais")]); MT._POSTER = s
    try:
        await derouler(cid, "Bonjour", 1.0)
        leve = None
    except RuntimeError as e:
        leve = str(e)
    l = await st.lire(cid)
    check("sans clé : RuntimeError('sans_cle')", leve == "sans_cle", str(leve))
    check("sans clé : rien écrit, aucun appel, aucune dépense",
          l["messages"] == [] and l["cout_usd"] == 0 and s.corps == [], str(l)[:200])
    check("sans clé : cle_presente() faux", AC.cle_presente() is False)
    settings.ANTHROPIC_API_KEY = "sk-ant-FACTICE-boucle"
    check("cle_presente() vrai avec une clé", AC.cle_presente() is True)
    check("sans clé : registre vide", not await depenses(cid))

    # ---- test_lecture_puis_reponse -------------------------------------------------------------------------------
    s = Script([outil("chercher_app", {"question": "planificateur brouillon"}, 1000, 200),
                texte("Voilà ce que l'app sait faire.", 1500, 300)])
    MT._POSTER = s
    ev = await derouler(cid, "Que sait faire le Planificateur ?", 1.0)
    types = [e["type"] for e in ev]
    check("test_lecture_puis_reponse : outil, texte, fin", types == ["outil", "texte", "fin"], str(types))
    check("lecture : évènement outil nommé et réussi",
          ev[0].get("nom") == "chercher_app" and ev[0].get("ok") is True and isinstance(ev[0].get("resume"), str),
          str(ev[0]))
    check("lecture : texte final", ev[1].get("texte") == "Voilà ce que l'app sait faire.")
    check("lecture : deux appels du modèle", len(s.corps) == 2)
    c0, c1 = s.corps
    check("lecture : corps (modèle, outils, sortie bornée, système)",
          c0["model"] == MODELE and c0["max_tokens"] == AC.SORTIE_MAX
          and [t["name"] for t in c0["tools"]] == [t["name"] for t in ao.definitions()]
          and "# Agent Campagnes" in c0["system"], str({k: c0[k] for k in ("model", "max_tokens")}))
    check("lecture : le premier appel finit par le message de l'utilisateur",
          c0["messages"][-1] == {"role": "user", "content": "Que sait faire le Planificateur ?"},
          str(c0["messages"])[:300])
    dernier = c1["messages"][-1]
    tr = dernier["content"][0] if isinstance(dernier.get("content"), list) else {}
    check("lecture : tool_result renvoyé au modèle, contenu = pour_modele",
          dernier["role"] == "user" and tr.get("type") == "tool_result" and tr.get("tool_use_id") == "toolu_chercher_app"
          and json.loads(tr["content"]).get("ok") is True and "resume" in json.loads(tr["content"]), str(dernier)[:300])
    check("lecture : le tour de l'assistant (tool_use) est rejoué tel quel",
          c1["messages"][-2] == {"role": "assistant", "content": [
              {"type": "tool_use", "id": "toolu_chercher_app", "name": "chercher_app",
               "input": {"question": "planificateur brouillon"}}]}, str(c1["messages"][-2])[:300])
    l = await st.lire(cid)
    roles = [m["role"] for m in l["messages"]]
    check("lecture : utilisateur, puis un message agent par tour", roles == ["utilisateur", "agent", "agent"], str(roles))
    check("lecture : résultat d'outil noté (résumé seulement)",
          any(b.get("type") == "resultat_outil" and b.get("outil") == "chercher_app" for b in l["messages"][1]["blocs"]))
    reel = cout(1000, 200) + cout(1500, 300)
    check("lecture : coût cumulé = coût RÉEL des deux tours", abs(l["cout_usd"] - reel) < 1e-9, f"{l['cout_usd']} {reel}")
    check("lecture : cout_paye par message", abs(l["messages"][1]["cout_paye"] - cout(1000, 200)) < 1e-9
          and abs(l["messages"][2]["cout_paye"] - cout(1500, 300)) < 1e-9 and l["messages"][0]["cout_paye"] == 0)
    fin = ev[-1]
    check("lecture : fin porte le coût du message", fin.get("motif") == "reponse"
          and abs(fin.get("cout_usd", -1) - reel) < 1e-9, str(fin))

    # un second message rejoue l'historique en rôles alternés, en commençant par l'utilisateur
    s = Script([texte("Oui.")]); MT._POSTER = s
    await derouler(cid, "Et ensuite ?", 1.0)
    msgs = s.corps[0]["messages"]
    alt = all(msgs[i]["role"] != msgs[i + 1]["role"] for i in range(len(msgs) - 1))
    check("historique : alterné, commence et finit par user", alt and msgs[0]["role"] == "user"
          and msgs[-1]["role"] == "user" and "Et ensuite ?" in json.dumps(msgs[-1], ensure_ascii=False),
          str([m["role"] for m in msgs]))
    check("historique : le résultat d'outil d'avant est relu (résumé)",
          "chercher_app" in json.dumps(msgs, ensure_ascii=False))

    # ---- outil inconnu : erreur au modèle, jamais d'exception ----------------------------------------------------
    s = Script([outil("publier", {"tout": True}), texte("Je ne peux pas publier.")]); MT._POSTER = s
    ev = await derouler(cid, "Publie tout.", 1.0)
    tr = s.corps[1]["messages"][-1]["content"][0]
    check("outil inconnu : tool_result en erreur, la boucle continue",
          tr.get("is_error") is True and "outil inconnu" in tr["content"] and ev[-1]["type"] == "fin", str(tr)[:200])

    # ---- test_carte_arrete_la_boucle -----------------------------------------------------------------------------
    conv2 = await st.creer("campagnes", B, "Porte")
    c2 = conv2["id"]
    s = Script([outils([("proposer_porte", {"resume": "Objectif : 300 inscrits\nCanaux : X", "calendrier": []}),
                        ("creer_brouillons", {"posts": [{"caption": "x", "quand": "2026-11-02T10:00:00"}]})]),
                texte("jamais")])
    MT._POSTER = s
    ev = await derouler(c2, "Propose la stratégie.", 1.0)
    cartes = [e for e in ev if e["type"] == "carte"]
    check("test_carte_arrete_la_boucle : une carte porte", len(cartes) == 1 and cartes[0]["carte"]["genre"] == "porte",
          str(ev)[:300])
    check("carte : plus aucun appel du modèle", len(s.corps) == 1)
    check("carte : l'outil suivant n'est pas exécuté",
          [e.get("nom") for e in ev if e["type"] == "outil"] == ["proposer_porte"], str(ev)[:300])
    check("carte : fin motif carte", ev[-1]["type"] == "fin" and ev[-1].get("motif") == "carte", str(ev[-1]))
    l = await st.lire(c2)
    check("carte : état de porte et carte écrite",
          l["etat_porte"] == "porte1_proposee" and any(b.get("type") == "carte" and b.get("genre") == "porte"
                                                       for b in l["messages"][-1]["blocs"]), str(l)[:300])
    async with async_session_factory() as se:
        n = len(list((await se.execute(select(ScheduledPost).where(ScheduledPost.plan_id == c2))).scalars().all()))
    check("carte : aucun brouillon écrit", n == 0)

    # ---- test_arret_au_plafond (vigilance 1) ---------------------------------------------------------------------
    conv3 = await st.creer("campagnes", B, "Plafond")
    c3 = conv3["id"]
    UN = cout(2000, 2000)
    check("préparation : un tour réel coûte 0,006 $", abs(UN - 0.006) < 1e-12, str(UN))
    s = Script([], boucle=outil("chercher_app", {"question": "x"}, 2000, 2000)); MT._POSTER = s
    ev = await derouler(c3, "Lance tout.", 0.01)
    check("test_arret_au_plafond : un seul appel", len(s.corps) == 1, str(len(s.corps)))
    cartes = [e["carte"] for e in ev if e["type"] == "carte"]
    check("plafond : une carte continuer", len(cartes) == 1 and cartes[0]["genre"] == "continuer", str(ev)[:400])
    k = cartes[0] if cartes else {}
    check("plafond : la carte porte un NOUVEAU devis",
          isinstance(k.get("devis"), float) and k["devis"] > 0 and k.get("action") == "continuer"
          and set((k.get("arguments") or {}).get("devis") or {}) == {"plafond_usd", "in_tok", "out_tok", "modele"}
          and abs(k["arguments"]["devis"]["plafond_usd"] - k["devis"]) < 1e-12, str(k)[:300])
    l = await st.lire(c3)
    check("plafond : coût cumulé = un tour", abs(l["cout_usd"] - UN) < 1e-12, str(l["cout_usd"]))
    check("plafond : la carte continuer est écrite",
          any(b.get("genre") == "continuer" for b in l["messages"][-1]["blocs"]))
    check("plafond : fin motif plafond, coût du message", ev[-1]["type"] == "fin" and ev[-1].get("motif") == "plafond"
          and abs(ev[-1].get("cout_usd", -1) - UN) < 1e-12, str(ev[-1]))
    lignes = await depenses(c3)
    check("plafond : une seule garde passée, catégorie campagnes, espace B",
          len(lignes) == 1 and lignes[0].categorie == "campagnes" and lignes[0].espace_id == B,
          str([(x.categorie, x.espace_id) for x in lignes]))

    # un plafond sous le PREMIER tour : aucun appel, rien d'écrit, la carte continuer reprend le texte
    conv4 = await st.creer("campagnes", B, "Trop court")
    c4 = conv4["id"]
    s = Script([texte("jamais")]); MT._POSTER = s
    ev = await derouler(c4, "Fais tout.", 0.0001)
    l = await st.lire(c4)
    check("plafond trop bas : aucun appel, rien d'écrit, aucune garde",
          s.corps == [] and l["messages"] == [] and l["cout_usd"] == 0 and not await depenses(c4), str(l)[:200])
    k = [e["carte"] for e in ev if e["type"] == "carte"]
    check("plafond trop bas : carte continuer avec le texte et son devis",
          len(k) == 1 and k[0]["genre"] == "continuer" and k[0]["arguments"].get("texte") == "Fais tout."
          and k[0]["devis"] > 0.0001, str(ev)[:300])

    # ---- test_max_tours ------------------------------------------------------------------------------------------
    conv5 = await st.creer("campagnes", B, "Boucle")
    c5 = conv5["id"]
    s = Script([], boucle=outil("chercher_app", {"question": "x"}, 100, 100)); MT._POSTER = s
    ev = await derouler(c5, "Tourne.", 100.0)
    check("test_max_tours : exactement MAX_TOURS appels", len(s.corps) == AC.MAX_TOURS, str(len(s.corps)))
    k = [e["carte"] for e in ev if e["type"] == "carte"]
    check("max_tours : carte continuer avec devis, fin motif max_tours",
          len(k) == 1 and k[0]["genre"] == "continuer" and k[0]["devis"] > 0
          and ev[-1]["type"] == "fin" and ev[-1].get("motif") == "max_tours", str(ev[-3:])[:300])
    l = await st.lire(c5)
    check("max_tours : coût = MAX_TOURS tours réels", abs(l["cout_usd"] - AC.MAX_TOURS * cout(100, 100)) < 1e-9)

    # ---- test_verifier_appele_par_tour_avec_espace ---------------------------------------------------------------
    vrai = plafonds.verifier
    try:
        vus = []
        async def espion(op, categorie="", ref=None, confirme=None, espace_id=None):
            vus.append((op, categorie, ref, espace_id))
            return {"devis": pricing.estimate(op), "lignes": [], "etat": {}}
        plafonds.verifier = espion
        conv6 = await st.creer("campagnes", B, "Garde")
        c6 = conv6["id"]
        s = Script([outil("lire_espace", {}), texte("Fini.")]); MT._POSTER = s
        await derouler(c6, "Lis l'espace.", 1.0)
        check("test_verifier_appele_par_tour_avec_espace : une garde par tour", len(vus) == 2, str(len(vus)))
        check("verifier : catégorie campagnes, ref = conversation, espace B (A est actif)",
              all(v[1] == "campagnes" and v[2] == c6 and v[3] == B for v in vus) and espaces.lire()["actif"] == A,
              str([v[1:] for v in vus]))
        check("verifier : op du tour (op_tour du modèle de l'agent, sortie SORTIE_MAX)",
              all(v[0].get("kind") == "llm" and v[0].get("provider") == "anthropic" and v[0].get("modele") == MODELE
                  and v[0].get("out_tok") == AC.SORTIE_MAX and v[0].get("in_tok") > 0 for v in vus), str(vus[0][0]))
        check("verifier : l'outil a lu l'espace DE LA CAMPAGNE",
              json.loads(s.corps[1]["messages"][-1]["content"][0]["content"])["donnees"]["espace"]["id"] == B)

        # refus 402 au premier tour : erreur, aucun appel, AUCUN message orphelin
        async def refus(op, categorie="", ref=None, confirme=None, espace_id=None):
            vus.append((op, categorie, ref, espace_id))
            raise HTTPException(402, {"dz_plafond": {"motif": "global", "message": "plafond atteint"}})
        plafonds.verifier = refus
        conv7 = await st.creer("campagnes", B, "Refus")
        c7 = conv7["id"]
        s = Script([texte("jamais")]); MT._POSTER = s
        ev = await derouler(c7, "Bonjour.", 1.0)
        l = await st.lire(c7)
        check("refus 402 : évènement erreur dz_plafond", ev and ev[-1]["type"] == "erreur"
              and ev[-1].get("code") == "dz_plafond" and ev[-1].get("statut") == 402
              and "dz_plafond" in (ev[-1].get("detail") or {}), str(ev))
        check("refus 402 : aucun appel, aucun message écrit", s.corps == [] and l["messages"] == [] and l["cout_usd"] == 0)

        # refus au SECOND tour : le premier reste payé et écrit, la boucle s'arrête
        n = {"i": 0}
        async def refus_second(op, categorie="", ref=None, confirme=None, espace_id=None):
            n["i"] += 1
            if n["i"] == 2:
                raise HTTPException(402, {"dz_plafond": {"motif": "espace"}})
            return {"devis": pricing.estimate(op), "lignes": [], "etat": {}}
        plafonds.verifier = refus_second
        conv8 = await st.creer("campagnes", B, "Refus 2")
        c8 = conv8["id"]
        s = Script([outil("chercher_app", {"question": "x"}, 1000, 100), texte("jamais")]); MT._POSTER = s
        ev = await derouler(c8, "Cherche.", 1.0)
        l = await st.lire(c8)
        check("refus au second tour : un seul appel, erreur à la fin", len(s.corps) == 1 and ev[-1]["type"] == "erreur")
        check("refus au second tour : utilisateur + premier tour écrits et payés",
              [m["role"] for m in l["messages"]] == ["utilisateur", "agent"]
              and abs(l["cout_usd"] - cout(1000, 100)) < 1e-12, str(l)[:200])
    finally:                                   # jamais une garde factice laissée en place
        plafonds.verifier = vrai

    # ---- test_systeme_crypto_seulement_espace_jeton --------------------------------------------------------------
    MARQUE = "Grille de conformité"
    cj = await st.creer("campagnes", "deepotus", "Jeton")
    sj = AC.systeme(await st.lire(cj["id"]), "fr")
    sb = AC.systeme(await st.lire(c2), "fr")
    cd = await st.creer("campagnes", D, "Jeton bis")
    sd = AC.systeme(await st.lire(cd["id"]), "fr")
    check("test_systeme_crypto_seulement_espace_jeton : espace deepotus", MARQUE in sj)
    check("crypto : persona marquée crypto", MARQUE in sd)
    check("crypto : JAMAIS pour un autre espace", MARQUE not in sb)
    check("systeme : CAMPAGNES.md, espace nommé et ses mots interdits",
          "# Agent Campagnes" in sb and "Bravo" in sb and B in sb and "garanti" in sb and "100x" in sb, sb[-800:])
    check("systeme : le rôle est dit", "Campagnes" in sb and "rôle" in sb.lower())
    sans = await st.creer("orienteur", None, "Sans espace")
    s0 = AC.systeme(await st.lire(sans["id"]), "fr")
    check("systeme : sans espace, ne prend pas l'actif", "Alpha" not in s0 and A not in s0 and MARQUE not in s0)
    check("systeme : langue", "English" in AC.systeme(await st.lire(c2), "en")
          and "français" in sb.lower())

    # ---- test_role_bilan_lit_les_posts_de_la_campagne ------------------------------------------------------------
    cb = await st.creer("bilan", B, "Bilan lancement")
    cbid = cb["id"]
    import datetime as _dt
    async with async_session_factory() as se:
        se.add(ScheduledPost(id="post-camp", title="de la campagne", run_at=_dt.datetime(2026, 11, 1), status="sent",
                             espace_id=B, plan_id=cbid, metrics=json.dumps({"vues": 1200})))
        se.add(ScheduledPost(id="post-autre", title="autre campagne", run_at=_dt.datetime(2026, 11, 2),
                             status="sent", espace_id=B, plan_id="autre-plan"))
        await se.commit()
    sbil = AC.systeme(await st.lire(cbid), "fr")
    check("bilan : le système dit lire_planificateur, bilan.md, apprentissages.md",
          all(x in sbil for x in ("lire_planificateur", "bilan.md", "apprentissages.md")))
    s = Script([outil("lire_planificateur", {}),
                outils([("ecrire_dossier", {"chemin": "bilan.md", "contenu": "# Bilan\n1200 vues"}),
                        ("ecrire_dossier", {"chemin": "apprentissages.md", "contenu": "- vidéo courte : ok"})]),
                texte("Bilan écrit.")])
    MT._POSTER = s
    ev = await derouler(cbid, "Fais le bilan.", 1.0)
    lu = s.corps[1]["messages"][-1]["content"][0]["content"]
    check("test_role_bilan_lit_les_posts_de_la_campagne : posts de CETTE campagne seulement",
          "post-camp" in lu and "post-autre" not in lu and "1200" in lu, lu[:300])
    l = await st.lire(cbid)
    dossier = pathlib.Path(l["dossier"] or "")
    check("bilan : bilan.md et apprentissages.md écrits dans le dossier",
          l["dossier"] and (dossier / "bilan.md").is_file() and (dossier / "apprentissages.md").is_file(), str(l["dossier"]))
    check("bilan : fin", ev[-1]["type"] == "fin" and ev[-1].get("motif") == "reponse", str(ev[-1]))

    # ==== reprise 1 de la revue (plafond inviolable, registre réconcilié, envoi unique) ============================

    # ---- I1 : l'estimation d'entrée est PAR EXCÈS ----------------------------------------------------------------
    def n_caracteres(conv_, t):
        return (len(AC.systeme(conv_, "fr")) + len(json.dumps(AC._historique(conv_["messages"], t), ensure_ascii=False))
                + len(json.dumps(ao.definitions(), ensure_ascii=False)))
    ce = await st.creer("campagnes", B, "Estimation")
    cev = await st.lire(ce["id"])
    n0 = n_caracteres(cev, "Lance.")
    ancien = -(-n0 // 4)                                     # l'ancienne estimation (4 caractères par jeton)
    plaf_ancien = cout(ancien, AC.SORTIE_MAX)                # le plafond qui laissait passer l'ancien premier tour
    reel_in = -(-n0 // 3)                                    # le vrai tour coûte plus que l'ancienne estimation
    check("I1 préparation : le réel dépasse l'ancienne estimation", cout(reel_in, AC.SORTIE_MAX) > plaf_ancien)
    s = Script([], boucle=outil("chercher_app", {"question": "x"}, reel_in, AC.SORTIE_MAX)); MT._POSTER = s
    ev = await derouler(ce["id"], "Lance.", plaf_ancien)
    l = await st.lire(ce["id"])
    check("I1 estimation prudente : aucun dépassement, carte continuer plutôt qu'un appel",
          l["cout_usd"] <= plaf_ancien + 1e-12 and s.corps == []
          and any(e["type"] == "carte" and e["carte"]["genre"] == "continuer" for e in ev), str((l["cout_usd"], ev))[:300])
    ce2 = await st.creer("campagnes", B, "Estimation 2")
    s = Script([], boucle=outil("chercher_app", {"question": "x"}, reel_in + 900, AC.SORTIE_MAX)); MT._POSTER = s
    ev = await derouler(ce2["id"], "Lance.", 0.02)
    l = await st.lire(ce2["id"])
    check("I1 boucle : au moins un tour, cumul ≤ plafond, arrêt par continuer",
          len(s.corps) >= 1 and l["cout_usd"] <= 0.02 + 1e-12 and ev[-1].get("motif") == "plafond",
          str((len(s.corps), l["cout_usd"], ev[-1])))

    # ---- I2 : NaN et infini ne désarment pas le plafond ----------------------------------------------------------
    for v in (float("nan"), float("inf"), -1.0):
        cn = await st.creer("campagnes", B, f"Plafond {v}")
        s = Script([texte("jamais")]); MT._POSTER = s
        ev = await derouler(cn["id"], "Bonjour.", v)
        l = await st.lire(cn["id"])
        check(f"I2 plafond {v} : aucun appel, rien d'écrit, carte continuer",
              s.corps == [] and l["messages"] == [] and l["cout_usd"] == 0
              and any(e["type"] == "carte" and e["carte"]["genre"] == "continuer" for e in ev), str(ev)[:200])

    # ---- F3 : le registre reçoit le RÉEL sur les lignes du tour, et seulement elles ------------------------------
    lignes = await depenses(c3)
    check("F3 la ligne du tour porte le réel = coût ajouté à la conversation",
          len(lignes) == 1 and lignes[0].reel_usd is not None and abs(lignes[0].reel_usd - UN) < 1e-12,
          str([(x.estime_usd, x.reel_usd) for x in lignes]))
    cr = await st.creer("campagnes", B, "Registre")
    s = Script([outil("chercher_app", {"question": "x"}, 1000, 100), texte("Fin.", 1200, 50)]); MT._POSTER = s
    await derouler(cr["id"], "Cherche.", 1.0)
    lignes = sorted(await depenses(cr["id"]), key=lambda x: x.id)
    check("F3 une ligne par tour, chacune à SON réel",
          [round(x.reel_usd, 12) for x in lignes] == [round(cout(1000, 100), 12), round(cout(1200, 50), 12)]
          and abs(sum(x.reel_usd for x in lignes) - (await st.lire(cr["id"]))["cout_usd"]) < 1e-12,
          str([(x.estime_usd, x.reel_usd) for x in lignes]))

    class Panne:
        corps = []
        def __call__(self, url, **kw):
            raise RuntimeError("Anthropic HTTP 500 — panne")
    s = Script([texte("Avant.", 900, 40)]); MT._POSTER = s
    await derouler(cr["id"], "Encore.", 1.0)                 # un tour réussi de plus (ligne 3)
    MT._POSTER = Panne()
    ev = await derouler(cr["id"], "Et là ?", 1.0)
    lignes = sorted(await depenses(cr["id"]), key=lambda x: x.id)
    check("F3 panne après la garde : erreur moteur, la ligne du tour à 0 réel, les autres intactes",
          ev[-1]["type"] == "erreur" and ev[-1].get("code") == "moteur" and len(lignes) == 4
          and lignes[-1].reel_usd == 0.0 and abs(lignes[2].reel_usd - cout(900, 40)) < 1e-12
          and abs(lignes[0].reel_usd - cout(1000, 100)) < 1e-12, str([(x.estime_usd, x.reel_usd) for x in lignes]))

    # ---- F4 : deux envois simultanés sur la même conversation ----------------------------------------------------
    cc = await st.creer("campagnes", B, "Double envoi")
    s = Script([texte("Une fois.")]); MT._POSTER = s
    r1, r2 = await asyncio.gather(derouler(cc["id"], "Bonjour.", 1.0), derouler(cc["id"], "Bonjour.", 1.0))
    occupes = [r for r in (r1, r2) if r and r[-1]["type"] == "erreur" and r[-1].get("code") == "occupee"]
    l = await st.lire(cc["id"])
    check("F4 un seul tour : l'autre reçoit « conversation occupée » sans appel",
          len(occupes) == 1 and len(s.corps) == 1 and [m["role"] for m in l["messages"]] == ["utilisateur", "agent"]
          and "occupée" in occupes[0][-1].get("message", ""), str((r1, r2))[:300])
    s = Script([texte("Ensuite.")]); MT._POSTER = s
    ev = await derouler(cc["id"], "Encore.", 1.0)
    check("F4 le verrou est rendu après le tour", ev[-1]["type"] == "fin" and not AC._VERROUS, str(ev[-1]))

    # ---- F5 : un tool_use tronqué (arret max_tokens) n'est jamais exécuté ----------------------------------------
    ct = await st.creer("campagnes", B, "Tronqué")
    tronque = outil("ecrire_dossier", {"chemin": "strategie.md", "contenu": "début cou"})
    tronque["stop_reason"] = "max_tokens"
    s = Script([tronque, texte("Je recommence plus court.")]); MT._POSTER = s
    ev = await derouler(ct["id"], "Écris la stratégie.", 1.0)
    l = await st.lire(ct["id"])
    tr = s.corps[1]["messages"][-1]["content"][0] if len(s.corps) > 1 else {}
    check("F5 tronqué : tool_result en erreur « appel tronqué », la boucle continue",
          tr.get("is_error") is True and "appel tronqué" in tr.get("content", "") and ev[-1].get("motif") == "reponse",
          str(tr)[:300])
    check("F5 tronqué : rien n'est écrit sur le disque", l["dossier"] is None, str(l["dossier"]))

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(main()) else 0)
