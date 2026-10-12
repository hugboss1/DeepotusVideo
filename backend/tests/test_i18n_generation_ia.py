# -*- coding: utf-8 -*-
"""t192 (G10, 12/10/2026) — traduction FR/EN des lots « Génération IA » G0-G9 : contrôle final transverse.

Chaque lot G0-G9 a posé ses clés au fil de l'eau ; ce banc vérifie l'ensemble, et les oublis corrigés par t192 (pastille
de modèle de dz-champ-ia.js, refus serveur des routes G4-G7, devis d'un VFX IA, catalogue Musique).

  [1] les catalogues de l'écran (frontend/shared/i18n/<zone>.json) : chaque clé ajoutée par G0-G9 et t192 (liste
      EXPLICITE ci-dessous, relevée par git entre 32b2d6d6 et ab7d0c91 — le plan disait « au moins 60 », il y en a 339, + 12 de t197 sur main)
      existe, fr et en non vides, mêmes {variables} ; le dictionnaire assemblé est à jour et les porte toutes.
  [2] les messages du serveur (backend/app/i18n/messages.json) : idem pour les 180 clés G2-G9 + t192 (devis, musique, bruitages, noms ia.nom.<id> compris).
  [3] les clés UTILISÉES : chaque clé écrite dans les fichiers des lots (dzT, T, __dzT9, TP, t("photolab.…"), Refus,
      Message, msg, _msg_g, _m) existe — dans le dictionnaire assemblé (écran) ou dans messages.json (serveur) ; les
      familles composées (ia.voie.<voie>, detour.modele.<id>, son.sfx.libelle.<id>, vfx.ia.<geste>.titre/phrase,
      ia.nom.<id>, musique.<id>.desc) sont complètes et leur français EST celui du registre (aucune dérive).
  [4] les replis français écrits dans le code (table FR de dz-modeles-ia.js, TP(clé, fr) et PASTILLE_CLES de
      dz-champ-ia.js) sont, au caractère près, le français du dictionnaire.
  [5] plus de français en dur : les modules NEUFS (dz-modeles-ia.js, vectorlab/js/mod-iacalque.js,
      photolab/js/mod-iacalque.js) hors commentaires et replis ; les refus des services et routes des lots (vfx_ia,
      sfx_service, detourage, storyboard3d, pricing._ligne_vfx, routes G5-G7) hors refus d'appel mal formé (liste
      GARDÉE motivée : jamais déclenchés par l'écran).
  [6] fonctionnel : sous node, DzModelesIA rend l'anglais avec un dzT anglais et le français sans ; côté serveur, un
      refus (Refus/Message) garde son français d'avant à l'identique et se dit en anglais sans accent ; le catalogue
      Musique se traduit par copie ; un nom de modèle passe par ia.nom.<id>.

Run : & $PY tests/test_i18n_generation_ia.py   (depuis backend/)
"""
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
BACK = HERE.parent
RACINE = BACK.parent
FRONT = RACINE / "frontend"
sys.path.insert(0, str(BACK))
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


