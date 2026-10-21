# -*- coding: utf-8 -*-
"""Son & VFX › Musique › « Importer et séparer » (t269, 21/10/2026) — la page `DzSvPistes` posée par le maillon de
queue `dzsonvfx` depuis sa source frontend/patches/sonvfx-pistes.js : importer une piste, choisir une piste de la
Bibliothèque, séparer les instruments (Demucs 4 ou 6 pistes, devis au premier clic, envoi au second), écouter le
mélange des pistes séparées (muet, solo, volume), les télécharger, aller au Montage.
Sections :
  [S] source et livré : le livré porte la source APLATIE à l'octet, règles d'écriture, routes, aucun texte en dur ;
  [P] sous node, avec la VRAIE fonction du livré, un mini-moteur de hooks et un faux serveur : choix par défaut,
      devis puis séparation, annulation, choix du modèle, import (fichier, glisser-déposer, refus), mélange
      (muet, solo, volume, lecture), recherche, Montage, erreurs du serveur.
Run (depuis backend/) : & $PY tests/test_sonvfx_pistes.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
SRC_P = RACINE / "frontend" / "patches" / "sonvfx-pistes.js"
SRC = SRC_P.read_bytes().decode("utf-8")
_i, _j = BUNDLE.find("/*__dzsonvfx*/"), BUNDLE.find("/*__dzsvpistes*/")
PAGE = BUNDLE[_i + len("/*__dzsonvfx*/"):_j] if 0 <= _i < _j else ""

# ── [S] source et livré ───────────────────────────────────────────────────────────────────────────────────────────
print("[S] source et livré")
import patch_bundle_dzsonvfx as PS  # noqa: E402
check("S1 le livré porte la source aplatie, à l'octet", PAGE and PAGE == PS.aplatir(SRC), (len(PAGE), len(PS.aplatir(SRC))))
check("S2 la page est posée une fois, juste après le hub et avant `const Te=`",
      BUNDLE.count("function DzSvPistes(") == 1 and 0 < _i < _j < BUNDLE.find('const Te="/api";'))
_lignes, _dans = [], False
for _l in (l.strip() for l in SRC.splitlines()):          # hors commentaires de lignes entières, comme aplatir()
    if _dans or _l.startswith("/*"):
        _dans = not _l.endswith("*/")
        continue
    _lignes.append(_l)
check("S3 règles d'écriture : ni « // », ni ligne qui commence par ( ou [",
      not any(l.startswith(("//", "(", "[")) for l in _lignes))
check("S4 aucun texte en dur : libellés par dzT, aucun aria-label/placeholder/title littéral",
      not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', PAGE) and not re.search(r'"aria-label":"|placeholder:"|title:"', PAGE))
check("S5 routes : liste, sidecar, import, modèles, devis, séparation",
      all(u in PAGE for u in ('"/api/audio"', '"/api/audio/meta"', '"/api/audio/upload"', '"/api/audio/stems-models"',
                              '"/api/cost/estimate"', '"/api/audio/stems"')))
check("S6 hooks par alias dans la fonction (x.useState( absent de la page)",
      "var US=x.useState,UE=x.useEffect,UR=x.useRef;" in PAGE and "x.useState(" not in PAGE)
_ext = set(re.findall(r"\.(\w+)", re.search(r'accept:"([^"]+)"', PAGE).group(1))) if 'accept:"' in PAGE else set()
_rt = (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
_srv = set(re.findall(r'"\.(\w+)"', re.search(r"_AUDIO_EXTS = \{([^}]*)\}", _rt).group(1)))
check("S7 le sélecteur de fichiers accepte exactement les formats de la route d'import", _ext == _srv, (_ext, _srv))

# ── [P] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("/*__dzsonvfx*/"),j=S.indexOf("/*__dzsvpistes*/");if(i<0||j<i)throw new Error("page introuvable");
const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[];
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p[q]))EFF.push(f);H[k]=d||[]},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const r={jsx:(t,p)=>({t,p}),jsxs:(t,p)=>({t,p}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
class FormData{constructor(){this.e=[]}append(k,v){this.e.push([k,v&&v.name])}}
let APPELS=[],AUDIO=[],META={},MODS={},REP={};
function json(d,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(d)})}
function fetch(u,o){o=o||{};const corps=o.body instanceof FormData?o.body.e:(o.body?JSON.parse(o.body):null);
 APPELS.push([u,o.method||"GET",corps]);
 if(u==="/api/audio")return json({audio:AUDIO.slice()});
 if(u==="/api/audio/meta")return json({meta:Object.assign({},META)});
 if(u==="/api/audio/stems-models")return json(MODS);
 if(u==="/api/cost/estimate")return json({total_usd:0.0581,breakdown:[]});
 if(u==="/api/audio/upload"){const R0=REP.upload||{st:200,d:{filename:"ma_piste.wav"}};
  if(R0.st<400){AUDIO.unshift({name:R0.d.filename,url:"/api/audio/"+R0.d.filename});META[R0.d.filename]={kind:"import"}}
  return json(R0.d,R0.st)}
 if(u==="/api/audio/stems"){const R0=REP.stems||{st:200,d:{items:[{filename:"a"},{filename:"b"}],missing:["guitar"],usd:0.058}};return json(R0.d,R0.st)}
 return json({},404)}
eval(CODE);
const LECT={};let CLICK_FICHIER=0,ALLER=[];
function audioFaux(src){return LECT[src]||(LECT[src]={src,volume:1,muted:false,currentTime:0,joue:0,play(){this.joue++;return Promise.resolve()},pause(){this.joue=0}})}
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null||n===false)return "";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join("");if(n.t==="glyph")return "";return n.p?texte(n.p.children):""}
let A=null;
function rendre(){HI=0;EFF=[];A=DzSvPistes({go:v=>ALLER.push(v)});
 tout(A,n=>n.p&&n.p.ref,[]).forEach(n=>{if(typeof n.p.ref==="function")n.p.ref(audioFaux(n.p.src));else n.p.ref.current={click(){CLICK_FICHIER++}}});
 const e=EFF;EFF=[];e.forEach(f=>f());return A}
async function calme(){for(let k=0;k<8;k++){await new Promise(r0=>setImmediate(r0));rendre()}}
function un(f){return tout(A,f,[])[0]}
function btn(attr){return un(n=>n.t==="button"&&n.p["data-sv-pistes"]===attr)}
function etat(){
 const ls=un(n=>n.p&&n.p.className==="dzsvp-ligne"&&n.p["data-sel"]==="");
 return {sel:ls?texte(ls.p.children[0]):null,
  lignes:tout(A,n=>n.p&&n.p.className==="dzsvp-ligne",[]).map(n=>texte(n.p.children[0])),
  stems:tout(A,n=>n.p&&n.p.className==="dzsvp-stem",[]).map(n=>[n.p["data-stem"],texte(n.p.children[0])]),
  modeles:tout(A,n=>n.p&&n.p.className==="dzsvp-modele",[]).map(n=>[texte(n.p.children[0]),n.p["aria-pressed"]]),
  cle:!!un(n=>n.p&&n.p.className==="dzsvp-aide dzsvp-cle"),
  separer:btn("separer")?texte(btn("separer").p.children):null,
  arme:btn("separer")?btn("separer").p["data-arme"]==="":null,
  duree:texte(un(n=>n.p&&n.p.className==="dzsvp-tete")),
  note:texte(un(n=>n.p&&n.p.className==="dzsvp-note")),
  vide:texte(un(n=>n.p&&n.p.className==="dzsvp-vide")),
  aides:tout(A,n=>n.p&&n.p.className==="dzsvp-aide",[]).map(texte),
  lire:btn("lire")?texte(btn("lire").p.children):null,
  appels:APPELS.slice()}}
function stemBtn(stem,k){const L=un(n=>n.p&&n.p.className==="dzsvp-stem"&&n.p["data-stem"]===stem);return L.p.children[k]}
(async()=>{const R={};
 AUDIO=[{name:"import.wav",url:"/api/audio/import.wav"},{name:"musique_a.mp3",url:"/api/audio/musique_a.mp3"},
  {name:"stem_musique_a_drums.mp3",url:"/api/audio/stem_musique_a_drums.mp3"},{name:"stem_musique_a_vocals.mp3",url:"/api/audio/stem_musique_a_vocals.mp3"},
  {name:"sfx_boom.mp3",url:"/api/audio/sfx_boom.mp3"}];
 META={"musique_a.mp3":{kind:"musique"},"import.wav":{kind:"import"},"sfx_boom.mp3":{kind:"sfx"},
  "stem_musique_a_drums.mp3":{kind:"stem",stem:"drums",parent:"musique_a.mp3"},
  "stem_musique_a_vocals.mp3":{kind:"stem",stem:"vocals",parent:"musique_a.mp3"}};
 MODS={enabled:false,"default":"htdemucs_6s",models:[{id:"htdemucs_6s",stems:["vocals","drums","bass","other","guitar","piano"]},{id:"htdemucs_ft",stems:["vocals","drums","bass","other"]}]};
 rendre();R.charge0=etat();await calme();R.montage=etat();
 un(n=>n.p&&n.p.className==="dzsvp-lecteur").p.onLoadedMetadata({target:{duration:83}});rendre();R.duree=etat();
 APPELS=[];btn("separer").p.onClick();await calme();R.arme=etat();
 btn("separer").p.onClick();await calme();R.separe=etat();
 APPELS=[];btn("separer").p.onClick();await calme();
 un(n=>n.t==="button"&&n.p.className==="dzsvp-btn"&&texte(n.p.children)==="⟦sonvfx.pistes.annuler⟧").p.onClick();await calme();R.annule=etat();
 tout(A,n=>n.p&&n.p.className==="dzsvp-modele",[])[1].p.onClick();rendre();
 APPELS=[];btn("separer").p.onClick();await calme();btn("separer").p.onClick();await calme();R.modele4=etat();
 stemBtn("vocals",2).p.onClick();rendre();R.muet={v:LECT["/api/audio/stem_musique_a_vocals.mp3"].muted,d:LECT["/api/audio/stem_musique_a_drums.mp3"].muted};
 stemBtn("drums",3).p.onClick();rendre();stemBtn("vocals",2).p.onClick();rendre();
 R.solo={v:LECT["/api/audio/stem_musique_a_vocals.mp3"].muted,d:LECT["/api/audio/stem_musique_a_drums.mp3"].muted};
 stemBtn("drums",3).p.onClick();rendre();R.sans_solo={v:LECT["/api/audio/stem_musique_a_vocals.mp3"].muted,d:LECT["/api/audio/stem_musique_a_drums.mp3"].muted};
 stemBtn("drums",4).p.onChange({target:{value:"0.4"}});rendre();R.volume=LECT["/api/audio/stem_musique_a_drums.mp3"].volume;
 btn("lire").p.onClick();rendre();R.lecture={v:LECT["/api/audio/stem_musique_a_vocals.mp3"].joue,d:LECT["/api/audio/stem_musique_a_drums.mp3"].joue,lbl:etat().lire};
 btn("montage").p.onClick();rendre();R.montage_go={aller:ALLER.slice(),joue:LECT["/api/audio/stem_musique_a_drums.mp3"].joue};
 const tel=un(n=>n.t==="a");R.telecharger={href:tel.p.href,download:tel.p.download};
 un(n=>n.p&&n.p.className==="dzsvp-q").p.onChange({target:{value:"IMPORT"}});rendre();R.recherche=etat();
 un(n=>n.p&&n.p.className==="dzsvp-q").p.onChange({target:{value:""}});rendre();
 tout(A,n=>n.p&&n.p.className==="dzsvp-ligne",[]).find(n=>texte(n.p.children[0])==="import.wav").p.onClick();await calme();R.autre=etat();
 btn("importer").p.onClick();R.clic_fichier=CLICK_FICHIER;
 APPELS=[];un(n=>n.t==="input"&&n.p.type==="file").p.onChange({target:{files:[{name:"ma piste.wav"}],value:"x"}});await calme();R.importe=etat();
 REP.upload={st:415,d:{detail:"Fichier vide ou illisible : vide.wav (0 octet)"}};APPELS=[];
 const dep=un(n=>n.p&&n.p.className==="dzsvp-depot");
 dep.p.onDragOver({preventDefault(){}});rendre();R.survol=un(n=>n.p&&n.p.className==="dzsvp-depot").p["data-survol"];
 un(n=>n.p&&n.p.className==="dzsvp-depot").p.onDrop({preventDefault(){},dataTransfer:{files:[{name:"vide.wav"}]}});await calme();R.refus=etat();
 R.survol_apres=un(n=>n.p&&n.p.className==="dzsvp-depot").p["data-survol"]===void 0;
 tout(A,n=>n.p&&n.p.className==="dzsvp-ligne",[]).find(n=>texte(n.p.children[0])==="musique_a.mp3").p.onClick();await calme();
 REP.stems={st:400,d:{detail:"fal.ai: aucune clé configurée"}};btn("separer").p.onClick();await calme();btn("separer").p.onClick();await calme();R.erreur=etat();
 AUDIO=[];META={};H=[];rendre();await calme();R.vide=etat();
 process.stdout.write(JSON.stringify(R));})().catch(e=>process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)})));
"""


