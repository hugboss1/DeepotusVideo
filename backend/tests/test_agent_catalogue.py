# -*- coding: utf-8 -*-
"""C1 (spec 2026-10-19-agent-catalogue-design.md) — le catalogue des éléments de l'assistant : extraction depuis le
code (dépôt factice en tmp_path), fusion sans écraser le rédigé, --check, et l'intégrité du vrai catalogue.
Run : & $PY tests/test_agent_catalogue.py   (depuis backend/)"""
import json, pathlib, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "agent"))
sys.path.insert(0, str(RACINE / "backend"))
import catalogue_sources as S                                              # noqa: E402

BUNDLE = ('r.jsx("button",{className:"x",title:dzT("montage.outils.lame_titre"),icon:"dz-action-couper",'
          'children:dzT("montage.outils.lame")});r.jsx(K,{title:dzT("coque.rail.replier")});'
          'r.jsx("button",{onClick:f,title:"Lecture (Espace)"});r.jsx("button",{children:dzT("montage.outils.vide")})')

# un élément par cas : chaque morceau est un piège mesuré sur le vrai bundle (relecture du 19/10)
CAS = {
    "voisin": 'r.jsx("button",{children:busy?"…":dzT("a.b.ok")}),r.jsx(O,{label:dzT("a.b.champ")})',
    "maison": 'r.jsx(K,{variant:"x",onClick:f,children:dzT("a.b.lancer")})',
    "span": 'r.jsx("span",{title:dzT("a.b.duree")})',
    "champ": 'r.jsx("input",{placeholder:dzT("a.b.cherche"),value:v})',
    "doublon": 'r.jsx("button",{title:dzT("a.b.fermer_aide"),"aria-label":dzT("a.b.fermer_aria"),children:"×"})',
    "imbrique": 'r.jsx("button",{style:{a:{b:1}},onClick:f,children:dzT("a.b.x")}),r.jsx(K,{title:dzT("a.b.voisin")})',
    "accolade": 'r.jsx("button",{title:"a } b",onClick:f,children:dzT("a.b.y")}),r.jsx(K,{title:dzT("a.b.z")})',
    "message": 'r.jsx("button",{children:dzT("a.b.montage_vide")})',
    "glyphe": 'r.jsxs("button",{onClick:f,children:[__dzGlT("dz-action-favori",dzT("a.b.favori")),'
              'r.jsx("button",{onClick:g,children:dzT("a.b.interne")})]})',
    "champ_maison": 'r.jsx(le,{placeholder:dzT("a.b.filtre"),value:v,onChange:g})',
    "parametre": 'r.jsx("button",{onClick:f,title:dzT("a.b.param_aide",{k:x("y")}),children:dzT("a.b.param",{n:k})})',
    "commentaire": 'r.jsx("button",{onClick:f,/* l\'outil } */style:{a:1},// c\'est {\nchildren:dzT("a.b.com")}),'
                   'r.jsx(K,{title:dzT("a.b.com_voisin")})',
    "repos": 'r.jsx("button",{onClick:f,children:busy?dzT("a.b.envoi"):dzT("a.b.envoyer")})',
    "points_hors_ternaire": 'r.jsx("button",{onClick:f,children:dzT("a.b.parcourir")})',
    "icone_repos": 'r.jsx(K,{onClick:f,icon:j?"dz-etat-attente":"dz-action-generer",children:dzT("a.b.gen")})',
    "noeud": 'r.jsx(K,{onClick:f,title:dzT("avatar.noeud.visage")})',
    "deux_fois": 'r.jsx("button",{onClick:f,title:dzT("a.b.lancer_aide"),children:dzT("a.b.lancer")})',
}
CLES_A = {k: {"fr": k.rsplit(".", 1)[-1], "en": k.rsplit(".", 1)[-1].upper()} for k in (
    "a.b.ok", "a.b.champ", "a.b.lancer", "a.b.lancer_aide", "a.b.duree", "a.b.cherche", "a.b.fermer_aide", "a.b.fermer_aria", "a.b.x",
    "a.b.voisin", "a.b.y", "a.b.z", "a.b.montage_vide", "a.b.favori", "a.b.interne", "a.b.gen", "a.b.com", "a.b.com_voisin", "a.b.param", "a.b.param_aide", "a.b.filtre", "avatar.noeud.visage")}

CLES_A.update({"a.b.envoi": {"fr": "Envoi…", "en": "Sending…"}, "a.b.envoyer": {"fr": "Envoyer", "en": "Send"},
               "a.b.parcourir": {"fr": "Parcourir...", "en": "Browse..."}})


