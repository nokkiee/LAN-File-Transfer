"""The desktop window (Qt). All networking lives in discovery.py / transfer.py / updates.py."""

import collections
import logging
import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import QFileInfo, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFileIconProvider,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSplitter,
    QStyle, QToolButton, QVBoxLayout, QWidget,
)

from . import APP_NAME, VERSION, os_label, updates
from .discovery import Discovery, Peer, parse_address
from .icon import app_icon
from .settings import Settings
from .theme import THEMES, ThemeManager
from .transfer import (
    ACTIVE, CANCELLED, DECLINED, DONE, FAILED, PREPARING, WAITING, Offer, Transfer, TransferManager,
)
from .updates import UpdateOffer, UpdateService

log = logging.getLogger(__name__)


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def human_duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min {seconds % 60:02d} s"
    return f"{seconds // 3600} h {seconds % 3600 // 60:02d} min"


def open_folder(path: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---------------------------------------------------------------------------
# Small widgets
# ---------------------------------------------------------------------------

class HintListWidget(QListWidget):
    """A list that shows a centered hint while it is empty."""

    def __init__(self, hint: str = "", parent=None):
        super().__init__(parent)
        self._hint = hint

    def set_hint(self, text: str) -> None:
        if text != self._hint:
            self._hint = text
            self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0 and self._hint:
            p = QPainter(self.viewport())
            p.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
            p.drawText(self.viewport().rect().adjusted(16, 16, -16, -16),
                       Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._hint)


class DropListWidget(HintListWidget):
    pathsDropped = Signal(list)

    def __init__(self, hint: str, parent=None):
        super().__init__(hint, parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.pathsDropped.emit(paths)
            event.acceptProposedAction()


class TransferRow(QFrame):
    def __init__(self, transfer: Transfer, on_remove, parent=None):
        super().__init__(parent)
        self.transfer = transfer
        self.on_remove = on_remove
        self._samples: collections.deque = collections.deque()
        self._final_rendered = False
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.title = QLabel()
        bold = self.title.font()
        bold.setBold(True)
        self.title.setFont(bold)
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status = QLabel()
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(transfer.cancel)
        self.open_btn = QPushButton("Open folder")
        self.open_btn.clicked.connect(lambda: open_folder(transfer.save_dir))
        self.open_btn.hide()
        self.remove_btn = QToolButton()
        self.remove_btn.setText("✕")
        self.remove_btn.setToolTip("Remove from list")
        self.remove_btn.setAutoRaise(True)
        self.remove_btn.clicked.connect(lambda: self.on_remove(self))
        self.remove_btn.hide()

        top = QHBoxLayout()
        top.addWidget(self.title, 1)
        top.addWidget(self.status)
        bottom = QHBoxLayout()
        bottom.addWidget(self.detail, 1)
        bottom.addWidget(self.cancel_btn)
        bottom.addWidget(self.open_btn)
        bottom.addWidget(self.remove_btn)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.addLayout(top)
        layout.addWidget(self.bar)
        layout.addLayout(bottom)
        self.refresh()

    def _speed(self) -> float:
        t = self.transfer
        now = time.monotonic()
        self._samples.append((now, t.done_bytes))
        while len(self._samples) > 2 and now - self._samples[0][0] > 3:
            self._samples.popleft()
        (t0, b0), (t1, b1) = self._samples[0], self._samples[-1]
        return (b1 - b0) / (t1 - t0) if t1 - t0 > 0.5 else 0.0

    def refresh(self) -> None:
        t = self.transfer
        if self._final_rendered:
            return
        done = t.state == DONE
        if t.kind == "update":
            version = t.items[0] if t.items else "?"
            if t.direction == "send":
                text = f"↑  {'Updated' if done else 'Updating'} {t.peer_name} to version {version}"
            else:
                text = f"↓  {'Installed' if done else 'Receiving'} version {version} from {t.peer_name}"
        else:
            what = f"“{t.items[0]}”" if len(t.items) == 1 else plural(len(t.items), "item")
            arrow, verb_now, verb_done, prep = (("↑", "Sending", "Sent", "to") if t.direction == "send"
                                                else ("↓", "Receiving", "Received", "from"))
            text = f"{arrow}  {verb_done if done else verb_now} {what} {prep} {t.peer_name}"
        self.title.setText(text)
        fraction = t.done_bytes / t.total_bytes if t.total_bytes else (1.0 if t.state == DONE else 0.0)

        if t.state in (WAITING, PREPARING):
            self.bar.setRange(0, 0)  # busy animation
            self.status.setText("")
            self.detail.setText((t.message or "Starting") + "…")
        elif t.state == ACTIVE:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(fraction * 1000))
            speed = self._speed()
            parts = [f"{human_size(t.done_bytes)} of {human_size(t.total_bytes)}"]
            if speed > 0:
                parts.append(f"{human_size(speed)}/s")
                parts.append(f"about {human_duration((t.total_bytes - t.done_bytes) / speed)} left")
            if t.file_count > 1:
                parts.append(f"file {min(t.files_done + 1, t.file_count)} of {t.file_count}")
            self.status.setText(f"{fraction * 100:.0f}%")
            self.detail.setText(t.message or " · ".join(parts))
            self.detail.setToolTip(t.current_file)
        else:
            self._final_rendered = True
            self.bar.setRange(0, 1000)
            self.bar.setValue(1000 if t.state == DONE else int(fraction * 1000))
            self.cancel_btn.hide()
            self.remove_btn.show()
            if t.state == DONE:
                elapsed = (t.finished or time.monotonic()) - t.started
                self.status.setText("✓ Done")
                count = "" if t.kind == "update" else f"{plural(t.files_done, 'file')}, "
                self.detail.setText(f"{count}{human_size(t.done_bytes)} in {human_duration(elapsed)}. {t.message}")
                if t.direction == "receive" and t.kind == "files":
                    self.open_btn.show()
            else:
                self.status.setText({FAILED: "✗ Failed", CANCELLED: "Cancelled", DECLINED: "Declined"}[t.state])
                self.detail.setText(t.message)
                if t.direction == "receive" and t.kind == "files" and t.files_done:
                    self.open_btn.show()


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------

class _QuestionDialog(QDialog):
    """Accept/decline question for an incoming offer, with an automatic timeout."""

    def __init__(self, offer, title: str, parent=None):
        super().__init__(parent)
        self.offer = offer
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self._deadline = time.monotonic() + 115
        self._answered = False
        self.body = QVBoxLayout(self)

    def _add_buttons(self, accept_text: str, decline_text: str, countdown_text: str) -> None:
        self._countdown_text = countdown_text
        self.countdown = QLabel()
        self.countdown.setStyleSheet("color: gray;")
        self.body.addWidget(self.countdown)
        buttons = QDialogButtonBox()
        accept = buttons.addButton(accept_text, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(decline_text, QDialogButtonBox.ButtonRole.RejectRole)
        accept.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.body.addWidget(buttons)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)
        self._tick()

    def _tick(self) -> None:
        if self.offer.withdrawn:
            self._timer.stop()
            self.done(QDialog.DialogCode.Rejected)
            return
        left = self._deadline - time.monotonic()
        if left <= 0:
            self.reject()
            return
        self.countdown.setText(self._countdown_text.format(seconds=int(left)))

    def _answer(self, accept: bool) -> None:
        self._timer.stop()
        if not self._answered and not self.offer.withdrawn:
            self._answered = True
            self.offer.answer(accept)

    def accept(self) -> None:
        self._answer(True)
        super().accept()

    def reject(self) -> None:
        self._answer(False)
        super().reject()


class OfferDialog(_QuestionDialog):
    def __init__(self, offer: Offer, parent=None):
        super().__init__(offer, "Incoming files", parent)

        files = [i for i in offer.items if i["kind"] == "file"]
        total = sum(i["size"] for i in files)
        groups: dict[str, list] = {}
        for item in offer.items:
            groups.setdefault(item["path"].split("/")[0], []).append(item)

        heading = QLabel(f"<b>{_esc(offer.sender_name)}</b> ({_esc(offer.sender_os)} · {offer.sender_ip}) "
                         f"wants to send you {plural(len(files), 'file')} ({human_size(total)}).")
        heading.setWordWrap(True)

        listing = QListWidget()
        provider = QFileIconProvider()
        for name, members in list(groups.items())[:500]:
            is_dir = len(members) > 1 or members[0]["kind"] == "dir"
            if is_dir:
                count = sum(1 for m in members if m["kind"] == "file")
                size = sum(m["size"] for m in members)
                text = f"{name}   —   folder, {plural(count, 'file')}, {human_size(size)}"
                icon = provider.icon(QFileIconProvider.IconType.Folder)
            else:
                text = f"{name}   —   {human_size(members[0]['size'])}"
                icon = provider.icon(QFileIconProvider.IconType.File)
            listing.addItem(QListWidgetItem(icon, text))
        listing.setMaximumHeight(min(220, 26 * listing.count() + 10))

        where = QLabel(f"They will be saved in a new numbered folder inside: {_esc(offer.save_dir)}")
        where.setWordWrap(True)
        layout = self.body
        layout.addWidget(heading)
        layout.addWidget(listing)
        layout.addWidget(where)
        if offer.free_bytes is not None and offer.free_bytes < total:
            warn = QLabel(f"⚠ Not enough free space: only {human_size(offer.free_bytes)} available.")
            warn.setStyleSheet("color: #d97706; font-weight: bold;")
            layout.addWidget(warn)
        self._add_buttons("Accept", "Decline", "Declines automatically in {seconds} s")


class UpdateOfferDialog(_QuestionDialog):
    def __init__(self, offer: UpdateOffer, parent=None):
        super().__init__(offer, "Update available", parent)
        heading = QLabel(f"<b>{_esc(offer.sender_name)}</b> ({offer.sender_ip}) wants to update {APP_NAME} "
                         f"on this computer from version {_esc(offer.from_version)} to "
                         f"<b>{_esc(offer.to_version)}</b>.")
        heading.setWordWrap(True)
        note = QLabel("The update is signed by your computer and checked before it's installed. "
                      "The app restarts by itself afterwards, once any running transfers have finished.")
        note.setWordWrap(True)
        self.body.addWidget(heading)
        self.body.addWidget(note)
        self._add_buttons("Update now", "Not now", "Answers “Not now” automatically in {seconds} s")


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, addresses: list[str], port: int | None,
                 themes: ThemeManager | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.themes = themes
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)

        self.name = QLineEdit(settings.device_name)
        self.name.setMaxLength(60)
        self.folder = QLineEdit(settings.download_dir)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)
        self.ask = QCheckBox("Ask me before accepting incoming files (recommended)")
        self.ask.setChecked(settings.ask_before_receiving)
        self.theme = QComboBox()
        for key, label in THEMES.items():
            self.theme.addItem(label, key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(settings.theme)))

        form = QFormLayout()
        form.addRow("Name of this computer:", self.name)
        form.addRow("Save received files in:", folder_row)
        form.addRow("", self.ask)
        form.addRow("Appearance:", self.theme)
        info = QLabel(f"IP address: {', '.join(addresses) or 'not connected'}<br>"
                      f"Port: {port or 'not listening'}<br>Version {VERSION}")
        info.setStyleSheet("color: gray;")
        form.addRow("", info)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Save received files in", self.folder.text())
        if path:
            self.folder.setText(path)

    def accept(self) -> None:
        self.settings.device_name = self.name.text().strip() or self.settings.device_name
        self.settings.download_dir = self.folder.text().strip() or self.settings.download_dir
        self.settings.ask_before_receiving = self.ask.isChecked()
        self.settings.theme = self.theme.currentData()
        self.settings.save()
        if self.themes:
            self.themes.set(self.settings.theme)
        super().accept()


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    offerArrived = Signal(object)
    manualResult = Signal(str, object)
    updateOfferArrived = Signal(object)
    updateInstalled = Signal(str)

    def __init__(self, settings: Settings, themes: ThemeManager | None = None):
        super().__init__()
        self.settings = settings
        self.themes = themes
        self.manager = TransferManager(self.identity, lambda: self.settings.download_dir, self._present_offer)
        self.updates = UpdateService(self.manager, self.updateOfferArrived.emit, self.updateInstalled.emit,
                                     auto_install=lambda: self.settings.auto_install_updates)
        self.discovery = Discovery(self.identity)
        for address in settings.manual_peers:
            try:
                self.discovery.manual_addresses.add(parse_address(address))
            except ValueError:
                pass
        self._rows: dict[int, TransferRow] = {}
        self._peer_view: list[tuple] = []
        self._dialogs: list[QDialog] = []
        self._started = time.monotonic()
        self._release: updates.Release | None = None
        self._outdated: list[Peer] = []
        self._restart_pending = False
        self._restarting = False
        self.offerArrived.connect(self._show_offer)
        self.manualResult.connect(self._manual_result)
        self.updateOfferArrived.connect(self._show_update_offer)
        self.updateInstalled.connect(self._update_installed)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1000, 760)
        self.setAcceptDrops(True)
        self._build_ui()

        try:
            self.manager.receiver.start(settings.tcp_port)
        except OSError as exc:
            QMessageBox.critical(self, APP_NAME, f"This computer cannot receive files right now:\n{exc}\n\n"
                                                 "Sending still works.")
        self.discovery.start()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(250)
        self._tick_count = 0
        self._refresh_peers()
        self._refresh_header()

    # -- identity / networking callbacks ----------------------------------

    def identity(self) -> dict:
        return {"id": self.settings.device_id, "name": self.settings.device_name, "os": os_label(),
                "port": self.manager.receiver.port or self.settings.tcp_port, **updates.identity_fields()}

    def _present_offer(self, offer: Offer) -> None:  # called on a network thread
        if self.settings.ask_before_receiving:
            self.offerArrived.emit(offer)
        else:
            offer.answer(True)

    # -- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        title = QLabel(APP_NAME)
        f = title.font()
        f.setPointSizeF(f.pointSizeF() * 1.6)
        f.setBold(True)
        title.setFont(f)
        self.me_label = QLabel()
        self.me_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        settings_btn = QPushButton("Settings")
        settings_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        settings_btn.clicked.connect(self._open_settings)
        self.theme_btn = QToolButton()
        self.theme_btn.setToolTip("Light or dark appearance")
        self.theme_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        theme_menu = QMenu(self.theme_btn)
        for key, label in THEMES.items():
            action = theme_menu.addAction(label)
            action.setCheckable(True)
            action.setData(key)
            action.triggered.connect(lambda _=False, k=key: self._set_theme(k))
        theme_menu.aboutToShow.connect(lambda: [a.setChecked(a.data() == self.settings.theme)
                                                for a in theme_menu.actions()])
        self.theme_btn.setMenu(theme_menu)
        self.theme_btn.setVisible(self.themes is not None)
        self._update_theme_button()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        header_text.addWidget(title)
        header_text.addWidget(self.me_label)
        header = QHBoxLayout()
        header.addLayout(header_text, 1)
        header.addWidget(self.theme_btn, 0, Qt.AlignmentFlag.AlignTop)
        header.addWidget(settings_btn, 0, Qt.AlignmentFlag.AlignTop)

        # 1. devices
        self.device_list = HintListWidget()
        self.device_list.setIconSize(QSize(32, 32))
        self.device_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.device_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.device_list.setSpacing(2)
        self.device_list.itemSelectionChanged.connect(self._update_send_button)
        self.device_list.itemDoubleClicked.connect(lambda _: self._send())
        self.device_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_list.customContextMenuRequested.connect(self._device_menu)
        add_ip = QPushButton("Add computer by IP address…")
        add_ip.clicked.connect(self._add_by_ip)
        dev_box = QGroupBox("1.  Choose the computer to send to")
        dev_layout = QVBoxLayout(dev_box)
        dev_layout.addWidget(self.device_list, 1)
        dev_layout.addWidget(add_ip)

        # 2. files
        self.file_list = DropListWidget("Drag files or folders here\n\nor use the buttons below")
        self.file_list.setIconSize(QSize(24, 24))
        self.file_list.pathsDropped.connect(self._add_paths)
        self.file_list.model().rowsInserted.connect(self._update_send_button)
        self.file_list.model().rowsRemoved.connect(self._update_send_button)
        add_files = QPushButton("Add files…")
        add_files.clicked.connect(self._pick_files)
        add_folder = QPushButton("Add folder…")
        add_folder.clicked.connect(self._pick_folder)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_selected_files)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.file_list.clear)
        file_buttons = QHBoxLayout()
        for b in (add_files, add_folder):
            file_buttons.addWidget(b)
        file_buttons.addStretch(1)
        for b in (remove, clear):
            file_buttons.addWidget(b)
        self.send_btn = QPushButton("3.  Send")
        self.send_btn.setMinimumHeight(44)
        sf = self.send_btn.font()
        sf.setBold(True)
        sf.setPointSizeF(sf.pointSizeF() * 1.15)
        self.send_btn.setFont(sf)
        self.send_btn.clicked.connect(self._send)
        files_box = QGroupBox("2.  Choose files and folders")
        files_layout = QVBoxLayout(files_box)
        files_layout.addWidget(self.file_list, 1)
        files_layout.addLayout(file_buttons)
        files_layout.addWidget(self.send_btn)

        top_split = QSplitter(Qt.Orientation.Horizontal)
        top_split.addWidget(dev_box)
        top_split.addWidget(files_box)
        top_split.setStretchFactor(0, 2)
        top_split.setStretchFactor(1, 3)
        top_split.setChildrenCollapsible(False)

        # transfers
        self.rows_widget = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.no_transfers = QLabel("Nothing sent or received yet.")
        self.no_transfers.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_transfers.setEnabled(False)
        self.rows_layout.addWidget(self.no_transfers)
        self.rows_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.rows_widget)
        self.save_label = QLabel()
        self.save_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        change = QPushButton("Change…")
        change.clicked.connect(self._change_save_dir)
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._open_save_dir)
        save_row = QHBoxLayout()
        save_row.addWidget(self.save_label, 1)
        save_row.addWidget(change)
        save_row.addWidget(open_btn)
        tx_box = QGroupBox("Transfers")
        tx_layout = QVBoxLayout(tx_box)
        tx_layout.addWidget(scroll, 1)
        tx_layout.addLayout(save_row)

        main_split = QSplitter(Qt.Orientation.Vertical)
        main_split.addWidget(top_split)
        main_split.addWidget(tx_box)
        main_split.setStretchFactor(0, 1)
        main_split.setStretchFactor(1, 1)
        main_split.setChildrenCollapsible(False)
        main_split.setSizes([400, 330])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.addLayout(header)
        layout.addSpacing(6)
        layout.addWidget(self._build_banner())
        layout.addWidget(main_split, 1)
        self.setCentralWidget(central)
        self._update_save_label()
        self._update_send_button()

    def _build_banner(self) -> QFrame:
        self.banner = QFrame()
        self.banner.setFrameShape(QFrame.Shape.StyledPanel)
        icon = QLabel()
        icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload).pixmap(24, 24))
        self.banner_label = QLabel()
        self.banner_label.setWordWrap(True)
        self.update_btn = QPushButton("Update")
        self.update_btn.clicked.connect(self._update_all)
        self.restart_btn = QPushButton("Restart now")
        self.restart_btn.clicked.connect(self._restart_self)
        row = QHBoxLayout(self.banner)
        row.setContentsMargins(10, 6, 10, 6)
        row.addWidget(icon)
        row.addWidget(self.banner_label, 1)
        row.addWidget(self.update_btn)
        row.addWidget(self.restart_btn)
        self.banner.hide()
        return self.banner

    # -- periodic refresh -------------------------------------------------

    def _tick(self) -> None:
        self._tick_count += 1
        self._refresh_transfers()
        if self._restart_pending and not self.manager.active():
            self._restart()
            return
        if self._tick_count % 4 == 0:
            self._refresh_peers()
        if self._tick_count % 20 == 0:
            self._refresh_header()

    def _refresh_header(self) -> None:
        addresses = self.discovery.my_addresses()
        ip = addresses[0] if addresses else "no network connection"
        self.me_label.setText(f"This computer: <b>{_esc(self.settings.device_name)}</b>  ·  IP {ip}  ·  {os_label()}")
        self.me_label.setToolTip("All addresses: " + ", ".join(addresses) if addresses else "")

    def _refresh_peers(self) -> None:
        peers = self.discovery.peers()
        view = [(p.id, p.name, p.os, p.ip, p.port, p.version, p.build) for p in peers]
        if self.discovery.error:
            hint = self.discovery.error + "\n\nUse “Add computer by IP address…” instead."
        elif time.monotonic() - self._started < 6:
            hint = "Looking for other computers…"
        else:
            hint = ("No other computers found yet.\n\n"
                    f"Open {APP_NAME} on the other computer and make sure both are on the same Wi-Fi.\n\n"
                    "If a firewall question pops up, click Allow.")
        self.device_list.set_hint(hint)
        self._refresh_banner(peers)
        outdated_ids = {p.id for p in self._outdated}
        view = [v + (p.id in outdated_ids,) for v, p in zip(view, peers)]
        if view == self._peer_view:
            return
        selected = self._selected_peer()
        selected_id = selected.id if selected else None
        self._peer_view = view
        self.device_list.clear()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        for peer in peers:
            version = (f"Version {updates.display_version(peer.version, peer.build)}" if peer.version
                       else "Older version")
            if peer.id in outdated_ids:
                version += "  ·  update ready"
            item = QListWidgetItem(icon, f"{peer.name}\n{peer.os}  ·  {peer.ip}\n{version}")
            item.setData(Qt.ItemDataRole.UserRole, peer)
            self.device_list.addItem(item)
            if peer.id == selected_id or len(peers) == 1:
                item.setSelected(True)
        self._update_send_button()

    def _refresh_transfers(self) -> None:
        transfers = self.manager.snapshot()
        for t in transfers:
            row = self._rows.get(t.id)
            if row is None:
                row = TransferRow(t, self._remove_row)
                self._rows[t.id] = row
                self.rows_layout.insertWidget(0, row)
                self.no_transfers.hide()
            else:
                row.refresh()

    def _remove_row(self, row: TransferRow) -> None:
        self.manager.remove(row.transfer)
        self._rows.pop(row.transfer.id, None)
        row.deleteLater()
        if not self._rows:
            self.no_transfers.show()

    # -- devices ----------------------------------------------------------

    def _selected_peer(self) -> Peer | None:
        items = self.device_list.selectedItems()
        return items[0].data(Qt.ItemDataRole.UserRole) if items else None

    def _add_by_ip(self) -> None:
        text, ok = QInputDialog.getText(
            self, "Add computer by IP address",
            f"Type the IP address shown at the top of {APP_NAME} on the other computer\n"
            "(for example 192.168.1.42):")
        if not ok or not text.strip():
            return
        try:
            ip, port = parse_address(text)
        except ValueError:
            QMessageBox.warning(self, APP_NAME, f"“{text}” is not a valid IP address.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        def work():
            peer = self.discovery.add_manual(ip, port)
            self.manualResult.emit(f"{ip}:{port}", peer)

        threading.Thread(target=work, daemon=True).start()

    def _manual_result(self, address: str, peer: Peer | None) -> None:
        QApplication.restoreOverrideCursor()
        if peer is None:
            QMessageBox.warning(
                self, APP_NAME,
                f"Could not reach {address}.\n\nCheck that {APP_NAME} is open on that computer, that both "
                "computers are on the same network, and that its firewall allows the app.")
            return
        if address not in self.settings.manual_peers:
            self.settings.manual_peers.append(address)
            self.settings.save()
        self._refresh_peers()

    def _device_menu(self, pos) -> None:
        item = self.device_list.itemAt(pos)
        if not item:
            return
        peer: Peer = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        send = menu.addAction(f"Send files to {peer.name}")
        send.setEnabled(self.file_list.count() > 0)
        send.triggered.connect(self._send)
        if any(p.id == peer.id for p in self._outdated):
            update = menu.addAction(f"Update to version {self._release.label}")
            update.triggered.connect(lambda: self._push_updates([peer]))
        if peer.manual:
            forget = menu.addAction("Forget this computer")
            forget.triggered.connect(lambda: self._forget(peer))
        menu.exec(self.device_list.viewport().mapToGlobal(pos))

    def _forget(self, peer: Peer) -> None:
        address = f"{peer.ip}:{peer.port}"
        if address in self.settings.manual_peers:
            self.settings.manual_peers.remove(address)
            self.settings.save()
        self.discovery.forget(peer.id)
        self._refresh_peers()

    # -- files ------------------------------------------------------------

    def _paths(self) -> list[str]:
        return [self.file_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.file_list.count())]

    def _add_paths(self, paths: list[str]) -> None:
        existing = set(self._paths())
        provider = QFileIconProvider()
        for raw in paths:
            path = os.path.abspath(raw)
            if path in existing or not os.path.exists(path):
                continue
            existing.add(path)
            info = QFileInfo(path)
            name = Path(path).name or path
            detail = "folder" if info.isDir() else human_size(info.size())
            item = QListWidgetItem(provider.icon(info), f"{name}   —   {detail}")
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.file_list.addItem(item)

    def _pick_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose files to send", str(Path.home()))
        self._add_paths(paths)

    def _pick_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose a folder to send", str(Path.home()))
        if path:
            self._add_paths([path])

    def _remove_selected_files(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self._add_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])

    # -- sending ----------------------------------------------------------

    def _update_send_button(self, *_) -> None:
        peer = self._selected_peer()
        count = self.file_list.count()
        self.send_btn.setEnabled(bool(peer and count))
        if peer and count:
            self.send_btn.setText(f"3.  Send {plural(count, 'item')} to {peer.name}")
            self.send_btn.setToolTip("")
        else:
            self.send_btn.setText("3.  Send")
            self.send_btn.setToolTip("Choose a computer and add some files first.")

    def _send(self) -> None:
        peer = self._selected_peer()
        paths = self._paths()
        if not peer or not paths:
            return
        self.manager.send(peer.name, peer.ip, peer.port, paths)
        self.file_list.clear()
        self._refresh_transfers()

    # -- receiving --------------------------------------------------------

    def _show_offer(self, offer: Offer) -> None:
        self._present_dialog(OfferDialog(offer, self))

    def _present_dialog(self, dialog: QDialog) -> None:
        dialog.setWindowIcon(self.windowIcon())
        self._dialogs.append(dialog)
        dialog.finished.connect(lambda _: self._dialogs.remove(dialog))
        if self.isMinimized():
            self.showNormal()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        QApplication.alert(self)

    def _update_save_label(self) -> None:
        self.save_label.setText(f"Received files are saved in:  {self.settings.download_dir}")

    def _change_save_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Save received files in", self.settings.download_dir)
        if path:
            self.settings.download_dir = path
            self.settings.save()
            self._update_save_label()

    def _open_save_dir(self) -> None:
        os.makedirs(self.settings.download_dir, exist_ok=True)
        open_folder(self.settings.download_dir)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.discovery.my_addresses(), self.manager.receiver.port,
                                self.themes, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_save_label()
            self._refresh_header()
            self._update_theme_button()

    def _set_theme(self, theme: str) -> None:
        self.settings.theme = theme
        self.settings.save()
        if self.themes:
            self.themes.set(theme)
        self._update_theme_button()

    def _update_theme_button(self) -> None:
        self.theme_btn.setText({"light": "☀ Light", "dark": "☾ Dark"}.get(self.settings.theme, "◐ Auto"))

    # -- app updates ------------------------------------------------------

    def _refresh_banner(self, peers: list[Peer]) -> None:
        release = self._release = self.updates.local_release()
        busy = {t.peer_ip for t in self.manager.active() if t.kind == "update" and t.direction == "send"}
        self._outdated = [p for p in peers if updates.peer_needs_update(p, release) and p.ip not in busy]

        def is_stuck(p: Peer) -> bool:  # older, but can't take an update over Wi-Fi
            if not p.version:
                return True  # an app from before automatic updates existed
            return not p.updatable and release.key > updates.version_key(p.version, p.build)

        stuck = [p for p in peers if is_stuck(p)] if release else []
        target = self.updates.target
        self_stale = bool(release and updates.is_packaged() and target in release.builds
                          and release.key > updates.CURRENT
                          and release.path(target).resolve() == updates.executable())

        def names(group: list[Peer]) -> str:
            return ", ".join(f"<b>{_esc(p.name)}</b>" for p in group)

        lines = []
        if self._restart_pending:
            lines.append("Update installed. The app restarts as soon as the running transfers finish.")
        else:
            if self._outdated:
                lines.append(f"Version {_esc(release.label)} is ready for {names(self._outdated)}.")
            if stuck:
                lines.append(f"{names(stuck)} can't update automatically (an older or Mac version, or not the "
                             "packaged app). Download the new version there from the Releases page.")
            if self_stale:
                lines.append(f"Version {_esc(release.label)} is installed on this computer. "
                             "Restart the app to start using it.")
        self.banner_label.setText("<br>".join(lines))
        self.update_btn.setVisible(bool(self._outdated) and not self._restart_pending)
        self.update_btn.setText(f"Update {self._outdated[0].name}" if len(self._outdated) == 1
                                else f"Update all ({len(self._outdated)})")
        self.restart_btn.setVisible(self_stale and not self._restart_pending)
        self.banner.setVisible(bool(lines))

    def _update_all(self) -> None:
        self._push_updates(list(self._outdated))

    def _push_updates(self, peers: list[Peer]) -> None:
        if not self._release:
            return
        for peer in peers:
            if updates.peer_needs_update(peer, self._release):
                self.updates.push(peer, self._release)
        self._refresh_transfers()
        self._refresh_peers()

    def _show_update_offer(self, offer: UpdateOffer) -> None:
        dialog = UpdateOfferDialog(offer, self)
        self._present_dialog(dialog)

    def _update_installed(self, version: str) -> None:
        log.info("Version %s installed; restarting when idle", version)
        self._restart_pending = True
        self._refresh_peers()

    def _restart_self(self) -> None:
        active = self.manager.active()
        if active and QMessageBox.question(
                self, APP_NAME, f"{plural(len(active), 'transfer')} still in progress. Stop and restart?"
        ) != QMessageBox.StandardButton.Yes:
            return
        for t in active:
            t.cancel()
        self._restart()

    def _restart(self) -> None:
        """Start the newly installed version and quit this one."""
        self._restarting = True
        self._timer.stop()
        self.discovery.stop()  # free the ports for the new instance
        self.manager.receiver.stop()
        try:
            updates.launch_installed_app()
        except OSError:
            log.exception("Could not start the new version")
            QMessageBox.warning(self, APP_NAME, "The update is installed, but the app couldn't restart by "
                                                "itself. Please open it again.")
        QApplication.quit()

    # -- shutdown ---------------------------------------------------------

    def closeEvent(self, event):
        if self._restarting:
            event.accept()
            return
        active = self.manager.active()
        if active:
            answer = QMessageBox.question(
                self, APP_NAME, f"{plural(len(active), 'transfer')} still in progress. Stop and quit?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for t in active:
                t.cancel()
            deadline = time.monotonic() + 2
            while self.manager.active() and time.monotonic() < deadline:
                QApplication.processEvents()
                time.sleep(0.05)
        self.discovery.stop()
        self.manager.receiver.stop()
        event.accept()
