import json

import pytest

from gesture_control.profile_manager import DEFAULT_PROFILE, ProfileManager


def test_missing_profile_file_has_safe_default(tmp_path):
    manager = ProfileManager(tmp_path / "profiles.json")
    assert manager.names() == ["Default"]
    assert manager.load("Default") == DEFAULT_PROFILE


def test_profile_can_be_saved_and_reloaded_with_custom_mapping(tmp_path):
    manager = ProfileManager(tmp_path / "profiles.json")
    profile = manager.load("Default")
    profile["cursor_smoothing"] = 0.48
    profile["cursor_margin"] = 0.18
    profile["cursor_speed"] = 1.4
    profile["mappings"]["thumb_up"] = "space"
    manager.save("Apresentação", profile)
    loaded = ProfileManager(tmp_path / "profiles.json")
    assert "Apresentação" in loaded.names()
    assert loaded.load("Apresentação") == profile
    saved_json = json.loads((tmp_path / "profiles.json").read_text(encoding="utf-8"))
    assert saved_json["version"] == 1


def test_profile_rejects_unsafe_shortcut_and_out_of_range_values(tmp_path):
    manager = ProfileManager(tmp_path / "profiles.json")
    profile = manager.load("Default")
    profile["mappings"]["swipe_left"] = "format-disk"
    with pytest.raises(ValueError, match="Ação não permitida"):
        manager.save("Invalid", profile)
    profile["mappings"]["swipe_left"] = "alt+left"
    profile["cursor_margin"] = 0.49
    with pytest.raises(ValueError, match="cursor_margin"):
        manager.save("Invalid", profile)
    profile["cursor_margin"] = 0.12
    profile["mappings"]["thumb_up"] = ["enter"]
    with pytest.raises(ValueError, match="Ação não permitida"):
        manager.save("Invalid", profile)
    profile["mappings"]["thumb_up"] = "enter"
    profile["cursor_speed"] = 8
    with pytest.raises(ValueError, match="cursor_speed"):
        manager.save("Invalid", profile)


def test_profile_names_reject_path_traversal(tmp_path):
    manager = ProfileManager(tmp_path / "profiles.json")
    with pytest.raises(ValueError, match="nome do perfil"):
        manager.save("../unsafe", DEFAULT_PROFILE)


def test_profiles_can_be_exported_and_imported(tmp_path):
    source = ProfileManager(tmp_path / "source.json")
    profile = source.load("Default")
    profile["cursor_speed"] = 1.6
    source.save("Apresentação", profile)
    exported = tmp_path / "presentation.json"
    source.export_profile("Apresentação", exported)
    destination = ProfileManager(tmp_path / "destination.json")
    assert destination.import_profiles(exported) == ["Apresentação"]
    assert destination.load("Apresentação")["cursor_speed"] == 1.6
    with pytest.raises(ValueError, match="já existe"):
        destination.import_profiles(exported)


def test_profiles_can_be_renamed_and_deleted_but_default_is_protected(tmp_path):
    manager = ProfileManager(tmp_path / "profiles.json")
    manager.save("Apresentação", DEFAULT_PROFILE)
    manager.rename("Apresentação", "Sala de aula")
    assert "Sala de aula" in manager.names()
    manager.delete("Sala de aula")
    assert "Sala de aula" not in manager.names()
    with pytest.raises(ValueError, match="Default"):
        manager.rename("Default", "Outro")
    with pytest.raises(ValueError, match="Default"):
        manager.delete("Default")
