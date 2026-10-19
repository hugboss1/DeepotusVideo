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
    _ecrire(i18n / "photolab.json", json.dumps({"photolab.outil.pinceau": {"fr": "Pinceau", "en": "Brush"}}))
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
