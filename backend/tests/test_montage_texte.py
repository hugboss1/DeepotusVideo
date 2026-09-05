# -*- coding: utf-8 -*-
"""P3 — MONTAGE PAR LE TEXTE : couper une PLAGE de temps, pas un clip.
Banc-MIROIR pour ce qui peut l'etre : le cœur JS est EXECUTE sous node (le
fichier frontend/patches/montage.js, celui-la meme que le patcher injecte),
jamais lu. En-tete recopie de test_subs_animes.py (env, check, sh) — moins
ffmpeg et PIL : rien ici ne se rend en image, et faire dependre le banc d'un
binaire dont il n'a pas besoin le ferait SAUTER sur une machine ou tout est
pourtant mesurable.
Run : & $PY tests/test_montage_texte.py   (depuis backend/)

CE QUI EST FERME ICI
  [1] `find_fillers(words, lang, kind)` rend des PLAGES
      `{start, end, kind, words:[i]}` : voisines DE MEME NATURE fusionnees,
      FR et EN, et JAMAIS de plage pour un mot sans `start`/`end` — on ne
      coupe pas a l'aveugle.
  [1-bis] DEUX sacs, et la difference decide de ce qu'un bouton emporte SANS
      qu'on relise. « hesitation » : des non-mots (euh, hum, um, uh).
      « tic » : des mots PLEINS qui servent de bequille (voilà, genre, well,
      right). MESURE sur deux narrations SANS UNE hesitation : le sac unique
      rendait cinq plages en francais et emportait « Voilà », « Enfin »,
      « genre », « quoi » — quatre mots qui PORTENT la phrase ; en anglais il
      collait « right » et « Okay » dans la MEME plage que « um » et « uh »,
      donc inseparables d'eux. Le bouton en bloc ne prend plus que les
      hesitations, les tics ne se coupent qu'a la selection.
  [1-ter] `silences_to_timeline` : un clip fendu ou rogne ne joue qu'une
      TRANCHE du fichier. Le temps de fichier `t` tombe en
      `start + (t - src_in)/speed`, pas en `t + start`.
  [2] `_fold` : c'est celui de transcribe_service qui est appele, pas celui
      de subtitle_service. Les deux existent, ils ne font PAS la meme chose
      et l'ecart se voit sur « voila » — mesure ici, section [2].
  [3] la route POST /api/subtitles/fillers, par `words`, par `segments` et
      par `kind` ; et POST /api/subtitles/from-narration qui rend `aligned`
      dans SES DEUX branches.
  [4] `DzTracks.rippleCut(clips,t0,t1,opts)`, PUR, sous node : ce qui est
      dans [t0,t1[ disparait, ce qui chevauche est FENDU (le `srcIn` de la
      moitie droite suit la vitesse), tout ce qui suit REMONTE de (t1−t0),
      et les pistes en BOUCLE raccourcissent au lieu d'etre fendues.
  [5] les entrees MOLLES, que le plan ne couvrait pas : `t0 > t1`, plage
      nulle, plage hors de tous les clips, clip sans `srcIn`, piste
      verrouillee, `speed` absente ou nulle, `clips` nul.
  [6] les MOTS d'un clip fendu sont filtres ET RECALES sur le nouveau temps
      — sans le recalage ils gardaient leur date d'avant la coupe — et son
      TEXTE suit ses mots. Sans cette derniere regle, fendre un bloc de
      narration laissait la phrase ENTIERE sur les deux moities : le tiroir
      Narration la montrait deux fois, et « sous-titres depuis la
      narration » la calait deux fois. Convention reprise de `subsSplitAt`
      du bundle, qui decoupe deja un sous-titre ainsi.
  [7] `withWords(clips, aligned)` : les mots cales par le backend, recolles
      sur LEUR clip. Un clip qui porte deja ses mots (s1) n'est pas ecrase.
  [8] DEUX coupes dans LE MEME clip — le geste « retirer les N euh », qui
      est le cas NOMINAL — rendent des identifiants TOUS DIFFERENTS. Le
      suffixe `_r` seul ne suffisait pas : mesure, un clip n1 [0,10] avec des
      « euh » en [1,2] et [5,6] rendait ["n1","n1_r","n1_r"]. Le bundle
      selectionne par identifiant, ecrit par identifiant et cle ses rangees
      dessus : deux homonymes s'editent ENSEMBLE.
  [9] les bords : plage commencant avant zero, mot a cheval sur `t0`, clip
      dont le `start` ne se lit pas — aucun `start` negatif, aucun mot hors
      de sa moitie, aucun NaN.
  [10] `dropWords` : les mots PRETES pour la coupe ne restent pas dans le
      projet ; ceux d'un sous-titre, si.
  [11] la fonction ne MUTE pas son entree (c'est ce qui autorise l'appelant a
      garder `clipsRef.current` comme instantane pour `pushHistory`).

CE QUE CE BANC N'AFFIRME PAS, et qui est un RESTE ASSUME.
  * La reconstruction du texte passe par `.join(" ")` : les RETOURS A LA
    LIGNE d'un sous-titre fendu sont perdus. C'est deja le prix que paie le
    decoupage de sous-titre du bundle (`subsSplitAt`), et c'est la seule
    convention qui existe ici.
  * Un clip qui porte un `text` mais AUCUN mot garde son texte des deux
    cotes : rien ne dirait quel morceau lui revient. Mesure en [6].
  * `removed` vaut TOUJOURS (t1−t0) une fois la plage bornee a zero, meme
    quand elle ne touche aucun clip : c'est du temps de timeline retire.
    Mesure en sections [5] et [9].
  * L'ANNULATION est desormais COMPLETE, et c'est pour cela que M12 ne
    touche plus a `proj.dur` : `pushHistory` ne memorise que
    `{clips, mixDb}`, et la restauration au chargement fait gagner une duree
    SAUVEGARDEE sur les clips — couper, annuler, laisser l'autosave passer,
    rouvrir rendait une timeline plus courte que ses propres clips. La
    contrepartie ASSUMEE : apres une coupe, la fin de la timeline est VIDE
    et se raccourcit a la main. Ce n'est pas mesurable ici (les hooks du
    bundle sont hors de portee du shim node) : c'est garde par
    test_montage_bundle.py et dit dans la note comme dans les deux titres.
  * Le TIROIR lui-meme (chargement des mots, selection au glisser, clavier)
    n'est pas exerce : il n'appelle `r`/`x` que dans son corps, donc node ne
    peut pas l'evaluer. Ce que le bundle en garde est compte par
    test_montage_bundle.py ; le reste se voit au navigateur.
  * `detect_silences` est desormais MEMOISE (cle : chemin + mtime + taille +
    seuils, plafond 64). Le gain — une passe ffmpeg par clip et par coupe
    evitee — n'est pas chronometre ici.

LA REGLE DES ASSERTIONS NEGATIVES, PASSEE SUR CE BANC LE 05/09/2026. Elle
vient de l'en-tete de test_montage_media.py : un TEMOIN DISTINGUABLE, ou le
repli VIDE d'une garde, SE RETOURNE CONTRE TOUTE NEGATION. `a != b`,
`not (…)`, `x not in y`, `== []`, `== ""`, `is None` sont VRAIS PAR
CONSTRUCTION entre deux temoins comme sur un `{}` ou une `[]` de repli : la
ligne verdit sans avoir rien mesure. LA REGLE : toute assertion negative doit
d'abord exiger que ses operandes SOIENT ce qu'ils pretendent etre, et
seulement ensuite les comparer.

  DEUX FAUTES N°6 D'ABORD, ET LA SECONDE EST PIRE QU'UNE MORT.
  (a) `json.loads(r.stdout.strip().splitlines()[-1])` NU apres le shim :
      `splitlines()[-1]` sur une sortie VIDE leve IndexError, et node sort
      rc=0 dans ce cas (un `console.log` deplace suffit), donc le
      `if r.returncode != 0` ne le couvrait pas. MESURE le 05/09/2026
      (`& $PY scratchpad/vide4.py tests/test_montage_texte.py`, node muet a
      rc=0) : le banc MOURAIT ici, 63 des 113 lignes imprimees, aucun compte.
      APRES la garde (la meme que dans les bancs remplacer et bundle, dont
      les commentaires l'appelaient deja « la troisieme de la famille » —
      celle-ci est la quatrieme) : 63/51, ET LE COMPTE EST IMPRIME. La ligne
      `js_shim_rend_un_objet_json` ajoutee fait passer le compte de reference
      de 113 a 114.
  (b) DEUX `.json()` NUS dans le bloc `with TestClient(app)`. Celui de
      `route_kind_absent_rend_les_deux` levait quand le corps n'etait pas du
      JSON — et l'exception, traversant le bloc, arrivait a une sortie de
      cycle de vie qui N'EN REVENAIT JAMAIS : le banc ne mourait pas, il SE
      FIGEAIT a 49 lignes sur 113, sans compte, processus a tuer. Une mort
      laisse au moins un traceback ; un blocage ne laisse rien.
      MESURE : `& $PY scratchpad/vide2.py api503 tests/test_montage_texte.py`
      (toute route `/api/…` en 503) — AVANT : fige a 49. APRES : 93/20.
  LA LIGNE REPAREE : route_ne_modifie_rien. `"clips" not in dd and
  "segments" not in dd` etait vrai d'un `dd` valant `{}`, c'est-a-dire d'une
  reponse INEXISTANTE. Elle exige desormais la reponse mesuree par
  `route_deux_plages`. Croisement automatique apres reparation, sur toutes
  les lignes qui lisent une reponse ou le dict du shim : ZERO reste verte.
  A BON DROIT, ET DECLARE : les lignes de `find_fillers`, des deux sacs et
  de `_silence_key` appellent le service EN DIRECT et ne sont couvertes par
  aucun des deux leviers ; `les_deux_sacs_sont_disjoints` porte deja, depuis
  son ecriture, le `all(bool(b) …)` que la regle demande.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp3_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _exe(name):
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.expandvars(rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{name}.exe")
    if os.path.isfile(cand):
        os.environ["PATH"] = os.path.dirname(cand) + os.pathsep + os.environ["PATH"]
        return cand
    print(f"SKIP: {name} introuvable — le cœur JS ne peut pas être exécuté")
    sys.exit(0)


NODE = _exe("node")
from app.services import transcribe_service as T        # noqa: E402
from app.services import subtitle_service as S          # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


print("\n[1] find_fillers — plages, fusion, FR/EN, jamais sans temps")
W = [{"i": 0, "w": "bon", "start": 0.0, "end": 0.3, "clip": "a1x"},
     {"i": 1, "w": "euh", "start": 0.3, "end": 0.7, "clip": "a1x"},
     {"i": 2, "w": "la", "start": 0.7, "end": 0.9, "clip": "a1x"},
     {"i": 3, "w": "marée", "start": 0.9, "end": 1.4, "clip": "a1x"},
     {"i": 4, "w": "hum", "start": 1.4, "end": 1.6, "clip": "a1x"},
     {"i": 5, "w": "hum", "start": 1.6, "end": 1.8, "clip": "a1x"}]
f = T.find_fillers(W, "fr")
check("deux_plages", len(f) == 2, str(f))
check("premiere_plage",
      bool(f) and f[0] == {"start": 0.3, "end": 0.7, "kind": "hesitation",
                           "words": [1]}, str(f[:1]))
check("plage_fusionnee",
      len(f) > 1 and f[1]["start"] == 1.4 and f[1]["end"] == 1.8
      and f[1]["words"] == [4, 5], str(f[1:]))
check("en_um_uh", [x["words"] for x in T.find_fillers(
      [{"i": 0, "w": "um", "start": 0, "end": .2},
       {"i": 1, "w": "ok", "start": .2, "end": .4},
       {"i": 2, "w": "uh", "start": .4, "end": .6}], "en")] == [[0], [2]],
      str(T.find_fillers([{"i": 0, "w": "um", "start": 0, "end": .2},
                          {"i": 1, "w": "ok", "start": .2, "end": .4},
                          {"i": 2, "w": "uh", "start": .4, "end": .6}], "en")))
check("mot_sans_temps_ignore", T.find_fillers([{"i": 0, "w": "euh"}], "fr") == [])
check("mot_sans_fin_ignore",
      T.find_fillers([{"i": 0, "w": "euh", "start": 0.0}], "fr") == [])
check("temps_illisible_ignore",
      T.find_fillers([{"i": 0, "w": "euh", "start": "tôt", "end": "tard"}], "fr") == [],
      str(T.find_fillers([{"i": 0, "w": "euh", "start": "tôt", "end": "tard"}], "fr")))
check("liste_vide_ou_nulle", T.find_fillers([], "fr") == []
      and T.find_fillers(None, "fr") == [])
check("entree_non_dict_ignoree", T.find_fillers(["euh", 3, None], "fr") == [])
# 20 ms est le SEUIL, et il est FRANC : les temps reels ne tombent jamais
# dedans (0,0 dans une travee, ≥ 0,20 s a travers un silence — mesure en
# [1-bis]). Cette ligne exerce donc le mecanisme, pas la valeur ; ce que la
# valeur protege est le bruit flottant d'un calage venu d'ailleurs.
check("trou_de_50ms_ne_fusionne_pas",
      len(T.find_fillers([{"i": 0, "w": "euh", "start": 1.4, "end": 1.6},
                          {"i": 1, "w": "hum", "start": 1.65, "end": 1.8}], "fr")) == 2,
      str(T.find_fillers([{"i": 0, "w": "euh", "start": 1.4, "end": 1.6},
                          {"i": 1, "w": "hum", "start": 1.65, "end": 1.8}], "fr")))
check("ponctuation_collee_reconnue",
      [s["words"] for s in T.find_fillers(
          [{"i": 0, "w": "Euh,", "start": 0, "end": .2},
           {"i": 1, "w": "hein…", "start": .5, "end": .7},
           {"i": 2, "w": "« ben »", "start": 1.0, "end": 1.2}], "fr")]
      == [[0], [1], [2]],
      str(T.find_fillers([{"i": 0, "w": "Euh,", "start": 0, "end": .2},
                          {"i": 1, "w": "hein…", "start": .5, "end": .7},
                          {"i": 2, "w": "« ben »", "start": 1.0, "end": 1.2}], "fr")))
check("langue_inconnue_retombe_sur_fr",
      T.find_fillers([{"i": 0, "w": "euh", "start": 0, "end": .2}], "de")
      == [{"start": 0.0, "end": 0.2, "kind": "hesitation", "words": [0]}],
      str(T.find_fillers([{"i": 0, "w": "euh", "start": 0, "end": .2}], "de")))
check("en_US_est_de_l_anglais",
      len(T.find_fillers([{"i": 0, "w": "like", "start": 0, "end": .2}], "en-US")) == 1)
# l'index rendu est le `i` DU MOT, pas sa position dans la liste : le tiroir
# s'en sert pour surligner le bon bouton.
check("index_du_mot_pas_de_la_position",
      T.find_fillers([{"i": 41, "w": "ok", "start": 0, "end": .2},
                      {"i": 42, "w": "euh", "start": .2, "end": .4}], "fr")
      == [{"start": 0.2, "end": 0.4, "kind": "hesitation", "words": [42]}],
      str(T.find_fillers([{"i": 41, "w": "ok", "start": 0, "end": .2},
                          {"i": 42, "w": "euh", "start": .2, "end": .4}], "fr")))
# `i` ABSENT : la position sert de repli. Le plan ecrivait `-1`, qui ne
# designe aucun mot et rendrait la plage inutilisable par le tiroir.
check("index_absent_retombe_sur_la_position",
      T.find_fillers([{"w": "ok", "start": 0, "end": .2},
                      {"w": "euh", "start": .2, "end": .4}], "fr")
      == [{"start": 0.2, "end": 0.4, "kind": "hesitation", "words": [1]}],
      str(T.find_fillers([{"w": "ok", "start": 0, "end": .2},
                          {"w": "euh", "start": .2, "end": .4}], "fr")))

print("\n[1-bis] DEUX sacs : ce qu'un bouton a le droit d'emporter sans qu'on lise")
# MESURE qui DECIDE, sur deux narrations qui ne portent PAS UNE hesitation.
# Le sac unique rendait cinq plages en francais et emportait « Voilà »,
# « Enfin », « genre », « quoi » — quatre mots qui PORTENT la phrase.
FR_SANS_EUH = ("Voilà pourquoi la marée monte. Enfin, ce genre de détail "
               "change tout, quoi qu on en dise. Bon, hein, ben oui.")
EN_SANS_EUH = ("Well, this is why the tide rises. So, like, that kind of "
               "detail changes everything, right. Okay, um, uh yes.")
_fr = T.align_known_text(FR_SANS_EUH, start=0.0, end=8.0, lang="fr")["words"]
_en = T.align_known_text(EN_SANS_EUH, start=0.0, end=8.0, lang="en")["words"]
check("fr_sans_hesitation_marque_cinq_plages",
      len(T.find_fillers(_fr, "fr")) == 5, str(T.find_fillers(_fr, "fr")))
check("fr_sans_hesitation_le_bouton_en_bloc_ne_prend_RIEN",
      T.find_fillers(_fr, "fr", kind="hesitation") == [],
      str(T.find_fillers(_fr, "fr", kind="hesitation")))
# EN : « right. Okay, » (tics) touchent « um, uh » (hesitations). Fusionnes,
# ils etaient INSEPARABLES — le bouton en bloc emportait « right » et
# « Okay » quoi qu'on decide ensuite. Deux natures = deux plages.
_ens = T.find_fillers(_en, "en")
check("en_natures_ne_fusionnent_pas",
      [x["kind"] for x in _ens] == ["tic", "tic", "tic", "hesitation"],
      str([(x["kind"], [_en[i]["raw"] for i in x["words"]]) for x in _ens]))
check("en_le_bouton_en_bloc_ne_prend_que_um_et_uh",
      [[_en[i]["raw"] for i in x["words"]]
       for x in T.find_fillers(_en, "en", kind="hesitation")] == [["um,", "uh"]],
      str([[_en[i]["raw"] for i in x["words"]]
           for x in T.find_fillers(_en, "en", kind="hesitation")]))
# `bool()` sur les QUATRE sacs : « disjoints » et « union » sont tous deux
# VRAIS sur des ensembles vides — les deux lignes seraient restees vertes si
# les sacs avaient ete vides, c'est-a-dire si plus rien n'etait marque.
check("les_deux_sacs_sont_disjoints",
      all(bool(b) for b in (T.HESITATIONS["fr"], T.TICS["fr"],
                            T.HESITATIONS["en"], T.TICS["en"]))
      and not (T.HESITATIONS["fr"] & T.TICS["fr"])
      and not (T.HESITATIONS["en"] & T.TICS["en"]))
check("FILLERS_reste_l_union",
      all(bool(b) for b in (T.FILLERS["fr"], T.FILLERS["en"],
                            T.HESITATIONS["fr"], T.TICS["fr"]))
      and T.FILLERS["fr"] == T.HESITATIONS["fr"] | T.TICS["fr"]
      and T.FILLERS["en"] == T.HESITATIONS["en"] | T.TICS["en"])
# `_FILLER_JOIN_S` : ce que le SEUL producteur de ces temps rend vraiment.
# A l'interieur d'une travee de parole, l'ecart entre deux mots vaut
# EXACTEMENT 0,0 (les bornes sont partagees) ; a travers un silence il vaut
# au moins `min_silence_s` (0,20 s). Aucune valeur entre les deux ne change
# quoi que ce soit — le seuil est une garde contre le bruit flottant, pas une
# separation de « la respiration du locuteur » : une respiration EST un
# silence, elle est deja de l'autre cote.
_ww = T.align_known_text("bon euh la marée monte. Enfin voilà, hum.",
                         start=0.0, end=6.0, lang="fr")["words"]
_gaps = {round(_ww[i + 1]["start"] - _ww[i]["end"], 6)
         for i in range(len(_ww) - 1)}
check("ecart_entre_mots_contigus_vaut_zero", _gaps == {0.0}, str(sorted(_gaps)))
_wg = T.align_known_text("bon euh la marée monte. Enfin voilà, hum.",
                         start=0.0, end=6.0, lang="fr",
                         silences=[(1.0, 1.5)])["words"]
_gaps2 = {round(_wg[i + 1]["start"] - _wg[i]["end"], 6)
          for i in range(len(_wg) - 1)}
check("ecart_a_travers_un_silence_depasse_le_seuil",
      max(_gaps2) >= 0.20 > T._FILLER_JOIN_S, str(sorted(_gaps2)))

print("\n[1-ter] silences d'un clip FENDU — la fenêtre de source compte")
# Un clip joue [src_in, src_in + (end-start)*speed[ sur [start, end[ : le
# temps de fichier `t` tombe en start + (t - src_in)/speed, PAS en t + start.
# P3 fend les clips a longueur de journee et le panneau se recharge apres
# CHAQUE coupe : des la deuxieme, les mots auraient ete cales sur les
# silences du DEBUT du fichier.
check("silence_sans_fenetre_est_l_ancien_comportement",
      T.silences_to_timeline([(1.0, 1.5)], 10.0, 20.0) == [(11.0, 11.5)],
      str(T.silences_to_timeline([(1.0, 1.5)], 10.0, 20.0)))
check("silence_decale_par_srcIn",
      T.silences_to_timeline([(3.0, 3.5)], 10.0, 20.0, src_in=2.0)
      == [(11.0, 11.5)],
      str(T.silences_to_timeline([(3.0, 3.5)], 10.0, 20.0, src_in=2.0)))
check("silence_divise_par_la_vitesse",
      T.silences_to_timeline([(4.0, 5.0)], 10.0, 20.0, src_in=2.0, speed=2.0)
      == [(11.0, 11.5)],
      str(T.silences_to_timeline([(4.0, 5.0)], 10.0, 20.0, src_in=2.0, speed=2.0)))
# UN ecarte ET UN garde dans le MEME appel : attendre `[]` tout seul restait
# vert le jour ou la fonction ne rendrait plus rien du tout.
_MIX = T.silences_to_timeline([(0.0, 0.5), (6.0, 6.5)], 10.0, 20.0, src_in=5.0)
check("silence_hors_du_clip_ecarte_et_l_autre_garde",
      _MIX == [(11.0, 11.5)], str(_MIX))
check("silence_a_cheval_borne",
      T.silences_to_timeline([(0.0, 6.0)], 10.0, 20.0, src_in=5.0)
      == [(10.0, 11.0)],
      str(T.silences_to_timeline([(0.0, 6.0)], 10.0, 20.0, src_in=5.0)))
check("silence_vitesse_nulle_vaut_un",
      T.silences_to_timeline([(1.0, 1.5)], 0.0, 9.0, speed=0)
      == [(1.0, 1.5)],
      str(T.silences_to_timeline([(1.0, 1.5)], 0.0, 9.0, speed=0)))
# LE SITE D'APPEL, et pas seulement la formule. Six lignes epinglaient
# `silences_to_timeline` sans que rien ne dise qu'elle est APPELEE avec les
# bonnes valeurs : mesure, mettre `src_in=0.0` en dur dans
# `align_narration_clips` laissait le banc ENTIEREMENT vert. On substitue le
# MESUREUR (`detect_silences`) le temps d'un appel — le calcul, lui, reste
# celui de la production — et on lit les silences que le bloc rend.
_AUD = os.path.join(TMP, "voix.wav")
open(_AUD, "wb").write(b"\0" * 32)          # il suffit qu'il EXISTE
_orig_sil = T.detect_silences
try:
    T.detect_silences = lambda *a, **k: [(3.0, 3.5)]
    _nar = T.align_narration_clips(
        [{"tr": "a1", "id": "n1", "start": 10.0, "end": 20.0, "srcIn": 2.0,
          "text": "bon euh la marée monte encore un peu"},
         # DEUX clips, et le second porte une VITESSE : sans lui, mettre
         # `speed=1.0` en dur au site d'appel ne rougissait rien du tout —
         # la moitié de I7 restait non gardée.
         {"tr": "a1", "id": "n2", "start": 30.0, "end": 40.0, "srcIn": 1.0,
          "speed": 2.0,
          "text": "et la lune tire encore la mer vers le large"}],
        lambda c: _AUD)
finally:
    T.detect_silences = _orig_sil
_SIL = [[tuple(x) for x in b["silences"]] for b in _nar.get("blocks") or []]
check("le_site_d_appel_passe_bien_srcIn",
      _SIL[:1] == [[(11.0, 11.5)]], str(_nar.get("blocks")))
# srcIn 1,0 et vitesse 2 : 30 + (3,0−1,0)/2 = 31,0 et 30 + (3,5−1,0)/2 = 31,25.
check("le_site_d_appel_passe_bien_la_vitesse",
      _SIL[1:] == [[(31.0, 31.25)]], str(_nar.get("blocks")))
# la neutralisation est bien DEFAITE : sans ce controle, une fuite ferait
# passer les lignes suivantes pour des mesures.
check("mesureur_de_silences_retabli", T.detect_silences is _orig_sil)

print("\n[1-quater] la clé du mémo — ce qu'elle promet d'invalider")
# « une voix off re-synthetisee invalide son entree d'elle-meme » etait une
# revendication NON DEFENDUE : amputer la cle de `st_mtime_ns` et `st_size`
# laissait le banc a 105/0. Extraite, elle se mesure sans ffmpeg.
_K1 = os.path.join(TMP, "k1.wav")
open(_K1, "wb").write(b"\0" * 100)
_k_avant = T._silence_key(pathlib.Path(_K1), -33.0, 0.20)
check("meme_fichier_meme_cle",
      _k_avant == T._silence_key(pathlib.Path(_K1), -33.0, 0.20)
      and _k_avant is not None, str(_k_avant))
time.sleep(0.02)                      # le mtime est en NANOsecondes : suffit
open(_K1, "wb").write(b"\0" * 250)   # la voix est refaite, MEME chemin
_k_apres = T._silence_key(pathlib.Path(_K1), -33.0, 0.20)
check("fichier_reecrit_change_de_cle", _k_apres != _k_avant,
      f"{_k_avant} == {_k_apres}")
check("la_cle_porte_taille_ET_mtime",
      _k_apres[2] == 250 and _k_avant[2] == 100 and _k_apres[1] != _k_avant[1],
      f"{_k_avant} / {_k_apres}")
check("deux_seuils_deux_cles",
      T._silence_key(pathlib.Path(_K1), -33.0, 0.20)
      != T._silence_key(pathlib.Path(_K1), -40.0, 0.20)
      != T._silence_key(pathlib.Path(_K1), -40.0, 0.50),
      str(T._silence_key(pathlib.Path(_K1), -40.0, 0.50)))
check("fichier_absent_pas_de_cle",
      T._silence_key(pathlib.Path(os.path.join(TMP, "nulle-part.wav")),
                     -33.0, 0.20) is None)

print("\n[2] quel `_fold` — les deux existent, ils divergent sur « voilà »")
# MESURE : transcribe_service._fold GARDE les diacritiques, subtitle_service._fold
# les RETIRE. « voilà » est dans le sac FR : replie par celui de subtitle_service
# il donne « voila », qui n'y est pas, et le mot cesse d'etre reconnu. C'est la
# raison — mesurable — pour laquelle find_fillers appelle le _fold de SON module.
check("les_deux_folds_existent", callable(T._fold) and callable(S._fold))
check("fold_transcribe_garde_l_accent", T._fold("Voilà") == "voilà",
      T._fold("Voilà"))
check("fold_subtitle_retire_l_accent", S._fold("Voilà") == "voila",
      S._fold("Voilà"))
check("voila_est_dans_le_sac_fr", "voilà" in T.FILLERS["fr"]
      and "voila" not in T.FILLERS["fr"])
check("voila_accentue_reconnu",
      len(T.find_fillers([{"i": 0, "w": "Voilà", "start": 0, "end": .3}], "fr")) == 1,
      str(T.find_fillers([{"i": 0, "w": "Voilà", "start": 0, "end": .3}], "fr")))

print("\n[3] la ROUTE POST /api/subtitles/fillers")
from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402
with TestClient(app) as cli:
    rr = cli.post("/api/subtitles/fillers", json={"words": W, "lang": "fr"})
    check("route_200", rr.status_code == 200, rr.text[:200])
    dd = rr.json() if rr.status_code == 200 else {}
    check("route_deux_plages", dd.get("count") == 2, str(dd)[:220])
    check("route_rend_les_plages", (dd.get("spans") or [{}])[0].get("words") == [1],
          str(dd.get("spans"))[:200])
    check("route_dit_la_langue", dd.get("lang") == "fr", str(dd.get("lang")))
    # par SEGMENTS : les mots sont aplatis et RENUMEROTES sur la liste plate —
    # sinon deux repliques auraient chacune un mot d'indice 0.
    r2 = cli.post("/api/subtitles/fillers", json={"lang": "fr", "segments": [
        {"start": 0, "end": 1, "text": "bon euh",
         "words": [{"w": "bon", "start": 0, "end": .5},
                   {"w": "euh", "start": .5, "end": 1}]},
        {"start": 1, "end": 2, "text": "hein la",
         "words": [{"w": "hein", "start": 1, "end": 1.4},
                   {"w": "la", "start": 1.4, "end": 2}]}]})
    check("route_segments_200", r2.status_code == 200, r2.text[:200])
    d2 = r2.json() if r2.status_code == 200 else {}
    # « euh » 0,5–1,0 et « hein » 1,0–1,4 se TOUCHENT, et pourtant DEUX
    # plages : ils ne sont pas de la meme nature. Sans cette regle, « hein »
    # — un mot PLEIN — repartait avec « euh » en bloc, et rien n'aurait pu
    # les separer ensuite.
    check("route_segments_aplatis_pas_fusionnes_entre_natures",
          d2.get("spans") == [
              {"start": 0.5, "end": 1.0, "kind": "hesitation", "words": [1]},
              {"start": 1.0, "end": 1.4, "kind": "tic", "words": [2]}],
          str(d2.get("spans")))
    r3 = cli.post("/api/subtitles/fillers", json={})
    check("route_corps_vide_ne_casse_pas",
          r3.status_code == 200 and r3.json().get("spans") == [], r3.text[:200])
    r4 = cli.post("/api/subtitles/fillers", json={"lang": "en", "words": [
        {"i": 0, "w": "Well", "start": 0, "end": .3}]})
    # `(r4.json() or {})` ne garde de rien : c'est `.json()` LUI-MEME qui leve
    # quand le corps n'est pas du JSON. Meme forme que les trois lectures
    # ci-dessus, qui, elles, testent le code d'abord.
    d4 = r4.json() if r4.status_code == 200 else {}
    check("route_anglais", d4.get("count") == 1, r4.text[:200])
    # `kind` FILTRE — c'est ce que demande le bouton qui coupe sans qu'on
    # relise. « Well » est un mot PLEIN : il est marque, il ne part pas en bloc.
    rk = cli.post("/api/subtitles/fillers", json={
        "lang": "en", "kind": "hesitation",
        "words": [{"i": 0, "w": "Well", "start": 0, "end": .3},
                  {"i": 1, "w": "um", "start": 1.0, "end": 1.2}]})
    dk = rk.json() if rk.status_code == 200 else {}
    check("route_kind_filtre",
          dk.get("count") == 1
          and (dk.get("spans") or [{}])[0].get("words") == [1],
          str(dk)[:220])
    check("route_dit_le_kind_demande", dk.get("kind") == "hesitation",
          str(dk.get("kind")))
    # LE `.json()` NU QUI FIGEAIT LE BANC. MESURE le 05/09/2026
    # (`scratchpad/vide2.py api503`) : la lecture leve, l'exception traverse
    # le bloc `with TestClient(app)`, et la sortie du bloc n'en revient
    # JAMAIS — 49 lignes sur 113, aucun compte imprime, processus a tuer.
    # Une mort est deja la faute n°6 ; un blocage est pire, il ne laisse meme
    # pas de trace.
    r6 = cli.post("/api/subtitles/fillers", json={
        "lang": "en",
        "words": [{"i": 0, "w": "Well", "start": 0, "end": .3},
                  {"i": 1, "w": "um", "start": 1.0, "end": 1.2}]})
    d6 = r6.json() if r6.status_code == 200 else {}
    check("route_kind_absent_rend_les_deux", d6.get("count") == 2,
          r6.text[:200])
    # DEUX NEGATIONS SUR `dd`, QUI VAUT `{}` DES QUE LA ROUTE N'A PAS REPONDU
    # 200 : « la route n'ajoute rien » etait vrai d'une reponse inexistante.
    # MESURE (routes `/api/…` en 503) : VERTE. On exige la reponse mesuree
    # par `route_deux_plages`, reprise ici plutot que supposee.
    check("route_ne_modifie_rien",
          dd.get("count") == 2
          and "clips" not in dd and "segments" not in dd, str(dd.keys()))
    # POST /subtitles/from-narration doit dire DE QUEL CLIP vient chaque mot :
    # les `segments` ne le disent pas (normalize_segments ne garde que
    # w/start/end), et sans cette information la coupe ne peut pas repartir le
    # texte d'un bloc fendu. La cle `words` reste le COMPTE qu'elle etait.
    r5 = cli.post("/api/subtitles/from-narration", json={"clips": [
        {"tr": "a1", "id": "n1", "start": 0, "end": 2, "text": "bon euh la marée"}]})
    check("narration_200", r5.status_code == 200, r5.text[:200])
    d5 = r5.json() if r5.status_code == 200 else {}
    al = d5.get("aligned") or []
    check("narration_rend_les_mots_plats", len(al) == 4, str(len(al)))
    # `bool(al)` EXIGÉ : `all(...)` sur une liste vide est vrai, et la ligne
    # passait au vert quand la route ne rendait plus `aligned` du tout.
    check("narration_chaque_mot_dit_son_clip",
          bool(al) and all(w.get("clip") == "n1" for w in al), str(al[:1]))
    check("narration_words_reste_un_compte", d5.get("words") == 4,
          str(d5.get("words")))
    check("narration_les_mots_portent_raw_et_punct",
          bool(al) and "raw" in al[0] and "punct" in al[0], str(al[:1]))
    # LES DEUX branches de la route rendent `aligned` : celle des `clips` et
    # celle d'un bloc isole (`text`). Un contrat asymetrique se decouvre au
    # pire moment. Le bloc isole n'a pas de `clip` — il n'y en a pas.
    r6 = cli.post("/api/subtitles/from-narration",
                  json={"text": "bon euh la marée", "start": 0, "end": 2})
    check("narration_bloc_isole_200", r6.status_code == 200, r6.text[:200])
    a6 = (r6.json() if r6.status_code == 200 else {}).get("aligned") or []
    check("narration_bloc_isole_rend_aussi_aligned", len(a6) == 4, str(len(a6)))
    check("narration_bloc_isole_sans_clip",
          bool(a6) and all("clip" not in w for w in a6), str(a6[:1]))

print("\n[4] le cœur JS — dzmRippleCut EXÉCUTÉ sous node")
LAYER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                     "frontend", "patches", "montage.js")
SRC = open(LAYER, encoding="utf-8-sig").read()
PROBE = r"""
var T=window.DzTracks;
function C(){return [
 {tr:"v1",id:"v",start:0,end:4,srcIn:0},
 {tr:"a1",id:"a",start:0,end:2,srcIn:0},
 {tr:"a2",id:"m",start:0,end:4,srcIn:0,loop:!0},
 {tr:"s1",id:"s",start:0.5,end:2.5}]}
