#!/usr/bin/env bash
# Déploiement EtaComp2K25 sur Ubuntu Desktop (26.04+)
# Usage : bash ubuntu_install.sh
# Variables optionnelles :
#   ETACOMP_REPO_URL   (défaut : https://github.com/xmaquet/EtaComp2k25.git)
#   ETACOMP_BRANCH     (défaut : main)
#   ETACOMP_INSTALL_DIR (défaut : ~/EtaComp2k25)

set -euo pipefail

# --- Configuration -----------------------------------------------------------

REPO_URL="${ETACOMP_REPO_URL:-https://github.com/xmaquet/EtaComp2k25.git}"
BRANCH="${ETACOMP_BRANCH:-main}"
INSTALL_DIR="${ETACOMP_INSTALL_DIR:-${HOME}/EtaComp2k25}"
VENV_DIR="${INSTALL_DIR}/.venv"
DESKTOP_FILE="${HOME}/.local/share/applications/etacomp.desktop"
APP_ID="etacomp2k25"
ICON_NAME="${APP_ID}"
ICON_SRC="${INSTALL_DIR}/src/etacomp/resources/etaComp.svg"

# Paquets système requis pour PySide6/Qt sous Ubuntu Desktop
APT_PACKAGES=(
    git
    python3
    python3-venv
    python3-pip
    build-essential
    libxcb-cursor0
    libxkbcommon-x11-0
    libegl1
    libgl1
    libglib2.0-0
    libfontconfig1
    libx11-xcb1
    libxcb-icccm4
    libxcb-image0
    libxcb-keysyms1
    libxcb-render-util0
    libxcb-shape0
    libxcb-xfixes0
    libxcb-xinerama0
    libxcb-xinput0
    libxcb-xkb1
    libxkbcommon0
    libdbus-1-3
)

# --- Affichage ---------------------------------------------------------------

