"""Background webcam/gesture worker; all image processing stays on-device."""
import threading
import time
import platform
from datetime import datetime

import cv2
import mediapipe as mp
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .click_drag import ClickDragController
from .camera_capture import camera_backends
from .gesture_hysteresis import GestureHysteresis
from .keyboard_controller import KeyboardController
from .mode_manager import ModeManager
from .motion_recognizer import MotionRecognizer
from .mouse_controller import MouseController
from .pinch_zoom import PinchZoomRecognizer
from .profile_manager import ProfileManager
from .recognizer import HandGestureRecognizer
from .safety_manager import SafetyManager, SafetySettings


class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    action_recorded = Signal(str, str, str)
    mode_changed = Signal(str)
    gesture_feedback = Signal(str, float, str)
    calibration_sample = Signal(float)

    GESTURE_STABILITY_SECONDS = 0.25
    SCROLL_REPEAT_SECONDS = 0.18
    CAMERA_READ_FAILURE_LIMIT = 3
    CAMERA_RETRY_SECONDS = 1.0

    @staticmethod
    def _open_camera(camera_index):
        """Open with a Windows-native backend first, then try OpenCV default."""
        backends = camera_backends(
            platform.system(),
            getattr(cv2, "CAP_DSHOW", None),
            cv2.CAP_ANY,
        )
        for backend in backends:
            cap = None
            try:
                cap = cv2.VideoCapture(camera_index, backend)
                if cap.isOpened():
                    # Avoid building up a queue of stale frames on slower PCs.
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    return cap
            except Exception:
                pass
            if cap is not None:
                cap.release()
        return None

    def _wait_before_camera_retry(self, seconds):
        """Wait without making Stop unresponsive."""
        deadline = time.monotonic() + seconds
        while not self.isInterruptionRequested():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(0.1, remaining))
        return False

    def __init__(self, camera_index=0, execute=False, motion_sensitivity=1.0,
                 parent=None, profile=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.execute_actions = execute
        base_profile = (
            profile if profile is not None
            else {"motion_sensitivity": motion_sensitivity}
        )
        self.profile = ProfileManager.validate_profile(base_profile)
        self.motion_sensitivity = self.profile["motion_sensitivity"]
        self._pause_lock = threading.Lock()
        self._paused = False
        self._calibration_capture = False
        self._last_action_time = float("-inf")

    def set_paused(self, paused: bool) -> None:
        with self._pause_lock:
            self._paused = paused

    def _is_paused(self) -> bool:
        with self._pause_lock:
            return self._paused

    def set_calibration_capture(self, enabled: bool) -> None:
        with self._pause_lock:
            self._calibration_capture = bool(enabled)

    def _is_calibration_capture(self) -> bool:
        with self._pause_lock:
            return self._calibration_capture

    def _dispatch(self, gesture_name, action, keyboard, mouse, now,
                  continuous=False):
        delay = self.profile["action_switch_delay_seconds"]
        elapsed = now - self._last_action_time
        if not continuous and elapsed < delay:
            remaining = delay - elapsed
            return f"Aguardando intervalo entre ações ({remaining:.1f}s)"

        if action.startswith("scroll_"):
            result = mouse.execute(action)
        else:
            result = keyboard.execute(action)

        # Cursor and sustained scrolling are continuous interactions.
        if not continuous:
            self._last_action_time = now

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_recorded.emit(timestamp, gesture_name, result)
        return result

    def _record_mouse_event(self, event):
        if event is None:
            return
        gesture_name, result = event
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_recorded.emit(timestamp, gesture_name, result)
        self.status_changed.emit(f"{gesture_name}: {result}")

    def _draw_cursor_calibration(self, frame):
        margin = self.profile["cursor_margin"]
        height, width = frame.shape[:2]
        left = int(width * margin)
        top = int(height * margin)
        right = max(left + 1, width - left - 1)
        bottom = max(top + 1, height - top - 1)
        cv2.rectangle(frame, (left, top), (right, bottom), (220, 80, 220), 1)
        cv2.putText(
            frame,
            "AREA ATIVA DO CURSOR",
            (left + 6, max(20, top + 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (220, 80, 220),
            1,
        )

    def run(self) -> None:
        cap = None
        while not self.isInterruptionRequested():
            cap = self._open_camera(self.camera_index)
            if cap is not None:
                break
            self.status_changed.emit(
                f"Não foi possível abrir a câmera {self.camera_index}; "
                "tentando novamente. Verifique se outro programa está usando a webcam."
            )
            if not self._wait_before_camera_retry(self.CAMERA_RETRY_SECONDS):
                return
        if cap is None:
            return

        self.status_changed.emit("Câmera ativa — processamento local.")
        hands_api = mp.solutions.hands
        recognizer = HandGestureRecognizer(
            click_pinch_threshold=self.profile["click_pinch_threshold"]
        )
        gesture_hysteresis = GestureHysteresis(stable_seconds=0.10)
        mode_manager = ModeManager(initial_mode=ModeManager.MOUSE)
        pinch_zoom = PinchZoomRecognizer(
            min_interval=self.profile["zoom_repeat_seconds"]
        )
        motion_recognizer = MotionRecognizer(
            sensitivity=self.profile["motion_sensitivity"],
            enable_vertical=False,
        )
        safety = SafetyManager(
            SafetySettings(
                hold_seconds=self.GESTURE_STABILITY_SECONDS,
                cooldown_seconds=self.profile["action_switch_delay_seconds"],
                neutral_seconds=0.25,
                min_confidence=0.78,
            )
        )
        keyboard = KeyboardController(dry_run=not self.execute_actions)
        mouse = MouseController(
            dry_run=not self.execute_actions,
            smoothing=self.profile["cursor_smoothing"],
            edge_margin=self.profile["cursor_margin"],
            speed=self.profile["cursor_speed"],
            acceleration=self.profile["cursor_acceleration"],
            deadzone_pixels=self.profile["cursor_deadzone_pixels"],
            max_step_pixels=self.profile["cursor_max_step_pixels"],
            scroll_ticks_per_step=self.profile["scroll_ticks_per_step"],
        )
        click_drag = ClickDragController(
            mouse,
            double_click_window_seconds=self.profile["double_click_window_seconds"],
        )
        self.mode_changed.emit(mode_manager.mode)
        self.status_changed.emit(
            "Modo Mouse ativo. Para Atalhos: mão aberta-punho-mão aberta; "
            "para Mouse: punho-mão aberta-punho-mão aberta."
        )

        scroll_candidate = None
        scroll_candidate_since = 0.0
        last_scroll_action_time = float("-inf")
        right_click_latched = False
        right_click_started_at = None
        consecutive_read_failures = 0

        try:
            with hands_api.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.65,
                min_tracking_confidence=0.60,
            ) as hands:
                while not self.isInterruptionRequested():
                    try:
                        ok, frame = cap.read()
                    except Exception as exc:
                        ok, frame = False, None
                        read_error = str(exc)
                    else:
                        read_error = ""
                    if not ok:
                        consecutive_read_failures += 1
                        if consecutive_read_failures < self.CAMERA_READ_FAILURE_LIMIT:
                            time.sleep(0.05)
                            continue

                        detail = f" ({read_error})" if read_error else ""
                        self.status_changed.emit(
                            "Sinal da câmera perdido" + detail + "; reconectando..."
                        )
                        try:
                            cap.release()
                        except Exception:
                            pass
                        cap = None
                        while not self.isInterruptionRequested():
                            if not self._wait_before_camera_retry(self.CAMERA_RETRY_SECONDS):
                                break
                            cap = self._open_camera(self.camera_index)
                            if cap is not None:
                                consecutive_read_failures = 0
                                self.status_changed.emit(
                                    "Câmera reconectada — processamento local retomado."
                                )
                                break
                            self.status_changed.emit(
                                "Webcam ainda indisponível; nova tentativa em 1 s."
                            )
                        if cap is None:
                            break
                        continue
                    consecutive_read_failures = 0

                    frame = cv2.flip(frame, 1)
                    if self._is_paused():
                        self._record_mouse_event(click_drag.cancel(clear_pending=True))
                        cv2.putText(
                            frame,
                            "PAUSADO",
                            (18, 35),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 180, 255),
                            2,
                        )
                    else:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        result = hands.process(rgb)
                        detected = None
                        raw_detected = None
                        hand_landmarks = None
                        now = time.monotonic()

                        if result.multi_hand_landmarks:
                            hand = result.multi_hand_landmarks[0]
                            hand_landmarks = hand.landmark
                            mp.solutions.drawing_utils.draw_landmarks(
                                frame,
                                hand,
                                hands_api.HAND_CONNECTIONS,
                            )
                            raw_detected = recognizer.recognize(hand_landmarks)

                        calibrating = self._is_calibration_capture()
                        if calibrating:
                            ratio = recognizer.middle_pinch_ratio(hand_landmarks)
                            if ratio is not None:
                                self.calibration_sample.emit(ratio)
                            gesture_hysteresis.reset()
                        else:
                            detected = gesture_hysteresis.update(raw_detected, now)
                        changed_mode = mode_manager.update(detected, now)
                        if changed_mode:
                            self.mode_changed.emit(changed_mode)
                            label = (
                                "Atalhos"
                                if changed_mode == ModeManager.KEYBOARD
                                else "Mouse"
                            )
                            self.status_changed.emit(f"Modo {label} ativado.")

                        is_mode_pose = (
                            detected is not None
                            and detected.action in (
                                ModeManager.OPEN_ACTION,
                                ModeManager.FIST_ACTION,
                            )
                        )
                        action = getattr(detected, "action", None)
                        feedback_gesture = detected or raw_detected
                        if feedback_gesture is not None:
                            cv2.putText(
                                frame,
                                f"{feedback_gesture.name}  {feedback_gesture.confidence:.0%}",
                                (18, 34),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.62,
                                (80, 230, 140),
                                2,
                            )
                        if action != "right_click":
                            right_click_latched = False
                            right_click_started_at = None
                        elif mode_manager.mode == ModeManager.MOUSE:
                            if right_click_started_at is None:
                                right_click_started_at = now
                            elif (
                                not right_click_latched
                                and now - right_click_started_at
                                >= self.GESTURE_STABILITY_SECONDS
                            ):
                                right_click_latched = True
                                self._record_mouse_event(
                                    ("Clique direito", mouse.click_right())
                                )
                        if action in (
                            ModeManager.OPEN_ACTION,
                            ModeManager.FIST_ACTION,
                            "enter",
                            "esc",
                            "cursor",
                            "click_drag",
                            "scroll_up",
                            "scroll_down",
                            "right_click",
                        ):
                            motion_recognizer.reset()

                        # A missing hand, a mode switch or a different gesture
                        # cancels click candidates; a drag always releases.
                        if calibrating or (
                            mode_manager.mode != ModeManager.MOUSE
                            or is_mode_pose
                            or (action not in (None, "cursor", "click_drag"))
                        ):
                            click_event = click_drag.cancel(clear_pending=True)
                        elif hand_landmarks is None:
                            click_event = click_drag.update(False, None, now)
                        elif action == "click_drag":
                            index_tip = hand_landmarks[8]
                            click_event = click_drag.update(
                                True,
                                (index_tip.x, index_tip.y),
                                now,
                            )
                        else:
                            click_event = click_drag.update(False, None, now)
                        self._record_mouse_event(click_event)

                        if (
                            mode_manager.mode == ModeManager.MOUSE
                            and action == "pinch"
                        ):
                            zoom_action = pinch_zoom.update(hand_landmarks, now)
                        else:
                            pinch_zoom.reset()
                            zoom_action = None

                        if mode_manager.mode == ModeManager.MOUSE:
                            self._draw_cursor_calibration(frame)

                        # Hand-open/fist poses only switch modes.
                        if is_mode_pose:
                            scroll_candidate = None
                            safety.suppress_until_neutral()

                        # Thumb-index pinch: short tap clicks; hold drags.
                        elif action == "click_drag":
                            scroll_candidate = None
                            safety.suppress_until_neutral()

                        # Index-only pose moves the cursor immediately.
                        elif action == "cursor":
                            scroll_candidate = None
                            safety.suppress_until_neutral()
                            if mode_manager.mode == ModeManager.MOUSE:
                                index_tip = hand_landmarks[8]
                                mouse.move_cursor(index_tip.x, index_tip.y)

                        elif zoom_action and mode_manager.mode == ModeManager.MOUSE:
                            scroll_candidate = None
                            safety.suppress_until_neutral()
                            zoom_name = (
                                "Pinça afastando — zoom +"
                                if zoom_action == "zoom_in"
                                else "Pinça aproximando — zoom −"
                            )
                            response = self._dispatch(
                                zoom_name,
                                zoom_action,
                                keyboard,
                                mouse,
                                now,
                                continuous=True,
                            )
                            self.status_changed.emit(f"{zoom_name}: {response}")

                        else:
                            motion = motion_recognizer.update(
                                hand_landmarks,
                                now,
                            )

                            if motion:
                                scroll_candidate = None
                                safety.suppress_until_neutral()
                                if mode_manager.mode == ModeManager.KEYBOARD:
                                    mapping_key = (
                                        "swipe_left"
                                        if motion.action == "page_back"
                                        else "swipe_right"
                                    )
                                    action_name = self.profile["mappings"][mapping_key]
                                    response = self._dispatch(
                                        motion.name,
                                        action_name,
                                        keyboard,
                                        mouse,
                                        now,
                                    )
                                    self.status_changed.emit(
                                        f"{motion.name}: {response}"
                                    )
                                else:
                                    self.status_changed.emit(
                                        "Deslize horizontal ignorado no modo Mouse."
                                    )

                            elif action in ("scroll_up", "scroll_down"):
                                if mode_manager.mode == ModeManager.MOUSE:
                                    safety.suppress_until_neutral()
                                    if action != scroll_candidate:
                                        scroll_candidate = action
                                        scroll_candidate_since = now

                                    stable_for = now - scroll_candidate_since
                                    repeat_elapsed = now - last_scroll_action_time
                                    repeat_interval = self.profile[
                                        "scroll_repeat_seconds"
                                    ]
                                    if (
                                        stable_for >= self.GESTURE_STABILITY_SECONDS
                                        and repeat_elapsed >= repeat_interval
                                    ):
                                        response = self._dispatch(
                                            detected.name,
                                            action,
                                            keyboard,
                                            mouse,
                                            now,
                                            continuous=True,
                                        )
                                        last_scroll_action_time = now
                                        self.status_changed.emit(
                                            f"{detected.name}: {response}"
                                        )
                                    else:
                                        remaining = max(
                                            0.0,
                                            self.GESTURE_STABILITY_SECONDS - stable_for,
                                        )
                                        self.status_changed.emit(
                                            f"{detected.name} — mantenha; "
                                            f"rolagem em {remaining:.1f}s"
                                        )
                                else:
                                    scroll_candidate = None
                                    safety.update(None, now)

                            elif action == "pinch":
                                scroll_candidate = None
                                safety.update(None, now)

                            elif (
                                mode_manager.mode == ModeManager.KEYBOARD
                                and action in ("enter", "esc")
                            ):
                                safety_key = (
                                    "thumb_up" if action == "enter" else "thumb_down"
                                )
                                mapped_action = self.profile["mappings"][safety_key]
                                confirmed = safety.update(detected, now)
                                if confirmed:
                                    response = self._dispatch(
                                        confirmed.name,
                                        mapped_action,
                                        keyboard,
                                        mouse,
                                        now,
                                    )
                                    self.status_changed.emit(
                                        f"{confirmed.name}: {response}"
                                    )
                                else:
                                    self.status_changed.emit(
                                        f"Candidato: {detected.name} — "
                                        f"estabilizando por "
                                        f"{self.GESTURE_STABILITY_SECONDS:.2f} s"
                                    )
                            else:
                                scroll_candidate = None
                                safety.update(None, now)

                        if calibrating:
                            gesture_state = "Calibrando — comandos temporariamente bloqueados"
                        elif hand_landmarks is None:
                            gesture_state = "Mão não detectada"
                        elif raw_detected is not None and detected is None:
                            gesture_state = "Confirmando estabilidade do gesto"
                        elif action == "cursor":
                            gesture_state = "Cursor ativo — rastreando indicador"
                        elif action == "click_drag":
                            gesture_state = click_drag.state(now)
                        elif action in ("scroll_up", "scroll_down"):
                            elapsed = now - scroll_candidate_since if scroll_candidate == action else 0.0
                            if elapsed >= self.GESTURE_STABILITY_SECONDS:
                                ticks = self.profile["scroll_ticks_per_step"]
                                signed_ticks = ticks if action == "scroll_up" else -ticks
                                gesture_state = f"Rolando {signed_ticks:+.0f} ticks/passo"
                            else:
                                gesture_state = "Estabilizando pose de rolagem"
                        elif action == "pinch":
                            gesture_state = "Pinça de zoom detectada"
                        elif action == "right_click":
                            gesture_state = "Estabilizando clique direito"
                        elif is_mode_pose:
                            gesture_state = "Sequência de troca de modo"
                        elif detected is not None:
                            gesture_state = f"Gesto ativo: {detected.name}"
                        else:
                            gesture_state = "Aguardando gesto"
                        self.gesture_feedback.emit(
                            feedback_gesture.name if feedback_gesture else "Nenhum",
                            feedback_gesture.confidence if feedback_gesture else 0.0,
                            gesture_state,
                        )

                    height, width = frame.shape[:2]
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = QImage(
                        rgb_frame.data,
                        width,
                        height,
                        3 * width,
                        QImage.Format.Format_RGB888,
                    ).copy()
                    self.frame_ready.emit(image)

        except Exception as exc:
            self.status_changed.emit(f"Falha no reconhecimento: {exc}")
        finally:
            try:
                self._record_mouse_event(click_drag.cancel())
                self._record_mouse_event(click_drag.flush_pending())
            except Exception as exc:
                self.status_changed.emit(
                    f"Falha ao liberar o botão após arraste: {exc}"
                )
            if cap is not None:
                cap.release()
            self.status_changed.emit("Câmera desligada.")
