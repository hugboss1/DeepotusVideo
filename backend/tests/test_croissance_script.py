# -*- coding: utf-8 -*-
"""t496 (G6, 26/11/2026) — banc de l'outil `ecrire_script_court` de l'agent Campagnes (boîte « croissance »).

1. le script part dans textes/<nom>.md avec sa durée lue et son texte à l'écran ; le verdict dans controle.md ;
2. les quatre contrôles et les mots interdits de l'espace (persona) ; un script fautif est écrit et signalé « à revoir » ;
3. nom de fichier assaini ; script vide refusé ; aucune dépense (aucun appel réseau, aucune ligne au registre) ;
4. la boîte « croissance » : agent Campagnes seul, pas sur le téléphone avant G9.
Run (depuis backend/) : & $PY tests/test_croissance_script.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzg6_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import agent_outils as ao, agent_store as st, espaces, agent_boites as B   # noqa: E402
from app.services.storage import init_db                            # noqa: E402
import httpx                                                        # noqa: E402

RESEAU = []
httpx.post = lambda *a, **k: RESEAU.append(a) or (_ for _ in ()).throw(RuntimeError("réseau interdit"))


async def main():
    await init_db()
    E = espaces.creer({"nom": "Studio G6"})["id"]
    p = espaces.persona(E)
    p["ecran"] = {"banned": ["gratuit"]}
    espaces.ecrire_persona(E, p)
    conv = await st.creer("campagnes", E, "Reel prix")
    ctx = ao.Ctx(cid=conv["id"], espace_id=E, lang="fr", etat_porte="aucune")
    print("[1] script conforme")
    r = await ao.executer("ecrire_script_court", {"accroche": "Tu paies encore chaque mois ?",
                                                  "corps": ["VideoGen se paie une seule fois.", "Les mises à jour sont comprises."],
                                                  "appel": "Le lien est dans la bio.",
                                                  "ecran": ["chaque mois ?", "une seule fois", "", "lien bio"],
                                                  "gagnant": "reel du 05/11", "nom": "Reel Prix !"}, ctx)
    check("1a ok, conforme, durée estimée", r["ok"] and r["donnees"]["ok"] and r["donnees"]["duree_s"] > 0, r)
    l = await st.lire(conv["id"])
    d = pathlib.Path(l["dossier"])
    md = (d / "textes" / "reel-prix.md").read_text(encoding="utf-8") if (d / "textes" / "reel-prix.md").exists() else ""
    check("1b textes/reel-prix.md : lignes, écran, gagnant, durée", "1. Tu paies encore chaque mois ?" in md
          and "À l'écran : chaque mois ?" in md and "Part du gagnant : reel du 05/11" in md and "Durée lue estimée" in md, md)
    ctl = (d / "controle.md").read_text(encoding="utf-8")
    check("1c controle.md : quatre contrôles + interdits conformes", ctl.count(": conforme") == 5 and "Fin sur un appel" in ctl, ctl)
    print("[2] script fautif")
    r = await ao.executer("ecrire_script_court", {"accroche": "Voici une accroche beaucoup trop longue pour tenir dans les trois premières secondes",
                                                  "corps": ["C'est gratuit. Et rapide."], "appel": "Merci d'avoir regardé.",
                                                  "ecran": ["", "100 % offert"]}, ctx)
    c = r["donnees"]["controles"]
    check("2a écrit mais « à revoir »", r["ok"] and not r["donnees"]["ok"] and "à revoir" in r["resume"], r["resume"])
    check("2b accroche, une idée, appel, écran, interdits : tous KO", not any(c[k]["ok"] for k in ("accroche", "une_idee", "appel", "ecran", "interdits")), c)
    check("2c mot interdit de la persona relevé", c["interdits"]["detail"] == ["gratuit"], c["interdits"])
    print("[3] bornes")
    r = await ao.executer("ecrire_script_court", {"accroche": " ", "corps": [], "appel": ""}, ctx)
    check("3a script vide refusé", r["ok"] is False, r)
    r = await ao.executer("ecrire_script_court", {"accroche": "A ?", "corps": ["b."], "appel": "Lien en bio.", "nom": "../../evasion"}, ctx)
    check("3b nom assaini (aucune sortie du dossier)", r["ok"] and r["donnees"]["chemin"] == "textes/evasion.md", r)
    check("3c aucune dépense, aucun réseau", not RESEAU)
    print("[4] boîte")
    check("4a boîte croissance : agent Campagnes, sur le téléphone depuis G9 (t499)", B.boite_de("ecrire_script_court") == "croissance"
          and B.BOITES["croissance"]["agents"] == ["campagnes"] and B.BOITES["croissance"]["mobile"] is True)
    r = await ao.executer("ecrire_script_court", {"accroche": "a", "corps": ["b"], "appel": "c"}, ao.Ctx(cid=conv["id"], agent="whatsapp"))
    check("4b refusé à l'agent WhatsApp", r["ok"] is False and "boîte" in r["resume"], r)


def test_croissance_script():
    asyncio.run(main())
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
