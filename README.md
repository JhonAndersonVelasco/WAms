# WhatsApp MultiSession (WAms)

A native PyQt6 application for Linux that allows managing multiple WhatsApp Web sessions simultaneously and independently.

WAms seamlessly integrates with your desktop environment, providing a clean, tabbed interface to manage personal, work, and other WhatsApp accounts without mixing their data or relying on separate browser profiles. It also acts as a native protocol handler, directly intercepting "wa.me" and "whatsapp://" links from outside the app.

---

## ✨ Features

- **Multiple simultaneous sessions**: Run multiple WhatsApp Web instances at the same time in separate tabs.
- **Independent data per session**: Each session has its own isolated cookies, cache, and local storage.
- **Native Link Handling (New)**: Intercepts and opens `whatsapp://` and `api.whatsapp.com` links natively inside your active WAms tab seamlessly (no browser redirect needed).
- **System notifications**: Native desktop notifications for new messages (via D-Bus).
- **System tray integration**: Minimize to the system tray for discreet background operation.
- **Download management**: Native file dialogs to handle downloads directly from WhatsApp Web to XDG standard directories.
- **Microphone and Camera support**: Full support for WhatsApp audio and video calls.
- **Hardware Acceleration**: Smooth WebGL and 2D Canvas rendering using QtWebEngine.
- **Intuitive interface**: Easy-to-use tabbed interface. Rename tabs, drag them to reorder, or close them safely.
- **Internationalization**: Support for multiple languages globally and per-session.

## 📦 Requirements

Designed specifically with modern Linux environments in mind.

- Python 3.10+ (Tested on 3.10, 3.13, 3.14)
- PyQt6 (`python-pyqt6`)
- PyQt6 WebEngine (`python-pyqt6-webengine`)
- Python D-Bus (`python-dbus`)
- System utilities: `pciutils`, `mesa-utils`, `xdg-user-dirs`

*(Note: Hardware acceleration is optimized for Nvidia GPUs, e.g., GTX 1080 with proprietary drivers and CUDA).*

## 🚀 Installation

### Arch Linux (Recommended)

The easiest way to install WAms on Arch Linux or Arch-based distributions (Manjaro, EndeavourOS) is using the included `PKGBUILD`.
```bash
git clone https://github.com/JhonAndersonVelasco/WAms.git
cd WAms
makepkg -si
```

This will automatically resolve dependencies, install the desktop entry, and register WAms as the handler for `whatsapp://` and `wa.me` links.

### Other Linux Distributions (pip)

For any other distribution, first install the system-level dependencies, then install WAms via `pip`:

**Ubuntu / Debian:**
```bash
sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine python3-dbus pciutils mesa-utils xdg-user-dirs
pip install . --break-system-packages
```

**Fedora:**
```bash
sudo dnf install python3-pyqt6 python3-pyqt6-webengine python3-dbus pciutils mesa-libGL xdg-user-dirs
pip install .
```

**Other distros:**
```bash
# Install PyQt6 and dbus-python via pip if not available in your package manager
pip install PyQt6 PyQt6-WebEngine dbus-python
pip install .
```

After installation, run the app with:
```bash
wams
```

> **Note:** `dbus-python` may require system development headers (`libdbus-1-dev` on Debian/Ubuntu, `dbus-devel` on Fedora) if installed via pip.

## 💻 Usage

### Session Management

- **Add tab**: Click the `+` button in the top right corner to create a new session.
- **Rename tab**: Double-click on the tab name to give it a custom alias (e.g., "Work", "Personal").
- **Close tab**: Click the `X` on the tab. (You will be prompted to confirm, as closing a tab permanently deletes its session data).
- **Move tabs**: Drag tabs horizontally to reorder them.

### General Operation

- **System Tray**: Closing the main window minimizes the app to the system tray. Click the tray icon to restore it, or right-click it for more options.
- **Hamburger Menu (☰)**: Access the quick guide, about page, donation link, and toggle the autostart behavior.
- **Opening Chats**: Clicking any explicit WhatsApp link (`whatsapp://send?phone=...` or `https://wa.me/...`) in your web browser will automatically focus WAms and open that chat in your currently active tab.

## 🌍 Translation

The application supports multiple languages. To add a new language:

1. Create a new JSON file in `main/modules/translations/` with the language code (e.g., `fr.json` for French).
2. Copy the structure from `main/modules/translations/en.json`.
3. Translate all the strings.
4. Add the language code to the `language_map` in `main/modules/i18n.py`.

## ⚙️ Configuration & Data

- **Config File**: The application stores its UI and behavior preferences in `~/.WAms/config.ini`.
- **Session Data**: All independent browser session data (Cookies, LocalStorage, IndexedDB) is securely stored in `~/.WAms/sessions/`.
- **Downloads**: Files downloaded from WhatsApp are routed to your system's default `~/Downloads` folder automatically via `xdg-user-dirs`.

## 📄 License

GPL-3.0 License
© 2025, Jhon Velasco.

## 📬 Contact & Support

For questions, bug reports, or support, please contact: **jhandervelbux@gmail.com**

If you find this project useful, consider supporting the development through the **💝 Donate** option inside the app!
