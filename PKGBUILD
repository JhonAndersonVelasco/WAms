pkgname=wams
pkgver=0.1
pkgrel=1
pkgdesc="WhatsApp MultiSession: múltiples sesiones de WhatsApp Web independientes"
arch=('any')
url="https://github.com/jhandervelbux/wams"
license=('GPL3')
depends=('python' 'python-pyqt6' 'python-pyqt6-webengine' 'python-dbus')
source=(
  'main/main.py'
  'main/modules/get_theme.py'
  'main/modules/i18n.py'
  'main/modules/notification.py'
  'main/modules/web.py'
  'main/modules/wams.png'
  'main/modules/translations/en.json'
  'main/modules/translations/es.json'
  'main/wams.desktop'
  'main/README.md'
)
md5sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  # Crear directorios necesarios
  install -d "$pkgdir/usr/lib/wams"
  install -d "$pkgdir/usr/lib/wams/modules"
  install -d "$pkgdir/usr/lib/wams/modules/translations"

  # Instalar el script principal
  install -Dm755 "$srcdir/main/main.py" "$pkgdir/usr/lib/wams/main.py"

  # Instalar módulos
  install -m644 "$srcdir/main/modules/get_theme.py" "$pkgdir/usr/lib/wams/modules/"
  install -m644 "$srcdir/main/modules/i18n.py" "$pkgdir/usr/lib/wams/modules/"
  install -m644 "$srcdir/main/modules/notification.py" "$pkgdir/usr/lib/wams/modules/"
  install -m644 "$srcdir/main/modules/web.py" "$pkgdir/usr/lib/wams/modules/"
  install -m644 "$srcdir/main/modules/wams.png" "$pkgdir/usr/lib/wams/modules/"

  # Instalar traducciones
  install -m644 "$srcdir/main/modules/translations/en.json" "$pkgdir/usr/lib/wams/modules/translations/"
  install -m644 "$srcdir/main/modules/translations/es.json" "$pkgdir/usr/lib/wams/modules/translations/"

  # Crear script ejecutable en /usr/bin
  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/wams" << 'EOF'
#!/usr/bin/env python
import sys
import os
sys.path.insert(0, '/usr/lib/wams')
os.chdir('/usr/lib/wams')
exec(open('/usr/lib/wams/main.py').read())
EOF
  chmod +x "$pkgdir/usr/bin/wams"

  # Instalar icono
  install -Dm644 "$srcdir/main/modules/wams.png" "$pkgdir/usr/share/icons/hicolor/256x256/apps/wams.png"

  # Instalar archivo .desktop
  install -Dm644 "$srcdir/main/wams.desktop" "$pkgdir/usr/share/applications/wams.desktop"

  # Instalar documentación
  install -Dm644 "$srcdir/main/README.md" "$pkgdir/usr/share/doc/wams/README.md"
}