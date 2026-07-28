#!/bin/bash
# Install selenium-webdriver-at-spi + inputsynth on the DUT.
#
# This script runs INSIDE the VM. It prefers distro packages when available and
# falls back to a pinned source build of KDE/selenium-webdriver-at-spi.
#
# Outputs:
#   Exits 0 on success.
#   Prints "KDE_WEBDRIVER_SKIP=<reason>" and exits 0 when the suite should be
#   skipped rather than run (version skew, unsupported distro, etc.).
#
# The build is pinned to a full git commit SHA; no floating branch refs are used.

set -euo pipefail

# Pinned source ref for selenium-webdriver-at-spi (KDE GitHub mirror).
# Update only together with the runner image and after validating on all target distros.
readonly SELENIUM_AT_SPI_SHA="d45a21e8f1b3591dc921f0be85f1ecd834cbe413"
readonly SELENIUM_AT_SPI_URL="https://github.com/KDE/selenium-webdriver-at-spi.git"

log() { echo "[install-kde-webdriver] $*"; }

# Detect distro family from os-release.
ID=""
ID_LIKE=""
if [[ -r /etc/os-release ]]; then
  source /etc/os-release
fi

distros="${ID} ${ID_LIKE}"

is_distro() {
  [[ " ${distros} " =~ \ $1\  ]]
}

# Version-skew check: require Plasma >= 6.0 or >= 5.27 LTS.
plasma_version=""
if command -v plasmashell >/dev/null 2>&1; then
  plasma_version=$(plasmashell --version 2>/dev/null | head -1 || true)
fi
if [[ -z "${plasma_version}" ]] && command -v rpm >/dev/null 2>&1; then
  plasma_version=$(rpm -q --qf '%{VERSION}' plasma-workspace 2>/dev/null || true)
fi
if [[ -z "${plasma_version}" ]] && command -v dpkg >/dev/null 2>&1; then
  plasma_version=$(dpkg-query -W -f='${Version}' plasma-workspace 2>/dev/null || true)
fi
if [[ -z "${plasma_version}" ]] && command -v pacman >/dev/null 2>&1; then
  plasma_version=$(pacman -Q plasma-workspace 2>/dev/null | awk '{print $2}' || true)
fi

major=$(echo "${plasma_version}" | grep -oE '[0-9]+' | head -1 || true)
if [[ -z "${major}" ]]; then
  log "WARNING: could not determine Plasma version; continuing but version skew is possible"
elif [[ "${major}" -lt 5 ]]; then
  log "KDE_WEBDRIVER_SKIP=Plasma version '${plasma_version}' is below the supported baseline (5.27+/6.x)"
  exit 0
elif [[ "${major}" -eq 5 ]]; then
  minor=$(echo "${plasma_version}" | grep -oE '[0-9]+' | sed -n '2p' || true)
  if [[ -n "${minor}" && "${minor}" -lt 27 ]]; then
    log "KDE_WEBDRIVER_SKIP=Plasma version '${plasma_version}' is below the supported 5.27 LTS baseline"
    exit 0
  fi
fi
log "Plasma version: ${plasma_version:-unknown}"

# Prefer distro packages when available.
install_from_packages() {
  if is_distro fedora; then
    log "Trying Fedora packages..."
    if sudo dnf install -y --setopt=install_weak_deps=False \
        selenium-webdriver-at-spi selenium-webdriver-at-spi-inputsynth 2>/dev/null; then
      log "Installed from Fedora packages"
      return 0
    fi
  elif is_distro debian || is_distro ubuntu || is_distro neon; then
    log "Trying Debian/Ubuntu/Neon packages..."
    if sudo apt-get update -qq 2>/dev/null && \
       sudo apt-get install -y --no-install-recommends \
        selenium-webdriver-at-spi selenium-webdriver-at-spi-inputsynth 2>/dev/null; then
      log "Installed from Debian family packages"
      return 0
    fi
  elif is_distro arch || is_distro kde-linux; then
    log "Trying Arch packages..."
    if sudo pacman -Sy --noconfirm --needed \
        selenium-webdriver-at-spi selenium-webdriver-at-spi-inputsynth 2>/dev/null; then
      log "Installed from Arch packages"
      return 0
    fi
  fi
  return 1
}

# Fall back to a pinned source build.
build_from_source() {
  log "Building selenium-webdriver-at-spi from pinned source (${SELENIUM_AT_SPI_SHA})..."

  local build_dir="${HOME}/.cache/kde-webdriver-build"
  rm -rf "${build_dir}"
  mkdir -p "${build_dir}"

  if is_distro fedora; then
    sudo dnf install -y --setopt=install_weak_deps=False \
      cmake extra-cmake-modules gcc-c++ make git \
      qt6-qtbase-devel qt6-qtwayland-devel plasma-wayland-protocols-devel \
      libxkbcommon-devel wayland-devel python3-devel
  elif is_distro debian || is_distro ubuntu || is_distro neon; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
      cmake extra-cmake-modules g++ make git \
      qt6-base-dev qt6-wayland-dev libplasma-wayland-protocols-dev \
      libxkbcommon-dev libwayland-dev python3-dev
  elif is_distro arch || is_distro kde-linux; then
    sudo pacman -Sy --noconfirm --needed \
      base-devel cmake extra-cmake-modules git \
      qt6-base qt6-wayland plasma-wayland-protocols \
      libxkbcommon wayland python
  else
    log "KDE_WEBDRIVER_SKIP=unsupported distro '${ID}'; cannot install build dependencies"
    exit 0
  fi

  git clone --quiet --depth 1 "${SELENIUM_AT_SPI_URL}" "${build_dir}/src"
  cd "${build_dir}/src"
  git fetch --quiet --depth 1 origin "${SELENIUM_AT_SPI_SHA}"
  git checkout --quiet "${SELENIUM_AT_SPI_SHA}"

  # Strip heavy optional subdirectories and deps we do not need in CI.
  sed -i \
    -e 's/^add_subdirectory(screenshotter)/# add_subdirectory(screenshotter)/' \
    -e 's/^add_subdirectory(videorecorder)/# add_subdirectory(videorecorder)/' \
    -e 's/^add_subdirectory(autotests)/# add_subdirectory(autotests)/' \
    -e 's/^add_subdirectory(appidlister)/# add_subdirectory(appidlister)/' \
    -e 's/^find_package(KF6/# find_package(KF6/' \
    -e 's/^find_package(KWayland/# find_package(KWayland/' \
    -e 's/^find_package(KPipeWire/# find_package(KPipeWire/' \
    CMakeLists.txt

  mkdir -p "${build_dir}/build"
  cd "${build_dir}/build"
  cmake "${build_dir}/src" -DCMAKE_BUILD_TYPE=Release
  make -j"$(nproc)"
  sudo make install

  log "Installed from pinned source build"
}

if install_from_packages; then
  exit 0
fi

build_from_source
