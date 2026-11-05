import ctypes
import json
import os
import queue
import random
import threading
from ctypes import wintypes
from pathlib import Path

from dotenv import load_dotenv
from pynput import keyboard, mouse

load_dotenv()

SHUFFLE_INTERVAL_SECONDS = 60
STATE_POLL_SECONDS = 0.1
# state reported by the State Output mod while the player is in game with no menu open
ACTIVE_STATE = "inworld,unpaused"
RESHUFFLE_HOTKEY = "key.keyboard.page.up"
EXIT_HOTKEY = "key.keyboard.page.down"

# game actions whose physical key gets scrambled
ACTIONS = [
    "key_key.jump",
    "key_key.sneak",
    "key_key.sprint",
    "key_key.left",
    "key_key.right",
    "key_key.back",
    "key_key.forward",
    "key_key.attack",
    "key_key.pickItem",
    "key_key.use",
    "key_key.drop",
    "key_key.hotbar.1",
    "key_key.hotbar.2",
    "key_key.hotbar.3",
    "key_key.hotbar.4",
    "key_key.hotbar.5",
    "key_key.hotbar.6",
    "key_key.hotbar.7",
    "key_key.hotbar.8",
    "key_key.hotbar.9",
    "key_key.inventory",
    "key_key.swapOffhand",
    "key_key.screenshot",
    "key_key.smoothCamera",
    "key_key.togglePerspective",
]

# physical inputs that can be assigned to an action (and are blocked while unassigned)
AVAILABLE_KEYS = [
    "key.keyboard.q", "key.keyboard.w", "key.keyboard.e", "key.keyboard.r",
    "key.keyboard.t", "key.keyboard.y", "key.keyboard.u", "key.keyboard.i",
    "key.keyboard.o", "key.keyboard.p", "key.keyboard.a", "key.keyboard.s",
    "key.keyboard.d", "key.keyboard.f", "key.keyboard.g", "key.keyboard.h",
    "key.keyboard.j", "key.keyboard.k", "key.keyboard.l", "key.keyboard.z",
    "key.keyboard.x", "key.keyboard.c", "key.keyboard.v", "key.keyboard.b",
    "key.keyboard.n", "key.keyboard.m", "key.keyboard.space",
    "key.keyboard.left.shift", "key.keyboard.right.shift",
    "key.keyboard.left.control", "key.keyboard.right.control",
    "key.keyboard.left.alt", "key.keyboard.right.alt",
    "key.keyboard.tab", "key.keyboard.f1",
    "key.keyboard.f2", "key.keyboard.f3", "key.keyboard.f4",
    "key.keyboard.f5", "key.keyboard.f6", "key.keyboard.f7",
    "key.keyboard.f8", "key.keyboard.f9", "key.keyboard.f10",
    "key.keyboard.f12", "key.keyboard.1", "key.keyboard.2",
    "key.keyboard.3", "key.keyboard.4", "key.keyboard.5",
    "key.keyboard.6", "key.keyboard.7", "key.keyboard.8",
    "key.keyboard.9", "key.keyboard.0", "key.keyboard.insert",
    "key.keyboard.home", "key.mouse.left", "key.mouse.right",
    "key.mouse.middle", "key.mouse.4", "key.mouse.5",
]

# Minecraft key name -> Windows virtual key code
VK_CODES = {
    **{f"key.keyboard.{c}": ord(c.upper()) for c in "abcdefghijklmnopqrstuvwxyz0123456789"},
    **{f"key.keyboard.f{n}": 0x6F + n for n in range(1, 13)},
    "key.keyboard.space": 0x20,
    "key.keyboard.tab": 0x09,
    "key.keyboard.enter": 0x0D,
    "key.keyboard.escape": 0x1B,
    "key.keyboard.backspace": 0x08,
    "key.keyboard.caps.lock": 0x14,
    "key.keyboard.left.shift": 0xA0,
    "key.keyboard.right.shift": 0xA1,
    "key.keyboard.left.control": 0xA2,
    "key.keyboard.right.control": 0xA3,
    "key.keyboard.left.alt": 0xA4,
    "key.keyboard.right.alt": 0xA5,
    "key.keyboard.page.up": 0x21,
    "key.keyboard.page.down": 0x22,
    "key.keyboard.end": 0x23,
    "key.keyboard.home": 0x24,
    "key.keyboard.left": 0x25,
    "key.keyboard.up": 0x26,
    "key.keyboard.right": 0x27,
    "key.keyboard.down": 0x28,
    "key.keyboard.insert": 0x2D,
    "key.keyboard.delete": 0x2E,
    "key.keyboard.semicolon": 0xBA,
    "key.keyboard.equal": 0xBB,
    "key.keyboard.comma": 0xBC,
    "key.keyboard.minus": 0xBD,
    "key.keyboard.period": 0xBE,
    "key.keyboard.slash": 0xBF,
    "key.keyboard.grave.accent": 0xC0,
    "key.keyboard.left.bracket": 0xDB,
    "key.keyboard.backslash": 0xDC,
    "key.keyboard.right.bracket": 0xDD,
    "key.keyboard.apostrophe": 0xDE,
}
VK_TO_NAME = {vk: name for name, vk in VK_CODES.items()}
# keys that need the extended flag so the game can tell them apart from numpad/left keys
EXTENDED_VKS = {0xA3, 0xA5, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E}

