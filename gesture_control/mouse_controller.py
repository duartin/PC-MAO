"""Mouse actions with dry-run defaults and configurable cursor mapping."""

# One wheel step per repeat makes sustained scrolling smooth and controllable.
SCROLL_TICKS = {"scroll_up": 1, "scroll_down": -1}


class MouseController:
    CURSOR_MARGIN = 0.12

    def __init__(
        self,
        dry_run: bool = True,
        smoothing: float = 0.32,
        edge_margin: float = CURSOR_MARGIN,
        deadzone_pixels: float = 1.5,
    ):
        if not 0 < smoothing <= 1:
            raise ValueError("A suavização do cursor deve estar entre 0 e 1")
        if not 0.0 <= edge_margin < 0.5:
            raise ValueError("A margem do cursor precisa estar entre 0 e 0,5")
        self.dry_run = dry_run
        self.smoothing = smoothing
        self.edge_margin = edge_margin
        self.deadzone_pixels = deadzone_pixels
        self._smoothed_cursor = None
        self._left_button_down = False

    @classmethod
    def map_to_screen(cls, x, y, width, height, margin=None):
        """Map normalized camera coordinates from a calibrated area to screen."""
        if width <= 0 or height <= 0:
            raise ValueError("A resolução da tela deve ser positiva")
        margin = cls.CURSOR_MARGIN if margin is None else float(margin)
        if not 0.0 <= margin < 0.5:
            raise ValueError("A margem precisa estar entre 0 e 0,5")

        span = 1.0 - 2.0 * margin
        norm_x = min(1.0, max(0.0, (float(x) - margin) / span))
        norm_y = min(1.0, max(0.0, (float(y) - margin) / span))
        return round(norm_x * (width - 1)), round(norm_y * (height - 1))

    def _smooth(self, target_x, target_y):
        if self._smoothed_cursor is None:
            self._smoothed_cursor = (float(target_x), float(target_y))
        else:
            old_x, old_y = self._smoothed_cursor
            alpha = self.smoothing
            self._smoothed_cursor = (
                old_x + alpha * (target_x - old_x),
                old_y + alpha * (target_y - old_y),
            )
        return self._smoothed_cursor

    def move_cursor(self, x, y) -> str:
        """Move toward normalized index-tip coordinates; dry-run is default."""
        x = min(1.0, max(0.0, float(x)))
        y = min(1.0, max(0.0, float(y)))

        if self.dry_run:
            smooth_x, smooth_y = self._smooth(x, y)
            return (
                "Modo de teste: cursor iria para "
                f"({smooth_x:.2f}, {smooth_y:.2f})"
            )

        try:
            import pyautogui

            width, height = pyautogui.size()
            target_x, target_y = self.map_to_screen(
                x,
                y,
                width,
                height,
                margin=self.edge_margin,
            )
            smooth_x, smooth_y = self._smooth(target_x, target_y)
            current_x, current_y = pyautogui.position()
            distance = (
                (smooth_x - current_x) ** 2 + (smooth_y - current_y) ** 2
            ) ** 0.5
            if distance >= self.deadzone_pixels:
                pyautogui.moveTo(
                    round(smooth_x),
                    round(smooth_y),
                    duration=0,
                )
        except Exception as exc:
            raise RuntimeError(f"Falha ao mover o cursor: {exc}") from exc

        return "Cursor atualizado"

    def click_left(self) -> str:
        if self.dry_run:
            return "Modo de teste: clique esquerdo seria executado"
        try:
            import pyautogui
            pyautogui.click(button="left")
        except Exception as exc:
            raise RuntimeError(f"Falha ao clicar: {exc}") from exc
        return "Clique esquerdo executado"

    def press_left(self) -> str:
        if self._left_button_down:
            return "Botão esquerdo já pressionado"
        if self.dry_run:
            self._left_button_down = True
            return "Modo de teste: arraste iniciado"
        try:
            import pyautogui
            pyautogui.mouseDown(button="left")
            self._left_button_down = True
        except Exception as exc:
            raise RuntimeError(f"Falha ao iniciar arraste: {exc}") from exc
        return "Arraste iniciado"

    def release_left(self) -> str:
        if not self._left_button_down:
            return "Botão esquerdo já liberado"
        try:
            if not self.dry_run:
                import pyautogui
                pyautogui.mouseUp(button="left")
        except Exception as exc:
            raise RuntimeError(f"Falha ao liberar botão do mouse: {exc}") from exc
        self._left_button_down = False
        return "Arraste finalizado" if not self.dry_run else "Modo de teste: arraste finalizado"

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