# ── les clés des lots G0-G9 (+ t192), par catalogue — relevé git 32b2d6d6..ab7d0c91 + t192 ──────────────────────
CLES_FRONT = {
    "atelier": (
        "atelier.at2_dzp.a_mesurer", "atelier.at2_dzp.annuler", "atelier.at2_dzp.catalogue_ko",
        "atelier.at2_dzp.choisir", "atelier.at2_dzp.deja_en_cours", "atelier.at2_dzp.modele",
        "atelier.at2_obj3d.bouton_t", "atelier.at2_obj3d.corps_facultatif", "atelier.at2_obj3d.en_cours",
        "atelier.at2_obj3d.err", "atelier.at2_obj3d.objets_aide", "atelier.at2_obj3d.objets_ph",
        "atelier.at2_obj3d.objets_requis", "atelier.at2_obj3d.ouvrir_plateau", "atelier.at2_obj3d.prix",
        "atelier.at2_obj3d.reconstruire", "atelier.at2_obj3d.rester", "atelier.at2_obj3d.sans_image",
        "atelier.at2_obj3d.src_croquis", "atelier.at2_obj3d.src_prod", "atelier.at2_obj3d.titre",
        "atelier.at2_obj3d.unite_a_confirmer", "atelier.at2_video.aide_fl", "atelier.at2_video.aide_i2v",
        "atelier.at2_video.attente", "atelier.at2_video.bouton_t", "atelier.at2_video.cle_absente",
        "atelier.at2_video.cout_inconnu", "atelier.at2_video.debut", "atelier.at2_video.debut_aucune",
        "atelier.at2_video.devis_attente", "atelier.at2_video.devis_ko", "atelier.at2_video.echec",
        "atelier.at2_video.en_cours", "atelier.at2_video.err", "atelier.at2_video.fin_aucune",
        "atelier.at2_video.generees", "atelier.at2_video.generer", "atelier.at2_video.introuvable",
        "atelier.at2_video.lancee", "atelier.at2_video.prix_devis", "atelier.at2_video.progres",
        "atelier.at2_video.sans_debut", "atelier.at2_video.src_croquis", "atelier.at2_video.src_plateau",
        "atelier.at2_video.src_prod", "atelier.at2_video.suivi_arrete", "atelier.at2_video.titre",
        "atelier.plan.objets", "atelier.plan.objets_poses", "atelier.plan.objets_poses_tronques",
        "atelier.plan.reconstruire3d", "atelier.plan.video", "atelier.plan.video_fin",
        "atelier.t183_da.cle_a_ajouter",),
    "avatar": (
        "avatar.decor.sujet", "avatar.decor.sujet_requis",),
    "cartes": (
        "cartes.data2.cle_a_ajouter", "cartes.face.aucune_cle", "cartes.face.cle_a_ajouter",
        "cartes.frame2.aucune_cle", "cartes.frame2.cle_a_ajouter", "cartes.t186.detourer_a_mesurer",
        "cartes.t186.fal_a_mesurer", "cartes.t186.modele", "cartes.t186.sujet", "cartes.t186.sujet_requis",),
    "commun": (
        "ia.voie.fal", "ia.voie.openai", "ia.voie.gemini", "ia.voie.elevenlabs", "ia.voie.meshy", "ia.voie.heygen",
        "ia.voie.local", "ia.prix.a_mesurer", "ia.cle.absente", "ia.cle.a_ajouter", "ia.modele.choisir",
        "ia.etat.chargement", "ia.local.a_demarrer", "ia.pastille.badge", "ia.pastille.titre", "ia.pastille.modeles",
        "ia.pastille.aucun", "ia.pastille.aucun_dispo", "ia.pastille.fixe", "ia.pastille.lecture", "ia.pastille.fige",
        "ia.pastille.sans_selecteur", "ia.pastille.choisir", "ia.pastille.vue_sans_aucun", "ia.pastille.hors_vue",
        "ia.pastille.indisponible", "ia.pastille.actuel", "ia.pastille.choisir_ce", "ia.pastille.fg_desactive",
        "ia.pastille.fg_vide", "ia.pastille.pq_sfx", "ia.pastille.pq_da", "ia.pastille.pq_image_globale",
        "ia.pastille.pq_3d", "ia.pastille.pq_spritelab", "ia.pastille.fixe_heygen_photo", "ia.pastille.fixe_llm",
        "detour.champ.modele", "detour.champ.sujet", "detour.champ.sujet_requis", "detour.modele.local_rembg",
        "detour.modele.local_chroma", "detour.modele.sam3_sujet", "detour.modele.bria_objet",
        "detour.modele.rembg_fal", "detour.modele.sam_3_3d_objects", "detour.modele.sam_3_3d_body",
        "detour.modele.birefnet_v2_video", "detour.modele.veed_video_rapide", "detour.modele.pixelcut_video",
        "detour.modele.sam31_video", "detour.modele.general", "detour.modele.matting",),
    "matiere": (
        "matiere.t182_modele.cle_a_ajouter",),
    "photolab": (
        "photolab.calques.ia", "photolab.menu.calque_ia", "photolab.menu.retirer_fond", "photolab.iacalque.titre",
        "photolab.iacalque.titre_detour", "photolab.iacalque.fermer", "photolab.iacalque.calque",
        "photolab.iacalque.calque_aide", "photolab.iacalque.lieu", "photolab.iacalque.lieu_detour",
        "photolab.iacalque.aucun_calque_libre", "photolab.iacalque.prompt", "photolab.iacalque.placeholder",
        "photolab.iacalque.modele", "photolab.iacalque.modele_aide", "photolab.iacalque.retirer_fond",
        "photolab.iacalque.detourage", "photolab.iacalque.detour_aide", "photolab.iacalque.sujet",
        "photolab.iacalque.sujet_aide", "photolab.iacalque.generer_go", "photolab.iacalque.detourer_go",
        "photolab.iacalque.en_cours", "photolab.iacalque.detour_en_cours", "photolab.iacalque.prix_inconnu",
        "photolab.iacalque.prix", "photolab.iacalque.prix_partiel", "photolab.iacalque.prix_a_mesurer",
        "photolab.iacalque.gratuit", "photolab.iacalque.catalogue_absent", "photolab.iacalque.aucun_document",
        "photolab.iacalque.calque_absent", "photolab.iacalque.calque_groupe", "photolab.iacalque.calque_verrouille",
        "photolab.iacalque.calque_reglage", "photolab.iacalque.prompt_vide", "photolab.iacalque.detour_modele",
        "photolab.iacalque.detour_cle", "photolab.iacalque.sujet_requis", "photolab.iacalque.cle_absente",
        "photolab.iacalque.nom_calque", "photolab.iacalque.pose_inconnue", "photolab.iacalque.reduite",
        "photolab.iacalque.posee", "photolab.iacalque.detour_echoue_pose", "photolab.iacalque.detour_fait",
        "photolab.iacalque.prix_partiel_image",),   # t197 (module commun, sur main après G9)
    "son": (
        "son.gen.local", "son.gen.prix_modele", "son.gen.prix_sfx", "son.sfx.catalogue_attente", "son.sfx.confirmer",
        "son.sfx.cout_fin", "son.sfx.decrire_video", "son.sfx.depuis_video", "son.sfx.garder_voix",
        "son.sfx.libelle.kling_v2a", "son.sfx.libelle.mirelo_video", "son.sfx.libelle.sonilo_video", "son.sfx.modele",
        "son.sfx.prix_modele", "son.sfx.unite_video", "son.sfx.video_aide", "son.sfx.video_fait",
        "son.sfx.video_sans_clip", "son.sfx.video_sonorisee",),
    "sprites": (
        "sprites.t183_pm.defaut", "sprites.t183_pm.modele", "sprites.t183_pm.modele_t", "sprites.t186.modele",
        "sprites.t186.sujet", "sprites.t186.sujet_requis",),
    "studio": (
        "studio.compil.fin_vide", "studio.compose.fin", "studio.video.fl", "studio.video.fl_absent",),
    "studio3d": (
        "studio3d.t186.a_mesurer", "studio3d.t186.coins", "studio3d.t186.confirmer", "studio3d.t186.det_title",
        "studio3d.t186.detouree", "studio3d.t186.modele", "studio3d.t186.sujet", "studio3d.t186.sujet_requis",
        "studio3d.t186.titre",),
    "vectorlab": (
        "vectorlab.iacalque.aucun_calque_libre", "vectorlab.iacalque.biblio_sans_nom", "vectorlab.iacalque.bouton",
        "vectorlab.iacalque.bouton_titre", "vectorlab.iacalque.calque", "vectorlab.iacalque.calque_absent",
        "vectorlab.iacalque.calque_aide", "vectorlab.iacalque.calque_disparu", "vectorlab.iacalque.calque_verrouille",
        "vectorlab.iacalque.catalogue_absent", "vectorlab.iacalque.cle_absente", "vectorlab.iacalque.detour_aide",
        "vectorlab.iacalque.detour_cle", "vectorlab.iacalque.detour_cle_image",
        "vectorlab.iacalque.detour_echoue_pose", "vectorlab.iacalque.detour_en_cours",
        "vectorlab.iacalque.detour_fait", "vectorlab.iacalque.detour_modele",
        "vectorlab.iacalque.detour_remplacement", "vectorlab.iacalque.detour_vide", "vectorlab.iacalque.detourage",
        "vectorlab.iacalque.en_cours", "vectorlab.iacalque.fond", "vectorlab.iacalque.generer_sur",
        "vectorlab.iacalque.image_illisible", "vectorlab.iacalque.image_introuvable",
        "vectorlab.iacalque.image_invalide", "vectorlab.iacalque.masque", "vectorlab.iacalque.meme_image",
        "vectorlab.iacalque.modele_aide", "vectorlab.iacalque.modeles_vides", "vectorlab.iacalque.placeholder",
        "vectorlab.iacalque.pose_echouee", "vectorlab.iacalque.pose_refusee", "vectorlab.iacalque.posee",
        "vectorlab.iacalque.prix", "vectorlab.iacalque.prix_a_mesurer", "vectorlab.iacalque.prix_gratuit",
        "vectorlab.iacalque.prix_inconnu", "vectorlab.iacalque.prix_partiel", "vectorlab.iacalque.prix_partiel_image",
        "vectorlab.iacalque.prompt_vide", "vectorlab.iacalque.reessayer", "vectorlab.iacalque.reseau",
        "vectorlab.iacalque.retirer_fond", "vectorlab.iacalque.retirer_fond_titre", "vectorlab.iacalque.sujet",
        "vectorlab.iacalque.sujet_aide", "vectorlab.iacalque.sujet_requis", "vectorlab.iacalque.titre",
        "vectorlab.image.pose_impossible",
        # t197 / guide (sur main après G9) : guider par les calques du dessous
        "vectorlab.iacalque.guide", "vectorlab.iacalque.guide_aide", "vectorlab.iacalque.guide_aucun_modele",
        "vectorlab.iacalque.guide_choisir", "vectorlab.iacalque.guide_garde", "vectorlab.iacalque.guide_modele",
        "vectorlab.iacalque.guide_modele_remplace", "vectorlab.iacalque.guide_page_etiree", "vectorlab.iacalque.guide_rien",
        "vectorlab.iacalque.guide_sans_nom", "vectorlab.iacalque.posee_guide",),
    "vfx": (
        "vfx.ia.agrandir.phrase", "vfx.ia.agrandir.titre", "vfx.ia.aucune_video", "vfx.ia.bouton_aide",
        "vfx.ia.catalogue_echec", "vfx.ia.chargement", "vfx.ia.choisir", "vfx.ia.choisir_n",
        "vfx.ia.coloriser.phrase", "vfx.ia.coloriser.titre", "vfx.ia.confirmer", "vfx.ia.dans_biblio", "vfx.ia.des",
        "vfx.ia.devis", "vfx.ia.eau.phrase", "vfx.ia.eau.titre", "vfx.ia.echec", "vfx.ia.effacer_objet.phrase",
        "vfx.ia.effacer_objet.titre", "vfx.ia.effacer_perso.phrase", "vfx.ia.effacer_perso.titre",
        "vfx.ia.effets_pixverse.phrase", "vfx.ia.effets_pixverse.titre", "vfx.ia.en_cours", "vfx.ia.fait",
        "vfx.ia.filtrer", "vfx.ia.filtrer_n", "vfx.ia.geste", "vfx.ia.gestes", "vfx.ia.image", "vfx.ia.image_animer",
        "vfx.ia.image_lumiere", "vfx.ia.image_lumiere_aide", "vfx.ia.image_reference", "vfx.ia.indisponible",
        "vfx.ia.inserer_h3.phrase", "vfx.ia.inserer_h3.titre", "vfx.ia.jour_nuit.phrase", "vfx.ia.jour_nuit.titre",
        "vfx.ia.lancer", "vfx.ia.manque_image_animer", "vfx.ia.manque_image_lumiere", "vfx.ia.manque_option",
        "vfx.ia.manque_prompt", "vfx.ia.manque_video", "vfx.ia.opt.couleurs", "vfx.ia.opt.debut", "vfx.ia.opt.duree",
        "vfx.ia.opt.effet", "vfx.ia.opt.enrichir", "vfx.ia.opt.facteur", "vfx.ia.opt.format", "vfx.ia.opt.graine",
        "vfx.ia.opt.objet", "vfx.ia.opt.passe2", "vfx.ia.opt.reprise", "vfx.ia.opt.resolution",
        "vfx.ia.ouvrir_montage", "vfx.ia.prompt", "vfx.ia.prompt_facultatif", "vfx.ia.prompt_requis", "vfx.ia.rail",
        "vfx.ia.rail_bas", "vfx.ia.rail_desc", "vfx.ia.rail_note", "vfx.ia.recadrer.phrase", "vfx.ia.recadrer.titre",
        "vfx.ia.reessayer", "vfx.ia.relight_h3.phrase", "vfx.ia.relight_h3.titre", "vfx.ia.resultat",
        "vfx.ia.retoucher_flux3.phrase", "vfx.ia.retoucher_flux3.titre", "vfx.ia.retoucher_kling.phrase",
        "vfx.ia.retoucher_kling.titre", "vfx.ia.section", "vfx.ia.source", "vfx.ia.source_image",
        "vfx.ia.unite.effet", "vfx.ia.unite.mp", "vfx.ia.unite.s", "vfx.ia.unite.tranche10s", "vfx.ia.unite.video",),
}
CLES_SERVEUR = (
    "ia.video.pas_de_fin", "ia.cle.absente_tir", "photolab.ia.aucun_document", "photolab.ia.calque_illisible",
    "photolab.ia.calque_inconnu", "photolab.ia.calque_groupe", "photolab.ia.calque_sans_pixels",
    "photolab.ia.calque_vide", "photolab.ia.prompt_vide", "photolab.ia.taille", "photolab.ia.modele_inconnu",
    "photolab.ia.modele_vectoriel", "photolab.ia.pose_echouee", "photolab.ia.nom_calque", "ia.detour.inconnu",
    "ia.detour.nature", "ia.detour.sujet", "photolab.ia.parametre_inconnu", "photolab.ia.booleen",
    "photolab.ia.document_change", "photolab.ia.fournisseur", "photolab.ia.nom_detoure", "ia.prompt.trop_long",
    "ia.sfx.prompt_trop_long", "ia.sfx.prompt_requis", "ia.video.format", "ia.video.format_sans_ext",
    "ia.video.duree_plage", "ia.video.duree_moins", "ia.video.duree_max", "ia.video.duree_illisible",
    "ia.video.clip_introuvable", "ia.fichier.video_introuvable", "ia.fichier.image_introuvable",
    "ia.cle.non_configuree", "ia.image.pas_de_retouche", "ia.detour.sujet_manquant", "ia.detour.rembg_absent",
    "ia.detour.chroma_pas_uni", "ia.detour.refuse", "ia.detour.echec_fournisseur", "vfx.ia.option_requise",
    "vfx.ia.option_bornes", "vfx.ia.option_trop_longue", "vfx.ia.reprise_apres", "vfx.ia.reprise_avant_debut",
    "vfx.ia.pixverse_1080p", "vfx.ia.prompt_requis", "vfx.ia.sans_image", "vfx.ia.image_a_animer",
    "vfx.ia.image_lumiere", "vfx.ia.source_image", "vfx.ia.images_min", "vfx.ia.images_max", "vfx.ia.budget_720p",
    "vfx.ia.budget", "vfx.ia.cotes", "vfx.ia.poids_moins", "vfx.ia.poids_max", "vfx.ia.insertion_hors",
    "pricing.vfx.ligne", "pricing.vfx.ligne_a_mesurer", "pricing.vfx.ligne_jetons",
    "pricing.vfx.ligne_a_mesurer_jetons", "vfx.det.scene", "vfx.det.topaz", "vfx.det.passe1", "vfx.det.passe2",
    "vfx.det.passe1_masque", "vfx.det.passe2_masque", "storyboard3d.objets_requis", "storyboard3d.sans_image",
    "storyboard3d.plan_sans_image", "storyboard3d.image_illisible", "storyboard3d.objets_a_decrire",
    "storyboard3d.scene_pleine", "plan.video.sans_debut", "plan.video.debut_introuvable",
    "plan.video.fin_introuvable", "plan.video.mouvement_requis", "cartes.lot.cle_absente", "cartes.lot.la_cle",
    "ia.nom.relight-h3", "ia.nom.inserer-h3", "ia.nom.effacer-perso", "ia.nom.effacer-objet", "ia.nom.jour-nuit",
    "ia.nom.eau", "ia.nom.coloriser", "ia.nom.retoucher-kling", "ia.nom.retoucher-flux3", "ia.nom.recadrer",
    "ia.nom.agrandir", "ia.nom.effets-pixverse", "ia.nom.sonilo-video", "ia.nom.mirelo-video", "ia.nom.kling-v2a",
    "ia.nom.local-rembg", "ia.nom.local-chroma", "ia.nom.sam3-sujet", "ia.nom.bria-objet", "ia.nom.rembg-fal",
    "ia.nom.birefnet-v2-video", "ia.nom.veed-video-rapide", "ia.nom.pixelcut-video", "ia.nom.sam31-video",
    "ia.nom.sam-3-3d-objects", "ia.nom.sam-3-3d-body", "ia.nom.general", "ia.nom.matting", "musique.ace-step.nom",
    "musique.lyria3.desc", "musique.stable-audio-25.desc", "musique.minimax-music-26.desc", "musique.cassetteai.desc",
    "musique.ace-step.desc", "musique.minimax-music-20.desc", "musique.lyria-3.5.desc",
    "musique.elevenlabs-music-2.5.desc", "musique.minimax-music-3.desc", "musique.stable-audio-3.desc",
    "musique.mureka-9.5.desc", "musique.ambiance.cinematic", "musique.ambiance.abyss", "musique.ambiance.hype",
    "musique.ambiance.lofi", "musique.ambiance.synthwave", "musique.ambiance.corporate", "musique.ambiance.tension",
    "musique.ambiance.chill",
    # t192 relecture : devis G4/G5/G7, matte, musique, bruitages, options VFX, noms des modèles de musique
   
    "pricing.a_mesurer", "pricing.ligne_sec", "pricing.ligne_x", "pricing.detour.tranches", "pricing.objets3d.ligne",
    "pricing.objets3d.ligne_a_mesurer", "pricing.matte.ligne", "pricing.matte.ligne_a_mesurer", "pricing.musique.sec",
    "pricing.musique.min", "pricing.musique.piste", "pricing.musique.piste_a_mesurer", "pricing.musique.avec_paroles",
    "pricing.musique.sans_paroles", "matte.note_birefnet", "matte.note_a_mesurer", "musique.decrire",
    "musique.duree_bornes", "musique.paroles_exigees_10", "musique.paroles_exigees_3000",
    "musique.note.duree_imposee", "musique.note.duree_imposee_s", "musique.note.sans_paroles",
    "musique.note.sans_graine", "ia.sfx.modele_inconnu", "ia.sfx.nature_description", "ia.sfx.nature_video",
    "ia.sfx.duree_invalide", "ia.sfx.duree_positive", "ia.sfx.decrire", "ia.sfx.prompt_450", "ia.sfx.duree_route",
    "vfx.ia.option_inconnue", "vfx.ia.option_inconnue_aucune", "vfx.ia.option_refusee", "vfx.ia.option_booleen",
    "vfx.ia.option_nombre", "vfx.ia.option_entier", "vfx.ia.option_texte", "ia.nom.lyria3", "ia.nom.stable-audio-25",
    "ia.nom.minimax-music-26", "ia.nom.cassetteai", "ia.nom.ace-step", "ia.nom.minimax-music-20", "ia.nom.lyria-3.5",
    "ia.nom.elevenlabs-music-2.5", "ia.nom.minimax-music-3", "ia.nom.stable-audio-3", "ia.nom.mureka-9.5",)