# Minecraft mouse name -> (SendInput down flag, SendInput up flag, XBUTTON data)
MOUSE_BUTTONS = {
    "key.mouse.left": (0x0002, 0x0004, 0),
    "key.mouse.right": (0x0008, 0x0010, 0),
    "key.mouse.middle": (0x0020, 0x0040, 0),
    "key.mouse.4": (0x0080, 0x0100, 1),
    "key.mouse.5": (0x0080, 0x0100, 2),
}

WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
LLKHF_INJECTED = 0x10
LLMHF_INJECTED = 0x01
# mouse hook message -> (button name or None for XBUTTON, is_down)
MOUSE_MESSAGES = {
    0x201: ("key.mouse.left", True),
    0x202: ("key.mouse.left", False),
    0x204: ("key.mouse.right", True),
    0x205: ("key.mouse.right", False),
    0x207: ("key.mouse.middle", True),
    0x208: ("key.mouse.middle", False),
    0x20B: (None, True),
    0x20C: (None, False),
}


def decode_keyboard_event(msg, vk):
    """Return (key name, is_down) for a keyboard hook event, or (None, None) if unknown"""
    if msg in (WM_KEYDOWN, WM_SYSKEYDOWN):
        return VK_TO_NAME.get(vk), True
    if msg in (WM_KEYUP, WM_SYSKEYUP):
        return VK_TO_NAME.get(vk), False
    return None, None


def decode_mouse_event(msg, mouse_data):
    """Return (button name, is_down) for a mouse hook event, or (None, None) for moves/scrolls"""
    if msg not in MOUSE_MESSAGES:
        return None, None
    name, is_down = MOUSE_MESSAGES[msg]
    if name is None:
        xbutton = (mouse_data >> 16) & 0xFFFF
        name = {1: "key.mouse.4", 2: "key.mouse.5"}.get(xbutton)
    return name, is_down


def is_supported(key_name):
    return key_name in VK_CODES or key_name in MOUSE_BUTTONS


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def send_input(key_name, is_down):
    """Inject a key or mouse button press/release with the Win32 SendInput API"""
    user32 = ctypes.windll.user32
    event = INPUT()
    if key_name in MOUSE_BUTTONS:
        down_flag, up_flag, xbutton = MOUSE_BUTTONS[key_name]
        event.type = 0  # INPUT_MOUSE
        event.u.mi = MOUSEINPUT(0, 0, xbutton, down_flag if is_down else up_flag, 0, 0)
    else:
        vk = VK_CODES[key_name]
        flags = (0x0001 if vk in EXTENDED_VKS else 0) | (0 if is_down else 0x0002)
        event.type = 1  # INPUT_KEYBOARD
        event.u.ki = KEYBDINPUT(vk, user32.MapVirtualKeyW(vk, 0), flags, 0, 0)
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))


def get_foreground_window_title():
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buffer, 256)
    return buffer.value


