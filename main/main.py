"""
WhatsApp MultiSession (WAms) - Main Application
A native PyQt6 application for managing multiple WhatsApp Web sessions simultaneously.
"""
import locale
import os
import shutil
import sys
import time
import webbrowser

# Constantes de la aplicación
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".WAms")
"""Directorio de datos de la aplicación (~/.WAms)"""

KEEP_ALIVE_INTERVAL = 30000
"""Intervalo del timer para mantener activos los procesos de renderizado (30 segundos)"""

TAB_CLOSE_CLEANUP_DELAY = 3000
"""Retraso antes de eliminar físicamente los datos de sesión cerrada (3 milisegundos)"""

DEFAULT_WINDOW_WIDTH = 1000
"""Ancho predeterminado de la ventana"""

DEFAULT_WINDOW_HEIGHT = 600
"""Alto predeterminado de la ventana"""

# Configuración de rutas para encontrar los módulos
app_path = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(app_path, 'modules')):
    sys.path.insert(0, app_path)
else:
    sys.path.insert(0, os.path.join(app_path, '..'))

# Asegurar que el locale del sistema se detecte y configure UTF-8 antes de cualquier inicialización de GUI/WebEngine
# Esto mantiene la detección automática mientras previene advertencias de codificación ANSI
try:
    # Establecer el locale predeterminado del sistema
    locale.setlocale(locale.LC_ALL, '')
    current_locale, encoding = locale.getlocale()

    if not current_locale:
        # Fallback si la detección falla, intentar evitar hardcodear
        current_locale = 'en_US'

    # Forzar entorno UTF-8 para procesos hijos
    os.environ['LANG'] = f"{current_locale}.{encoding}"
    os.environ['LC_ALL'] = f"{current_locale}.{encoding}"
    try:
        locale.setlocale(locale.LC_ALL, f"{current_locale}.{encoding}")
    except Exception:
        pass
except Exception as e:
    print(f"Initial locale detection failed, using defaults: {e}")
    os.environ['LANG'] = 'en_US.UTF-8'
    os.environ['LC_ALL'] = 'en_US.UTF-8'

from PyQt6.QtCore import Qt, QUrl, QSettings, QLocale, pyqtSignal, QTimer, QObject, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusMessage
from PyQt6.QtGui import QIcon, QImage, QPainter, QBrush, QPen, QAction
from PyQt6.QtWidgets import (QMainWindow, QApplication, QFileDialog, QSystemTrayIcon, QMenu,
                             QTabWidget, QPushButton, QMessageBox, QLineEdit, QTabBar, QWidget,
                             QHBoxLayout, QDialog, QVBoxLayout, QLabel)
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

import modules.notification as Notification
from modules.i18n import tr
import modules.web as web

