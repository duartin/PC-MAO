"""Allowlisted mouse wheel actions."""

SCROLL_TICKS = {"scroll_up": 4, "scroll_down": -4}


class MouseController:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def execute(self, action: str) -> str:
        ticks = SCROLL_TICKS.get(action)
        if ticks is None:
            raise ValueError(f"Ação de mouse não permitida: {action}")
        if self.dry_run:
            return f"Modo de teste: {action} ({ticks} passos) seria executado"
        try:
            import pyautogui
            pyautogui.scroll(ticks)
        except Exception as exc:
            raise RuntimeError(f"Falha ao executar '{action}': {exc}") from exc
        return f"Rolagem executada: {action}"
