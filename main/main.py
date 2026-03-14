import os
import sys

# Configuración de rutas para encontrar los módulos
app_path = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(app_path, 'modules')):
    sys.path.insert(0, app_path)
else:
    sys.path.insert(0, os.path.join(app_path, '..'))

from modules.system_setup import initialize_environment
system_config = initialize_environment()

# Ensure system locale is detected and set to UTF-8 before any GUI/WebEngine initialization
# This maintains automatic detection while preventing ANSI encoding warnings
import locale
import os
try:
    # Set to system default
    locale.setlocale(locale.LC_ALL, '')
    current_locale, encoding = locale.getlocale()

    if not current_locale:
        # Fallback if detection fails but try to avoid hardcoding
        current_locale = 'en_US'

    # Force UTF-8 environment for child processes
    os.environ['LANG'] = f"{current_locale}.UTF-8"
    os.environ['LC_ALL'] = f"{current_locale}.UTF-8"
    try:
        locale.setlocale(locale.LC_ALL, f"{current_locale}.UTF-8")
    except Exception:
        pass
except Exception as e:
    print(f"Initial locale detection failed, using defaults: {e}")
    os.environ['LANG'] = 'en_US.UTF-8'
    os.environ['LC_ALL'] = 'en_US.UTF-8'

import locale
import shutil
import time
import webbrowser

