"""PySide6 interface with profiles, live calibration and mouse controls."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
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
        try:
            self.profile_names = self.profile_manager.names()
        except ValueError as exc:
            self.profile_names = ["Default"]
            self.profile_error = str(exc)

        if profile_name not in self.profile_names:
            self.profile_name = "Default"
            self.profile_error = (
                f"Perfil '{profile_name}' não encontrado; usando Default."
            )
        else:
            self.profile_name = profile_name

        try:
            self.profile = self.profile_manager.load(self.profile_name)
        except (KeyError, ValueError) as exc:
            self.profile_name = "Default"
            self.profile = dict(DEFAULT_PROFILE)
            self.profile_error = str(exc)

        if motion_sensitivity is not None:
            self.profile["motion_sensitivity"] = motion_sensitivity

        self.setWindowTitle("Controle do computador por gestos")
        self.resize(1320, 850)
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
        subtitle = QLabel(
            "Webcam processada localmente • sem gravação de vídeo"
        )
        subtitle.setObjectName("subtitle")
        page.addWidget(title)
        page.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(14)
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
        scroll.setMinimumWidth(430)
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
        mode_layout.addWidget(self.mode_label)
        mode_layout.addWidget(self.status)
        side.addWidget(mode_group)

        self.execute_checkbox = QCheckBox(
            "Executar ações reais no computador"
        )
        self.execute_checkbox.setChecked(execute_default)
        side.addWidget(self.execute_checkbox)
        safety_note = QLabel(
            "Desmarcado = modo de teste. Marque para permitir cursor, "
            "cliques, arraste, atalhos, rolagem e zoom reais."
        )
        safety_note.setWordWrap(True)
        safety_note.setObjectName("note")
        side.addWidget(safety_note)

        profile_group = QGroupBox("PERFIS, MAPEAMENTOS E CALIBRAÇÃO")
        form = QFormLayout(profile_group)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.profile_names)
        self.profile_combo.setCurrentText(self.profile_name)
        self.profile_combo.currentTextChanged.connect(
            self._load_selected_profile
        )
        form.addRow("Perfil", self.profile_combo)

        self.profile_sliders = {}
        self.profile_value_labels = {}
        self._add_slider(form, "Sensibilidade dos deslizes", "motion_sensitivity", 5, 20, 10, "{:.1f}")
        self._add_slider(form, "Suavização do cursor", "cursor_smoothing", 10, 90, 100, "{:.2f}")
        self._add_slider(form, "Margem da área ativa (%)", "cursor_margin", 5, 25, 100, "{:.0f}%", display_percent=True)
        self._add_slider(form, "Intervalo de rolagem (s)", "scroll_repeat_seconds", 8, 50, 100, "{:.2f} s")
        self._add_slider(form, "Intervalo do zoom (s)", "zoom_repeat_seconds", 10, 60, 100, "{:.2f} s")
        self._add_slider(form, "Intervalo entre ações (s)", "action_switch_delay_seconds", 5, 30, 10, "{:.1f} s")

        mapping_group = QGroupBox("Mapeamentos dos atalhos")
        mapping_form = QFormLayout(mapping_group)
        self.mapping_combos = {}
        mapping_labels = {
            "thumb_up": "Polegar para cima",
            "thumb_down": "Polegar para baixo",
            "swipe_left": "Deslize para a esquerda",
            "swipe_right": "Deslize para a direita",
        }
        for mapping_key, label in mapping_labels.items():
            combo = QComboBox()
            for action in sorted(SHORTCUTS):
                combo.addItem(action, action)
            self.mapping_combos[mapping_key] = combo
            mapping_form.addRow(label, combo)
            self._profile_widgets.append(combo)
        form.addRow(mapping_group)

        profile_buttons = QHBoxLayout()
        self.save_profile_button = QPushButton("Salvar perfil")
        self.save_profile_button.clicked.connect(self._save_profile)
        self.new_profile_button = QPushButton("Criar perfil")
        self.new_profile_button.clicked.connect(self._create_profile)
        profile_buttons.addWidget(self.save_profile_button)
        profile_buttons.addWidget(self.new_profile_button)
        form.addRow(profile_buttons)
        side.addWidget(profile_group)

        calibration_note = QLabel(
            "A moldura rosa no vídeo mostra a área do cursor. Ajuste a margem; "
            "uma margem menor amplia a área útil. Os ajustes ficam salvos "
            "no perfil selecionado."
        )
        calibration_note.setWordWrap(True)
        calibration_note.setObjectName("note")
        side.addWidget(calibration_note)

        history_group = QGroupBox("HISTÓRICO DE AÇÕES")
        history_layout = QVBoxLayout(history_group)
        self.history = QListWidget()
        self.history.setObjectName("history")
        self.history.setMinimumHeight(150)
        history_layout.addWidget(self.history)
        self.clear_history_button = QPushButton("Limpar histórico")
        self.clear_history_button.clicked.connect(self.history.clear)
        history_layout.addWidget(self.clear_history_button)
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

        footer = QLabel(
            "Mouse: indicador sozinho move; dois dedos rolam; polegar+indicador "
            "ajustam zoom; toque rápido polegar+médio clica e segurar inicia "
            "arraste. Atalhos: mão aberta-punho-mão aberta. Para voltar a "
            "Mouse: punho-mão aberta-punho-mão aberta. Poses estabilizam em "
            "0,25 s; 1,5 s é o intervalo inicial entre ações pontuais."
        )
        footer.setWordWrap(True)
        footer.setObjectName("note")
        page.addWidget(footer)

        self._profile_widgets.extend([
            self.profile_combo,
            self.save_profile_button,
            self.new_profile_button,
        ])

    def _add_slider(self, form, label, key, minimum, maximum, scale,
                    format_string, display_percent=False):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        value_label = QLabel()
        self.profile_sliders[key] = slider
        self.profile_value_labels[key] = value_label

        def update_label(value, setting=key, factor=scale,
                         template=format_string, percent=display_percent):
            shown = value / factor
            if percent:
                shown *= 100
            value_label.setText(template.format(shown))

        slider.valueChanged.connect(update_label)
        row_layout.addWidget(slider, 1)
        row_layout.addWidget(value_label)
        form.addRow(label, row)
        self._profile_widgets.append(slider)

    def _profile_from_controls(self):
        profile = {
            "motion_sensitivity": self.profile_sliders["motion_sensitivity"].value() / 10,
            "cursor_smoothing": self.profile_sliders["cursor_smoothing"].value() / 100,
            "cursor_margin": self.profile_sliders["cursor_margin"].value() / 100,
            "scroll_repeat_seconds": self.profile_sliders["scroll_repeat_seconds"].value() / 100,
            "zoom_repeat_seconds": self.profile_sliders["zoom_repeat_seconds"].value() / 100,
            "action_switch_delay_seconds": self.profile_sliders["action_switch_delay_seconds"].value() / 10,
            "mappings": {
                key: combo.currentData()
                for key, combo in self.mapping_combos.items()
            },
        }
        return ProfileManager.validate_profile(profile)

    def _set_profile_controls(self, profile):
        scales = {
            "motion_sensitivity": 10,
            "cursor_smoothing": 100,
            "cursor_margin": 100,
            "scroll_repeat_seconds": 100,
            "zoom_repeat_seconds": 100,
            "action_switch_delay_seconds": 10,
        }
        for key, slider in self.profile_sliders.items():
            slider.setValue(round(profile[key] * scales[key]))
        for key, combo in self.mapping_combos.items():
            index = combo.findData(profile["mappings"][key])
            if index >= 0:
                combo.setCurrentIndex(index)

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
            self.profile = self.profile_manager.save(
                name,
                self._profile_from_controls(),
            )
            self.profile_name = name
            self.status.setText(f"Perfil '{name}' salvo.")
        except (ValueError, OSError) as exc:
            self.status.setText(f"Não foi possível salvar o perfil: {exc}")

    def _create_profile(self):
        name, accepted = QInputDialog.getText(
            self,
            "Criar perfil",
            "Nome do novo perfil:",
        )
        if not accepted:
            return
        try:
            profile = self.profile_manager.save(
                name,
                self._profile_from_controls(),
            )
            if self.profile_combo.findText(name.strip()) < 0:
                self.profile_combo.addItem(name.strip())
            self.profile_combo.setCurrentText(name.strip())
            self.profile = profile
            self.profile_name = name.strip()
            self.status.setText(f"Perfil '{self.profile_name}' criado.")
        except (ValueError, OSError) as exc:
            self.status.setText(f"Não foi possível criar o perfil: {exc}")

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
            self.mode_label.setText(
                "MOUSE — cursor, clique/arraste, rolagem e zoom"
            )
        else:
            self.mode_label.setText(
                "Câmera parada — o próximo início selecionará Mouse"
            )

    def _set_profile_controls_enabled(self, enabled):
        for widget in self._profile_widgets:
            widget.setEnabled(enabled)

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            return
        profile = self._profile_from_controls()
        self._update_mode_label("mouse")
        self.worker = CameraWorker(
            camera_index=self.camera_index,
            execute=self.execute_checkbox.isChecked(),
            motion_sensitivity=profile["motion_sensitivity"],
            profile=profile,
            parent=self,
        )
        self.worker.frame_ready.connect(self._show_frame)
        self.worker.status_changed.connect(self.status.setText)
        self.worker.action_recorded.connect(self._add_history)
        self.worker.mode_changed.connect(self._update_mode_label)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.execute_checkbox.setEnabled(False)
        self._set_profile_controls_enabled(False)
        self.pause_button.setText("Pausar")

    def stop_camera(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Encerrando câmera...")
            self.worker.requestInterruption()
            if not self.worker.wait(5000):
                self.status.setText(
                    "A câmera ainda está encerrando; aguarde a liberação segura."
                )
                return
        self._worker_finished()

    def toggle_pause(self):
        if self.worker is None or not self.worker.isRunning():
            return
        paused = self.pause_button.text() == "Pausar"
        self.worker.set_paused(paused)
        self.pause_button.setText("Retomar" if paused else "Pausar")
        self.status.setText(
            "Reconhecimento pausado; arraste cancelado com segurança."
            if paused
            else "Reconhecimento retomado."
        )

    def _show_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video.setPixmap(
            pixmap.scaled(
                self.video.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _add_history(self, timestamp, gesture, action):
        self.history.insertItem(
            0,
            f"{timestamp}  |  {gesture}  →  {action}",
        )
        while self.history.count() > 200:
            self.history.takeItem(self.history.count() - 1)

    def _worker_finished(self):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.execute_checkbox.setEnabled(True)
        self._set_profile_controls_enabled(True)
        self.pause_button.setText("Pausar")
        self.video.clear()
        self.video.setText("Câmera desligada")
        self._update_mode_label(None)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.requestInterruption()
            if not self.worker.wait(5000):
                self.status.setText(
                    "Aguarde o encerramento seguro da câmera antes de fechar."
                )
                event.ignore()
                return
        event.accept()


def launch(camera_index=0, motion_sensitivity=None, execute_default=False,
           profile_name="Default"):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        camera_index,
        motion_sensitivity,
        execute_default,
        profile_name,
    )
    window.show()
    return app.exec()