def _node():
    with tempfile.TemporaryDirectory() as dd:
        h = pathlib.Path(dd) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"erreur": (p.stdout + p.stderr)[:900]}


print("[P] sous node (vraie fonction du livré)")
R = _node()
check("P0 harnais exécuté", "montage" in R, R)
m = R.get("montage", {})
check("P1 au chargement : « chargement », puis la liste sans les pistes séparées",
      R.get("charge0", {}).get("aides") == ["⟦sonvfx.pistes.chargement⟧"] and R.get("charge0", {}).get("lignes") == []
      and m.get("lignes") == ["import.wav", "musique_a.mp3", "sfx_boom.mp3"], m)
check("P2 la dernière musique générée est choisie par défaut", m.get("sel") == "musique_a.mp3", m)
check("P3 ses pistes séparées existantes sont listées, dans l'ordre voix → batterie, nommées",
      m.get("stems") == [["vocals", "⟦sonvfx.pistes.stem_voix⟧"], ["drums", "⟦sonvfx.pistes.stem_batterie⟧"]], m)
check("P4 deux modèles (6 puis 4 pistes), le défaut du serveur choisi ; sans clé : l'avertissement, bouton actif",
      m.get("modeles") == [["⟦sonvfx.pistes.modele_6⟧", "true"], ["⟦sonvfx.pistes.modele_4⟧", "false"]]
      and m.get("cle") and m.get("separer") == "⟦sonvfx.pistes.separer⟧", m)