# les fichiers des lots (écran) dont chaque clé écrite doit exister dans le dictionnaire assemblé
FICHIERS_ECRAN = (
    "shared/dz-modeles-ia.js", "shared/dz-champ-ia.js", "shared/dz-iacalque-commun.js", "vectorlab/js/mod-iacalque.js",
    "vectorlab/js/mod-image.js",
    "photolab/js/mod-iacalque.js", "photolab/js/mod-menus.js", "photolab/js/mod-calques.js", "atelier/atelier.js",
    "patches/vfxrack.js", "patches/sfxstudio.js", "patches/son-vfx-montage.js", "avatar/avatar.js",
    "cardforge/js/mod-capture.js", "materialforge/materialforge.js", "spritelab/spritelab.js", "studio3d/vues.js")
# les fichiers des lots (serveur) dont chaque clé de message écrite doit exister dans messages.json
FICHIERS_SERVEUR = (
    "app/api/routes.py", "app/api/photolab_routes.py", "app/api/avatar_live_routes.py", "app/services/vfx_ia.py",
    "app/services/sfx_service.py", "app/services/detourage.py", "app/services/storyboard3d.py",
    "app/services/pricing.py", "app/services/cards/capture.py", "app/services/cards/data.py",
    "app/i18n/catalogues.py")
# les modules NEUFS des lots : aucun français hors commentaires et replis
MODULES_NEUFS = ("shared/dz-modeles-ia.js", "shared/dz-iacalque-commun.js", "vectorlab/js/mod-iacalque.js",
                 "photolab/js/mod-iacalque.js")

VAR = re.compile(r"\{(\w+)\}")
ACCENTS = re.compile(r"[àâçéèêëîïôûùüÿœæ«»]", re.I)
MOTS_FR = re.compile(r"\b(le|la|les|une|des|du|aucun|aucune|avec|sans|pour|dans|calque|fond|retirer|modèle|clé|"
                     r"détourer|générer|choisissez|donnez|décrivez)\b", re.I)


def francais(t: str) -> bool:
    t = str(t)
    if not re.search(r"[A-Za-zÀ-ÿ]{2}", t) or re.fullmatch(r"[\w.\-/:#%]+", t):
        return False                                      # identifiant, clé, chemin, classe
    return bool(ACCENTS.search(t) or MOTS_FR.search(t))


def lire(p: pathlib.Path) -> str:
    return p.read_bytes().decode("utf-8")


def dico_assemble() -> dict:
    """frontend/shared/dz-i18n-dico.js -> {clé: {fr, en, …}} (le fichier est un appel Object.assign(…, {json}))."""
    s = lire(FRONT / "shared" / "dz-i18n-dico.js")
    i = s.index("{", s.index("Object.assign("))
    i = s.index("{", i + 1)
    j = s.rindex("}")
    return json.loads(s[i:j + 1])


