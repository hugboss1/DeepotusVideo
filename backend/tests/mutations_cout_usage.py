"""Banc de mutations de la facture par provider : casser → rouge → remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_cout_usage.py          # toutes
    python tests/mutations_cout_usage.py 0 4      # celles-là

Il MUTE `app/api/routes.py` une mutation à la fois et la REMET à l'octet près
(assertion sur le sha256), donc il ne se lance pas pendant qu'un autre banc lit
ce fichier. Chaque ligne de `M` nomme les lignes de `tests/test_cost_usage.py`
qu'elle doit faire rougir — ET ELLES SEULES : une mutation qui en rougit
d'autres est signalée « ROUGE(autres) », une qui n'en rougit aucune « VERTE »,
c'est-à-dire une assertion qui manque.

LA MUTATION N°5 EST VERTE, ET C'EST VOULU : retirer `montage_proxy` de la
liste blanche ne change rien ICI parce que `GET /cost/usage` l'écarte déjà par
un `where` (65afc16). C'est `cout_un_proxy_ne_coute_rien`, dans
`tests/test_montage_media.py`, qui tient ce cas-là — et il le tient TOUJOURS
après ce lot, ce qui a été REJOUÉ plutôt que promis : la mutation N-P20 (le
`where` de `cost_usage` retiré) rend ce banc-là 66/1, la ligne rouge étant
`cout_un_proxy_ne_coute_rien` et elle seule, sur
`{'total_usd': 0.0, 'by_provider': {'local': 0.0}}` — la carte n'est plus
vide, et c'est exactement ce que cette ligne exige. Une mutation verte
déclarée vaut mieux qu'une couverture supposée.

RÉSULTAT MESURÉ le 05/09/2026 (python embarqué, un processus par exécution du
banc) : les six autres mutations sont ROUGES et rougissent EXACTEMENT les
lignes déclarées, aucune de plus. Voir le tableau en tête de
`test_cost_usage.py` pour les montants.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
BANC = "tests/test_cost_usage.py"
CIBLE = "backend/app/api/routes.py"

# (fichier, ancien, nouveau, lignes attendues rouges)
M = [
    # 0 — la liste blanche des providers qui ne dépensent rien, retirée : les
    #     sept retombent sur la campagne par défaut, exactement l'état d'avant.
    (CIBLE,
     "    if prov in _JOBS_SANS_DEPENSE:\n"
     "        return _pricing.no_spend(_JOBS_SANS_DEPENSE[prov])\n",
     "",
     ["cout_montage_ne_coute_rien", "cout_animation_ne_coute_rien",
      "cout_ugc_ne_coute_rien", "cout_news_ne_coute_rien",
      "cout_template_ne_coute_rien", "cout_composition_ne_coute_rien",
      "cout_card3d_ne_coute_rien"]),
    # 1 — la branche `asset3d` débranchée : un maillage redevient une vidéo.
    (CIBLE,
     '    if prov == "asset3d":',
     '    if prov == "asset3d_JAMAIS":',
     ["cout_asset3d_rodin_est_facture_au_tarif_de_son_moteur",
      "cout_asset3d_hunyuan_est_facture_au_tarif_de_son_moteur",
      "cout_asset3d_texturage_est_facture_en_credits_meshy"]),
    # 2 — le texturage Meshy retombe sur le tarif d'un maillage neuf : une
    #     dépense RÉELLE, mais chez le mauvais fournisseur (fal au lieu de
    #     meshy) et au mauvais prix. Discrimine la ligne meshy des deux autres.
    (CIBLE,
     '        if meta.get("texturier") == "meshy":',
     '        if meta.get("texturier") == "meshy_JAMAIS":',
     ["cout_asset3d_texturage_est_facture_en_credits_meshy"]),
    # 3 — LA MUTATION DU LOT : la campagne redevient la branche PAR DÉFAUT,
    #     donc tout provider inconnu refacture 10 s de Seedance + une image.
    (CIBLE,
     "    if prov in _JOBS_CAMPAGNE:",
     "    if True:",
     ["cout_provider_inconnu_ne_fabrique_aucune_depense",
      "cout_provider_inconnu_se_nomme_dans_by_provider"]),
    # 4 — le zéro GÉNÉRALISÉ, la faute symétrique : plus rien n'est facturé.
    #     `heygen` garde sa branche nommée et reste vert — c'est ce qui rend
    #     les deux lignes de campagne discriminantes.
    (CIBLE,
     '_JOBS_CAMPAGNE = {"seedance"}',
     "_JOBS_CAMPAGNE = set()",
     ["cout_seedance_facture_son_image_et_sa_video",
      "cout_provider_nul_reste_une_campagne_seedance"]),
    # 5 — VERTE ATTENDUE, déclarée en tête : le `where` de la route tient déjà
    #     `montage_proxy`, et c'est le banc media qui le mesure.
    (CIBLE,
     '    "montage_proxy": "Proxy de montage (transcodage ffmpeg local)",\n',
     "",
     []),
    # 6 — le blanc ne porte plus le NOM du provider : il rend toujours 0, mais
    #     `by_provider` ne dit plus LEQUEL n'est pas tarifé. Seule la ligne qui
    #     parle du nom rougit — celle du montant reste verte, à bon droit.
    (CIBLE,
     'f"non-tarifé:{prov}")',
     '"local")',
     ["cout_provider_inconnu_se_nomme_dans_by_provider"]),
]


def rouges():
    """Les noms des lignes ROUGES du banc, sa sortie, et un drapeau d'ERREUR.

    Le banc rend 0 (tout vert) ou 1 (des rouges) ; tout autre code veut dire
    qu'il est MORT au lieu de rougir — la faute n°6 du chantier — et l'on rend
    un troisième état plutôt que de lire une liste vide comme « rien cassé ».
    """
    r = subprocess.run([PY, BANC], capture_output=True,
                       cwd=R / "backend", timeout=900)
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
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF et
        # l'on réécrit avec la fin de ligne du fichier ; la remise se fait à
        # l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        txt = txt.replace(old, new)
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
        print(f"[{i}] {verdict:16s} {old.strip()[:46]!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:2] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