check("P5 la durée lue du lecteur s'affiche", '"d":"1:23"' in R.get("duree", {}).get("duree", ""), R.get("duree"))
a = R.get("arme", {})
check("P6 premier clic : devis du serveur pour la durée, AUCUNE séparation, bouton « Confirmer · ~$0.058 »",
      a.get("appels") == [["/api/cost/estimate", "POST", {"kind": "stems", "duration_s": 83}]]
      and a.get("arme") and a.get("separer") == '⟦sonvfx.pistes.confirmer⟧{"prix":"~$0.058"}', a)
s = R.get("separe", {})
check("P7 second clic : une séparation de la piste choisie, avec le modèle choisi, puis la liste relue",
      [c for c in s.get("appels", []) if c[0] == "/api/audio/stems"] == [["/api/audio/stems", "POST", {"filename": "musique_a.mp3", "model": "htdemucs_6s"}]]
      and ["/api/audio", "GET", None] in s.get("appels", [])[2:] and not s.get("arme"), s)
check("P8 la note dit le nombre, le prix et les pistes absentes (nommées)",
      s.get("note") == '⟦sonvfx.pistes.separee⟧{"n":2,"usd":"0.058"} ⟦sonvfx.pistes.manquants⟧{"liste":"⟦sonvfx.pistes.stem_guitare⟧"}', s)