var out={},IN=C(),avant=JSON.stringify(IN);
out.base=T.rippleCut(IN,0.3,0.7,{loopTracks:["a2"]});
out.entree_intacte=(JSON.stringify(IN)===avant);
/* t0 > t1 : la plage est remise a l'endroit, pas jouee a l'envers */
out.inverse=T.rippleCut(C(),0.7,0.3,{loopTracks:["a2"]});
/* plage NULLE : rien a retirer, donc rien de fendu */
out.nulle=T.rippleCut(C(),0.7,0.7,{loopTracks:["a2"]});
/* plage hors de tous les clips */
out.hors=T.rippleCut(C(),10,11,{loopTracks:["a2"]});
/* piste VERROUILLEE : ses clips ne bougent pas d'un millieme */
out.verrou=T.rippleCut(C(),0.3,0.7,{loopTracks:["a2"],locked:{v1:1}});
/* vitesse : le srcIn de la moitie droite consomme vitesse x duree */
out.vitesse=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,srcIn:0,speed:2}],0.3,0.7,{});
out.vitesse0=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,srcIn:0,speed:0}],0.3,0.7,{});
out.vitesseNaN=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,srcIn:0,speed:"vite"}],0.3,0.7,{});
/* ni srcIn ni src : aucune fenetre de source a inventer */
out.sans_srcin=T.rippleCut([{tr:"v1",id:"v",start:0,end:4}],0.3,0.7,{});
out.src_sans_srcin=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,src:{file_path:"x"}}],0.3,0.7,{});
/* entierement DANS la plage : le clip disparait */
out.dedans=T.rippleCut([{tr:"v1",id:"d",start:0.4,end:0.6,srcIn:0}],0.3,0.7,{});
/* boucle AVANT / APRES / DEDANS la plage */
out.loop_avant=T.rippleCut([{tr:"a2",id:"m",start:0,end:0.2,loop:!0}],0.3,0.7,{loopTracks:["a2"]});
out.loop_apres=T.rippleCut([{tr:"a2",id:"m",start:1,end:2,loop:!0}],0.3,0.7,{loopTracks:["a2"]});
out.loop_dedans=T.rippleCut([{tr:"a2",id:"m",start:0.4,end:0.6,loop:!0}],0.3,0.7,{loopTracks:["a2"]});
/* rien du tout */
out.vide=T.rippleCut(null,0.3,0.7,{});
out.sans_opts=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,srcIn:0}],0.3,0.7);
/* les MOTS d'un s1 fendu, et son TEXTE qui les suit */
out.mots=T.rippleCut([{tr:"s1",id:"s",start:0,end:2,text:"bon euh la",words:[
  {w:"bon",start:0,end:0.3},{w:"euh",start:0.3,end:0.7},{w:"la",start:0.7,end:2}]}],
  0.3,0.7,{});
