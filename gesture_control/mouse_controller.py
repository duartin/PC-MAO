
SCROLL_TICKS = {
    "scroll_up": 80,
    "scroll_down": -80,
}


class MouseController:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def execute(self, action: str) -> str:
        ticks = SCROLL_TICKS.get(action)
        if ticks is None:
            raise ValueError(f"Ação de mouse não permitida: {action}")

        direction = "para cima" if ticks > 0 else "para baixo"

        if self.dry_run:
            return (
                "Modo de teste: 1 passo de rolagem "
                f"{direction} seria executado"
            )

        try:
            import pyautogui
            pyautogui.scroll(ticks)
        except Exception as exc:
            raise RuntimeError(
                f"Falha ao executar '{action}': {exc}"
            ) from exc

        return f"1 passo de rolagem {direction} executado"