def _ecrire(p: pathlib.Path, txt: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


def _depot(tmp_path, bundle):
    i18n = tmp_path / "frontend" / "shared" / "i18n"
    _ecrire(i18n / "montage.json", json.dumps({
        "montage.outils.lame": {"fr": "lame", "en": "blade"},
        "montage.outils.lame_titre": {"fr": "couper le clip", "en": "split the clip"},
        "montage.outils.vide": {"fr": "rien", "en": "nothing"}}, ensure_ascii=False))
    _ecrire(i18n / "coque.json", json.dumps({"coque.rail.replier": {"fr": "Replier", "en": "Collapse"},
                                             "commun.lit.lecture": {"fr": "Lecture (Espace)", "en": "Play (Space)"}}))
    _ecrire(i18n / "a.json", json.dumps(CLES_A, ensure_ascii=False))
    _ecrire(i18n / "vectorlab.json", json.dumps({"vectorlab.core.grille_titre": {"fr": "Grille", "en": "Grid"},
                                                 "vectorlab.calques.renommer_titre": {"fr": "Renommer", "en": "Rename"},
                                                 "vectorlab.pixel.teinte": {"fr": "Teinte", "en": "Hue"},
                                                 "vectorlab.pixel.remplir_titre": {"fr": "Remplir", "en": "Fill"},
                                                 "vectorlab.pixel.vlt_aide": {"fr": "Aide", "en": "Help"},
                                                 "vectorlab.pixel.boite_titre": {"fr": "Boîte", "en": "Box"}}))
    _ecrire(i18n / "photolab.json", json.dumps({"photolab.outil.pinceau": {"fr": "Pinceau", "en": "Brush"},
                                                "photolab.masquer.titre": {"fr": "Masquer", "en": "Mask"}}))
    _ecrire(i18n / "avatar.json", json.dumps({"avatar.direct.lancer": {"fr": "Lancer le direct", "en": "Start live"}}))
    _ecrire(tmp_path / "frontend" / "dist" / "assets" / "index-TEST.js", bundle)
    _ecrire(tmp_path / "frontend" / "vectorlab" / "js" / "core.js", 'b.title = T("vectorlab.core.grille_titre");\n'
            'const n = await VL.dialogue.saisir({ titre: T("vectorlab.calques.renommer_titre") });')
    _ecrire(tmp_path / "frontend" / "vectorlab" / "js" / "mod-pixelui.js", "\n".join([
        'p.innerHTML = `<div class="ap-ligne"><input type="number" id="pxH" min="-180" title="${T("vectorlab.pixel.teinte")}"/>',
        '  <button id="pxRemplir" ${o ? "" : "disabled"} title="${T("vectorlab.pixel.remplir_titre")}">OK</button></div>`;',
        'b.title = vlT("vectorlab.pixel.vlt_aide");',
        'await ouvrirDialogue(PL, {',
        '  titre: T("vectorlab.pixel.boite_titre"), classe: "large",',
        '});']))
    _ecrire(tmp_path / "frontend" / "vectorlab" / "index.html", "<html></html>")
    _ecrire(tmp_path / "frontend" / "photolab" / "index.html", "<html></html>")
    _ecrire(tmp_path / "frontend" / "photolab" / "js" / "mod-masquer.js",
            'const coq = coquilleReglage(PL, {' + chr(10) + '  titre: T("photolab.masquer.titre"), classe: "pl-masquer",' + chr(10) + '});')
    _ecrire(tmp_path / "frontend" / "avatar" / "avatar.js",
            'el("button", { type: "button", title: T("avatar.direct.lancer"), onclick: go });')
    _ecrire(tmp_path / "frontend" / "vectorlab" / "aide" / "index.json", json.dumps(
        [{"id": "plume", "titre": "Plume", "phrase": "Trace des courbes.", "titre_en": "Pen", "phrase_en": "Draws curves."}]))
    _ecrire(tmp_path / "backend" / "app" / "api" / "settings_routes.py",
            '_INDEX_FIXE = [\n    ("keys", "Clés API", "clé api jeton"),\n]\n')
    return tmp_path


@pytest.fixture
def depot(tmp_path):
    return _depot(tmp_path, BUNDLE)


@pytest.fixture
def cas(tmp_path):
    return S.extraire(_depot(tmp_path, ";".join(CAS.values())))


def test_bundle_bouton_complet(depot):
    e = S.extraire(depot)
    x = e["montage.outils.lame"]
    assert x["type"] == "bouton" and x["ecran"] == "montage" and x["cadre"] is None
    assert x["libelle"] == {"fr": "lame", "en": "blade"}
    assert x["infobulle"] == {"fr": "couper le clip", "en": "split the clip"}
    assert x["icone"] == "dz-action-couper"
    assert set(x["sources"]) == {"i18n:montage.outils.lame", "i18n:montage.outils.lame_titre"}


def test_bundle_infobulle_seule_et_litteral(depot):
    e = S.extraire(depot)
    r = e["coque.rail.replier"]
    assert r["ecran"] == "commun" and r["libelle"] == {"fr": "", "en": ""} and r["infobulle"]["en"] == "Collapse"
    lit = [x for x in e.values() if x["id"].startswith("lit.")]
    assert len(lit) == 1 and lit[0]["infobulle"] == {"fr": "Lecture (Espace)", "en": "Play (Space)"}
    assert lit[0]["ecran"] == "commun"
    assert lit[0]["id"] == "lit." + S._sha8("commun" + "Lecture (Espace)")


def test_messages_ecartes(depot):
    assert "montage.outils.vide" not in S.extraire(depot)      # rôle « vide » = un message, pas un élément


def test_ternaire_et_voisin(cas):
    assert cas["a.b.ok"]["libelle"]["fr"] == "ok" and cas["a.b.ok"]["infobulle"] is None
    assert "a.b.champ" not in cas                              # le champ d'un composant sans clic n'est pas retenu
    assert all("a.b.champ" not in str(x["sources"]) for x in cas.values())


def test_bouton_maison(tmp_path):                          # seul : la fiche ne peut venir que du composant
    x = S.extraire(_depot(tmp_path, CAS["maison"]))["a.b.lancer"]
    assert x["type"] == "bouton" and x["libelle"]["en"] == "LANCER"


def test_non_cliquable_exclu(tmp_path):
    assert "a.b.duree" not in S.extraire(_depot(tmp_path, CAS["span"]))


def test_champ(cas):
    x = cas["a.b.cherche"]
    assert x["type"] == "champ" and x["infobulle"]["fr"] == "cherche" and x["libelle"] == {"fr": "", "en": ""}


def test_champ_maison(cas):
    assert cas["a.b.filtre"]["type"] == "champ" and cas["a.b.filtre"]["infobulle"]["fr"] == "filtre"


def test_cle_avec_parametres(cas):
    assert cas["a.b.param"]["infobulle"]["fr"] == "param_aide"   # dzT("cle",{n:…}) se lit comme dzT("cle")


def test_commentaires_sautes(cas):
    assert cas["a.b.com"]["infobulle"] is None and cas["a.b.com_voisin"]["infobulle"]["fr"] == "com_voisin"


def test_ternaire_branche_au_repos(cas):
    assert "a.b.envoi" not in cas and cas["a.b.envoyer"]["libelle"]["fr"] == "Envoyer"
    assert cas["a.b.parcourir"]["libelle"]["fr"] == "Parcourir..."   # « … » hors ternaire : un vrai bouton


def test_icone_au_repos(cas):
    assert cas["a.b.gen"]["icone"] == "dz-action-generer"     # icon:j?"dz-etat-…":"dz-B" → l'icône au repos


def test_doublon_un_element_une_fiche(cas):
    assert "a.b.fermer_aide" in cas and "a.b.fermer_aria" not in cas


def test_props_imbriquees(cas):
    assert cas["a.b.x"]["infobulle"] is None and "a.b.voisin" in cas


def test_chaine_avec_accolade(cas):
    assert cas["a.b.y"]["infobulle"] is None and cas["a.b.z"]["infobulle"]["fr"] == "z"


def test_message_par_suffixe(cas):
    assert "a.b.montage_vide" not in cas
    assert S.message("montage.projets.montage_vide") and S.message("coque.accueil.etape_pret")
    assert S.message("studio.motion.code_en_cours")             # rôle en plusieurs morceaux
    assert not S.message("a.b.fermer_aide") and not S.message("montage.outils.lame_titre")


def test_glyphe_et_bouton_interne(cas):
    assert cas["a.b.favori"]["icone"] == "dz-action-favori"   # libellé lu dans __dzGlT(icône, dzT(…))
    assert "a.b.interne" in cas                                # le bouton imbriqué a sa propre fiche


def test_meme_cle_deux_elements(cas):
    x = cas["a.b.lancer"]                                      # 1er élément gardé, la source du 2e ajoutée
    assert x["infobulle"] is None and "i18n:a.b.lancer_aide" in x["sources"]
    assert x["sources"].count("i18n:a.b.lancer") == 1


def test_noeuds_avatar_au_studio(cas):
    assert cas["avatar.noeud.visage"]["ecran"] == "studio"


def test_litteraux(tmp_path):
    moyen, trop = "x" * 150, "y" * 250
    b = ('r.jsx("button",{onClick:f,children:dzT("a.b.ok")});r.jsx("button",{onClick:f,title:"Inconnu ici"});'
         'r.jsx("button",{onClick:f,title:"' + moyen + '"});r.jsx("button",{onClick:f,title:"' + trop + '"});'
         'r.jsx("span",{title:"Pas un bouton"});r.jsx("button",{onClick:f,title:"12"})')
    e = S.extraire(_depot(tmp_path, b))
    lit = {x["infobulle"]["fr"]: x for x in e.values() if x["id"].startswith("lit.")}
    assert set(lit) == {"Inconnu ici", moyen}                  # ≤ 200 caractères, une lettre, élément retenu
    x = lit["Inconnu ici"]
    assert x["ecran"] == S.ecran("a.b.ok") and x["infobulle"]["en"] == ""   # pas de traduction : vide, jamais le FR
    assert x["id"] == "lit." + S._sha8(x["ecran"] + "Inconnu ici")


def test_litteral_ecran_de_la_cle_proche(tmp_path):
    b = 'r.jsx("button",{onClick:f,children:dzT("montage.outils.lame")});r.jsx("button",{onClick:f,title:"Zoom"})'
    lit = [x for x in S.extraire(_depot(tmp_path, b)).values() if x["id"].startswith("lit.")]
    assert len(lit) == 1 and lit[0]["ecran"] == "montage"


def test_labs(depot):
    e = S.extraire(depot)
    g = e["vectorlab.core.grille_titre"]
    assert g["ecran"] == "vectorlab" and g["cadre"] == "/vectorlab/" and g["infobulle"]["en"] == "Grid"
    assert "frontend/vectorlab/js/core.js" in g["sources"]
    p = e["photolab.outil.pinceau"]
    assert p["type"] == "outil" and p["cadre"] == "/photolab/" and p["libelle"]["en"] == "Brush"


def test_avatar_live(depot):
    a = S.extraire(depot)["avatar.direct.lancer"]
    assert a["ecran"] == "avatarlive" and a["cadre"] == "/avatar/" and a["infobulle"]["en"] == "Start live"
    assert a["sources"] == ["frontend/avatar/avatar.js"]


def test_meme_cle_bundle_et_lab(tmp_path):
    b = 'r.jsx("button",{onClick:f,title:dzT("vectorlab.core.grille_titre")})'
    e = S.extraire(_depot(tmp_path, b))
    g = e["vectorlab.core.grille_titre"]                       # une seule fiche, sources fusionnées
    assert set(g["sources"]) == {"i18n:vectorlab.core.grille_titre", "frontend/vectorlab/js/core.js"}
    assert g["infobulle"]["en"] == "Grid" and g["cadre"] == "/vectorlab/"


def test_reglages_et_fiches(depot):
    e = S.extraire(depot)
    r = e["reglages.keys.cles-api"]
    assert r["type"] == "reglage" and r["ecran"] == "settings" and r["reglages"] == "keys"
    assert r["libelle"]["fr"] == "Clés API"
    f = e["vectorlab.fiche.plume"]
    assert f["fiche"] == "plume" and f["cadre"] == "/vectorlab/" and f["infobulle"]["en"] == "Draws curves."


def test_titre_de_dialogue_ecarte(depot):
    assert "vectorlab.calques.renommer_titre" not in S.extraire(depot)   # saisir({ titre: … }) : pas un élément


def test_exclusions_du_skill(depot):
    _ecrire(depot / "docs" / "agent" / "catalogue" / "_exclus.json", json.dumps(
        {"ids": ["coque.rail.replier"], "prefixes": ["reglages."], "note": "test"}))
    e = S.extraire(depot)
    assert "coque.rail.replier" not in e and not any(k.startswith("reglages.") for k in e)
    assert "montage.outils.lame" in e and "vectorlab.fiche.plume" in e


def test_gabarits_du_vectorlab(depot):
    e = S.extraire(depot)
    assert e["vectorlab.pixel.teinte"]["type"] == "champ"            # title="${T(…)}" porté par un <input>
    assert e["vectorlab.pixel.remplir_titre"]["type"] == "bouton"    # … par un <button>
    assert e["vectorlab.pixel.remplir_titre"]["infobulle"]["en"] == "Fill"
    assert e["vectorlab.pixel.vlt_aide"]["cadre"] == "/vectorlab/"   # vlT(…) comme T(…)


def test_dialogue_sur_deux_lignes(depot):
    assert "vectorlab.pixel.boite_titre" not in S.extraire(depot)    # ouvrirDialogue(PL, { puis titre: T(…)


def test_dialogue_coquille_reglage(depot):
    assert "photolab.masquer.titre" not in S.extraire(depot)         # coquilleReglage(PL, { puis titre: T(…)


# ── robustesse des sources (relecture du 19/10) ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("contenu", [
    "{pas du json",                                                   # JSON invalide
    '["coque.rail.replier"]',                                         # racine non objet
    '{"ids": [], "prefixes": "reglages."}',                           # une chaîne : un tuple de lettres effacerait tout
    '{"ids": "coque.rail.replier"}',
    '{"ids": [12], "prefixes": []}',                                  # éléments non chaînes
    '{"ids": [], "prefixes": [null]}',
])
def test_exclusions_mal_formees(depot, contenu):
    _ecrire(depot / "docs" / "agent" / "catalogue" / "_exclus.json", contenu)
    with pytest.raises(RuntimeError, match=r"docs/agent/catalogue/_exclus\.json illisible : "):
        S.extraire(depot)


