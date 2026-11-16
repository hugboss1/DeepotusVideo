# -*- coding: utf-8 -*-
"""15/11/2026 : la RÉFLEXION des modèles de l'agent. Constat sur l'app installée : avec `claude-sonnet-5-5` et une
sortie de 2 000 jetons, trois réponses payées et vides de suite. Ce modèle réfléchit même sans `thinking` dans la
requête, la réflexion se compte dans `max_tokens`, l'arrêt était `max_tokens` et il ne restait ni texte ni appel.
Le banc fige : la table des modèles qui réfléchissent d'office, la sortie demandée (réserve comprise) et chiffrée,
l'effort envoyé seulement si le modèle l'accepte, et la boucle qui ne rend plus jamais une réponse vide sans le dire.
Le modèle est SIMULÉ (`moteurs_texte._POSTER`) : aucun réseau, aucune dépense.
Run : & $PY tests/test_agent_reflexion.py   (depuis backend/, PYTHONUTF8=1)."""
import asyncio, json, os, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="dzreflexion_")
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


from app.config import settings                                      # noqa: E402
from app.services import (agent_store as st, espaces, moteurs_texte as MT)   # noqa: E402
from app.services import agent_campagnes as AC, agent_metier as AM, agent_whatsapp as AW          # noqa: E402
from app.services.storage import init_db                             # noqa: E402
from _faux_sse import evt, FluxRep, lignes_depuis_message            # noqa: E402

PENSEUR = "claude-sonnet-5-5"
SANS = "claude-haiku-4-5-20251001"
settings.ANTHROPIC_API_KEY = "sk-ant-FACTICE-reflexion"


def debut(i):
    return evt("message_start", {"type": "message_start", "message": {
        "id": "msg_x", "type": "message", "role": "assistant", "content": [], "stop_reason": None,
        "usage": {"input_tokens": i, "output_tokens": 1}}})


def bloc_reflexion(idx):
    """Un bloc `thinking` tel que l'API le rend par défaut (`display: omitted`) : texte vide, signature seule."""
    return (evt("content_block_start", {"type": "content_block_start", "index": idx,
                                        "content_block": {"type": "thinking", "thinking": "", "signature": ""}})
            + evt("content_block_delta", {"type": "content_block_delta", "index": idx,
                                          "delta": {"type": "signature_delta", "signature": "sig_banc"}})
            + evt("content_block_stop", {"type": "content_block_stop", "index": idx}))


def bloc_texte(idx, t):
    return (evt("content_block_start", {"type": "content_block_start", "index": idx,
                                        "content_block": {"type": "text", "text": ""}})
            + evt("content_block_delta", {"type": "content_block_delta", "index": idx,
                                          "delta": {"type": "text_delta", "text": t}})
            + evt("content_block_stop", {"type": "content_block_stop", "index": idx}))


def fin(arret, o):
    return (evt("message_delta", {"type": "message_delta", "delta": {"stop_reason": arret, "stop_sequence": None},
                                  "usage": {"output_tokens": o}})
            + evt("message_stop", {"type": "message_stop"}))


class Faux:
    def __init__(self, flux):
        self.flux, self.corps = list(flux), []
    def __call__(self, url, **kw):
        self.corps.append(json.loads(json.dumps(kw.get("json"))))
        if not self.flux:
            raise AssertionError("appel du modèle en trop")
        return FluxRep(self.flux.pop(0))


async def derouler(cid, t, plafond, lang="fr"):
    return [e async for e in AC.tour(cid, t, plafond, lang)]


