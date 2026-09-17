# Maintainer: Julian
pkgname=amd-control-center-git
pkgver=1.1.0
pkgrel=1
pkgdesc="AMD Software: Adrenalin Edition for Linux (Radeon & Ryzen Master)"
arch=('any')
url="https://github.com/lenzi96/amd-control-center"
license=('GPL3')
depends=('python' 'python-pyqt6')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=()

package() {
  cd "$srcdir/.."
  install -d "$pkgdir/usr/share/amd-control-center"
  install -d "$pkgdir/usr/bin"
  install -d "$pkgdir/usr/share/applications"
  install -d "$pkgdir/usr/share/icons/hicolor/scalable/apps"

  cp -r amd_control_center "$pkgdir/usr/share/amd-control-center/"
  cp main.py "$pkgdir/usr/share/amd-control-center/"

  install -Dm755 amd-control-center "$pkgdir/usr/bin/amd-control-center"
  install -Dm644 amd-control-center.desktop "$pkgdir/usr/share/applications/amd-control-center.desktop"
  install -Dm644 amd_control_center/resources/app_icon.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/amd-control-center.svg"

  for sz in 16 24 32 48 64 128 256 512; do
    if [ -f "amd_control_center/resources/app_icon_${sz}.png" ]; then
      install -Dm644 "amd_control_center/resources/app_icon_${sz}.png" \
        "$pkgdir/usr/share/icons/hicolor/${sz}x${sz}/apps/amd-control-center.png"
    fi
  done
}