def test_exclusions_absentes(depot):
    assert S._exclusions(depot) == (set(), ())


def test_index_fixe_annote(depot):
    _ecrire(depot / "backend" / "app" / "api" / "settings_routes.py",
            '_INDEX_FIXE: list = [\n    ("keys", "Clés API", "clé api jeton"),\n]\n')
    assert "reglages.keys.cles-api" in S.extraire(depot)


@pytest.mark.parametrize("source", [
    "AUTRE = []\n",                                                   # affectation introuvable
    "_INDEX_FIXE = construire()\n",                                   # valeur non littérale
    '_INDEX_FIXE = [("keys", "Clés API")]\n',                          # tuple de 2 éléments
])
def test_index_fixe_illisible(depot, source):
    _ecrire(depot / "backend" / "app" / "api" / "settings_routes.py", source)
    with pytest.raises(RuntimeError, match=r"settings_routes\.py.*_INDEX_FIXE"):
        S.extraire(depot)


def test_index_fixe_absent(depot):
    (depot / "backend" / "app" / "api" / "settings_routes.py").unlink()
    assert not any(k.startswith("reglages.") for k in S.extraire(depot))


def test_dialogue_ne_filtre_que_titre(depot):
    _ecrire(depot / "frontend" / "vectorlab" / "js" / "mod-dialogue.js", "\n".join([
        'h.innerHTML = `<h3>${spec.titre}</h3><button class="dialogue-x" title="${T("vectorlab.dialogue.fermer")}">×</button>`;',
        'const r = await saisir({',
        '  titre: T("vectorlab.dialogue.saisie_titre"),',
        '});']))
    i18n = depot / "frontend" / "shared" / "i18n" / "vectorlab.json"
    d = json.loads(i18n.read_text(encoding="utf-8"))
    d.update({"vectorlab.dialogue.fermer": {"fr": "Fermer", "en": "Close"},
              "vectorlab.dialogue.saisie_titre": {"fr": "Saisie", "en": "Input"}})
    i18n.write_text(json.dumps(d), encoding="utf-8")
    e = S.extraire(depot)
    assert e["vectorlab.dialogue.fermer"]["infobulle"]["en"] == "Close"     # title= jamais filtré par la règle
    assert "vectorlab.dialogue.saisie_titre" not in e                       # titre: après saisir( : écarté


def test_motif_de_dialogue_resserre():
    assert S.RE_DIALOGUE.search("VL.dialogue.saisir({") and S.RE_DIALOGUE.search("ouvrirDialogue(PL, {")
    assert S.RE_DIALOGUE.search("coquilleReglage(PL, {") and S.RE_DIALOGUE.search("{ valider: ok }")
    assert S.RE_DIALOGUE.search("return dialogueExport({")               # photolab mod-documents.js
    assert not S.RE_DIALOGUE.search("dialogues.forEach(x)") and not S.RE_DIALOGUE.search("ressaisir(x)")


@pytest.mark.parametrize("contenu", ["[{pas du json", '{"id": "plume"}'])
def test_fiches_illisibles(depot, contenu):
    _ecrire(depot / "frontend" / "vectorlab" / "aide" / "index.json", contenu)
    with pytest.raises(RuntimeError, match=r"frontend/vectorlab/aide/index\.json"):
        S.extraire(depot)


def test_fiche_incomplete_ignoree(depot):
    _ecrire(depot / "frontend" / "vectorlab" / "aide" / "index.json", json.dumps(
        [{"id": "plume", "titre": "Plume", "phrase": "Trace."}, {"id": "gomme", "titre": "Gomme"}, {"titre": "x"}]))
    e = S.extraire(depot)
    assert "vectorlab.fiche.plume" in e and "vectorlab.fiche.gomme" not in e
    assert S.IGNOREES == ["frontend/vectorlab/aide/index.json#gomme", "frontend/vectorlab/aide/index.json#2"]
    S.extraire(_depot(depot, BUNDLE))                                       # remise à zéro à chaque extraction
    assert S.IGNOREES == []


def test_pas_de_francais_dans_en(depot):
    _ecrire(depot / "frontend" / "vectorlab" / "aide" / "index.json", json.dumps(
        [{"id": "plume", "titre": "Plume", "phrase": "Trace des courbes."}]))
    e = S.extraire(depot)
    assert e["reglages.keys.cles-api"]["libelle"] == {"fr": "Clés API", "en": ""}   # aucune traduction connue
    f = e["vectorlab.fiche.plume"]
    assert f["libelle"]["en"] == "" and f["infobulle"]["en"] == ""


def test_bundle_unique(depot):
    _ecrire(depot / "frontend" / "dist" / "assets" / "index-AUTRE.js", BUNDLE)
    with pytest.raises(RuntimeError, match="index-"):
        S.extraire(depot)


def test_bundle_absent(depot):
    (depot / "frontend" / "dist" / "assets" / "index-TEST.js").unlink()
    assert S._bundle(depot) == "" and "vectorlab.core.grille_titre" in S.extraire(depot)


def test_outil_photolab_garde_son_infobulle(depot):
    _ecrire(depot / "frontend" / "photolab" / "js" / "outils.js", 'b.title = T("photolab.outil.pinceau");')
    p = S.extraire(depot)["photolab.outil.pinceau"]
    assert p["infobulle"] == {"fr": "Pinceau", "en": "Brush"}
    assert set(p["sources"]) == {"i18n:photolab.outil.pinceau", "frontend/photolab/js/outils.js"}


# tiroir Sons (sfxstudio.js) : l'infobulle au repos est un PARAMÈTRE de la fabrique du bouton, la clé est à l'appel
FABRIQUE = ('function actBtn(it,act,lbl,tt){var armed=q;return r.jsx("button",{className:"svx-abtn",'
            'title:armed?dzT("a.b.armee",{prix:p}):tt,"aria-label":tt+" : "+it.name,'
            'onClick:function(e){go(it,act)},children:armed?[p]:lbl},act)}'
            'r.jsxs("div",{children:[k==="m"?actBtn(it,"stems",__dzGl("dz-media-stems"),dzT("a.b.stems_aide")):null,'
            'actBtn(it,"iso",__dzGl("dz-media-isoler-voix"),dzT("a.b.iso_aide"))]})')
CLES_A.update({k: {"fr": k.rsplit(".", 1)[-1], "en": k.rsplit(".", 1)[-1].upper()}
               for k in ("a.b.armee", "a.b.stems_aide", "a.b.iso_aide", "a.b.local_aide")})


def test_infobulle_en_parametre_suivie_aux_appels(tmp_path):
    e = S.extraire(_depot(tmp_path, FABRIQUE))
    s = e["a.b.stems_aide"]
    assert s["type"] == "bouton" and s["infobulle"] == {"fr": "stems_aide", "en": "STEMS_AIDE"}
    assert s["icone"] == "dz-media-stems" and s["sources"] == ["i18n:a.b.stems_aide"]
    assert e["a.b.iso_aide"]["icone"] == "dz-media-isoler-voix"
    assert "a.b.armee" in e                                   # le 2e clic garde sa fiche