class KeybindRandomizer:
    def __init__(self, settings_path, send=send_input):
        self.settings_path = Path(settings_path)
        # standardsettings.json lives in .minecraft/config/mcsr/
        self.state_path = self.settings_path.parents[2] / "wpstateout.txt"
        self.send = send
        self.binds = {}        # action -> key the game expects
        self.mapping = {}      # physical input -> action
        self.held = {}         # physical input -> injected key currently held down
        self.blocked = set()   # physical inputs whose press was swallowed
        self.active = False
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.injections = queue.Queue()

    def load_game_binds(self):
        """Read the game's binds for ACTIONS from standardsettings.json. Returns skipped actions."""
        with open(self.settings_path, "r", encoding="utf-8") as file:
            settings = json.load(file)
        self.binds = {}
        skipped = []
        for action in ACTIONS:
            key_name = settings.get(action)
            if key_name and is_supported(key_name):
                self.binds[action] = key_name
            else:
                skipped.append(action)
        return skipped

    def shuffle(self):
        """Assign every bound action a random unique physical input"""
        actions = list(self.binds)
        physical = random.sample(AVAILABLE_KEYS, len(actions))
        self.mapping = dict(zip(physical, actions))

    def write_controls_file(self, path="controls.txt"):
        lines = ["=" * 50, "MINECRAFT CONTROLS", "=" * 50, ""]
        by_action = {action: phys for phys, action in self.mapping.items()}
        for action in ACTIONS:
            if action in by_action:
                lines.append(f"{action[8:]}: {by_action[action][4:]}")
        with open(path, "w") as txt:
            txt.write("\n".join(lines) + "\n")
        print("\n".join(lines[4:]))

    def handle_input(self, name, is_down):
        """Remap one physical input. Returns True if the original event should be suppressed."""
        if is_down:
            if name in self.held:
                self.send_later(self.held[name], True)  # key auto-repeat
                return True
            if name in self.blocked:
                return True
            if not self.active or name not in AVAILABLE_KEYS:
                return False
            action = self.mapping.get(name)
            if action is None:
                self.blocked.add(name)
                return True
            target = self.binds[action]
            self.held[name] = target
            self.send_later(target, True)
            return True

        # releases follow whatever happened on press, even if the state or mapping changed since
        if name in self.held:
            self.send_later(self.held.pop(name), False)
            return True
        if name in self.blocked:
            self.blocked.discard(name)
            return True
        return False

    def send_later(self, key_name, is_down):
        # injecting from inside the hook callback can stall input, so a worker thread does it
        self.injections.put((key_name, is_down))

    def injection_worker(self):
        while True:
            item = self.injections.get()
            if item is None:
                return
            self.send(*item)

    def read_game_state(self):
        try:
            return self.state_path.read_text().strip()
        except OSError:
            return None

    def should_be_active(self):
        if not get_foreground_window_title().startswith("Minecraft"):
            return False
        state = self.read_game_state()
        # without the State Output mod, fall back to "Minecraft window is focused"
        return state is None or state == ACTIVE_STATE

    def state_watcher(self):
        while not self.stop_event.wait(STATE_POLL_SECONDS):
            self.active = self.should_be_active()

    def shuffle_loop(self):
        while not self.stop_event.is_set():
            self.shuffle()
            print("\n" + "=" * 50)
            print(f"New controls! Next change in {SHUFFLE_INTERVAL_SECONDS}s")
            print("=" * 50)
            self.write_controls_file()
            self.wake_event.wait(SHUFFLE_INTERVAL_SECONDS)
            self.wake_event.clear()

    def keyboard_filter(self, listener):
        def event_filter(msg, data):
            if data.flags & LLKHF_INJECTED:
                return True
            name, is_down = decode_keyboard_event(msg, data.vkCode)
            if name is None:
                return True
            if is_down and name == RESHUFFLE_HOTKEY:
                self.wake_event.set()
            elif is_down and name == EXIT_HOTKEY:
                self.stop()
            elif self.handle_input(name, is_down):
                listener().suppress_event()
            return True

        return event_filter

    def mouse_filter(self, listener):
        def event_filter(msg, data):
            if data.flags & LLMHF_INJECTED:
                return True
            name, is_down = decode_mouse_event(msg, data.mouseData)
            if name is not None and self.handle_input(name, is_down):
                listener().suppress_event()
            return True

        return event_filter

    def stop(self):
        self.stop_event.set()
        self.wake_event.set()

    def run(self):
        listeners = {}
        keyboard_listener = keyboard.Listener(win32_event_filter=self.keyboard_filter(lambda: listeners["kb"]))
        mouse_listener = mouse.Listener(win32_event_filter=self.mouse_filter(lambda: listeners["mouse"]))
        listeners.update(kb=keyboard_listener, mouse=mouse_listener)

        injector = threading.Thread(target=self.injection_worker, daemon=True)
        workers = [
            injector,
            threading.Thread(target=self.state_watcher, daemon=True),
            threading.Thread(target=self.shuffle_loop, daemon=True),
        ]
        keyboard_listener.start()
        mouse_listener.start()
        for worker in workers:
            worker.start()

        try:
            self.stop_event.wait()
        except KeyboardInterrupt:
            self.stop()
        finally:
            keyboard_listener.stop()
            mouse_listener.stop()
            # release anything still held so no key gets stuck down in the game
            for target in self.held.values():
                self.send_later(target, False)
            self.held.clear()
            self.injections.put(None)
            injector.join(timeout=2)
            print("\nExiting Minecraft 1.16.1 Keybind Randomizer...")


def main():
    print("=" * 60)
    print("MINECRAFT 1.16.1 KEYBIND RANDOMIZER")
    print("=" * 60)
    print(f"Your controls get scrambled every {SHUFFLE_INTERVAL_SECONDS} seconds while you play.")
    print("Scrambling only applies while Minecraft is focused and no menu is open.")
    print("=" * 60)

    settings_path = os.getenv("DIRECTORY_PATH")
    if not settings_path or not os.path.exists(settings_path):
        print(f"Error: settings file not found at {settings_path}. Check DIRECTORY_PATH in .env.")
        return

    randomizer = KeybindRandomizer(settings_path)
    try:
        skipped = randomizer.load_game_binds()
    except json.JSONDecodeError:
        print("Error: settings file is not valid JSON.")
        return
    if skipped:
        print(f"Not scrambling (unbound or unsupported key): {', '.join(a[8:] for a in skipped)}")
    if not randomizer.state_path.exists():
        print("Note: State Output mod not detected, scrambling whenever Minecraft is focused.")

    print("\nHotkeys:")
    print("Page Up   - Reshuffle now")
    print("Page Down - Exit program")
    randomizer.run()


if __name__ == "__main__":
    main()
