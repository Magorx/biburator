from image_generator import ImageGenerator, ndarray_to_image

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QGridLayout, QHBoxLayout, QVBoxLayout,
    QProgressBar,
    QCheckBox,
    QWIDGETSIZE_MAX
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter

from random import randint
from threading import Thread


class MainWindow(QMainWindow):
    canvas_sync = pyqtSignal()

    def __init__(self, image_generator):
        super(MainWindow, self).__init__()
        self.image_generator = image_generator
        self.logger = image_generator.logger

        self.init_ui()
        self.callback = self.create_step_callback()

    def init_ui(self):
        self.setWindowTitle("Biburator")

        self.canvas_512 = QPixmap(512, 512)
        self.canvas_512.fill(QColor(215, 215, 215))
        self.canvas_64 = QPixmap(64, 64)
        self.canvas_64.fill(QColor(215, 215, 215))

        self.canvas = self.canvas_512

        self.image_label = QLabel("This is a label")
        self.image_label.setPixmap(self.canvas)
        self.image_label.setBaseSize(self.canvas.size())

        self.image_label.mouseDoubleClickEvent = lambda event: QApplication.clipboard().setPixmap(self.canvas)

        self.progress_bar = QProgressBar()

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Promt")

        self.negative_prompt_input = QTextEdit()
        self.negative_prompt_input.setPlaceholderText("Negative promt")

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.button_clicked)

        self.steps_input = QLineEdit("25")
        self.steps_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.steps_label = QLabel("Steps")
        self.steps_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.guidence_input = QLineEdit("7.5")
        self.guidence_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.guidence_label = QLabel("Guidence")

        self.seed_input = QLineEdit("-1")
        self.seed_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.seed_label = QLabel("Seed")
        self.seed_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.count_input = QLineEdit("1")
        self.count_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label = QLabel("Count")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.history_frame_duration_input = QLineEdit("-1")
        self.history_frame_duration_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_frame_duration_label = QLabel("GIF ms")
        self.history_frame_duration_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        grid = QGridLayout()

        widget = QWidget()
        widget.setLayout(hlayout)
        self.setCentralWidget(widget)

        hlayout.addLayout(vlayout)

        vlayout.addWidget(self.prompt_input)
        vlayout.addWidget(self.negative_prompt_input)
        vlayout.addWidget(self.generate_button)

        opts = [
            [ self.steps_label, self.steps_input ],
            [ self.guidence_label, self.guidence_input ],
            [ self.seed_label, self.seed_input ],
            [ self.count_label, self.count_input ],
            [ self.history_frame_duration_label, self.history_frame_duration_input ]
        ]

        for i, opt in enumerate(opts):
            for j, widget in enumerate(opt):
                grid.addWidget(widget, i, j)
        vlayout.addLayout(grid)

        vl = QVBoxLayout()
        vl.addWidget(self.image_label)
        vl.addWidget(self.progress_bar)
        hlayout.addLayout(vl)

        self.inited = False
        # self.setFixedWidth(self.canvas.width())

        self.canvas_sync.connect(self.redraw_canvas)
    
    def redraw_canvas(self):
        painter = QPainter(self.canvas)
        painter.drawImage(0, 0, self.qt_image)
        painter.end()

        self.image_label.setPixmap(self.canvas)
    
    def set_max_progress(self, max_progress):
        self.max_progress = max_progress
        self.progress_bar.setRange(0, max_progress)
    
    def center(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init(self):
        if self.inited:
            return
        self.inited = True

        self.center()

        self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.setMinimumSize(0, 0)

    def resizeEvent(self, event):
        if not self.inited:
            self.init()
    
    def enter_generating_mode(self):
        if self.image_generator.is_generating:
            return False
        else:
            self.generate_button.setText("Cancel")
            return True
    
    def exit_generating_mode(self):
        self.generate_button.setText("Generate")
        self.generate_button.setEnabled(True)
        self.callback(0, 0, self.image_generator.image)
    
    def button_clicked(self):
        if self.image_generator.is_generating:
            self.image_generator.cancel_generation()
            return

        if not self.enter_generating_mode():
            return

        prompt = self.prompt_input.toPlainText()
        negative_prompt = self.negative_prompt_input.toPlainText()
        steps = int(self.steps_input.text())
        guidence = float(self.guidence_input.text())
        seed = int(self.seed_input.text())
        count = int(self.count_input.text())

        if seed == -1:
            seed = randint(0, 2**32 - 1)

        self.image_generator.history_frame_duration = int(self.history_frame_duration_input.text())

        self.image_generator.logger.info(f"Prompt: {prompt}")
        self.image_generator.logger.info(f"negative prompt: {negative_prompt}")
        self.image_generator.logger.info(f"guidence: {guidence}, seed: {seed}, count: {count}")
        Thread(target=self.generate_thread, args=(prompt, negative_prompt, steps, guidence, seed, count)).start()
    
    def create_step_callback(self):
        def callback(iter, time_left, image):
            self.progress_bar.setValue(iter)

            if image.shape != (512, 512, 3):
                return

            self.qt_image = ndarray_to_image(image)
            self.canvas_sync.emit()

        return callback
    
    def generate_thread(self, prompt, negative_prompt, steps, guidence, seed, count):
        for i in range(count):
            seed += 1024 * i
            self.logger.info(f"Seed: {seed}")
            self.set_max_progress(steps)

            self.image_generator(prompt, negative_prompt, steps, guidence, seed, self.callback)
            self.progress_bar.setValue(0)

        self.exit_generating_mode()


class UI:
    app = QApplication([])

    def __init__(self, model, logger, args={}) -> None:
        self.image_generator = ImageGenerator(model, logger, args)
    
        self.window = MainWindow(self.image_generator)
        self.window.show()
        
    def exec(self):
        UI.app.exec()
