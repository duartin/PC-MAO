"""Allowlisted keyboard actions. No arbitrary shell commands are supported."""

SHORTCUTS = {
    "enter": ("enter",),
    "esc": ("esc",),
    "space": ("space",),
    "ctrl+s": ("ctrl", "s"),
    "alt+tab": ("alt", "tab"),
    "alt+left": ("alt", "left"),
    "alt+right": ("alt", "right"),
}


class KeyboardController:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def execute(self, action: str) -> str:
        keys = SHORTCUTS.get(action)
        if keys is None:
            raise ValueError(f"Ação não permitida: {action}")
        if self.dry_run:
            return f"Modo de teste: {action} seria executado"
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
        except Exception as exc:
            raise RuntimeError(f"Falha ao enviar atalho '{action}': {exc}") from exc
        return f"Atalho executado: {action}"
