<p align="center">
  <img src="assets/logo.png" alt="Palworld Editor" width="360">
</p>

<h1 align="center">Palworld Editor</h1>

<p align="center">
  Modern save editor for <b>Palworld (Xbox / Microsoft Store / Game Pass build)</b> — items, character and Pals.
  <br>
  <a href="README.pt-BR.md">🇧🇷 Portugues</a> · <b>🇺🇸 English</b>
</p>

---

> **Unofficial tool.** Not affiliated with Pocketpair. Use only with a save from a game you own. See [NOTICE](NOTICE.md).

## Features

- **Items** — edit any quantity, add items you don't have, per chest / storage / inventory, with in-game names and icons.
- **Character** — level, experience and status points.
- **Pals** — level, gender, IVs (HP/Attack/Defense), soul rank and the 4 passive skills, with a "suggest best passives" helper.
- **Day / night** modern theme (Windows 11 Fluent).
- **Automatic backups** and one-click restore. An untouched copy of your original save is kept forever.

This build targets the **Xbox/GDK** version of Palworld (the one whose saves live under
`%LOCALAPPDATA%\Packages\PocketpairInc.Palworld_*`), which the common Steam editors do not read.

## Install (Windows)

Open **PowerShell** and run:

```powershell
git clone https://github.com/disouz4-dev/Palworld-Edit.git
cd Palworld-Edit
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer checks for **Python** (installs it if missing), installs the
dependencies and creates a **Desktop shortcut** with the app icon. Then just
open **Palworld Editor** from your Desktop.

> No git? Download the ZIP from the green **Code** button on GitHub, extract it,
> then run `install.ps1` inside the folder.

## Usage

1. **Close Palworld** before saving (the game overwrites the save on exit).
2. Open the app, pick your world.
3. Edit in **Items / Character / Pals**, then click **SAVE TO GAME**.
4. If anything goes wrong in-game, use **Restore backup** on the home screen.

## Optional: regenerate names/icons from the game

The Portuguese names ship with the repo. Icons and other languages are generated
from your own game files (they are game content and are not redistributed). This
needs the **Oodle** DLL (the one FModel downloads from Epic's official source).
Create `extracao_local.json` in the project root:

```json
{
  "paks":  "X:\...\Palworld\Pal\Content\Paks",
  "oodle": "X:\...\oodle-data-shared.dll"
}
```

Then run the scripts in `tools/` (`extrair_traducao.py`, `icones.py`).

## How it works

The Xbox save is four nested layers, all decoded from scratch in Python:
`containers.index (WGS) → container.N → CNK0 → PlZ2 (double zlib) → GVAS`.
The reader/writer round-trips the save **byte-for-byte** when nothing is edited.
Item/Pal names and icons are read directly from the game's IoStore
(`.utoc`/`.ucas`) using the Oodle decompressor — no FModel export needed.

## License

[MIT](LICENSE). Names and artwork belong to Pocketpair — see [NOTICE](NOTICE.md).
