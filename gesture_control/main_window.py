"""PySide6 interface with profiles, calibration, feedback and mouse controls."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QProgressBar, QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from .camera_worker import CameraWorker
from .keyboard_controller import SHORTCUTS
from .profile_manager import DEFAULT_PROFILE, ProfileManager


class MainWindow(QMainWindow):
    def __init__(self, camera_index=0, motion_sensitivity=None,
                 execute_default=False, profile_name="Default"):
        super().__init__()
        self.camera_index = camera_index
        self.profile_manager = ProfileManager()
        self.worker = None
        self.profile_error = None
        self._calibration_phase = None
        self._pinch_samples = []
        self._neutral_samples = []
        try:
            self.profile_names = self.profile_manager.names()
        except ValueError as exc:
            self.profile_names, self.profile_error = ["Default"], str(exc)
        if profile_name not in self.profile_names:
            self.profile_name = "Default"
            self.profile_error = f"Perfil '{profile_name}' não encontrado; usando Default."
        else:
            self.profile_name = profile_name
        try:
            self.profile = self.profile_manager.load(self.profile_name)
        except (KeyError, ValueError) as exc:
            self.profile_name, self.profile = "Default", dict(DEFAULT_PROFILE)
            self.profile_error = str(exc)
        if motion_sensitivity is not None:
            self.profile["motion_sensitivity"] = motion_sensitivity
        self.setWindowTitle("Controle do computador por gestos")
        self.resize(1320, 900)
        self._profile_widgets = []
        self._build_ui(execute_default)
        self._apply_style()
        self._set_profile_controls(self.profile)
        self._update_mode_label("mouse")
        if self.profile_error:
            self.status.setText(f"Aviso de perfil: {self.profile_error}")

    def _build_ui(self, execute_default):
        root = QWidget()
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(18, 18, 18, 18)
        page.setSpacing(12)
        title = QLabel("Controle por gestos")
        title.setObjectName("title")
        subtitle = QLabel("Webcam processada localmente • sem gravação de vídeo")
        subtitle.setObjectName("subtitle")
        page.addWidget(title)
        page.addWidget(subtitle)

        body = QHBoxLayout()
        page.addLayout(body, 1)
        self.video = QLabel("Câmera desligada")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(600, 450)
        self.video.setObjectName("video")
        body.addWidget(self.video, 3)
        panel = QWidget()
        side = QVBoxLayout(panel)
        side.setContentsMargins(8, 8, 8, 8)
        side.setSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(450)
        scroll.setWidget(panel)
        body.addWidget(scroll, 2)

        mode_group = QGroupBox("CONTROLE ATIVO")
        mode_layout = QVBoxLayout(mode_group)
        self.mode_label = QLabel("Mouse — cursor, scroll e zoom")
        self.mode_label.setWordWrap(True)
        self.mode_label.setObjectName("mode")
        self.status = QLabel("Pronto. Inicie a câmera para começar.")
        self.status.setWordWrap(True)
        self.status.setObjectName("status")
        self.gesture_label = QLabel("Gesto: nenhum")
        self.gesture_state_label = QLabel("Estado: aguardando mão")
        self.confidence_label = QLabel("Compatibilidade da pose: 0%")
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setTextVisible(False)
        mode_layout.addWidget(self.mode_label)
        mode_layout.addWidget(self.status)
        mode_layout.addWidget(self.gesture_label)
        mode_layout.addWidget(self.gesture_state_label)
        mode_layout.addWidget(self.confidence_label)
        mode_layout.addWidget(self.confidence_bar)
        side.addWidget(mode_group)
        self.execute_checkbox = QCheckBox("Executar ações reais no computador")
        self.execute_checkbox.setChecked(execute_default)
        side.addWidget(self.execute_checkbox)
        safety_note = QLabel("Desmarcado = modo de teste. Marque para permitir ações reais no computador.")
        safety_note.setWordWrap(True)
        safety_note.setObjectName("note")
        side.addWidget(safety_note)

        profile_group = QGroupBox("PERFIS, MAPEAMENTOS E CALIBRAÇÃO")
        form = QFormLayout(profile_group)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profile_names)
        self.profile_combo.setCurrentText(self.profile_name)
        self.profile_combo.currentTextChanged.connect(self._load_selected_profile)
        form.addRow("Perfil", self.profile_combo)
        self.profile_sliders, self.profile_value_labels = {}, {}
        self._add_slider(form, "Sensibilidade dos deslizes", "motion_sensitivity", 5, 20, 10, "{:.1f}")
        self._add_slider(form, "Suavização do cursor", "cursor_smoothing", 10, 90, 100, "{:.2f}")
        self._add_slider(form, "Margem da área ativa (%)", "cursor_margin", 5, 25, 100, "{:.0f}%", True)
        self._add_slider(form, "Velocidade do cursor", "cursor_speed", 5, 20, 10, "{:.1f}×")
        self._add_slider(form, "Aceleração do cursor", "cursor_acceleration", 0, 15, 10, "{:.1f}")
        self._add_slider(form, "Zona morta do cursor (px)", "cursor_deadzone_pixels", 0, 12, 1, "{:.0f} px")
        self._add_slider(form, "Passo máximo do cursor (px/quadro)", "cursor_max_step_pixels", 20, 300, 1, "{:.0f} px")
        self._add_slider(form, "Intervalo de rolagem (s)", "scroll_repeat_seconds", 8, 50, 100, "{:.2f} s")
        self._add_slider(form, "Intensidade do scroll (ticks/passo)", "scroll_ticks_per_step", 10, 160, 1, "{:.0f}")
        self._add_slider(form, "Intervalo do zoom (s)", "zoom_repeat_seconds", 10, 60, 100, "{:.2f} s")
        self._add_slider(form, "Limiar pinça polegar+médio", "click_pinch_threshold", 12, 60, 100, "{:.2f}")
        self._add_slider(form, "Janela do duplo clique (s)", "double_click_window_seconds", 20, 60, 100, "{:.2f} s")
        self._add_slider(form, "Intervalo entre ações (s)", "action_switch_delay_seconds", 5, 30, 10, "{:.1f} s")

        mapping_group = QGroupBox("Mapeamentos dos atalhos")
        mapping_form = QFormLayout(mapping_group)
        self.mapping_combos = {}
        for key, label in {"thumb_up": "Polegar para cima", "thumb_down": "Polegar para baixo", "swipe_left": "Deslize à esquerda", "swipe_right": "Deslize à direita"}.items():
            combo = QComboBox()
            for action in sorted(SHORTCUTS):
                combo.addItem(action, action)
            self.mapping_combos[key] = combo
            mapping_form.addRow(label, combo)
            self._profile_widgets.append(combo)
        form.addRow(mapping_group)

        buttons = QHBoxLayout()
        self.save_profile_button = QPushButton("Salvar")
        self.save_profile_button.clicked.connect(self._save_profile)
        self.new_profile_button = QPushButton("Criar")
        self.new_profile_button.clicked.connect(self._create_profile)
        self.rename_profile_button = QPushButton("Renomear")
        self.rename_profile_button.clicked.connect(self._rename_profile)
        self.delete_profile_button = QPushButton("Excluir")
        self.delete_profile_button.clicked.connect(self._delete_profile)
        for button in (self.save_profile_button, self.new_profile_button, self.rename_profile_button, self.delete_profile_button):
            buttons.addWidget(button)
        form.addRow(buttons)
        io_buttons = QHBoxLayout()
        self.export_profile_button = QPushButton("Exportar perfil")
        self.export_profile_button.clicked.connect(self._export_profile)
        self.import_profile_button = QPushButton("Importar perfis")
        self.import_profile_button.clicked.connect(self._import_profiles)
        io_buttons.addWidget(self.export_profile_button)
        io_buttons.addWidget(self.import_profile_button)
        form.addRow(io_buttons)
        side.addWidget(profile_group)

        calibration_note = QLabel("A moldura rosa mostra a área do cursor. Use o assistente para ajustar a região e testar os extremos.")
        calibration_note.setWordWrap(True)
        calibration_note.setObjectName("note")
        side.addWidget(calibration_note)
        self.calibrate_button = QPushButton("Calibrar pinça de clique")
        self.calibrate_button.setEnabled(False)
        self.calibrate_button.clicked.connect(self._calibration_wizard)
        side.addWidget(self.calibrate_button)
        calibration_note = QLabel("O assistente coleta a pinça polegar–médio e, em seguida, a mão relaxada. Depois, revise a área do cursor e salve o perfil.")
        calibration_note.setWordWrap(True)
        calibration_note.setObjectName("note")
        side.addWidget(calibration_note)

        history_group = QGroupBox("HISTÓRICO DE AÇÕES")
        history_layout = QVBoxLayout(history_group)
        self.history = QListWidget()
        self.history.setMinimumHeight(150)
        history_layout.addWidget(self.history)
        clear = QPushButton("Limpar histórico")
        clear.clicked.connect(self.history.clear)
        history_layout.addWidget(clear)
        side.addWidget(history_group)

        controls = QHBoxLayout()
        page.addLayout(controls)
        self.start_button = QPushButton("Iniciar câmera")
        self.start_button.clicked.connect(self.start_camera)
        self.pause_button = QPushButton("Pausar")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button = QPushButton("Parar câmera")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_camera)
        controls.addWidget(self.start_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)
        footer = QLabel("Mouse: indicador move; dois dedos rolam; polegar+indicador ajustam zoom; toque rápido polegar+médio clica e segurar inicia arraste. Atalhos: mão aberta-punho-mão aberta; para voltar a Mouse: punho-mão aberta-punho-mão aberta.")
        footer.setWordWrap(True)
        footer.setObjectName("note")
        page.addWidget(footer)
        self._profile_widgets.extend([self.profile_combo, self.save_profile_button, self.new_profile_button, self.rename_profile_button, self.delete_profile_button, self.export_profile_button, self.import_profile_button])

    def _add_slider(self, form, label, key, minimum, maximum, scale, template, percent=False):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        value_label = QLabel()
        self.profile_sliders[key] = slider
        self.profile_value_labels[key] = value_label
        def update_label(value, factor=scale, fmt=template, is_percent=percent):
            shown = value / factor
            value_label.setText(fmt.format(shown * 100 if is_percent else shown))
        slider.valueChanged.connect(update_label)
        layout.addWidget(slider, 1)
        layout.addWidget(value_label)
        form.addRow(label, row)
        self._profile_widgets.append(slider)

    def _profile_from_controls(self):
        scales = {"motion_sensitivity": 10, "cursor_smoothing": 100, "cursor_margin": 100,
                  "cursor_speed": 10, "cursor_acceleration": 10, "cursor_deadzone_pixels": 1,
                  "cursor_max_step_pixels": 1, "scroll_repeat_seconds": 100,
                  "scroll_ticks_per_step": 1, "zoom_repeat_seconds": 100,
                  "click_pinch_threshold": 100, "double_click_window_seconds": 100,
                  "action_switch_delay_seconds": 10}
        profile = {key: slider.value() / scales[key] for key, slider in self.profile_sliders.items()}
        profile["mappings"] = {key: combo.currentData() for key, combo in self.mapping_combos.items()}
        return ProfileManager.validate_profile(profile)

    def _set_profile_controls(self, profile):
        scales = {"motion_sensitivity": 10, "cursor_smoothing": 100, "cursor_margin": 100,
                  "cursor_speed": 10, "cursor_acceleration": 10, "cursor_deadzone_pixels": 1,
                  "cursor_max_step_pixels": 1, "scroll_repeat_seconds": 100,
                  "scroll_ticks_per_step": 1, "zoom_repeat_seconds": 100,
                  "click_pinch_threshold": 100, "double_click_window_seconds": 100,
                  "action_switch_delay_seconds": 10}
        for key, slider in self.profile_sliders.items():
            slider.setValue(round(profile[key] * scales[key]))
        for key, combo in self.mapping_combos.items():
            index = combo.findData(profile["mappings"][key])
            if index >= 0:
                combo.setCurrentIndex(index)

    def _refresh_profiles(self, select=None):
        names = self.profile_manager.names()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(names)
        target = select if select in names else "Default"
        self.profile_combo.setCurrentText(target)
        self.profile_combo.blockSignals(False)
        self._load_selected_profile(target)

    def _load_selected_profile(self, name):
        if not name:
            return
        try:
            self.profile = self.profile_manager.load(name)
            self.profile_name = name
            self._set_profile_controls(self.profile)
            if hasattr(self, "status"):
                self.status.setText(f"Perfil '{name}' carregado.")
        except (KeyError, ValueError) as exc:
            self.status.setText(f"Erro ao carregar perfil: {exc}")

    def _save_profile(self):
        name = self.profile_combo.currentText()
        try:
            self.profile = self.profile_manager.save(name, self._profile_from_controls())
            self.profile_name = name
            self.status.setText(f"Perfil '{name}' salvo.")
        except (ValueError, OSError) as exc:
            self.status.setText(f"Não foi possível salvar o perfil: {exc}")

    def _create_profile(self):
        name, accepted = QInputDialog.getText(self, "Criar perfil", "Nome do novo perfil:")
        if not accepted:
            return
        try:
            clean = ProfileManager._validate_name(name)
            if clean in self.profile_manager.names():
                raise ValueError(f"Já existe um perfil chamado '{clean}'")
            self.profile = self.profile_manager.save(clean, self._profile_from_controls())
            self._refresh_profiles(clean)
            self.status.setText(f"Perfil '{clean}' criado.")
        except (ValueError, OSError) as exc:
            self.status.setText(f"Não foi possível criar o perfil: {exc}")

    def _rename_profile(self):
        old = self.profile_combo.currentText()
        name, accepted = QInputDialog.getText(self, "Renomear perfil", "Novo nome:", text=old)
        if not accepted:
            return
        try:
            self.profile_manager.rename(old, name)
            self._refresh_profiles(name.strip())
            self.status.setText(f"Perfil renomeado para '{name.strip()}'.")
        except (KeyError, ValueError, OSError) as exc:
            self.status.setText(f"Não foi possível renomear: {exc}")

    def _delete_profile(self):
        name = self.profile_combo.currentText()
        if name == "Default":
            self.status.setText("O perfil Default é protegido e não pode ser excluído.")
            return
        answer = QMessageBox.question(self, "Excluir perfil", f"Excluir '{name}'? Esta ação não pode ser desfeita.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.profile_manager.delete(name)
            self._refresh_profiles("Default")
            self.status.setText(f"Perfil '{name}' excluído.")
        except (KeyError, ValueError, OSError) as exc:
            self.status.setText(f"Não foi possível excluir: {exc}")

    def _export_profile(self):
        name = self.profile_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "Exportar perfil", f"{name}.json", "JSON (*.json)")
        if not path:
            return
        try:
            self.profile_manager.export_profile(name, path)
            self.status.setText(f"Perfil exportado para {path}")
        except (OSError, ValueError) as exc:
            self.status.setText(f"Falha ao exportar perfil: {exc}")

    def _import_profiles(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar perfis", "", "JSON (*.json)")
        if not path:
            return
        try:
            try:
                names = self.profile_manager.import_profiles(path)
            except ValueError as exc:
                if "já existe" not in str(exc):
                    raise
                answer = QMessageBox.question(
                    self,
                    "Sobrescrever perfil",
                    f"{exc}. Deseja sobrescrever o perfil existente?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                names = self.profile_manager.import_profiles(path, overwrite=True)
            self._refresh_profiles(names[0])
            self.status.setText(f"Perfis importados: {', '.join(names)}")
        except (OSError, ValueError) as exc:
            self.status.setText(f"Falha ao importar: {exc}")

    def _calibration_wizard(self):
        if self.worker is None or not self.worker.isRunning():
            self.status.setText("Inicie a câmera antes de calibrar o gesto de clique.")
            return
        if self._calibration_phase is not None:
            self.status.setText("A calibração já está em andamento.")
            return
        self._pinch_samples = []
        self._neutral_samples = []
        self._begin_calibration_capture("pinch")

    def _begin_calibration_capture(self, phase):
        if self.worker is None or not self.worker.isRunning():
            self._calibration_phase = None
            self.status.setText("Calibração cancelada: câmera não está ativa.")
            return
        self._calibration_phase = phase
        self.worker.set_calibration_capture(True)
        if phase == "pinch":
            self.status.setText("CALIBRAÇÃO 1/2 — mantenha polegar e médio encostados por 2,5 s.")
        else:
            self.status.setText("CALIBRAÇÃO 2/2 — relaxe a mão e afaste os dedos por 2,5 s.")
        QTimer.singleShot(2500, lambda current=phase: self._finish_calibration_capture(current))

    def _finish_calibration_capture(self, phase):
        if self._calibration_phase != phase:
            return
        self.worker.set_calibration_capture(False)
        self._calibration_phase = None
        samples = self._pinch_samples if phase == "pinch" else self._neutral_samples
        if len(samples) < 10:
            self.status.setText("Poucas amostras. Mantenha a mão bem visível e tente novamente.")
            return
        if phase == "pinch":
            self.status.setText("Agora afaste o polegar do médio e mantenha a mão relaxada.")
            QTimer.singleShot(900, lambda: self._begin_calibration_capture("neutral"))
            return
        from .gesture_calibration import estimate_pinch_threshold
        try:
            threshold = estimate_pinch_threshold(
                self._pinch_samples,
                self._neutral_samples,
            )
            self.profile["click_pinch_threshold"] = threshold
            self.profile_sliders["click_pinch_threshold"].setValue(round(threshold * 100))
            self.status.setText(
                f"Calibração concluída: limiar {threshold:.2f}. "
                "Teste a pinça e clique em Salvar para guardar no perfil."
            )
        except ValueError as exc:
            self.status.setText(f"Calibração não concluída: {exc}")

    def _collect_calibration_sample(self, value):
        if self._calibration_phase == "pinch":
            self._pinch_samples.append(value)
        elif self._calibration_phase == "neutral":
            self._neutral_samples.append(value)

    def _update_gesture_feedback(self, name, confidence, state):
        self.gesture_label.setText(f"Gesto: {name}")
        self.gesture_state_label.setText(f"Estado: {state}")
        percent = max(0, min(100, int(round(confidence * 100))))
        self.confidence_label.setText(f"Compatibilidade geométrica da pose: {percent}%")
        self.confidence_bar.setValue(percent)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111827; color: #e5e7eb; font-size: 14px; }
            QLabel#title { font-size: 26px; font-weight: 700; color: #f9fafb; }
            QLabel#subtitle, QLabel#note { color: #9ca3af; }
            QLabel#video { background: #030712; border: 1px solid #374151; border-radius: 12px; }
            QLabel#status { background: #1f2937; padding: 12px; border-radius: 8px; }
            QLabel#mode { background: #173b31; color: #86efac; padding: 12px; border-radius: 8px; font-weight: 700; }
            QGroupBox { border: 1px solid #374151; border-radius: 8px; margin-top: 8px; padding: 8px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QListWidget { background: #0b1220; border: 1px solid #374151; border-radius: 8px; }
            QComboBox { background: #1f2937; border: 1px solid #4b5563; border-radius: 5px; padding: 6px; }
            QScrollArea { border: 0; }
            QPushButton { background: #2563eb; border: 0; border-radius: 7px; padding: 9px 14px; }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #374151; color: #9ca3af; }
            QCheckBox { padding: 8px 0; font-weight: 600; }
            QSlider::groove:horizontal { height: 6px; background: #374151; border-radius: 3px; }
            QSlider::handle:horizontal { background: #60a5fa; width: 14px; margin: -5px 0; border-radius: 7px; }
        """)

    def _update_mode_label(self, mode):
        if mode == "keyboard":
            self.mode_label.setText("ATALHOS — mapeamentos configuráveis")
        elif mode == "mouse":
            self.mode_label.setText("MOUSE — cursor, clique/arraste, rolagem e zoom")
        else:
            self.mode_label.setText("Câmera parada — o próximo início selecionará Mouse")

    def _set_profile_controls_enabled(self, enabled):
        for widget in self._profile_widgets:
            widget.setEnabled(enabled)

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            return
        profile = self._profile_from_controls()
        self._update_mode_label("mouse")
        self.worker = CameraWorker(camera_index=self.camera_index,
                                   execute=self.execute_checkbox.isChecked(),
                                   motion_sensitivity=profile["motion_sensitivity"],
                                   profile=profile, parent=self)
        self.worker.frame_ready.connect(self._show_frame)
        self.worker.status_changed.connect(self.status.setText)
        self.worker.gesture_feedback.connect(self._update_gesture_feedback)
        self.worker.calibration_sample.connect(self._collect_calibration_sample)
        self.worker.action_recorded.connect(self._add_history)
        self.worker.mode_changed.connect(self._update_mode_label)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.execute_checkbox.setEnabled(False)
        self._set_profile_controls_enabled(False)
        self.calibrate_button.setEnabled(True)
        self.pause_button.setText("Pausar")

    def stop_camera(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Encerrando câmera...")
            self.worker.requestInterruption()
            if not self.worker.wait(5000):
                self.status.setText("A câmera ainda está encerrando; aguarde a liberação segura.")
                return
        self._worker_finished()

    def toggle_pause(self):
        if self.worker is None or not self.worker.isRunning():
            return
        paused = self.pause_button.text() == "Pausar"
        self.worker.set_paused(paused)
        self.pause_button.setText("Retomar" if paused else "Pausar")
        self.status.setText("Reconhecimento pausado; arraste cancelado com segurança." if paused else "Reconhecimento retomado.")

    def _show_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video.setPixmap(pixmap.scaled(self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))

    def _add_history(self, timestamp, gesture, action):
        self.history.insertItem(0, f"{timestamp}  |  {gesture}  →  {action}")
        while self.history.count() > 200:
            self.history.takeItem(self.history.count() - 1)

    def _worker_finished(self):
        if self.worker is not None:
            self.worker.set_calibration_capture(False)
        self._calibration_phase = None
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.execute_checkbox.setEnabled(True)
        self._set_profile_controls_enabled(True)
        self.calibrate_button.setEnabled(False)
        self.pause_button.setText("Pausar")
        self.video.clear()
        self.video.setText("Câmera desligada")
        self._update_mode_label(None)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            if not self.worker.wait(5000):
                self.status.setText("Aguarde o encerramento seguro da câmera antes de fechar.")
                event.ignore()
                return
        event.accept()


def launch(camera_index=0, motion_sensitivity=None, execute_default=False, profile_name="Default"):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(camera_index, motion_sensitivity, execute_default, profile_name)
    window.show()
    return app.exec()