/* un clip qui porte un TEXTE mais AUCUN mot : rien ne dit quel morceau lui
   revient, son texte est laissé tel quel des deux côtés */
out.texte_sans_mots=T.rippleCut([{tr:"a1",id:"n",start:0,end:2,src:{file_path:"x"},
  text:"bon euh la"}],0.3,0.7,{});
/* withWords : les mots calés du backend, recollés sur LEUR clip */
var AL=[{i:0,w:"bon",start:0,end:0.3,clip:"n"},{i:1,w:"euh",start:0.3,end:0.7,clip:"n"},
        {i:2,w:"la",start:0.7,end:2,clip:"n"},{i:3,w:"ailleurs",start:0,end:1,clip:"z"}];
out.ww=T.withWords([{tr:"a1",id:"n",start:0,end:2,text:"bon euh la"},
                    {tr:"v1",id:"v",start:0,end:2}],AL);
/* un clip qui porte DÉJÀ ses mots n'est pas écrasé */
out.ww_garde=T.withWords([{tr:"s1",id:"n",start:0,end:2,
  words:[{w:"deja",start:0,end:2}]}],AL);
out.ww_vide=T.withWords([{tr:"a1",id:"n",start:0,end:2}],[]);
/* la chaîne complète : withWords puis rippleCut sur un bloc de narration */
out.chaine=T.rippleCut(T.withWords([{tr:"a1",id:"n",start:0,end:2,
  src:{file_path:"x"},srcIn:0,text:"bon euh la"}],AL),0.3,0.7,{});