def test_infobulle_variable_locale_non_suivie(tmp_path):
    b = ('function f(it,act){var tt=dzT("a.b.local_aide");return r.jsx("button",{onClick:g,title:o.it})}'
         'f(1,dzT("a.b.stems_aide"))')
    e = S.extraire(_depot(tmp_path, b))                       # o.it : une propriété, pas le paramètre « it »
    assert "a.b.stems_aide" not in e


# t279 : pages de Son & VFX (sonvfx-post.js) dont les textes passent par une TABLE — function txt(){return {go:dzT(…)}},
# var T=txt(), puis children:T.go — la clé n'est pas dans l'élément : l'extracteur suit la table dans sa portée
TABLE = 'function txt(){return {go:dzT("a.b.tgo"),aide:dzT("a.b.taide"),cache:dzT("a.b.tcache")}}'
CLES_A.update({k: {"fr": k.rsplit(".", 1)[-1], "en": k.rsplit(".", 1)[-1].upper()}
               for k in ("a.b.tgo", "a.b.taide", "a.b.tcache")})


def test_table_de_textes_suivie(tmp_path):
    b = TABLE + ('function Page(){var T=txt();function ligne(){return r.jsxs("div",{children:['
                 'r.jsx("button",{onClick:f,children:T.go}),r.jsx("button",{onClick:g,title:T.aide,children:"x"})]})}'
                 'return ligne()}')
    e = S.extraire(_depot(tmp_path, b))
    assert e["a.b.tgo"]["libelle"] == {"fr": "tgo", "en": "TGO"} and e["a.b.tgo"]["sources"] == ["i18n:a.b.tgo"]
    assert e["a.b.taide"]["infobulle"] == {"fr": "taide", "en": "TAIDE"} and e["a.b.taide"]["type"] == "bouton"


def test_table_hors_portee_ou_sans_affectation_non_suivie(tmp_path):
    b = TABLE + ('function A(){var T=txt();return 1}function B(){return r.jsx("button",{onClick:f,children:T.go})}'
                 'function C(){var T=autre();return r.jsx("button",{onClick:f,title:T.aide})}')
    e = S.extraire(_depot(tmp_path, b))
    assert "a.b.tgo" not in e and "a.b.taide" not in e


def test_table_dans_une_fabrique_branche_au_repos(tmp_path):
    b = TABLE + ('function Page(){var T=txt();function mini(k,tt){return r.jsx("button",{onClick:f,title:tt})}'
                 'return r.jsx("div",{children:[mini("m",x?T.aide:T.cache),mini("g",T.go)]})}')
    e = S.extraire(_depot(tmp_path, b))
    assert "a.b.tcache" in e and "a.b.taide" not in e and e["a.b.tgo"]["infobulle"]["fr"] == "tgo"


def test_table_et_cle_dans_l_ordre_du_texte(tmp_path):
    # !armé ? T.go : dzT(confirmer) — la branche au repos vient en premier, qu'elle soit une clé ou une table
    b = TABLE + 'function Page(){var T=txt();return r.jsx("button",{onClick:f,"aria-label":!a?T.go:dzT("a.b.taide")})}'
    e = S.extraire(_depot(tmp_path, b))
    assert "a.b.tgo" in e and "a.b.taide" not in e


def test_bouton_object_assign(tmp_path):
    # function mini(k,tt,props){return r.jsx("button",Object.assign({title:tt,…},props))} : l'objet littéral se lit
    b = TABLE + ('function Page(){var T=txt();function mini(k,tt,p){return r.jsx("button",Object.assign({type:"button",'
                 'title:tt,children:k},p),k)}return r.jsx("div",{children:[mini("m",T.cache,{onClick:f})]})}')
    e = S.extraire(_depot(tmp_path, b))
    assert e["a.b.tcache"]["infobulle"]["fr"] == "tcache"


def test_parametre_champ_et_libelle_non_suivis(tmp_path):
    b = ('function rng(k,label){return r.jsx("input",{type:"range","aria-label":label})}rng(1,dzT("a.b.stems_aide"));'
         'function row(label,kids){return r.jsx("button",{onClick:f,children:label})}row(dzT("a.b.iso_aide"),[])')
    e = S.extraire(_depot(tmp_path, b))
    assert "a.b.stems_aide" not in e and "a.b.iso_aide" not in e


def test_parametre_nom_minifie_dans_sa_portee(tmp_path):
    b = ('function A(){function e(t){return r.jsx("button",{onClick:f,title:t})}e(dzT("a.b.stems_aide"))}'
         'function B(){function e(t){return t}e(dzT("a.b.iso_aide"))}')
    e = S.extraire(_depot(tmp_path, b))                       # le « e » de B n'est pas celui de A
    assert "a.b.stems_aide" in e and "a.b.iso_aide" not in e


def test_parametre_branche_au_repos(tmp_path):
    b = ('function k(t){return r.jsx("button",{onClick:f,title:t})}k(busy?dzT("a.b.armee"):dzT("a.b.iso_aide"));'
         'k(dzT("coque.rail.replier"))')
    e = S.extraire(_depot(tmp_path, b))
    assert "a.b.iso_aide" in e and "a.b.armee" not in e
    assert "coque.rail.replier" in e                          # une clé d'écran est suivie…


def test_parametre_objet_et_sa_propriete(tmp_path):
    b = ('function dztBouton(o){return r.jsx("button",{onClick:o.fn,title:o.title||""})}'
         'dztBouton({fn:g,title:dzT("a.b.stems_aide")});'
         'function row(f,i){return r.jsx("button",{onClick:g,title:f.behind?dzT("a.b.armee"):x})}'
         'row(dzT("a.b.iso_aide"),1)')
    e = S.extraire(_depot(tmp_path, b))
    assert "a.b.stems_aide" in e                               # la propriété « title » de l'objet passé
    assert "a.b.iso_aide" not in e                             # f.behind : f est un objet, pas l'infobulle


def test_parametre_action_commune_ignoree(tmp_path):
    _ecrire(tmp_path / "frontend" / "shared" / "i18n" / "commun.json",
            json.dumps({"commun.action.fermer": {"fr": "Fermer", "en": "Close"}}))
    b = 'function k(t){return r.jsx("button",{onClick:f,title:t})}k(dzT("commun.action.fermer"))'
    assert "commun.action.fermer" not in S.extraire(_depot(tmp_path, b))   # …une action commune non


def test_lab_libelle_voisin_de_l_infobulle(depot):
    d = json.loads((depot / "frontend/shared/i18n/vectorlab.json").read_text(encoding="utf-8"))
    d.update({"vectorlab.persona.vecteur": {"fr": "Vecteur", "en": "Vector"},
              "vectorlab.persona.vecteur_titre": {"fr": "Dessin vectoriel", "en": "Vector drawing"},
              "vectorlab.persona.pixel_titre": {"fr": "Retouche au pixel", "en": "Pixel retouching"},
              "vectorlab.flyout.deposer": {"fr": "Déposer", "en": "Drop"},
              "vectorlab.flyout.titre_typo": {"fr": "Typo", "en": "Type"}})
    _ecrire(depot / "frontend/shared/i18n/vectorlab.json", json.dumps(d, ensure_ascii=False))
    _ecrire(depot / "frontend/vectorlab/js/mod-persona.js", "\n".join([
        '  { id: "vecteur", libelle: T("vectorlab.persona.vecteur"), titre: T("vectorlab.persona.vecteur_titre") },',
        '  { id: "pixel", libelle: "Pixel", icone: "dz-nav-espace-pixel", titre: T("vectorlab.persona.pixel_titre") },',
        '  return { titre: T("vectorlab.flyout.titre_typo"), entrees: [{ id: "d", libelle: T("vectorlab.flyout.deposer") }] };']))
    e = S.extraire(depot)
    assert e["vectorlab.persona.vecteur_titre"]["libelle"] == {"fr": "Vecteur", "en": "Vector"}
    assert e["vectorlab.persona.pixel_titre"]["libelle"]["fr"] == "Pixel"
    assert e["vectorlab.flyout.titre_typo"]["libelle"] == {"fr": "", "en": ""}   # le libellé d'un AUTRE objet


