# -*- coding: utf-8 -*-
# scripts/patch_bundle_episodes_style.py
"""Assert-guarded patcher : le select « Style » du storyboard Épisodes.

BASELINE : bundle POST-patch dzdesign (dernier patch en date).
Backup dédié : .js.bak_episodes_style (état juste avant CE patch).

Réf : chantier vitrail Młoda Polska 27/08
(docs/superpowers/specs/2026-08-27-option-vitrail-design.md, décision D2-3).
Trois octets chirurgicaux dans DzEpisodes, étape storyboard :

  S1  l'état `sceneStyle` (useState("")) à côté de `sceneMethod` ;
  S2  la requête `D.episodeScenes` transmet `style:sceneStyle` — le backend
      applique le bloc de la famille de façon DÉTERMINISTE aux prompts
      d'illustration (voir routes.py episode_scenes + style_vitrail épinglé),
      les prompts restent éditables dans les cartes de scène ;
  S3  le select UI (primitive `re`) entre le sélecteur de méthode et le
      bouton « Generate scenes » : « Style: none » / « Vitrail Młoda Polska ».

Aucun autre octet ne bouge.

Run : python scripts/patch_bundle_episodes_style.py
"""
import pathlib
import shutil

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_episodes_style")

S1_OLD = ('_sm=x.useState("paragraph"),sceneMethod=_sm[0],'
          'setSceneMethod=_sm[1],')
S1_NEW = ('_sm=x.useState("paragraph"),sceneMethod=_sm[0],'
          'setSceneMethod=_sm[1],_sst=x.useState(""),sceneStyle=_sst[0],'
          'setSceneStyle=_sst[1],')

S2_OLD = ('D.episodeScenes({script:script.trim(),language:lang,'
          'method:sceneMethod})')
S2_NEW = ('D.episodeScenes({script:script.trim(),language:lang,'
          'method:sceneMethod,style:sceneStyle})')

S3_OLD = ('options:[{value:"paragraph",label:"By paragraph"},'
          '{value:"ai",label:"By AI"}]})}),'
          'r.jsx(K,{variant:"primary",size:"sm",icon:"zap",'
          'disabled:sceneBusy||!script.trim(),onClick:genScenes,')
S3_NEW = ('options:[{value:"paragraph",label:"By paragraph"},'
          '{value:"ai",label:"By AI"}]})}),'
          'r.jsx("div",{style:{width:190},title:"Style visuel appliqué aux '
          'prompts d\'illustration (grammaire Młoda Polska épinglée au '
          'backend)",children:r.jsx(re,{value:sceneStyle,'
          'onChange:setSceneStyle,options:[{value:"",label:"Style: none"},'
          '{value:"vitrail",label:"Vitrail Młoda Polska"}]})}),'
          'r.jsx(K,{variant:"primary",size:"sm",icon:"zap",'
          'disabled:sceneBusy||!script.trim(),onClick:genScenes,')


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    s = BUNDLE.read_text(encoding="utf-8")
    if "sceneStyle" in s:
        raise SystemExit("Bundle déjà patché (sceneStyle présent). Aborting.")
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK.name)
    s = apply(s, S1_OLD, S1_NEW, "S1-etat")
    s = apply(s, S2_OLD, S2_NEW, "S2-requete")
    s = apply(s, S3_OLD, S3_NEW, "S3-select")
    BUNDLE.write_text(s, encoding="utf-8", newline="")
    print("bundle écrit :", len(s), "o — select Style du storyboard en place")


if __name__ == "__main__":
    main()