async def main():
    await init_db()
    E = espaces.creer({"nom": "Reflexion"})["id"]

    print("\n== 1. la table : qui réfléchit d'office ==")
    oui = ["claude-sonnet-5-5", "claude-sonnet-5", "claude-opus-5-5", "claude-opus-5", "claude-haiku-5-5",
           "claude-fable-5-2", "claude-mythos-5-1"]
    non = ["claude-haiku-4-5-20251001", "claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-8", "claude-opus-4-7",
           "claude-banc", "", None, "gpt-6-astra"]
    check("1a réfléchissent d'office", all(MT.reflechit(m) for m in oui), [m for m in oui if not MT.reflechit(m)])
    check("1b ne réfléchissent pas d'office (ou id inconnu)", not any(MT.reflechit(m) for m in non),
          [m for m in non if MT.reflechit(m)])

    print("\n== 2. la sortie demandée ==")
    check("2a sans réflexion : la sortie de l'agent, inchangée", MT.sortie_tour(SANS, 2000, "medium") == 2000
          and MT.sortie_tour("claude-banc", 1800, "medium") == 1800)
    check("2b réflexion + effort accepté : sortie + réserve du niveau",
          MT.sortie_tour(PENSEUR, 2000, "medium") == 8000 and MT.sortie_tour(PENSEUR, 2000, "low") == 4000)
    check("2c effort absent : la réserve du DÉFAUT du modèle (high ; medium sur Opus 5.5)",
          MT.sortie_tour(PENSEUR, 2000) == 12000 and MT.sortie_tour("claude-opus-5-5", 2000) == 8000)
    check("2d bornée par PLAFOND_SORTIE", MT.sortie_tour(PENSEUR, 30000, "max") == MT.PLAFOND_SORTIE)
    settings.AGENT_MODEL = PENSEUR
    check("2e les trois agents demandent plus que leur sortie écrite sur un modèle qui réfléchit",
          AC.sortie_tour() == 8000 and MT.sortie_tour(PENSEUR, AM.SORTIE_MAX, AM.EFFORT) == 7800
          and MT.sortie_tour(PENSEUR, AW.SORTIE_MAX, AW.EFFORT) == 4000)
    settings.AGENT_MODEL = SANS
    check("2f et rien de plus sur un modèle qui ne réfléchit pas", AC.sortie_tour() == AC.SORTIE_MAX == 2000)

    print("\n== 3. converser : l'effort ne part que s'il est accepté ==")
    f = Faux([debut(10) + bloc_texte(0, "ok") + fin("end_turn", 5)] * 3); MT._POSTER = f
    MT.converser(PENSEUR, "s", [{"role": "user", "content": "x"}], [], 8000, effort="medium")
    MT.converser(SANS, "s", [{"role": "user", "content": "x"}], [], 2000, effort="medium")
    MT.converser(PENSEUR, "s", [{"role": "user", "content": "x"}], [], 8000)
    check("3a modèle qui l'accepte : output_config.effort", f.corps[0].get("output_config") == {"effort": "medium"}
          and f.corps[0]["max_tokens"] == 8000, f.corps[0].get("output_config"))
    check("3b modèle qui ne l'accepte pas : rien n'est envoyé", "output_config" not in f.corps[1])
    check("3c effort absent : rien n'est envoyé", "output_config" not in f.corps[2])
    check("3d jamais de `thinking` ni de budget dans la requête", all("thinking" not in c for c in f.corps))

    print("\n== 4. la boucle Campagnes sur un modèle qui réfléchit ==")
    settings.AGENT_MODEL = PENSEUR
    conv = await st.creer("campagnes", E, "Reflexion")
    cid = conv["id"]
    d = AC.devis_message(conv, "Fais le plan.", "fr")
    check("4a le devis chiffre la sortie RÉELLEMENT demandée (8 × 8 000)", d["out_tok"] == AC.MAX_TOURS * 8000, d)
    # le cas du 15/11 : la réflexion a tout pris — un bloc thinking vide, arrêt max_tokens, ni texte ni appel
    f = Faux([debut(60000) + bloc_reflexion(0) + fin("max_tokens", 8000)]); MT._POSTER = f
    ev = await derouler(cid, "Fais le plan.", d["plafond_usd"])
    check("4b la requête demande le garde-fou (32 000, plus les 8 000 du devis) et l'effort medium",
          f.corps[0]["max_tokens"] == MT.GARDE_SORTIE == 32000
          and f.corps[0].get("output_config") == {"effort": "medium"}, f.corps[0].get("max_tokens"))
    textes = [e["texte"] for e in ev if e["type"] == "texte"]
    check("4c un texte DIT que la réponse a été coupée (plus de réponse vide)", textes == [AC.COUPE["fr"]], textes)
    cartes = [e["carte"] for e in ev if e["type"] == "carte"]
    check("4d une carte Continuer « sortie » est proposée",
          len(cartes) == 1 and cartes[0]["genre"] == "continuer" and cartes[0]["arguments"]["motif"] == "sortie"
          and cartes[0]["arguments"]["depense_usd"] > 0, cartes)
    check("4e fin du tour : motif sortie, coût compté", ev[-1]["type"] == "fin" and ev[-1]["motif"] == "sortie"
          and ev[-1]["cout_usd"] > 0, ev[-1])
    l = await st.lire(cid)
    vides = [m for m in l["messages"] if m["role"] == "agent"
             and all(b.get("type") == "texte" and not b.get("texte") for b in m["blocs"])]
    check("4f aucun message d'agent vide n'est écrit", not vides and len(l["messages"]) == 3,
          [m["role"] for m in l["messages"]])

    # un texte amputé à la limite : il est gardé, l'avis et la carte suivent
    conv2 = await st.creer("campagnes", E, "Reflexion"); c2 = conv2["id"]
    f = Faux([debut(1000) + bloc_reflexion(0) + bloc_texte(1, "Jour 1 : accroche") + fin("max_tokens", 8000)])
    MT._POSTER = f
    ev = await derouler(c2, "Fais le plan.", AC.devis_message(conv2, "Fais le plan.", "en")["plafond_usd"], "en")
    textes = [e["texte"] for e in ev if e["type"] == "texte"]
    check("4g texte amputé : le texte reçu puis l'avis (en anglais), puis la carte",
          textes == ["Jour 1 : accroche", AC.COUPE["en"]] and ev[-1]["motif"] == "sortie", textes)

    # la réponse normale d'un modèle qui réfléchit : le bloc thinking n'est ni affiché ni pris pour une réponse vide
    conv3 = await st.creer("campagnes", E, "Reflexion"); c3 = conv3["id"]
    f = Faux([debut(1000) + bloc_reflexion(0) + bloc_texte(1, "Voici le plan.") + fin("end_turn", 900)])
    MT._POSTER = f
    ev = await derouler(c3, "Fais le plan.", AC.devis_message(conv3, "Fais le plan.", "fr")["plafond_usd"])
    check("4h réponse normale : le texte seul, fin « reponse », aucune carte",
          [e["texte"] for e in ev if e["type"] == "texte"] == ["Voici le plan."] and ev[-1]["motif"] == "reponse"
          and not [e for e in ev if e["type"] == "carte"], [e["type"] for e in ev])

    # un refus sans texte : dit, sans carte
    conv4 = await st.creer("campagnes", E, "Reflexion"); c4 = conv4["id"]
    f = Faux([debut(1000) + fin("refusal", 0)]); MT._POSTER = f
    ev = await derouler(c4, "Fais le plan.", AC.devis_message(conv4, "Fais le plan.", "fr")["plafond_usd"])
    check("4i refus sans texte : l'avis de refus, fin « reponse »",
          [e["texte"] for e in ev if e["type"] == "texte"] == [AC.REFUS["fr"]] and ev[-1]["motif"] == "reponse", ev[-1])

    print("\n== 5. sur un modèle qui ne réfléchit pas, rien ne change ==")
    settings.AGENT_MODEL = SANS
    conv5 = await st.creer("campagnes", E, "Reflexion"); c5 = conv5["id"]
    f = Faux([debut(1000) + bloc_texte(0, "Bonjour.") + fin("end_turn", 20)]); MT._POSTER = f
    d5 = AC.devis_message(conv5, "Salut", "fr")
    ev = await derouler(c5, "Salut", d5["plafond_usd"])
    check("5a aucun effort envoyé, devis inchangé à 8 × 2 000, et le tour demande ce que ce devis paie",
          "output_config" not in f.corps[0] and d5["out_tok"] == 16000
          and 2000 <= f.corps[0]["max_tokens"] <= MT.GARDE_SORTIE
          and f.corps[0]["max_tokens"] == AC._sortie_possible(
              SANS, AC._jetons(f.corps[0]["system"], f.corps[0]["messages"], f.corps[0]["tools"]),
              d5["plafond_usd"], 2000), f.corps[0].get("max_tokens"))

    print("\n== 6. l'espace choisi : une carte Continuer suit (l'écran ne relance rien de lui-même) ==")
    from app.api import agent_campagnes_routes as ACR
    from app.services import agent_format as fmt
    conv6 = await st.creer("campagnes", None, "Sans espace"); c6 = conv6["id"]
    await st.ajouter(c6, [fmt.nouveau_message("utilisateur", [{"type": "texte", "texte": "Fais la campagne."}]),
                          fmt.nouveau_message("agent", [{
                              "type": "carte", "genre": "espace", "libelle": "Choisir l'espace de marque de la campagne",
                              "etat": "proposee", "action": "choisir_espace",
                              "arguments": {"espaces": [{"id": E, "nom": "Reflexion"}]}}])])
    await st.regler_espace(c6, E)
    await ACR._proposer_suite(c6, "en")
    l6 = await st.lire(c6)
    dern = l6["messages"][-1]
    carte6 = dern["blocs"][0] if dern["blocs"] else {}
    check("6a une carte Continuer « espace » proposée, chiffrée, au texte de reprise",
          dern["role"] == "agent" and carte6.get("genre") == "continuer" and carte6.get("etat") == "proposee"
          and carte6["arguments"]["motif"] == "espace" and carte6["arguments"]["texte"] == AC.TEXTE_CONTINUER["en"]
          and carte6["devis"] > 0 and carte6["arguments"]["depense_usd"] == 0, carte6)
    d6 = AC.devis_message(l6, AC.TEXTE_CONTINUER["en"], "en")
    check("6b son devis est celui de l'espace choisi", abs(carte6["devis"] - d6["plafond_usd"]) < 0.05, (carte6.get("devis"), d6["plafond_usd"]))
    source = pathlib.Path(ACR.__file__).read_text(encoding="utf-8")
    apres = source.split("if not await ST.regler_espace(cid, extra[\"espace_id\"]):", 1)[1][:400]
    check("6c la route /carte la propose juste après avoir réglé l'espace", "_proposer_suite(cid, _lang(request))" in apres)
    await ACR._proposer_suite("conversation-inconnue", "fr")
    check("6d une conversation illisible ne lève rien (le choix reste écrit)", True)

    print("\n== 7. le garde-fou de sortie suit le devis (16/11/2026) ==")
    # Constat du 16/11 (claude-opus-5-5) : deux tours de production coupés à 8 000 jetons de réflexion, sans texte ni
    # appel ; « Continue » rejouait le même tour. `max_tokens` devient un garde-fou borné par le RESTE du devis.
    OPUS = "claude-opus-5-5"
    check("7a sortie connue par modèle ; inconnue = 0",
          MT.sortie_modele(OPUS) == 128000 and MT.sortie_modele(PENSEUR) == 128000 and MT.sortie_modele(SANS) == 64000
          and MT.sortie_modele("claude-haiku-5-5") == 128000 and MT.sortie_modele("claude-opus-4-5") == 0
          and MT.sortie_modele("claude-banc") == 0 and MT.sortie_modele(None) == 0)
    check("7b garde d'un tour : 32 000 sur un modèle connu, la base sur un inconnu, jamais moins que la base",
          MT.garde_tour(OPUS, 8000) == 32000 and MT.garde_tour(SANS, 2000) == 32000
          and MT.garde_tour("claude-banc", 2000) == 2000 and MT.garde_tour(OPUS, 40000) == 40000)

    def usd(m, i, o):
        return AC._usd(MT.op_tour(m, i, o))
    check("7c budget large : le garde-fou entier",
          AC._sortie_possible(OPUS, 20000, usd(OPUS, 20000, 32000) + 1.0, 8000) == 32000)
    reste = usd(OPUS, 20000, 15000)
    n = AC._sortie_possible(OPUS, 20000, reste, 8000)
    # le devis est arrondi au dix-millième de dollar : quelques jetons d'écart au plus (4 à 25 $ le million)
    check("7d budget serré : le plus grand nombre de jetons que le reste paie, à l'arrondi du devis près",
          0 <= n - 15000 <= 8 and usd(OPUS, 20000, n) <= reste + 1e-12, n)
    check("7e budget sous la base : 0, aucun appel ne partira",
          AC._sortie_possible(OPUS, 20000, usd(OPUS, 20000, 7990), 8000) == 0
          and AC._sortie_possible(OPUS, 20000, 0.0, 8000) == 0)
    check("7f budget = la sortie du devis exactement : elle part (à l'arrondi près), jamais 0",
          0 <= AC._sortie_possible(OPUS, 20000, usd(OPUS, 20000, 8000), 8000) - 8000 <= 8)

    # la boucle : le cas du 16/11 rejoué avec des tours chers. La dépense ne passe jamais le devis, la sortie demandée
    # rétrécit avec le reste, et la boucle s'arrête d'elle-même quand même la sortie du devis ne tient plus.
    settings.AGENT_MODEL = OPUS
    conv7 = await st.creer("campagnes", E, "Reflexion"); c7 = conv7["id"]
    d7 = AC.devis_message(conv7, "Lance la production.", "fr")
    base7 = AC.sortie_tour(OPUS)
    SORTIES = []

    class Gourmand:
        """Un modèle qui prend à chaque tour 30 000 jetons, ou toute la sortie accordée si elle est plus petite."""
        def __init__(self):
            self.corps = []
        def __call__(self, url, **kw):
            c = json.loads(json.dumps(kw.get("json")))
            self.corps.append(c)
            o = min(30000, int(c["max_tokens"]))
            SORTIES.append(o)
            return FluxRep(lignes_depuis_message({
                "content": [{"type": "tool_use", "id": f"toolu_{len(self.corps)}", "name": "chercher_app",
                             "input": {"requete": "planificateur"}}],
                "stop_reason": "tool_use", "usage": {"input_tokens": 1000, "output_tokens": o}}))
    f = Gourmand(); MT._POSTER = f
    ev = await derouler(c7, "Lance la production.", d7["plafond_usd"])
    check("7g le devis du message n'a pas changé (8 × la sortie du devis)",
          d7["out_tok"] == AC.MAX_TOURS * base7 == 64000, d7)
    check("7h le premier tour demande 32 000 jetons, plus 8 000", bool(f.corps) and f.corps[0]["max_tokens"] == 32000,
          [c["max_tokens"] for c in f.corps])
    dep, tenu, serre = 0.0, True, True
    for k, c in enumerate(f.corps):
        est = AC._jetons(c["system"], c["messages"], c["tools"])
        tenu = (tenu and base7 <= c["max_tokens"] <= 32000
                and dep + usd(OPUS, est, c["max_tokens"]) <= d7["plafond_usd"] + 1e-9)
        if c["max_tokens"] < 32000:                          # borné par le reste : le plus grand nombre qui tient
            serre = serre and dep + usd(OPUS, est, c["max_tokens"] + 8) > d7["plafond_usd"] - 1e-9
        dep += usd(OPUS, 1000, SORTIES[k])
    check("7i chaque tour : entre la sortie du devis et le garde-fou, et payé par le reste du devis", tenu,
          [c["max_tokens"] for c in f.corps])
    check("7j un tour borné par le reste demande le plus grand nombre qui tient",
          serre and any(c["max_tokens"] < 32000 for c in f.corps), [c["max_tokens"] for c in f.corps])
    check("7k la boucle s'arrête d'elle-même sur la carte Continuer « plafond », sans dépasser le devis",
          ev[-1]["type"] == "fin" and ev[-1]["motif"] == "plafond" and ev[-1]["cout_usd"] <= d7["plafond_usd"] + 1e-9
          and 0 < len(f.corps) < AC.MAX_TOURS
          and [e["carte"]["arguments"]["motif"] for e in ev if e["type"] == "carte"] == ["plafond"],
          (ev[-1], len(f.corps)))

    # les plafonds du mois : le garde-fou large refusé (402), le tour du devis accepté : il part à la sortie du devis
    from fastapi import HTTPException
    vrai = AC.plafonds.verifier
    vus = []

    async def verifier_serre(op, categorie="", ref=None, confirme=None, espace_id=None):
        vus.append(op["out_tok"])
        if op["out_tok"] > base7:
            raise HTTPException(402, {"code": "dz_plafond"})
        return {"devis": {}, "lignes": [], "etat": {}}

    async def verifier_ferme(op, categorie="", ref=None, confirme=None, espace_id=None):
        raise HTTPException(402, {"code": "dz_plafond"})
    try:
        AC.plafonds.verifier = verifier_serre
        conv8 = await st.creer("campagnes", E, "Reflexion"); c8 = conv8["id"]
        f = Faux([debut(1000) + bloc_reflexion(0) + bloc_texte(1, "Voici.") + fin("end_turn", 500)]); MT._POSTER = f
        ev = await derouler(c8, "Bonjour.", AC.devis_message(conv8, "Bonjour.", "fr")["plafond_usd"])
        check("7l plafond du mois serré : le tour part à la sortie du devis au lieu d'être refusé",
              vus == [32000, base7] and f.corps[0]["max_tokens"] == base7 and ev[-1]["motif"] == "reponse",
              (vus, ev[-1]))
        AC.plafonds.verifier = verifier_ferme
        conv9 = await st.creer("campagnes", E, "Reflexion"); c9 = conv9["id"]
        f = Faux([]); MT._POSTER = f
        ev = await derouler(c9, "Bonjour.", AC.devis_message(conv9, "Bonjour.", "fr")["plafond_usd"])
        l9 = await st.lire(c9)
        check("7m plafond du mois fermé : erreur dz_plafond, aucun appel, aucun message orphelin",
              ev[-1]["type"] == "erreur" and ev[-1]["code"] == "dz_plafond" and not f.corps and not l9["messages"],
              ev[-1])
    finally:
        AC.plafonds.verifier = vrai

    # la reprise après une coupure dit comment avancer, sans pousser à abréger
    conv10 = await st.creer("campagnes", E, "Reflexion"); c10 = conv10["id"]
    f = Faux([debut(1000) + bloc_reflexion(0) + fin("max_tokens", 32000)]); MT._POSTER = f
    ev = await derouler(c10, "Lance la production.",
                        AC.devis_message(conv10, "Lance la production.", "en")["plafond_usd"], "en")
    carte10 = ([e["carte"] for e in ev if e["type"] == "carte"] or [{"arguments": {}}])[0]
    check("7n la carte après coupure porte la reprise « une pièce à la fois, en entier »",
          carte10["arguments"].get("motif") == "sortie" and carte10["arguments"].get("texte") == AC.TEXTE_APRES_COUPE["en"]
          and "one piece at a time" in AC.TEXTE_APRES_COUPE["en"] and "in full" in AC.TEXTE_APRES_COUPE["en"]
          and "une pièce à la fois" in AC.TEXTE_APRES_COUPE["fr"], carte10)
    check("7o ni l'avis de coupure ni l'appel tronqué ne poussent à raccourcir",
          "plus court" not in AC.APPEL_TRONQUE and "sans raccourcir" in AC.APPEL_TRONQUE
          and "Rien n'est perdu" not in AC.COUPE["fr"] and "Nothing is lost" not in AC.COUPE["en"])
    camp = (AC.DOCS / "CAMPAGNES.md").read_text(encoding="utf-8")
    check("7p CAMPAGNES.md : une pièce à la fois, jamais abrégée",
          "une pièce à la fois" in camp and "N'abrège jamais" in camp)
    settings.AGENT_MODEL = SANS

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(main()) else 0)
