import json

import pytest

from main import MinecraftControlChanger


@pytest.fixture
def changer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = MinecraftControlChanger()
    c.config_path = str(tmp_path / "standardsettings.json")
    return c


def write_settings(changer, data):
    with open(changer.config_path, "w") as f:
        json.dump(data, f)


def test_random_mapping_has_one_unique_key_per_control(changer):
    mapping = changer.get_random_key_mapping()
    assert len(mapping) == len(changer.keys_to_change)
    assert len(set(mapping)) == len(mapping)
    assert set(mapping) <= set(changer.available_keys)


def test_load_returns_none_when_file_missing(changer):
    assert changer.load_current_settings() is None


def test_load_returns_none_for_invalid_json(changer):
    with open(changer.config_path, "w") as f:
        f.write("{not json")
    assert changer.load_current_settings() is None


def test_load_returns_dict_for_valid_file(changer):
    write_settings(changer, {"fov": 110.0})
    assert changer.load_current_settings() == {"fov": 110.0}


def test_change_controls_rewrites_keys_and_keeps_other_settings(changer, tmp_path):
    original = {"fov": 110.0, "key_key.chat": "key.keyboard.enter"}
    original.update({k: "key.keyboard.unknown" for k in changer.keys_to_change})
    write_settings(changer, original)

    changer.change_controls()

    with open(changer.config_path) as f:
        result = json.load(f)
    assert result["fov"] == 110.0
    assert result["key_key.chat"] == "key.keyboard.enter"
    new_keys = [result[k] for k in changer.keys_to_change]
    assert "key.keyboard.unknown" not in new_keys
    assert len(set(new_keys)) == len(new_keys)

    controls = (tmp_path / "controls.txt").read_text()
    assert f"jump: {result['key_key.jump'][4:]}" in controls
    assert changer.is_changing is False


def test_change_controls_aborts_cleanly_when_settings_missing(changer, capsys):
    changer.change_controls()

    assert "Aborting: could not load settings" in capsys.readouterr().out
    assert changer.is_changing is False