info()  { printf '\033[1;34m[INFO]\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m[ OK ]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
fail()  { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*" >&2; exit 1; }

# --- Vérifications préalables ------------------------------------------------

if [[ "$(uname -s)" != "Linux" ]]; then
    fail "Ce script doit être exécuté sur Ubuntu/Linux (pas sous Windows/macOS)."
fi

if ! command -v apt-get >/dev/null 2>&1; then
    fail "Gestionnaire apt-get introuvable. Ce script cible Ubuntu/Debian."
fi

# --- Paquets système ---------------------------------------------------------

install_apt_packages() {
    local missing=()
    for pkg in "${APT_PACKAGES[@]}"; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done

    if ((${#missing[@]} == 0)); then
        ok "Tous les paquets système requis sont déjà installés."
        return 0
    fi

    info "Installation des paquets système manquants (${#missing[@]})…"
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
    elif command -v sudo >/dev/null 2>&1; then
        sudo apt-get update -qq
        DEBIAN_FRONTEND=noninteractive sudo apt-get install -y "${missing[@]}"
    else
        fail "Paquets manquants et sudo indisponible. Installez : ${missing[*]}"
    fi
    ok "Paquets système installés."
}

# --- Dépôt Git ---------------------------------------------------------------

clone_or_update_repo() {
    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        info "Dépôt existant détecté dans ${INSTALL_DIR} — mise à jour…"
        git -C "${INSTALL_DIR}" fetch origin
        git -C "${INSTALL_DIR}" checkout "${BRANCH}"
        git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
    else
        info "Clonage de ${REPO_URL} (branche ${BRANCH})…"
        git clone --branch "${BRANCH}" --single-branch "${REPO_URL}" "${INSTALL_DIR}"
    fi
    ok "Sources à jour dans ${INSTALL_DIR}."
}

# --- Environnement Python ------------------------------------------------------

setup_venv() {
    local py_version
    py_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

    info "Python détecté : ${py_version}"
    python3 - <<'PYCHECK'
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
    raise SystemExit(f"Python {major}.{minor} — version minimale requise : 3.10")
PYCHECK

    if [[ ! -d "${VENV_DIR}" ]]; then
        info "Création de l'environnement virtuel…"
        python3 -m venv "${VENV_DIR}"
    else
        info "Environnement virtuel existant réutilisé."
    fi

    info "Installation des dépendances Python (pip install -e \".[dev]\")…"
    "${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel setuptools
    "${VENV_DIR}/bin/pip" install -e "${INSTALL_DIR}[dev]"
    ok "Application installée dans le venv."
}

# --- Icône application ---------------------------------------------------------

install_app_icon() {
    local icon_base="${HOME}/.local/share/icons/hicolor"
    local icon_scalable="${icon_base}/scalable/apps"
    local icon_256="${icon_base}/256x256/apps"
    local icon_48="${icon_base}/48x48/apps"
    local png_src_256="${INSTALL_DIR}/scripts/deploy/icons/256x256/apps/${ICON_NAME}.png"
    local png_src_48="${INSTALL_DIR}/scripts/deploy/icons/48x48/apps/${ICON_NAME}.png"

    if [[ ! -f "${ICON_SRC}" ]]; then
        warn "Icône introuvable : ${ICON_SRC} — icône générique conservée."
        return 0
    fi

    mkdir -p "${icon_scalable}" "${icon_256}" "${icon_48}"
    cp "${ICON_SRC}" "${icon_scalable}/${ICON_NAME}.svg"

    if [[ -f "${png_src_256}" ]]; then
        cp "${png_src_256}" "${icon_256}/${ICON_NAME}.png"
    fi
    if [[ -f "${png_src_48}" ]]; then
        cp "${png_src_48}" "${icon_48}/${ICON_NAME}.png"
    fi

    if [[ ! -f "${icon_base}/index.theme" ]]; then
        cat > "${icon_base}/index.theme" <<'EOF'
[icon theme]
Name=Hicolor
Comment=Fallback icon theme
Directories=scalable/apps,256x256/apps,48x48/apps

[scalable/apps]
Size=256
Type=Scalable
MinSize=1
MaxSize=512

[256x256/apps]
Size=256
Type=Fixed

[48x48/apps]
Size=48
Type=Fixed
EOF
    fi

    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "${icon_base}" 2>/dev/null || true
    fi
    ok "Icône installée : ${icon_scalable}/${ICON_NAME}.svg"
    [[ -f "${icon_256}/${ICON_NAME}.png" ]] && ok "PNG 256 : ${icon_256}/${ICON_NAME}.png"
}

# --- Raccourci bureau ----------------------------------------------------------

create_desktop_entry() {
    local desktop_dir icon_line icon_png
    desktop_dir="$(xdg-user-dir DESKTOP 2>/dev/null || echo "${HOME}/Desktop")"
    icon_png="${HOME}/.local/share/icons/hicolor/256x256/apps/${ICON_NAME}.png"
    mkdir -p "$(dirname "${DESKTOP_FILE}")" "${desktop_dir}"

    if [[ -f "${icon_png}" ]]; then
        icon_line="Icon=${icon_png}"
    elif [[ -f "${ICON_SRC}" ]]; then
        icon_line="Icon=${ICON_SRC}"
    else
        icon_line="Icon=applications-science"
    fi

    cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=EtaComp2K25
Comment=Vérification de comparateurs (métrologie)
Exec=${VENV_DIR}/bin/etacomp
Path=${INSTALL_DIR}
${icon_line}
Terminal=false
Categories=Science;Engineering;
StartupWMClass=${APP_ID}
EOF

    cp "${DESKTOP_FILE}" "${desktop_dir}/EtaComp2K25.desktop"
    chmod +x "${DESKTOP_FILE}" "${desktop_dir}/EtaComp2K25.desktop"

    if command -v gio >/dev/null 2>&1; then
        gio set "${desktop_dir}/EtaComp2K25.desktop" metadata::trusted true 2>/dev/null || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${HOME}/.local/share/applications" 2>/dev/null || true
    fi
    ok "Raccourci menu : ${DESKTOP_FILE}"
    ok "Raccourci bureau : ${desktop_dir}/EtaComp2K25.desktop"
}

# --- Port série (adaptateur RS-232 USB) ----------------------------------------

setup_serial_access() {
    local user_name
    user_name="$(id -un)"

    if groups "${user_name}" | grep -q '\bdialout\b'; then
        ok "L'utilisateur ${user_name} est déjà dans le groupe dialout."
    elif command -v sudo >/dev/null 2>&1; then
        info "Ajout de ${user_name} au groupe dialout (accès port série)…"
        sudo usermod -aG dialout "${user_name}"
        warn "Déconnectez-vous puis reconnectez-vous pour activer le groupe dialout."
    else
        warn "Impossible d'ajouter dialout sans sudo. Lancez : sudo usermod -aG dialout ${user_name}"
    fi
}

# --- Profil utilisateur vide ---------------------------------------------------

ensure_user_data_dir() {
    # L'application crée ~/.EtaComp2K25/ au premier lancement.
    # On ne copie pas data/ du dépôt : profil vide volontaire.
    local data_dir="${HOME}/.EtaComp2K25"
    if [[ ! -d "${data_dir}" ]]; then
        info "Le profil utilisateur sera créé au premier lancement (${data_dir})."
    else
        ok "Profil utilisateur existant conservé : ${data_dir}"
    fi
}

# --- Résumé --------------------------------------------------------------------

print_summary() {
    cat <<EOF

================================================================================
  EtaComp2K25 — déploiement terminé
================================================================================

  Sources (stockage Git) : ${INSTALL_DIR}
  Branche                  : ${BRANCH}
  Environnement Python     : ${VENV_DIR}
  Données métier           : ~/.EtaComp2K25/
  Raccourci                : Menu Applications → EtaComp2K25

  Lancer depuis le terminal :
    ${VENV_DIR}/bin/etacomp

  Mettre à jour plus tard :
    cd ${INSTALL_DIR}
    git pull
    ${VENV_DIR}/bin/pip install -e ".[dev]"

  Port série (adaptateur USB-RS232) :
    1. Brancher le câble
    2. Lister les ports : ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
    3. Sonde de test :
       ${VENV_DIR}/bin/python ${INSTALL_DIR}/src/etacomp/tools/serial_probe.py /dev/ttyUSB0
    4. Choisir le port dans l'application (Session → connexion série)

  Si le port série ne répond pas : vérifiez dialout (déconnexion/reconnexion).

================================================================================

EOF
}

# --- Main ----------------------------------------------------------------------

main() {
    info "EtaComp2K25 — installation Ubuntu Desktop"
    info "Dépôt  : ${REPO_URL}"
    info "Branche: ${BRANCH}"
    info "Cible  : ${INSTALL_DIR}"
    echo

    install_apt_packages
    clone_or_update_repo
    setup_venv
    install_app_icon
    create_desktop_entry
    setup_serial_access
    ensure_user_data_dir
    print_summary
}

main "$@"
