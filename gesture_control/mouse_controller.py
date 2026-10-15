"""Mouse actions with dry-run defaults and configurable cursor mapping."""
import math
import time

SCROLL_TICKS = {"scroll_up": 80, "scroll_down": -80}


class MouseController:
    CURSOR_MARGIN = 0.12

    def __init__(self, dry_run=True, smoothing=0.32, edge_margin=CURSOR_MARGIN,
                 deadzone_pixels=1.5, speed=1.0, acceleration=0.0,
                 max_step_pixels=120.0, scroll_ticks_per_step=80):
        if not 0 < smoothing <= 1:
            raise ValueError("A suavização do cursor deve estar entre 0 e 1")
        if not 0.0 <= edge_margin < 0.5:
            raise ValueError("A margem do cursor precisa estar entre 0 e 0,5")
        if not 0.5 <= speed <= 2.0 or not 0.0 <= acceleration <= 1.5:
            raise ValueError("Velocidade/aceleração do cursor fora dos limites")
        if deadzone_pixels < 0:
            raise ValueError("A zona morta não pode ser negativa")
        if not 20 <= max_step_pixels <= 300:
            raise ValueError("O passo máximo do cursor precisa ficar entre 20 e 300 px")
        if not 10 <= scroll_ticks_per_step <= 160:
            raise ValueError("A intensidade do scroll precisa ficar entre 10 e 160 ticks")
        self.dry_run = dry_run
        self.smoothing = smoothing
        self.edge_margin = edge_margin
        self.deadzone_pixels = deadzone_pixels
        self.speed = speed
        self.acceleration = acceleration
        self.max_step_pixels = float(max_step_pixels)
        self.scroll_ticks_per_step = int(round(scroll_ticks_per_step))
        self._smoothed_cursor = None
        self._previous_hand_point = None
        self._previous_move_time = None
        self._left_button_down = False

    @staticmethod
    def adaptive_delta(dx, dy, hand_speed, speed=1.0, acceleration=0.0,
                       max_step=120.0, edge_factor=1.0):
        """Scale slow hand motion for precision, accelerate fast motion, and cap steps."""
        velocity_fraction = min(1.0, max(0.0, float(hand_speed) / 0.8))
        gain = float(speed) * (0.55 + velocity_fraction * (0.45 + float(acceleration)))
        gain *= min(1.0, max(0.35, float(edge_factor)))
        out_x, out_y = float(dx) * gain, float(dy) * gain
        distance = math.hypot(out_x, out_y)
        if distance > max_step:
            ratio = max_step / distance
            out_x *= ratio
            out_y *= ratio
        return out_x, out_y

    @staticmethod
    def _edge_factor(x, y, width, height, zone=120.0):
        distance_to_edge = min(x, y, width - 1 - x, height - 1 - y)
        proximity = min(1.0, max(0.0, distance_to_edge / max(zone, 1.0)))
        return 0.45 + 0.55 * proximity

    @classmethod
    def map_to_screen(cls, x, y, width, height, margin=None):
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
            self._smoothed_cursor = (old_x + alpha * (target_x - old_x),
                                     old_y + alpha * (target_y - old_y))
        return self._smoothed_cursor

    def move_cursor(self, x, y):
        x, y = min(1.0, max(0.0, float(x))), min(1.0, max(0.0, float(y)))
        if self.dry_run:
            smooth_x, smooth_y = self._smooth(x, y)
            return f"Modo de teste: cursor iria para ({smooth_x:.2f}, {smooth_y:.2f})"
        try:
            import pyautogui
            now = time.monotonic()
            width, height = pyautogui.size()
            target_x, target_y = self.map_to_screen(x, y, width, height, self.edge_margin)
            smooth_x, smooth_y = self._smooth(target_x, target_y)
            current_x, current_y = pyautogui.position()
            dx, dy = smooth_x - current_x, smooth_y - current_y
            distance = (dx * dx + dy * dy) ** 0.5
            if distance < self.deadzone_pixels:
                return "Cursor estável dentro da zona morta"
            if self._previous_hand_point is None or self._previous_move_time is None:
                hand_speed = 0.0
            else:
                elapsed = max(0.001, now - self._previous_move_time)
                hand_speed = math.hypot(x - self._previous_hand_point[0],
                                        y - self._previous_hand_point[1]) / elapsed
            self._previous_hand_point = (x, y)
            self._previous_move_time = now
            edge_factor = self._edge_factor(current_x, current_y, width, height)
            step_x, step_y = self.adaptive_delta(
                dx, dy, hand_speed, self.speed, self.acceleration,
                self.max_step_pixels, edge_factor,
            )
            pyautogui.moveTo(round(current_x + step_x), round(current_y + step_y), duration=0)
        except Exception as exc:
            raise RuntimeError(f"Falha ao mover o cursor: {exc}") from exc
        return "Cursor atualizado"

    def click_left(self):
        if self.dry_run:
            return "Modo de teste: clique esquerdo seria executado"
        try:
            import pyautogui
            pyautogui.click(button="left")
        except Exception as exc:
            raise RuntimeError(f"Falha ao clicar: {exc}") from exc
        return "Clique esquerdo executado"

    def double_click_left(self):
        if self.dry_run:
            return "Modo de teste: clique duplo esquerdo seria executado"
        try:
            import pyautogui
            pyautogui.doubleClick(button="left", interval=0.12)
        except Exception as exc:
            raise RuntimeError(f"Falha no clique duplo: {exc}") from exc
        return "Clique duplo esquerdo executado"

    def click_right(self):
        if self.dry_run:
            return "Modo de teste: clique direito seria executado"
        try:
            import pyautogui
            pyautogui.click(button="right")
        except Exception as exc:
            raise RuntimeError(f"Falha ao clicar com botão direito: {exc}") from exc
        return "Clique direito executado"

    def press_left(self):
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

    def release_left(self):
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

    def execute(self, action):
        direction = 1 if action == "scroll_up" else -1 if action == "scroll_down" else None
        if direction is None:
            raise ValueError(f"Ação de mouse não permitida: {action}")
        ticks = direction * self.scroll_ticks_per_step
        direction_name = "para cima" if direction > 0 else "para baixo"
        if self.dry_run:
            return f"Modo de teste: rolagem {ticks:+d} ({direction_name}) seria executada"
        try:
            import pyautogui
            pyautogui.scroll(ticks)
        except Exception as exc:
            raise RuntimeError(f"Falha ao executar '{action}': {exc}") from exc
        return f"Rolagem {ticks:+d} ({direction_name}) executada"