c = R.get("annule", {})
check("P9 armer puis Annuler : désarmé, aucune séparation",
      not c.get("arme") and not any(x[0] == "/api/audio/stems" for x in c.get("appels", [])), c)
c = R.get("modele4", {})
check("P10 le modèle 4 pistes choisi part dans la séparation",
      [x[2] for x in c.get("appels", []) if x[0] == "/api/audio/stems"] == [{"filename": "musique_a.mp3", "model": "htdemucs_ft"}]
      and c.get("modeles", [[], []])[1][1] == "true", c)
check("P11 muet : la voix se tait seule", R.get("muet") == {"v": True, "d": False}, R.get("muet"))
check("P12 solo sur la batterie : la voix reste muette même démutée",
      R.get("solo") == {"v": True, "d": False}, R.get("solo"))
check("P13 sans solo ni muet : tout s'entend", R.get("sans_solo") == {"v": False, "d": False}, R.get("sans_solo"))
check("P14 le volume d'une piste va à son lecteur", R.get("volume") == 0.4, R.get("volume"))
c = R.get("lecture", {})
check("P15 « Lire le mélange » lance toutes les pistes ensemble, le bouton devient « Mettre en pause »",
      c.get("v") == 1 and c.get("d") == 1 and (c.get("lbl") or "").strip() == "⟦sonvfx.pistes.pause⟧", c)
