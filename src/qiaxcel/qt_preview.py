"""Native Qt PDF viewing and explicitly calibrated graph measurements."""
from io import BytesIO
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGraphicsScene,
    QGraphicsView, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from .core import file_sha256


class PageRenderer(QObject):
    rendered = pyqtSignal(bytes, int)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, source, page, expected_hash=''):
        super().__init__()
        self.source, self.page, self.expected_hash = source, page, expected_hash

    def run(self):
        try:
            import pdfplumber
            if self.expected_hash and file_sha256(self.source) != self.expected_hash:
                raise ValueError('Kildefilen er endret etter innlesing. Les rapporten på nytt før kontroll.')
            with pdfplumber.open(self.source) as pdf:
                if not 1 <= self.page <= len(pdf.pages):
                    raise ValueError('Siden finnes ikke i rapporten.')
                image = pdf.pages[self.page - 1].to_image(resolution=115).original
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                self.rendered.emit(buffer.getvalue(), len(pdf.pages))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class PageView(QGraphicsView):
    clicked = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor('#E5EDF1'))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setAccessibleName('PDF-side. Bruk zoomknappene for større visning.')
        self.image_item = None
        self.measurement_mode = False

    def set_image(self, png):
        image = QImage.fromData(png)
        if image.isNull():
            raise ValueError('PDF-siden kunne ikke tegnes.')
        self.scene().clear()
        self.image_item = self.scene().addPixmap(QPixmap.fromImage(image))
        self.scene().setSceneRect(self.image_item.boundingRect())
        self.fit_width()

    def fit_width(self):
        if self.image_item is not None:
            self.resetTransform()
            ratio = max(1, self.viewport().width() - 24) / self.image_item.boundingRect().width()
            self.scale(ratio, ratio)
            self.verticalScrollBar().setValue(0)
            self.horizontalScrollBar().setValue(0)

    def fit_page(self):
        if self.image_item is not None:
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event):
        if self.measurement_mode and self.image_item is not None and event.button() == Qt.MouseButton.LeftButton:
            point = self.mapToScene(event.position().toPoint())
            if self.image_item.boundingRect().contains(point):
                self.clicked.emit(point.x(), point.y())
            return
        super().mousePressEvent(event)


