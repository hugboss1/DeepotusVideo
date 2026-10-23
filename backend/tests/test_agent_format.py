# -*- coding: utf-8 -*-
"""t285a (23/10/2026) — le paquet agent « Campagnes » et le format de conversation v1.

Vérifie services/agent_format.py (nouveau_message, valider, empreinte), le schéma JSON (contrôle fait à la main,
aucune bibliothèque ajoutée) et la présence du paquet docs/agent/campagnes/.
Run : & $PY tests/test_agent_format.py   (depuis backend/)
"""
import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from app.services import agent_format as F                 # noqa: E402

PAQUET = REPO / "docs" / "agent" / "campagnes"
TXT = [{"type": "texte", "texte": "ok"}]

TYPES_JSON = {"object": dict, "array": list, "string": str, "number": (int, float), "integer": int,
              "boolean": bool, "null": type(None)}


def erreurs_schema(val, sch, racine, chemin="$"):
    """Contrôle minimal d'un schéma JSON : $ref local, oneOf, type, const, enum, minimum, required, properties, items."""
    err = []
    if "$ref" in sch:
        cible = racine
        for p in sch["$ref"].lstrip("#/").split("/"):
            if p:
                cible = cible[p]
        return erreurs_schema(val, cible, racine, chemin)
    if "oneOf" in sch:
        if not any(not erreurs_schema(val, a, racine, chemin) for a in sch["oneOf"]):
            err.append(f"{chemin}: aucune alternative ne convient")
    t = sch.get("type")
    if t:
        ts = t if isinstance(t, list) else [t]
        if not any(isinstance(val, TYPES_JSON[x]) and not (x in ("number", "integer") and isinstance(val, bool))
                   for x in ts):
            return [f"{chemin}: type {t} attendu"]
    if "const" in sch and val != sch["const"]:
        err.append(f"{chemin}: const {sch['const']}")
    if "enum" in sch and val not in sch["enum"]:
        err.append(f"{chemin}: hors enum")
    if "minimum" in sch and isinstance(val, (int, float)) and val < sch["minimum"]:
        err.append(f"{chemin}: sous le minimum")
    if "minItems" in sch and isinstance(val, list) and len(val) < sch["minItems"]:
        err.append(f"{chemin}: trop court")
    if isinstance(val, dict):
        for k in sch.get("required", []):
            if k not in val:
                err.append(f"{chemin}: clé requise {k}")
        for k, s in sch.get("properties", {}).items():
            if k in val:
                err += erreurs_schema(val[k], s, racine, f"{chemin}.{k}")
    if isinstance(val, list) and "items" in sch:
        for i, v in enumerate(val):
            err += erreurs_schema(v, sch["items"], racine, f"{chemin}[{i}]")
    return err


print("=== t285a : format de conversation v1 ===")
check("constantes du format", lambda: (
    F.ROLES_MESSAGE == ("utilisateur", "agent", "outil", "fait")
    and F.TYPES_BLOC == ("texte", "carte", "resultat_outil", "porte")
    and F.GENRES_CARTE == ("porte", "devis", "continuer", "espace", "brouillons", "ouvrir")
    and F.ETATS_CARTE == ("proposee", "acceptee", "refusee", "terminee")))

m = F.nouveau_message("agent", TXT)
check("test_message_neuf_valide", F.valider(m) == [], F.valider(m))
check("message neuf : forme", lambda: (
    m["v"] == 1 and m["role"] == "agent" and m["origine"] == "pc" and m["appareil"] is None
    and m["cout_paye"] == 0.0 and m["blocs"] == TXT and len(m["id"]) == 36 and m["quand"].endswith(("Z", "+00:00"))))
check("origine et appareil passés", lambda: (
    F.nouveau_message("utilisateur", TXT, origine="telephone", appareil="tel-1")["origine"] == "telephone"
    and F.nouveau_message("utilisateur", TXT, origine="telephone", appareil="tel-1")["appareil"] == "tel-1"))
check("ids distincts", F.nouveau_message("agent", TXT)["id"] != m["id"])

carte_ok = F.nouveau_message("agent", [{"type": "carte", "genre": "devis", "libelle": "Image", "etat": "proposee",
                                         "devis": 0.04, "action": "deviser_generation", "arguments": {"n": 1}}])
check("carte complète valide", F.valider(carte_ok) == [], F.valider(carte_ok))
sans_genre = F.nouveau_message("agent", [{"type": "carte", "libelle": "x", "etat": "proposee"}])
check("test_carte_sans_genre_refusee", len(F.valider(sans_genre)) >= 1)
check("carte : genre inconnu refusé", len(F.valider(F.nouveau_message("agent", [
    {"type": "carte", "genre": "publier", "libelle": "x", "etat": "proposee"}]))) >= 1)
check("carte : état inconnu refusé", len(F.valider(F.nouveau_message("agent", [
    {"type": "carte", "genre": "devis", "libelle": "x", "etat": "bof"}]))) >= 1)
