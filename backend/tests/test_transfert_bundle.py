"""Le miroir de la couche « Transfert entre machines » dans le bundle.

Même discipline que `test_montage_bundle.py` : le patcher est CHARGÉ comme
un module (ses ancres sont des données, pas de la prose), le bloc injecté
doit ÊTRE la couche octet pour octet, et chaque section est vérifiée des
DEUX côtés — l'ancre consommée, le remplacement présent.

Ce banc épingle aussi ce que la charte impose au modal
(design_handoff_icones_couleurs §1 et §2.1) : les jetons de surface, la
mono des métadonnées, le `letter-spacing` des en-têtes, les deux niveaux
d'opacité des icônes, et l'absence d'arrondi de châssis.

Run: python tests/test_transfert_bundle.py
"""
import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
COUCHE = RACINE / "frontend" / "patches" / "transfert.js"
PATCHER = RACINE / "scripts" / "patch_bundle_transfert.py"
SERVICE = RACINE / "backend" / "app" / "services" / "transfert.py"

ok = fail = 0
_plantages = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def temoin(e):
    global _plantages
    _plantages += 1
    return f"{type(e).__name__}: {e} ·ECHEC#{_plantages}"


def NODE(args, **kw):
    """`node` peut manquer : la garde en fait un témoin, jamais une mort."""
    try:
        return subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", **kw)
    except Exception as e:                                  # noqa: BLE001
        t = temoin(e)
        print(f"  ----  node a levé : {t}")

        class Echec:
            returncode = -1
            stdout = ""
            stderr = t
        return Echec()