# panneau Actions du Photolab (mod-actions.js, t261) : boutons, cases, menu et dialogue bâtis par des fabriques du lab
ACTIONS_JS = "\n".join([
    'const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);',
    'PL.signaler(T("photolab.actions.lot_compte", { n }));',
    'const bouton = (icone, cle, fn, cls = "") => {',
    '  const b = el("button", "pr-btn " + cls); b.type = "button";',
    '  b.title = T(cle); b.setAttribute("aria-label", b.title); pied.appendChild(b); return b;',
    '};',
    'const bJouer = bouton("dz-media-lecture", "photolab.actions.jouer", () => jouer());',
    'const bRien = bouton("dz-x", variable, f);',
    'function caseAllumage(etat, aria, fn) {',
    '  const b = el("button", "ac-case " + etat); b.setAttribute("aria-label", aria); return b;',
    '}',
    'row.append(caseAllumage(a.allumage, T("photolab.actions.allumer_action"), () => go()));',
    'function champ(c, libelleCle, element) {',
    '  const l = el("label", "ac-champ"); l.append(el("span", null, T(libelleCle)), element); c.appendChild(l);',
    '}',
    'champ(tete, "photolab.actions.lot_format", sFmt);',
    'export function entreesMenu(e) {',
    '  const it = (id, cle, actif, x = {}) => ({ id, cle, actif: !!actif, ...x });',
    '  return [it("lot", "photolab.actions.menu.lot", e.n > 0), null];',
    '}',
    'function ouvrirMenu() { const l = el("div", "menu-ligne"); l.setAttribute("role", "menuitem");',
    '  l.appendChild(el("span", "menu-lib", T(it.cle))); }',
    'const bTout = el("button", "pl-bouton", T("photolab.actions.lot_tout")); bTout.type = "button";',
    'const p = el("p", "ac-aide", T("photolab.actions.lot_aide"));',
    'ouvrirDialogue(PL, { titre: T("photolab.actions.lot_titre"),',
    '  boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.actions.lot_lancer"), principal: true }] });',
    'const signaler = (cle) => PL.signaler(T(cle));',
    'signaler("photolab.actions.lot_compte");'])
CLES_ACTIONS = {k: {"fr": k.rsplit(".", 1)[-1], "en": k.rsplit(".", 1)[-1].upper()} for k in (
    "photolab.actions.jouer", "photolab.actions.allumer_action", "photolab.actions.lot_format", "photolab.actions.menu.lot",
    "photolab.actions.lot_tout", "photolab.actions.lot_aide", "photolab.actions.lot_titre", "photolab.actions.lot_lancer",
    "photolab.actions.lot_compte")}


def _actions(depot):
    i18n = depot / "frontend/shared/i18n"
    d = json.loads((i18n / "photolab.json").read_text(encoding="utf-8"))
    d.update(CLES_ACTIONS)
    _ecrire(i18n / "photolab.json", json.dumps(d, ensure_ascii=False))
    _ecrire(i18n / "commun.json", json.dumps({"commun.action.annuler": {"fr": "Annuler", "en": "Cancel"}}))
    _ecrire(depot / "frontend/photolab/js/mod-actions.js", ACTIONS_JS)
    return S.extraire(depot)


def test_lab_fabrique_cle_et_texte(depot):
    e = _actions(depot)
    j = e["photolab.actions.jouer"]                           # bouton(…, "cle", …) : title = T(cle)
    assert j["type"] == "bouton" and j["ecran"] == "photolab" and j["cadre"] == "/photolab/"
    assert j["infobulle"] == {"fr": "jouer", "en": "JOUER"} and j["icone"] == "dz-media-lecture"
    assert j["sources"] == ["frontend/photolab/js/mod-actions.js"]
    a = e["photolab.actions.allumer_action"]                  # caseAllumage(…, T("cle"), …) : aria-label = texte
    assert a["type"] == "bouton" and a["infobulle"]["en"] == "ALLUMER_ACTION"
    c = e["photolab.actions.lot_format"]                      # champ(…, "cle", contrôle) : libellé d'un champ
    assert c["type"] == "champ" and c["libelle"] == {"fr": "lot_format", "en": "LOT_FORMAT"} and c["infobulle"] is None


def test_lab_menu_bouton_et_dialogue(depot):
    e = _actions(depot)
    m = e["photolab.actions.menu.lot"]                        # entrée de menu rendue par T(it.cle) en menuitem
    assert m["type"] == "menu" and m["libelle"]["fr"] == "lot" and m["infobulle"] is None
    assert e["photolab.actions.lot_tout"]["type"] == "bouton"   # el("button", classe, T(cle))
    assert e["photolab.actions.lot_tout"]["libelle"]["en"] == "LOT_TOUT"
    assert e["photolab.actions.lot_lancer"]["type"] == "bouton"  # boutons: [{ libelle: T(cle) }] d'un dialogue
    for k in ("photolab.actions.lot_aide", "photolab.actions.lot_titre", "photolab.actions.lot_compte",
              "commun.action.annuler"):
        assert k not in e, k                                  # un paragraphe, un titre de boîte, un signal, l'action commune


def test_lab_menu_seulement_pres_du_menuitem(depot):
    js = ACTIONS_JS + "\n" + "\n".join(["// " + "x" * 900,
        'const aide = (id, texte) => ({ id, texte });',
        'aide("a", "photolab.actions.lot_compte");',
        'function bulle(o) { return el("p", null, T(o.texte)); }'])
    _actions(depot)
    _ecrire(depot / "frontend/photolab/js/mod-actions.js", js)
    e = S.extraire(depot)                                     # T(o.cle) loin de tout menuitem : pas une entrée de menu
    assert "photolab.actions.menu.lot" in e and "photolab.actions.lot_compte" not in e


def test_page_de_lab_texte_connu_dans_un_AUTRE_lab(depot):
    e = _page_vectorlab(depot)
    d = json.loads((depot / "frontend/shared/i18n/photolab.json").read_text(encoding="utf-8"))
    d["photolab.page.plume"] = {"fr": "Plume Bézier — clic = ancre (P)", "en": "x"}
    _ecrire(depot / "frontend/shared/i18n/photolab.json", json.dumps(d, ensure_ascii=False))
    _ecrire(depot / "frontend/photolab/js/plume.js", 'b.title = T("photolab.page.plume");')
    assert "vectorlab.page.outil_plume" in S.extraire(depot)   # même texte au Photolab : autre élément, fiche gardée


def _page_vectorlab(depot):
    i18n = depot / "frontend" / "shared" / "i18n"
    d = json.loads((i18n / "vectorlab.json").read_text(encoding="utf-8"))
    d.update({"vectorlab.page.outil_plume": {"fr": "Plume Bézier — clic = ancre (P)", "en": "Bézier Pen — click = anchor (P)"},
              "vectorlab.page.filtrer_role": {"fr": "Filtrer par rôle", "en": "Filter by role"},
              "vectorlab.page.cotes": {"fr": "Cotes", "en": "Dimensions"},
              "vectorlab.page.forme_titre": {"fr": "Forme & gestes", "en": "Shape & gestures"},
              "vectorlab.page.grille": {"fr": "Grille", "en": "Grid"}})
    _ecrire(i18n / "vectorlab.json", json.dumps(d, ensure_ascii=False))
    _ecrire(depot / "frontend" / "vectorlab" / "index.html", "\n".join([
        '<nav id="outils"><button data-outil="plume" title="Plume Bézier — clic = ancre (P)"></button></nav>',
        '<span title="Cotes"></span><select id="r" title="Filtrer par rôle"></select>',
        '<summary class="panneau-tete" title="Forme &amp; gestes">x</summary>',
        '<button id="g" title="Grille"></button><button title="Sans clé"></button>']))
    return S.extraire(depot)


def test_page_de_lab_titres_litteraux(depot):
    e = _page_vectorlab(depot)
    p = e["vectorlab.page.outil_plume"]
    assert p["type"] == "bouton" and p["ecran"] == "vectorlab" and p["cadre"] == "/vectorlab/"
    assert p["infobulle"]["en"] == "Bézier Pen — click = anchor (P)" and p["libelle"] == {"fr": "", "en": ""}
    assert p["sources"] == ["frontend/vectorlab/index.html"]
    assert e["vectorlab.page.filtrer_role"]["type"] == "champ"
    assert "vectorlab.page.cotes" not in e and "vectorlab.page.forme_titre" not in e    # span, en-tête de section
    assert not any(f["infobulle"] and f["infobulle"]["fr"] == "Sans clé" for f in e.values())


def test_page_de_lab_element_deja_connu(depot):
    e = _page_vectorlab(depot)                                # « Grille » : déjà vu par core.js sous une autre clé
    assert "vectorlab.page.grille" not in e and "vectorlab.core.grille_titre" in e


