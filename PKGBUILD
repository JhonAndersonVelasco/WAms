pkgname=wams
pkgver=0.1
pkgrel=1
pkgdesc="WhatsApp MultiSession - Múltiples sesiones independientes de WhatsApp Web"
arch=('any')
url="https://github.com/jhandervelbux/wams"
license=('GPL3')
depends=('python' 'python-pyqt6' 'python-pyqt6-webengine' 'python-dbus' 'python-dbus.mainloop.glib')
makedepends=('python-setuptools')
source=('wams.desktop' 'src/wams.png' 'README.md'
        'main.py' 'src/i18n.py' 'src/web.py' 'src/get_theme.py' 'src/notification.py')
md5sums=('SKIP' 'SKIP' 'SKIP'
         'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  install -d "$pkgdir/usr/bin"
  echo -e '#!/usr/bin/env python\nimport sys\nfrom wams import main\nmain()' > "$pkgdir/usr/bin/wams"
  chmod +x "$pkgdir/usr/bin/wams"

  install -Dm644 wams.desktop "$pkgdir/usr/share/applications/wams.desktop"
  install -Dm644 wams.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/wams.png"

  install -d "$pkgdir/usr/lib/wams"
  cp -r wams/* "$pkgdir/usr/lib/wams"
}
