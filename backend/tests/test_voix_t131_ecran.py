"""t131 — l'écran : le fournisseur de voix choisi PAR GÉNÉRATION dans Quick (mémorisé, localStorage
dz_voice_provider) et dans le nœud Voiceover (prop `vo_provider`, absente = Auto : la prop historique `provider`
vaut "elevenlabs" dans TOUS les nœuds existants sans que personne l'ait choisie, elle n'est donc pas lue) ;
le sélecteur de voix liste le catalogue de CE fournisseur ; Voicebox masque le modèle et le réglage fin ElevenLabs
et coûte 0 ; le graphe porte le duckDb de l'AudioMix jusqu'au Render.

  [1] sous node : le bloc pur de la couche montage (/*__T131_DEBUT__*/ … /*__T131_FIN__*/).
  [2] le bundle : chaque substitution native (consignées T131_NATIF, hors de PATCHES) une fois, et plus aucun
      « v1 gère ElevenLabs seul ».
Run : & $PY tests/test_voix_t131_ecran.py   (depuis backend/)
"""
import json, pathlib, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as AIDE  # noqa: E402  (t142 : la traduction L2 passe le bloc et les paires par dzT)
COUCHE = (RACINE / "frontend/patches/montage.js").read_text("utf-8")
m = re.search(r"/\*__T131_DEBUT__\*/(.*?)/\*__T131_FIN__\*/", COUCHE, re.S)
check("1a_le_bloc_pur_est_balise", m is not None)
if m and NODE:
    HARNAIS = r"""
const bloc = process.argv[1];
const magasin = {};
const localStorage = { getItem: (k) => (k in magasin ? magasin[k] : null), setItem: (k, v) => { magasin[k] = String(v); } };
const f = new Function("localStorage", bloc + "\n;return { dzVoFournisseurEffectif, dzVoFournisseurOptions, dzVoLocalLire, dzVoLocalPoser, dzVoDuck };");
const o = f(localStorage);
const P = (res, eleven, vbox) => ({ providers: [{ id: "elevenlabs", label: "ElevenLabs", ready: eleven }, { id: "voicebox", label: "Voicebox (local)", ready: vbox }], configured: "", resolved: res });
const R = {};
R.charge = o.dzVoFournisseurEffectif(undefined, "");
R.auto = o.dzVoFournisseurEffectif(P("elevenlabs", true, true), "");
R.choisi = o.dzVoFournisseurEffectif(P("elevenlabs", true, true), "voicebox");
R.indispo = o.dzVoFournisseurEffectif(P("elevenlabs", true, false), "voicebox");
R.aucun = o.dzVoFournisseurEffectif(P(null, false, false), "");
R.inconnu = o.dzVoFournisseurEffectif(P("elevenlabs", true, true), "openai");
R.options = o.dzVoFournisseurOptions(P("voicebox", false, true));
R.lu0 = o.dzVoLocalLire();
o.dzVoLocalPoser("voicebox"); R.lu1 = o.dzVoLocalLire();
o.dzVoLocalPoser("zz"); R.lu2 = o.dzVoLocalLire();
o.dzVoLocalPoser(""); R.lu3 = o.dzVoLocalLire();
magasin.dz_voice_provider = "openai"; R.lu4 = o.dzVoLocalLire();
R.duck = o.dzVoDuck({ file: "v.mp3" }, { type: "AudioMix", props: { duckDb: -8 } });
R.duck0 = o.dzVoDuck({ file: "v.mp3" }, { type: "AudioMix", props: { duckDb: 0 } });
R.sansMix = o.dzVoDuck({ file: "v.mp3" }, null);
R.sansVo = o.dzVoDuck(null, { props: { duckDb: -8 } });
R.defaut = o.dzVoDuck({ file: "v.mp3" }, { type: "AudioMix", props: {} });
process.stdout.write(JSON.stringify(R));
"""
    # t142 (09/10) : le bloc appelle dzT (globale) — prélude dans sa propre portée, dzT publié sur globalThis, en
    # français : les libellés attendus ci-dessous restent ceux d'avant
    # (le dictionnaire dépasse la ligne de commande Windows : le harnais passe par un fichier, le bloc devient argv[2])
    import tempfile
    _fh = pathlib.Path(tempfile.mkdtemp(prefix="dzt131_")) / "h.js"
    _fh.write_text("(function(){\n" + AIDE.PRELUDE_DZT + "\n})();\n" + HARNAIS.replace("process.argv[1]", "process.argv[2]"), "utf-8")
    r = subprocess.run([NODE, str(_fh), m.group(1)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        check("1b_le_bloc_s_evalue_sous_node", False, r.stderr[-600:])
    else:
        R = json.loads(r.stdout)
        check("1b_chargement_pas_pret", R["charge"]["ok"] is False and R["charge"]["etat"] == "chargement", R["charge"])
        check("1c_auto_suit_le_fournisseur_resolu", R["auto"] == {"id": "elevenlabs", "ok": True, "etat": "auto"}, R["auto"])
        check("1d_un_choix_pret_l_emporte", R["choisi"] == {"id": "voicebox", "ok": True, "etat": "choisi"}, R["choisi"])
        check("1e_un_choix_indisponible_n_est_jamais_remplace_en_silence", R["indispo"] == {"id": "voicebox", "ok": False, "etat": "indisponible"}, R["indispo"])
        check("1f_aucune_voix", R["aucun"] == {"id": "", "ok": False, "etat": "aucun"}, R["aucun"])
        check("1g_un_choix_inconnu_vaut_auto", R["inconnu"] == R["auto"], R["inconnu"])
        check("1h_options_auto_puis_chaque_fournisseur_et_son_etat",
              R["options"] == [{"value": "", "label": "Auto (Voicebox (local))"}, {"value": "elevenlabs", "label": "ElevenLabs — indisponible"},
                               {"value": "voicebox", "label": "Voicebox (local)"}], R["options"])
        check("1i_choix_quick_memorise_et_borne", R["lu0"] == "" and R["lu1"] == "voicebox" and R["lu2"] == "" and R["lu3"] == "" and R["lu4"] == "",
              [R["lu0"], R["lu1"], R["lu2"], R["lu3"], R["lu4"]])
        check("1j_ducking_porte_le_duckDb_de_l_AudioMix", R["duck"] == {"file": "v.mp3", "duck_db": -8} and R["defaut"] == {"file": "v.mp3", "duck_db": -8}, [R["duck"], R["defaut"]])
        check("1k_sans_AudioMix_ou_duckDb_nul_pas_de_ducking", R["duck0"] == {"file": "v.mp3"} and R["sansMix"] == {"file": "v.mp3"} and R["sansVo"] is None,
              [R["duck0"], R["sansMix"], R["sansVo"]])

B = (RACINE / "frontend/dist/assets/index-BEOJX8L5.js").read_bytes().decode("utf-8")
sys.path.insert(0, str(RACINE / "scripts"))
try:
    import patch_bundle_montage as PM
    paires = PM.T131_NATIF
except Exception as e:
    paires = None
    print(f"  (patcher illisible : {e!r})")
# t142 (09/10) : les paires sont celles que le patcher AMONT a posées ; la traduction L2 en a repris certaines
# (libellés passés par dzT) — contrôlées sur le bundle d'AVANT la traduction
B0 = AIDE.avant_i18n(B)
check("2a_paires_consignees_hors_de_PATCHES_et_chacune_une_fois_au_bundle",
      paires is not None and len(paires) >= 15 and all(B0.count(r) == 1 for _n, _a, r in paires)
      and not any(n.startswith("T131") for n, _a, _r in PM.PATCHES), paires and [n for n, _a, r in paires if B0.count(r) != 1])
check("2b_plus_aucun_v1_gere_ElevenLabs_seul", "v1 gère ElevenLabs seul" not in B)
check("2c_le_selecteur_de_voix_recoit_le_fournisseur_dans_Quick_et_le_noeud",
      B.count("r.jsx(DzVoicePicker,{provider:dzVp.id,") == 2)
check("2d_la_generation_porte_le_fournisseur", B.count('name:"quick_vo",provider:dzVp.id||void 0}') == 1 and B.count('name:"studio_vo",provider:dzVp.id||void 0}') == 1)
check("2e_le_graphe_porte_le_ducking_jusqu_au_Render", B.count("return dzVoDuck(vo,dzMix)}") == 1)
check("2f_composant_DzVoFournisseur_monte_dans_les_deux_ecrans", B.count("r.jsx(DzVoFournisseur,{prov:prov,") == 2 and B.count("function DzVoFournisseur(") == 1)
r = subprocess.run([NODE, "--check", str(RACINE / "frontend/dist/assets/index-BEOJX8L5.js")], capture_output=True, text=True) if NODE else None
check("2g_bundle_node_check", r is not None and r.returncode == 0, r and r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
