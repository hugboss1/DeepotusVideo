# Library Image Management — Design (delete / favorite / rename)

> **Context:** The Library page (`um` component in the compiled bundle) lists Images, Renders, Audio, Favoris. Clicking an asset opens a modal. Images currently get **Download + Delete** only; renders also get a ☆ Favori toggle and "Rouvrir dans Studio" (gated on `m.jobId`). This adds **favorite** and **rename** for images, and keeps delete clearly available in the image view.

**Goal:** From the Library image view, the user can delete an image (already works), save it as a favorite, and rename it — rename matters most for images imported from another source.

**Tech stack:** FastAPI backend (one new route + a unit-tested helper, pytest) + compiled React bundle (count-guarded string patches, `node --check`, deploy). No change to the render/audio paths.

---

## 1. Backend — rename endpoint

New module-level helper in `routes.py`, unit-tested:

```
_safe_rename_image(old_name, new_name) -> str   # returns the final new filename
```
- `old` and `new` are reduced to bare names (`Path(x).name`) — no path traversal.
- The new name keeps the **original extension** (if the user omits or changes it, the original extension is enforced); the stem is sanitized to `[A-Za-z0-9._ -]` (others → `_`), trimmed, non-empty (fallback `image`).
- The source must exist under `images_path`; the destination must resolve inside `images_path`.
- **Collision:** if the destination already exists (and isn't the source), auto-suffix `_2`, `_3`, … before the extension.
- Renames the file (`Path.rename`) and returns the final filename.

Route: `POST /api/images/{filename}/rename`, body `{ "new_name": "..." }` → `{ "old": "...", "new": "..." }`; 404 if the source is missing, 400 if `new_name` is blank.

`DELETE /images/{filename}` is unchanged (already exists). No reference-rewrite: a rename changes the file only (per scope decision); references in already-saved renders/graphs are not touched.

## 2. Frontend — image favorites (`localStorage`)

Mirror the existing render-favorite helpers (`__dzFavGet/Has/Toggle` over `dz_fav_renders`) with an **image** set keyed by filename:
- `__dzFavImgGet()` → array of filenames (try/catch JSON over `localStorage.dz_fav_images`).
- `__dzFavImgHas(name)` / `__dzFavImgToggle(name)`.

Wire-up:
- **Image modal:** add a **☆/★ Favori** toggle (same style as the render one) in the image branch — visible when the modal item is an image (`!m.jobId && !m.audioFile`). Clicking toggles `__dzFavImgToggle(m.name)` and refreshes the modal item.
- **Favoris category:** today `T.Favoris = H.filter(z=>__dzFavHas(z.jobId))` (favorited renders). Extend it to also include favorited images: concatenate the Images list filtered by `__dzFavImgHas(name)`. So Favoris shows favorited renders **and** images.

## 3. Frontend — rename in the image view

In the image branch of the modal, make the filename editable:
- A small **✎ Rename** affordance next to the name (or an inline editable input). On submit it calls a new client method `D.renameImage(old, newName)` → `POST /api/images/{old}/rename`.
- On success: update the open modal item (`m.name`, `m.url`), update the grid list state (replace the renamed entry's `name`/`url`), and **migrate the favorite** — if `__dzFavImgHas(old)`, toggle old off and new on so the star is preserved.
- Empty/whitespace name is a no-op; the backend enforces extension + sanitization, and the UI uses whatever filename the backend returns (so a collision-suffixed name shows correctly).

## 4. Delete (unchanged, kept visible)

The image modal already deletes via `D.deleteImage(m.name)` (→ `DELETE /images/{filename}`) then filters the grid. It stays, grouped with the new Favori + Rename controls so all three image actions sit together in the view.

---

## Scope / non-goals
- **File-only rename** — no rewrite of references in existing renders/graphs.
- Favorites are **frontend-only** (localStorage), consistent with render favorites; no backend favorites store.
- No bulk operations (one image at a time, from its modal).
- No change to renders, audio, the Studio image picker, or import endpoints.

## Testing
- Backend: pytest for `_safe_rename_image` — extension enforced, sanitization, collision auto-suffix, traversal rejected. Plus a live route smoke (rename a throwaway image, GET it under the new name, 404 under the old).
- Frontend: browser — favorite an image (persists across reload, appears in Favoris), rename an image (grid + modal update, file served under new name, star preserved), delete still works. No console errors.