c = R.get("montage_go", {})
check("P16 « Aller au Montage » arrête la lecture et ouvre le Montage", c.get("aller") == ["montage"] and c.get("joue") == 0, c)
check("P17 téléchargement : le fichier de la piste, sous son nom",
      R.get("telecharger") == {"href": "/api/audio/stem_musique_a_vocals.mp3", "download": "stem_musique_a_vocals.mp3"},
      R.get("telecharger"))
check("P18 recherche sans casse dans les noms", R.get("recherche", {}).get("lignes") == ["import.wav"], R.get("recherche"))
c = R.get("autre", {})
check("P19 une autre piste : ses pistes séparées seulement (aucune), désarmé", c.get("sel") == "import.wav"
      and c.get("stems") == [] and not c.get("arme"), c)
check("P20 « Importer une piste » ouvre le sélecteur de fichiers", R.get("clic_fichier") == 1, R.get("clic_fichier"))
c = R.get("importe", {})
check("P21 import : un envoi multipart du fichier, la piste importée devient la piste choisie, note",
      [x for x in c.get("appels", []) if x[0] == "/api/audio/upload"] == [["/api/audio/upload", "POST", [["file", "ma piste.wav"]]]]
      and c.get("sel") == "ma_piste.wav" and c.get("note") == '⟦sonvfx.pistes.importee⟧{"nom":"ma_piste.wav"}', c)
check("P22 glisser au-dessus : la zone s'allume ; déposer : elle s'éteint",
      R.get("survol") == "" and R.get("survol_apres"), [R.get("survol"), R.get("survol_apres")])
c = R.get("refus", {})
check("P23 import refusé (415) : le message du serveur, rien de choisi à la place",
      c.get("note") == '⟦sonvfx.pistes.import_echec⟧{"e":"Fichier vide ou illisible : vide.wav (0 octet)"}'
      and c.get("sel") == "ma_piste.wav", c)
check("P24 séparation refusée : le message du serveur tel quel, bouton rendu",
      R.get("erreur", {}).get("note") == "fal.ai: aucune clé configurée"
      and R.get("erreur", {}).get("separer") == "⟦sonvfx.pistes.separer⟧", R.get("erreur"))
c = R.get("vide", {})
check("P25 Bibliothèque vide : l'invitation, aucune carte de séparation",
      c.get("aides") == ["⟦sonvfx.pistes.vide⟧"] and c.get("vide") == "⟦sonvfx.pistes.choisir⟧"
      and c.get("separer") is None, c)

print(f"\n{ok} PASS / {fail} FAIL")


def test_sonvfx_pistes():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
