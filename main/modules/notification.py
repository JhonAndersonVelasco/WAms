"""
Módulo de notificaciones - Integración con DBus para notificaciones del sistema.
Proporciona una interfaz para mostrar notificaciones nativas de escritorio
usando el estándar freedesktop.org notifications.
"""
import dbus
from collections import OrderedDict
from modules.i18n import tr

DBusGMainLoop = None
try:
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    print(
        "Could not import DBusGMainLoop, is package 'python-dbus.mainloop.glib' installed?"
    )

APP_NAME = ""
DBUS_IFACE = None
NOTIFICATIONS = {}

class Urgency:
    """Niveles de urgencia para notificaciones freedesktop.org"""
    LOW, NORMAL, CRITICAL = range(3)

class UninitializedError(RuntimeError):
    """Error que se lanza si intentas mostrar una notificación antes de inicializar"""
    pass

def init(app_name):
    """Inicializa la conexión con DBus para el sistema de notificaciones.

    Configura la interfaz DBus para comunicarse con el servidor de notificaciones
    del sistema y conecta las señales necesarias para manejar acciones y cierres
    de notificaciones.

    Args:
        app_name (str): Nombre de la aplicación que se mostrará en las notificaciones.
    """
    global APP_NAME, DBUS_IFACE
    APP_NAME = app_name

    name = "org.freedesktop.Notifications"
    path = "/org/freedesktop/Notifications"
    interface = "org.freedesktop.Notifications"

    mainloop = None
    if DBusGMainLoop is not None:
        mainloop = DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus(mainloop)
    proxy = bus.get_object(name, path)
    DBUS_IFACE = dbus.Interface(proxy, interface)

    if mainloop is not None:
        # Hay un mainloop disponible, conectar callbacks
        DBUS_IFACE.connect_to_signal("ActionInvoked", _onActionInvoked)
        DBUS_IFACE.connect_to_signal("NotificationClosed", _onNotificationClosed)

def _onActionInvoked(nid, action):
    """Se llama cuando se hace clic en una acción de la notificación.

    Args:
        nid (int): ID de la notificación que activó la acción.
        action (str): Identificador de la acción activada.
    """
    nid, action = int(nid), str(action)
    try:
        notification = NOTIFICATIONS[nid]
    except KeyError:
        # La notificación fue creada por otro programa
        return
    notification._onActionInvoked(action)

def _onNotificationClosed(nid, reason):
    """Se llama cuando la notificación se cierra.

    Args:
        nid (int): ID de la notificación que se cerró.
        reason (int): Motivo del cierre (expirado, descartado por usuario, etc.).
    """
    nid, reason = int(nid), int(reason)
    try:
        notification = NOTIFICATIONS[nid]
    except KeyError:
        # La notificación fue creada por otro programa
        return
    notification._onNotificationClosed(notification)
    del NOTIFICATIONS[nid]

