import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl, QLocale, QTimer, Qt, QSettings, QEvent
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtGui import QDesktopServices

import modules.get_theme as get_theme

class WhatsApp(QWebEnginePage):

    link_url = ""

    def __init__(self, *args, **kwargs):
        QWebEnginePage.__init__(self, *args, **kwargs)
        QApplication.instance().installEventFilter(self)
        self.featurePermissionRequested.connect(self.permission)
        self.linkHovered.connect(self.link_hovered)
        self.loadFinished.connect(self.load_finished)
        self.destroyed.connect(self.cleanup)

        # Setup application directory for settings
        self.setup_app_directory()

        # Set system language
        self.system_language = 'en' # Default fallback
        self.setup_system_language()

        # Mantener página activa
        self.keep_alive_timer = QTimer(self)
        self.keep_alive_timer.timeout.connect(self.keep_connection_alive)
        self.keep_alive_timer.start(45000)  # 45 segundos

    def cleanup(self):
        """Ensure global event filters are removed"""
        try:
            QApplication.instance().removeEventFilter(self)
        except:
            pass

    def setup_app_directory(self):
        """Setup application directory"""
        home_dir = os.path.expanduser("~")
        self.app_dir = os.path.join(home_dir, ".WAms")

        # Create directory if it doesn't exist
        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)

    def setup_system_language(self):
        """Setup system language for WhatsApp Web"""
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
        if flag or not flag:
            # JavaScript to configure language and other functions
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

            # Use settings from specific directory
            settings = QSettings(os.path.join(self.app_dir, "config.ini"), QSettings.Format.IniFormat)
            theme_mode = settings.value("system/theme", "auto", str)
            if theme_mode == "auto":
                self.setTheme(get_theme.get_system_theme())
            elif theme_mode == "light":
                self.setTheme(False)
            else:
                self.setTheme(True)

    def setTheme(self, isNight_mode):
        if isNight_mode == False:
            self.runJavaScript("document.body.classList.remove('dark')")
        else:
            self.runJavaScript("document.body.classList.add('dark')")

    def link_hovered(self, url):
        self.link_url = url

    def permission(self, frame, feature):
        # Automatically grant permissions for calls and media
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
            # For other features, could be more restrictive, but we keep it open for now
            self.setFeaturePermission(
                frame, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if (
                    self.link_url != ""
                    and self.link_url != "https://web.whatsapp.com/"
                    and not "faq.whatsapp.com/web/download-and-installation/how-to-log-in-or-out"
                    in self.link_url
                ):
                    # Intercept whatsapp:// protocol and api.whatsapp.com links
                    if self.link_url.startswith("whatsapp://"):
                        new_url = self.link_url.replace("whatsapp://", "https://web.whatsapp.com/")
                        self.load(QUrl(new_url))
                        return True
                    elif "api.whatsapp.com/send" in self.link_url:
                        new_url = self.link_url.replace("https://api.whatsapp.com/", "https://web.whatsapp.com/")
                        new_url = new_url.replace("http://api.whatsapp.com/", "https://web.whatsapp.com/")
                        self.load(QUrl(new_url))
                        return True
                        
                    QDesktopServices.openUrl(QUrl(self.link_url))
                    return True
        return False
    
    def keep_connection_alive(self):
        """Mantiene la conexión WebSocket de WhatsApp activa"""
        self.runJavaScript("""
            if (window.Store && window.Store.State) {
                console.log('Keep-alive ping');
            }
        """)