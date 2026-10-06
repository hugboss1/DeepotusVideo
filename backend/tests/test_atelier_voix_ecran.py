# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T14-T15, D4) — l'Atelier montre le casting voix + tempérament. La page est autonome (DOM) :
ses fonctions PURES (foldName, castChip, temperRow, et le `esc` de la page) sont extraites de frontend/atelier/
atelier.js et EXÉCUTÉES sous node ; le câblage (dialogues maison, routes appelées) est lu dans le même fichier.
Vérifié : la palette vient de /api/voice-tags (émotion + voix, jamais les bruitages, aucune balise recopiée), les
balises posées s'allument, Voicebox ou clé absente le DISENT (et ce qui est gardé reste visible) ; la puce de
casting replie accents et casse comme le serveur (_fold_name), nomme voix + tempérament, et marque « sans voix »
en pointillés ; le clonage passe par __dzDialogue.saisir + confirmer (jamais window.prompt), POST
/bible/entities/{id}/voice-clone, puis recharge le casting.
Run (depuis backend/) : & $PY tests/test_atelier_voix_ecran.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
SRC = (RACINE / "frontend" / "atelier" / "atelier.js").read_text(encoding="utf-8")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzatvoix_"))
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def fonction(nom):
    m = re.search(r"\nfunction " + nom + r"\(.*?\n}\n", SRC, re.S)
    return m.group(0) if m else ""
FN = {n: fonction(n) for n in ("esc", "foldName", "castChip", "temperRow")}
check("T0 les quatre fonctions sont dans la page", all(FN.values()), str([k for k, v in FN.items() if not v]))

JS = "\n".join(FN.values()) + r"""
var voiceCast={narrator:null,cast:{"deepotus":{voice_id:"v_deep",name:"Deepotus",style:{tags:["[whispers]","[sighs]"]}},
  "marin":{voice_id:"v_marin",name:"Marin",style:{tags:[]}}},uncast:["Silhouette"]};
var voiceTags=null;var OUT={};
OUT.fold=foldName("  Élodie ÂGÉE ");
OUT.chipDeep=castChip("DÉEPOTUS");OUT.chipMarin=castChip("Marin");OUT.chipSans=castChip("Silhouette");
voiceTags={groups:{emotion:["[excited]","[curious]"],voix:["[whispers]","[sighs]"],sons:["[gunshot]"],special:["[sings]"]},
  providers:{elevenlabs:true,voicebox:false}};
OUT.rowOn=temperRow({voice_style:{tags:["[curious]","[sighs]"]}});
voiceTags={groups:{emotion:["[excited]"]},providers:{elevenlabs:false,voicebox:true}};
OUT.rowVb=temperRow({voice_style:{tags:["[curious]"]}});
voiceTags=null;
OUT.rowRien=temperRow({voice_style:null});
console.log(JSON.stringify(OUT));
"""
f = _TMP / "atelier_voix.js"; f.write_text(JS, encoding="utf-8")
p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
try:
    O = json.loads(p.stdout.strip().splitlines()[-1])
except Exception:
    O = {"erreur": p.stdout[-300:] + p.stderr[-600:]}
check("T1 les fonctions s'exécutent sous node", "erreur" not in O, str(O.get("erreur", ""))[:600])
if "erreur" not in O:
    print("\n[casting]")
    check("C1 repli accents + casse comme le serveur", O["fold"] == "elodie agee", O["fold"])
    check("C2 puce d'un rôle casté : nom, voix, tempérament (accents/casse du plan ignorés)",
          "DÉEPOTUS · Deepotus [whispers] [sighs]" in O["chipDeep"] and "cast-none" not in O["chipDeep"], O["chipDeep"])
    check("C3 sans tempérament : la voix seule, aucune balise inventée", O["chipMarin"].endswith("Marin · Marin</span>"), O["chipMarin"])
    check("C4 personnage sans voix : « sans voix », pointillés (cast-none), et le chemin pour en avoir une",
          "cast-none" in O["chipSans"] and "sans voix" in O["chipSans"] and "Cloner" in O["chipSans"], O["chipSans"])
    print("\n[tempérament]")
    boutons = re.findall(r'data-t="([^"]+)"', O["rowOn"])
    check("T2 palette = émotion + voix SERVIES, jamais les bruitages ni le spécial", boutons == ["[excited]", "[curious]", "[whispers]", "[sighs]"],
          str(boutons))
    allumes = re.findall(r'act-temper on" data-t="([^"]+)"', O["rowOn"])
    check("T3 les balises posées s'allument (aria-pressed suit)", allumes == ["[curious]", "[sighs]"] and O["rowOn"].count('aria-pressed="true"') == 2,
          str(allumes))
    check("T4 Voicebox : pas de palette, la raison est dite, ce qui est GARDÉ reste visible",
          "act-temper" not in O["rowVb"] and "Voicebox ne lit pas" in O["rowVb"] and "[curious]" in O["rowVb"], O["rowVb"])
    check("T5 rien de chargé : clé requise, aucune palette", "act-temper" not in O["rowRien"] and "clé ElevenLabs requise" in O["rowRien"], O["rowRien"])

print("\n[câblage, lu dans la page]")
clone = SRC.split('const vclone = card.querySelector(".act-voice-clone");', 1)[1].split("card.querySelectorAll(\".act-temper\")", 1)[0] \
    if 'const vclone' in SRC else ""
check("W1 clonage : saisie puis confirmation par le dialogue maison, jamais window.prompt/confirm",
      "window.__dzDialogue.saisir(" in clone and "window.__dzDialogue.confirmer(" in clone
      and "prompt(" not in clone.replace("saisir(", "") and "window.confirm" not in clone, clone[:200])
i_conf, i_post = clone.find("if (!await window.__dzDialogue.confirmer(`Cloner la voix"), clone.find('api.send("POST"')
check("W1b un refus de la confirmation ARRÊTE le clonage (le POST vient après, derrière `return`)",
      0 <= i_conf < i_post and clone.find(")) return;", i_conf) < i_post, f"{i_conf} {i_post}")
check("W2 clonage : POST /bible/entities/{id}/voice-clone avec les prises, puis le casting est RECHARGÉ",
      'api.send("POST", `/bible/entities/${id}/voice-clone`, { files })' in clone and "await loadVoiceCast();" in clone)
temp = SRC.split('card.querySelectorAll(".act-temper")', 1)[1].split("}));", 1)[0] if '.act-temper")' in SRC else ""
check("W3 tempérament : PUT voice_style (≤ 4 côté écran, le serveur clampe), casting rechargé",
      'voice_style: { tags: next' in temp and ".slice(-4)" in temp and "await loadVoiceCast();" in temp)
check("W4 la carte plan montre le casting de ses personnages",
      'class="shot-cast"' in SRC and "castChip(en.name)" in SRC)
check("W5 le casting se recharge avec la bible, la palette vient de /voice-tags",
      'await loadVoiceCast();\n}' in SRC and 'api.get("/voice-tags")' in SRC and 'api.get("/voice-cast")' in SRC)
check("W6 aucune balise Eleven v3 recopiée dans la page (le registre est servi)",
      not re.search(r'"\[(excited|whispers|sighs|curious|sad)\]"', SRC))
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