# ── tokeniseur JS minimal : chaînes ("…", '…', `…` sans ${…}), commentaires sautés, littéraux regex sautés ──────────
def chaines_js(src: str):
    """[(position, texte, guillemet)] des littéraux de chaîne d'un source JS, hors commentaires et regex."""
    out, i, n = [], 0, len(src)
    prec = ""                                             # dernier caractère significatif (regex ou division ?)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            i = src.find("\n", i)
            i = n if i < 0 else i
            continue
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "/" and (prec == "" or prec in "(,=:[!&|?{};+-*%<>~^") :
            j, cls = i + 1, False                         # littéral regex : jusqu'au / non échappé hors classe
            while j < n and src[j] != "\n":
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "[":
                    cls = True
                elif src[j] == "]":
                    cls = False
                elif src[j] == "/" and not cls:
                    break
                j += 1
            i, prec = j + 1, "x"
            continue
        if c in "\"'`":
            j, buf = i + 1, []
            while j < n and src[j] != c:
                if src[j] == "\\":
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if c == "`" and src.startswith("${", j):  # gabarit : l'expression (accolades équilibrées) est
                    k, prof = j + 2, 1                    # relue à part — ses propres chaînes comptent aussi
                    while k < n and prof:
                        prof += {"{": 1, "}": -1}.get(src[k], 0)
                        k += 1
                    out += [(j + 2 + p, t, q) for p, t, q in chaines_js(src[j + 2:k - 1])]
                    buf.append(" ")
                    j = k
                    continue
                buf.append(src[j])
                j += 1
            out.append((i, "".join(buf), c))
            i, prec = j + 1, "x"
            continue
        if not c.isspace():
            prec = c if c in "(,=:[!&|?{};+-*%<>~^)]" else "x"
            if c in ")]":
                prec = "x"
        i += 1
    return out


