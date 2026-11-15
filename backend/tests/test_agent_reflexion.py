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
from _faux_sse import evt, FluxRep                                   # noqa: E402

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
    check("4b la requête demande 8 000 jetons et l'effort medium",
          f.corps[0]["max_tokens"] == 8000 and f.corps[0].get("output_config") == {"effort": "medium"},
          f.corps[0].get("max_tokens"))
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
    check("5a 2 000 jetons demandés, aucun effort envoyé, devis à 8 × 2 000",
          f.corps[0]["max_tokens"] == 2000 and "output_config" not in f.corps[0] and d5["out_tok"] == 16000,
          f.corps[0].get("max_tokens"))

    print(f"\n{ok} PASS, {fail} FAIL")
    return fail


if __name__ == "__main__":
    sys.exit(1 if asyncio.run(main()) else 0)
