"""Banc de mutations de la pastille de coût : casser → rouge → remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_cout_pastille.py          # toutes
    python tests/mutations_cout_pastille.py 0 3      # celles-là

IL MUTE LE BUNDLE LIVRÉ, PAS LE PATCHER — c'est le fichier que l'application
charge, et c'est lui que `tests/test_cout_pastille.py` lit. Muter le patcher
prouverait seulement que le patcher est cohérent avec lui-même. Chaque
mutation est remise à l'octet près (sha256 vérifié après coup) ; le bundle
fait 1,5 Mo et ses fins de ligne sont homogènes (le patcher l'exige), donc
l'aller-retour CRLF→LF→CRLF est sûr — et c'est le sha qui le dit, pas moi.

LA MUTATION N°0 EST LA SEULE QUI COMPTE VRAIMENT. Le préfixe `non-tarifé:`
est écrit par Python (`_job_to_cost`) et découpé par JavaScript (le préambule
du bundle) : deux littéraux, deux langages, deux fichiers, et rien d'autre que
`prefixe_du_bundle_est_celui_du_backend` pour les tenir ensemble. Elle est
donc jouée DANS LES DEUX SENS (0 côté bundle, 1 côté backend).

CE QUE CETTE TABLE A TROUVÉ, ET C'EST SA RAISON D'ÊTRE. Écrite une première
fois, elle a rendu `ROUGE(autres)` sur 0 et 1 avec TROIS lignes manquantes :
`un_blanc_sans_son_prefixe_technique` comparait le titre au préfixe EXTRAIT DU
BUNDLE — donc à elle-même. Renommer le préfixe d'un seul côté laissait l'écran
afficher « non-tarifé:provider_de_demain » en entier et la ligne restait
VERTE. Elle compare désormais à la CLÉ que le backend a réellement écrite.
Les deux autres (`..._est_nomme_dans_l_infobulle`, `deux_blancs_nomment_...`)
sont VERTES à bon droit sous 0 et 1, et c'est la n°8 qui les tient.

RÉSULTAT MESURÉ le 05/09/2026, python embarqué, un processus par exécution du
banc : les NEUF mutations sont ROUGES et rougissent EXACTEMENT les lignes
déclarées — aucune manquante, aucune en trop.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
BANC = "tests/test_cout_pastille.py"
BUNDLE = "frontend/dist/assets/index-BEOJX8L5.js"
ROUTES = "backend/app/api/routes.py"

# (fichier, ancien, nouveau, lignes attendues rouges)
M = [
    # 0 — le préfixe renommé CÔTÉ BUNDLE : plus une seule clé ne correspond,
    #     tous les blancs deviennent invisibles. C'est le mode de panne exact
    #     qu'un renommage « propre » d'un seul côté produirait.
    # DÉCLARÉ POUR 0 ET 1 : `un_blanc_est_nomme_dans_l_infobulle` et
    # `deux_blancs_nomment_les_deux` restent VERTES, et à bon droit — la clé
    # non découpée tombe dans la branche ordinaire et s'affiche EN ENTIER,
    # donc le nom du fournisseur EST bien à l'écran, noyé dans son préfixe.
    # C'est `un_blanc_sans_son_prefixe_technique` qui voit la différence, et
    # elle ne la voyait PAS avant que cette table ne l'y oblige (elle
    # comparait au préfixe du bundle, donc à elle-même).
    (BUNDLE,
     'var P="non-tarifé:"',
     'var P="non-tarife:"',
     ["prefixe_du_bundle_est_celui_du_backend",
      "bundle_porte_L1-preambule",
      "un_blanc_est_compte", "un_blanc_sans_son_prefixe_technique",
      "un_blanc_annonce_un_minorant",
      "deux_blancs_sont_comptes", "deux_blancs_accordent_le_pluriel"]),
    # 1 — le MÊME renommage, CÔTÉ BACKEND. Le bundle est intact ; c'est la
    #     clé qui change. Les mêmes lignes rougissent, par l'autre bout —
    #     sauf `bundle_porte_L1`, puisque le bundle n'a pas bougé.
    (ROUTES,
     'f"non-tarifé:{prov}")',
     'f"non-tarife:{prov}")',
     ["prefixe_du_bundle_est_celui_du_backend",
      "un_blanc_est_compte", "un_blanc_sans_son_prefixe_technique",
      "un_blanc_annonce_un_minorant",
      "deux_blancs_sont_comptes", "deux_blancs_accordent_le_pluriel"]),
    # 2 — le nom du fournisseur affiché AVEC son préfixe technique : le
    #     compte reste juste, le minorant s'annonce, seule la lisibilité
    #     tombe. Une seule ligne le voit, et c'est celle qui le dit.
    (BUNDLE,
     'nt.push(x.slice(P.length));',
     'nt.push(x);',
     ["bundle_porte_L1-preambule", "un_blanc_sans_son_prefixe_technique"]),
    # 3 — l'avertissement de MINORANT supprimé : le total incomplet se
    #     présente de nouveau comme un total. La puce et le « ≥ » restent,
    #     donc les comptes ne bougent pas — seul l'aveu disparaît.
    (BUNDLE,
     'if(nt.length){t+="\\n\\n⚠ Ce total est un MINORANT : "',
     'if(0){t+="\\n\\n⚠ Ce total est un MINORANT : "',
     ["bundle_porte_L1-preambule", "un_blanc_annonce_un_minorant",
      "deux_blancs_accordent_le_pluriel"]),
    # 4 — le pluriel figé au singulier.
    (BUNDLE,
     '+" fournisseur"+(nt.length>1?"s":"")+" sans tarif ("',
     '+" fournisseur"+" sans tarif ("',
     ["bundle_porte_L1-preambule", "deux_blancs_accordent_le_pluriel"]),
    # 5 — le zéro local redevient un « $0 » nu, qui se lit comme une panne.
    (BUNDLE,
     '+(x==="local"?" (opérations locales, sans dépense)":"")',
     '+""',
     ["bundle_porte_L1-preambule", "carte_tarifee_explique_le_zero_local"]),
    # 6 — l'infobulle revient à la phrase fixe d'avant le lot : `by_provider`
    #     n'atteint plus le pixel du tout. Le préambule reste, donc le cœur
    #     s'exécute encore — ce sont les lignes du MIROIR qui le voient.
    (BUNDLE,
     "title:__dzCoutBlanc(Cu).titre",
     'title:"Estimated spend on this app + live provider balances. '
     'Click for Settings."',
     ["bundle_porte_L2-infobulle", "ancre_consommee_L2-infobulle",
      "marqueur_compte_exact"]),
    # 7 — le « ≥ » retiré du total : le chiffre incomplet redevient un
    #     chiffre net. Le MIROIR le voit ; le cœur, non — il ne connaît pas
    #     la pastille. C'est la raison d'être de la section [1].
    (BUNDLE,
     'children:[__dzCoutBlanc(Cu).n?"≥ $":"$",',
     'children:["$",',
     ["bundle_porte_L3-total-et-puce", "ancre_consommee_L3-total-et-puce",
      "marqueur_compte_exact"]),
    # 8 — DEUX remplacements, et il en faut deux : le nom du fournisseur est
    #     imprimé À DEUX ENDROITS (la ligne de la liste, et la phrase du
    #     MINORANT qui les énumère). Aucune mutation d'un seul point ne peut
    #     donc le faire disparaître de l'écran — c'est une redondance de
    #     l'affichage, pas une faiblesse des lignes. Elles sont tenues ici.
    (BUNDLE,
     [('ls.push("  ? "+x.slice(P.length)', 'ls.push("  ? "+"(masqué)"'),
      ('+nt.join(", ")', '+""')],
     None,
     ["bundle_porte_L1-preambule", "un_blanc_est_nomme_dans_l_infobulle",
      "un_blanc_sans_son_prefixe_technique", "deux_blancs_nomment_les_deux"]),
]


def rouges():
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR.

    Le banc rend 0 (tout vert) ou 1 (des rouges) ; tout autre code veut dire
    qu'il est MORT au lieu de rougir — la faute n°6 du chantier — et l'on rend
    un troisième état plutôt que de lire une liste vide comme « rien cassé ».
    """
    r = subprocess.run([PY, BANC], capture_output=True,
                       cwd=R / "backend", timeout=1800)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    erreur = r.returncode not in (0, 1) or "=== " not in txt
    return set(re.findall(r"^  FAIL  (\S+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        # une mutation est UN remplacement, ou une LISTE de remplacements
        # appliqués dans l'ordre — voir la n°8 et sa raison d'être.
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges()
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = sorted(set(attendus) - rg)
        en_trop = sorted(rg - set(attendus))
        if erreur:
            verdict = "MORT(pas rouge)"
            print(sortie[-1500:], file=sys.stderr)
        elif attendus:
            verdict = ("ROUGE" if not manquants and not en_trop
                       else ("VERTE" if not rg else "ROUGE(autres)"))
        else:
            verdict = "VERTE(attendue)" if not rg else "ROUGE(inattendu)"
        bilan.append((i, verdict, sorted(rg), manquants, en_trop))
        print(f"[{i}] {verdict:16s} {pathlib.Path(rel).name:24s} "
              f"{paires[0][0].strip()[:38]!r}")
        print(f"     rouges={sorted(rg)}")
        if manquants:
            print(f"     MANQUANTS={manquants}")
        if en_trop:
            print(f"     EN TROP={en_trop}")
        print(f"     sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