def get_app_icon():
    """Obtiene el icono de la aplicación desde diferentes ubicaciones.
    
    Busca el icono en orden de prioridad:
    1. Instalación del paquete (/opt/wams/modules/wams.png)
    2. Iconos del sistema (/usr/share/icons/hicolor/256x256/apps/wams.png)
    3. Desarrollo local (rutas relativas)
    4. Fallback al icono del tema del sistema
    
    Returns:
        QIcon: El icono de la aplicación o un icono fallback si no se encuentra
    """
    icon_paths = [
        '/opt/wams/modules/wams.png',     # Instalación del paquete (corregido desde /usr/lib)
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
    """Barra de tabs personalizada que permite renombrar tabs con doble clic.
    
    Hereda de QTabBar y agrega funcionalidad de edición inline para que
    los usuarios puedan cambiar el nombre de las sesiones de WhatsApp.
    """
    tabNameChanged = pyqtSignal(int, str)

    def __init__(self, parent=None):
        """Inicializa la barra de tabs con un editor de texto emergente.
        
        Args:
            parent: Widget padre de la barra de tabs.
        """
        super().__init__(parent)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.hide()
        self.editor.editingFinished.connect(self.finish_editing)
        self.edit_index = -1

    def mouseDoubleClickEvent(self, event):
        """Maneja el evento de doble clic para iniciar la edición del tab.
        
        Args:
            event: Evento de clic que contiene la posición del clic.
        """
        self.edit_index = self.tabAt(event.pos())
        if self.edit_index >= 0:
            self.start_editing()

    def start_editing(self):
        """Inicia la edición del tab actual mostrando un campo de texto popup."""
        rect = self.tabRect(self.edit_index)
        self.editor.setFixedSize(rect.size())

        # Mapear coordenadas locales a globales para que el popup aparezca exactamente sobre el tab
        global_pos = self.mapToGlobal(rect.topLeft())
        self.editor.move(global_pos)

        self.editor.setText(self.tabText(self.edit_index))
        self.editor.show()
        self.editor.selectAll()
        self.editor.setFocus()

    def finish_editing(self):
        """Finaliza la edición del tab y emite la señal de cambio de nombre."""
        if self.edit_index >= 0:
            self.tabNameChanged.emit(self.edit_index, self.editor.text())
            self.editor.hide()
            self.edit_index = -1

class DBusHandler(QObject):
    """Manejador de mensajes D-Bus para la instancia única."""
    url_received = pyqtSignal(str)

    @pyqtSlot(str)
    def handle_url(self, url):
        self.url_received.emit(url)

class MainWindow(QMainWindow):
    """Ventana principal de la aplicación WhatsApp MultiSession.
    
    Gestiona múltiples sesiones de WhatsApp Web en tabs independientes,
    cada una con su propio perfil de navegador, cookies y almacenamiento.
    """
    def __init__(self, *args, **kwargs):
        """Inicializa la ventana principal y configura todos los componentes de la UI.
        
        Configura:
        - Icono de la aplicación
        - Locale del sistema
        - Directorio de datos de la aplicación
        - Ajustes de ventana
        - Sistema de bandeja (system tray)
        - Timer keep-alive para prevenir suspensión
        - Carga de sesiones existentes
        """
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
        self.keep_alive_timer.start(KEEP_ALIVE_INTERVAL)  # Cada 30 segundos

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
        """Mantiene activos los procesos de renderizado de todas las tabs.
        
        Se ejecuta periódicamente para evitar que el sistema suspenda
        los procesos de WebEngine por inactividad, enviando un pequeño
        script JavaScript nulo a cada tab activa.
        """
        for i in range(self.tabs.count()):
            webview = self.tabs.widget(i)
            if webview and hasattr(webview, 'page'):
                # Fuerza una pequeña actualización para mantener activo el proceso
                webview.page().runJavaScript("void(0);")

    def setup_corner_buttons(self):
        """Configura los botones de esquina: agregar tab (+) y menú hamburguesa.
        
        Crea un widget de esquina en la parte superior derecha del QTabWidget
        que contiene el botón para agregar nuevas sesiones y el botón de menú.
        """
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
        """Muestra el menú hamburguesa con opciones de guía, acerca de y donaciones.
        
        Crea un menú contextual con opciones de navegación rápida,
        información de la aplicación, donaciones y configuración de autostart.
        """
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
        """Muestra el diálogo con la guía rápida de uso de la aplicación."""
        guide_text = tr("quick_guide_content")

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("Quick guide"))
        msg.setText(guide_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def show_about(self):
        """Muestra el diálogo de información sobre la aplicación."""
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
        """Muestra el diálogo con opciones de donación para apoyar el desarrollo."""
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
        """Configura el directorio de datos de la aplicación (~/.WAms).
        
        Crea el directorio principal de la aplicación y el subdirectorio
        de sesiones si no existen. También obtiene y crea el directorio
        de descargas usando el estándar XDG.
        """
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
        """Obtiene la carpeta de descargas del usuario usando el estándar XDG.
        
        Implementa múltiples métodos de fallback para máxima compatibilidad:
        1. Comando xdg-user-dir (más confiable)
        2. Archivo de configuración XDG (~/.config/user-dirs.dirs)
        3. Variable de entorno XDG_DOWNLOAD_DIR
        4. Fallbacks comunes por idioma (Downloads, Descargas, etc.)
        5. Último recurso: crear directorio WAms en inglés
        
        Returns:
            str: Ruta absoluta al directorio de descargas del usuario.
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
        """Escanea el directorio de sesiones y carga cada una como un tab.
        
        Lee el directorio ~/.WAms/sessions/ y restaura todas las sesiones
        previamente guardadas, usando los alias configurados en settings.
        Si no hay sesiones, crea una sesión predeterminada.
        """
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
        """Agrega un nuevo tab con una sesión de WhatsApp Web independiente.
        
        Crea un nuevo perfil de navegador con almacenamiento persistente
        aislado, configurando idioma, tema y permisos para la sesión.
        
        Args:
            name (str, opcional): Nombre alias para mostrar en el tab.
            folder_id (str, opcional): ID permanente de la carpeta de sesión.
        
        Returns:
            QWebEngineView: El widget de la vista web del nuevo tab, o None si falla.
        """
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
        """Renombra un tab (alias) sin mover carpetas ni causar errores.
        
        Actualiza únicamente el alias en settings y la UI, manteniendo
        el ID permanente de la carpeta de sesión intacto.
        
        Args:
            index (int): Índice del tab a renombrar.
            new_name (str): Nuevo nombre para el tab.
        """
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

    def close_tab(self, index):
        """Maneja la solicitud de cerrar un tab, pidiendo confirmación.
        
        El proceso de cierre:
        1. Pide confirmación al usuario
        2. Limpia los settings del perfil
        3. Detiene la página web y elimina el tab
        4. Renombra la carpeta de sesión a .deleted
        5. Programa la eliminación física después de 3 segundos
        
        Args:
            index (int): Índice del tab a cerrar.
        """
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

                QTimer.singleShot(TAB_CLOSE_CLEANUP_DELAY, final_cleanup)

            except Exception as e:
                print(f"Error closing tab: {e}")
                QMessageBox.critical(self, tr("Error"), tr("Error closing tab: {}").format(e))

    def configure_webview_settings(self, webview):
        """Configura todos los ajustes de la vista web.
        
        Establece opciones para JavaScript, imágenes, WebGL, aceleración
        de hardware y otras características del navegador embebido.
        
        Args:
            webview (QWebEngineView): Vista web a configurar.
        """
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
        """Configura la geometría y posición de la ventana desde los ajustes guardados.
        
        Lee las preferencias de tamaño y posición de la ventana desde config.ini,
        aplica valores predeterminados si no existen, y muestra la ventana maximizada
        si así se configuró previamente.
        """
        default_width, default_height = DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
        self.setMinimumSize(default_width, default_height)
        width = self.settings.value("window/width", default_width, int)
        height = self.settings.value("window/height", default_height, int)
        pos_x = self.settings.value("window/pos_x", 100, int)
        pos_y = self.settings.value("window/pos_y", 100, int)
        is_maximized = self.settings.value("window/maximized", False, bool)
        self.resize(max(width, default_width), max(height, default_height))
        self.move(pos_x, pos_y)
        # Mostrar la ventana se difiere hasta después de la inicialización completa en __main__
        self.save_window_settings()
        print(f"Window geometry configured: {width}x{height} at ({pos_x}, {pos_y})")

    def setup_system_locale(self):
        """Imprime información sobre el locale actual del sistema.
        
        Muestra el locale detectado para propósitos de depuración.
        La configuración real de UTF-8 ya se realizó al inicio del módulo.
        """
        # Usa el locale ya configurado al inicio
        try:
            current_locale = os.environ.get('LANG', 'en_US.UTF-8').split('.')[0]
            print(f"System locale confirmed: {current_locale}")
        except Exception as e:
            print(f"Error viewing system locale: {e}")

    def setup_system_tray(self):
        """Configura el icono de bandeja del sistema (system tray).
        
        Verifica la disponibilidad del system tray y configura el icono,
        el menú contextual y las conexiones de activación.
        """
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
        """Crea el menú contextual para el icono de bandeja del sistema."""
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
        """Maneja la activación del icono de bandeja.
        
        Args:
            reason: Motivo de la activación (clic, doble clic, etc.).
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def show_window(self):
        """Muestra y activa la ventana principal de la aplicación."""
        self.show()
        self.raise_()
        self.activateWindow()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()

    def minimize_to_tray(self):
        """Minimiza la aplicación al icono de bandeja del sistema.
        
        Oculta la ventana principal y muestra el icono de bandeja,
        mostrando un mensaje informativo la primera vez que se minimiza.
        """
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
        """Guarda los ajustes y cierra todo limpiamente.
        
        Detiene los timers, oculta componentes de UI, guarda el estado
        de la ventana y cierra la aplicación.
        """
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
        """Guarda la configuración de geometría de la ventana en settings.
        
        Almacena el tamaño y posición de la ventana, pero solo si no está
        maximizada (para preservar las dimensiones reales de la ventana).
        """
        if not self.isMaximized():
            self.settings.setValue("window/width", self.width())
            self.settings.setValue("window/height", self.height())
            self.settings.setValue("window/pos_x", self.x())
            self.settings.setValue("window/pos_y", self.y())
        self.settings.setValue("window/maximized", self.isMaximized())
        self.settings.sync()
        print("Window settings saved.")

    def download(self, download):
        """Maneja la descarga de archivos desde WhatsApp Web.
        
        Muestra un diálogo de guardado de archivos nativo para que el usuario
        elija dónde guardar el archivo descargado.
        
        Args:
            download (QWebEngineDownloadRequest): Solicitud de descarga.
        """
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
        """Crea una notificación del sistema a través de DBus.
        
        Muestra una notificación nativa con título, mensaje e icono
        personalizados según las preferencias del usuario.
        
        Args:
            notification: Objeto de notificación de WebEngine.
            source_webview: Vista web de origen de la notificación.
        """
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
        """Guarda la imagen de contacto en carpeta temporal para notificaciones.
        
        Procesa la imagen de contacto de WhatsApp, la redondea y la guarda
        en un archivo temporal para usarla como icono de notificación.
        
        Args:
            qin (QImage): Imagen de contacto a procesar.
        
        Returns:
            str: Ruta al archivo de imagen guardada o icono fallback.
        """
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
        """Maneja el evento de cierre de ventana: minimizar a bandeja o salir.
        
        Si la configuración lo permite, minimiza a la bandeja del sistema
        en lugar de cerrar completamente la aplicación.
        
        Args:
            event: Evento de cierre de ventana.
        """

        if self.force_quit:
            event.accept()
            return

        if self.settings.value("general/minimize_on_close", True, bool) and hasattr(self, 'tray_icon') and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.minimize_to_tray()
        else:
            self.quit_application()

    def resizeEvent(self, event):
        """Maneja el evento de redimensionamiento de ventana.
        
        Guarda las nuevas dimensiones de la ventana si no está maximizada.
        
        Args:
            event: Evento de redimensionamiento.
        """
        super().resizeEvent(event)
        if not self.isMaximized():
            self.settings.setValue("window/width", self.width())
            self.settings.setValue("window/height", self.height())

    def moveEvent(self, event):
        """Maneja el evento de movimiento de ventana.
        
        Guarda la nueva posición de la ventana si no está maximizada.
        
        Args:
            event: Evento de movimiento.
        """
        super().moveEvent(event)
        if not self.isMaximized():
            self.settings.setValue("window/pos_x", self.x())
            self.settings.setValue("window/pos_y", self.y())

    def toggle_autostart(self, state):
        """Habilita o deshabilita el inicio automático de la aplicación al iniciar sesión.
        
        Args:
            state (bool): True para habilitar el autostart, False para deshabilitarlo.
        
        Crea o elimina un archivo .desktop en ~/.config/autostart/ para controlar
        si la aplicación se inicia automáticamente con la sesión del usuario.
        """
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file_name = "wams.desktop"
        autostart_path = os.path.join(autostart_dir, desktop_file_name)
        
        # Calcular la ruta del script actual para encontrar archivos .desktop
        current_script_path = os.path.dirname(os.path.abspath(__file__))

        if state:
            try:
                if not os.path.exists(autostart_dir):
                    os.makedirs(autostart_dir)

                # Candidatos de origen (orden de prioridad)
                src_paths = [
                    "/usr/share/applications/wams.desktop",
                    os.path.join(current_script_path, "wams.desktop"),
                    os.path.join(current_script_path, "main", "wams.desktop")
                ]

                src_file = None
                for path in src_paths:
                    if os.path.exists(path):
                        src_file = path
                        break

                if src_file:
                    shutil.copy2(src_file, autostart_path)
                    # Asegurar que tiene permisos correctos
                    os.chmod(autostart_path, 0o755)
                    print(f"Autostart enabled: {src_file} -> {autostart_path}")
                else:
                    # Fallback: crear archivo .desktop manualmente si no se encuentra
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

    def process_url(self, url):
        """Procesa una URL entrante y la carga en la sesión activa."""
        self.show_window()
        
        if not url:
            return
            
        web_url = ""
        if url.startswith("whatsapp://"):
            # Transformar whatsapp:// a https://web.whatsapp.com/
            web_url = url.replace("whatsapp://", "https://web.whatsapp.com/", 1)
        elif url.startswith("https://wa.me/") or url.startswith("http://wa.me/"):
            phone = url.split("wa.me/")[1]
            web_url = f"https://web.whatsapp.com/send/?phone={phone}"
        elif "api.whatsapp.com/send" in url:
            web_url = url.replace("api.whatsapp.com/send", "web.whatsapp.com/send", 1)
        else:
            return
            
        target_index = self.tabs.currentIndex()
        if target_index >= 0:
            webview = self.tabs.widget(target_index)
            if webview:
                webview.load(QUrl(web_url))



def main():
    """Función principal de entrada de la aplicación.
    
    Inicializa la aplicación Qt, configura nombres y parámetros,
    crea la ventana principal y ejecuta el bucle de eventos.
    """
    app = QApplication(sys.argv)

    # Establecer nombres de aplicación para evitar que "main.py" o "python"
    # aparezcan en las barras de tareas de Wayland
    app.setApplicationName("WAms")
    app.setApplicationDisplayName("WhatsApp MultiSession")
    app.setDesktopFileName("wams.desktop")

    app.setQuitOnLastWindowClosed(False)

    system_locale = QLocale.system()
    QLocale.setDefault(system_locale)

    # Implementación de instancia única con D-Bus
    dbus_conn = QDBusConnection.sessionBus()
    SERVICE_NAME = "org.wams.SingleInstance"

    if not dbus_conn.registerService(SERVICE_NAME):
        # Ya hay una instancia en ejecución, le pasamos los argumentos y terminamos
        url_to_open = ""
        if len(sys.argv) > 1:
            url_to_open = sys.argv[1]
            
        msg = QDBusMessage.createMethodCall(SERVICE_NAME, "/", "", "handle_url")
        msg << url_to_open
        dbus_conn.call(msg)
        
        sys.exit(0)
        
    dbus_handler = DBusHandler()
    dbus_conn.registerObject("/", dbus_handler, QDBusConnection.RegisterOption.ExportScriptableSlots)

    window = MainWindow()
    window.setWindowTitle("WhatsApp MultiSession")
    
    dbus_handler.url_received.connect(window.process_url)
    
    # Prevenimos que el manejador sea destruido guardando una referencia
    app.dbus_handler = dbus_handler

    # Procesar la URL inicial si la hay, usando un timer para asegurar que la UI esté lista
    if len(sys.argv) > 1:
        QTimer.singleShot(500, lambda: window.process_url(sys.argv[1]))

    if window.settings.value("window/maximized", False, bool):
        window.showMaximized()
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
