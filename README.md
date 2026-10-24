# Focus Available Notifications

Hearts of Iron IV does not tell you when a national focus becomes available. This mod does.

Notifications are off at the start of a new game. A **Focus Notifications** decision section has two decisions:

- **Enable Focus Available Notifications**
- **Disable Focus Available Notifications**

While notifications are on, each national focus that becomes available opens an event titled **New Focus Available**. The text is **The focus X is now available**, where X is the focus name already used by the game (so it follows the language you are playing in).

Enabling it also opens one event for every focus that is already available. Each focus is remembered after its event fires. Turning notifications off and on again does not repeat events you have already been shown. A focus that became available while notifications were off, and that you have not been shown, is reported the next time you enable them.

The check runs when you click enable, and again at each daily tick while notifications stay on. It only runs for a country you are playing.

## Separate mods

`vanilla` and `owb` are separate mods. Each one is built only from that game's own focus files, so another mod's focus edits are not mixed in.

| Keyword | Mod name | Depends on | Built from |
| --- | --- | --- | --- |
| `vanilla` | Focus Available Notifications | nothing | the Hearts of Iron IV install |
| `owb` | Focus Available Notifications - Old World Blues | Old World Blues | that workshop mod only |

Enable the one that matches the game you are playing. Both can be enabled together: the decisions, events, and flags use different ids, so they do not overwrite each other or the focus trees. In an Old World Blues game the vanilla trees are not loaded, so leave the vanilla Enable decision off. Clicking it looks up missing trees, writes those lookups to error.log, and reports nothing.

```
pip install -r requirements.txt
python tools/build.py vanilla owb
python tools/deploy_local_mod.py vanilla owb
```

Each built mod reports focuses from that parent's own trees, assuming no submod changes those trees. `python tools/build.py` lists playset mods that ship national focus files and are not a target yet. Adding one is a new keyword in this repo, with that mod's display name in `dependencies`. Pull requests for those parents are welcome.

`mods/` is build output. It is not committed. Rebuild after a game update or an Old World Blues update so the checks match the focus trees you have installed.

## Images

| Use | Path | Size | Format | Max file |
| --- | --- | --- | --- | --- |
| Launcher / Workshop preview | `assets/<keyword>/thumbnail.png` | **512×512**, 1:1 | PNG | 1 MB |
| Workshop gallery | `screenshots/<keyword>/` | **1920×1080**, 16:9 | PNG or JPG | 1 MB |

The thumbnails in the repo are placeholders. Replace either file, or drop gallery shots in `screenshots/vanilla/` and `screenshots/owb/`, then run:

```
python tools/resize_workshop_images.py
python tools/build.py vanilla owb
```

The resize script center-crops to the target aspect, scales, and keeps the file under 1 MB. Rebuild so the new thumbnail is copied into the mod. Screenshots are not deployed.

Steam Workshop copy-paste text is in [`workshop.txt`](workshop.txt). Implementation notes for later changes are in [`CLAUDE.md`](CLAUDE.md).

## Licence

Code, tools, and the generated script are under the MIT licence ([LICENSE](LICENSE)).

Thumbnails and screenshots are under CC0 1.0 ([ASSETS_LICENCE.md](ASSETS_LICENCE.md)).