class PdfPreview(QWidget):
    loaded = pyqtSignal()
    loading = pyqtSignal()
    invalidated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None
        self.png = None
        self.loaded_identity = None
        self._render_identity = None
        self.source = ''
        self.expected_hash = ''
        self.available_pages = 9999
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.page_box = QSpinBox()
        self.page_box.setRange(1, 9999)
        self.page_box.setPrefix('Side ')
        self.page_box.setAccessibleName('PDF-side som skal vises')
        controls.addWidget(self.page_box)
        self.load_button = QPushButton('Vis side')
        self.load_button.clicked.connect(self.load_page)
        controls.addWidget(self.load_button)
        controls.addStretch()
        for text, callback in [('−', lambda: self.view.scale(0.8, 0.8)),
                               ('+', lambda: self.view.scale(1.25, 1.25)),
                               ('Tilpass', lambda: self.view.fit_page())]:
            button = QPushButton(text)
            button.setAccessibleName({'−': 'Zoom ut', '+': 'Zoom inn'}.get(text, 'Tilpass side'))
            button.clicked.connect(callback)
            if text != 'Tilpass':
                button.setMaximumWidth(34)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.view = PageView()
        self.view.setMinimumHeight(150)
        layout.addWidget(self.view, 1)
        self.message = QLabel('')
        self.message.setWordWrap(True)
        self.message.setObjectName('muted')
        layout.addWidget(self.message)
        self.page_box.valueChanged.connect(self._page_changed)

    @property
    def identity(self):
        return (str(self.source), self.page_box.value(), self.expected_hash)

    def has_current_image(self):
        return self.png is not None and self.loaded_identity == self.identity

    def invalidate_image(self):
        self.png = None
        self.loaded_identity = None
        self.view.scene().clear()
        self.view.image_item = None
        self.invalidated.emit()

    def _page_changed(self):
        self.invalidate_image()
        self.message.setText('')

    def set_source(self, source, page, expected_hash=''):
        if (str(source), max(1, page), expected_hash) == self.identity:
            return
        self.source, self.expected_hash = source, expected_hash
        self.page_box.setMaximum(9999)
        self.page_box.setValue(max(1, page))
        self.invalidate_image()
        self.message.setText('')

    def load_page(self):
        if self.thread is not None or not self.source:
            return
        self.invalidate_image()
        self.loading.emit()
        self.load_button.setEnabled(False)
        self.message.setText('Tegner PDF-side …')
        source, page, expected_hash = self.source, self.page_box.value(), self.expected_hash
        self._render_identity = self.identity
        self.thread = QThread(self)
        self.worker = PageRenderer(source, page, expected_hash)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.rendered.connect(self._show_page)
        self.worker.failed.connect(self._show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _show_page(self, png, count):
        # Ignore a completed render when selection changed during the render.
        if self._render_identity != self.identity:
            return
        self.png = png
        self.loaded_identity = self.identity
        self.available_pages = count
        self.page_box.setMaximum(count)
        self.view.set_image(png)
        self.message.setText(f'{Path(self.source).name} · side {self.page_box.value()} av {count}')
        self.loaded.emit()

    def _show_error(self, message):
        if self._render_identity == self.identity:
            self.invalidate_image()
            self.message.setText(message)

    def _finished(self):
        self.thread = None
        self.load_button.setEnabled(True)

    def is_busy(self):
        return self.thread is not None


class GraphDialog(QDialog):
    """Coordinates measure RFU only; fragment size must come from a label/table."""
    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Kalibrert grafavlesning')
        available = self.screen().availableGeometry()
        self.resize(min(1000, available.width() - 60), min(800, available.height() - 80))
        self.original_result = result
        self.raw_height = None
        self.calibration_note = ''
        self.points = []
        self.source_page = result.peak.page if result.peak else result.sample.header_page
        layout = QVBoxLayout(self)
        heading = QLabel('Grafavlesning')
        heading.setObjectName('sectionTitle')
        layout.addWidget(heading)
        row = QHBoxLayout()
        self.value0 = QDoubleSpinBox()
        self.value1 = QDoubleSpinBox()
        for spin in (self.value0, self.value1):
            spin.setRange(0, 100000000)
            spin.setDecimals(2)
            spin.setSuffix(' RFU')
        self.value1.setValue(5000)
        form = QFormLayout()
        form.addRow('Nedre referanse:', self.value0)
        form.addRow('Øvre referanse:', self.value1)
        row.addLayout(form)
        row.addStretch()
        reset = QPushButton('Nullstill punkter')
        reset.clicked.connect(self.reset_points)
        row.addWidget(reset)
        layout.addLayout(row)
        self.preview = PdfPreview()
        self.preview.set_source(result.sample.source, self.source_page, result.sample.source_sha256)
        self.preview.view.measurement_mode = True
        self.preview.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.preview.view.clicked.connect(self.pick_point)
        self.preview.loaded.connect(self.reset_points)
        self.preview.loading.connect(self.reset_points)
        self.preview.invalidated.connect(self.reset_points)
        layout.addWidget(self.preview, 1)
        self.instruction = QLabel('Nedre referanse')
        self.instruction.setWordWrap(True)
        self.instruction.setObjectName('notice')
        layout.addWidget(self.instruction)
        self.values_label = QLabel('Ingen RFU beregnet.')
        self.values_label.setObjectName('sectionTitle')
        layout.addWidget(self.values_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.use_button = self.buttons.addButton('Bruk i manuell kontroll', QDialogButtonBox.ButtonRole.AcceptRole)
        self.use_button.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.value0.valueChanged.connect(self.calculate)
        self.value1.valueChanged.connect(self.calculate)
        self.preview.page_box.valueChanged.connect(self.reset_points)
        self.preview.load_page()

    def reset_points(self):
        self.points = []
        self.raw_height = None
        self.calibration_note = ''
        self.use_button.setEnabled(False)
        self.values_label.setText('Ingen RFU beregnet.')
        self.instruction.setText('Nedre referanse')
        if self.preview.has_current_image():
            self.preview.view.set_image(self.preview.png)

    def pick_point(self, x, y):
        if not self.preview.has_current_image() or len(self.points) >= 3:
            return
        self.points.append((x, y))
        scene = self.preview.view.scene()
        scene.addEllipse(x - 5, y - 5, 10, 10, QPen(QColor('#BE123C'), 2))
        label = scene.addText(str(len(self.points)))
        label.setDefaultTextColor(QColor('#BE123C'))
        label.setPos(x + 6, y - 15)
        if len(self.points) == 1:
            self.instruction.setText('Øvre referanse')
        elif len(self.points) == 2:
            self.instruction.setText('Topp')
        self.calculate()

    def calculate(self):
        self.use_button.setEnabled(False)
        self.raw_height = None
        if not self.preview.has_current_image() or len(self.points) != 3:
            return
        try:
            from .graph import rfu_from_y
            rfu = rfu_from_y(self.points[0][1], self.value0.value(), self.points[1][1],
                             self.value1.value(), self.points[2][1])
            if self.original_result.factor is None:
                raise ValueError('RFU-skala må bekreftes før grafavlesning kan brukes.')
            self.raw_height = rfu / self.original_result.factor
            self.source_page = self.preview.page_box.value()
            self.calibration_note = (
                f'Kalibrering side {self.source_page}: '
                f'y={self.points[0][1]:.6f} → {self.value0.value():.12g} RFU; '
                f'y={self.points[1][1]:.6f} → {self.value1.value():.12g} RFU; '
                f'topp y={self.points[2][1]:.6f} → {rfu:.12g} RFU '
                '(originale bildepiksler ved 115 dpi).')
            self.values_label.setText(f'Estimat: {rfu:,.1f} RFU'.replace(',', ' '))
            self.instruction.setText('Kontroller avlesningen.')
            self.use_button.setEnabled(True)
        except ValueError as exc:
            self.values_label.setText('Avlesning kan ikke brukes.')
            self.instruction.setText(str(exc))

    def reject(self):
        if self.preview.is_busy():
            self.instruction.setText('Vent til PDF-siden er ferdig tegnet før du lukker.')
            return
        super().reject()

    def accept(self):
        if not self.preview.has_current_image() or self.raw_height is None or self.preview.is_busy():
            self.instruction.setText('Last riktig PDF-side og utfør en ny kalibrering før verdien brukes.')
            return
        super().accept()

    def closeEvent(self, event):
        if self.preview.is_busy():
            event.ignore()
            return
        super().closeEvent(event)