# t287 (24/10/2026) : les scripts PARTAGÉS en DOM nu (el("tag", {…}) de frontend/shared) — le composant de l'agent
# Campagnes en entier, et du tiroir F1 les seuls éléments de t285b (onglets, espace, passage de main)
CAMPAGNES_JS = "\n".join([
    'function el(tag, attrs, enfants) { var n = document.createElement(tag); n.textContent = attrs.texte; return n; }',
    'var champ = el("textarea", { rows: "2", "data-dz-camp": "champ" });',
    'var envoyer = el("button", { type: "button", "data-dz-camp": "envoyer" });',
    'var statut = el("div", { class: "s", role: "status" });',
    'function etat(texte, ton) { return el("div", { class: "dzCampEtat", texte: texte }); }',
    'function bouton(texte, surClic, primaire) {',
    '  var b = el("button", { type: "button", texte: texte });',
    '  b.addEventListener("click", surClic);',
    '  return b;',
    '}',
    'function carte() {',
    '  actions.appendChild(bouton(T("campagnes.action.valider"), function () { decider(n, "acceptee"); }, true));',
    '  actions.appendChild(bouton(S.rendus[n] ? T("campagnes.action.enregistrer") : T("campagnes.action.generer", { usd: usd(a.usd) }),',
    '    function () { genererDevis(n, b); }, true));',
    '  c.appendChild(etat(T("campagnes.etat.validee"), "ok"));',
    '  c.appendChild(el("div", { class: "dzCampCarteT", texte: T("campagnes.carte.porte", { n: 1 }) }));',
    '  var lien = el("a", { class: "dzCampLien", href: "#", texte: T("campagnes.action.ouvrir") });',
    '  statut.textContent = T("campagnes.erreur.reseau", { msg: "x" });',
    '}',
    'function dessinerPied() {',
    '  champ.setAttribute("placeholder", T(S.correction !== null ? "campagnes.champ.correction" : "campagnes.champ.placeholder"));',
    '  envoyer.textContent = T("campagnes.champ.envoyer");',
    '}',
])
AGENT_JS = "\n".join([
    'const btnEnvoyer = el("button", { texte: T("agent.tiroir.envoyer"), on: { click: () => envoyer() } });',
    'const ongletBouton = (nom, cle) => el("button", { type: "button", role: "tab", id: "dzAgentOnglet-" + nom,',
    '  "aria-selected": "false", texte: T(cle), on: { click: () => choisirOnglet(nom) } });',
    'const ongDemander = ongletBouton("demander", "agent.onglet.demander"), ongCampagnes = ongletBouton("campagnes", "agent.onglet.campagnes");',
    'const liste = el("div", { role: "tablist", "aria-label": T("agent.onglets.libelle") }, [ongDemander, ongCampagnes]);',
    'const selEspace = el("select", { "aria-label": T("agent.campagnes.espace"), title: T("agent.campagnes.espace"),',
    '  "data-dz-agent": "espace" }, [el("option", { value: "", texte: T("agent.campagnes.sans_espace") })]);',
    'hote.appendChild(el("p", { class: "v", texte: T("agent.campagnes.indisponible") }));',
    'return el("button", { type: "button", "data-dz-agent": "ouvrir-campagnes", texte: T("agent.action.campagnes"),',
    '  on: { click: () => passerLaMain(q) } });',
])
CLES_PARTAGES = {k: {"fr": k.rsplit(".", 1)[-1], "en": k.rsplit(".", 1)[-1].upper()} for k in (
    "campagnes.action.valider", "campagnes.action.enregistrer", "campagnes.action.generer", "campagnes.etat.validee",
    "campagnes.carte.porte", "campagnes.action.ouvrir", "campagnes.erreur.reseau", "campagnes.champ.correction",
    "campagnes.champ.placeholder", "campagnes.champ.envoyer", "agent.tiroir.envoyer", "agent.onglet.demander",
    "agent.onglet.campagnes", "agent.onglets.libelle", "agent.campagnes.espace", "agent.campagnes.sans_espace",
    "agent.campagnes.indisponible", "agent.action.campagnes")}


def _partages(tmp_path):
    racine = _depot(tmp_path, BUNDLE)
    _ecrire(racine / "frontend" / "shared" / "i18n" / "partages.json", json.dumps(CLES_PARTAGES))
    _ecrire(racine / "frontend" / "shared" / "dz-campagnes.js", CAMPAGNES_JS)
    _ecrire(racine / "frontend" / "shared" / "dz-agent.js", AGENT_JS)
    return S.extraire(racine)


def test_partage_fabrique_de_bouton(tmp_path):
    e = _partages(tmp_path)
    x = e["campagnes.action.valider"]                          # bouton(T("…"), …) : la fabrique pose texte: texte
    assert x["type"] == "bouton" and x["ecran"] == "commun" and x["cadre"] is None
    assert x["libelle"] == {"fr": "valider", "en": "VALIDER"} and x["infobulle"] is None
    assert x["sources"] == ["frontend/shared/dz-campagnes.js"]
    # le ternaire : les deux états du même bouton ont chacun leur fiche
    assert e["campagnes.action.enregistrer"]["type"] == e["campagnes.action.generer"]["type"] == "bouton"


def test_partage_lien_et_affectations(tmp_path):
    e = _partages(tmp_path)
    assert e["campagnes.action.ouvrir"]["type"] == "bouton"     # el("a", { texte: T(…) }) : un lien qui agit
    assert e["campagnes.champ.envoyer"]["type"] == "bouton"     # envoyer = el("button") ; envoyer.textContent = T(…)
    assert e["campagnes.champ.envoyer"]["libelle"]["fr"] == "envoyer"
    for k in ("campagnes.champ.placeholder", "campagnes.champ.correction"):   # setAttribute("placeholder", T(a ? … : …))
        assert e[k]["type"] == "champ" and e[k]["infobulle"]["fr"] == k.rsplit(".", 1)[-1] and e[k]["libelle"]["fr"] == ""


def test_partage_non_elements_ecartes(tmp_path):
    e = _partages(tmp_path)
    for k in ("campagnes.etat.validee", "campagnes.carte.porte", "campagnes.erreur.reseau",   # div, statut : des messages
              "agent.onglets.libelle", "agent.campagnes.sans_espace", "agent.campagnes.indisponible"):
        assert k not in e, k


def test_partage_tiroir_onglets_seuls(tmp_path):
    e = _partages(tmp_path)
    for k in ("agent.onglet.demander", "agent.onglet.campagnes"):     # la fabrique d'onglets (role: "tab")
        assert e[k]["type"] == "onglet" and e[k]["libelle"]["fr"] == k.rsplit(".", 1)[-1]
        assert e[k]["sources"] == ["frontend/shared/dz-agent.js"]
    x = e["agent.campagnes.espace"]                                    # aria-label et title : une seule clé
    assert x["type"] == "champ" and x["infobulle"]["fr"] == "espace" and x["libelle"]["fr"] == ""
    assert e["agent.action.campagnes"]["type"] == "bouton"
    assert "agent.tiroir.envoyer" not in e                             # tiroir d'avant t285b : hors du périmètre


def test_partages_absents(depot):
    assert not any(k.startswith(("campagnes.", "agent.")) for k in S.extraire(depot))


def test_vrai_catalogue_agent_campagnes():
    """t287 : le vrai composant de l'agent Campagnes et les onglets du tiroir F1 sont au catalogue, sur « commun »."""
    e = S.extraire(RACINE)
    for k in ("campagnes.champ.envoyer", "campagnes.action.valider", "campagnes.action.modifier",
              "campagnes.action.generer", "campagnes.action.refuser", "campagnes.action.continuer",
              "campagnes.action.reprendre", "campagnes.action.ouvrir", "campagnes.action.enregistrer",
              "campagnes.action.activer_ouvrir", "agent.onglet.campagnes", "agent.onglet.demander",
              "agent.campagnes.espace", "agent.action.campagnes"):
        assert k in e and e[k]["ecran"] == "commun", k
    assert e["agent.onglet.campagnes"]["type"] == "onglet"
    assert not [k for k in e if k.startswith(("campagnes.etat.", "campagnes.erreur.", "campagnes.carte.",
                                              "campagnes.fil.", "campagnes.outil.", "agent.tiroir."))]


def test_vrai_catalogue_canaux_projet():
    """t307 (25/10/2026) : le bouton « Canaux » de la barre « Projet » (couche montage.js, aide dzPcB) et le bouton
    « Enregistrer » de la boîte des canaux (frontend/shared/dz-projet-canaux.js) sont au catalogue, sur la Bibliothèque
    (zone « projets ») ; ni les messages de la boîte, ni son « Annuler » commun."""
    e = S.extraire(RACINE)
    b = e.get("projets.canaux.bouton")
    assert b and b["type"] == "bouton" and b["ecran"] == "library"   # glyphe donné par le script partagé (P.glyphe())
    assert b["infobulle"] and b["infobulle"]["fr"].startswith("Choisir les comptes")
    s = e.get("projets.canaux.enregistrer")
    assert s and s["type"] == "bouton" and s["ecran"] == "library"
    assert s["sources"] == ["frontend/shared/dz-projet-canaux.js"]
    assert not [k for k in e if k.startswith("projets.canaux.") and k not in ("projets.canaux.bouton",
                                                                               "projets.canaux.enregistrer")]
    assert "frontend/shared/dz-projet-canaux.js" not in (e.get("commun.action.annuler") or {}).get("sources", [])


