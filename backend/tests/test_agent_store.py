# -*- coding: utf-8 -*-
"""t285a (23/10/2026) : le registre des conversations de l'agent interne (table + dossier de campagne).
Run : & $PY tests/test_agent_store.py   (depuis backend/)"""
import asyncio, json, os, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt285a_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import agent_store as st, agent_format as fmt   # noqa: E402
from app.services.storage import init_db                          # noqa: E402
from app.config import DATA_ROOT                                  # noqa: E402


def msg(texte="salut", role="utilisateur", cout=0.0, origine="pc"):
    m = fmt.nouveau_message(role, [{"type": "texte", "texte": texte}], origine=origine)
    m["cout_paye"] = cout
    return m


async def main():
    await init_db()
    # creer / lire
    c = await st.creer("campagnes", "esp1", "Lancement")
    check("creer : champs", c["role"] == "campagnes" and c["espace_id"] == "esp1" and c["etat_porte"] == "aucune"
          and c["cout_usd"] == 0 and c["dossier"] is None and c["origine"] == "pc" and len(c["id"]) == 36)
    l = await st.lire(c["id"])
    check("lire : ligne + messages vides", l and l["titre"] == "Lancement" and l["messages"] == [])
    check("lire inconnu = None", await st.lire("nope") is None)
    o = await st.creer("orienteur", None, "Q", id="fixe-1")
    check("creer : id imposé, sans dossier -> _conversations",
          o["id"] == "fixe-1" and (DATA_ROOT / "campagnes" / "_conversations" / "fixe-1").parent.name == "_conversations")
    try:
        await st.creer("inconnu", None, "x"); r = False
    except ValueError:
        r = True
    check("creer : rôle inconnu -> ValueError", r)

    # ajouter cumule le coût
    m1, m2 = msg("a"), msg("b", "agent")
    await st.ajouter(c["id"], [m1], 0.25)
    await st.ajouter(c["id"], [m2], 0.5)
    l = await st.lire(c["id"])
    check("ajouter : messages dans l'ordre", [m["id"] for m in l["messages"]] == [m1["id"], m2["id"]])
    check("ajouter : coût cumulé", abs(l["cout_usd"] - 0.75) < 1e-9, str(l["cout_usd"]))
    check("ajouter : fichier sous _conversations", (DATA_ROOT / "campagnes" / "_conversations" / c["id"] / "conversation.json").is_file())
    bad = {"v": 1}
    try:
        await st.ajouter(c["id"], [bad]); r = False
    except ValueError:
        r = True
    check("ajouter : message invalide refusé", r)

    # import idempotent
    conv = {"id": "tel-1", "role": "campagnes", "espace_id": "esp1", "titre": "Du téléphone", "origine": "telephone",
            "messages": [msg("x", origine="telephone", cout=0.4), msg("y", "agent", cout=0.1, origine="telephone")]}
    r1 = await st.importer(conv)
    check("import 1 : ajoutes", r1 == {"ajoutes": 2, "ignores": 0, "conflits": []}, str(r1))
    a = await st.lire("tel-1")
    check("import 1 : coût payé compté", abs(a["cout_usd"] - 0.5) < 1e-9 and a["origine"] == "telephone", str(a["cout_usd"]))
    r2 = await st.importer(conv)
    b = await st.lire("tel-1")
    check("import 2 : 0 ajouté, 2 ignorés", r2 == {"ajoutes": 0, "ignores": 2, "conflits": []}, str(r2))
    check("import 2 : coût inchangé, pas de doublon", abs(b["cout_usd"] - 0.5) < 1e-9 and len(b["messages"]) == 2)

    # conflit
    autre = json.loads(json.dumps(conv))
    autre["messages"][0]["blocs"][0]["texte"] = "MODIFIE"
    nouveau = msg("z", cout=0.2, origine="telephone")
    autre["messages"].append(nouveau)
    r3 = await st.importer(autre)
    d = await st.lire("tel-1")
    check("conflit : signalé, rien écrasé", len(r3["conflits"]) == 1 and r3["ajoutes"] == 1 and r3["ignores"] == 1, str(r3))
    check("conflit : texte d'origine gardé", d["messages"][0]["blocs"][0]["texte"] == "x")
    check("conflit : id inconnu ajouté, coût +0.2", len(d["messages"]) == 3 and abs(d["cout_usd"] - 0.7) < 1e-9, str(d["cout_usd"]))
    inval = {"id": "tel-2", "role": "campagnes", "messages": [{"v": 1, "id": "m"}]}
    r4 = await st.importer(inval)
    check("import : message invalide signalé, non ajouté",
          r4["ajoutes"] == 0 and len(r4.get("invalides", [])) == 1 and (await st.lire("tel-2"))["messages"] == [], str(r4))

    # dossier confiné
    base = (DATA_ROOT / "campagnes" / "esp1").resolve()
    p = st.dossier_campagne("esp1", "..\\x")
    check("dossier : confiné", p.resolve().is_relative_to(base) and p.is_dir() and p.name.endswith("-x"), str(p))
    p2 = st.dossier_campagne("esp1", "../../../evil/..")
    check("dossier : slug hostile confiné", p2.resolve().is_relative_to(base), str(p2))
    try:
        st.dossier_campagne("..", "x"); r = False
    except ValueError:
        r = True
    check("dossier : espace hostile refusé", r)
    await st.regler_dossier(c["id"], str(p))
    await st.ajouter(c["id"], [msg("c")], 0)
    check("dossier réglé : conversation.json dedans", (p / "conversation.json").is_file()
          and len((await st.lire(c["id"]))["messages"]) == 3)

    # porte
    await st.regler_porte(c["id"], "porte1_proposee")
    check("porte : état écrit", (await st.lire(c["id"]))["etat_porte"] == "porte1_proposee")
    try:
        await st.regler_porte(c["id"], "nimporte"); r = False
    except ValueError:
        r = True
    check("porte : état inconnu -> ValueError", r)

    # fichier illisible : jamais écrasé
    ci = await st.creer("campagnes", "esp1", "Corrompue")
    await st.ajouter(ci["id"], [msg("avant")], 0)
    f = DATA_ROOT / "campagnes" / "_conversations" / ci["id"] / "conversation.json"
    f.write_text("{pas du json", encoding="utf-8")
    check("lire : illisible signalé", (await st.lire(ci["id"])).get("illisible") is True)
    for nom, coro in (("ajouter", lambda: st.ajouter(ci["id"], [msg("n")], 1.0)),
                      ("importer", lambda: st.importer({"id": ci["id"], "role": "campagnes", "messages": [msg("n", cout=0.3)]})),
                      ("regler_dossier", lambda: st.regler_dossier(ci["id"], str(st.dossier_campagne("esp1", "corr"))))):
        try:
            await coro(); r = False
        except st.ConversationIllisible:
            r = True
        check(f"{nom} : refuse sur fichier illisible", r)
    check("original intact", f.read_text(encoding="utf-8") == "{pas du json")
    check("copie .corrompu-* présente", len(list(f.parent.glob("conversation.json.corrompu-*"))) >= 1)
    check("coût inchangé", abs((await st.lire(ci["id"]))["cout_usd"] - 0.0) < 1e-9)
    f.write_text("[]", encoding="utf-8")
    f.write_text('{"a": 1}', encoding="utf-8")
    try:
        await st.ajouter(ci["id"], [msg("n")]); r = False
    except st.ConversationIllisible:
        r = True
    check("JSON non liste = illisible", r)
    # regler_dossier hors racine
    try:
        await st.regler_dossier(c["id"], TMP + "/ailleurs"); r = False
    except ValueError:
        r = True
    check("regler_dossier : hors racine refusé", r)

asyncio.run(main())
print(f"\n{ok} OK, {fail} KO")
sys.exit(1 if fail else 0)
