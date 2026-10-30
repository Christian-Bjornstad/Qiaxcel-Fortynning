"""Local PyQt6 workbench for explicit fragment selection and traceable review."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys

from PyQt6.QtCore import QObject, QThread, Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QProgressBar,
    QSpinBox, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)

from . import __version__
from .core import ASSAYS, analyze, read_pdf, review_result
from .excel import export_workbook, fill_template
from .qt_preview import GraphDialog, PdfPreview


SCALES = {'Ubekreftet': None,
          '×1000 · 2,71 → 2710 RFU': 1000,
          '×1 · 2710 → 2710 RFU': 1}
DILUTIONS = ['Ufortynnet', '1:2', '1:5', '1:10', '1:15', '1:20', 'Kontrollprøve']
ASSETS = Path(__file__).parent / 'assets'

STYLE = '''
QWidget { font-family: "Segoe UI"; font-size: 10pt; color: #173746; }
QMainWindow, QWidget#workspace { background: #F2F6F8; }
QFrame#sidebar { background: #123443; border: none; }
QLabel#brand { color: #FFFFFF; font-size: 16pt; font-weight: 650; }
QPushButton#nav { background: transparent; color: #D6E5ED; text-align: left;
    border: none; border-radius: 7px; padding: 12px 16px; font-weight: 550; }
QPushButton#nav:hover { background: #1A4658; }
QPushButton#nav:checked { background: #22566A; color: #FFFFFF; border-left: 3px solid #22D3EE; }
QLabel#pageTitle { font-size: 23pt; font-weight: 650; color: #123443; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 600; }
QLabel#muted { color: #526A77; }
QLabel#eyebrow { color: #416576; font-size: 9pt; font-weight: 650; }
QLabel#notice { background: #FFF5DF; border: 1px solid #DEC68E; color: #634800;
    border-radius: 6px; padding: 10px; }
QFrame#card { background: white; border: 1px solid #D6E2E8; border-radius: 8px; }
QLabel#metricValue { font-size: 20pt; font-weight: 650; color: #164E63; }
QLabel#metricLabel { color: #526A77; font-size: 9pt; }
QPushButton { background: white; border: 1px solid #B6C9D3; border-radius: 5px;
    padding: 7px 12px; min-height: 19px; font-weight: 550; }
QPushButton:hover { border-color: #087E9B; background: #EDF9FC; }
QPushButton:pressed { background: #D5EEF4; }
QPushButton:focus { border: 2px solid #087E9B; padding: 6px 11px; }
QPushButton:disabled { color: #81939D; background: #EDF1F3; border-color: #D8E2E7; }
QPushButton#primary { background: #087E9B; color: white; border-color: #087E9B; }
QPushButton#primary:hover { background: #076A83; border-color: #076A83; }
QPushButton#primary:disabled { background: #B5C8D0; border-color: #B5C8D0; color: #FFFFFF; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { background: white;
    border: 1px solid #AFC4CF; border-radius: 4px; padding: 6px; selection-background-color: #087E9B; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus { border: 2px solid #087E9B; }
QComboBox::drop-down { border: none; width: 22px; }
QTableWidget, QListWidget { background: white; border: 1px solid #CCDCE5;
    border-radius: 5px; gridline-color: #E5EDF1; selection-background-color: #CDEBF3; selection-color: #123443; }
QTableWidget { alternate-background-color: #F7FAFB; }
QHeaderView::section { background: #EDF3F6; padding: 8px; border: none;
    border-right: 1px solid #DBE6EC; border-bottom: 1px solid #DBE6EC; color: #355465; font-weight: 600; }
QTableWidget::item { padding: 5px; border-bottom: 1px solid #EDF2F5; }
QTableWidget::item:selected { background: #CDEBF3; color: #123443; }
QProgressBar { border: 1px solid #CEDCE4; border-radius: 3px; background: #E9EFF3; max-height: 7px; }
QProgressBar::chunk { background: #087E9B; border-radius: 3px; }
QSplitter::handle { background: #DFE8ED; }
QStatusBar { background: #E5EEF3; color: #355465; border-top: 1px solid #CDDEE7; }
QToolTip { color: #173746; background: white; border: 1px solid #98B3C2; padding: 4px; }
'''


def number(value):
    return '—' if value is None else f'{value:.12g}'


def rfu_number(value):
    return '—' if value is None else f'{value:,.12g}'.replace(',', ' ')


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName('primary')
    widget.clicked.connect(callback)
    return widget


def card():
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    return frame, layout


class ReportReader(QObject):
    samples = pyqtSignal(object)
    failure = pyqtSignal(str, str)
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal()

    def __init__(self, paths):
        super().__init__()
        self.paths = paths

    def run(self):
        for index, path in enumerate(self.paths, 1):
            self.progress.emit(index - 1, len(self.paths), Path(path).name)
            try:
                self.samples.emit(read_pdf(path))
            except Exception as exc:
                self.failure.emit(str(path), str(exc))
        self.finished.emit()


class ReviewDialog(QDialog):
    def __init__(self, result, parent=None, *, raw_height=None, source_page=None, method=None,
                 calibration_note=''):
        super().__init__(parent)
        self.original_result = result
        self.result_value = None
        self.method = method
        self.calibration_note = calibration_note
        self.setWindowTitle(f'Kontroller {result.sample.position}')
        self.resize(610, 690)
        layout = QVBoxLayout(self)
        layout.addWidget(label(f'{result.sample.position} · {result.sample.info}', wrap=True))
        if result.note:
            layout.addWidget(label(result.note, 'notice', True))
        if len(result.candidates) > 1 and result.peak is None:
            layout.addWidget(label('Velg først en eksakt topp i kandidatlisten før du lagrer kontroll.', 'notice', True))
        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.assay_box = QComboBox()
        self.assay_box.addItem('Velg analyse', '')
        self.assay_box.addItems(list(ASSAYS))
        self.assay_box.setCurrentText(result.assay or 'Velg analyse')
        self.bp_edit = QLineEdit('' if result.peak is None else str(result.peak.bp))
        self.raw_edit = QLineEdit('' if result.peak is None or result.peak.height is None else str(result.peak.height))
        if raw_height is not None:
            self.raw_edit.setText(str(raw_height))
        self.page_box = QSpinBox()
        self.page_box.setRange(1, 9999)
        self.page_box.setValue(source_page or (result.peak.page if result.peak else result.sample.header_page))
        self.dilution_box = QComboBox()
        self.dilution_box.addItem('Velg konkret fortynning', '')
        self.dilution_box.addItems(DILUTIONS)
        self.dilution_box.setCurrentText(result.dilution if result.dilution in DILUTIONS else 'Velg konkret fortynning')
        if raw_height is not None:
            self.dilution_box.setCurrentIndex(0)
        self.bp_edit.textChanged.connect(lambda: self.dilution_box.setCurrentIndex(0))
        self.raw_edit.textChanged.connect(lambda: self.dilution_box.setCurrentIndex(0))
        self.assay_box.currentIndexChanged.connect(lambda: self.dilution_box.setCurrentIndex(0))
        self.reviewer_edit = QLineEdit(result.reviewer)
        self.comment_edit = QTextEdit(result.review_note)
        self.comment_edit.setMaximumHeight(90)
        for title, widget in [('Analyse', self.assay_box), ('Valgt topp (bp)', self.bp_edit),
                              (f'Råhøyde · faktor {result.factor or "ubekreftet"}', self.raw_edit),
                              ('Kildeside', self.page_box), ('Fortynning etter kontroll', self.dilution_box),
                              ('Kontrollør · navn eller initialer', self.reviewer_edit),
                              ('Kommentar og begrunnelse', self.comment_edit)]:
            form.addRow(title, widget)
            widget.setAccessibleName(title)
        layout.addLayout(form)
        self.live_rfu = label('', 'muted', True)
        layout.addWidget(self.live_rfu)
        self.raw_edit.textChanged.connect(self.show_rfu)
        self.show_rfu()
        self.error_label = label('', 'notice', True)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        save = self.buttons.addButton('Lagre kontroll', QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName('primary')
        self.buttons.accepted.connect(self.save_review)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def show_rfu(self):
        try:
            raw = float(self.raw_edit.text().replace(',', '.'))
            factor = self.original_result.factor
            text = f'{number(raw)} × {factor} = {rfu_number(raw * factor)} RFU' if factor else 'Velg RFU-skala.'
        except ValueError:
            text = 'Oppgi råhøyden i rapportens skala.'
        self.live_rfu.setText(text)

    def save_review(self):
        try:
            comment = self.comment_edit.toPlainText().strip()
            if not comment:
                raise ValueError('Oppgi en kontrollkommentar og begrunnelse.')
            if self.calibration_note:
                comment += ' | ' + self.calibration_note
            self.result_value = review_result(self.original_result, assay=self.assay_box.currentText(),
                bp=float(self.bp_edit.text().replace(',', '.')),
                raw_height=float(self.raw_edit.text().replace(',', '.')),
                reviewer=self.reviewer_edit.text(), comment=comment,
                chosen_dilution=self.dilution_box.currentText(), source_page=self.page_box.value(), method=self.method)
        except ValueError as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        self.accept()


class App(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.paths, self.rows, self.errors = [], [], []
        self.busy = False
        self.unsaved_changes = False
        self.active_settings = {'factor': 1000, 'tolerance': 20}
        self._read_thread = None
        self.setWindowTitle('QIAxcel')
        self.setWindowIcon(QIcon(str(ASSETS / 'qiaxcel.svg')))
        self.resize(1320, 900)
        available = self.screen().availableGeometry()
        self.setMinimumSize(min(980, available.width() - 40), min(600, available.height() - 60))
        self.setStyleSheet(STYLE)
        root = QWidget()
        root.setObjectName('workspace')
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(192)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(16, 25, 16, 18)
        nav.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(self.windowIcon().pixmap(42, 42))
        icon.setAccessibleName('Ett cyan PCR-toppikon')
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(icon)
        brand = label('QIAxcel', 'brand')
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(brand)
        nav.addSpacing(30)
        self.nav_buttons = []
        for index, (text, icon_name) in enumerate([('Rapporter', 'import'), ('Resultater', 'results'),
                                                   ('Eksport', 'export'), ('Innstillinger', 'settings')]):
            item = button(text, lambda checked=False, i=index: self.navigate(i))
            item.setObjectName('nav')
            item.setCheckable(True)
            item.setIcon(QIcon(str(ASSETS / f'{icon_name}.svg')))
            item.setIconSize(QSize(18, 18))
            nav.addWidget(item)
            self.nav_buttons.append(item)
        nav.addStretch()
        outer.addWidget(sidebar)
        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)
        self.build_import_page()
        self.build_results_page()
        self.build_export_page()
        self.build_settings_page()
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.navigate(0)
        self.refresh_files()
        self.refresh()

    def page(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(13)
        layout.addWidget(label(title, 'pageTitle'))
        self.pages.addWidget(widget)
        return layout

    def build_import_page(self):
        layout = self.page('Rapporter')
        box, content = card()
        actions = QHBoxLayout()
        self.choose_files_button = button('Legg til PDF-filer', self.choose_files, True)
        self.choose_folder_button = button('Legg til mappe', self.choose_folder)
        self.clear_button = button('Tøm', self.clear)
        actions.addWidget(self.choose_files_button)
        actions.addWidget(self.choose_folder_button)
        actions.addStretch()
        actions.addWidget(self.clear_button)
        content.addLayout(actions)
        self.recursive = QCheckBox('Ta med undermapper')
        content.addWidget(self.recursive)
        self.file_label = label('Ingen PDF-filer valgt', 'sectionTitle')
        content.addWidget(self.file_label)
        self.file_list = QListWidget()
        self.file_list.setAccessibleName('Valgte PDF-rapporter')
        self.file_list.setMinimumHeight(130)
        content.addWidget(self.file_list, 1)
        self.read_button = button('Les rapporter', self.read, True)
        self.read_button.setMinimumWidth(170)
        content.addWidget(self.read_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(box, 1)
        errors, content = card()
        self.error_card = errors
        self.error_heading = label('Filfeil · ingen', 'sectionTitle')
        content.addWidget(self.error_heading)
        self.error_list = QListWidget()
        self.error_list.setAccessibleName('Filfeil som blir med i eksporten')
        self.error_list.setMaximumHeight(100)
        content.addWidget(self.error_list)
        layout.addWidget(errors)

    def build_results_page(self):
        layout = self.page('Resultater')
        metrics = QHBoxLayout()
        self.metric_labels = []
        for title in ('PRØVER', 'KLARE', 'TIL KONTROLL', 'KONTROLLERT'):
            frame, content = card()
            content.setContentsMargins(14, 9, 14, 9)
            content.setSpacing(2)
            value = label('0', 'metricValue')
            content.addWidget(value)
            content.addWidget(label(title, 'metricLabel'))
            metrics.addWidget(frame)
            self.metric_labels.append(value)
        layout.addLayout(metrics)
        self.scale_notice = label('Velg RFU-skala i Innstillinger.', 'notice', True)
        layout.addWidget(self.scale_notice)
        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Søk …')
        self.search_edit.setAccessibleName('Søk i resultatene')
        self.search_edit.textChanged.connect(self.filter_rows)
        filters.addWidget(self.search_edit, 1)
        self.status_filter = QComboBox()
        self.status_filter.addItems(['Alle statuser', 'KLAR', 'KONTROLL', 'KONTROLLERT'])
        self.status_filter.setAccessibleName('Filtrer status')
        self.status_filter.currentTextChanged.connect(self.filter_rows)
        filters.addWidget(self.status_filter)
        layout.addLayout(filters)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(['Posisjon', 'Prøveinfo', 'Analyse', 'Mål bp', 'Valgt bp', 'RFU', 'Fortynning', 'Status'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column, width in enumerate([75, 200, 115, 70, 75, 85, 115, 115]):
            self.table.setColumnWidth(column, width)
        self.table.setAccessibleName('Prøver med eksakt valgt bp, RFU og kontrollstatus')
        self.table.itemSelectionChanged.connect(self.describe)
        self.table.doubleClicked.connect(self.review)
        splitter.addWidget(self.table)
        lower = QSplitter(Qt.Orientation.Horizontal)
        detail, content = card()
        content.setContentsMargins(14, 12, 14, 12)
        self.detail_heading = label('Velg prøve', 'sectionTitle')
        content.addWidget(self.detail_heading)
        self.detail_label = label('', 'muted', True)
        content.addWidget(self.detail_label)
        self.candidate_table = QTableWidget(0, 3)
        self.candidate_table.setHorizontalHeaderLabels(['Kandidat bp', 'Råhøyde', 'PDF-side'])
        self.candidate_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.candidate_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.candidate_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.candidate_table.verticalHeader().hide()
        self.candidate_table.setMinimumHeight(90)
        self.candidate_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.candidate_table.setAccessibleName('Topper i søkevinduet. Velg en eksakt kandidat.')
        content.addWidget(self.candidate_table, 1)
        choices = QHBoxLayout()
        self.pick_button = button('Velg topp', self.pick_candidate)
        self.review_button = button('Kontroller', self.review, True)
        self.graph_button = button('Graf', self.graph_review)
        choices.addWidget(self.pick_button)
        choices.addWidget(self.review_button)
        choices.addWidget(self.graph_button)
        content.addLayout(choices)
        lower.addWidget(detail)
        preview_card, preview_layout = card()
        preview_layout.setContentsMargins(12, 10, 12, 10)
        self.pdf_preview = PdfPreview()
        preview_layout.addWidget(self.pdf_preview)
        lower.addWidget(preview_card)
        lower.setSizes([560, 450])
        splitter.addWidget(lower)
        splitter.setSizes([290, 300])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        bulk = QHBoxLayout()
        self.assay_box = QComboBox()
        self.assay_box.addItem('Velg analyse', '')
        self.assay_box.addItems(list(ASSAYS))
        self.assay_box.setAccessibleName('Analyse som skal settes på markerte rader')
        bulk.addWidget(self.assay_box)
        self.set_assay_button = button('Sett analyse', self.set_assay)
        bulk.addWidget(self.set_assay_button)
        bulk.addStretch()
        bulk.addWidget(button('Til eksport', lambda: self.navigate(2)))
        layout.addLayout(bulk)

    def build_export_page(self):
        layout = self.page('Eksport')
        box, content = card()
        content.addWidget(label('Excel', 'sectionTitle'))
        self.export_summary = label('Ingen resultater å eksportere.', 'muted', True)
        content.addWidget(self.export_summary)
        self.export_scope = QComboBox()
        self.export_scope.addItems(['Alle prøver', 'Kun KLAR og KONTROLLERT'])
        self.export_scope.setAccessibleName('Utvalg for Excel-eksport')
        content.addWidget(self.export_scope)
        self.export_button = button('Eksporter Excel', self.export, True)
        content.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(box)
        box, content = card()
        content.addWidget(label('Excel-mal', 'sectionTitle'))
        self.template_button = button('Fyll mal …', self.template)
        content.addWidget(self.template_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(box)
        self.export_message = label('', 'muted', True)
        layout.addWidget(self.export_message)
        layout.addStretch()

    def build_settings_page(self):
        layout = self.page('Innstillinger')
        box, content = card()
        form = QFormLayout()
        self.scale_box = QComboBox()
        for text, value in SCALES.items():
            self.scale_box.addItem(text, value)
        self.scale_box.setCurrentIndex(self.scale_box.findData(1000))
        self.scale_box.setAccessibleName('RFU-skala i rapporten')
        form.addRow('RFU-skala', self.scale_box)
        self.tolerance_box = QSpinBox()
        self.tolerance_box.setRange(1, 50)
        self.tolerance_box.setValue(20)
        self.tolerance_box.setSuffix(' bp')
        self.tolerance_box.setAccessibleName('Søkevindu på hver side av forventet bp')
        form.addRow('Søkevindu ±', self.tolerance_box)
        content.addLayout(form)
        self.settings_button = button('Bruk innstillinger', self.apply_settings, True)
        content.addWidget(self.settings_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(box)
        layout.addStretch()

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        for i, widget in enumerate(self.nav_buttons):
            widget.setChecked(i == index)

    def settings(self):
        return {'factor': self.scale_box.currentData(), 'tolerance': self.tolerance_box.value()}

    def sync_settings(self):
        index = self.scale_box.findData(self.active_settings['factor'])
        self.scale_box.setCurrentIndex(index)
        self.tolerance_box.setValue(self.active_settings['tolerance'])

    def confirm_discard(self, action, *, closing=False):
        has_reviews = any(r.reviewer for r in self.rows)
        if not has_reviews or (closing and not self.unsaved_changes):
            return True
        response = QMessageBox.warning(self, 'Bevar manuelle kontroller',
            f'{action} kan forkaste manuelle kontroller. Eksporter først hvis kontrollene skal bevares.',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if response == QMessageBox.StandardButton.Save:
            return self.export(force_all=True)
        return response == QMessageBox.StandardButton.Discard

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Velg QIAxcel-rapporter', '', 'PDF-rapporter (*.pdf)')
        self.add_paths(paths)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Velg rapportmappe')
        if folder:
            root = Path(folder)
            self.add_paths(sorted(p for p in (root.rglob('*') if self.recursive.isChecked() else root.iterdir())
                                  if p.is_file() and p.suffix.lower() == '.pdf'))

    def add_paths(self, paths):
        if self.busy:
            return
        for path in paths:
            path = Path(path).resolve()
            if path.suffix.lower() == '.pdf' and path not in self.paths:
                self.paths.append(path)
        self.refresh_files()

    def refresh_files(self):
        self.file_list.clear()
        for path in self.paths:
            self.file_list.addItem(Path(path).name)
            self.file_list.item(self.file_list.count() - 1).setToolTip(str(path))
        self.file_label.setText(f'{len(self.paths)} PDF-filer valgt' if self.paths else 'Ingen PDF-filer valgt')
        self.read_button.setEnabled(bool(self.paths) and not self.busy)

    def clear(self):
        if self.busy or not self.confirm_discard('Å tømme arbeidslisten'):
            return
        self.paths, self.rows, self.errors = [], [], []
        self.unsaved_changes = False
        self.refresh_files()
        self.refresh()

    def set_busy(self, value):
        self.busy = value
        for widget in (self.choose_files_button, self.choose_folder_button, self.clear_button,
                       self.scale_box, self.tolerance_box, self.settings_button, self.assay_box,
                       self.set_assay_button, self.export_button, self.template_button,
                       self.pick_button, self.review_button, self.graph_button):
            widget.setEnabled(not value)
        self.read_button.setEnabled(bool(self.paths) and not value)
        self.progress.setVisible(value)

    def read(self):
        if self.busy or not self.paths or not self.confirm_discard('Ny innlesing'):
            return
        self.rows, self.errors = [], []
        self.unsaved_changes = False
        self.refresh()
        self.set_busy(True)
        self._read_thread = QThread(self)
        self._reader = ReportReader(list(self.paths))
        self._reader.moveToThread(self._read_thread)
        self._read_thread.started.connect(self._reader.run)
        self._reader.samples.connect(self.receive_samples)
        self._reader.failure.connect(self.receive_error)
        self._reader.progress.connect(self.read_progress)
        self._reader.finished.connect(self._read_thread.quit)
        self._reader.finished.connect(self._reader.deleteLater)
        self._read_thread.finished.connect(self.read_finished)
        self._read_thread.finished.connect(self._read_thread.deleteLater)
        self._read_thread.start()

    def receive_samples(self, samples):
        self.rows.extend(analyze(s, **self.active_settings) for s in samples)
        self.refresh()

    def receive_error(self, source, message):
        self.errors.append((source, message))
        self.refresh()

    def read_progress(self, index, total, source):
        self.progress.setRange(0, total)
        self.progress.setValue(index)
        self.statusBar().showMessage(f'Leser {index + 1} av {total} · {source}')

    def read_finished(self):
        self._read_thread = None
        self.set_busy(False)
        self.refresh()
        self.navigate(1 if self.rows else 0)

    def refresh(self, selected_index=None):
        if selected_index is None:
            selected_index = self.selected()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.rows))
        for index, result in enumerate(self.rows):
            values = [result.sample.position, result.sample.info, result.assay or 'Velg analyse',
                      number(result.expected), number(result.peak.bp if result.peak else None),
                      rfu_number(result.rfu), result.dilution or '—', result.status]
            tooltip = f'{Path(result.sample.source).name}\n{result.note}'
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(tooltip)
                if col in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    item.setFont(QFont('Consolas', 10))
                if col == 7:
                    item.setForeground(QColor('#7B5600' if result.status == 'KONTROLL' else '#0A6650'))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(index, col, item)
        self.table.blockSignals(False)
        self.filter_rows()
        if selected_index is not None and selected_index < len(self.rows):
            self.table.selectRow(selected_index)
        elif self.rows:
            self.table.selectRow(0)
        self.describe()
        counts = Counter(r.status for r in self.rows)
        for item, value in zip(self.metric_labels, [len(self.rows), counts['KLAR'], counts['KONTROLL'], counts['KONTROLLERT']]):
            item.setText(str(value))
        self.scale_notice.setVisible(self.active_settings['factor'] is None)
        self.error_list.clear()
        for path, message in self.errors:
            self.error_list.addItem(f'{Path(path).name} · {message}')
            self.error_list.item(self.error_list.count() - 1).setToolTip(str(path))
        self.error_heading.setText(f'Filfeil · {len(self.errors)}' if self.errors else 'Filfeil · ingen')
        self.error_card.setVisible(bool(self.errors))
        self.export_summary.setText(f'{len(self.rows)} prøver · {counts["KLAR"] + counts["KONTROLLERT"]} avklarte · '
                                    f'{counts["KONTROLL"]} til kontroll · {len(self.errors)} filfeil')
        self.export_button.setEnabled(bool(self.rows or self.errors) and not self.busy)
        self.template_button.setEnabled(bool(self.rows) and not self.busy)
        self.statusBar().showMessage(f'{len(self.rows)} prøver · {counts["KLAR"]} klare · '
                                     f'{counts["KONTROLL"]} til kontroll · {counts["KONTROLLERT"]} kontrollert · {len(self.errors)} filfeil')

    def filter_rows(self):
        term = self.search_edit.text().strip().casefold()
        status = self.status_filter.currentText()
        for index, result in enumerate(self.rows):
            text = ' '.join([result.sample.source, result.sample.position, result.sample.info, result.assay or '']).casefold()
            self.table.setRowHidden(index, bool((term and term not in text) or (status != 'Alle statuser' and result.status != status)))
        current = self.selected()
        if current is not None and self.table.isRowHidden(current):
            self.table.clearSelection()

    def selected(self):
        selection = self.table.selectionModel().selectedRows()
        return selection[0].row() if selection else None

    def selected_rows(self):
        return sorted(item.row() for item in self.table.selectionModel().selectedRows()
                      if not self.table.isRowHidden(item.row()))

    def describe(self):
        index = self.selected()
        self.candidate_table.setRowCount(0)
        for item in (self.pick_button, self.review_button, self.graph_button):
            item.setEnabled(index is not None and not self.busy)
        if index is None or index >= len(self.rows):
            self.detail_heading.setText('Velg prøve')
            self.detail_label.setText('')
            self.pdf_preview.set_source('', 1)
            return
        result = self.rows[index]
        self.detail_heading.setText(f'{result.sample.position} · {result.assay or "Velg analyse"}')
        note = result.note
        if result.reviewer:
            note += f'\nKontrollert av {result.reviewer}: {result.review_note}'
        self.detail_label.setText(note)
        self.candidate_table.setRowCount(len(result.candidates))
        selected = None
        for row, peak in enumerate(result.candidates):
            for col, value in enumerate([number(peak.bp), number(peak.height) if peak.height is not None else 'Mangler høyde', str(peak.page)]):
                self.candidate_table.setItem(row, col, QTableWidgetItem(value))
            if result.peak is not None and peak.bp == result.peak.bp:
                selected = row
        if selected is not None:
            self.candidate_table.selectRow(selected)
        self.pick_button.setEnabled(bool(result.candidates) and not self.busy)
        page = result.peak.page if result.peak else result.sample.header_page
        self.pdf_preview.set_source(result.sample.source, page, result.sample.source_sha256)

    def apply_settings(self):
        if self.busy:
            return
        settings = self.settings()
        if settings == self.active_settings:
            return
        if not self.confirm_discard('Endring av RFU-skala eller søkevindu'):
            self.sync_settings()
            return
        try:
            rows = [analyze(r.sample, **settings, assay_override=r.assay if r.override else None,
                            target_bp=r.target_bp if r.target_bp is not None and r.expected is not None
                            and abs(r.target_bp - r.expected) <= settings['tolerance'] else None) for r in self.rows]
        except ValueError as exc:
            QMessageBox.warning(self, 'Innstillingene kunne ikke brukes', str(exc))
            self.sync_settings()
            return
        self.rows = rows
        self.active_settings = settings
        self.unsaved_changes = False
        self.refresh()
        self.statusBar().showMessage('Innstillinger brukt · resultatene er beregnet på nytt')

    recalculate = apply_settings

    def set_assay(self):
        indices = self.selected_rows()
        assay = self.assay_box.currentText()
        if self.busy or not indices or assay not in ASSAYS:
            return
        if any(self.rows[i].reviewer for i in indices) and not self.confirm_discard('Endring av analyse'):
            return
        for index in indices:
            result = self.rows[index]
            self.rows[index] = analyze(result.sample, factor=result.factor, tolerance=result.tolerance, assay_override=assay)
        self.unsaved_changes = any(r.reviewer for r in self.rows)
        self.refresh(indices[0])

    def pick_candidate(self):
        index = self.selected()
        selected = self.candidate_table.selectionModel().selectedRows()
        if self.busy or index is None or not selected:
            return
        result = self.rows[index]
        peak = result.candidates[selected[0].row()]
        if result.reviewer and not self.confirm_discard('Endring av valgt topp'):
            return
        try:
            self.rows[index] = analyze(result.sample, factor=result.factor, tolerance=result.tolerance,
                                       assay_override=result.assay if result.override else None, target_bp=peak.bp)
        except ValueError as exc:
            QMessageBox.warning(self, 'Toppen kan ikke velges', str(exc))
            return
        self.unsaved_changes = True
        self.refresh(index)

    def review(self, *_):
        index = self.selected()
        if index is None or self.busy:
            return
        result = self.rows[index]
        if not self.can_review(result):
            return
        dialog = ReviewDialog(result, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rows[index] = dialog.result_value
            self.unsaved_changes = True
            self.refresh(index)

    def can_review(self, result):
        if result.factor is None:
            QMessageBox.information(self, 'RFU-skala', 'Velg RFU-skala i Innstillinger.')
            return False
        if len(result.candidates) > 1 and result.peak is None:
            QMessageBox.information(self, 'Velg topp', 'Velg topp i kandidatlisten før kontroll.')
            return False
        return True

    def graph_review(self):
        index = self.selected()
        if index is None or self.busy:
            return
        result = self.rows[index]
        if not self.can_review(result):
            return
        dialog = GraphDialog(result, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        reviewer = ReviewDialog(result, self, raw_height=dialog.raw_height,
                                source_page=dialog.source_page, method='Kalibrert manuell grafavlesning',
                                calibration_note=dialog.calibration_note)
        if reviewer.exec() == QDialog.DialogCode.Accepted:
            self.rows[index] = reviewer.result_value
            self.unsaved_changes = True
            self.refresh(index)

    def output_path(self, title):
        path, _ = QFileDialog.getSaveFileName(self, title,
                    f'Qiaxcel_{datetime.now():%Y%m%d_%H%M%S}.xlsx', 'Excel (*.xlsx)')
        return path

    def export(self, *_args, force_all=False):
        if self.busy or not (self.rows or self.errors):
            return False
        path = self.output_path('Lagre ny Excel-eksport')
        if not path:
            return False
        try:
            approved = not force_all and self.export_scope.currentIndex() == 1
            export_workbook(self.rows, Path(path), errors=self.errors, approved_only=approved)
            if not approved:
                self.unsaved_changes = False
            self.export_message.setText(f'Excel lagret: {path}')
            self.statusBar().showMessage(f'Excel lagret · {Path(path).name}')
            return True
        except Exception as exc:
            QMessageBox.warning(self, 'Eksport mislyktes', str(exc))
            return False

    def template(self):
        if self.busy or not self.rows:
            return
        if self.errors:
            QMessageBox.warning(self, 'Avklar filfeil først', 'Filfeil må avklares før malinnfylling. Vanlig Excel-eksport er tilgjengelig.')
            return
        source, _ = QFileDialog.getOpenFileName(self, 'Velg eksisterende Excel-mal', '', 'Excel (*.xlsx)')
        if not source:
            return
        profile, _ = QFileDialog.getOpenFileName(self, 'Velg JSON-profil med prøver og målceller', '', 'Malprofil (*.json)')
        if not profile:
            return
        output = self.output_path('Lagre utfylt kopi av malen')
        if not output:
            return
        try:
            mapping = json.loads(Path(profile).read_text(encoding='utf-8-sig'))
            fill_template(self.rows, Path(source), mapping, Path(output))
            self.export_message.setText(f'Utfylt kopi lagret: {output}')
            self.statusBar().showMessage(f'Utfylt kopi lagret · {Path(output).name}')
        except Exception as exc:
            QMessageBox.warning(self, 'Malen ble ikke fylt ut', str(exc))

    def closeEvent(self, event):
        if self.busy or any(preview.is_busy() for preview in self.findChildren(PdfPreview)):
            self.statusBar().showMessage('Vent til lesing eller PDF-tegning er ferdig før du lukker.')
            event.ignore()
            return
        if not self.confirm_discard('Lukking', closing=True):
            event.ignore()
            return
        event.accept()


def launch():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('QIAxcel Fortynning')
    app.setOrganizationName('QIAxcel Fortynning')
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    app.setWindowIcon(QIcon(str(ASSETS / 'qiaxcel.svg')))
    window = App()
    screen = app.primaryScreen()
    if screen:
        available = screen.availableGeometry()
        window.resize(min(1320, available.width() - 40), min(900, available.height() - 60))
    window.show()
    return app.exec()