def test_deterministe(tmp_path):
    racine = _depot(tmp_path, ";".join(CAS.values()) + ";" + BUNDLE)
    a, b = S.extraire(racine), S.extraire(racine)
    assert list(a) == list(b) and all(a[k]["sources"] == b[k]["sources"] for k in a)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


import catalogue as C                                                      # noqa: E402


def _fiche(i="a.b.c", lib="x", etat=None, role=""):
    f = {"id": i, "ecran": "montage", "cadre": None, "type": "bouton", "libelle": {"fr": lib, "en": lib},
         "infobulle": None, "icone": None, "sources": ["i18n:" + i]}
    if etat:
        f.update(etat=etat, role={"fr": role, "en": role}, synonymes={"fr": ["s"], "en": ["s"]},
                 localisateur={"selecteur": "button", "texte": {"fr": lib, "en": lib}}, guide="montage",
                 empreinte=C.empreinte(f))
    return f


def test_fusion_neuve_et_preservee():
    neuf = C.fusionner({}, {"a.b.c": _fiche()})["a.b.c"]
    assert neuf["etat"] == "extrait" and neuf["role"] == {"fr": "", "en": ""} and neuf["localisateur"] is None
    ancien = _fiche(etat="redige", role="Coupe.")
    f = C.fusionner({"a.b.c": ancien}, {"a.b.c": _fiche()})["a.b.c"]
    assert f["etat"] == "redige" and f["role"]["fr"] == "Coupe." and f["synonymes"]["fr"] == ["s"]
    assert f["localisateur"]["selecteur"] == "button" and f["guide"] == "montage"


def test_fusion_perime_retire_revient():
    ancien = _fiche(etat="redige", role="Coupe.")
    f = C.fusionner({"a.b.c": ancien}, {"a.b.c": _fiche(lib="autre")})["a.b.c"]
    assert f["etat"] == "perime" and f["role"]["fr"] == "Coupe."
    assert C.fusionner({"a.b.c": f}, {"a.b.c": _fiche(lib="autre")})["a.b.c"]["etat"] == "perime"   # reste à relire
    r = C.fusionner({"a.b.c": ancien}, {})["a.b.c"]
    assert r["etat"] == "retire"
    assert C.fusionner({"a.b.c": r}, {"a.b.c": _fiche()})["a.b.c"]["etat"] == "redige"


def test_ecran_fixe_preserve():
    ancien = {**_fiche(etat="redige", role="R"), "ecran": "quick", "ecran_fixe": True}
    assert C.fusionner({"a.b.c": ancien}, {"a.b.c": _fiche()})["a.b.c"]["ecran"] == "quick"


def test_ecriture_stable(tmp_path):
    fiches = C.fusionner({}, {"z.y.x": _fiche("z.y.x"), "a.b.c": _fiche()})
    C.ecrire(tmp_path, fiches)
    txt = (tmp_path / "montage.json").read_text(encoding="utf-8")
    assert txt.index('"a.b.c"') < txt.index('"z.y.x"') and txt.count("\n") == 7
    assert C.charger(tmp_path) == fiches
    C.ecrire(tmp_path, fiches)
    assert (tmp_path / "montage.json").read_text(encoding="utf-8") == txt


def test_check(depot):
    d = depot / "docs" / "agent" / "catalogue"
    assert C.main(["--racine", str(depot)]) == 0
    _ecrire(d / "_couverture.json", '{"ecrans": []}')
    assert C.main(["--racine", str(depot), "--check"]) == 0
    i18n = depot / "frontend" / "shared" / "i18n" / "montage.json"
    i18n.write_text(i18n.read_text(encoding="utf-8").replace("couper le clip", "scinder le clip"), encoding="utf-8")
    assert C.main(["--racine", str(depot), "--check"]) == 1                 # pas à jour : il faut relancer
    assert C.main(["--racine", str(depot)]) == 0
    assert C.main(["--racine", str(depot), "--check"]) == 0
    assert (d / "_couverture.json").exists()                                # l'écriture ne supprime pas les `_*.json`
    _ecrire(d / "_couverture.json", '{"ecrans": ["montage"]}')
    assert C.main(["--racine", str(depot), "--check"]) == 1                 # écran couvert avec du « extrait »


def test_rapport(depot, capsys):
    C.main(["--racine", str(depot)])
    assert C.main(["--racine", str(depot), "--rapport"]) == 0
    sortie = capsys.readouterr().out
    assert "montage" in sortie and "extrait" in sortie


# --- menus du Photolab : la barre GÉNÉRÉE par construireMenus (mod-menus.js), sur le registre capturé du moteur ---
# Faux mod-menus.js : même interface que le vrai (REFUSES, construireMenus(catalogue, registre, refuses, lang, t)).
# Une entrée refusée ou absente du registre est « bientot » ; une commande dont le registre n'a pas de `champs` aussi
# (preuve que les champs structurés par photolab_registre arrivent bien) ; « pl.envoyer » est ajoutée par l'écran.
FAUX_MENUS_JS = """
export const REFUSES = ["file.import."];
export function construireMenus(catalogue, registre, refuses, lang, t = (c) => c) {
  const idx = new Map(registre.map((c) => [c.id, c]));
  const etat = (id) => refuses.some((p) => id.startsWith(p)) || !idx.has(id) || !Array.isArray(idx.get(id).champs) ? "bientot"
    : (idx.get(id).enabled === false ? "inactif" : "actif");
  const noms = catalogue.menus_fr || {};
  const aff = (n) => (lang === "fr" ? noms[n] || n : n);
  const menus = [];
  for (const e of catalogue.entrees) {
    const [haut, ...reste] = e.chemin;
    let m = menus.find((x) => x.nom === haut);
    if (!m) { m = { nom: haut, nom_affiche: aff(haut), entrees: [] }; menus.push(m); }
    let l = m.entrees;
    for (const n of reste) {
      let s = l.find((x) => x.type === "sous-menu" && x.nom === n);
      if (!s) { s = { type: "sous-menu", nom: n, nom_affiche: aff(n), entrees: [] }; l.push(s); }
      l = s.entrees;
    }
    if (e.separateur) { l.push({ type: "separateur" }); continue; }
    l.push({ type: "commande", id: e.id, libelle: lang === "fr" ? e.libelle_fr : e.libelle_en,
             raccourci: (e.raccourci || "").replace("Cmd", "Ctrl"), etat: etat(e.id) });
  }
  menus[0].entrees.push({ type: "commande", id: "pl.envoyer", libelle: t("photolab.menu.envoyer"), raccourci: "", etat: "actif" });
  return menus;
}
"""
FAUX_CATALOGUE_MENUS = {"menus_fr": {"File": "Fichier", "Export": "Exporter", "Import": "Importer", "Layer": "Calque"},
                        "entrees": [
    {"chemin": ["File"], "id": "file.open", "libelle_fr": "Ouvrir…", "libelle_en": "Open…", "raccourci": "Cmd+O"},
    {"chemin": ["File"], "separateur": True},
    {"chemin": ["File", "Export"], "id": "file.export.png", "libelle_fr": "PNG rapide", "libelle_en": "Quick PNG"},
    {"chemin": ["File", "Import"], "id": "file.import.notes", "libelle_fr": "Notes…", "libelle_en": "Notes…"},
    {"chemin": ["Layer"], "id": "layer.absent", "libelle_fr": "Absent", "libelle_en": "Missing"},
    {"chemin": ["Layer"], "id": "layer.mergeDown", "libelle_fr": "Fusionner", "libelle_en": "Merge Down"}]}
FAUX_REGISTRE = [{"id": "file.open", "label": "Open…", "menu": ["File"], "enabled": True, "params": "", "shortcut": ""},
                 {"id": "file.export.png", "label": "PNG", "menu": ["File"], "enabled": True, "params": "", "shortcut": ""},
                 {"id": "file.import.notes", "label": "Notes", "menu": ["File"], "enabled": True, "params": "", "shortcut": ""},
                 {"id": "layer.mergeDown", "label": "Merge", "menu": ["Layer"], "enabled": False, "params": "", "shortcut": ""}]


def _menus_photolab(depot, registre=FAUX_REGISTRE):
    _ecrire(depot / "frontend/photolab/js/mod-menus.js", FAUX_MENUS_JS)
    _ecrire(depot / "frontend/photolab/donnees/menus.json", json.dumps(FAUX_CATALOGUE_MENUS, ensure_ascii=False))
    _ecrire(depot / "vendor/photocraft.json", json.dumps({"nom": "photocraft", "version": "9.9.9"}))
    _ecrire(depot / "backend/tests/photocraft_commandes_9.9.9.json", json.dumps(registre))
    d = json.loads((depot / "frontend/shared/i18n/photolab.json").read_text(encoding="utf-8"))
    d["photolab.menu.envoyer"] = {"fr": "Envoyer vers…", "en": "Send to…"}
    _ecrire(depot / "frontend/shared/i18n/photolab.json", json.dumps(d, ensure_ascii=False))
    return depot


