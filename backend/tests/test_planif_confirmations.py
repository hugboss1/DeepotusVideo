# -*- coding: utf-8 -*-
"""Planificateur, confirmer avant de publier ou de supprimer (20/10/2026, relevé du catalogue t248) — « Envoyer
maintenant » (vue Routage) et l'envoi de l'inspecteur publiaient au premier clic, « Supprimer » effaçait un post sans
corbeille. Le maillon de queue `dzschedconf` (scripts/patch_bundle_dzschedconf.py, APRÈS dzdock) les fait passer par
`window.__dzDialogue.confirmer` ; annuler = rien n'est envoyé ni supprimé.
Sections :
  [A] câblage dans le livré : plus d'appel nu, confirmation AVANT l'appel, dialogues `danger` ;
  [F] sous node, avec les VRAIES fonctions extraites du livré (H, N, V, __dzSchedCanaux, table _t) : annuler n'appelle
      rien, confirmer appelle une fois, le message nomme le post et ses canaux ;
  [D] chaîne : sans le maillon = la base octet pour octet ; aller-retour ; comptes figés ; octets / CRLF ;
  [K] textes : clés FR ET EN dans planif_confirmer.json (scheduler.json est écrit par i18n_l2_generer), mêmes variables,
      dictionnaire assemblé.
Run (depuis backend/) : & $PY tests/test_planif_confirmations.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
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
        print(f"  FAIL  {label} {str(detail)[:500]}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
BASE = "efd047f7"            # origin/main (#399 fusionnée), dzdock en queue
CONF = "await window.__dzDialogue.confirmer("

# ── [A] câblage ───────────────────────────────────────────────────────────────────────────────────────────────────
print("[A] câblage dans le livré")
check("A1 plus d'envoi nu dans la vue Routage (H)",
      'async function H(){l(!0),u("");const I=await D.fireScheduledPost(e.id);' not in BUNDLE)
check("A2 plus d'envoi nu dans l'inspecteur (N)",
      'async function N(){y(!0),v("");const j=await D.fireScheduledPost(e.id);' not in BUNDLE)
check("A3 plus de suppression nue (V)",
      'async function V(){j&&(await D.deleteScheduledPost(j.id)' not in BUNDLE)
for nom, debut, appel in (("H", "async function H(){if(!" + CONF, "D.fireScheduledPost(e.id)"),
                          ("N", "async function N(){if(!" + CONF, "D.fireScheduledPost(e.id)"),
                          ("V", "async function V(){if(!j||!" + CONF, "D.deleteScheduledPost(j.id)")):
    i = BUNDLE.find(debut)
    corps = BUNDLE[i:i + 700] if i >= 0 else ""
    check(f"A4 {nom} : la confirmation précède l'appel, dialogue danger, sortie si refus",
          i >= 0 and corps.find(appel) > corps.find("danger:!0}))return;") > 0, corps[:300])
check("A5 les deux envois disent le post et ses canaux, bouton « Publier »",
      BUNDLE.count('dzT("scheduler.envoi.question",{titre:e.title||"",canaux:__dzSchedCanaux(e.channels)}),'
                   '{titre:dzT("scheduler.envoi.titre"),ok:dzT("scheduler.envoi.publier"),danger:!0})') == 2)
check("A6 __dzSchedCanaux posée une fois, devant la table des canaux _t",
      BUNDLE.count("function __dzSchedCanaux(") == 1
      and 0 < BUNDLE.find("function __dzSchedCanaux(") < BUNDLE.find('const _t={x:{id:"x",label:"X",'))

# ── [F] sous node ─────────────────────────────────────────────────────────────────────────────────────────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
function tranche(a,b){const i=S.indexOf(a);if(i<0)throw new Error("introuvable : "+a);const j=S.indexOf(b,i);
 if(j<0)throw new Error("fin introuvable : "+b);return S.slice(i,j)}
const CAN=tranche("function __dzSchedCanaux(","const _t=");
const T="const _t="+tranche('{x:{id:"x",label:"X",',",Bu=Object.values(_t)")+";";
const SH=tranche("async function H(){","const F=e.runAt");
const SN=tranche("async function N(){","async function P(){");
const SV=tranche("async function V(){","return r.jsxs(");
let APPELS=[],DIAL=[],REP=true;
function dzT(k,v){return k+(v?JSON.stringify(v):"")}
const window={__dzDialogue:{confirmer:(m,o)=>{DIAL.push([m,o]);return Promise.resolve(REP)}}};
const D={fireScheduledPost:id=>{APPELS.push(["fire",id]);return Promise.resolve({ok:true,sent:["x"]})},
 deleteScheduledPost:id=>{APPELS.push(["delete",id]);return Promise.resolve({deleted:id})}};
const l=()=>{},u=()=>{},y=()=>{},v=()=>{},n=null,d=null,o=null;
let e={id:"p1",title:"Lancement",channels:["x","telegram","mastodon"]},j={id:"p2",title:"Brouillon"};
eval(T+CAN+SH+SN+SV);
async function cas(nom,f,rep){APPELS=[];DIAL=[];REP=rep;await f();return {nom,appels:APPELS,dial:DIAL}}
(async()=>{const R=[];
 R.push(await cas("H_annule",H,false));R.push(await cas("H_ok",H,true));
 R.push(await cas("N_annule",N,false));R.push(await cas("N_ok",N,true));
 R.push(await cas("V_annule",V,false));R.push(await cas("V_ok",V,true));
 e={id:"p3",title:"",channels:[]};R.push(await cas("H_sans_canal",H,true));
 j=null;R.push(await cas("V_sans_post",V,true));
 process.stdout.write(JSON.stringify(R));})().catch(e=>{process.stdout.write(JSON.stringify({erreur:String(e&&e.stack||e)}))});
"""