check("porte valide", F.valider(F.nouveau_message("agent", [{"type": "porte", "numero": 1, "etat": "proposee"}])) == [])
check("porte : numéro 3 refusé", len(F.valider(F.nouveau_message("agent", [
    {"type": "porte", "numero": 3, "etat": "proposee"}]))) >= 1)
check("resultat_outil valide", F.valider(F.nouveau_message("outil", [
    {"type": "resultat_outil", "outil": "lire_espace", "resume": "3 espaces"}])) == [])
check("bloc de type inconnu refusé", len(F.valider(F.nouveau_message("agent", [{"type": "video"}]))) >= 1)
check("texte sans texte refusé", len(F.valider(F.nouveau_message("agent", [{"type": "texte"}]))) >= 1)
check("blocs vides refusés", len(F.valider(F.nouveau_message("agent", []))) >= 1)

bad = dict(m, role="robot")
check("test_role_inconnu_refuse", len(F.valider(bad)) >= 1)
check("version 2 refusée", len(F.valider(dict(m, v=2))) >= 1)
check("origine inconnue refusée", len(F.valider(dict(m, origine="lune"))) >= 1)
check("coût négatif refusé", len(F.valider(dict(m, cout_paye=-1))) >= 1)
check("non-dict refusé", len(F.valider("x")) >= 1)  # type: ignore[arg-type]
sans_id = {k: v for k, v in m.items() if k != "id"}
check("id absent refusé", len(F.valider(sans_id)) >= 1)

e1 = F.empreinte(m)
check("test_empreinte_stable", lambda: (
    e1 == F.empreinte(json.loads(json.dumps(m)))
    and len(e1) == 40
    and e1 != F.empreinte(dict(m, blocs=[{"type": "texte", "texte": "autre"}]))))
check("empreinte : ordre des clés sans effet", F.empreinte(m) == F.empreinte(dict(reversed(list(m.items())))))
check("empreinte : quand et coût hors empreinte",
      F.empreinte(m) == F.empreinte(dict(m, quand="2020-01-01T00:00:00Z", cout_paye=9.0)))
check("empreinte : id compte", F.empreinte(m) != F.empreinte(dict(m, id="autre")))

sch_p = PAQUET / "format.schema.json"
SCH = json.loads(sch_p.read_text(encoding="utf-8")) if sch_p.exists() else {}
check("schéma JSON lisible", SCH.get("type") == "object")
for nom, msg in (("message neuf", m), ("carte", carte_ok)):
    e = erreurs_schema(msg, SCH, SCH)
    check(f"test_schema_conforme ({nom})", SCH != {} and e == [], e)
check("schéma : refuse un rôle inconnu", len(erreurs_schema(bad, SCH, SCH)) >= 1)
check("schéma : refuse une carte sans genre", len(erreurs_schema(sans_genre, SCH, SCH)) >= 1)
check("schéma : refuse sans id", len(erreurs_schema(sans_id, SCH, SCH)) >= 1)
check("schéma : listes alignées sur le module", lambda: (
    set(SCH["properties"]["role"]["enum"]) == set(F.ROLES_MESSAGE)
    and set(SCH["$defs"]["carte"]["properties"]["genre"]["enum"]) == set(F.GENRES_CARTE)
    and set(SCH["$defs"]["carte"]["properties"]["etat"]["enum"]) == set(F.ETATS_CARTE)))

fichiers = ("CAMPAGNES.md", "conformite-crypto.md", "dossier-modele.md", "format.md", "format.schema.json")
check("test_paquet_present : les cinq fichiers", all((PAQUET / f).is_file() for f in fichiers),
      [f for f in fichiers if not (PAQUET / f).is_file()])
camp = (PAQUET / "CAMPAGNES.md").read_text(encoding="utf-8") if (PAQUET / "CAMPAGNES.md").exists() else ""
check("CAMPAGNES.md : PORTE 1 et PORTE 2", "PORTE 1" in camp and "PORTE 2" in camp)
check("CAMPAGNES.md : ni ~/.claude ni skill", "~/.claude" not in camp and "skill" not in camp.lower())
check("CAMPAGNES.md : ni dz_api ni Claude Code", "dz_api" not in camp and "claude code" not in camp.lower())
check("CAMPAGNES.md : concis", 0 < len(camp.splitlines()) < 300, len(camp.splitlines()))
check("CAMPAGNES.md : sections demandées", all(s in camp.lower() for s in (
    "stratégie", "accroches", "formats par canal", "contrôle")))
check("CAMPAGNES.md : outils nommés", all(o in camp for o in (
    "chercher_app", "lire_espace", "lire_bibliotheque", "lire_planificateur", "lire_document", "ecrire_dossier",
    "proposer_porte", "deviser_generation", "creer_brouillons", "pointer")))
fmt = (PAQUET / "format.md").read_text(encoding="utf-8") if (PAQUET / "format.md").exists() else ""
check("format.md : v1 et empreinte", '"v": 1' in fmt and "empreinte" in fmt)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