from PyQt6.QtCore import Qt, QUrl, QSettings, QLocale, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QImage, QPainter, QBrush, QPen, QAction, QDesktopServices
from PyQt6.QtWidgets import (QMainWindow, QApplication, QFileDialog, QSystemTrayIcon, QMenu,
                             QTabWidget, QPushButton, QMessageBox, QLineEdit, QTabBar, QWidget,
                             QHBoxLayout, QDialog, QVBoxLayout, QLabel)
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
        
        # Map local coordinates to global ones so the popup appears exactly over the tab
        global_pos = self.mapToGlobal(rect.topLeft())
        self.editor.move(global_pos)
        
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

        # Prevenir suspensión del renderizado
        self.keep_alive_timer = QTimer(self)
        self.keep_alive_timer.timeout.connect(self.prevent_suspension)
        self.keep_alive_timer.start(30000)  # Cada 30 segundos

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

    def prevent_suspension(self):
        """Mantiene activos los procesos de renderizado"""
        for i in range(self.tabs.count()):
            webview = self.tabs.widget(i)
            if webview and hasattr(webview, 'page'):
                # Fuerza una pequeña actualización para mantener activo el proceso
                webview.page().runJavaScript("void(0);")

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

        # Autostart
        autostart_action = QAction(tr("Autostart"), self)
        autostart_action.setCheckable(True)
        # Check actual file existence for truth, rather than just config.ini
        autostart_dir = os.path.join(os.path.expanduser('~'), '.config', 'autostart')
        autostart_path = os.path.join(autostart_dir, 'wams.desktop')
        is_autostart = os.path.exists(autostart_path)
        
        autostart_action.setChecked(is_autostart)
        
        # Ensure config setting matches reality
        if is_autostart != self.settings.value("general/autostart", False, bool):
            self.settings.setValue("general/autostart", is_autostart)
            
        autostart_action.triggered.connect(self.toggle_autostart)
        menu.addAction(autostart_action)

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

        # Obtener la carpeta de descargas usando el estándar XDG
        self.downloads_dir = self.get_downloads_directory()

        # Solo crear los directorios de la aplicación, no el de descargas
        for directory in [self.app_dir, self.sessions_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Directory created: {directory}")

        # Verificar que la carpeta de descargas existe
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)
            print(f"Downloads directory created: {self.downloads_dir}")
        else:
            print(f"Using Downloads directory: {self.downloads_dir}")

    def get_downloads_directory(self):
        """
        Obtiene la carpeta de descargas del usuario usando el estándar XDG
        y varios métodos de fallback para máxima compatibilidad
        """
        import subprocess

        # Método 1: Usar xdg-user-dir (más confiable)
        try:
            result = subprocess.run(['xdg-user-dir', 'DOWNLOAD'],
                                capture_output=True, text=True, check=True)
            downloads_path = result.stdout.strip()
            if downloads_path and os.path.exists(downloads_path):
                print(f"Downloads directory found via xdg-user-dir: {downloads_path}")
                return downloads_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("xdg-user-dir not available, trying alternative methods...")

        # Método 2: Leer el archivo de configuración XDG directamente
        home_dir = os.path.expanduser("~")
        xdg_config_file = os.path.join(home_dir, ".config", "user-dirs.dirs")

        if os.path.exists(xdg_config_file):
            try:
                with open(xdg_config_file, 'r') as f:
                    for line in f:
                        if line.startswith('XDG_DOWNLOAD_DIR='):
                            # Extraer la ruta, removiendo comillas y expandiendo variables
                            path = line.split('=', 1)[1].strip().strip('"\'')
                            path = path.replace('$HOME', home_dir)
                            if os.path.exists(path):
                                print(f"Downloads directory found via XDG config: {path}")
                                return path
            except Exception as e:
                print(f"Error reading XDG config file: {e}")

        # Método 3: Variable de entorno XDG_DOWNLOAD_DIR
        xdg_download = os.environ.get('XDG_DOWNLOAD_DIR')
        if xdg_download and os.path.exists(xdg_download):
            print(f"Downloads directory found via XDG_DOWNLOAD_DIR: {xdg_download}")
            return xdg_download

        # Método 4: Fallbacks comunes por idioma
        common_download_names = [
            'Downloads',    # Inglés
            'Descargas',    # Español
            'Téléchargements',  # Francés
            'Download',     # Alemán
            'Scaricati',    # Italiano
            'Baixades',     # Catalán
            'Preuzimanja',  # Serbio
            'Λήψεις',       # Griego
            'Загрузки',     # Ruso
        ]

        for name in common_download_names:
            path = os.path.join(home_dir, name)
            if os.path.exists(path):
                print(f"Downloads directory found via fallback: {path}")
                return path

        # Método 5: Último recurso - crear WAms Downloads en inglés
        fallback_path = os.path.join(home_dir, 'WAms')
        print(f"Using fallback downloads directory: {fallback_path}")
        return fallback_path

    def load_sessions_on_startup(self):
        """Scans the sessions directory and loads each one as a tab using mapped aliases."""
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

        session_folders = [d for d in os.listdir(self.sessions_dir)
                          if os.path.isdir(os.path.join(self.sessions_dir, d))
                          and not d.endswith(".deleted")]

        # Clean up any leftover .deleted folders from previous crashes
        for d in os.listdir(self.sessions_dir):
            if d.endswith(".deleted"):
                shutil.rmtree(os.path.join(self.sessions_dir, d), ignore_errors=True)

        if not session_folders:
            self.add_new_tab(tr("Default Session"))
        else:
            # We use the folder name as a fixed ID, and read the Alias from settings
            for folder_id in sorted(session_folders):
                alias = self.settings.value(f"aliases/{folder_id}", folder_id, str)
                self.add_new_tab(alias, folder_id)
        print(f"Loaded {len(session_folders) or 1} session(s).")

    def add_new_tab(self, name=None, folder_id=None):
        """Adds a new tab with a permanent folder ID and a display alias."""
        # if folder_id is None, it's a brand new session
        if folder_id is None:
            i = 1
            while True:
                folder_id = f"session_{i}"
                if not os.path.exists(os.path.join(self.sessions_dir, folder_id)):
                    break
                i += 1
            if name is None:
                name = tr("Session {}").format(i)
        
        # Ensure we have an initial name if loading existing
        if name is None:
            name = folder_id

        try:
            # Create web view and profile with a parent to avoid it being a top-level window in Wayland
            webview = QWebEngineView(self)
            webview.hide() # Force hide until it's properly embedded in the tab widget
            profile_path = os.path.join(self.sessions_dir, folder_id)

            # Create profile directory if it doesn't exist
            if not os.path.exists(profile_path):
                os.makedirs(profile_path)
                print(f"Created new profile directory: {profile_path}")

            # Each tab gets its own profile based on the permanent ID
            profile = QWebEngineProfile(folder_id) # No parent yet
            profile.setPersistentStoragePath(profile_path)
            profile.setCachePath(os.path.join(profile_path, "cache"))
            profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
            profile.setHttpCacheMaximumSize(50 * 1024 * 1024)  # 50 MB limit

            # Store alias in settings
            self.settings.setValue(f"aliases/{folder_id}", name)
            self.settings.sync()

            # Configure User-Agent and headers
            system_locale = QLocale.system()
            language_code = system_locale.name().replace('_', '-')
            agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            profile.setHttpUserAgent(agent)
            profile.setHttpAcceptLanguage(f"{language_code},en;q=0.9")
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

            # Set up the page with webview as parent
            # This ensures page is destroyed with webview
            page = web.WhatsApp(profile, webview)
            webview.setPage(page)
            
            # Make the profile a child of the page so it lives as long as the page
            # and is destroyed AFTER the page is gone/stopped.
            profile.setParent(page)

            # Connect signals
            profile.downloadRequested.connect(self.download)
            profile.setNotificationPresenter(lambda notif: self.show_notification(notif, webview))

            # Configure settings
            self.configure_webview_settings(webview)
            webview.load(QUrl("https://web.whatsapp.com"))

            # Store permanent references
            webview.folder_id = folder_id
            webview.profile_path = profile_path
            webview.profile = profile
            webview.session_name = name # This is the alias/display name

            # Add tab with display name
            index = self.tabs.addTab(webview, name)
            self.tabs.setCurrentIndex(index)
            self.tabs.setTabsClosable(True)
            self.tabs.tabBar().update()

            return webview

        except Exception as e:
            print(f"Error creating tab: {e}")
            return None

    def rename_tab(self, index, new_name):
        """Renames a tab (Alias) without moving folders or crashing the profile."""
        new_name = new_name.strip()
        if not new_name:
            return

        current_webview = self.tabs.widget(index)
        if not current_webview:
            return

        old_name = self.tabs.tabText(index)
        if old_name == new_name:
            return

        # Check if another tab already has this alias
        for i in range(self.tabs.count()):
            if i != index and self.tabs.tabText(i) == new_name:
                QMessageBox.warning(self, tr("Rename Failed"), tr("A tab named '{}' already exists.").format(new_name))
                return

        try:
            # We ONLY update the alias in settings and the UI
            # No folder moves = No Segfault
            folder_id = current_webview.folder_id
            
            self.settings.setValue(f"aliases/{folder_id}", new_name)
            self.settings.sync()
            
            current_webview.session_name = new_name
            self.tabs.setTabText(index, new_name)
            
            print(f"Renamed alias: '{old_name}' -> '{new_name}' (ID: {folder_id})")

        except Exception as e:
            print(f"Error renaming session alias: {e}")
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
        # Safety check for index and double calls
        if index < 0 or index >= self.tabs.count():
            return
            
        if hasattr(self, "_closing_tab_lock") and self._closing_tab_lock:
            return
            
        tab_name = self.tabs.tabText(index)
        is_last_tab = self.tabs.count() <= 1
        
        reply = QMessageBox.question(
            self,
            tr('Confirm Close'),
            tr("Are you sure you want to close the tab '{}'? This will permanently delete its session data.").format(tab_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._closing_tab_lock = True
            current_webview = self.tabs.widget(index)
            folder_id = getattr(current_webview, 'folder_id', None)
            session_path = getattr(current_webview, 'profile_path', None)

            if not folder_id or not session_path:
                print(f"Error: Missing folder information for tab {index}")
                self.tabs.removeTab(index)
                self._closing_tab_lock = False
                return

            print(f"Attempting to close tab '{tab_name}' (ID: {folder_id})")

            try:
                # 1. Clear profile settings for this ID
                self.settings.remove(f"aliases/{folder_id}")
                self.settings.sync()

                # 2. Shutdown the page first to stop all JS and timers
                if current_webview.page():
                    # Stop its internal timers if any
                    current_webview.page().runJavaScript("window.stop();")
                    current_webview.page().deleteLater()
                
                # 3. Remove tab (destroys the webview container)
                self.tabs.removeTab(index)
                current_webview.deleteLater()

                # If it was the last tab, recreate a new one
                if is_last_tab:
                    self.add_new_tab(tr("Default Session"))

                self._closing_tab_lock = False
                # Process events to let Qt start deleting objects
                QApplication.processEvents()

                # 4. Immediate Rename + Delayed Physical deletion
                # Renaming prevents the session from being loaded if the app restarts before deletion
                temp_deleted_path = session_path + ".deleted"
                
                def final_cleanup():
                    # Check if program is still running
                    if not QApplication.instance() or not QApplication.instance().activeWindow():
                        return
                        
                    if os.path.exists(temp_deleted_path):
                        shutil.rmtree(temp_deleted_path, ignore_errors=True)
                        print(f"Permanently deleted session data: {temp_deleted_path}")

                try:
                    if os.path.exists(session_path):
                        # On Linux, renaming usually works even if files are open
                        os.rename(session_path, temp_deleted_path)
                        print(f"Session folder marked for deletion: {temp_deleted_path}")
                except Exception as e:
                    print(f"Could not rename session folder immediately: {e}")
                    # If rename fails (rare on Linux), we'll try to delete the original path directly
                    temp_deleted_path = session_path
                
                QTimer.singleShot(3000, final_cleanup)

            except Exception as e:
                print(f"Error closing tab: {e}")
                QMessageBox.critical(self, tr("Error"), tr("Error closing tab: {}").format(e))

    def configure_webview_settings(self, webview):
        """Configure all webview settings with error handling"""
        try:
            settings = webview.settings()

            # Configuraciones básicas
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
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, True)

            # Configuraciones avanzadas con manejo de excepciones
            try:
                settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
            except Exception as e:
                print(f"Warning: Could not enable hardware acceleration: {e}")

            settings.setDefaultTextEncoding("UTF-8")

        except Exception as e:
            print(f"Error configuring webview settings: {e}")

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
        # Showing the window is now deferred to __main__ after full initialization
        self.save_window_settings()
        print(f"Window geometry configured: {width}x{height} at ({pos_x}, {pos_y})")

    def setup_system_locale(self):
        # Uses the locale already configured at startup
        try:
            current_locale = os.environ.get('LANG', 'en_US.UTF-8').split('.')[0]
            print(f"System locale confirmed: {current_locale}")
        except Exception as e:
            print(f"Error viewing system locale: {e}")

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
        """Saves settings and shuts down everything cleanly."""
        self.force_quit = True
        
        # 1. Stop app-level timers to avoid accessing dying objects
        if hasattr(self, 'keep_alive_timer'):
            self.keep_alive_timer.stop()
            
        print("Stopping application timers...")
            
        # 2. Hide UI components
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            
        # 3. Save state
        self.save_window_settings()
        
        # 4. Quit - Qt will handle the destruction of the widget tree
        print("Application shutting down...")
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

    def toggle_autostart(self, state):
        """Enable or disable application autostart on session login"""
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file_name = "wams.desktop"
        autostart_path = os.path.join(autostart_dir, desktop_file_name)

        if state:
            try:
                if not os.path.exists(autostart_dir):
                    os.makedirs(autostart_dir)

                # Source candidates
                src_paths = [
                    "/usr/share/applications/wams.desktop",
                    os.path.join(app_path, "wams.desktop"),
                    os.path.join(app_path, "main", "wams.desktop")
                ]

                src_file = None
                for path in src_paths:
                    if os.path.exists(path):
                        src_file = path
                        break

                if src_file:
                    shutil.copy2(src_file, autostart_path)
                    # Ensure it has correct permissions
                    os.chmod(autostart_path, 0o755)
                    print(f"Autostart enabled: {src_file} -> {autostart_path}")
                else:
                    # Fallback manually create the desktop file if not found
                    with open(autostart_path, 'w') as f:
                        f.write("[Desktop Entry]\n")
                        f.write("Name=WhatsApp MultiSession\n")
                        f.write("Exec=wams %u\n")
                        f.write("Icon=wams\n")
                        f.write("Terminal=false\n")
                        f.write("Type=Application\n")
                        f.write("Categories=Network;Chat;\n")
                    print("Autostart enabled (manual fallback created)")

                self.settings.setValue("general/autostart", True)
            except Exception as e:
                print(f"Error enabling autostart: {e}")
                QMessageBox.warning(self, tr("Error"), f"Could not enable autostart: {e}")
        else:
            try:
                if os.path.exists(autostart_path):
                    os.remove(autostart_path)
                    print(f"Autostart disabled: removed {autostart_path}")
                self.settings.setValue("general/autostart", False)
            except Exception as e:
                print(f"Error disabling autostart: {e}")
                QMessageBox.warning(self, tr("Error"), f"Could not disable autostart: {e}")

        self.settings.sync()


class SessionSelectorDialog(QDialog):
    """Dialog that lets the user pick which session should handle an external link."""

    def __init__(self, tabs: QTabWidget, parent=None):
        super().__init__(parent)
        self.selected_index = -1

        self.setWindowTitle(tr("Open link in…"))
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(tr("Which session should open this link?"))
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        for i in range(tabs.count()):
            alias = tabs.tabText(i)
            btn = QPushButton(alias)
            btn.setMinimumHeight(36)
            # Capture loop variable correctly via default argument
            btn.clicked.connect(lambda checked, idx=i: self._select(idx))
            layout.addWidget(btn)

        cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _select(self, index: int):
        self.selected_index = index
        self.accept()


def _route_external_link(window: 'MainWindow', raw_link: str):
    """Resolve and route an external WhatsApp link to the appropriate session tab."""
    # Normalise to web.whatsapp.com URL
    if raw_link.startswith("whatsapp://"):
        new_url = raw_link.replace("whatsapp://", "https://web.whatsapp.com/")
    elif "api.whatsapp.com/send" in raw_link:
        new_url = raw_link.replace("https://api.whatsapp.com/", "https://web.whatsapp.com/")
        new_url = new_url.replace("http://api.whatsapp.com/", "https://web.whatsapp.com/")
    else:
        return  # Unrecognised scheme – do nothing

    tab_count = window.tabs.count()

    if tab_count == 1:
        # Single session: load directly
        webview = window.tabs.widget(0)
        if webview:
            webview.load(QUrl(new_url))
        return

    # Multiple sessions: ask the user
    dlg = SessionSelectorDialog(window.tabs, parent=window)
    if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_index >= 0:
        webview = window.tabs.widget(dlg.selected_index)
        if webview:
            webview.load(QUrl(new_url))
            window.tabs.setCurrentIndex(dlg.selected_index)  # Activate the chosen tab
            window.show_window()  # Bring the main window to front


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set app names to prevent "main.py" or "python" from showing up in Wayland taskbars
    app.setApplicationName("WAms")
    app.setApplicationDisplayName("WhatsApp MultiSession")
    app.setDesktopFileName("wams.desktop")
    
    app.setQuitOnLastWindowClosed(False)

    system_locale = QLocale.system()
    QLocale.setDefault(system_locale)

    window = MainWindow()
    window.setWindowTitle("WhatsApp MultiSession")

    if window.settings.value("window/maximized", False, bool):
        window.showMaximized()
    else:
        window.show()

    if len(sys.argv) > 1:
        link = sys.argv[1]
        if link.startswith("whatsapp://") or "api.whatsapp.com/send" in link:
            # Use a short delay so the window is fully rendered before the dialog pops up
            QTimer.singleShot(300, lambda: _route_external_link(window, link))

    sys.exit(app.exec())
