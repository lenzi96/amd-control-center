# Maintainer: Julian
pkgname=amd-control-center-git
pkgver=1.0.0
pkgrel=1
pkgdesc="AMD Radeon Software Adrenalin Edition for Linux"
arch=('any')
url="https://github.com/amd/radeon-software-linux"
license=('GPL3')
depends=('python' 'python-pyqt6')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=()

package() {
  install -d "$pkgdir/usr/share/amd-control-center"
  cp -r "$startdir"/* "$pkgdir/usr/share/amd-control-center/"
  
  install -d "$pkgdir/usr/bin"
  ln -sf "/usr/share/amd-control-center/amd-control-center" "$pkgdir/usr/bin/amd-control-center"
  
  install -Dm644 "$startdir/amd-control-center.desktop" "$pkgdir/usr/share/applications/amd-control-center.desktop"
  install -Dm644 "$startdir/amd_control_center/resources/app_icon.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/amd-control-center.svg"
}
