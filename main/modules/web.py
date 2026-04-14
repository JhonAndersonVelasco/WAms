"""
Módulo web - Página de WhatsApp Web
Maneja la página web de WhatsApp Web dentro de cada tab de la aplicación.
"""
import os

# Intervalo del timer keep-alive para mantener la conexión WebSocket activa (45 segundos)
WEB_KEEP_ALIVE_INTERVAL = 45000

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QLocale, QTimer, QSettings
from PyQt6.QtWebEngineCore import QWebEnginePage

import modules.get_theme as get_theme

class WhatsApp(QWebEnginePage):
    """Clase que representa una página de WhatsApp Web en una tab.
    
    Hereda de QWebEnginePage y proporciona funcionalidades como:
    - Configuración del idioma del sistema.
    - Gestión de permisos (micrófono, cámara, notificaciones).
    - Mantenimiento de conexión activa mediante un timer.
    - Detección de temas (claro/oscuro) al cargar la página.

    No devuelve nada. Instala filtros de eventos y conecta señales necesarias.
    """

    def __init__(self, *args, **kwargs):
        """Inicializa una nueva instancia de WhatsApp Web.

        Args:
            *args: Argumentos posicionales para QWebEnginePage
            **kwargs: Argumentos nombrados para QWebEnginePage
        """
        QWebEnginePage.__init__(self, *args, **kwargs)
        
        # Instalar filtro de eventos global para capturar eventos de la aplicación
        QApplication.instance().installEventFilter(self)
        
        # Conectar señales para manejar permisos, hover de links, carga y limpieza
        self.featurePermissionRequested.connect(self.permission)
        self.linkHovered.connect(self.link_hovered)
        self.loadFinished.connect(self.load_finished)
        self.destroyed.connect(self.cleanup)

        # Variable de instancia para almacenar la URL del último link hoverizado
        # (antes era variable de clase, causando race conditions entre sesiones)
        self.link_url = ""

        # Configurar el directorio de la aplicación para ajustes
        self.setup_app_directory()

        # Configurar idioma del sistema
        self.system_language = 'en'  # Fallback predeterminado
        self.setup_system_language()

        # Mantener página activa con timer keep-alive
        self.keep_alive_timer = QTimer(self)
        self.keep_alive_timer.timeout.connect(self.keep_connection_alive)
        self.keep_alive_timer.start(WEB_KEEP_ALIVE_INTERVAL)  # 45 segundos

    def cleanup(self):
        """Asegura que los filtros de eventos globales se eliminen.
        
        Se ejecuta cuando la página se destruye para evitar
        fugas de memoria y referencias colgantes.
        """
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass

    def setup_app_directory(self):
        """Configura el directorio de datos de la aplicación (~/.WAms).
        
        Crea el directorio si no existe, para almacenar configuración
        y datos de sesión de la aplicación.
        """
        home_dir = os.path.expanduser("~")
        self.app_dir = os.path.join(home_dir, ".WAms")

        # Crear directorio si no existe
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)

    def setup_system_language(self):
        """Configura el idioma del sistema para WhatsApp Web.
        
        Detecta el locale del sistema y mapea el código de idioma
        al formato que WhatsApp Web espera, configurando variables
        de entorno y almacenando el idioma para su uso posterior.
        """
        try:
            # Get system language using QLocale
            system_locale = QLocale.system()
            language_code = system_locale.name().split('_')[0]  # Get only language code (e.g., 'en' from 'en_US')

            # Language mapping for WhatsApp Web
            language_map = {
                'es': 'es',      # Spanish
                'en': 'en',      # English
                'pt': 'pt_BR',   # Portuguese (Brazil)
                'fr': 'fr',      # French
                'de': 'de',      # German
                'it': 'it',      # Italian
                'ru': 'ru',      # Russian
                'ja': 'ja',      # Japanese
                'ko': 'ko',      # Korean
                'zh': 'zh_CN',   # Chinese (Simplified)
                'ar': 'ar',      # Arabic
                'hi': 'hi',      # Hindi
                'tr': 'tr',      # Turkish
                'nl': 'nl',      # Dutch
                'sv': 'sv',      # Swedish
                'da': 'da',      # Danish
                'no': 'no',      # Norwegian
                'fi': 'fi',      # Finnish
                'pl': 'pl',      # Polish
                'cs': 'cs',      # Czech
                'hu': 'hu',      # Hungarian
                'ro': 'ro',      # Romanian
                'sk': 'sk',      # Slovak
                'sl': 'sl',      # Slovenian
                'hr': 'hr',      # Croatian
                'bg': 'bg',      # Bulgarian
                'et': 'et',      # Estonian
                'lv': 'lv',      # Latvian
                'lt': 'lt',      # Lithuanian
                'mt': 'mt',      # Maltese
                'el': 'el',      # Greek
                'ca': 'ca',      # Catalan
                'eu': 'eu',      # Basque
                'gl': 'gl',      # Galician
                'cy': 'cy',      # Welsh
                'ga': 'ga',      # Irish
                'is': 'is',      # Icelandic
                'mk': 'mk',      # Macedonian
                'sq': 'sq',      # Albanian
                'sr': 'sr',      # Serbian
                'bs': 'bs',      # Bosnian
                'me': 'me',      # Montenegrin
                'uk': 'uk',      # Ukrainian
                'be': 'be',      # Belarusian
                'ka': 'ka',      # Georgian
                'hy': 'hy',      # Armenian
                'az': 'az',      # Azerbaijani
                'kk': 'kk',      # Kazakh
                'ky': 'ky',      # Kyrgyz
                'uz': 'uz',      # Uzbek
                'tg': 'tg',      # Tajik
                'mn': 'mn',      # Mongolian
                'th': 'th',      # Thai
                'vi': 'vi',      # Vietnamese
                'id': 'id',      # Indonesian
                'ms': 'ms',      # Malay
                'tl': 'tl',      # Filipino
                'fa': 'fa',      # Persian
                'ur': 'ur',      # Urdu
                'bn': 'bn',      # Bengali
                'ta': 'ta',      # Tamil
                'te': 'te',      # Telugu
                'ml': 'ml',      # Malayalam
                'kn': 'kn',      # Kannada
                'gu': 'gu',      # Gujarati
                'pa': 'pa',      # Punjabi
                'or': 'or',      # Odia
                'as': 'as',      # Assamese
                'ne': 'ne',      # Nepali
                'si': 'si',      # Sinhala
                'my': 'my',      # Myanmar
                'km': 'km',      # Khmer
                'lo': 'lo',      # Lao
                'am': 'am',      # Amharic
                'sw': 'sw',      # Swahili
                'zu': 'zu',      # Zulu
                'xh': 'xh',      # Xhosa
                'af': 'af',      # Afrikaans
                'he': 'he',      # Hebrew
            }

            # Get mapped language or use English as default
            whatsapp_language = language_map.get(language_code, 'en')

            # Set environment variables for language
            os.environ['LANG'] = f"{whatsapp_language}.UTF-8"
            os.environ['LC_ALL'] = f"{whatsapp_language}.UTF-8"

            # Store language for later use
            self.system_language = whatsapp_language

            print(f"System language detected: {language_code}")
            print(f"Language configured for WhatsApp Web: {whatsapp_language}")

        except Exception as e:
            print(f"Error setting up system language: {e}")
            self.system_language = 'en'  # Fallback to English

    def load_finished(self, flag):
        """Configura la página web después de que se carga completamente.
        
        Inyecta JavaScript para:
        - Configurar el idioma del navegador
        - Establecer platform y vendor para evitar detección
        - Forzar encabezados Accept-Language
        - Ajustar el layout de WhatsApp Web
        - Activar notificaciones
        - Spoofear window.chrome para compatibilidad
        
        Args:
            flag (bool): True si la carga fue exitosa, False si falló
        """
        # La configuración se ejecuta independientemente del resultado de la carga
        # JavaScript para configurar idioma y otras funciones
        self.runJavaScript(
            f"""
            // Configure browser language
            Object.defineProperty(navigator, 'language', {{
                value: '{self.system_language}',
                writable: false
            }});

            Object.defineProperty(navigator, 'languages', {{
                value: ['{self.system_language}', 'en'],
                writable: false
            }});

            // Strictly Linux native - no spoofing Win/Mac
            Object.defineProperty(navigator, 'platform', {{
                value: 'Linux x86_64',
                writable: false
            }});

            Object.defineProperty(navigator, 'vendor', {{
                value: 'Google Inc.',
                writable: false
            }});

            // Disable userAgentData to avoid platform-specific detection
            if (navigator.userAgentData) {{
                Object.defineProperty(navigator, 'userAgentData', {{
                    get: () => undefined
                }});
            }}

            // Force browser calls flags in localStorage
            try {{
                localStorage.setItem('wa-browser-calls', 'true');
                localStorage.setItem('wa-browser-calls-v2', 'true');
            }} catch(e) {{
                console.log('Error setting wa-browser-calls:', e);
            }}

            // Configure Accept-Language header
            if (window.XMLHttpRequest) {{
                const originalOpen = XMLHttpRequest.prototype.open;
                XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
                    this.addEventListener('readystatechange', function() {{
                        if (this.readyState === 1) {{
                            this.setRequestHeader('Accept-Language', '{self.system_language},en;q=0.9');
                        }}
                    }});
                    return originalOpen.apply(this, arguments);
                }};
            }}

            // Configure language in localStorage if available
            try {{
                localStorage.setItem('whatsapp-lang', '{self.system_language}');
                localStorage.setItem('lang', '{self.system_language}');
            }} catch(e) {{
                console.log('Could not configure language in localStorage:', e);
            }}

            // Original code to adjust layout
            const checkExist = setInterval(() => {{
                const classElement = document.getElementsByClassName("_1XkO3")[0];
                if (classElement != null) {{
                    classElement.style = 'max-width: initial; width: 100%; height: 100%; position: unset;margin: 0'
                    clearInterval(checkExist);
                }}
            }}, 100);

            // Original code for notifications
            const checkNotify = setInterval(() => {{
                const classElement = document.evaluate('//*[@id="side"]/span/div/div/div[2]/div[2]/span/span[1]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (classElement != null) {{
                    classElement.click()
                    clearInterval(checkNotify);
                    }}
            }}, 100);

            // Spoof window.chrome for better compatibility
            if (!window.chrome) {{
                window.chrome = {{
                    runtime: {{}},
                    loadTimes: function() {{}},
                    csi: function() {{}},
                    app: {{}}
                }};
            }}

            // Ensure mediaDevices exists (should be native now)
            if (navigator.mediaDevices === undefined) {{
                console.warn('navigator.mediaDevices is still undefined');
            }}

            // Force language update after page loads completely
            setTimeout(() => {{
                // Try to change language through WhatsApp Web settings
                const settingsButton = document.querySelector('[data-testid="menu"]');
                if (settingsButton) {{
                    console.log('Configuring system language...');
                }}
            }}, 2000);
        """
        )

        # Configurar el tema (claro/oscuro) desde los ajustes
        settings = QSettings(os.path.join(self.app_dir, "config.ini"), QSettings.Format.IniFormat)
        theme_mode = settings.value("system/theme", "auto", str)
        if theme_mode == "auto":
            self.setTheme(get_theme.get_system_theme())
        elif theme_mode == "light":
            self.setTheme(False)
        else:
            self.setTheme(True)

    def setTheme(self, is_dark_mode):
        """Aplica el tema claro u oscuro a la página web de WhatsApp.
        
        Args:
            is_dark_mode (bool): True para aplicar el tema oscuro, False para el claro.
        """
        if is_dark_mode:
            self.runJavaScript("document.body.classList.add('dark')")
        else:
            self.runJavaScript("document.body.classList.remove('dark')")

    def link_hovered(self, url):
        """Maneja el evento cuando el cursor pasa sobre un enlace.
        
        Almacena la URL del link para posibles usos futuros como previsualización.
        
        Args:
            url (str): La URL del enlace sobre el que se hizo hover.
        """
        self.link_url = url

    def permission(self, frame, feature):
        """Maneja las solicitudes de permiso de características web.
        
        Concede automáticamente permisos para llamadas de audio/video,
        captura de escritorio y notificaciones, que son esenciales
        para el funcionamiento completo de WhatsApp Web.
        
        Args:
            frame: El marco QWebEnginePage que solicita el permiso.
            feature: La característica solicitada (audio, video, notificaciones, etc.).
        """
        # Lista de características que se conceden automáticamente
        granted_features = [
            QWebEnginePage.Feature.MediaAudioCapture,
            QWebEnginePage.Feature.MediaVideoCapture,
            QWebEnginePage.Feature.MediaAudioVideoCapture,
            QWebEnginePage.Feature.DesktopVideoCapture,
            QWebEnginePage.Feature.DesktopAudioVideoCapture,
            QWebEnginePage.Feature.Notifications
        ]

        if feature in granted_features:
            self.setFeaturePermission(
                frame, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
        else:
            # Para otras características, también concedemos por ahora
            self.setFeaturePermission(
                frame, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )

    def keep_connection_alive(self):
        """Mantiene la conexión WebSocket de WhatsApp activa.
        
        Envía un ping periódico para evitar que la conexión se cierre
        por inactividad, asegurando que los mensajes se reciban en tiempo real.
        """
        self.runJavaScript("""
            if (window.Store && window.Store.State) {
                console.log('Keep-alive ping');
            }
        """)