"""Validated local JSON profiles for cursor, timing and shortcut mappings."""
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile

from .keyboard_controller import SHORTCUTS


DEFAULT_PROFILE = {
    "motion_sensitivity": 1.0,
    "cursor_smoothing": 0.32,
    "cursor_margin": 0.12,
    "scroll_repeat_seconds": 0.18,
    "zoom_repeat_seconds": 0.22,
    "action_switch_delay_seconds": 1.5,
    "mappings": {
        "thumb_up": "enter",
        "thumb_down": "esc",
        "swipe_left": "alt+left",
        "swipe_right": "alt+right",
    },
}

NUMERIC_LIMITS = {
    "motion_sensitivity": (0.5, 2.0),
    "cursor_smoothing": (0.10, 0.90),
    "cursor_margin": (0.05, 0.25),
    "scroll_repeat_seconds": (0.08, 0.50),
    "zoom_repeat_seconds": (0.10, 0.60),
    "action_switch_delay_seconds": (0.5, 3.0),
}
MAPPING_KEYS = tuple(DEFAULT_PROFILE["mappings"])
ALLOWED_MAPPING_ACTIONS = frozenset(SHORTCUTS)


class ProfileManager:
    """Read/write named profiles under ~/.pc-mao/profiles.json by default."""

    def __init__(self, path=None):
        self.path = (
            Path(path)
            if path is not None
            else Path.home() / ".pc-mao" / "profiles.json"
        )

    @staticmethod
    def _validate_name(name):
        clean = str(name).strip()
        if not re.fullmatch(r"[\w -]{1,32}", clean, flags=re.UNICODE):
            raise ValueError(
                "O nome do perfil deve ter até 32 caracteres e usar letras, "
                "números, espaço, hífen ou sublinhado."
            )
        return clean

    @staticmethod
    def validate_profile(profile):
        if not isinstance(profile, dict):
            raise ValueError("O perfil precisa ser um objeto JSON")
        normalized = deepcopy(DEFAULT_PROFILE)
        for key, (minimum, maximum) in NUMERIC_LIMITS.items():
            value = profile.get(key, normalized[key])
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"O parâmetro '{key}' precisa ser numérico")
            value = float(value)
            if not minimum <= value <= maximum:
                raise ValueError(
                    f"O parâmetro '{key}' precisa ficar entre "
                    f"{minimum} e {maximum}"
                )
            normalized[key] = value

        mappings = profile.get("mappings", {})
        if not isinstance(mappings, dict):
            raise ValueError("'mappings' precisa ser um objeto JSON")
        for key in MAPPING_KEYS:
            action = mappings.get(key, normalized["mappings"][key])
            if (
                not isinstance(action, str)
                or action not in ALLOWED_MAPPING_ACTIONS
            ):
                raise ValueError(
                    f"Ação não permitida no mapeamento '{key}': {action}"
                )
            normalized["mappings"][key] = action
        return normalized

    def _read_all(self):
        if not self.path.exists():
            return {"Default": deepcopy(DEFAULT_PROFILE)}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Não foi possível ler perfis em {self.path}: {exc}") from exc
        raw_profiles = data.get("profiles") if isinstance(data, dict) else None
        if not isinstance(raw_profiles, dict) or not raw_profiles:
            raise ValueError("O arquivo de perfis precisa conter um objeto 'profiles'")
        profiles = {}
        for name, value in raw_profiles.items():
            clean_name = self._validate_name(name)
            profiles[clean_name] = self.validate_profile(value)
        if "Default" not in profiles:
            profiles["Default"] = deepcopy(DEFAULT_PROFILE)
        return profiles

    def names(self):
        return sorted(self._read_all(), key=str.casefold)

    def load(self, name="Default"):
        profiles = self._read_all()
        if name not in profiles:
            raise KeyError(f"Perfil não encontrado: {name}")
        return deepcopy(profiles[name])

    def save(self, name, profile):
        clean_name = self._validate_name(name)
        normalized = self.validate_profile(profile)
        profiles = self._read_all()
        profiles[clean_name] = normalized
        payload = {"version": 1, "profiles": profiles}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                delete=False,
                suffix=".tmp",
            ) as temporary:
                json.dump(payload, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary_path = Path(temporary.name)
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return normalized
