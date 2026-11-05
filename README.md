# mc-random-keybinds

Randomizes your Minecraft 1.16.1 keybinds with a single hotkey. The script edits the `standardsettings.json` file used by the StandardSettings mod, so the new controls apply the next time the game loads them.

## Requirements

- Python 3
- Minecraft 1.16.1 with the StandardSettings mod (for example, an MCSR instance in MultiMC)

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate   # Windows (Git Bash)
   source .venv/bin/activate       # macOS/Linux
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Find your `standardsettings.json` file. It is usually at `.minecraft/config/mcsr/standardsettings.json` inside your instance folder.
4. Create a `.env` file in the project root with the full path to that file:
   ```
   DIRECTORY_PATH='C:\Users\you\Desktop\MultiMC\instances\1.16.1\.minecraft\config\mcsr\standardsettings.json'
   ```
   Wrap the path in **single quotes** or use forward slashes (`C:/Users/you/...`). Inside double quotes, python-dotenv reads backslashes as escape characters (for example, `\r` in `\rattl` becomes a carriage return), and the file will not be found.

## Usage

Close Minecraft, then run:

```bash
python main.py
```

| Key | Action |
| --- | ------ |
| F2  | Randomize controls |
| F3  | Exit the program |

Each randomization writes the new bindings to `standardsettings.json` and saves a readable list of them to `controls.txt` in the project folder.

## Troubleshooting

- **"Config file not found"** or **"Aborting: could not load settings"**: check that `DIRECTORY_PATH` in `.env` points to an existing file and is quoted as described above.
- **"Config file is not valid JSON"**: the settings file is corrupted. Restore it from a backup or let the mod regenerate it.
