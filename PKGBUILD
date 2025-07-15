pkgname=wams
pkgver=0.1
pkgrel=1
pkgdesc="WhatsApp MultiSession: múltiples sesiones independientes de WhatsApp Web"
arch=('any')
url="https://github.com/jhandervelbux/wams"
license=('GPL3')
depends=('python' 'python-pyqt6' 'python-pyqt6-webengine' 'python-dbus' 'python-dbus.mainloop.glib')
makedepends=('python-setuptools')
source=('main.py'
        'src/get_theme.py'
        'src/i18n.py'
        'src/notification.py'
        'src/web.py'
        'src/wams.png'
        'src/translations/en.json'
        'src/translations/es.json'
        'wams.desktop'
        'README.md')
md5sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  install -Dm755 main.py "$pkgdir/usr/bin/wams"
  sed -i '1i#!/usr/bin/env python' "$pkgdir/usr/bin/wams"  # shebang si no existe

  install -Dm644 wams.desktop "$pkgdir/usr/share/applications/wams.desktop"
  install -Dm644 src/wams.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/wams.png"

  # Archivos de Python
  install -d "$pkgdir/usr/lib/wams"
  install -Dm644 src/get_theme.py "$pkgdir/usr/lib/wams/get_theme.py"
  install -Dm644 src/i18n.py "$pkgdir/usr/lib/wams/i18n.py"
  install -Dm644 src/notification.py "$pkgdir/usr/lib/wams/notification.py"
  install -Dm644 src/web.py "$pkgdir/usr/lib/wams/web.py"

  # Traducciones
  install -d "$pkgdir/usr/lib/wams/translations"
  install -m644 src/translations/*.json "$pkgdir/usr/lib/wams/translations/"
}