class Notification(object):
    """Clase que representa una notificación del sistema.

    Proporciona una interfaz para crear, mostrar y gestionar notificaciones
    de escritorio usando el estándar freedesktop.org a través de DBus.
    """

    id = 0
    timeout = -1
    _onNotificationClosed = lambda *args: None

    def __init__(self, title, body="", icon="", timeout=-1):
        """Inicializa un nuevo objeto de notificación.

        Args:
            title (str): El título de la notificación.
            body (str, opcional): El texto del cuerpo de la notificación.
            icon (str, opcional): La ruta del icono a mostrar con la notificación.
            timeout (int, opcional): El tiempo en ms antes de que la notificación se oculte.
                                     -1 para predeterminado, 0 para nunca.
        """

        self.title = title  # título de la notificación
        self.body = body  # el texto del cuerpo de la notificación
        self.icon = icon  # la ruta del icono a mostrar
        self.timeout = timeout  # tiempo en ms antes de que la notificación desaparezca
        self.hints = {}  # dict de varios hints de visualización
        self.actions = OrderedDict()  # nombres de acciones y sus callbacks
        self.data = {}  # datos arbitrarios del usuario

    def show(self):
        """Muestra la notificación en el sistema.

        Raises:
            UninitializedError: Si no se llamó a Notification.init() primero.

        Returns:
            bool: True si la notificación se mostró exitosamente.
        """
        if DBUS_IFACE is None:
            raise UninitializedError(
                "You must call 'Notification.init()' before 'Notification.show()'"
            )

        nid = DBUS_IFACE.Notify(
            tr("WhatsApp MultiSession"),
            self.id,
            self.icon,
            self.title,
            self.body,
            self._makeActionsList(),
            self.hints,
            self.timeout,
        )

        self.id = int(nid)

        NOTIFICATIONS[self.id] = self
        return True

    def close(self):
        """Solicita al servidor de notificaciones que cierre la notificación."""
        if self.id != 0:
            DBUS_IFACE.CloseNotification(self.id)

    def onClosed(self, callback):
        """Establece el callback que se llama cuando la notificación se cierra.

        Args:
            callback: Función que se ejecutará al cerrar la notificación.
        """
        self._onNotificationClosed = callback

    def setUrgency(self, value):
        """Establece el nivel de urgencia de la notificación freedesktop.org.

        Args:
            value (int): Nivel de urgencia (LOW, NORMAL o CRITICAL).

        Raises:
            ValueError: Si el nivel de urgencia no es válido.
        """
        if value not in range(3):
            raise ValueError("Unknown urgency level '%s' specified" % value)
        self.hints["urgency"] = dbus.Byte(value)

    def setSoundFile(self, sound_file):
        """Establece un archivo de sonido para reproducir cuando se muestra la notificación.

        Args:
            sound_file (str): Ruta al archivo de sonido.
        """
        self.hints["sound-file"] = sound_file

    def setSoundName(self, sound_name):
        """Establece un nombre de sonido freedesktop.org para reproducir.

        Args:
            sound_name (str): Nombre del sonido (ej: "message-new-instant").
        """
        self.hints["sound-name"] = sound_name

    def setIconPath(self, icon_path):
        """Establece la URI del icono a mostrar en la notificación.

        Args:
            icon_path (str): Ruta al archivo de icono.
        """
        self.hints["image-path"] = "file://" + icon_path

    def setQIcon(self, q_icon):
        """Establece un icono Qt para la notificación (no implementado).

        Args:
            q_icon: Objeto QIcon de Qt (actualmente no soportado).

        Raises:
            NotImplementedError: Este método aún no está implementado.
        """
        # FIXME: Esto sería conveniente pero puede no ser posible con DBus
        raise NotImplementedError("setQIcon is not implemented")

    def setLocation(self, x_pos, y_pos):
        """Establece la ubicación donde se mostrará la notificación.

        Args:
            x_pos (int): Coordenada X de la notificación.
            y_pos (int): Coordenada Y de la notificación.
        """
        self.hints["x"] = int(x_pos)
        self.hints["y"] = int(y_pos)

    def setCategory(self, category):
        """Establece la categoría de la notificación freedesktop.org.

        Args:
            category (str): Categoría de la notificación (ej: "im.received").
        """
        self.hints["category"] = category

    def setTimeout(self, timeout):
        """Establece la duración de visualización en milisegundos.

        Args:
            timeout (int): Tiempo en milisegundos, -1 para predeterminado.

        Raises:
            TypeError: Si el timeout no es un entero.
        """
        if not isinstance(timeout, int):
            raise TypeError("Timeout value '%s' was not int" % timeout)
        self.timeout = timeout

    def setHint(self, key, value):
        """Establece uno de los otros hints disponibles.

        Args:
            key (str): Nombre del hint.
            value: Valor del hint.
        """
        self.hints[key] = value

    def addAction(self, action, label, callback, user_data=None):
        """Agrega una acción a la notificación.

        Args:
            action (str): Identificador de la acción (clave de ordenación).
            label (str): Texto a mostrar en el botón de acción.
            callback (método): Método que se ejecutará cuando se active la acción.
            user_data (cualquiera, opcional): Datos de usuario para pasar al callback.
        """
        self.actions[action] = (label, callback, user_data)

    def _makeActionsList(self):
        """Crea la lista de acciones para enviar por DBus.

        Returns:
            list: Lista alternada de [acción, etiqueta, acción, etiqueta, ...].
        """
        arr = []
        for action, (label, callback, user_data) in self.actions.items():
            arr.append(action)
            arr.append(label)
        return arr

    def _onActionInvoked(self, action):
        """Se llama cuando el usuario activa una acción de la notificación.

        Args:
            action (str): Identificador de la acción activada.
        """
        try:
            label, callback, user_data = self.actions[action]
        except KeyError:
            return

        if user_data is None:
            callback(self, action)
        else:
            callback(self, action, user_data)