/* DEUX coupes dans LE MÊME clip — le geste « retirer les N euh », qui est le
   cas NOMINAL. La boucle de M12 : plages triées de la FIN vers le DÉBUT,
   `cs` accumulé d'une coupe à l'autre. */
var deux=[{tr:"a1",id:"n1",start:0,end:10,srcIn:0,src:{file_path:"x"}}];
[[1,2],[5,6]].slice().sort(function(u,v){return v[0]-u[0]}).forEach(function(p){
  deux=T.rippleCut(deux,p[0],p[1],{}).clips});
out.deux=deux;
/* et l'identifiant déjà pris n'est pas repris non plus quand il existe DÉJÀ
   dans la timeline : `x_r` occupé => `x_r2` */
out.id_pris=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,srcIn:0},
  {tr:"v1",id:"v_r",start:5,end:6,srcIn:0}],1,2,{}).clips.map(function(c){
  return c.id});
/* `taken` est un objet NU : un clip nommé « toString » ne doit pas passer
   pour un identifiant déjà pris (Object.prototype le porte). */
out.id_prototype=T.rippleCut([{tr:"v1",id:"toString",start:0,end:4,srcIn:0}],
  1,2,{}).clips.map(function(c){return c.id});
/* M5 — plage qui commence AVANT zéro : la timeline ne va pas plus bas */
out.avant_zero=T.rippleCut([{tr:"v1",id:"v",start:0,end:4,srcIn:0}],-1,1,{});
/* M5 — mot À CHEVAL sur t0 : il part à gauche, mais sa fin doit rester dans
   sa moitié */
