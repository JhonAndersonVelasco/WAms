"""
Internationalization module for WhatsApp MultiSession
Simple translation system for the application
"""
import os
import json
from PyQt6.QtCore import QLocale

class Translator:
    def __init__(self):
        self.current_language = 'en'
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """Carga las traducciones desde archivos JSON.

            Detecta el idioma del sistema e intenta cargar el archivo de traducción
            correspondiente. Si no existe, crea el archivo por defecto en inglés
            y lo guarda para usos futuros.

            No devuelve nada. Imprime mensajes informativos sobre la carga o creación de archivos.
        """
        try:
            # Obtener el idioma del sistema
            system_locale = QLocale.system()
            lang_code = system_locale.name().split('_')[0]

            # Establecer el idioma actual (predeterminado: inglés)
            supported_languages = ['en', 'es', 'pt', 'fr', 'de']
            self.current_language = lang_code if lang_code in supported_languages else 'en'

            # Cargar archivos de traducción
            translations_dir = os.path.join(os.path.dirname(__file__), 'translations')
            if not os.path.exists(translations_dir):
                os.makedirs(translations_dir)

            # Intentar cargar el archivo de traducción
            translation_file = os.path.join(translations_dir, f'{self.current_language}.json')
            if os.path.exists(translation_file):
                with open(translation_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            else:
                # Crear traducciones predeterminadas en inglés y guardarlas
                self.create_default_translations()
                # Guardar el archivo JSON para futuros inicios
                try:
                    default_file = os.path.join(translations_dir, f'{self.current_language}.json')
                    with open(default_file, 'w', encoding='utf-8') as f:
                        json.dump(self.translations, f, ensure_ascii=False, indent=2)
                    print(f"Default translations created and saved: {default_file}")
                except Exception as save_error:
                    print(f"Warning: Could not save default translations: {save_error}")

        except Exception as e:
            print(f"Error loading translations: {e}")
            self.current_language = 'en'
            self.translations = {}

    def create_default_translations(self):
        """Crea las traducciones predeterminadas en inglés y las guarda en un archivo JSON.

            Genera un diccionario con todas las cadenas de texto de la aplicación
            en inglés y lo persiste en el directorio de traducciones para evitar
            recrearlo en cada inicio.
        """
        self.translations = {
            # Application
            "WhatsApp MultiSession": "WhatsApp MultiSession",

            # Buttons and UI
            "Add new tab": "Add new tab",
            "Menu": "Menu",
            "Quick guide": "Quick guide",
            "About": "About",
            "Donate": "Donate",
            "Quit": "Quit",
            "Show": "Show",
            "Exit": "Exit",

            # Sessions
            "Default Session": "Default Session",
            "Session {}": "Session {}",

            # Dialogs
            "Cannot Close": "Cannot Close",
            "Cannot close the last tab. The application needs at least one session.": "Cannot close the last tab. The application needs at least one session.",
            "Confirm Close": "Confirm Close",
            "Are you sure you want to close the tab '{}'? This will permanently delete its session data.": "Are you sure you want to close the tab '{}'? This will permanently delete its session data.",
            "Rename Failed": "Rename Failed",
            "A tab named '{}' already exists.": "A tab named '{}' already exists.",
            "A session folder named '{}' already exists.": "A session folder named '{}' already exists.",
            "Error": "Error",
            "Could not rename the session folder.\\nError: {}": "Could not rename the session folder.\\nError: {}",
            "An unexpected error occurred.\\nError: {}": "An unexpected error occurred.\\nError: {}",
            "Error closing tab: {}": "Error closing tab: {}",

            # System tray
            "Minimized to system tray.": "Minimized to system tray.",

            # Downloads
            "WhatsApp MultiSession - Save file": "WhatsApp MultiSession - Save file",

            # Notifications
            "New message...": "New message...",

            # Menu items
            "📖 Quick guide": "📖 Quick guide",
            "ℹ️ About": "ℹ️ About",
            "💝 Donate": "💝 Donate",
            "❌ Quit": "❌ Quit",
            "📧 Contact developer": "📧 Contact developer",
            "About WhatsApp MultiSession": "About WhatsApp MultiSession",
            "Donations": "Donations",
            "Open donation page": "Open donation page",

            # Quick guide content
            "quick_guide_content": """
        <h3>🚀 WhatsApp MultiSession v0.1 Quick Guide</h3>

        <p><b>Main Features:</b></p>
        <ul>
            <li><b>Add tab:</b> Click the "+" button to create a new session</li>
            <li><b>Rename tab:</b> Double-click on the tab name</li>
            <li><b>Close tab:</b> Click the "X" on the tab (confirmation required)</li>
            <li><b>Move tabs:</b> Drag tabs to reorder them</li>
        </ul>

        <p><b>Features:</b></p>
        <ul>
            <li>Each tab is an independent WhatsApp session</li>
            <li>Data is saved automatically</li>
            <li>Minimizes to system tray</li>
            <li>System notifications enabled</li>
        </ul>

        <p><b>Shortcuts:</b></p>
        <ul>
            <li>Close window: Minimizes to tray</li>
            <li>Click on tray: Restore window</li>
        </ul>
        """,

            # About content
            "about_content": """
        <div style="text-align: center;">
            <h2>📱 WhatsApp MultiSession</h2>
            <p><b>Version:</b> 0.1</p>
            <hr>
            <p><b>Developer:</b> Jhon Velasco</p>
            <p><b>Contact:</b> <a href="mailto:jhandervelbux@gmail.com">jhandervelbux@gmail.com</a></p>
            <hr>
            <p><b>Description:</b></p>
            <p>Application that allows managing multiple WhatsApp Web sessions
            simultaneously and independently.</p>
            <hr>
            <p><b>Main Features:</b></p>
            <ul style="text-align: left;">
                <li>✅ Multiple simultaneous sessions</li>
                <li>✅ Independent data per session</li>
                <li>✅ System notifications</li>
                <li>✅ System tray minimization</li>
                <li>✅ Download management</li>
                <li>✅ Intuitive interface</li>
            </ul>
            <hr>
            <p><small>Developed with PyQt6 and QtWebEngine</small></p>
            <p><small>© 2025 Jhon Velasco. All rights reserved.</small></p>
        </div>
        """,

            # Donate content
            "donate_content": """
        <h3>💝 Support Development</h3>

        <p>If you like WhatsApp MultiSession and want to support its development,
        you can make a donation:</p>

        <p><b>Donation methods:</b></p>
        <ul>
            <li>PayPal: <a href="https://www.paypal.com/donate/?hosted_button_id=FX7FC6R7WJ85W">paypal.com/donate</a></li>
        </ul>

        <p>Any contribution is greatly appreciated! 🙏</p>

        <p><small>You can also support the project by:</small></p>
        <ul>
            <li>⭐ Starring on GitHub</li>
            <li>🐛 Reporting bugs</li>
            <li>💡 Suggesting new features</li>
            <li>📢 Sharing with friends</li>
        </ul>
        """
        }

    def tr(self, text):
        """Traduce un texto al idioma actual.

            Args:
                text (str): Texto a traducir.

            Returns:
                str: Texto traducido o el original si no hay traducción disponible.
        """
        return self.translations.get(text, text)

    def set_language(self, language_code):
        """Cambia el idioma actual y recarga las traducciones.

            Args:
                language_code (str): Código del idioma (ej: 'es', 'en', 'fr').
        """
        self.current_language = language_code
        self.load_translations()

# Instancia global del traductor
_translator = Translator()

def tr(text):
    """Función global de traducción.

        Args:
            text (str): Texto a traducir.

        Returns:
            str: Texto traducido o el original si no hay traducción disponible.
    """
    return _translator.tr(text)

def set_language(language_code):
    """Establece el idioma global de la aplicación.

        Args:
            language_code (str): Código del idioma (ej: 'es', 'en', 'fr').
    """
    _translator.set_language(language_code)