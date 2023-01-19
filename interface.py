from image_generator import ImageGenerator, ndarray_to_image

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QGridLayout,
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

        grid = QGridLayout()

        widget = QWidget()
        widget.setLayout(grid)
        self.setCentralWidget(widget)

        self.canvas = QPixmap(512, 512)
        self.canvas.fill(QColor(215, 215, 215))
        self.image_label = QLabel("This is a label")
        self.image_label.setPixmap(self.canvas)
        self.image_label.setBaseSize(self.canvas.size())

        self.progress_bar = QProgressBar()

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Enter promt here")

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.button_clicked)

        self.steps_input = QLineEdit("5")
        self.steps_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.steps_label = QLabel("Steps")

        self.guidence_input = QLineEdit("7.5")
        self.guidence_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.guidence_label = QLabel("Guidence")

        self.seed_input = QLineEdit("-1")
        self.seed_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.seed_label = QLabel("Seed")

        self.count_input = QLineEdit("1")
        self.count_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label = QLabel("Count")

        self.history_frame_duration_input = QLineEdit("100")
        self.history_frame_duration_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_frame_duration_label = QLabel("Frame duration")

        opts = [
            [
                self.steps_label,
                self.steps_input,
                self.guidence_label,
                self.guidence_input,
                self.seed_label,
                self.seed_input,
                self.count_label,
                self.count_input,
            ],
            [
                self.history_frame_duration_label,
                self.history_frame_duration_input,
            ]
        ]

        max_opts = max([len(opt) for opt in opts])
        px = max_opts
        cur = 0

        # add widgets to layout
        grid.addWidget(self.image_label, 0, 0, px, px, Qt.AlignmentFlag.AlignCenter)
        cur += px

        grid.addWidget(self.progress_bar, cur, 0, 1, px)
        cur += 1

        grid.addWidget(self.prompt_input, cur, 0, 1, px)
        cur += 1

        grid.addWidget(self.generate_button, cur, 0, 1, px)
        cur += 1

        for i, opt in enumerate(opts):
            for j, widget in enumerate(opt):
                grid.addWidget(widget, i + cur, j, 1, 1)
        cur += 1

        self.inited = False
        self.setFixedWidth(self.canvas.width())

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
            self.generate_button.setEnabled(False)
            return True
    
    def exit_generating_mode(self):
        self.generate_button.setEnabled(True)
    
    def button_clicked(self):
        if not self.enter_generating_mode():
            return

        prompt = self.prompt_input.toPlainText()
        steps = int(self.steps_input.text())
        guidence = float(self.guidence_input.text())
        seed = int(self.seed_input.text())
        count = int(self.count_input.text())

        if seed == -1:
            seed = randint(0, 2**32 - 1)

        self.image_generator.history_frame_duration = int(self.history_frame_duration_input.text())

        self.image_generator.logger.info(f"Prompt: {prompt}, guidence: {guidence}, seed: {seed}, count: {count}")
        Thread(target=self.generate_thread, args=(prompt, steps, guidence, seed, count)).start()
    
    def create_step_callback(self):
        def callback(iter, time_left, image):
            self.qt_image = ndarray_to_image(image)

            self.canvas_sync.emit()
            self.progress_bar.setValue(iter)

        return callback
    
    def generate_thread(self, prompt, steps, guidence, seed, count):
        for i in range(count):
            steps += 1024 * i
            self.logger.info(f"Prompt: {prompt}, guidence: {guidence}, seed: {seed}")
            self.set_max_progress(steps)

            self.image_generator(prompt, steps, guidence, seed, self.callback)
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