def test_menus_photolab_entree_active(depot):
    e = S.extraire(_menus_photolab(depot))
    o = e["photolab.menu.file.open"]
    assert o["type"] == "menu" and o["ecran"] == "photolab" and o["cadre"] == "/photolab/"
    assert o["libelle"] == {"fr": "Ouvrir…", "en": "Open…"} and o["infobulle"] is None and o["icone"] is None
    assert o["chemin"] == {"fr": "Fichier", "en": "File"}
    assert o["raccourci"] == {"fr": "Ctrl+O", "en": "Ctrl+O"}
    assert o["sources"] == ["frontend/photolab/donnees/menus.json"]
    x = e["photolab.menu.file.export.png"]                    # sous-menu : le chemin complet, nom affiché par langue
    assert x["chemin"] == {"fr": "Fichier › Exporter", "en": "File › Export"} and "raccourci" not in x


def test_menus_photolab_bientot_exclus(depot):
    e = S.extraire(_menus_photolab(depot))
    assert "photolab.menu.file.import.notes" not in e         # refusée par le pont : « bientôt »
    assert "photolab.menu.layer.absent" not in e              # absente du registre : « bientôt »


def test_menus_photolab_inactif_garde(depot):
    e = S.extraire(_menus_photolab(depot))                    # grisée faute de document : l'entrée existe
    assert e["photolab.menu.layer.mergeDown"]["libelle"]["en"] == "Merge Down"


def test_menus_photolab_entree_de_l_ecran(depot):
    p = S.extraire(_menus_photolab(depot))["photolab.menu.pl.envoyer"]
    assert p["libelle"] == {"fr": "Envoyer vers…", "en": "Send to…"} and p["chemin"]["fr"] == "Fichier"
    assert p["sources"] == ["frontend/photolab/js/mod-menus.js"]   # absente de menus.json : insérée par l'écran


def test_menus_photolab_champs_structures(depot):
    """Les champs viennent de photolab_registre.structurer, comme GET /api/photolab/commandes : sans eux le faux
    construireMenus grise tout."""
    e = S.extraire(_menus_photolab(depot))
    assert "photolab.menu.file.export.png" in e


def test_menus_photolab_absents(depot):
    assert not any(k.startswith("photolab.menu.") for k in S.extraire(depot))   # pas de mod-menus.js : rien


def test_menus_photolab_registre_manquant(depot):
    _menus_photolab(depot)
    (depot / "backend/tests/photocraft_commandes_9.9.9.json").unlink()
    with pytest.raises(RuntimeError, match="photocraft_commandes_9.9.9"):
        S.extraire(depot)                                     # jamais un catalogue vidé en silence


def test_menus_photolab_empreinte_suit_le_chemin():
    f = _fiche()
    assert C.empreinte(f) == C.empreinte({**f, "chemin": None})          # fiches sans chemin : empreinte inchangée
    g = {**f, "chemin": {"fr": "Fichier", "en": "File"}}
    assert C.empreinte(g) != C.empreinte({**g, "chemin": {"fr": "Calque", "en": "Layer"}})
    assert C.empreinte(g) != C.empreinte({**g, "raccourci": {"fr": "Ctrl+O", "en": "Ctrl+O"}})


# --- le VRAI catalogue (docs/agent/catalogue), sur le dépôt réel ---
import catalogue_commun as CC                                              # noqa: E402

VUES = ("quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library", "assets3d",
        "vectorlab", "photolab", "avatarlive", "settings", "commun")
CADRES = {None, *CC.CADRE_DE_ZONE.values(), *(c for _, c in S.LABS.values())}
TYPES = {"bouton", "champ", "outil", "reglage", "onglet", "menu", "icone", "raccourci", "panneau"}


def test_cadres_attendus():
    assert "/avatar/" in CADRES and "/vectorlab/" in CADRES and None in CADRES


def test_vrai_catalogue_a_jour():
    assert C.main(["--check"]) == 0


def test_vrai_catalogue_langue_de_l_interface():
    """t248 : le réglage de la langue (DzLangueUI, un libellé à côté d'un sélecteur maison) échappe à l'extraction du
    bundle ; il entre par la recherche des Réglages (_INDEX_FIXE), qui doit donc le connaître, traduit."""
    langue = [f for f in C.charger().values()
              if f["ecran"] == "settings" and f["libelle"]["fr"] == "Langue de l'interface"]
    assert len(langue) == 1, [f["id"] for f in langue]
    assert langue[0]["libelle"]["en"] == "Interface language" and langue[0]["type"] == "reglage"


def test_vrai_catalogue_menus_photolab():
    """Le vrai mod-menus.js sur le registre capturé : les entrées actives ont leur fiche, les « bientôt » non."""
    e = S.extraire(RACINE)
    o = e["photolab.menu.file.open"]
    assert o["chemin"] == {"fr": "Fichier", "en": "File"} and o["libelle"]["en"].startswith("Open")
    assert e["photolab.menu.pl.envoyer"]["sources"] == ["frontend/photolab/js/mod-menus.js"]
    assert "photolab.menu.layer.mergeGroup" in e                # insertion M7 (INSERTIONS_M7)
    assert "photolab.menu.file.openAs" not in e                 # refusée par le pont : « bientôt »
    assert "photolab.menu.edit.puppetWarp" not in e             # D9 : « bientôt »


def test_vrai_catalogue_integre():
    fiches = C.charger()
    assert len(fiches) >= 300, len(fiches)
    chapitres = {c["id"] for c in json.loads((RACINE / "docs/guide/src/chapitres.json")
                                             .read_text(encoding="utf-8"))["chapitres"]}
    for f in fiches.values():
        assert f["ecran"] in VUES and f.get("cadre") in CADRES and f["etat"] in C.ETATS, f["id"]
        assert f["type"] in TYPES, (f["id"], f["type"])
        assert set(f["libelle"]) == {"fr", "en"}, f["id"]
        if f["infobulle"] is not None:
            assert set(f["infobulle"]) == {"fr", "en"}, f["id"]
        assert f["libelle"]["fr"] or (f["infobulle"] or {}).get("fr"), f["id"]
        assert f["sources"], f["id"]
        assert f.get("guide") in (None, *chapitres), f["id"]
        if f["etat"] == "redige":
            for l in ("fr", "en"):
                assert 0 < len(f["role"][l]) <= 300, (f["id"], l)
                assert isinstance(f["synonymes"][l], list), (f["id"], l)


def _categories_du_code() -> set:
    """Les catégories qu'une dépense peut vraiment porter : plafonds.CATEGORIES, plus les littéraux `categorie="x"`
    passés par le code (tirer_garde : « motion », « aide »). Rien d'autre n'existe."""
    import re
    from app.services import plafonds as P
    vues = set(P.CATEGORIES)
    for f in (RACINE / "backend" / "app").rglob("*.py"):
        vues |= set(re.findall(r'categorie\s*(?::\s*str\s*)?=\s*"([a-z0-9_]+)"', f.read_text(encoding="utf-8")))
    return vues


def test_roles_ne_citent_que_des_categories_reelles():
    """t244 (20/10/2026) : « Rejouer la recette » disait « sous le plafond generation » (une `source` que
    _categorie_image ramène à « bibliotheque ») et les illustrations de Chapitres « bibliotheque » (elles envoient
    « chapitres »). Un rôle ne cite qu'une catégorie de dépense qui existe, sous son id exact, dans les deux langues.
    Et il dit « catégorie », jamais « plafond « X » » : aucun plafond par catégorie ne se règle, l'utilisateur le
    cherchait dans les Réglages."""
    import re
    vues = _categories_du_code()
    motifs = {"fr": r'catégorie\s+[«"“]\s*([A-Za-z0-9_ ]+?)\s*[»"”]', "en": r'[«"“]\s*([A-Za-z0-9_ ]+?)\s*[»"”]\s+category'}
    rediges = [f for f in C.charger().values() if f["etat"] == "redige"]
    faux = [(f["id"], l, m) for f in rediges for l, motif in motifs.items()
            for m in re.findall(motif, f["role"][l]) if m not in vues]
    assert not faux, faux
    anciens = [f["id"] for f in rediges if re.search(r'plafonds?\s+(?:de\s+dépense\s+)?[«"“]', f["role"]["fr"])
               or re.search(r'[»"”]\s+(?:spending\s+)?cap\b', f["role"]["en"])]
    assert not anciens, anciens


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
