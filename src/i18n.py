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
        """Load translations from JSON files"""
        try:
            # Get system language
            system_locale = QLocale.system()
            lang_code = system_locale.name().split('_')[0]

            # Set current language (default to English)
            self.current_language = lang_code if lang_code in ['en', 'es', 'pt', 'fr', 'de'] else 'en'

            # Load translation files
            translations_dir = os.path.join(os.path.dirname(__file__), 'translations')
            if not os.path.exists(translations_dir):
                os.makedirs(translations_dir)

            # Try to load the translation file
            translation_file = os.path.join(translations_dir, f'{self.current_language}.json')
            if os.path.exists(translation_file):
                with open(translation_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            else:
                # Create default English translations
                self.create_default_translations()

        except Exception as e:
            print(f"Error loading translations: {e}")
            self.current_language = 'en'
            self.translations = {}

    def create_default_translations(self):
        """Create default English translations"""
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
        <h3>🚀 WhatsApp MultiSession Quick Guide</h3>

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
            <p>Application that allows managing multiple WhatsApp Web sessions<br>
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
        """Translate text to current language"""
        return self.translations.get(text, text)

    def set_language(self, language_code):
        """Set the current language"""
        self.current_language = language_code
        self.load_translations()

# Global translator instance
_translator = Translator()

def tr(text):
    """Global translation function"""
    return _translator.tr(text)

def set_language(language_code):
    """Set global language"""
    _translator.set_language(language_code)