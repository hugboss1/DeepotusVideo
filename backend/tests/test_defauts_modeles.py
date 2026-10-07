"""t130 (W-d du plan 2026-07-22-modeles-generation-onthefly) : modèle VIDÉO et modèle TTS par défaut des NOUVEAUX
nœuds, réglés dans Settings → Provider defaults. Les nœuds naissent avec ces défauts (la fabrique `Y` du Studio),
chacun peut ensuite dévier (les panneaux de nœud existants) ; les nœuds existants et les graphes chargés (passés par
`ts`) ne changent pas.

  [1] sous node : le bloc pur de la couche montage (balisé /*__T130_DEBUT__*/ … /*__T130_FIN__*/) — lecture et
      écriture dans `deepotus.provider_defaults` sans toucher aux autres clés (video, voice… = des NOMS DE CLÉ),
      `dzPropsNaissance` pour Seedance et Voiceover seulement, jamais l'objet d'entrée muté.
  [2] le bundle : le composant monté dans Provider defaults, la fabrique passe par dzPropsNaissance, et le registre
      `Me` comme la normalisation `ts` sont octet pour octet ceux de main (rien ne change pour un graphe chargé).
Run : & $PY tests/test_defauts_modeles.py   (depuis backend/)
"""
import json, os, pathlib, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
REL = "frontend/dist/assets/index-BEOJX8L5.js"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