out.mot_a_cheval=T.rippleCut([{tr:"s1",id:"s",start:0,end:3,text:"a b",words:[
  {w:"a",start:0.2,end:2.5},{w:"b",start:2.5,end:3}]}],0.5,1.0,{});
/* M5 — `start` illisible : aucun NaN ne doit sortir */
out.start_illisible=T.rippleCut([{tr:"v1",id:"v",start:"tot",end:4,srcIn:0,
  src:{file_path:"x"}}],0.3,0.7,{});
/* M6 — les mots prêtés sont retirés des pistes qui ne sont pas des s1 */
out.drop=T.dropWords([{tr:"a1",id:"n",words:[{w:"x",start:0,end:1}],text:"x"},
  {tr:"s1",id:"s",words:[{w:"y",start:0,end:1}]}],["s1"]);
console.log(JSON.stringify(out));
"""
shim = os.path.join(TMP, "shim.js")          # fichier, jamais `node -e`
# "use strict" en PROLOGUE : concatene, celui de montage.js n'est plus une
# directive. Sans lui le cœur tournerait RELACHE ici alors que le navigateur
# l'execute strict (module).
with open(shim, "w", encoding="utf-8") as fh:
    fh.write('"use strict";\nvar window={};var SVM_TRACK_BUS={};\n' + SRC + "\n" + PROBE)
r = sh([NODE, shim])
if r.returncode != 0:
    check("js_shim_execute", False, (r.stderr or "")[-600:])
    D = {}
else:
    check("js_shim_execute", True)
    # QUATRIEME LIGNE DE LA MEME FAMILLE (faute n°6) — celle qui manquait.
    # `splitlines()[-1]` sur une sortie VIDE leve IndexError, et `json.loads`
    # sur une derniere ligne qui n'est pas du JSON leve JSONDecodeError ; node
    # sort rc=0 dans les deux cas (un `console.log` deplace suffit), donc le
    # `if r.returncode != 0` ci-dessus n'en couvre AUCUN. MESURE le
    # 05/09/2026 (`scratchpad/vide4.py`, node muet a rc=0) : le banc MOURAIT
    # ici, IndexError, 49 des 113 lignes imprimees, aucun compte.
    _lignes = r.stdout.strip().splitlines()
    _derniere = _lignes[-1] if _lignes else ""
    try:
        D = json.loads(_derniere) if _derniere else None
        _mal = "" if isinstance(D, dict) and D else "sortie sans objet JSON"
    except Exception as _e:
        D, _mal = None, "%s: %s" % (type(_e).__name__, _e)
    if not isinstance(D, dict):
        D = {}
    check("js_shim_rend_un_objet_json", _mal == "",
          f"{_mal} — {len(_lignes)} ligne(s), derniere={_derniere[:160]!r}")


def trio(res, tr):
    return sorted((c["start"], c["end"], c.get("srcIn"))
                  for c in (res or {}).get("clips") or [] if c.get("tr") == tr)


def byid(res):
    return {c["id"]: c for c in (res or {}).get("clips") or []}


B = D.get("base") or {}
check("v1_coupe_en_deux", trio(B, "v1") == [(0, 0.3, 0), (0.3, 3.6, 0.7)],
      str(trio(B, "v1")))
check("a1_coupe_en_deux", trio(B, "a1") == [(0, 0.3, 0), (0.3, 1.6, 0.7)],
      str(trio(B, "a1")))
check("musique_bouclee_raccourcie",
      byid(B).get("m", {}).get("start") == 0 and byid(B).get("m", {}).get("end") == 3.6,
      str(byid(B).get("m")))
check("musique_bouclee_pas_fendue",
      len([c for c in B.get("clips") or [] if c.get("tr") == "a2"]) == 1,
      str([c for c in B.get("clips") or [] if c.get("tr") == "a2"]))
check("sous_titre_decale_et_rogne",
      byid(B).get("s", {}).get("start") == 0.3 and byid(B).get("s", {}).get("end") == 2.1,
      str(byid(B).get("s")))
check("duree_retiree", B.get("removed") == 0.4, str(B.get("removed")))
# la moitie DROITE prend un identifiant neuf : deux clips de meme id se
# disputeraient la selection, l'inspecteur et l'historique.
check("moitie_droite_id_suffixe",
      sorted(c["id"] for c in B.get("clips") or [] if c.get("tr") == "v1")
      == ["v", "v_r"],
      str(sorted(c.get("id") for c in B.get("clips") or [] if c.get("tr") == "v1")))
check("entree_non_mutee", D.get("entree_intacte") is True)

print("\n[5] entrées molles — ce que le plan ne couvrait pas")
# Comparé au LITTÉRAL, et non au résultat voisin : `bool(D.get("base"))`
# était un garde-fou trop faible — `{"clips":[],"removed":0}` est un dict
# VRAI, donc deux résultats vides se seraient validés l'un l'autre. C'est
# exactement ce que le commentaire de `plage_hors_clips` interdit dix lignes
# plus bas, et cette ligne-ci y dérogeait.
_ENVERS = {"clips": [
    {"tr": "v1", "id": "v", "start": 0, "end": 0.3, "srcIn": 0},
    {"tr": "v1", "id": "v_r", "start": 0.3, "end": 3.6, "srcIn": 0.7},
    {"tr": "a1", "id": "a", "start": 0, "end": 0.3, "srcIn": 0},
    {"tr": "a1", "id": "a_r", "start": 0.3, "end": 1.6, "srcIn": 0.7},
    {"tr": "a2", "id": "m", "start": 0, "end": 3.6, "srcIn": 0, "loop": True},
    {"tr": "s1", "id": "s", "start": 0.3, "end": 2.1}], "removed": 0.4}
check("t0_superieur_a_t1_remis_a_l_endroit",
      D.get("inverse") == _ENVERS and D.get("base") == _ENVERS,
      str(D.get("inverse"))[:240])
INTACT = [{"tr": "v1", "id": "v", "start": 0, "end": 4, "srcIn": 0},
          {"tr": "a1", "id": "a", "start": 0, "end": 2, "srcIn": 0},
          {"tr": "a2", "id": "m", "start": 0, "end": 4, "srcIn": 0, "loop": True},
          {"tr": "s1", "id": "s", "start": 0.5, "end": 2.5}]
check("plage_nulle_ne_fend_rien",
      (D.get("nulle") or {}).get("clips") == INTACT
      and (D.get("nulle") or {}).get("removed") == 0,
      str(D.get("nulle"))[:240])
# comparé au LITTÉRAL, pas au résultat de la plage nulle : deux lignes qui se
# comparent l'une à l'autre rougissent ensemble et ne nomment plus laquelle
# des deux a cédé.
check("plage_hors_clips_ne_touche_aucun_clip",
      (D.get("hors") or {}).get("clips") == INTACT,
      str(D.get("hors"))[:240])
# ASSUME : `removed` est du TEMPS DE TIMELINE, pas du temps de clip. Couper
# une plage vide raccourcit quand meme le projet d'autant — c'est voulu.
check("plage_hors_clips_retire_quand_meme_le_temps",
      (D.get("hors") or {}).get("removed") == 1, str((D.get("hors") or {}).get("removed")))
V = D.get("verrou") or {}
check("piste_verrouillee_intacte",
      trio(V, "v1") == [(0, 4, 0)], str(trio(V, "v1")))
check("piste_verrouillee_n_empeche_pas_les_autres",
      trio(V, "a1") == [(0, 0.3, 0), (0.3, 1.6, 0.7)], str(trio(V, "a1")))
check("vitesse_2_consomme_deux_fois_la_source",
      trio(D.get("vitesse"), "v1") == [(0, 0.3, 0), (0.3, 3.6, 1.4)],
      str(trio(D.get("vitesse"), "v1")))
# `speed: 0` est la valeur « non reglee » du modele de clip (montage_service
# la lit ainsi) : la prendre au pied de la lettre donnerait un srcIn nul.
check("vitesse_nulle_vaut_un", trio(D.get("vitesse0"), "v1")
      == [(0, 0.3, 0), (0.3, 3.6, 0.7)], str(trio(D.get("vitesse0"), "v1")))
check("vitesse_illisible_vaut_un", trio(D.get("vitesseNaN"), "v1")
      == [(0, 0.3, 0), (0.3, 3.6, 0.7)], str(trio(D.get("vitesseNaN"), "v1")))
check("sans_source_aucun_srcIn_invente",
      len((D.get("sans_srcin") or {}).get("clips") or []) == 2
      and all("srcIn" not in c
              for c in (D.get("sans_srcin") or {}).get("clips") or []),
      str(D.get("sans_srcin")))
check("source_sans_srcIn_en_recoit_un",
      trio(D.get("src_sans_srcin"), "v1") == [(0, 0.3, None), (0.3, 3.6, 0.7)],
      str(trio(D.get("src_sans_srcin"), "v1")))
check("clip_entierement_dedans_disparait",
      (D.get("dedans") or {}).get("clips") == []
      and (D.get("dedans") or {}).get("removed") == 0.4, str(D.get("dedans")))
# une boucle AVANT la plage n'a rien a voir avec la coupe : le code du plan
# la raccourcissait quand meme (end = max(start, end − len)), donc une
# musique de 0,2 s posee avant la coupe tombait a duree NULLE.
check("boucle_avant_la_plage_intacte",
      (D.get("loop_avant") or {}).get("clips") == [
          {"tr": "a2", "id": "m", "start": 0, "end": 0.2, "loop": True}],
      str(D.get("loop_avant")))
check("boucle_apres_la_plage_remonte",
      [(c["start"], c["end"]) for c in (D.get("loop_apres") or {}).get("clips") or []]
      == [(0.6, 1.6)], str(D.get("loop_apres")))
check("boucle_entierement_dedans_retiree",
      (D.get("loop_dedans") or {}).get("clips") == []
      and (D.get("loop_dedans") or {}).get("removed") == 0.4,
      str(D.get("loop_dedans")))
check("clips_nuls_ne_cassent_pas",
      D.get("vide") == {"clips": [], "removed": 0.4}, str(D.get("vide")))
check("opts_absent_ne_casse_pas",
      trio(D.get("sans_opts"), "v1") == [(0, 0.3, 0), (0.3, 3.6, 0.7)],
      str(D.get("sans_opts")))

print("\n[6] les mots d'un sous-titre fendu — filtrés ET recalés")
M = D.get("mots") or {}
mc = M.get("clips") or []
check("s1_fendu_en_deux", len(mc) == 2, str(mc))
check("mot_de_la_plage_retire",
      [[w["w"] for w in c.get("words") or []] for c in mc] == [["bon"], ["la"]],
      str([[w.get("w") for w in c.get("words") or []] for c in mc]))
# LE point : sans recalage, « la » gardait 0,7–2,0 alors que son clip vit
# desormais en 0,3–1,6 — le karaoke se serait allume apres la fin de la ligne.
check("mot_de_droite_recale",
      len(mc) == 2 and (mc[1].get("words") or [{}])[0] == {"w": "la", "start": 0.3,
                                                           "end": 1.6},
      str(mc[1].get("words") if len(mc) == 2 else mc))
check("mot_de_gauche_inchange",
      len(mc) == 2 and (mc[0].get("words") or [{}])[0] == {"w": "bon", "start": 0,
                                                           "end": 0.3},
      str(mc[0].get("words") if len(mc) == 2 else mc))
# LE TEXTE SUIT LES MOTS — meme convention que `subsSplitAt` du bundle, qui
# decoupe deja un sous-titre ainsi. Sans elle, les DEUX moities gardaient la
# phrase entiere : le tiroir Narration la montrait deux fois et « sous-titres
# depuis la narration » la calait deux fois. Les retours a la ligne sont
# perdus dans la reconstruction — c'est le prix de la convention, deja paye
# par le decoupage de sous-titre du bundle.
check("le_texte_suit_les_mots",
      len(mc) == 2 and [c.get("text") for c in mc] == ["bon", "la"],
      str([c.get("text") for c in mc]))
# et l'INVERSE : sans `words`, rien ne dit quel morceau revient a qui. Le
# texte est laisse tel quel plutot que devine.
TS = D.get("texte_sans_mots") or {}
check("texte_sans_mots_laisse_intact",
      [c.get("text") for c in TS.get("clips") or []] == ["bon euh la",
                                                         "bon euh la"],
      str([c.get("text") for c in TS.get("clips") or []]))

print("\n[7] withWords — les mots calés recollés sur LEUR clip")
WW = D.get("ww") or []
check("withWords_pose_les_mots_du_bon_clip",
      len(WW) == 2 and [w["w"] for w in WW[0].get("words") or []]
      == ["bon", "euh", "la"], str(WW[:1]))
check("withWords_ne_touche_pas_un_clip_sans_mots",
      len(WW) == 2 and "words" not in WW[1], str(WW[1:]))
check("withWords_ne_garde_que_w_start_end",
      len(WW) == 2 and sorted((WW[0].get("words") or [{}])[0].keys())
      == ["end", "start", "w"], str(WW[:1]))
# un clip qui porte DEJA ses mots (un sous-titre s1) fait foi : les ecraser
# avec le calage de la narration lui volerait son propre decoupage.
check("withWords_n_ecrase_pas_des_mots_existants",
      [w["w"] for w in (D.get("ww_garde") or [{}])[0].get("words") or []]
      == ["deja"], str(D.get("ww_garde")))
check("withWords_sans_calage_rend_les_clips_tels_quels",
      D.get("ww_vide") == [{"tr": "a1", "id": "n", "start": 0, "end": 2}],
      str(D.get("ww_vide")))
# LA CHAINE COMPLETE, celle que M12 exécute : un bloc de narration passe par
# withWords puis par rippleCut, et ressort en DEUX clips dont chacun porte SON
# texte et SA fenêtre de source.
CH = (D.get("chaine") or {}).get("clips") or []
check("chaine_narration_fendue_en_deux", len(CH) == 2, str(CH))
check("chaine_chaque_moitie_son_texte",
      [c.get("text") for c in CH] == ["bon", "la"],
      str([c.get("text") for c in CH]))
check("chaine_la_moitie_droite_reprend_la_source",
      len(CH) == 2 and CH[1].get("srcIn") == 0.7 and CH[1].get("id") == "n_r",
      str(CH[1:]))

print("\n[8] DEUX coupes dans le même clip — le geste « retirer les N euh »")
# LE cas nominal, et celui que le banc ne voyait pas : il ne mesurait qu'UNE
# coupe. La deuxieme refendait la moitie GAUCHE, qui porte encore l'id
# d'origine, et recreait « n1_r ». Le bundle ne survit pas aux homonymes : il
# selectionne par identifiant (clips.find(c=>c.id===selId)), ecrit par
# identifiant (map(k=>k.id===id?…:k)) et cle ses rangees dessus — deux
# homonymes s'editent ENSEMBLE et se disputent la rangee.
DX = D.get("deux") or []
check("deux_coupes_rendent_trois_clips", len(DX) == 3, str(DX))
check("deux_coupes_identifiants_TOUS_DIFFERENTS",
      len(DX) == 3 and len({c.get("id") for c in DX}) == 3,
      str([c.get("id") for c in DX]))
check("deux_coupes_bornes_justes",
      [(c["start"], c["end"], c.get("srcIn")) for c in DX]
      == [(0, 1, 0), (1, 4, 2), (4, 8, 6)],
      str([(c.get("start"), c.get("end"), c.get("srcIn")) for c in DX]))
check("identifiant_deja_dans_la_timeline_evite",
      D.get("id_pris") == ["v", "v_r2", "v_r"], str(D.get("id_pris")))
# CE QUE CETTE LIGNE MESURE, exactement : un identifiant exotique traverse la
# passe sans etre abime. Elle ne prouve PAS que la table des identifiants pris
# doit etre NUE — mesure, Object.prototype ne porte aucun membre finissant par
# `_r` ni `_r<n>`, et tout candidat genere finit ainsi : aucune entree ne peut
# donc etre faussement declaree prise. La table nue est une precaution de
# construction, pas un correctif mesure, et c'est dit tel quel dans le code.
check("identifiant_exotique_traverse_intact",
      D.get("id_prototype") == ["toString", "toString_r"],
      str(D.get("id_prototype")))

print("\n[9] bords fermés de rippleCut")
AZ = D.get("avant_zero") or {}
check("plage_avant_zero_ne_pose_pas_de_start_negatif",
      all((c.get("start") or 0) >= 0 for c in AZ.get("clips") or [])
      and bool(AZ.get("clips")), str(AZ))
check("plage_avant_zero_ne_retire_que_le_temps_reel",
      AZ.get("removed") == 1, str(AZ.get("removed")))
MC = (D.get("mot_a_cheval") or {}).get("clips") or []
check("mot_a_cheval_borne_dans_sa_moitie",
      bool(MC) and all(w["end"] <= c["end"] and w["start"] >= c["start"]
                       for c in MC for w in c.get("words") or []),
      str([(c.get("start"), c.get("end"), c.get("words")) for c in MC]))
SI = (D.get("start_illisible") or {}).get("clips") or []
# `JSON.stringify(NaN)` rend `null` : chercher un NaN cote Python ne trouvait
# donc RIEN, et la ligne passait au vert sur un `srcIn: null` bien present.
# On exige un NOMBRE — c'est ce qui traverse le payload et le rendu.
check("start_illisible_ne_produit_ni_NaN_ni_null",
      bool(SI) and all(isinstance(c.get(k), (int, float))
                       for c in SI for k in ("start", "end", "srcIn")),
      str(SI))

print("\n[10] dropWords — les mots prêtés ne restent pas dans le projet")
DW = D.get("drop") or []
check("drop_retire_les_mots_d_une_piste_non_sous_titres",
      len(DW) == 2 and "words" not in DW[0] and DW[0].get("text") == "x",
      str(DW[:1]))
check("drop_garde_les_mots_d_un_sous_titre",
      len(DW) == 2 and [w["w"] for w in DW[1].get("words") or []] == ["y"],
      str(DW[1:]))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
