# Format de conversation de l'agent Campagnes, v1

Défini une seule fois, ici et dans `format.schema.json`. Le code de référence est
`backend/app/services/agent_format.py` (`nouveau_message`, `valider`, `empreinte`). Le téléphone reprend ce format.

## Un message

```json
{
  "v": 1,
  "id": "uuid créé par l'appareil d'origine",
  "role": "utilisateur | agent | outil | fait",
  "quand": "2026-10-23T18:00:00+00:00",
  "origine": "pc | telephone",
  "appareil": null,
  "blocs": [{"type": "texte", "texte": "..."}],
  "cout_paye": 0.0
}
```

- `v` vaut toujours 1. Un message d'une autre version est refusé, jamais deviné.
- `id` : UUID créé par l'appareil d'origine, stable pour toute la vie du message.
- `quand` : horodatage ISO 8601 en UTC.
- `cout_paye` : dollars déjà payés pour ce tour, sur l'appareil où il a eu lieu. Compté une fois, jamais repayé.
- `role` `fait` : un événement noté par l'app (carte acceptée, porte validée, dossier écrit), sans texte de l'agent.

## Les blocs

| `type` | Clés requises | Clés facultatives |
|---|---|---|
| `texte` | `texte` | |
| `carte` | `genre`, `libelle`, `etat` | `devis` (dollars), `action`, `arguments` |
| `resultat_outil` | `outil`, `resume` | |
| `porte` | `numero` (1 ou 2), `etat` (`proposee`, `validee`, `refusee`) | |

- `genre` d'une carte : `porte`, `devis`, `continuer`, `espace`, `brouillons`, `ouvrir`, `reponse_whatsapp`, `modele_whatsapp`, `humain` (ces trois-là : agent WhatsApp d'un espace), `recherche` (t354 : une recherche web d'entreprises payante, lancée seulement si l'utilisateur accepte la carte), `sequence` (t355 : la porte 2 d'une séquence de prospection ; `arguments` = {sid, pid, canal, etapes [{objet, texte, delai_jours}]} ; acceptée = validée par l'utilisateur, refusée = annulée).
- `etat` d'une carte : `proposee`, `acceptee`, `refusee`, `terminee`.
- `resultat_outil` porte un résumé, **jamais** un secret (clé, jeton, mot de passe).

## Décider une carte (t285a)

- Les cartes d'une conversation sont numérotées `n` = 0, 1, 2… dans l'ordre des blocs `carte` des messages
  `agent`. C'est le `n` de `POST …/{id}/carte/{n}`.
- Une décision ne modifie **jamais** le message d'origine : elle s'écrit comme un message `fait` neuf, dont le bloc
  `carte` reprend le genre, le libellé et l'action, avec `etat` `acceptee` ou `refusee` et `arguments.carte = n`
  (plus `job_id` pour un devis, `espace_id` pour le choix d'espace). Une carte déjà décidée ne se redécide pas.
- Quand le job d'un devis vidéo accepté finit (réussi ou en échec), un message `fait` de plus porte la carte en
  `etat` `terminee`, `action` `continuer`, `arguments` `{carte, job_id, statut}`. Un seul par job.
- Un devis image ou voix (rendu immédiat) s'accepte avec le `fichier` rendu : le message `fait` `terminee`
  (`arguments` `{carte, fichier, statut: done}`) s'écrit aussitôt, avec la décision.

## Idempotence de l'import

`empreinte(message)` est le sha1 de `id`, `role` et `blocs`, en JSON trié (`quand`, `origine`, `appareil` et
`cout_paye` n'y entrent pas). Importer deux fois la même conversation (`POST .../importer`) ne crée aucun
doublon : un message dont l'empreinte est connue est ignoré, et un conflit n'écrase rien. Le coût déjà payé côté
téléphone est compté une seule fois.