def _node():
    with tempfile.TemporaryDirectory() as dd:
        h = pathlib.Path(dd) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout)
    except Exception:  # noqa: BLE001
        return {"erreur": (p.stdout + p.stderr)[:800]}


print("[F] sous node (vraies fonctions du livré)")
NR = _node()
C = {c["nom"]: c for c in NR} if isinstance(NR, list) else {}
check("F0 harnais exécuté", bool(C), NR)
for nom in ("H", "N"):
    a, b = C.get(nom + "_annule", {}), C.get(nom + "_ok", {})
    check(f"F1 {nom} annulé : une question, AUCUN envoi", len(a.get("dial", [])) == 1 and a.get("appels") == [], a)
    check(f"F2 {nom} confirmé : un seul envoi du bon post", b.get("appels") == [["fire", "p1"]], b)
    m, o = (b.get("dial") or [["", {}]])[0]
    check(f"F3 {nom} : le message nomme le post et ses canaux en clair (inconnu gardé tel quel), bouton Publier, danger",
          m.startswith("scheduler.envoi.question") and '"titre":"Lancement"' in m
          and '"canaux":"X, Telegram, mastodon"' in m and o.get("danger") is True
          and o.get("ok") == "scheduler.envoi.publier" and o.get("titre") == "scheduler.envoi.titre", b)
a, b = C.get("V_annule", {}), C.get("V_ok", {})
check("F4 V annulé : une question, AUCUNE suppression", len(a.get("dial", [])) == 1 and a.get("appels") == [], a)
check("F5 V confirmé : une seule suppression du bon post", b.get("appels") == [["delete", "p2"]], b)
m, o = (b.get("dial") or [["", {}]])[0]
check("F6 V : message « définitif » qui nomme le post, bouton Supprimer, danger",
      m.startswith("scheduler.post.supprimer_q") and '"titre":"Brouillon"' in m and o.get("danger") is True
      and o.get("ok") == "scheduler.post.supprimer", b)
c = C.get("H_sans_canal", {})
check("F7 sans canal : le message dit « aucun canal »",
      'scheduler.envoi.aucun_canal' in ((c.get("dial") or [[""]])[0][0]), c)
c = C.get("V_sans_post", {})
check("F8 V sans post sélectionné : ni question ni appel", c.get("dial") == [] and c.get("appels") == [], c)

# ── [D] chaîne ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[D] chaîne dzschedconf")
try:
    import patch_bundle_dzschedconf as PS
except Exception as e:  # noqa: BLE001
    PS = None
    print(f"  (maillon introuvable : {e})")


BUN_OCTETS_T280 = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes()


def _base_bytes():
    r_ = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True,
                        cwd=str(RACINE))
    b_ = r_.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")     # le dépôt garde le bundle en LF
    # t280 : la couche sonvfx retouchée après BASE (L4 + G1) — le bloc SONVFX attendu est celui du livré
    return __import__("_i18n_l1_aide").base_avec_couches_livrees(b_, BUN_OCTETS_T280)


check("D1 maillon présent", PS is not None)
check("D2 sans le maillon (avant_dzschedconf) = la base octet pour octet",
      lambda: __import__("_i18n_l1_aide").avant_dzschedconf(BUNDLE).encode("utf-8") == _base_bytes())
check("D3 avant_dzdock défait dzschedconf d'abord",
      lambda: "__dzSchedCanaux" not in __import__("_i18n_l1_aide").avant_dzdock(BUNDLE))
check("D4 aller-retour exact", lambda: PS.appliquer(PS.defaire(BUNDLE)) == BUNDLE)
check("D5 comptes figés : x.useState( 731, DzTracks 181, v2.8.0 ×4, confirmer ×28, aucun hook neuf",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("DzTracks") == 181 and BUNDLE.count("v2.8.0") == 4
      and __import__("_i18n_l1_aide").avant_dzconstats(BUNDLE).count(CONF) == 28)   # sans le maillon aval dzconstats
check("D6 octets : CRLF partout", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
_src = (RACINE / "scripts" / "patch_bundle_dzschedconf.py").read_bytes().decode("utf-8")
check("D7 le maillon lit en octets", "read_text(" not in _src and "write_text(" not in _src)
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzschedconf.py"), "--check"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                    env=dict(__import__("os").environ, PYTHONIOENCODING="utf-8"))
check("D8 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)
check("D9 pas de .bak_dzschedconf laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzschedconf")).exists())

# ── [K] textes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "planif_confirmer.json").read_text(encoding="utf-8"))
CLES = ["scheduler.envoi.question", "scheduler.envoi.titre", "scheduler.envoi.publier", "scheduler.envoi.aucun_canal",
        "scheduler.post.supprimer_q", "scheduler.post.supprimer_titre"]
check("K0 le fichier ne porte que ces clés, à trois segments", sorted(DICO) == sorted(CLES)
      and all(len(k.split(".")) == 3 for k in CLES), sorted(DICO))
for k in CLES:
    v = DICO.get(k) or {}
    check(f"K1 {k} : FR et EN, mêmes variables, littérale dans le livré",
          v.get("fr") and v.get("en") and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
          and f'"{k}"' in BUNDLE, v)
src_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K2 dictionnaire assemblé (source = copie de dist)",
      all(k.encode() in src_dico for k in CLES)
      and src_dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")


def test_planif_confirmations():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
