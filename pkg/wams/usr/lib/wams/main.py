import os
import sys
import locale
import shutil
import time
import webbrowser

from PyQt6.QtCore import Qt, QUrl, QSettings, QLocale, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QImage, QPainter, QBrush, QPen, QAction, QDesktopServices
from PyQt6.QtWidgets import (QMainWindow, QApplication, QFileDialog, QSystemTrayIcon, QMenu,
                             QTabWidget, QPushButton, QMessageBox, QLineEdit, QTabBar, QWidget,
                             QHBoxLayout)
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

import modules.notification as Notification
from modules.i18n import tr
import modules.web as web

def get_app_icon():
    """Obtiene el icono de la aplicación desde diferentes ubicaciones"""
    icon_paths = [
        '/usr/lib/wams/modules/wams.png',  # Instalación del paquete
        '/usr/share/icons/hicolor/256x256/apps/wams.png',  # Iconos del sistema
        'main/modules/wams.png',          # Para desarrollo local
        'modules/wams.png'                # Para desarrollo local alternativo
    ]

    for path in icon_paths:
        if os.path.exists(path):
            return QIcon(path)

    # Fallback al icono del tema del sistema
    return QIcon.fromTheme('wams', QIcon.fromTheme('application-x-executable'))

class RenameTabBar(QTabBar):
    tabNameChanged = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.hide()
        self.editor.editingFinished.connect(self.finish_editing)
        self.edit_index = -1

    def mouseDoubleClickEvent(self, event):
        self.edit_index = self.tabAt(event.pos())
        if self.edit_index >= 0:
            self.start_editing()

    def start_editing(self):
        rect = self.tabRect(self.edit_index)
        self.editor.setFixedSize(rect.size())
        self.editor.move(rect.topLeft())
        self.editor.setText(self.tabText(self.edit_index))
        self.editor.show()
        self.editor.selectAll()
        self.editor.setFocus()

    def finish_editing(self):
        if self.edit_index >= 0:
            self.tabNameChanged.emit(self.edit_index, self.editor.text())
            self.editor.hide()
            self.edit_index = -1

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.app_icon = get_app_icon()
        self.setWindowIcon(self.app_icon)

        self.setup_system_locale()
        self.setup_app_directory()
        self.settings = QSettings(os.path.join(self.app_dir, "config.ini"), QSettings.Format.IniFormat)
        self.setup_window_configuration()

        self.force_quit = False

        Notification.init("WAms")

        # Central QTabWidget for multi-session
        self.tabs = QTabWidget()

        # Configure tab behavior
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)

        # Custom TabBar for renaming
        custom_tab_bar = RenameTabBar()
        custom_tab_bar.tabNameChanged.connect(self.rename_tab)
        self.tabs.setTabBar(custom_tab_bar)

        # Create container widget for buttons
        self.setup_corner_buttons()

        # Connect signals
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.setCentralWidget(self.tabs)
        self.setup_system_tray()
        self.load_sessions_on_startup()
        self.tabs.repaint()

    def setup_corner_buttons(self):
        """Setup the corner buttons: Add tab (+) and hamburger menu"""
        # Create container widget
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(2)

        # Add tab button (+)
        add_tab_button = QPushButton("+")
        add_tab_button.setFixedSize(30, 25)
        add_tab_button.setToolTip(tr("Add new tab"))
        add_tab_button.clicked.connect(lambda: self.add_new_tab())
        corner_layout.addWidget(add_tab_button)

        # Hamburger menu button
        menu_button = QPushButton("☰")
        menu_button.setFixedSize(30, 25)
        menu_button.setToolTip(tr("Menu"))
        menu_button.clicked.connect(self.show_hamburger_menu)
        corner_layout.addWidget(menu_button)

        # Set the corner widget
        self.tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)

    def show_hamburger_menu(self):
        """Show the hamburger menu with the requested options"""
        menu = QMenu(self)

        # Quick guide
        quick_guide_action = QAction(tr("📖 Quick guide"), self)
        quick_guide_action.triggered.connect(self.show_quick_guide)
        menu.addAction(quick_guide_action)

        # About
        about_action = QAction(tr("ℹ️ About"), self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)

        # Donate
        donate_action = QAction(tr("💝 Donate"), self)
        donate_action.triggered.connect(self.show_donate)
        menu.addAction(donate_action)

        menu.addSeparator()

        # Exit
        exit_action = QAction(tr("❌ Quit"), self)
        exit_action.triggered.connect(self.quit_application)
        menu.addAction(exit_action)

        # Show menu at the button position
        button = self.sender()
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def show_quick_guide(self):
        """Show quick guide dialog"""
        guide_text = tr("quick_guide_content")

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("Quick guide"))
        msg.setText(guide_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_about(self):
        """Show about dialog with app information"""
        about_text = tr("about_content")

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("About WhatsApp MultiSession"))
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Add button to send email
        contact_button = msg.addButton(tr("📧 Contact developer"), QMessageBox.ButtonRole.ActionRole)
        contact_button.clicked.connect(lambda: webbrowser.open("mailto:jhandervelbux@gmail.com?subject=WhatsApp MultiSession - Inquiry"))

        msg.exec()

    def show_donate(self):
        """Show donation dialog"""
        donate_text = tr("donate_content")

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("Donations"))
        msg.setText(donate_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Add button to open donation page
        donate_button = msg.addButton(tr("Open donation page"), QMessageBox.ButtonRole.ActionRole)
        donate_button.clicked.connect(lambda: webbrowser.open("https://www.paypal.com/donate/?hosted_button_id=FX7FC6R7WJ85W"))

        msg.exec()

    def setup_app_directory(self):
        """Setup application directory and session subdirectories"""
        home_dir = os.path.expanduser("~")
        self.app_dir = os.path.join(home_dir, ".WAms")
        self.sessions_dir = os.path.join(self.app_dir, "sessions")
        self.downloads_dir = os.path.join(self.app_dir, "downloads")

        for directory in [self.app_dir, self.sessions_dir, self.downloads_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Directory created: {directory}")

    def load_sessions_on_startup(self):
        """Scans the sessions directory and loads each one as a tab."""
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

        session_folders = [d for d in os.listdir(self.sessions_dir)
                          if os.path.isdir(os.path.join(self.sessions_dir, d))]

        if not session_folders:
            self.add_new_tab(tr("Default Session"))
        else:
            for session_name in sorted(session_folders):
                self.add_new_tab(session_name)
        print(f"Loaded {len(session_folders) or 1} session(s).")

    def add_new_tab(self, name=None):
        """Adds a new tab with its own QWebEngineView and profile."""
        if name is None:
            i = 1
            while True:
                name = tr("Session {}").format(i)
                if not os.path.exists(os.path.join(self.sessions_dir, name)):
                    break
                i += 1

        # Create web view and profile
        webview = QWebEngineView()
        profile_path = os.path.join(self.sessions_dir, name)

        # Create profile directory if it doesn't exist
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)
            print(f"Created new profile directory: {profile_path}")

        # Each tab gets its own profile
        profile = QWebEngineProfile(name, webview)
        profile.setPersistentStoragePath(profile_path)
        profile.setCachePath(os.path.join(profile_path, "cache"))

        # Configure User-Agent and headers for this profile
        system_locale = QLocale.system()
        language_code = system_locale.name().replace('_', '-')
        agent = f"Safari/537.36 Mozilla/5.0 (X11; Linux x86_64) Chrome/103.0.5060.114 Edg/103.0.1264.51 AppleWebKit/537.36 (KHTML, like Gecko) Accept-Language: {language_code},en;q=0.9"
        profile.setHttpUserAgent(agent)
        profile.setHttpAcceptLanguage(f"{language_code},en;q=0.9")

        # Set up the page with the custom profile
        page = web.WhatsApp(profile, self)
        webview.setPage(page)

        # Connect download requests to the main download handler
        profile.downloadRequested.connect(self.download)
        profile.setNotificationPresenter(lambda notif: self.show_notification(notif, webview))

        # Configure webview settings
        self.configure_webview_settings(webview)
        webview.load(QUrl("https://web.whatsapp.com"))

        # Store profile path and name in webview for later reference
        webview.profile_path = profile_path
        webview.profile = profile
        webview.session_name = name

        # Add the fully configured webview as a new tab
        index = self.tabs.addTab(webview, name)
        self.tabs.setCurrentIndex(index)

        self.tabs.setTabsClosable(True)
        self.tabs.tabBar().update()

        return webview

    def rename_tab(self, index, new_name):
        """Renames a tab and its corresponding session folder using a safer approach."""
        new_name = new_name.strip()
        if not new_name:
            return  # Don't allow empty names

        current_webview = self.tabs.widget(index)
        if not current_webview:
            return

        old_name = self.tabs.tabText(index)
        if old_name == new_name:
            return

        # Check if another tab already has this name
        for i in range(self.tabs.count()):
            if i != index and self.tabs.tabText(i) == new_name:
                QMessageBox.warning(self, tr("Rename Failed"), tr("A tab named '{}' already exists.").format(new_name))
                return

        old_path = os.path.join(self.sessions_dir, old_name)
        new_path = os.path.join(self.sessions_dir, new_name)

        # Check if the target folder already exists
        if os.path.exists(new_path):
            QMessageBox.warning(self, tr("Rename Failed"), tr("A session folder named '{}' already exists.").format(new_name))
            return

        try:
            # SAFE APPROACH: Don't modify active profiles, just rename the directory
            # and update our references

            # Rename the directory
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                print(f"Successfully renamed profile folder: '{old_path}' -> '{new_path}'")
            else:
                # If old directory doesn't exist, create new one
                os.makedirs(new_path, exist_ok=True)
                print(f"Created new profile directory: {new_path}")

            # Update our internal references (but NOT the active profile paths)
            current_webview.profile_path = new_path
            current_webview.session_name = new_name

            # Update tab text only after successful directory operation
            self.tabs.setTabText(index, new_name)
            print(f"Successfully renamed tab from '{old_name}' to '{new_name}'")

        except OSError as e:
            print(f"Error renaming session folder: {e}")
            QMessageBox.critical(self, tr("Error"), tr("Could not rename the session folder.\\nError: {}").format(e))
        except Exception as e:
            print(f"Unexpected error during rename: {e}")
            QMessageBox.critical(self, tr("Error"), tr("An unexpected error occurred.\\nError: {}").format(e))

    def safe_remove_directory(self, path, max_attempts=3):
        """Safely remove a directory with retry logic."""
        for attempt in range(max_attempts):
            try:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    print(f"Successfully deleted directory: {path}")
                    return True
            except PermissionError:
                print(f"Permission error deleting {path}, attempt {attempt + 1}/{max_attempts}")
                time.sleep(0.5)  # Wait before retry
            except OSError as e:
                print(f"OS error deleting {path}: {e}, attempt {attempt + 1}/{max_attempts}")
                time.sleep(0.5)

        print(f"Failed to delete directory after {max_attempts} attempts: {path}")
        return False

    def close_tab(self, index):
        """Handles the request to close a tab, asking for confirmation."""
        if self.tabs.count() <= 1:
            # Don't allow closing the last tab
            QMessageBox.information(self, tr("Cannot Close"), tr("Cannot close the last tab. The application needs at least one session."))
            return

        tab_name = self.tabs.tabText(index)
        reply = QMessageBox.question(
            self,
            tr('Confirm Close'),
            tr("Are you sure you want to close the tab '{}'? This will permanently delete its session data.").format(tab_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            current_webview = self.tabs.widget(index)
            session_path = os.path.join(self.sessions_dir, tab_name)

            print(f"Attempting to close tab '{tab_name}' with session path: {session_path}")

            try:
                # Close the webview and its profile properly
                if current_webview and hasattr(current_webview, 'profile'):
                    # Clear cache and close connections
                    current_webview.profile.clearHttpCache()
                    current_webview.page().deleteLater()

                # Remove the tab first
                self.tabs.removeTab(index)

                # Schedule the webview for deletion
                if current_webview:
                    current_webview.deleteLater()

                # Process events to ensure cleanup
                QApplication.processEvents()

                # Use a timer to delete the directory after a short delay
                # This ensures all file handles are closed
                QTimer.singleShot(500, lambda: self.safe_remove_directory(session_path))

            except Exception as e:
                print(f"Error closing tab: {e}")
                QMessageBox.critical(self, tr("Error"), tr("Error closing tab: {}").format(e))

    def configure_webview_settings(self, webview):
        """Configure all webview settings"""
        settings = webview.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setDefaultTextEncoding("UTF-8")

    def setup_window_configuration(self):
        default_width, default_height = 1000, 600
        self.setMinimumSize(default_width, default_height)
        width = self.settings.value("window/width", default_width, int)
        height = self.settings.value("window/height", default_height, int)
        pos_x = self.settings.value("window/pos_x", 100, int)
        pos_y = self.settings.value("window/pos_y", 100, int)
        is_maximized = self.settings.value("window/maximized", False, bool)
        self.resize(max(width, default_width), max(height, default_height))
        self.move(pos_x, pos_y)
        if is_maximized:
            self.showMaximized()
        else:
            self.show()
        print(f"Window configured: {width}x{height} at ({pos_x}, {pos_y})")

    def setup_system_locale(self):
        try:
            system_locale = QLocale.system()
            locale_name = system_locale.name()
            os.environ['LANG'] = f"{locale_name}.UTF-8"
            os.environ['LC_ALL'] = f"{locale_name}.UTF-8"
            try:
                locale.setlocale(locale.LC_ALL, f"{locale_name}.UTF-8")
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_ALL, '')
                except locale.Error:
                    pass
            print(f"System locale configured: {locale_name}")
        except Exception as e:
            print(f"Error configuring system locale: {e}")

    def setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("System tray is not available.")
            return
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip(tr("WhatsApp MultiSession"))
        self.create_tray_menu()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        print("System tray configured.")

    def create_tray_menu(self):
        self.tray_menu = QMenu()
        show_action = QAction(tr("Show"), self)
        show_action.triggered.connect(self.show_window)
        self.tray_menu.addAction(show_action)
        self.tray_menu.addSeparator()
        quit_action = QAction(tr("Exit"), self)
        quit_action.triggered.connect(self.quit_application)
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()

    def minimize_to_tray(self):
        if hasattr(self, 'tray_icon'):
            self.hide()
            self.tray_icon.show()
            if not hasattr(self, 'first_minimize_shown'):
                self.tray_icon.showMessage(
                    tr("WhatsApp MultiSession"),
                    tr("Minimized to system tray."),
                    QSystemTrayIcon.MessageIcon.Information, 3000)
                self.first_minimize_shown = True

    def quit_application(self):
        self.force_quit = True
        # Close all tabs properly before quitting
        while self.tabs.count() > 0:
            current_webview = self.tabs.widget(0)
            if current_webview and hasattr(current_webview, 'profile'):
                current_webview.profile.clearHttpCache()
            self.tabs.removeTab(0)
            if current_webview:
                current_webview.deleteLater()

        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        self.save_window_settings()
        QApplication.instance().quit()

    def save_window_settings(self):
        if not self.isMaximized():
            self.settings.setValue("window/width", self.width())
            self.settings.setValue("window/height", self.height())
            self.settings.setValue("window/pos_x", self.x())
            self.settings.setValue("window/pos_y", self.y())
        self.settings.setValue("window/maximized", self.isMaximized())
        self.settings.sync()
        print("Window settings saved.")

    def download(self, download):
        if download.state() == QWebEngineDownloadRequest.DownloadState.DownloadRequested:
            current_webview = self.tabs.currentWidget()
            default_path = os.path.join(self.downloads_dir, download.downloadFileName())

            path, _ = QFileDialog.getSaveFileName(
                self, tr("WhatsApp MultiSession - Save file"), default_path
            )
            if path:
                download.setDownloadDirectory(os.path.dirname(path))
                download.setDownloadFileName(os.path.basename(path))
                download.url().setPath(path)
                download.accept()

    def show_notification(self, notification, source_webview):
        """Create a notification through the DBus.Notification for the system."""
        if self.settings.value("notification/app", True, bool):
            try:
                title = (
                    notification.title()
                    if self.settings.value("notification/show_name", True, bool)
                    else tr("WhatsApp MultiSession")
                )
                message = (
                    notification.message()
                    if self.settings.value("notification/show_msg", True, bool)
                    else tr("New message...")
                )
                icon = (
                    self.getPathImage(notification.icon())
                    if self.settings.value("notification/show_photo", True, bool)
                    else "com.dev.sriramp.whatsappLinux"
                )

                n = Notification.Notification(title, message, timeout=3000)
                n.setUrgency(Notification.Urgency.NORMAL)
                n.setCategory("im.received")
                n.setIconPath(icon)
                n.setHint("desktop-entry", "com.dev.sriramp.whatsappLinux")
                n.show()
            except Exception as e:
                print(e)

    def getPathImage(self, qin):
        """Save contact image in temporary folder for notifications"""
        try:
            tmp_dir = os.path.join(self.app_dir, "tmp")
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)

            path = os.path.join(tmp_dir, "whatsapp.png")

            qout = QImage(qin.width(), qin.height(), QImage.Format.Format_ARGB32)
            qout.fill(Qt.GlobalColor.transparent)

            brush = QBrush(qin)
            pen = QPen()
            pen.setColor(Qt.GlobalColor.darkGray)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

            painter = QPainter(qout)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.drawRoundedRect(
                0, 0, qin.width(), qin.height(), qin.width() // 2, qin.height() // 2
            )
            painter.end()
            c = qout.save(path)
            if c == False:
                return "com.dev.sriramp.whatsappLinux"
            else:
                return path
        except:
            return "com.dev.sriramp.whatsappLinux"

    def closeEvent(self, event):
        """On close, either minimize to tray or save settings and exit."""

        if self.force_quit:
            event.accept()
            return

        if self.settings.value("general/minimize_on_close", True, bool) and hasattr(self, 'tray_icon') and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.minimize_to_tray()
        else:
            self.quit_application()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.isMaximized():
            self.settings.setValue("window/width", self.width())
            self.settings.setValue("window/height", self.height())

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self.isMaximized():
            self.settings.setValue("window/pos_x", self.x())
            self.settings.setValue("window/pos_y", self.y())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    system_locale = QLocale.system()
    QLocale.setDefault(system_locale)

    window = MainWindow()
    window.setWindowTitle("WhatsApp MultiSession")

    if len(sys.argv) > 1:
        link = sys.argv[1]
        if link.startswith("whatsapp://"):
            QDesktopServices.openUrl(QUrl(link.replace("whatsapp://", "https://wa.me/")))
    else:
        window.show()

    sys.exit(app.exec())
