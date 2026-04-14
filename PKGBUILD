pkgname=wams
pkgver=0.1
pkgrel=7
pkgdesc="WhatsApp MultiSession: múltiples sesiones de WhatsApp Web independientes"
arch=('any')
url="https://github.com/JhonAndersonVelasco/WAms"
license=('GPL3')
depends=('python' 'python-pyqt6' 'python-pyqt6-webengine' 'python-dbus' 'pciutils' 'mesa-utils' 'xdg-user-dirs')
install=main/wams.install

package() {
  # Crear directorios necesarios
  install -d "$pkgdir/opt/wams"
  install -d "$pkgdir/opt/wams/modules"
  install -d "$pkgdir/opt/wams/modules/translations"

  # Instalar el script principal
  install -Dm755 "$startdir/main/main.py" "$pkgdir/opt/wams/main.py"

  # Instalar módulos
  install -m644 "$startdir/main/modules/get_theme.py" "$pkgdir/opt/wams/modules/"
  install -m644 "$startdir/main/modules/i18n.py" "$pkgdir/opt/wams/modules/"
  install -m644 "$startdir/main/modules/notification.py" "$pkgdir/opt/wams/modules/"
  install -m644 "$startdir/main/modules/web.py" "$pkgdir/opt/wams/modules/"
  install -m644 "$startdir/main/modules/wams.png" "$pkgdir/opt/wams/modules/"

  # Instalar traducciones
  install -m644 "$startdir/main/modules/translations/en.json" "$pkgdir/opt/wams/modules/translations/"
  install -m644 "$startdir/main/modules/translations/es.json" "$pkgdir/opt/wams/modules/translations/"

  # Crear script ejecutable en /usr/bin
  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/wams" << 'EOF'
#!/bin/bash
exec /usr/bin/python /opt/wams/main.py "$@"
EOF
  chmod +x "$pkgdir/usr/bin/wams"

  # Instalar icono
  install -Dm644 "$startdir/main/modules/wams.png" "$pkgdir/usr/share/icons/hicolor/256x256/apps/wams.png"

  # Instalar archivo .desktop
  install -Dm644 "$startdir/main/wams.desktop" "$pkgdir/usr/share/applications/wams.desktop"

  # Instalar hook de post-instalación (actualiza base de datos MIME e iconos)
  install -Dm644 "$startdir/main/wams.install" "$pkgdir/usr/share/wams/wams.install"
}
