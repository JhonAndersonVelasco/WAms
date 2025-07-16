# WhatsApp MultiSession

A PyQt6 application that allows managing multiple WhatsApp Web sessions simultaneously and independently.

## Features

- **Multiple simultaneous sessions**: Run multiple WhatsApp Web instances at the same time
- **Independent data per session**: Each session has its own data storage
- **System notifications**: Get notifications for new messages
- **System tray minimization**: Minimize to system tray for background operation
- **Download management**: Handle file downloads from WhatsApp Web
- **Intuitive interface**: Easy-to-use tabbed interface
- **Internationalization**: Support for multiple languages

## Requirements

- Python 3.6+
- PyQt6
- python-dbus (for notifications on Linux)

## Installation

1. Install the required dependencies:
```bash
pip install PyQt6 PyQt6-WebEngine
```

2. For Linux users, install python-dbus:
```bash
sudo apt-get install python3-dbus python3-dbus.mainloop.glib  # Ubuntu/Debian
sudo dnf install python3-dbus                                 # Fedora
```

3. Run the application:
```bash
python main.py
```

## Usage

### Main Features

- **Add tab**: Click the "+" button to create a new session
- **Rename tab**: Double-click on the tab name
- **Close tab**: Click the "X" on the tab (confirmation required)
- **Move tabs**: Drag tabs to reorder them

### Features

- Each tab is an independent WhatsApp session
- Data is saved automatically
- Minimizes to system tray
- System notifications enabled

### Shortcuts

- Close window: Minimizes to tray
- Click on tray: Restore window

## Translation

The application supports multiple languages. To add a new language:

1. Create a new JSON file in `src/translations/` with the language code (e.g., `fr.json` for French)
2. Copy the structure from `src/translations/en.json`
3. Translate all the strings
4. Add the language code to the `language_map` in `src/i18n.py`

## Configuration

The application stores its configuration in `~/.WAms/config.ini`. Session data is stored in `~/.WAms/sessions/`.

## License

2025, Jhon Velasco.
GPL-3

## Contact

For questions or support, contact: jhandervelbux@gmail.com