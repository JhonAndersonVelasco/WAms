"""
Módulo de detección de tema del sistema.
Detecta si el sistema prefiere un tema claro u oscuro usando
el portal de escritorio de freedesktop.org a través de QtDBus.
"""
from PyQt6 import QtDBus

def get_system_theme():
    """Detecta el esquema de color preferido del sistema.

    Utiliza el portal de configuración de escritorio de freedesktop.org
    para determinar si el sistema prefiere un tema claro u oscuro.

    Devuelve:
        bool: True si se prefiere el tema oscuro, False para claro.

    Esquemas disponibles:
        - 0: Sin preferencia (se interpreta como claro)
        - 1: Preferir apariencia oscura
        - 2: Preferir apariencia clara
    """
    try:
        name = "org.freedesktop.portal.Desktop"
        path = "/org/freedesktop/portal/desktop"
        interface = "org.freedesktop.portal.Settings"

        smp = QtDBus.QDBusInterface(name, path, interface)
        msg = smp.call("Read", "org.freedesktop.appearance", "color-scheme")
        color_scheme = msg.arguments()[0]
        # print(f'Current color: {color_scheme}')
        # Retorna True (oscuro) solo si color_scheme es 1, de lo contrario False (claro)
        return color_scheme == 1
    except Exception:
        # Si falla la detección, asumir tema oscuro por defecto
        return True