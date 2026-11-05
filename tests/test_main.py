import json

import pytest

from main import (
    ACTIONS,
    AVAILABLE_KEYS,
    WM_KEYDOWN,
    WM_KEYUP,
    WM_SYSKEYDOWN,
    KeybindRandomizer,
    decode_keyboard_event,
    decode_mouse_event,
    is_supported,
)


@pytest.fixture
def settings_file(tmp_path):
    path = tmp_path / ".minecraft" / "config" / "mcsr" / "standardsettings.json"
    path.parent.mkdir(parents=True)
    binds = {action: "key.keyboard.unknown" for action in ACTIONS}
    binds.update({
        "fov": 110.0,
        "key_key.forward": "key.keyboard.w",
        "key_key.jump": "key.keyboard.space",
        "key_key.attack": "key.mouse.left",
        "key_key.hotbar.9": "key.mouse.4",
    })
    path.write_text(json.dumps(binds))
    return path


@pytest.fixture
def randomizer(settings_file):
    sent = []
    r = KeybindRandomizer(settings_file, send=lambda key, down: sent.append((key, down)))
    r.load_game_binds()
    r.sent = sent
    return r


def drain(r):
    """Run queued injections synchronously and return them"""
    r.injections.put(None)
    r.injection_worker()
    return r.sent


def test_every_available_key_is_supported():
    assert all(is_supported(k) for k in AVAILABLE_KEYS)
    assert len(set(AVAILABLE_KEYS)) == len(AVAILABLE_KEYS)


def test_state_path_is_in_minecraft_folder(randomizer, settings_file):
    assert randomizer.state_path == settings_file.parents[2] / "wpstateout.txt"


def test_load_skips_unbound_actions(randomizer):
    assert randomizer.binds == {
        "key_key.forward": "key.keyboard.w",
        "key_key.jump": "key.keyboard.space",
        "key_key.attack": "key.mouse.left",
        "key_key.hotbar.9": "key.mouse.4",
    }


def test_shuffle_gives_each_action_a_unique_available_input(randomizer):
    randomizer.shuffle()
    assert sorted(randomizer.mapping.values()) == sorted(randomizer.binds)
    assert set(randomizer.mapping) <= set(AVAILABLE_KEYS)


def test_decode_keyboard_event():
    assert decode_keyboard_event(WM_KEYDOWN, 0x57) == ("key.keyboard.w", True)
    assert decode_keyboard_event(WM_SYSKEYDOWN, 0xA4) == ("key.keyboard.left.alt", True)
    assert decode_keyboard_event(WM_KEYUP, 0xA1) == ("key.keyboard.right.shift", False)
    assert decode_keyboard_event(WM_KEYDOWN, 0xFF) == (None, True)


def test_decode_mouse_event():
    assert decode_mouse_event(0x201, 0) == ("key.mouse.left", True)
    assert decode_mouse_event(0x205, 0) == ("key.mouse.right", False)
    assert decode_mouse_event(0x20B, 1 << 16) == ("key.mouse.4", True)
    assert decode_mouse_event(0x20C, 2 << 16) == ("key.mouse.5", False)
    assert decode_mouse_event(0x200, 0) == (None, None)  # mouse move


def test_assigned_input_sends_the_game_bind(randomizer):
    randomizer.mapping = {"key.keyboard.k": "key_key.jump"}
    randomizer.active = True

    assert randomizer.handle_input("key.keyboard.k", True) is True
    assert randomizer.handle_input("key.keyboard.k", True) is True  # auto-repeat
    assert randomizer.handle_input("key.keyboard.k", False) is True
    assert drain(randomizer) == [
        ("key.keyboard.space", True),
        ("key.keyboard.space", True),
        ("key.keyboard.space", False),
    ]


def test_unassigned_available_input_is_blocked(randomizer):
    randomizer.mapping = {"key.keyboard.k": "key_key.jump"}
    randomizer.active = True

    assert randomizer.handle_input("key.keyboard.w", True) is True
    assert randomizer.handle_input("key.keyboard.w", False) is True
    assert drain(randomizer) == []


def test_keys_outside_available_list_pass_through(randomizer):
    randomizer.active = True
    assert randomizer.handle_input("key.keyboard.escape", True) is False
    assert randomizer.handle_input("key.keyboard.escape", False) is False


def test_inactive_inputs_pass_through(randomizer):
    randomizer.mapping = {"key.keyboard.k": "key_key.jump"}
    randomizer.active = False

    assert randomizer.handle_input("key.keyboard.k", True) is False
    assert randomizer.handle_input("key.keyboard.k", False) is False
    assert drain(randomizer) == []


def test_release_after_going_inactive_still_releases_injected_key(randomizer):
    randomizer.mapping = {"key.mouse.right": "key_key.forward"}
    randomizer.active = True
    randomizer.handle_input("key.mouse.right", True)

    randomizer.active = False
    randomizer.mapping = {}
    assert randomizer.handle_input("key.mouse.right", False) is True
    assert drain(randomizer) == [("key.keyboard.w", True), ("key.keyboard.w", False)]


def test_controls_file_lists_new_bindings(randomizer, tmp_path):
    randomizer.mapping = {"key.keyboard.k": "key_key.jump", "key.mouse.5": "key_key.attack"}
    out = tmp_path / "controls.txt"
    randomizer.write_controls_file(out)

    text = out.read_text()
    assert "jump: keyboard.k" in text
    assert "attack: mouse.5" in text


def test_should_be_active_requires_focus_and_in_world_state(randomizer, monkeypatch):
    monkeypatch.setattr("main.get_foreground_window_title", lambda: "Minecraft* 1.16.1")
    randomizer.state_path.write_text("inworld,unpaused")
    assert randomizer.should_be_active() is True

    randomizer.state_path.write_text("inworld,paused")
    assert randomizer.should_be_active() is False

    randomizer.state_path.write_text("inworld,unpaused")
    monkeypatch.setattr("main.get_foreground_window_title", lambda: "Discord")
    assert randomizer.should_be_active() is False


def test_should_be_active_without_state_mod_uses_focus_only(randomizer, monkeypatch):
    monkeypatch.setattr("main.get_foreground_window_title", lambda: "Minecraft* 1.16.1")
    assert randomizer.should_be_active() is True
