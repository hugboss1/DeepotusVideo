# Deepotus Video Gen — Migration vers un autre PC / Move to another PC

Transférer **l'app (avec toutes les nouveautés), toutes tes générations, le calendrier et les posts planifiés, et tes clés API** vers un autre portable — sans interrompre le planning.

Ce qui est transféré :
- **L'application** (code + runtime Python + ffmpeg + les nouveautés : node **Effects/Mask**, bouton **Preview**, miniatures d'effets, fix des overlays, etc.).
- **Toutes tes générations** (`assets/outputs`, images, audio, graphes Studio).
- **La base** `deepotus.db` : jobs, **calendrier + posts planifiés (Scheduler)**, préférences.
- **Tes clés** (`.env` : fal, ElevenLabs, HeyGen, OpenAI, Anthropic, X, Telegram).
- **Tes sessions & chats Claude Code** (`claude-home` dans le kit, si exporté avec `-IncludeClaude`).
- **L'installateur** `DeepotusVideoGen-Setup-1.15.8.exe` (joint au kit) pour une install propre sur une 3e machine.

> ⚠️ **Ne fais PAS tourner l'app sur les deux PC en même temps** → risque de double-publication des posts planifiés. Une fois migré, utilise le nouveau portable ; garde l'ancien fermé.
> ✅ **Idéal : même nom d'utilisateur Windows** sur les deux PC (les chemins des rendus correspondent). Sinon, le script d'import réécrit les chemins automatiquement.

---

## Méthode A — Scripts (recommandé)

**Sur CE PC** (source), avec un disque externe / clé USB branché (ex. `E:`), OU un dossier cloud synchronisé :
```powershell
powershell -ExecutionPolicy Bypass -File .\export-migration.ps1 -Dest "E:\deepotus-transfer"
```
- ~2,4 Go (dont 1,9 Go de rendus). Pour un transfert léger sans les rendus : ajoute `-SkipOutputs`.
- Le script copie l'app + les données + un **snapshot cohérent** de la base, et pose `import-migration.ps1` + ce guide dans le dossier.

**Sur le NOUVEAU portable**, copie `E:\deepotus-transfer` en local (ou branche le disque), puis **double-clique `IMPORT-TOUT.cmd`** à la racine du dossier : il restaure **tout en un clic** (app + données + calendrier + clés + sessions Claude Code), vérifie l'espace disque, réécrit les chemins si l'utilisateur diffère et recrée le raccourci.
   (Équivalent manuel : `powershell -ExecutionPolicy Bypass -File .\import-migration.ps1 -Src "E:\deepotus-transfer"`.)
- **Lance « Deepotus Video Gen »** (Bureau / Menu Démarrer). Vérifie : Library = tes rendus, Scheduler = tes posts planifiés, Settings = tes clés.

---

## Méthode B — Copie manuelle (si les scripts posent souci)

1. **Ferme l'app** sur ce PC.
2. Copie ces **deux dossiers** vers le disque de transfert :
   - `%LOCALAPPDATA%\DeepotusVideoGen`  (l'app + les nouveautés)
   - `%LOCALAPPDATA%\DeepotusVideoGenData`  (données + calendrier + clés)
   > `%LOCALAPPDATA%` = `C:\Users\<toi>\AppData\Local`
3. Sur le nouveau portable, colle-les aux **mêmes emplacements** `%LOCALAPPDATA%\`.
4. Recrée le raccourci : lance
   `%LOCALAPPDATA%\DeepotusVideoGen\scripts\create-desktop-shortcut.ps1`
   (clic droit → Exécuter avec PowerShell), ou double-clic sur
   `%LOCALAPPDATA%\DeepotusVideoGen\scripts\launch-silent.vbs`.

---

## Méthode C — Installation propre + données (utilisateur Windows différent)

Si le nouveau portable a un **autre nom d'utilisateur** et que tu préfères une base saine :
1. Installe avec `DeepotusVideoGen-Setup-1.15.8.exe` (joint à ce kit, aussi dans `Bureau\DeepotusVideoGen-Export`) — il contient **déjà toutes les nouveautés**.
2. Copie le dossier de données `DeepotusVideoGenData` (Méthode B, étape 2-3).
3. Les chemins des anciens rendus pointant vers l'ancien utilisateur : lance
   `import-migration.ps1 -Src <dossier contenant _migration-info.txt>` pour les réécrire,
   ou régénère au besoin.

---

## Le planning continue-t-il ?

Oui : le **Scheduler s'exécute quand l'app tourne**. Sur le nouveau portable, tant que l'app est **lancée** aux heures prévues, tes posts planifiés partent normalement (les mêmes 119 posts que sur ce PC). En voyage, garde l'app ouverte (ou lance-la avant les heures de publication). L'ancien PC doit rester **fermé** pour éviter les doublons.

---

# ENGLISH

Move **the app (with all new features), every generation, the calendar + scheduled posts, and your API keys** to another laptop — without interrupting the schedule.

**Transferred:** the application (code + Python runtime + ffmpeg + new features: **Effects/Mask** node, **Preview** button, effect thumbnails, overlay fix…), all generations (`assets/outputs`, images, audio, Studio graphs), the `deepotus.db` database (jobs, **calendar + scheduled posts**, preferences), and your `.env` keys (fal, ElevenLabs, HeyGen, OpenAI, Anthropic, X, Telegram).

> ⚠️ **Do NOT run the app on both PCs at once** → scheduled posts could double-publish. After moving, use the new laptop; keep the old one closed.
> ✅ **Best: same Windows username** on both PCs (render paths match). Otherwise the import script rewrites paths automatically.

### Method A — Scripts (recommended)
On **THIS PC**, with a USB/external drive (e.g. `E:`):
```powershell
powershell -ExecutionPolicy Bypass -File .\export-migration.ps1 -Dest "E:\deepotus-transfer"
```
(~2.4 GB; add `-SkipOutputs` to skip the 1.9 GB of renders.)
On the **NEW laptop**: **double-click `IMPORT-TOUT.cmd`** at the root of the folder — one click restores app + data + calendar + keys + Claude Code sessions. (Manual equivalent: `powershell -ExecutionPolicy Bypass -File .\import-migration.ps1 -Src "E:\deepotus-transfer"`.)
Then launch **“Deepotus Video Gen”** and check Library / Scheduler / Settings.

### Method B — Manual copy
Close the app, copy `%LOCALAPPDATA%\DeepotusVideoGen` and `%LOCALAPPDATA%\DeepotusVideoGenData` to the same paths on the new PC, then run `scripts\create-desktop-shortcut.ps1`.

### Does the schedule keep running?
Yes — the Scheduler runs while the app is open. Keep the app running on the new laptop around the posting times; keep the old PC closed to avoid duplicates.