COUCHE = (RACINE / "frontend/patches/montage.js").read_text("utf-8")
m = re.search(r"/\*__T130_DEBUT__\*/(.*?)/\*__T130_FIN__\*/", COUCHE, re.S)
check("1a_le_bloc_pur_est_balise_dans_la_couche", m is not None)
if m and NODE:
    HARNAIS = r"""
const bloc = process.argv[1];
const magasin = {};
const localStorage = { getItem: (k) => (k in magasin ? magasin[k] : null), setItem: (k, v) => { magasin[k] = String(v); } };
const f = new Function("localStorage", bloc + "\n;return { dzDefautsLire, dzDefautsEcrire, dzPropsNaissance, DZ_DEFAUTS_CLE };");
const o = f(localStorage);
const K = o.DZ_DEFAUTS_CLE, res = {};
res.vide = o.dzDefautsLire();
magasin[K] = "{pas du json";
res.casse = o.dzDefautsLire();
magasin[K] = JSON.stringify({ video: "FAL_KEY", voice: "ELEVENLABS_API_KEY", video_model: 42, tts_model: "eleven_v3" });
res.types = o.dzDefautsLire();
o.dzDefautsEcrire("video_model", "kling-v3-pro");
res.apres_ecrire = JSON.parse(magasin[K]);
o.dzDefautsEcrire("tts_model", "");
res.apres_effacer = JSON.parse(magasin[K]);
let refus = 0;
try { o.dzDefautsEcrire("video", "x"); } catch (e) { refus++; }
try { o.dzDefautsEcrire("video_model", "a b/../c"); } catch (e) { refus++; }
res.refus = refus;
magasin[K] = JSON.stringify({ video_model: "kling-v3-pro", tts_model: "eleven_flash_v2_5" });
const seed = { model: "seedance-2.5", style: "cinematic", durationS: 10 };
res.seed = o.dzPropsNaissance("Seedance", seed);
res.seed_intact = seed.model;
res.voix = o.dzPropsNaissance("Voiceover", { provider: "elevenlabs", model: "", tune: null });
res.image = o.dzPropsNaissance("ImageGen", { model: "flux" });
magasin[K] = "{}";
res.seed_sans = o.dzPropsNaissance("Seedance", { model: "seedance-2.5" });
res.voix_sans = o.dzPropsNaissance("Voiceover", { model: "" });
res.voix_garde = o.dzPropsNaissance("Voiceover", { model: "eleven_v3" });
magasin[K] = "[1,2]";
res.tableau = o.dzDefautsLire();
o.dzDefautsEcrire("tts_model", "eleven_v3");
res.tableau_ecrit = JSON.parse(magasin[K]);
magasin[K] = JSON.stringify({ video_model: "../evil", tts_model: "<b>" });
res.seed_sale = o.dzPropsNaissance("Seedance", { model: "seedance-2.5" });
process.stdout.write(JSON.stringify(res));
"""
    r = subprocess.run([NODE, "-e", HARNAIS, m.group(1)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        check("1b_le_bloc_s_evalue_sous_node", False, r.stderr[-600:])
    else:
        R = json.loads(r.stdout)
        check("1b_lecture_vide_ou_cassee_rend_des_defauts_vides", R["vide"] == R["casse"] == {"video_model": "", "tts_model": ""}, R)
        check("1c_lecture_une_valeur_non_chaine_tombe", R["types"] == {"video_model": "", "tts_model": "eleven_v3"}, R["types"])
        check("1d_ecrire_garde_les_noms_de_cle_des_roles", R["apres_ecrire"] == {"video": "FAL_KEY", "voice": "ELEVENLABS_API_KEY",
              "video_model": "kling-v3-pro", "tts_model": "eleven_v3"}, R["apres_ecrire"])
        check("1e_une_valeur_vide_retire_le_defaut", "tts_model" not in R["apres_effacer"] and R["apres_effacer"]["video"] == "FAL_KEY", R["apres_effacer"])
        check("1f_refuse_une_cle_de_role_ou_un_id_hors_patron", R["refus"] == 2, R["refus"])
        check("1g_seedance_nait_avec_le_modele_video_par_defaut", R["seed"] == {"model": "kling-v3-pro", "style": "cinematic", "durationS": 10}
              and R["seed_intact"] == "seedance-2.5", R["seed"])
        check("1h_voiceover_nait_avec_le_modele_tts_par_defaut", R["voix"] == {"provider": "elevenlabs", "model": "eleven_flash_v2_5", "tune": None}, R["voix"])
        check("1i_les_autres_types_ne_bougent_pas", R["image"] == {"model": "flux"}, R["image"])
        check("1j_sans_defaut_les_props_du_registre", R["seed_sans"] == {"model": "seedance-2.5"} and R["voix_sans"] == {"model": ""},
              [R["seed_sans"], R["voix_sans"]])
        check("1l_sans_defaut_tts_un_voiceover_garde_son_modele", R["voix_garde"] == {"model": "eleven_v3"}, R["voix_garde"])
        check("1m_un_tableau_stocke_compte_pour_vide_et_l_ecriture_repart_d_un_objet", R["tableau"] == {"video_model": "", "tts_model": ""}
              and R["tableau_ecrit"] == {"tts_model": "eleven_v3"}, [R["tableau"], R["tableau_ecrit"]])
        check("1k_un_id_stocke_hors_patron_est_ignore", R["seed_sale"] == {"model": "seedance-2.5"}, R["seed_sale"])

B = (RACINE / REL).read_bytes().decode("utf-8")
# t131 : le témoin est main AVANT t130 (e58280c9) — origin/main contient t130 depuis sa fusion, son ancre
# props:{...L.props||{}} n'y figure plus et 2g rougissait sur main même.
H = subprocess.run(["git", "show", f"e58280c9:{REL}"], cwd=str(RACINE), capture_output=True).stdout.decode("utf-8")


def entre(s, a, z):
    i = s.index(a)
    return s[i:s.index(z, i)]


check("2a_monte_dans_provider_defaults_apres_la_voix",
      B.count('r.jsx(DzVoiceProvider,{},"voiceprov"),r.jsx(DzModelDefaults,{},"modeldefaults"),') == 1
      and B.count("function DzModelDefaults(") == 1)
check("2b_la_fabrique_fait_naitre_par_dzPropsNaissance", B.count("props:dzPropsNaissance(R,{...L.props||{}})") == 1
      and B.count("props:{...L.props||{}}") == 0)
check("2c_registre_Me_et_normalisation_ts_inchanges", entre(B, "Me={Image:{", "};") == entre(H, "Me={Image:{", "};")
      and entre(B, "function ts(e){", "function Lh(") == entre(H, "function ts(e){", "function Lh("))
sys.path.insert(0, str(RACINE / "scripts"))
try:
    import patch_bundle_montage as PM
    paires = PM.T130_NATIF
except Exception as e:                        # le banc rougit, ne meurt pas
    paires = None
    print(f"  (patcher illisible : {e!r})")
check("2g_les_paires_consignees_au_patcher_sont_celles_du_bundle_hors_de_PATCHES",
      paires is not None and len(paires) == 2 and all(B.count(r) == 1 and H.count(a) == 1 for _n, a, r in paires)
      and not any(n.startswith("P10md") for n, _a, _r in PM.PATCHES), paires and [n for n, _a, _r in paires])
check("2d_les_selecteurs_reutilises_existent", B.count("function DzVideoModelSel(") == 1 and B.count("function DzVoModelSel(") == 1)
check("2e_aucun_etat_x_useState_de_plus", B.count("x.useState(") == H.count("x.useState("), (B.count("x.useState("), H.count("x.useState(")))
r = subprocess.run([NODE, "--check", str(RACINE / REL)], capture_output=True, text=True) if NODE else None
check("2f_bundle_node_check", r is not None and r.returncode == 0, r and r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