def load(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


for p in (BUNDLE, COUCHE, PATCHER, SERVICE):
    if not p.exists():
        print(f"  FAIL  fichier absent : {p}")
        print("\n=== 0 passed, 1 failed ===")
        sys.exit(1)

s = BUNDLE.read_text(encoding="utf-8")
src = COUCHE.read_text(encoding="utf-8")
P = load("patch_bundle_transfert", PATCHER)
crlf = "\r\n" in s


def nl(t):
    return t.replace("\n", "\r\n") if crlf else t


# ── [1] le bloc EST la couche, et les deux sections sont là ──
_i = s.find(nl(P.BEGIN))
_j = s.find(nl(P.END), _i if _i >= 0 else 0)
_bloc = s[_i:_j + len(nl(P.END))] if _i >= 0 and _j > _i else ""
check("bloc_EST_la_couche_octet_pour_octet", _bloc == nl(src).strip(),
      f"bloc={len(_bloc)} o, couche={len(nl(src).strip())} o — le bundle "
      f"n'exécute pas le fichier que ce banc mesure")
check("bloc_unique", s.count(nl(P.BEGIN)) == 1 and s.count(nl(P.END)) == 1)
for tag, a, rp in P.PATCHES:
    check(tag + "_remplace", s.count(nl(rp)) == 1, f"count={s.count(nl(rp))}")
    if a not in rp:
        check(tag + "_ancre_consommee", s.count(nl(a)) == 0)
    check("couche_ne_cite_pas_l_ancre_de_" + tag, a not in src)
check("l_ancre_d_injection_est_reprise",
      s.count(nl(P.ANCHOR_INJECT)) == 1)
# 07/09/2026 : le patcher lisait le bundle en MODE TEXTE. Les fins de ligne
# y sont repliees en LF sans le dire, le test `crlf` rendait False, et la
# reecriture aplatissait 17 204 CRLF — trois lignes de `test_montage_bundle`
# rougissaient parce qu'elles decoupent le bundle sur une ligne vide.
# La preuve se prend en OCTETS : le mode texte mentirait ici aussi.
_octets = BUNDLE.read_bytes()
check("le_bundle_garde_ses_fins_de_ligne_CRLF",
      _octets.count(b"\r\n") > 15000
      and _octets.count(b"\n") == _octets.count(b"\r\n"),
      f"CRLF={_octets.count(chr(13).encode() + chr(10).encode())} "
      f"LF={_octets.count(chr(10).encode())}")
_psrc = PATCHER.read_text(encoding="utf-8")
check("le_patcher_n_ouvre_le_bundle_qu_en_octets",
      "read_text(" not in _psrc and "write_text(" not in _psrc
      and "read_bytes()" in _psrc and "write_bytes(" in _psrc,
      "le mode texte replie les CRLF en silence")

# ── [2] les deux faces : ce que la section appelle est DÉCLARÉ ──
check("T3_appelle_DzTransfert_qui_est_declare",
      s.count("r.jsx(DzTransfert,{})") == 1
      and s.count("function DzTransfert()") == 1,
      f"appel={s.count('r.jsx(DzTransfert,{})')} "
      f"decl={s.count('function DzTransfert()')}")
check("la_categorie_et_la_section_portent_la_MEME_cle",
      'k:"transfert"' in s and 's==="transfert"' in s)
check("la_categorie_est_la_derniere_de_la_liste",
      '{k:"transfert",l:"Transfert entre machines"}]' in s)
# la couche n'emploie que ce que le bundle lui offre — pas de React global
check("la_couche_emploie_le_runtime_du_bundle_et_pas_un_React_global",
      "React." not in src and "window.__dzR" not in src
      and "r.jsx(" in src and "x.useState(" in src)

# ── [3] la couche s'exécute : node la charge avec des bouchons ──
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dztrb_"))
shim = TMP / "shim.js"
shim.write_text(
    '"use strict";\n'
    "var appels=[];\n"
    "var r={jsx:function(t,p,k){return {t:t,p:p,k:k}},"
    " jsxs:function(t,p,k){return {t:t,p:p,k:k}}};\n"
    "var x={useState:function(v){return [v,function(){}]},"
    " useRef:function(v){return {current:v}},"
    " useEffect:function(f){appels.push('effet')}};\n"
    + src.replace("\r\n", "\n") + "\n"
    "var vue=DzTransfert();\n"
    "function texte(n){ if(n==null||typeof n!=='object')return String(n||'');\n"
    "  var p=n.p||{}, out='';\n"
    "  if(typeof p.children==='string')out+=p.children;\n"
    "  else if(Array.isArray(p.children))p.children.forEach(function(c){out+=texte(c)});\n"
    "  else if(p.children)out+=texte(p.children);\n"
    "  return out; }\n"
    "console.log(JSON.stringify({\n"
    "  effets: appels.length,\n"
    "  racine: vue.t,\n"
    "  texte: texte(vue),\n"
    "  octets: [dztOctets(0), dztOctets(900), dztOctets(1536),\n"
    "           dztOctets(5e9), dztOctets(-3), dztOctets(null)],\n"
    "  barre0: dztBarre(0).p.children.p.style.width,\n"
    "  barre50: dztBarre(50).p.children.p.style.width,\n"
    "  barreHors: [dztBarre(-10).p.children.p.style.width,\n"
    "              dztBarre(999).p.children.p.style.width],\n"
    "  barreRayon: JSON.stringify(dztBarre(10).p.style),\n"
    "  iconeExport: JSON.stringify(dztIcone('export',16)),\n"
    "  iconeImport: JSON.stringify(dztIcone('import',16))\n"
    "}));\n", encoding="utf-8")
rn = NODE(["node", str(shim)])
check("js_la_couche_s_execute_sous_node", rn.returncode == 0,
      (rn.stderr or "")[-300:])
d = {}
if rn.returncode == 0:
    try:
        import json
        d = json.loads(rn.stdout.strip().splitlines()[-1])
    except Exception as e:                                  # noqa: BLE001
        check("js_sortie_lisible", False, temoin(e))
        d = {}

check("js_l_ecran_annonce_les_deux_gestes",
      "texte" in d and "Exporter…" in d["texte"] and "Importer…" in d["texte"],
      str(d.get("texte"))[:160])
check("js_l_ecran_DIT_que_les_cles_restent",
      "texte" in d and "clés d'API restent ici" in d["texte"],
      str(d.get("texte"))[:200])
check("js_les_octets_se_lisent_en_unites_humaines",
      d.get("octets") == ["0 o", "900 o", "1.5 Ko", "4.7 Go", "-3 o", "0 o"],
      str(d.get("octets")))
check("js_la_barre_suit_le_pourcentage",
      d.get("barre0") == "0%" and d.get("barre50") == "50%",
      f"{d.get('barre0')} / {d.get('barre50')}")
check("js_la_barre_borne_les_valeurs_hors_champ",
      d.get("barreHors") == ["0%", "100%"], str(d.get("barreHors")))
check("js_la_barre_n_a_AUCUN_arrondi",
      "barreRayon" in d and "adius" not in d["barreRayon"],
      str(d.get("barreRayon")))
# §2.1 : deux niveaux d'opacité, masses pleines, aucun contour
for sens in ("Export", "Import"):
    ic = d.get("icone" + sens, "")
    check(f"js_l_icone_{sens.lower()}_suit_le_2_1_du_handoff",
          '"opacity":".38"' in ic and '"fill":"currentColor"' in ic
          and '"viewBox":"0 0 24 24"' in ic and "stroke" not in ic,
          ic[:150])
check("js_les_deux_icones_different",
      d.get("iconeExport") != d.get("iconeImport"))

# ── [4] la charte : jetons, mono, en-têtes ──
check("charte_les_surfaces_viennent_des_JETONS_du_handoff",
      "--srf-panel" in src and "--srf-raised" in src
      and "--brd-hard" in src and "--txt-hi" in src and "--txt-mid" in src)
check("charte_les_metadonnees_sont_en_IBM_Plex_Mono",
      "IBM Plex Mono" in src and src.count("DZT_MONO") >= 4)
check("charte_les_en_tetes_capitales_portent_le_letter_spacing",
      'letterSpacing: ".12em"' in src and 'textTransform: "uppercase"' in src)
check("charte_aucun_arrondi_de_chassis",
      "borderRadius" not in src)
check("le_modal_est_un_vrai_dialogue_pour_le_lecteur_d_ecran",
      'role: "dialog"' in src and '"aria-modal": "true"' in src
      and '"aria-label"' in src)
check("le_modal_ne_se_ferme_PAS_pendant_le_travail",
      'if (job && job.statut === "en cours") return;' in src)

# ── [5] l'écran et le service parlent des mêmes routes ──
svc = SERVICE.read_text(encoding="utf-8")
for route in ("/api/transfer/destinations", "/api/transfer/export",
              "/api/transfer/import", "/api/transfer/inspect",
              "/api/transfer/jobs/"):
    check("l_ecran_appelle_" + route.split("/")[-1].strip("/") or "jobs",
          route in src, route)
check("le_service_porte_les_exclusions_que_l_ecran_promet",
      "SECRETS" in svc and ".env" in svc and "logs/*" in svc)
check("le_service_ne_copie_JAMAIS_la_base_en_octets",
      "s.backup(t)" in svc and "shutil.copyfile(src, dst)" not in svc)
check("le_service_reancre_les_chemins_absolus",
      "def reancrer(" in svc and "COLONNES_CHEMIN" in svc)
check("l_import_FUSIONNE_et_n_ecrase_pas",
      "insert or ignore into" in svc and "insert or replace into" not in svc)

check("aucun_appel_n_a_plante", _plantages == 0, f"{_plantages} plantage(s)")
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
