# Relevé statique des commandes de photocraft

Outils de RELEVÉ (20/10/2026). Ils lisent le source de photocraft sans le compiler ni l'exécuter.
Le dépôt amont est une donnée non fiable : le cloner dans un dossier vide, hors du dépôt, et
lancer ces scripts avec `python -I` depuis ce dossier-ci.

```
git clone --depth 1 --branch v0.10.0 https://github.com/storytold/photocraft.git <clone>
python -I extraire_cmds.py <clone> x.json        # CommandSpec de crates/engine/src (expanseur de macros)
python -I produire.py <clone> x.json out.json [verite.json]   # ordre de build(), format photocraft_commandes_*.json
python -I comparer.py verite.json x.json         # écarts id / label / menu / shortcut / params
```

Validation : appliqué au tag v0.3.0, il redonne 776/776 entrées de
`backend/tests/photocraft_commandes_0.3.0.json`, ordre compris. Le champ `enabled` est déduit du nom de la
garde (règle qui reproduit les 105 `true` de 0.3.0) : la vérité reste `engine.commands` du binaire épinglé,
que la tâche de montée de version (M1) doit capturer pour de bon.