def main():
    from app import i18n as I

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
    print("\n[1] les catalogues de l'écran")
    d_zone, vus, manquantes, vides, variables = {}, 0, [], [], []
    for zone, cles in CLES_FRONT.items():
        d = json.loads(lire(FRONT / "shared" / "i18n" / f"{zone}.json"))
        d_zone.update(d)
        for k in cles:
            vus += 1
            e = d.get(k)
            if not isinstance(e, dict):
                manquantes.append(f"{zone}:{k}")
                continue
            fr, en = e.get("fr"), e.get("en")
            if not (isinstance(fr, str) and fr.strip() and isinstance(en, str) and en.strip()):
                vides.append(f"{zone}:{k}")
            elif set(VAR.findall(fr)) != set(VAR.findall(en)):
                variables.append(f"{zone}:{k} fr={VAR.findall(fr)} en={VAR.findall(en)}")
    check(f"1a les {vus} clés des lots existent dans leur catalogue", not manquantes, manquantes[:10])
    check("1b chaque clé a un fr ET un en non vides", not vides, vides[:10])
    check("1c mêmes {variables} en français et en anglais", not variables, variables[:10])
    check("1d au moins 351 clés d'écran (relevé réel ; le plan en annonçait 60)", vus >= 351, vus)
    p = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1e i18n_assembler.py --check : dictionnaire assemblé à jour", p.returncode == 0, (p.stdout + p.stderr)[-300:])
    D = dico_assemble()
    absentes = [k for cles in CLES_FRONT.values() for k in cles
                if k not in D or D[k].get("en") != d_zone.get(k, {}).get("en")]
    check("1f le dictionnaire assemblé porte chaque clé, avec son anglais", not absentes, absentes[:10])
    check("1g la copie dist/shared du dictionnaire est identique à l'octet",
          (FRONT / "shared" / "dz-i18n-dico.js").read_bytes() == (FRONT / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())
    for f in ("dz-modeles-ia.js", "dz-champ-ia.js", "dz-iacalque-commun.js"):
        check(f"1h dist/shared/{f} = shared/{f} (octet pour octet)",
              (FRONT / "shared" / f).read_bytes() == (FRONT / "dist" / "shared" / f).read_bytes())

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
    print("\n[2] les messages du serveur")
    M = json.loads(lire(BACK / "app" / "i18n" / "messages.json"))
    mq = [k for k in CLES_SERVEUR if k not in M]
    vd = [k for k in CLES_SERVEUR if k in M and not (str(M[k].get("fr") or "").strip() and str(M[k].get("en") or "").strip())]
    vr = [k for k in CLES_SERVEUR if k in M and set(VAR.findall(M[k].get("fr", ""))) != set(VAR.findall(M[k].get("en", "")))]
    check(f"2a les {len(CLES_SERVEUR)} clés serveur des lots existent dans messages.json", not mq, mq[:10])
    check("2b fr ET en non vides", not vd, vd[:10])
    check("2c mêmes {variables}", not vr, vr[:10])
    check("2d au moins 180 clés serveur (G2-G9 : 22, t192 : 158)", len(CLES_SERVEUR) >= 180, len(CLES_SERVEUR))
    en_fr = [k for k in CLES_SERVEUR if k in M and ACCENTS.search(M[k].get("en", "").replace("→", ""))]
    check("2e aucun anglais serveur ne porte d'accent français", not en_fr, en_fr[:10])

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
    print("\n[3] les clés utilisées existent")
    CLE_JS = re.compile(r"""(?<![\w.])(?:dzT|__dzT9|T|TP|W\.dzT|window\.dzT)\(\s*["']([a-z0-9_]+(?:\.[A-Za-z0-9_\-]+)+)["']""")
    CLE_PL = re.compile(r"""(?<![\w.])t\(\s*["'](photolab\.[A-Za-z0-9_.\-]+)["']""")
    total, perdues = 0, []
    for f in FICHIERS_ECRAN:
        s = lire(FRONT / f)
        ks = set(CLE_JS.findall(s)) | set(CLE_PL.findall(s))
        total += len(ks)
        perdues += [f"{f}:{k}" for k in sorted(ks) if k not in D]
    check(f"3a chaque clé écrite dans les {len(FICHIERS_ECRAN)} fichiers d'écran des lots existe ({total} clés)",
          not perdues and total >= 1500, perdues[:10] or total)
    CLE_PY = re.compile(r"""(?<![\w.])(?:Refus|Message|_msg_g|_i18n\.msg|I\.msg|msg|_m)\(\s*["']([a-z0-9_]+(?:\.[A-Za-z0-9_\-]+)+)["']""")
    tot_s, perdues_s = 0, []
    for f in FICHIERS_SERVEUR:
        s = lire(BACK / f)
        ks = set(CLE_PY.findall(s))
        tot_s += len(ks)
        perdues_s += [f"{f}:{k}" for k in sorted(ks) if k not in M]
    check(f"3b chaque clé de message écrite dans les fichiers serveur des lots existe ({tot_s} clés)",
          not perdues_s and tot_s >= 60, perdues_s[:10] or tot_s)
    # clés COMPOSÉES dans le code : les combinaisons possibles existent toutes
    composees = ["pricing.vfx.ligne" + a + j for a in ("", "_a_mesurer") for j in ("", "_jetons")]
    composees += ["vfx.det.passe" + p_ + m_ for p_ in ("1", "2") for m_ in ("", "_masque")]
    composees += ["ia.video.format", "ia.video.format_sans_ext", "ia.video.duree_plage", "ia.video.duree_moins",
                  "ia.video.duree_max", "vfx.ia.budget", "vfx.ia.budget_720p", "vfx.ia.poids_moins", "vfx.ia.poids_max",
                  "vfx.ia.image_a_animer", "vfx.ia.image_lumiere", "ia.fichier.image_introuvable",
                  "ia.fichier.video_introuvable"]
    check("3c les clés serveur composées à l'exécution existent toutes", all(k in M for k in composees),
          [k for k in composees if k not in M])
    from app.services import detourage as DT, sfx_service as SX, vfx_ia as VI, storyboard3d as SB
    from app.services import matte_service as MT, music_service as MS
    import app.api.routes  # noqa: F401  (inscrit les natures du catalogue)
    from app.services import catalogue_ia as CI
    voies = sorted({m.get("voie") for n in CI.natures() for m in CI.lister(n) if m.get("voie")})
    js_mod = lire(FRONT / "shared" / "dz-modeles-ia.js")
    ordre = json.loads(re.search(r"var ORDRE = (\[[^\]]*\])", js_mod).group(1))
    check("3d ia.voie.<voie> pour chaque voie servie par le catalogue et chaque voie d'ORDRE",
          all(f"ia.voie.{v}" in D for v in set(voies) | set(ordre)), [v for v in set(voies) | set(ordre) if f"ia.voie.{v}" not in D])
    reg_fr = {**{k: v["label"] for k, v in DT.REGISTRE.items()}, **{k: v["label"] for k, v in SB.MODELES.items()},
              **{k: v["label"] for k, v in MT.MATTE_MODELS.items()}}
    a_traduire = {k: l for k, l in reg_fr.items() if francais(l) or re.search(r"\b(vidéo|rapide|local|gratuit|ancien)\b", l)}
    derive = [k for k, l in a_traduire.items()
              if (D.get("detour.modele." + k.replace("-", "_")) or {}).get("fr") != l]
    check(f"3e detour.modele.<id> pour les {len(a_traduire)} libellés FRANÇAIS du détourage / SAM 3 / matte, fr = le registre",
          len(a_traduire) >= 10 and not derive, derive)
    sfx_fr = {k: v["label"] for k, v in SX.SFX_MODELS.items() if francais(v["label"]) or "vidéo" in v["label"]}
    derive = [k for k, l in sfx_fr.items() if (D.get("son.sfx.libelle." + k.replace("-", "_")) or {}).get("fr") != l]
    check(f"3f son.sfx.libelle.<id> pour les {len(sfx_fr)} libellés français des bruitages, fr = le registre",
          len(sfx_fr) >= 3 and not derive, derive)
    sans = [g for g in VI.REGISTRE if not all(f"vfx.ia.{g.replace('-', '_')}.{r}" in D for r in ("titre", "phrase"))]
    check(f"3g vfx.ia.<geste>.titre/phrase pour les {len(VI.REGISTRE)} gestes VFX IA", not sans, sans)
    noms = {k[len("ia.nom."):]: v for k, v in M.items() if k.startswith("ia.nom.")}
    tous = {**reg_fr, **{k: v["label"] for k, v in SX.SFX_MODELS.items()}, **{k: v["label"] for k, v in VI.REGISTRE.items()},
            **{k: v["label"] for k, v in MS.MUSIC_MODELS.items()}}
    derive = [k for k, v in noms.items() if tous.get(k) != v.get("fr")]
    manque_nom = [k for k, l in tous.items() if (francais(l) or re.search(r"\b(vidéo|rapide|gratuit|ancien|nuit|eau)\b", l))
                  and k not in noms]
    check(f"3h ia.nom.<id> ({len(noms)}) : fr = le libellé du registre ; chaque libellé français a son nom serveur",
          not derive and not manque_nom, (derive, manque_nom))
    cat = MS.catalog()
    derive = [m["id"] for m in cat["models"] if (M.get(f"musique.{m['id']}.desc") or {}).get("fr") != m["desc"]]
    derive += [a["id"] for a in cat["moods"] if (M.get(f"musique.ambiance.{a['id']}") or {}).get("fr") != a["name"]]
    derive += [m["id"] for m in cat["models"] if francais(m["label"]) and (M.get(f"musique.{m['id']}.nom") or {}).get("fr") != m["label"]]
    check(f"3i musique.* : chaque description ({len(cat['models'])}), ambiance ({len(cat['moods'])}) et nom français du "
          "catalogue a sa clé, fr = le catalogue", not derive, derive)
    sans = [m["id"] for m in cat["models"] if (M.get(f"ia.nom.{m['id']}") or {}).get("fr") != m["label"]]
    check(f"3j ia.nom.<id> pour TOUS les modèles du catalogue Musique ({len(cat['models'])}), fr = le libellé "
          "(le 503 « clé absente » de /audio/music les nomme)", len(cat["models"]) >= 11 and not sans, sans)
    tous_ids = {}
    for nom_reg, reg in (("detourage", DT.REGISTRE), ("matte", MT.MATTE_MODELS), ("sfx", SX.SFX_MODELS),
                         ("vfx", VI.REGISTRE), ("sam3", SB.MODELES), ("musique", MS.MUSIC_MODELS)):
        for k in reg:
            tous_ids.setdefault(k, []).append(nom_reg)
    doubles = {k: v for k, v in tous_ids.items() if len(v) > 1}
    check("3k l'espace ia.nom.<id> est partagé sans collision : aucun id dans deux registres", not doubles, doubles)
    var_reservee = [k for k in CLES_SERVEUR if k in M and {"cle", "lang"} & set(VAR.findall(M[k]["fr"] + M[k]["en"]))]
    check("3l aucune clé serveur des lots n'a de {cle} ni {lang} (noms des paramètres de msg / Message)",
          not var_reservee, var_reservee)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
    print("\n[4] les replis français écrits dans le code")
    table = re.search(r"var FR = \{(.*?)\n\s*\};", js_mod, re.S).group(1)
    repli = dict(re.findall(r'"([a-z0-9_.]+)":\s*"([^"]*)"', table))
    faux = [k for k, v in repli.items() if (D.get(k) or {}).get("fr") != v]
    check(f"4a dz-modeles-ia.js : la table FR ({len(repli)} replis) = le français du dictionnaire", len(repli) >= 9 and not faux, faux)
    champ = lire(FRONT / "shared" / "dz-champ-ia.js")
    tp = re.findall(r'TP\("([a-z0-9_.]+)",\s*"((?:[^"\\]|\\.)*)"', champ)
    faux = [k for k, v in tp if (D.get(k) or {}).get("fr") != v]
    check(f"4b dz-champ-ia.js : chaque TP(clé, repli) ({len(tp)}) a pour repli le français du dictionnaire",
          len(tp) >= 15 and not faux, faux)
    pc = dict((v, k) for k, v in re.findall(r'"([^"]+)":\s*"(ia\.pastille\.[a-z0-9_]+)"', champ))
    da = re.search(r'var DA = "([^"]+)"', champ).group(1)
    pc["ia.pastille.pq_da"] = da
    faux = [k for k, v in pc.items() if (D.get(k) or {}).get("fr") != v]
    check(f"4c dz-champ-ia.js : PASTILLE_CLES ({len(pc)}) — chaque raison / nom fixe a sa clé, fr = le texte posé",
          len(pc) >= 9 and not faux and 'PASTILLE_CLES[DA] = "ia.pastille.pq_da"' in champ, faux)
    sources_pq = re.findall(r'A_(?:defaut|texte)\([^)]*?"((?:le|la) [^"]+)"\)', champ) + re.findall(r'A_fixe\("([^"]+)"\)', champ)
    sources_pq += re.findall(r'pourquoi: "([^"]+)"', champ)
    sans_cle = [t for t in sources_pq if t not in pc.values() and francais(t)]
    check("4d chaque raison « pourquoi » et nom fixe FRANÇAIS des adaptateurs passe par PASTILLE_CLES", not sans_cle, sans_cle)

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
    print("\n[5] plus de français en dur")
    for f in MODULES_NEUFS:
        s = lire(FRONT / f)
        if f.endswith("dz-modeles-ia.js"):           # la table de repli FR est vérifiée en [4]
            a, b = s.index("var FR = {"), s.index("};", s.index("var FR = {"))
            s = s[:a] + " " * (b - a) + s[b:]
        lits = [t for _, t, _ in chaines_js(s) if francais(t)]
        check(f"5a {f} : aucun littéral français hors commentaires et replis", not lits, lits[:8])

    def chaine_de(n):
        """le texte d'un littéral (Constant str) ou les morceaux fixes d'un f-string, sinon None."""
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            return n.value
        if isinstance(n, ast.JoinedStr):
            return "".join(v.value for v in n.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
        if isinstance(n, ast.BinOp):
            g, d = chaine_de(n.left), chaine_de(n.right)
            return (g or "") + (d or "") if (g or d) else None
        return None

    # Refus GARDÉS en dur : le texte FIXE exact (les morceaux littéraux du f-string), et pourquoi. Jamais déclenchés
    # par l'écran (listes fermées, contrôles bornés, appels internes), ou échec technique d'un fournisseur — lot L10.
    _API = "appel mal formé : l'écran envoie toujours une valeur de sa liste / de son contrôle borné"
    _FOURN = "réponse inexploitable d'un fournisseur (échec technique, 502)"
    _INTERNE = "appel interne après les contrôles de la route (jamais atteint depuis l'écran)"
    GARDES_API = {
        "options : un objet {nom: valeur} est attendu": _API,
        "clip_id refusé": _API,
        "donnez la vidéo  : clip_id (un clip du Montage) ou video_filename": _API,
        " refusé : un nom  nu ()": _API,
        "origine refusée :  ()": _API,
        "Modèle de storyboard 3D inconnu :  (connus : ).": _API,
        "detection_threshold : un nombre de 0,1 à 1.": _API,
        "Modèle vidéo inconnu :  (ids : ).": _API,
        "duration_s : un nombre de secondes.": _API,
        "duration_s invalide ( s).": _API,
        "seed doit être un entier.": _API,
        "VFX IA : geste inconnu  (non chiffré)": _API,
        "Bruitage : modèle inconnu  (non chiffré)": _API,
        "Storyboard 3D : modèle inconnu  (non chiffré)": _API,
        "Détourage : modèle inconnu  (non chiffré)": _API,
        "boîtes : une liste d'au plus  rectangles {x_min, y_min, x_max, y_max}.": _API,
        "boîte  illisible.": _API,
        "boîte  illisible : x_min, y_min, x_max, y_max attendus.": _API,
        "boîte  vide ou hors de l'image.": _API,
        "boîte  hors de l'image ( ×  px).": _API,
        "boîte  : object_id entier attendu.": _API,
        "modèle SAM 3 inconnu :  (connus : )": _API,
        " part d'une vidéo : aucune vidéo fournie": _INTERNE,
        " passe par l'API directe : aucune requête fal": _INTERNE,
        "vidéo source introuvable": _INTERNE,
        "image source introuvable": _INTERNE,
        "Plan introuvable.": _INTERNE,
        "fal.ai () : aucun son dans la réponse (clés : )": _FOURN,
        "fal.ai () : aucune image dans la réponse (clés : )": _FOURN,
        "SAM 3 (fal) : aucun GLB dans la réponse (clés : ).": _FOURN,
        "SAM 3 (fal) : le fichier rendu n'est pas un GLB (en-tête glTF absent,  octets).": _FOURN,
        "SAM 3 (fal) : ": _FOURN,
        "fal.ai: ": _FOURN,
        "ElevenLabs: ": _FOURN,
    }
    CIBLES = {
        "app/services/vfx_ia.py": ("options_valides", "prompt_valide", "image_refusee", "source_refusee",
                                   "insertion_refusee", "unites"),
        "app/services/sfx_service.py": ("build_request", "video_refusee"),
        "app/services/detourage.py": ("sujet_de", "_local_rembg", "_local_chroma"),
        "app/services/storyboard3d.py": ("build_request", "reconstruire"),
        "app/services/pricing.py": ("_ligne_vfx", "_ligne_sfx", "_ligne_objets3d", "_ligne_detourage"),
        "app/services/music_service.py": ("build_prompt", "_duree", "_payload_champs", "_payload"),
        "app/services/matte_service.py": ("note_prix",),
        "app/api/routes.py": ("generate_sfx_video", "generate_sfx_audio", "vfx_ia_appliquer", "shot_objets3d",
                              "_video_plan", "_sfx_video_source", "_nom_nu", "_detourage_controles",
                              "generate_music_audio", "cost_estimate", "matte_status"),
        "app/api/photolab_routes.py": ("calque_detourer", "calque_ia"),
        "app/services/cards/capture.py": ("_rembg_par_registre",),
    }
    for f, fonctions in CIBLES.items():
        arbre = ast.parse(lire(BACK / f))
        vues, durs = set(), []
        for fn in ast.walk(arbre):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name not in fonctions:
                continue
            vues.add(fn.name)
            for n in ast.walk(fn):
                cands = []
                if isinstance(n, ast.Return) and n.value is not None:
                    cands.append(n.value)
                if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
                    cands += list(n.exc.args)
                if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) in ("HTTPException", "_refus", "_line"):
                    cands += list(n.args)
                if isinstance(n, ast.Assign) and any(getattr(t, "id", "") in ("label", "det", "conseil", "quoi", "haut", "bas")
                                                     for t in n.targets):
                    cands.append(n.value)
                for c in cands:
                    t = chaine_de(c)
                    if t and francais(t) and t not in GARDES_API:
                        durs.append(f"{fn.name}:{n.lineno}: {t[:70]}")
        check(f"5b {f} : les refus des lots passent par messages.json (hors refus d'appel mal formé gardés)",
              vues == set(fonctions) and not durs, (sorted(set(fonctions) - vues), durs[:8]))

    # ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
    print("\n[6] fonctionnel")
    from app.services import pricing as PR
    exemples = []
    try:
        VI.options_valides("inserer-h3", {"start_time": 3, "resume_time": 2})
    except ValueError as e:
        exemples.append(e)
    try:
        VI.prompt_valide("effacer-objet", "")
    except ValueError as e:
        exemples.append(e)
    try:
        DT.sujet_de("sam3-sujet", "")
    except ValueError as e:
        exemples.append(e)
    m1 = SX.video_refusee("kling-v2a", pathlib.Path("a.mp4"), 100)
    m2 = VI.source_refusee("retoucher-kling", "a.avi", 5)
    exemples += [m1, m2, VI.image_refusee("effets-pixverse", False)]
    check("6a les refus d'exemple sont des Refus / Message de app.i18n",
          len(exemples) == 6 and all(isinstance(x, (I.Refus, I.Message)) for x in exemples), [type(x) for x in exemples])
    # table FIGÉE : appel -> texte français rendu par main AVANT t192 (sonde relecture2/cas6b.py, identique à l'octet)
    CAS_6B = [
        ("VI.source_refusee('relight-h3', 'a.mp4', 30)", lambda: VI.source_refusee("relight-h3", "a.mp4", 30)),
        ("VI.source_refusee('relight-h3', 'a.mp4', 0.5)", lambda: VI.source_refusee("relight-h3", "a.mp4", 0.5)),
        ("VI.source_refusee('retoucher-flux3', 'a.mp4', 20)", lambda: VI.source_refusee("retoucher-flux3", "a.mp4", 20)),
        ("VI.source_refusee('retoucher-flux3', 'a.mp4', 5, None, None, 60_000_000)", lambda: VI.source_refusee("retoucher-flux3", "a.mp4", 5, None, None, 60_000_000)),
        ("VI.source_refusee('retoucher-kling', 'a.mp4', 5, None, None, 300_000_000)", lambda: VI.source_refusee("retoucher-kling", "a.mp4", 5, None, None, 300_000_000)),
        ("VI.source_refusee('retoucher-kling', 'a.mp4', 5, None, (100, 5000))", lambda: VI.source_refusee("retoucher-kling", "a.mp4", 5, None, (100, 5000))),
        ("VI.source_refusee('effacer-perso', 'a.mp4', 7.9, {'resolution': '720p'})", lambda: VI.source_refusee("effacer-perso", "a.mp4", 7.9, {"resolution": "720p"})),
        ("VI.source_refusee('effacer-perso', 'a.mp4', 30, {'resolution': '480p'})", lambda: VI.source_refusee("effacer-perso", "a.mp4", 30, {"resolution": "480p"})),
        ("VI.source_refusee('effacer-perso', 'a.mp4', 100, {'resolution': '480p'})", lambda: VI.source_refusee("effacer-perso", "a.mp4", 100, {"resolution": "480p"})),
        ("VI.source_refusee('effets-pixverse', 'a.mp4', 3)", lambda: VI.source_refusee("effets-pixverse", "a.mp4", 3)),
        ("VI.options_valides('effets-pixverse', {'duration': '10', 'resolution': '1080p'})", lambda: VI.options_valides("effets-pixverse", {"duration": "10", "resolution": "1080p"})),
        ("VI.options_valides('recadrer', {'inconnue': 1})", lambda: VI.options_valides("recadrer", {"inconnue": 1})),
        ("VI.options_valides('agrandir', {'upscale_factor': 'abc'})", lambda: VI.options_valides("agrandir", {"upscale_factor": "abc"})),
        ("VI.options_valides('agrandir', {'upscale_factor': 99})", lambda: VI.options_valides("agrandir", {"upscale_factor": 99})),
        ("VI.prompt_valide('retoucher-flux3', 'x' * 2000)", lambda: VI.prompt_valide("retoucher-flux3", "x" * 2000)),
        ("devis vfx effacer-objet", lambda: PR.estimate(VI.op_vfx("effacer-objet", 4.0, {"enable_pass2_refinement": True, "mask_prompt": "m"}))["breakdown"][0]["label"]),
        ("devis vfx inserer-h3", lambda: PR.estimate(VI.op_vfx("inserer-h3", 7.5, {}, 1280, 720))["breakdown"][0]["label"]),
        ("devis vfx agrandir", lambda: PR.estimate(VI.op_vfx("agrandir", 25, {}, 1280, 720))["breakdown"][0]["label"]),
        ("devis sfx mirelo-1.6", lambda: PR.estimate({"kind": "sfx", "modele": "mirelo-1.6", "secondes": 4, "echantillons": 2})["breakdown"][0]["label"]),
        ("devis sfx kling-v2a", lambda: PR.estimate({"kind": "sfx_video", "modele": "kling-v2a", "secondes": 6})["breakdown"][0]["label"]),
        ("devis détourage sam3-sujet x3", lambda: PR.estimate({"kind": "detourage", "modele": "sam3-sujet", "images": 3})["breakdown"][0]["label"]),
        ("devis détourage birefnet-v2-video 95 images", lambda: PR.estimate({"kind": "detourage", "modele": "birefnet-v2-video", "images_video": 95})["breakdown"][0]["label"]),
        ("devis détourage local-rembg", lambda: PR.estimate({"kind": "detourage", "modele": "local-rembg", "images": 2})["breakdown"][0]["label"]),
        ("devis matte BiRefNet", lambda: PR.estimate(MT.op_devis("general", 6.5))["breakdown"][0]["label"]),
        ("devis objets3d", lambda: PR.estimate({"kind": "objets3d", "modele": "sam-3-3d-objects", "n": 2})["breakdown"][0]["label"]),
        ("devis musique ace-step", lambda: PR.estimate({"kind": "music", "model": "ace-step", "duration_s": 45, "n": 2})["breakdown"][0]["label"]),
        ("devis musique elevenlabs-music-2.5", lambda: PR.estimate({"kind": "music", "model": "elevenlabs-music-2.5", "duration_s": 90})["breakdown"][0]["label"]),
        ("devis musique mureka-9.5 paroles", lambda: PR.estimate({"kind": "music", "model": "mureka-9.5", "paroles": True})["breakdown"][0]["label"]),
        ("devis musique lyria-3.5", lambda: PR.estimate({"kind": "music", "model": "lyria-3.5"})["breakdown"][0]["label"]),
        ("MT.note_prix('pixelcut-video')", lambda: MT.note_prix("pixelcut-video")),
        ("MT.USD_NOTE", lambda: MT.USD_NOTE),
        ("musique : notes lyria3 durée + graine", lambda: (MS.preparer({"model": "lyria3", "prompt": "x", "duration_s": 12, "seed": 3})["notes"])),
        ("musique : notes lyria-3.5 paroles", lambda: (MS.preparer({"model": "lyria-3.5", "prompt": "x", "lyrics": "la", "duration_s": 12})["notes"])),
        ("musique : minimax-music-20 sans paroles", lambda: MS.preparer({"model": "minimax-music-20", "prompt": "x"})),
        ("musique : minimax-music-3 sans paroles", lambda: MS.preparer({"model": "minimax-music-3", "prompt": "x"})),
        ("musique : stable-audio-3 9999 s", lambda: MS.preparer({"model": "stable-audio-3", "prompt": "x", "duration_s": 9999})),
        ("musique : sans description", lambda: MS.preparer({"model": "lyria3", "prompt": ""})),
        ("SX.duree_sfx('mirelo-1.6', 'abc')", lambda: SX.duree_sfx("mirelo-1.6", "abc")),
        ("SX.entree_sfx('sonilo-video', SX.SFX_TEXTE)", lambda: SX.entree_sfx("sonilo-video", SX.SFX_TEXTE)),
        ("SX.build_request('hunyuan-foley', video_url='u', prompt='')", lambda: SX.build_request("hunyuan-foley", video_url="u", prompt="")),
        ("DT.sujet_de('sam31-video', '')", lambda: DT.sujet_de("sam31-video", "")),
    ]
    ATTENDU_6B = {
        "VI.source_refusee('relight-h3', 'a.mp4', 30)": "Rééclairer (MiniMax H3) : la vidéo doit durer 15 s au plus (celle-ci : 30.0 s)",
        "VI.source_refusee('relight-h3', 'a.mp4', 0.5)": "Rééclairer (MiniMax H3) : 56 images au moins à 24 i/s, soit 2.33 s (celle-ci : 0.5 s)",
        "VI.source_refusee('retoucher-flux3', 'a.mp4', 20)": "Modifier par une phrase (rapide) : la vidéo doit durer moins de 15 s (celle-ci : 20.0 s)",
        "VI.source_refusee('retoucher-flux3', 'a.mp4', 5, None, None, 60_000_000)": "Modifier par une phrase (rapide) : moins de 50 Mo (celle-ci : 60.0 Mo)",
        "VI.source_refusee('retoucher-kling', 'a.mp4', 5, None, None, 300_000_000)": "Modifier par une phrase (Kling O3) : 200 Mo au plus (celle-ci : 300.0 Mo)",
        "VI.source_refusee('retoucher-kling', 'a.mp4', 5, None, (100, 5000))": "Modifier par une phrase (Kling O3) : côtés de 720 à 3840 px exigés (celle-ci : 100x5000)",
        "VI.source_refusee('effacer-perso', 'a.mp4', 7.9, {'resolution': '720p'})": "Effacer un personnage (plaque propre) : en 720p, 145 images au plus à 24 i/s (≈ 6 s, budget du modèle) — celle-ci en demande 190 (7.9 s) : passez en 480p ou coupez le plan",
        "VI.source_refusee('effacer-perso', 'a.mp4', 30, {'resolution': '480p'})": "Effacer un personnage (plaque propre) : 481 images au plus à 24 i/s, soit 20.0 s (celle-ci : 30.0 s) — coupez le plan d'abord",
        "VI.source_refusee('effacer-perso', 'a.mp4', 100, {'resolution': '480p'})": "Effacer un personnage (plaque propre) : 481 images au plus à 24 i/s, soit 20.0 s (celle-ci : 100.0 s) — coupez le plan d'abord",
        "VI.source_refusee('effets-pixverse', 'a.mp4', 3)": "Effet prêt à l'emploi (PixVerse) part d'une image (.png, .jpg, .jpeg, .webp)",
        "VI.options_valides('effets-pixverse', {'duration': '10', 'resolution': '1080p'})": "!Effet prêt à l'emploi (PixVerse) : l'option « effect » est requise",
        "VI.options_valides('recadrer', {'inconnue': 1})": "!Changer le format (9:16 ↔ 16:9) : option inconnue inconnue (permises : aspect_ratio, resolution)",
        "VI.options_valides('agrandir', {'upscale_factor': 'abc'})": "!Agrandir / netteté (Topaz) : upscale_factor attend un nombre",
        "VI.options_valides('agrandir', {'upscale_factor': 99})": "!Agrandir / netteté (Topaz) : upscale_factor doit valoir de 1 à 4 (reçu 99)",
        "VI.prompt_valide('retoucher-flux3', 'x' * 2000)": "!Modifier par une phrase (rapide) : description trop longue (2000 caractères, 1500 au plus)",
        "devis vfx effacer-objet": "Effacer un objet nommé (passe 2 + masque SAM 3)",
        "devis vfx inserer-h3": "Insérer une scène (MiniMax H3) (scène générée 5 s · 768p) — jetons de référence au-delà de 4 096 non chiffrés (0,02 $ / 1 000)",
        "devis vfx agrandir": "Agrandir / netteté (Topaz) (25 s -> 3 x 10 s · sortie 4k)",
        "devis sfx mirelo-1.6": "Mirelo SFX 1.6 — prix à mesurer x2",
        "devis sfx kling-v2a": "Kling vidéo → son x1",
        "devis détourage sam3-sujet x3": "SAM 3 — garder un sujet nommé x3",
        "devis détourage birefnet-v2-video 95 images": "BiRefNet v2 vidéo — prix à mesurer",
        "devis détourage local-rembg": "rembg (local, gratuit)",
        "devis matte BiRefNet": "Détourage vidéo (BiRefNet) — prix à mesurer",
        "devis objets3d": "SAM 3 — objets 3D x2 — unité fal à confirmer au premier tir",
        "devis musique ace-step": "Musique (ACE-Step (paroles)) 45 s x2",
        "devis musique elevenlabs-music-2.5": "Musique (ElevenLabs Music 2.5) 90 s = 2 min x1",
        "devis musique mureka-9.5 paroles": "Musique (Mureka 9.5 avec paroles) x1",
        "devis musique lyria-3.5": "Musique (Lyria 3.5 (Google)) — prix à mesurer x1",
        "MT.note_prix('pixelcut-video')": "",
        "MT.USD_NOTE": "prix à mesurer : fal n'affiche que « $0 per compute second » (06/10/2026) — lire le montant sur le tableau de bord fal après ce tir, puis l'écrire dans pricing.birefnet_video_usd_per_s",
        "musique : notes lyria3 durée + graine": "Lyria 3 (Google) impose sa durée (30 s) — la durée demandée a été ignorée. | Lyria 3 (Google) n'accepte pas de graine — le résultat n'est pas reproductible.",
        "musique : notes lyria-3.5 paroles": "Lyria 3.5 (Google) impose sa durée — la durée demandée a été ignorée. | Lyria 3.5 (Google) ne prend pas de paroles — le texte saisi a été ignoré.",
        "musique : minimax-music-20 sans paroles": "!MiniMax Music 2.0 exige des paroles (10 à 3000 caractères).",
        "musique : minimax-music-3 sans paroles": "!MiniMax Music 3 exige des paroles (10 caractères au moins, balises non comptées).",
        "musique : stable-audio-3 9999 s": "!duration_s doit être entre 1 et 380 s pour Stable Audio 3.",
        "musique : sans description": "!Décris la musique voulue, ou choisis une ambiance.",
        "SX.duree_sfx('mirelo-1.6', 'abc')": "!durée invalide (un nombre de secondes, ou rien pour la durée du modèle)",
        "SX.entree_sfx('sonilo-video', SX.SFX_TEXTE)": "!Sonilo 1.1 (vidéo) ne part pas d'une description (connus : elevenlabs-direct, elevenlabs-v2-fal, sonilo-1.1, mirelo-1.6, stable-audio-3-sfx)",
        "SX.build_request('hunyuan-foley', video_url='u', prompt='')": "!Hunyuan Video Foley : décrivez le son voulu : ce modèle exige une description (« prompt » vide)",
        "DT.sujet_de('sam31-video', '')": "!SAM 3.1 — suivre un sujet nommé : dites quel sujet garder : ce modèle détoure un sujet NOMMÉ (« sujet » vide)",
    }
    rendu_fr, rendu_en = {}, {}
    for nom, f in CAS_6B:
        try:
            r = f()
            obj = r
            if isinstance(r, list):                       # les notes de la carte Musique : une ligne par note
                rendu_fr[nom] = " | ".join(map(str, r))
                rendu_en[nom] = " | ".join(I.texte(x, "en") for x in r)
                continue
            rendu_fr[nom] = str(r) if r is not None and not isinstance(r, dict) else ("<dict>" if isinstance(r, dict) else None)
        except Exception as e:  # noqa: BLE001
            obj = getattr(e, "message", e)
            rendu_fr[nom] = "!" + str(obj)
        rendu_en[nom] = None if obj is None or isinstance(obj, dict) else I.texte(obj, "en")
    ecarts = {k: (rendu_fr.get(k), v) for k, v in ATTENDU_6B.items() if rendu_fr.get(k) != v}
    check(f"6b table figée ({len(ATTENDU_6B)} appels : bornes, poids, images, durées, devis VFX / bruitage / détourage / "
          "matte / SAM 3 / musique, notes et refus Musique, bruitages) : le français d'avant, à l'octet",
          len(ATTENDU_6B) >= 40 and not ecarts, ecarts)
    restes = {k: v for k, v in rendu_en.items() if v and ACCENTS.search(v.replace("→", "").replace("↔", ""))}
    check("6b' les mêmes appels en anglais (texte(…, 'en')) : aucun accent français", not restes, restes)

    # _detourage_controles sans `nommer` : le nom traduit AVANT d'être tronqué (un Nom coupé perdait son id)
    from fastapi import HTTPException
    from app.api import routes as R

    class _Req:
        def __init__(self, lang):
            self.headers = {"accept-language": lang}

    def refus_controle(lang):
        try:
            R._detourage_controles("local-rembg", DT.VIDEO, None, _Req(lang))
        except HTTPException as e:
            return e.detail
        return None
    d_en, d_fr = refus_controle("en"), refus_controle("fr")
    check("6i _detourage_controles('local-rembg', VIDEO) en anglais : nom anglais, aucun français",
          bool(d_en) and "rembg (local, free)" in d_en and not ACCENTS.search(d_en), d_en)
    try:
        DT.entree("local-rembg", DT.VIDEO)
        avant = None
    except ValueError as e:
        avant = str(e)
    check("6j … et en français, le message d'avant (le ValueError du registre), à l'octet", d_fr == avant, (d_fr, avant))

    # /audio/music sans FAL_KEY : le 503 nomme le modèle par ia.nom.<id> (la route elle-même, pas seulement msg)
    import asyncio
    from app.config import settings as _S

    class _ReqJson(_Req):
        def __init__(self, lang, corps):
            super().__init__(lang)
            self._corps = corps

        async def json(self):
            return self._corps

    def refus_musique(lang):
        garde = _S.FAL_KEY
        _S.FAL_KEY = ""
        try:
            asyncio.run(R.generate_music_audio(_ReqJson(lang, {"model": "ace-step", "prompt": "x"})))
        except HTTPException as e:
            return e.status_code, e.detail
        finally:
            _S.FAL_KEY = garde
        return None, None
    c_en, m_en = refus_musique("en")
    c_fr, m_fr = refus_musique("fr")
    check("6k /audio/music sans FAL_KEY, en anglais : 503 qui nomme « ACE-Step (lyrics) », aucun accent",
          c_en == 503 and "ACE-Step (lyrics)" in (m_en or "") and not ACCENTS.search(m_en or ""), (c_en, m_en))
    check("6l … et en français : le message d'avant, à l'octet",
          c_fr == 503 and m_fr == "FAL_KEY non configurée (Réglages) pour ACE-Step (paroles) — rien n'a été lancé.", (c_fr, m_fr))
    libelles = [v["label"] for v in MS.MUSIC_MODELS.values()]
    check("6m les libellés des modèles de musique sont uniques (music_service._nom retrouve l'id par le libellé)",
          len(libelles) == len(set(libelles)) and all(MS._nom(v).mid == k for k, v in MS.MUSIC_MODELS.items()), libelles)
    ens = [I.texte(x, "en") for x in exemples]
    check("6c en anglais : aucun accent français, le nom du modèle traduit (ia.nom.<id>)",
          all(not ACCENTS.search(t.replace("→", "")) for t in ens) and "Kling video → sound" in ens[3]
          and "Insert a scene (MiniMax H3)" in ens[0] and ens[4] == "Edit with a sentence (Kling O3) only accepts .mp4, .mov (.avi video)", ens)
    lab = I.msg("ia.cle.absente_tir", "en", nom_cle="FAL_KEY", modele=I.Nom("relight-h3", VI.REGISTRE["relight-h3"]["label"]))
    check("6d un refus « clé absente » nomme le geste en anglais (Nom -> ia.nom.relight-h3)",
          lab == "FAL_KEY is not configured (Settings) for Relight (MiniMax H3) — nothing was started.", lab)
    from app.services import pricing as PR
    lig = PR.estimate(VI.op_vfx("effacer-objet", 4.0, {"enable_pass2_refinement": True, "mask_prompt": "chat"}))["breakdown"][0]["label"]
    check("6e la ligne de devis d'un VFX IA : français d'avant, anglais par texte()",
          str(lig).startswith("Effacer un objet nommé (passe 2 + masque SAM 3)")
          and I.texte(lig, "en").startswith("Erase a named object (pass 2 + SAM 3 mask)"), (str(lig), I.texte(lig, "en")))
    from app.i18n import catalogues as CAT
    en_cat = CAT.musique(cat, "en")
    check("6f catalogue Musique : copie traduite en anglais, la table source intacte, le français rendu tel quel",
          CAT.musique(cat, "fr") is cat and en_cat is not cat and all(not ACCENTS.search(m["desc"]) for m in en_cat["models"])
          and cat["moods"][0]["name"] == "Cinématique" and en_cat["moods"][0]["name"] == "Cinematic"
          and en_cat["moods"][0]["prompt"] == cat["moods"][0]["prompt"], [m["desc"][:30] for m in en_cat["models"]][:3])

    if not NODE:
        check("6g node disponible pour le banc DzModelesIA", False, "node absent")
    else:
        js = r"""
const fs = require("fs");
const dico = JSON.parse(process.argv[2]);
globalThis.window = globalThis;
function charger() { delete globalThis.DzModelesIA; eval(fs.readFileSync(process.argv[1], "utf8")); return globalThis.DzModelesIA; }
const M1 = charger();                                     // sans dzT : le français
const fr = { voie: M1.grouper([{ id: "x", voie: "fal" }])[0].titre, prix: M1.prix(0), texte: M1.texte({ id: "sam3-sujet", label: "SAM 3 — garder un sujet nommé", voie: "fal", usd: 0, dispo: false, cle: "FAL_KEY" }) };
globalThis.DZ_I18N = dico;
globalThis.dzT = (k, v) => { const e = dico[k]; if (!e) return k; let t = e.en; for (const x in (v || {})) t = t.split("{" + x + "}").join(v[x]); return t; };
const M2 = charger();
const en = { voie: M2.grouper([{ id: "x", voie: "fal" }])[0].titre, prix: M2.prix(0), texte: M2.texte({ id: "sam3-sujet", label: "SAM 3 — garder un sujet nommé", voie: "fal", usd: 0, dispo: false, cle: "FAL_KEY" }) };
console.log(JSON.stringify({ fr, en }));
"""
        sous = {k: D[k] for k in D if k.startswith(("ia.", "detour."))}
        p = subprocess.run([NODE, "-e", js, str(FRONT / "shared" / "dz-modeles-ia.js"), json.dumps(sous, ensure_ascii=False)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            r = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            r = {}
        check("6g DzModelesIA sous node SANS dzT : le français (repli)",
              r.get("fr") == {"voie": "via la clé fal", "prix": "prix à mesurer",
                              "texte": "SAM 3 — garder un sujet nommé · prix à mesurer · clé FAL_KEY à ajouter dans Réglages"},
              (r, p.stderr[-300:]))
        check("6h DzModelesIA avec un dzT anglais : voie, prix, nom du modèle et mention de clé en anglais",
              r.get("en") == {"voie": "with the fal key", "prix": "price to be measured",
                              "texte": "SAM 3 — keep a named subject · price to be measured · add the FAL_KEY key in Settings"},
              r.get("en"))

    print(f"\n{ok} ok, {fail} fail")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
