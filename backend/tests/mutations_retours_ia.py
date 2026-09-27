# -*- coding: utf-8 -*-
"""Banc de mutations des RETOURS DU 26/09 ET DES CHAMPS IA (plan du 27/09/2026,
tache 11) : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/, le
ffmpeg de l'APPLICATION (9.0.1) en tete du PATH :

    python tests/mutations_retours_ia.py            # toutes
    python tests/mutations_retours_ia.py 0 7 14     # celles-la
    python tests/mutations_retours_ia.py --pre-vol  # le pre-vol seul

MODELE EXACT : `mutations_retours_l6.py` (5-uplets, mutation en OCTETS avec
fin de ligne MESUREE, `ecrire()` avec retentatives, sha256 restaure dans
`finally` par application INVERSE -- jamais un `git checkout` --, etat MORT
distinct de ROUGE, compte declare `N_ROUGES`, pre-vol de la chaine).

PRE-VOL : `repatch_all.py --list` doit rendre `montage` PUIS `dzcout` ; sinon
sortie code 2, rien n'est mute.

LU PAR CODE DE SORTIE, jamais par grep : 0 quand TOUTES les mutations sont
ROUGES sur les lignes nommees ET au compte declare, 1 des qu'une survit, meurt,
rougit ailleurs ou plus / moins que la table ne le dit.

CE QU'IL MUTE (les huit themes du plan, A B C D F I H G) :
  A  `montage_service.py`, l'horloge du rendu (T1)      -> `retours_horloge`
  B  `montage_service.py` / `grading.py`, grade-frame
     avec retime, stabilisation et piste J1 (T2)        -> `retours_grade`
  C  `frontend/patches/montage.js`, les scopes en plein
     ecran (T3), la COUCHE jouee sous node              -> `edition`
  D  `scripts/patch_bundle_montage.py` (section R7up1,
     T4) : patcher mute PUIS chaine rejouee (`repatch_all.py --from montage`),
     banc joue, patcher RESTAURE puis chaine rejouee ; le sha256 du patcher,
     du bundle ET du `.bak_dzcout` d'apres est compare a celui d'avant ; une
     chaine qui ne se rejoue pas = MORT                  -> `retours_bundle_r7`
  F  `fal_service.py`, `routes.py`, `pricing.py` (T5)   -> `video_models`,
                                                           `seedance_garde`
  I  `image_providers.py`, `material_store.py` (T6)     -> `gpt_image_25`
  H  `dictation_service.py` (T7) et la couche
     `dz-champ-ia.js` (T10)                             -> `dictation`,
                                                           `champ_ia`
  G  la couche `dz-champ-ia.js` (T8, T9)                -> `champ_ia`
LA COUCHE `frontend/shared/dz-champ-ia.js` a une copie OCTET POUR OCTET dans
`frontend/dist/shared/` (le banc `champ_ia` les compare) : ses mutations
portent sur LES DEUX (`JUMEAUX`), restaurees et comparees au sha256 toutes
deux.

AUCUN reseau, AUCUNE depense : fal, OpenAI, la transcription sont des espions
ou des bouchons dans chaque banc ; `retours_horloge` et `retours_grade` jouent
ffmpeg reel sur des sources lavfi generees en TMP.

RESULTAT MESURE le 27/09/2026 (worktree practical-tu-925076, sommet 4eb85c5,
python embarque, ffmpeg 9.0.1 de l'application en tete du PATH, un processus
par execution de banc, campagne ENTIERE jouee deux fois : la premiere pour
MESURER, la seconde pour PROUVER) : LES VINGT-TROIS SONT ROUGES, AUCUN
SURVIVANT, AUCUN MORT ; sha256 identiques avant / apres chaque mutation
(patcher, bundle et .bak_dzcout compris, jumeaux de la couche compris).

    #   fonction visee                                    banc             rouges
    0   A  V1 : start_time retire                          retours_horloge   7
    1   A  amorce des coupes franches omise                retours_horloge  19
    2   A  trou en tete : +0,04 rendu                      retours_horloge   4
    3   A  V2 video : start_time retire                    retours_horloge   7
    4   B  .trf fabrique a la volee (stab_detect)          retours_grade     1
    5   B  tblend avant fps=                               retours_grade     3
    6   B  piste J1 avant la pile et son masque            retours_grade     1
    7   B  marge de fenetre en images de sortie seulement  retours_grade     1
    8   C  sortie du plein ecran : pas de retour racine    edition           2
    9   C  ecouteur fullscreenchange jamais retire         edition           1
   10   D  `detail` ignore (patcher + chaine)              retours_bundle_r7 2
   11   F  defaut serveur v1-pro                           video_models      3
   12   F  garde de cout contournee                        seedance_garde   22
   13   F  forfait 0,04 $/s retabli (modele vide)          seedance_garde    7
   14   F  soumission fal rejouee                          seedance_garde    6
   15   I  `-fal` route par le prefixe gpt-image           gpt_image_25     18
   16   I  id absent de MS.MODELS                          gpt_image_25      4
   17   H  transcription sans max_usd                      dictation         6
   18   H  isfinite retire                                 dictation         6
   19   H  Entree = Oui dans le dialogue maison            champ_ia          3
   20   G  .dz-studio-grid non exclu                       champ_ia          3
   21   G  reduced-motion retire                           champ_ia          1
   22   G  pastille grisee cliquable                       champ_ia         21

CE QUE CETTE TABLE A MESURE, ET QUI NE SE DEVINAIT PAS :
  . la n°22 rougit 21 lignes : la liste ouverte sur une pastille grisee
    appelle `m.lire` d'une regle qui n'en a pas (Son & VFX) -- TypeError, la
    section T9 du harnais s'arrete ; les deux lignes nommees (« une pastille
    grisee n'ouvre aucune liste », « SANS CLE ») rougissent quand meme ;
  . la n°6 (J1 avant le masque) ne rougit QUE r11 : un seul cas du banc
    combine masque et piste J1 ; la n°7 (marge) ne rougit que le balayage
    r13 du ralenti x0,25 / F60.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
SVC = "backend/app/services/montage_service.py"
GRD = "backend/app/services/grading.py"
JS = "frontend/patches/montage.js"
PAT = "scripts/patch_bundle_montage.py"
BUN = "frontend/dist/assets/index-BEOJX8L5.js"
BAK = "frontend/dist/assets/index-BEOJX8L5.js.bak_dzcout"
FAL = "backend/app/services/fal_service.py"
RTE = "backend/app/api/routes.py"
PRI = "backend/app/services/pricing.py"
IPR = "backend/app/services/image_providers.py"
MST = "backend/app/services/material_store.py"
DIC = "backend/app/services/dictation_service.py"
CIA = "frontend/shared/dz-champ-ia.js"
CIA_D = "frontend/dist/shared/dz-champ-ia.js"
JUMEAUX = {CIA: (CIA_D,)}

B_HOR = "tests/test_retours_horloge.py"
B_GRD = "tests/test_retours_grade.py"
B_EDIT = "tests/test_montage_edition.py"
B_R7 = "tests/test_retours_bundle_r7.py"
B_VM = "tests/test_video_models.py"
B_SG = "tests/test_seedance_garde.py"
B_G25 = "tests/test_gpt_image_25.py"
B_DIC = "tests/test_dictation.py"
B_CIA = "tests/test_champ_ia.py"

# (banc, fichier, ancien | [(ancien, nouveau), ...], nouveau, lignes rouges attendues)
M = [
    # -- A : l'horloge du rendu (T1), jouee par `retours_horloge` -------------------------
    # 0 -- V1 : `start_time=0` retire du prefixe sf (fps part de l'image dont le pts depasse 0).
    (B_HOR, SVC,
     'f"crop={w}:{h},setsar=1,fps={fps}:start_time=0,format=yuv420p")',
     'f"crop={w}:{h},setsar=1,fps={fps},format=yuv420p")',
     ["1.1 prefixe sf : fps=30:start_time=0", "2 1 plan in 0,5 source 25 : aligne"]),
    # 1 -- amorce des coupes franches omise (chaque coupe avance le plan entrant de 0,04 s).
    (B_HOR, SVC,
     '            lead[k] = _XFADE["cut"][1]\n',
     '            pass\n',
     ["1.4 coupe franche : amorce clonee de 0,04 s", "1.6 total = timeline (3,0 s pour 3 plans de 1 s en coupe)"]),
    # 2 -- trou EN TETE : le +0,04 de la coupe entrante rendu au premier segment (2,54 s).
    (B_HOR, SVC,
     '(0.04 if segs else 0.0)',
     '0.04',
     ["6 trou initial 0,5 s + 2 plans en coupe : total = timeline 2.5 s", "6 trou initial 0,5 s + 2 plans en coupe : /measure"]),
    # 3 -- V2 video : `start_time=0` retire de l'overlay (une image d'avance).
    (B_HOR, SVC,
     'else f"fps={fps}:start_time=0,trim=duration={d}")',
     'else f"fps={fps},trim=duration={d}")',
     ["7 V2 plein cadre, source 25, in 0,5, canevas 30", "7 V2 D-14 echelle animee (zoompan + sendcmd)"]),
    # -- B : grade-frame (T2), joue par `retours_grade` -----------------------------------
    # 4 -- `.trf` FABRIQUE a la volee : stab_detect appele quand il manque.
    (B_GRD, SVC,
     '    if mt is None:\n        return sans, ["stab-non-analysee"]\n',
     '    if mt is None:\n        MM.stab_detect(p)\n        return sans, ["stab-non-analysee"]\n',
     ["r9_sans_trf_zero_appel_a_stab_detect"]),
    # 5 -- tblend AVANT fps= (le rendu le pose apres).
    (B_GRD, SVC,
     [('f"setpts=PTS/{n(spd)}" + (f",{rtf}" if rt == "flow" else "")',
       'f"setpts=PTS/{n(spd)}" + (f",{rtf}" if rt in ("flow", "blend") else "")'),
      ('+ f",fps={f}:start_time=0" + (f",{rtf}" if rt == "blend" else ""))',
       '+ f",fps={f}:start_time=0")')],
     None,
     ["r6_blend_image_egale_rendu_ecart_moyen_6_sur_trois_instants", "r13_retime_lent_blend_x0_25_et_F60_flow_x0_25_chaque_instant_egal_au_rendu_6"]),
    # 6 -- la piste J1 AVANT la pile V1 et son masque (le rendu la pose apres).
    (B_GRD, GRD,
     '    parts = _grade_graph(effs, m, w, h, "gv1" if aj else "gout", pre) + aj\n',
     '    parts = _grade_graph(effs, m, w, h, "gv1" if aj else "gout", pre) + aj\n'
     '    if aj:\n'
     '        parts = ([parts[0].replace("[gpre]", "[gq0]")] + _adjust_graph(cadre, w, h, "gq0", "gpre")\n'
     '                 + _grade_graph(effs, m, w, h, "gout", pre)[1:])\n',
     ["r11_j1_couvrant_la_tete_negatif_au_coin_hors_masque_et_au_centre_etalonne"]),
    # 7 -- marge de la fenetre comptee en images de SORTIE seulement (ralenti : image k+1).
    (B_GRD, SVC,
     '        m = max(m, (2 if rt == "flow" else 1) * par_src + 2)\n',
     '        pass\n',
     ["r13_retime_lent_blend_x0_25_et_F60_flow_x0_25_chaque_instant_egal_au_rendu_6"]),
    # -- C : scopes en plein ecran (T3), la couche jouee par `edition` --------------------
    # 8 -- sortie du plein ecran : le portail ne revient pas a la racine.
    (B_EDIT, JS,
     'var oteFs=dzmScwVeilleFs(dc,function(){var cb=dzmScwCible(hote,dc.fullscreenElement);',
     'var oteFs=dzmScwVeilleFs(dc,function(){var cb=dc.fullscreenElement?dzmScwCible(hote,dc.fullscreenElement)'
     ':(cibleR.current||hote);',
     ["r6s_C_sortie_du_plein_ecran_retour_dans_la_racine_rien_ecrit_dans_la_memoire"]),
    # 9 -- l'ecouteur « fullscreenchange » n'est jamais retire.
    (B_EDIT, JS,
     'return function(){d.removeEventListener("fullscreenchange",fn)}}',
     'return function(){}}',
     ["r6s_C_demontage_ecouteur_fullscreenchange_ote"]),
    # -- D : upload refuse lisible (T4), le PATCHER rejoue, joue par `retours_bundle_r7` --
    # 10 -- le `detail` du serveur ignore : « HTTP 415 » seul.
    (B_R7, PAT,
     "error:d||`HTTP ${n.status}`}}')",
     "error:`HTTP ${n.status}`}}')",
     ["up_415_rend_le_detail_du_serveur", "R7up1_ancre_et_remplacement_du_patcher_sont_ceux_du_plan"]),
    # -- F : Seedance 2.5 et garde de cout (T5) --------------------------------------------
    # 11 -- defaut serveur rendu a v1-pro.
    (B_VM, FAL,
     'DEFAULT_VIDEO_MODEL = "seedance-2.5"\n',
     'DEFAULT_VIDEO_MODEL = "seedance-v1-pro"\n',
     ["defaut_seedance_25", "estimation_sans_modele_tarif_25"]),
    # 12 -- garde contournee : aucun 402.
    (B_SG, RTE,
     '    refus = _pricing.cost_guard(total, max_usd, p)\n',
     '    refus = None\n',
     ["composition_402_nomme_le_montant", "composition_max_usd_refuse_402"]),
    # 13 -- le forfait 0,04 $/s retabli pour un modele vide.
    (B_SG, PRI,
     'model = str(op.get("model") or "").strip() or _default_video_model()\n',
     'model = str(op.get("model") or "").strip()\n',
     ["vide_720p_10s_vaut_4_73", "sans_resolution_vaut_4_73_jamais_0_40"]),
    # 14 -- rejeu de la soumission fal (trois generations payees possibles).
    (B_SG, FAL,
     '        return await fal_client.submit_async(endpoint, arguments=arguments)\n',
     '        for _i in range(3):\n'
     '            try:\n'
     '                return await fal_client.submit_async(endpoint, arguments=arguments)\n'
     '            except Exception:\n'
     '                if _i == 2:\n'
     '                    raise\n',
     ["ReadError_au_1er_essai_une_seule_soumission", "RemoteProtocolError_au_1er_essai_une_seule_soumission"]),
    # -- I : GPT Image 2.5 (T6), joue par `gpt_image_25` -----------------------------------
    # 15 -- les `-fal` routes par le prefixe « gpt-image » (OpenAI, mauvaise cle, mauvaise facture).
    (B_G25, IPR,
     '    if provider in _FAL_GPT:\n        if not settings.FAL_KEY:\n',
     '    if provider in _FAL_GPT and not provider.startswith("gpt-image"):\n        if not settings.FAL_KEY:\n',
     ["gen_gpt-image-2.5-flare-fal_200_sans_openai", "edit_gpt-image-2.5-flare-fal_200_sans_openai"]),
    # 16 -- un id du registre absent de MS.MODELS (clean_model le ramene a flux).
    (B_G25, MST,
     '"gpt-image-2.5-flare-fal", ',
     '',
     ["ms_models_gpt-image-2.5-flare-fal", "clean_model_garde_gpt-image-2.5-flare-fal"]),
    # -- H : la dictee (T7 serveur, T10 client) --------------------------------------------
    # 17 -- transcription SANS max_usd (plafond par defaut 1e9).
    (B_DIC, DIC,
     'max_usd: float = Form(...),',
     'max_usd: float = Form(1e9),',
     ["dictation sans max_usd : refusee (4xx)", "402 / 503 / 415 / 413 / 4xx : espion jamais appele"]),
    # 18 -- isfinite retire : NaN / inf passent la garde.
    (B_DIC, DIC,
     'if not math.isfinite(max_usd) or max_usd < 0:',
     'if max_usd < 0:',
     ["dictation max_usd=NaN : 422 avec detail", "dictation max_usd=inf : 422 avec detail"]),
    # 19 -- Entree dans le dialogue maison = Oui (l'action payante devient le defaut).
    (B_CIA, CIA,
     'fin(!!(f && f.getAttribute && f.getAttribute("data-role") === "oui" && v.contains(f)));',
     'fin(true);',
     ["NÉGATIF : Entrée dans le dialogue maison = Non", "AUCUNE DÉPENSE hors accord"]),
    # -- G : les champs IA (T8, T9), joues par `champ_ia` ----------------------------------
    # 20 -- l'editeur de noeuds du Studio n'est plus exclu.
    (B_CIA, CIA,
     'var ZONES = [".dz-studio-grid"];',
     'var ZONES = [];',
     ["NÉGATIF : le Prompt du Studio (.dz-studio-grid) n'est JAMAIS marqué", "NÉGATIF : un champ ajouté sous .dz-studio-grid"]),
    # 21 -- reduced-motion ne coupe plus l'animation du liseré.
    (B_CIA, CIA,
     '".dzia-lis.dzia-lis,.dzia-lis.dzia-lis:focus-within{animation:none!important;--dzia-ang:200deg;transition:none}" +',
     '"" +',
     ["reduced-motion : @media qui coupe toute animation"]),
    # 22 -- pastille GRISEE cliquable (la liste s'ouvre sans cle).
    (B_CIA, CIA,
     '      if (b.getAttribute("aria-disabled") === "true") return;\n      ouvrirListe(el, b);',
     '      ouvrirListe(el, b);',
     ["NÉGATIF : une pastille grisée n'ouvre aucune liste", "SANS CLÉ : la pastille grisée n'ouvre pas de liste"]),
]

# LE COMPTE MESURE, compare par main() -- une valeur par mutation de M.
N_ROUGES = (7, 19, 4, 7, 1, 3, 1, 1, 2, 1, 2, 3, 22, 7, 6, 18, 4, 6, 6, 3, 3, 1, 21)
assert len(N_ROUGES) == len(M), (len(N_ROUGES), len(M))

# Les fichiers dont le sha256 doit revenir a l'identique apres une mutation du
# PATCHER : le patcher lui-meme, le bundle et le point de chaine aval.
CHAINE = (PAT, BUN, BAK)


def ecrire(p, data):
    """Ecrit les OCTETS, avec retentatives (OSError transitoire mesuree sous
    Windows, banc E-C du 23/09) ; au-dela de cinq essais l'erreur remonte et
    le sha256 du `finally` accuse. Jamais un `git checkout`."""
    for essai in range(5):
        try:
            p.write_bytes(data)
            return
        except OSError:
            if essai == 4:
                raise
            time.sleep(0.5)


def sha(rel):
    """sha256 des octets, avec retentatives de lecture (meme piege qu'`ecrire`)."""
    for essai in range(5):
        try:
            return hashlib.sha256((R / rel).read_bytes()).hexdigest()
        except OSError:
            if essai == 4:
                raise
            time.sleep(0.5)


def chaine():
    """Rejoue la chaine des patchers depuis `montage` (cwd = racine). (ok, sortie)."""
    r = subprocess.run([PY, "scripts/repatch_all.py", "--from", "montage"], capture_output=True,
                       cwd=R, timeout=600)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode == 0 and "OK" in txt, txt


def rouges(banc):
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR
    (code autre que 0/1 ou pas de ligne `=== ` : MORT, pas « rien casse »)."""
    try:
        r = subprocess.run([PY, banc], capture_output=True,
                           cwd=R / "backend", timeout=1800)
    except subprocess.TimeoutExpired as e:
        return set(), "TIMEOUT du banc : %r" % e, True
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    erreur = r.returncode not in (0, 1) or "=== " not in txt
    return set(l.strip()[6:].strip() for l in txt.splitlines() if l.strip().startswith("FAIL  ")), txt, erreur


def pre_vol():
    """`repatch_all.py --list` doit rendre `montage` PUIS `dzcout`, chacun avec
    son script (ordre = mtime des `.bak_*`). Rend (ok, message)."""
    r = subprocess.run([PY, "scripts/repatch_all.py", "--list"], capture_output=True,
                       cwd=R, timeout=120)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    if r.returncode != 0:
        return False, "repatch_all.py --list a rendu le code %d :\n%s" % (r.returncode, txt)
    lignes = [l.split() for l in txt.splitlines() if l.strip()]
    tags = [l[0] for l in lignes]
    sans = [l[0] for l in lignes if len(l) < 2 or l[1] != "OK"]
    if "montage" not in tags or "dzcout" not in tags:
        return False, "chaine sans `montage` ou sans `dzcout` : %s" % tags
    if tags.index("montage") > tags.index("dzcout"):
        return False, ("chaine INVERSEE (mtime des .bak_*) : %s -- retablir le mtime des .bak "
                       "avant toute mutation" % tags)
    if sans:
        return False, "maillon(s) sans script : %s" % sans
    return True, "chaine %s : montage puis dzcout, OK" % " -> ".join(tags)


def main():
    seuls = [a for a in sys.argv[1:] if not a.startswith("--")]
    bilan = []
    for i, (banc, rel, old, new, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        cibles = (rel,) + JUMEAUX.get(rel, ())
        est_patcher = rel == PAT
        srcs = {f: (R / f).read_bytes() for f in cibles}          # OCTETS, jamais read_text
        assert len(set(srcs.values())) == 1, (i, "jumeaux divergents", cibles)
        src = srcs[rel]
        avant = {f: sha(f) for f in (cibles + (CHAINE if est_patcher else ()))}
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            # EXACTEMENT UNE FOIS : deux sites mutes rendraient le verdict illisible.
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        mute = txt.replace("\n", eol).encode("utf-8")
        for f in cibles:
            ecrire(R / f, mute)
        mort_chaine = ""
        try:
            if est_patcher:
                ok_c, sortie_c = chaine()
                if not ok_c:
                    mort_chaine = sortie_c[-1500:]
            if mort_chaine:
                rg, sortie, erreur = set(), mort_chaine, True
            else:
                rg, sortie, erreur = rouges(banc)
        finally:
            for f in cibles:
                ecrire(R / f, srcs[f])                           # application INVERSE, jamais git
            if est_patcher:
                ok_r, sortie_r = chaine()                         # le bundle et le .bak_dzcout d'avant
                assert ok_r, (i, "la chaine ne se rejoue pas a la restauration", sortie_r[-800:])
            apres = {f: sha(f) for f in avant}
            assert apres == avant, (i, rel, avant, apres)
        manquants = sorted(a for a in attendus if not any(x.startswith(a) for x in rg))
        if erreur:
            verdict = "MORT(pas rouge)"
            print(sortie[-1500:], file=sys.stderr)
        elif not rg:
            verdict = "SURVIVANT"
        elif manquants:
            verdict = "ROUGE(autres)"
        elif len(rg) != N_ROUGES[i]:
            verdict = "ROUGE(compte)"
        else:
            verdict = "ROUGE"
        bilan.append((i, verdict, sorted(rg), manquants))
        print(f"[{i:2d}] {verdict:16s} {banc[len('tests/test_'):-3]:18s} "
              f"{pathlib.Path(rel).name:24s} {paires[0][0].strip()[:40]!r}")
        print(f"     rouges({len(rg)}/{N_ROUGES[i]})={json.dumps(sorted(x[:150] for x in rg), ensure_ascii=False)}")
        if manquants:
            print(f"     MANQUANTS={manquants}")
        print("     sha " + " ".join(f"{pathlib.Path(f).name}:{avant[f][:10]}={apres[f][:10]}" for f in avant))
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))
    sys.exit(0 if bilan and all(v == "ROUGE" for _, v, _, _ in bilan) else 1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ok_pv, msg_pv = pre_vol()
    print("PRE-VOL : " + msg_pv)
    if not ok_pv:
        sys.exit(2)                               # AVANT toute mutation
    if "--pre-vol" in sys.argv:                   # s'arreter apres le pre-vol
        sys.exit(0)
    main()
