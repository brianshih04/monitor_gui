import sys
import time

import psutil
from PySide6.QtCore import Qt, QMutex, QMutexLocker, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class SystemResourcePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        title_label = QLabel("系統資源即時監控")
        title_label.setStyleSheet("font-size: 20px; font-weight: 600; color: #222;")

        hint_label = QLabel("每秒更新一次目前 CPU / 記憶體 / 磁碟 / 網路 使用情況。")
        hint_label.setStyleSheet("font-size: 12px; color: #777;")

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)

        # CPU
        cpu_box = QGroupBox("CPU 使用率")
        cpu_layout = QVBoxLayout(cpu_box)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_label = QLabel("0 %")
        self.cpu_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cpu_layout.addWidget(self.cpu_bar)
        cpu_layout.addWidget(self.cpu_label)

        # Memory
        mem_box = QGroupBox("記憶體使用率")
        mem_layout = QVBoxLayout(mem_box)
        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_label = QLabel("0 %  (0 / 0 GB)")
        self.mem_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        mem_layout.addWidget(self.mem_bar)
        mem_layout.addWidget(self.mem_label)

        # Disk
        disk_box = QGroupBox("系統磁碟使用率")
        disk_layout = QVBoxLayout(disk_box)
        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        self.disk_label = QLabel("0 %  (0 / 0 GB)")
        self.disk_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        disk_layout.addWidget(self.disk_bar)
        disk_layout.addWidget(self.disk_label)

        # Network
        net_box = QGroupBox("網路流量")
        net_layout = QVBoxLayout(net_box)
        self.net_up_label = QLabel("上行：0 KB/s")
        self.net_down_label = QLabel("下行：0 KB/s")
        self.net_up_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.net_down_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        net_layout.addWidget(self.net_up_label)
        net_layout.addWidget(self.net_down_label)

        # Disk list (all drives)
        self.disk_box = QGroupBox("磁碟機使用率")
        disk_list_layout = QVBoxLayout(self.disk_box)
        self.disk_labels = []
        self._refresh_disk_list(disk_list_layout)

        # GPU
        self.gpu_box = QGroupBox("GPU 使用率")
        gpu_layout = QVBoxLayout(self.gpu_box)
        gpu_label = QLabel("GPU 監控目前停用（僅支援 NVIDIA 時才建議開啟）。")
        gpu_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        gpu_layout.addWidget(gpu_label)

        grid.addWidget(cpu_box, 0, 0)
        grid.addWidget(mem_box, 0, 1)
        grid.addWidget(self.disk_box, 1, 0)
        grid.addWidget(net_box, 1, 1)
        grid.addWidget(self.gpu_box, 2, 0, 1, 2)

        root_layout.addWidget(title_label)
        root_layout.addWidget(hint_label)
        root_layout.addSpacing(8)
        root_layout.addLayout(grid)
        root_layout.addStretch(1)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #f4f5f7;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 8px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QProgressBar {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background: #f0f0f0;
                text-visible: false;
                height: 14px;
            }
            QProgressBar::chunk {
                background-color: #2f7de1;
                border-radius: 3px;
            }
            """
        )

    def _refresh_disk_list(self, layout: QVBoxLayout):
        # 清空舊 label
        for lbl in self.disk_labels:
            layout.removeWidget(lbl)
            lbl.deleteLater()
        self.disk_labels.clear()

        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            # 只顯示本機磁碟（忽略光碟機、虛擬裝置等）
            if "cdrom" in part.opts or part.fstype == "":
                continue
            label = QLabel(f"{part.device} - 探測中...")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(label)
            self.disk_labels.append((label, part.mountpoint))

        if not self.disk_labels:
            label = QLabel("找不到本機磁碟。")
            layout.addWidget(label)
            self.disk_labels.append((label, None))

    def _init_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(1000)

    def _update_stats(self):
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        self.cpu_bar.setValue(int(cpu))
        self.cpu_label.setText(f"{cpu:5.1f} %")

        # Memory
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        total_gb = mem.total / (1024**3)
        used_gb = (mem.total - mem.available) / (1024**3)
        self.mem_bar.setValue(int(mem_percent))
        self.mem_label.setText(
            f"{mem_percent:5.1f} %  ({used_gb:4.1f} / {total_gb:4.1f} GB)"
        )

        # Disks: 更新每個磁碟機使用率
        for label, mountpoint in self.disk_labels:
            if not mountpoint:
                continue
            try:
                d = psutil.disk_usage(mountpoint)
                percent = d.percent
                total_gb = d.total / (1024**3)
                used_gb = d.used / (1024**3)
                label.setText(
                    f"{mountpoint}  {percent:5.1f} %  ({used_gb:4.1f} / {total_gb:4.1f} GB)"
                )
            except Exception:
                label.setText(f"{mountpoint}  無法讀取")

        # Network：計算 KB/s
        now = time.time()
        net = psutil.net_io_counters()
        dt = max(now - self._last_time, 1e-3)
        sent_per_s = (net.bytes_sent - self._last_net.bytes_sent) / dt
        recv_per_s = (net.bytes_recv - self._last_net.bytes_recv) / dt

        self._last_net = net
        self._last_time = now

        def to_human(speed_bytes_per_s: float) -> str:
            kb = speed_bytes_per_s / 1024
            if kb < 1024:
                return f"{kb:6.1f} KB/s"
            mb = kb / 1024
            return f"{mb:6.2f} MB/s"

        self.net_up_label.setText(f"上行：{to_human(sent_per_s)}")
        self.net_down_label.setText(f"下行：{to_human(recv_per_s)}")


class _WatchdogHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def on_any_event(self, event):
        # event.event_type: created / modified / deleted / moved
        # event.is_directory: bool
        self._callback(event)


class FileWatchThread(QThread):
    file_event = Signal(str, str, str)  # time, event_type, path
    error = Signal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        self._observer = None
        self._running = True
        self._mutex = QMutex()

    def run(self):
        try:
            handler = _WatchdogHandler(self._on_event)
            self._observer = Observer()
            self._observer.schedule(handler, self._path, recursive=True)
            self._observer.start()

            # watchdog 本身會阻塞在 observer.join()，我們用 while loop 輕量等待
            while True:
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break
                time.sleep(0.2)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self._observer is not None:
                self._observer.stop()
                self._observer.join(timeout=2)

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False

    def _on_event(self, event):
        # 在背景執行緒，但 Qt 訊號是 thread-safe 的
        t = time.strftime("%H:%M:%S")
        kind = event.event_type
        if event.is_directory:
            kind += " (dir)"
        path = getattr(event, "dest_path", None) or event.src_path
        self.file_event.emit(t, kind, path)


class FileMonitorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: FileWatchThread | None = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("資料夾 / 檔案異動監控")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #222;")

        hint = QLabel("選擇一個要監控的資料夾，會即時顯示新增 / 修改 / 刪除 / 移動 等事件。")
        hint.setStyleSheet("font-size: 12px; color: #777;")

        # 選擇資料夾列
        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("請選擇要監控的資料夾路徑")
        browse_btn = QPushButton("選擇資料夾...")
        browse_btn.clicked.connect(self._choose_folder)
        self.toggle_btn = QPushButton("開始監控")
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.clicked.connect(self._toggle_watch)

        row.addWidget(self.path_edit, 1)
        row.addWidget(browse_btn)
        row.addWidget(self.toggle_btn)

        # 表格顯示事件
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["時間", "事件", "路徑"])
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)

        root.addWidget(title)
        root.addWidget(hint)
        root.addLayout(row)
        root.addWidget(self.table, 1)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #f4f5f7;
            }
            QLineEdit {
                background: #ffffff;
                border-radius: 4px;
                border: 1px solid #cccccc;
                padding: 4px 6px;
            }
            QPushButton {
                padding: 6px 12px;
            }
            QTableWidget {
                background: #ffffff;
            }
            """
        )

        self.path_edit.textChanged.connect(self._on_path_changed)

    def _on_path_changed(self, text: str):
        self.toggle_btn.setEnabled(bool(text.strip()))

    def _choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "選擇要監控的資料夾")
        if path:
            self.path_edit.setText(path)

    def _toggle_watch(self):
        if self._thread is None:
            # start
            path = self.path_edit.text().strip()
            if not path:
                return
            self.table.setRowCount(0)
            self._thread = FileWatchThread(path, self)
            self._thread.file_event.connect(self._on_file_event)
            self._thread.error.connect(self._on_error)
            self._thread.start()
            self.toggle_btn.setText("停止監控")
            self.path_edit.setEnabled(False)
        else:
            # stop
            self._thread.stop()
            self._thread.wait(2000)
            self._thread = None
            self.toggle_btn.setText("開始監控")
            self.path_edit.setEnabled(True)

    def _on_file_event(self, t: str, kind: str, path: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(t))
        self.table.setItem(row, 1, QTableWidgetItem(kind))
        self.table.setItem(row, 2, QTableWidgetItem(path))
        self.table.scrollToBottom()

    def _on_error(self, msg: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
        self.table.setItem(row, 1, QTableWidgetItem("錯誤"))
        self.table.setItem(row, 2, QTableWidgetItem(msg))
        self.table.scrollToBottom()

    def closeEvent(self, event):
        if self._thread is not None:
            self._thread.stop()
            self._thread.wait(2000)
            self._thread = None
        super().closeEvent(event)


class NetworkMonitorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(3000)  # 每 3 秒更新一次
        self._timer.timeout.connect(self._refresh_connections)
        self._init_ui()
        self._timer.start()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("連線 / Port 監控")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: #222;")

        hint = QLabel("顯示目前系統的網路連線（只讀），包含本機位址/Port、遠端位址/Port、狀態與對應程式。")
        hint.setStyleSheet("font-size: 12px; color: #777;")

        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("立即更新")
        self.refresh_btn.clicked.connect(self._refresh_connections)
        info = QLabel("提示：部分連線可能需要系統權限才能取得完整資訊。")
        info.setStyleSheet("font-size: 11px; color: #999;")
        controls.addWidget(self.refresh_btn)
        controls.addStretch(1)
        controls.addWidget(info)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["本機位址", "遠端位址", "狀態", "PID", "程式名稱"]
        )
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 60)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)

        root.addWidget(title)
        root.addWidget(hint)
        root.addLayout(controls)
        root.addWidget(self.table, 1)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #f4f5f7;
            }
            QTableWidget {
                background: #ffffff;
            }
            """
        )

        # 第一次載入
        self._refresh_connections()

    def _format_addr(self, addr):
        if not addr:
            return "-"
        host, port = addr
        return f"{host}:{port}"

    def _refresh_connections(self):
        try:
            conns = psutil.net_connections(kind="inet")
        except Exception as e:
            self.table.setRowCount(0)
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(""))
            self.table.setItem(0, 1, QTableWidgetItem(""))
            self.table.setItem(0, 2, QTableWidgetItem("錯誤"))
            self.table.setItem(0, 3, QTableWidgetItem(""))
            self.table.setItem(0, 4, QTableWidgetItem(str(e)))
            return

        self.table.setRowCount(0)
        for c in conns:
            row = self.table.rowCount()
            self.table.insertRow(row)

            laddr = self._format_addr(c.laddr if c.laddr else None)
            raddr = self._format_addr(c.raddr if c.raddr else None)
            status = c.status or "-"
            pid = c.pid if c.pid is not None else -1

            # 取程式名稱
            pname = ""
            if pid not in (None, -1):
                try:
                    proc = psutil.Process(pid)
                    pname = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pname = "無法取得"

            self.table.setItem(row, 0, QTableWidgetItem(laddr))
            self.table.setItem(row, 1, QTableWidgetItem(raddr))
            self.table.setItem(row, 2, QTableWidgetItem(status))
            self.table.setItem(row, 3, QTableWidgetItem(str(pid) if pid != -1 else ""))
            self.table.setItem(row, 4, QTableWidgetItem(pname))

        self.table.scrollToTop()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系統監視中心")
        self.resize(1100, 700)
        self._init_ui()

    def _init_ui(self):
        tabs = QTabWidget()
        tabs.addTab(SystemResourcePage(), "系統資源")
        tabs.addTab(FileMonitorPage(), "檔案監控")
        tabs.addTab(NetworkMonitorPage(), "連線 / Port")

        self.setCentralWidget(tabs)

    @staticmethod
    def _create_placeholder_tab(title: str, description: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setStyleSheet(
            "font-size: 22px; font-weight: 600; color: #222;"
        )

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            "font-size: 13px; color: #555;"
        )

        hint_label = QLabel("功能尚在建置中，之後會顯示即時監控資訊。")
        hint_label.setStyleSheet(
            "font-size: 12px; color: #888; font-style: italic;"
        )

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addSpacing(12)
        layout.addWidget(hint_label)
        layout.addStretch(1)

        page.setStyleSheet(
            """
            QWidget {
                background-color: #f4f5f7;
            }
            """
        )
        return page


def main():
    app = QApplication(sys.argv)

    # 可在這裡設定全域樣式，讓 UI 比較現代
    app.setStyleSheet(
        """
        QMainWindow {
            background-color: #f4f5f7;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            background: #ffffff;
        }
        QTabBar::tab {
            padding: 8px 18px;
            border: 0px;
            border-bottom: 2px solid transparent;
            color: #666;
            font-size: 13px;
        }
        QTabBar::tab:selected {
            color: #222;
            font-weight: 600;
            border-bottom: 2px solid #2f7de1;
        }
        """
    )

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

