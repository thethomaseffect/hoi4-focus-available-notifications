# Focus Available Notifications

This git repo is the source of truth. Hearts of Iron IV does not load it. `tools/build.py` writes one mod per keyword into `mods/<keyword>/`. `tools/deploy_local_mod.py` mirrors that folder into the local mods directory and updates the same slug on every later deploy.

## How HOI4 local mods work

The launcher only reads `.mod` files in:

`C:/Users/[replace with username]/Documents/Paradox Interactive/Hearts of Iron IV/mod`

```
Documents/Paradox Interactive/Hearts of Iron IV/mod/
  focus_available_notifications.mod
  focus_available_notifications/
    descriptor.mod
    thumbnail.png
    common/ ...
```

- `mods/<keyword>/descriptor.mod` has **no** `path` and **no** `replace_path`.
- The Documents `*.mod` is the launcher pointer: same metadata plus `path=` with **forward slashes**, and the display name gets ` (local)` so it does not collide with a Workshop item.
- `dependencies` are exact display names (`"Old World Blues"`), not folder names or Steam IDs.
- If the Documents copy already has `remote_file_id`, deploy keeps it on the inner `descriptor.mod` only. The launcher pointer does not get `remote_file_id`.
- Do not set `replace_path`. It wipes that folder for every earlier mod.

| Keyword | Slug | Display name | Depends on |
| --- | --- | --- | --- |
| `vanilla` | `focus_available_notifications` | Focus Available Notifications | none |
| `owb` | `focus_available_notifications_owb` | Focus Available Notifications - Old World Blues | Old World Blues |

Old World Blues uses `replace_path` on `common/national_focus`, `common/decisions`, `common/on_actions`, `common/scripted_effects`, and `events`. That wipe does not apply to mods loaded **after** it. The OWB notification mod must depend on `"Old World Blues"` so its added files survive. It must not contain focus files of its own.

Supported version is read from the install `launcher-settings.json` `rawVersion` at build time.

```
python tools/build.py vanilla
python tools/build.py owb
python tools/deploy_local_mod.py vanilla
python tools/deploy_local_mod.py owb
```

Deploy only the keyword that matches the playset. Enable the local copy, not a Workshop item of the same name, until you upload it.

Both built mods can be enabled in one playset. `fanv_` and `fano_` ids do not collide, and neither mod ships `common/national_focus` or `replace_path`. Old World Blues does use `replace_path` on decisions, events, on_actions, and scripted effects, which removes copies of those files from mods loaded above it. Put the vanilla notification mod below Old World Blues if it should remain present. Its scan reads a vanilla focus id only after `fanv_enabled` is set. With the vanilla Enable decision left off, that lookup never runs.

## Why targets are separate

`targets.json` lists keywords. Each keyword has explicit `layers`:

- `install` reads only `Hearts of Iron IV/common/national_focus`
- `workshop` reads only `workshop/content/394360/<id>/common/national_focus`
- `path` reads a folder (absolute, or relative to the repo)

Later layers in one target replace earlier files with the same relative path. Vanilla is not an implicit base. OWB replaces the focus database, so the `owb` target lists only the Old World Blues workshop id `2265420196`.

Do not build by walking the active playset. Another mod's focus file would be baked into the wrong notification mod. `tools/build.py` prints playset mods that have `common/national_focus` files, or `replace_path="common/national_focus"`, and are not already a target. Leave them alone until the user picks one. A new parent is a new keyword, a new slug, a new display name, and `dependencies` set to that parent's exact display name. If the parent only overwrites some files, list the parent layer first and the submod layer second.

## What "available" means

There is no script trigger that asks the game if a focus can be started. The build copies the conditions into a generated check.

A focus is reported when all of these are true:

