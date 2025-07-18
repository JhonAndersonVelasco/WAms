from PyQt6 import QtDBus

def get_system_theme():
    """Available color schemes:
    - 0: No preference (True)
    - 1: Prefer dark appearance (False)
    - 2: Prefer light appearance (True)
    """
    try:
        name = "org.freedesktop.portal.Desktop"
        path = "/org/freedesktop/portal/desktop"
        interface = "org.freedesktop.portal.Settings"

        smp = QtDBus.QDBusInterface(name, path, interface)
        msg = smp.call("Read", "org.freedesktop.appearance", "color-scheme")
        color_scheme = msg.arguments()[0]
        # print(f'Current color: {color_scheme}')
        return False if (color_scheme == 0) or color_scheme == 2 else True
    except Exception:
        return True