# mc-random-keybinds

Scrambles your Minecraft 1.16.1 controls every 60 seconds while you play. The script sits between your keyboard/mouse and the game: when you press a physical key, it blocks that key and sends the game whichever key is bound to the action currently assigned to it. Your actual game binds and settings files are never modified.

## How it works

- Every 60 seconds, each action (jump, sneak, sprint, movement, attack, use, hotbar slots, inventory and so on) gets a random physical input from the list of available keys, which includes mouse buttons.
- Available keys that are not assigned to any action are blocked, so your normal binds stop working while scrambled.
- Keys outside the available list (Esc, Enter, slash and others) always work normally.
- Scrambling only applies while the Minecraft window is focused and you are in a world with no menu open. Menus, chat, the pause screen and other windows use your normal controls. Game state is read from the State Output mod's `wpstateout.txt` (included in MCSR packs). Without that mod, scrambling applies whenever Minecraft is focused.
- The current mapping is printed in the terminal and saved to `controls.txt` after each shuffle.

## Requirements

- Windows (the remapper uses Win32 input hooks)
- Python 3
- Minecraft 1.16.1 with the StandardSettings mod (for example, an MCSR instance in MultiMC)

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Find your `standardsettings.json` file. It is usually at `.minecraft/config/mcsr/standardsettings.json` inside your instance folder. The script reads your binds from it and expects this folder layout to locate `wpstateout.txt`.
4. Create a `.env` file in the project root with the full path to that file:
   ```
   DIRECTORY_PATH='C:\Users\you\Desktop\MultiMC\instances\1.16.1\.minecraft\config\mcsr\standardsettings.json'
   ```
   Wrap the path in **single quotes** or use forward slashes (`C:/Users/you/...`). Inside double quotes, python-dotenv reads backslashes as escape characters (for example, `\r` in `\rattl` becomes a carriage return), and the file will not be found.

## Usage

Start the script (Minecraft can be open or closed):

```bash
python main.py
```

Then play. Controls reshuffle every 60 seconds.

| Key       | Action |
| --------- | ------ |
| Page Up   | Reshuffle now |
| Page Down | Exit the program |

To change the interval, edit `SHUFFLE_INTERVAL_SECONDS` in `main.py`. To change which actions or physical keys are used, edit `ACTIONS` or `AVAILABLE_KEYS`.

## Development

Install the dev dependencies and enable the pre-push hook:

```bash
pip install -r requirements-dev.txt
git config core.hooksPath .githooks
```

The hook in `.githooks/pre-push` runs `pytest` with the `.venv` interpreter and blocks the push if any test fails. To run the tests manually:

```bash
python -m pytest
```

## Troubleshooting

- **"Settings file not found"**: check that `DIRECTORY_PATH` in `.env` points to an existing file and is quoted as described above.
- **"Not scrambling: ..."**: those actions are unbound (`key.keyboard.unknown`) or use a key the script does not recognize. Bind them in game to include them.
- **Controls never scramble**: the script checks that the focused window title starts with "Minecraft". Make sure the game window is focused and you are in a world with no menu open.
- **A key feels stuck after exiting**: press and release it once. The script releases held keys on exit, but closing the terminal window directly skips that step.