- It belongs to the country's current focus tree (`has_focus_tree`), including a `shared_focus` or `joint_focus` id that tree references. Inline `focus`, `shared_focus`, and `joint_focus` blocks in the tree count too.
- This mod has not already fired its event (`<prefix>_seen_<focus id>` country flag).
- It is not completed and not in progress (`has_completed_focus`, `focus_progress > 0`). Bypassed focuses count as completed.
- Every `prerequisite` block has at least one listed focus completed. Focuses inside one block are OR. Separate blocks are AND.
- No `mutually_exclusive` focus is completed or in progress.
- `allow_branch` and `available` are true. Those blocks are copied as text, with file-level `@constants` substituted.
- `bypass` is not true. A bypassed focus cannot be selected.
- The country has not capitulated, unless `available_if_capitulated = yes`.

Skipped and given no event:

- `allow_branch = { always = no }`
- `available = { always = no }`
- `bypass = { always = yes }`

`always = yes` blocks and `bypass = { always = no }` are omitted as noise. Cost, position, rewards, and `ai_will_do` are ignored. Continuous focuses (`common/continuous_focus`) are not national focuses and are not included.

The seen flag is set when the event is fired, not when the option is clicked. Disable only clears `<prefix>_enabled`. It does not clear seen flags. The event is also `fire_only_once`, so the same popup cannot be produced again in that save. A new game clears both.

The enable decision sets the flag and runs the scan inside `hidden_effect`, then shows a one-line tooltip. The scan must stay hidden: a visible tooltip would expand every generated check. `on_daily` calls the same scan. The scan returns immediately unless the country `is_ai = no` and the enabled flag is set. Only the active focus tree's effect runs.

Each focus has its own country event. One shared event id would be wrong: the game resolves the description when the popup opens, so every queued copy would show whichever focus was stored last. The title loc is `New Focus Available`. The description is `The focus $FOCUS_ID$ is now available.` The `$FOCUS_ID$` loc key is the game's own focus name.

Prefixes are `fanv` (vanilla) and `fano` (Old World Blues): decision category, flags, effects, and event namespaces. Generated script is rebuilt from scratch. `mods/` is gitignored build output. Do not hand-edit it.

## Images

| Use | Path | Size | Notes |
| --- | --- | --- | --- |
| Launcher / Workshop preview | `assets/<keyword>/thumbnail.png`, copied to the mod root as `thumbnail.png` | **512×512** PNG, 1:1, under 1 MB | The launcher rejects a bad thumbnail without a useful error. |
| Workshop gallery | `screenshots/<keyword>/` | **1920×1080**, 16:9, under 1 MB | Not deployed. |

`python tools/make_placeholder_thumbnails.py` redraws the placeholders. `python tools/resize_workshop_images.py` center-crops and recompresses thumbnails and screenshots. Run the resize script after a replacement image is added, then rebuild. Workshop paragraphs live in `workshop.txt` and are not deployed.

## Tests

```
python -m unittest tests.test_focuses
```

The fixture covers OR/AND prerequisites, shared focuses, capitulation, constant substitution, dead branches, seen flags, and brace balance.

## Debug logs (when the game crashes)

Logs are written automatically. `-debug` on the Steam launch options makes them complete.

`C:/Users/[replace with username]/Documents/Paradox Interactive/Hearts of Iron IV/logs/`

That folder is overwritten every launch. CTD copies go to `.../Hearts of Iron IV/crashes/hoi4_YYYYMMDD_HHMMSS/`.

When reporting a crash, send:

1. `logs/error.log` — script problems. Invalid focus ids in a generated check show up here.
2. `logs/exceptions.log` — CTD stack
3. `logs/setup.log` — last thing that finished loading
4. The matching `crashes/hoi4_*` folder if it exists

Optional: add `-crash_data_log` only while reproducing a CTD. It writes `LastRead:` into `meta.yml` in the documents folder and is slow.

## Licence

- **MIT** ([LICENSE](LICENSE)): code, tools, and generated HOI4 script.
- **CC0 1.0** ([ASSETS_LICENCE.md](ASSETS_LICENCE.md)): `assets/` and `screenshots/`.
