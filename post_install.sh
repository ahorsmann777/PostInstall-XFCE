#!/usr/bin/env bash
#--------------------------------#
# Author: Alejandro Horsmann     #
# 03/05/2024                     #
# Optimized & multi-distro       #
#--------------------------------#

set -euo pipefail

#--------------------------------------------------------------------#
# General settings                                                   #
#--------------------------------------------------------------------#
PROC=POST_INSTALL
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(mktemp -d /tmp/${PROC}.XXXXXX)"
LOG="${SCRIPT_DIR}/${PROC}.log"
FONT_DIR="${HOME}/.local/share/fonts"
USER="${USER:-$(id -un)}"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

#--------------------------------------------------------------------#
# utilidades de output                                               #
#--------------------------------------------------------------------#
COLOR_GREEN='\e[32m'
COLOR_YELLOW='\e[33m'
COLOR_RED='\e[31m'
COLOR_RESET='\e[0m'

print_green()  { echo -e "${COLOR_GREEN}$1${COLOR_RESET}"; }
print_yellow() { echo -e "${COLOR_YELLOW}$1${COLOR_RESET}"; }
print_red()    { echo -e "${COLOR_RED}$1${COLOR_RESET}" >&2; }

# lolcat is optional
print_banner() {
    local msg="$1"
    if command -v lolcat >/dev/null 2>&1; then
        printf '%s\n' "$msg" | lolcat
    else
        print_green "$msg"
    fi
}

#--------------------------------------------------------------------#
# Log                                                                #
#--------------------------------------------------------------------#
exec > >(tee -a "$LOG") 2>&1

#--------------------------------------------------------------------#
# chequea que no se ejecute como root                                #
#--------------------------------------------------------------------#
if [[ "${EUID}" -eq 0 ]]; then
    print_red "# Dont't run this script as root. No ejecutar como root #."
    exit 1
fi

if [[ -n "${SUDO_USER:-}" ]]; then
    print_red "# No uses sudo para lanzar el script. Don't use sudo to run this script #"
    exit 1
fi

# Define ditribución #
DISTRO_ID=""
DISTRO_LIKE=""
if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_ID="${ID:-}"
    DISTRO_LIKE="${ID_LIKE:-}"
fi

# Packet managger #
PKG_MANAGER=""
for pm in apt-get dnf yum pacman zypper apk xbps-install emerge; do
    if command -v "$pm" >/dev/null 2>&1; then
        PKG_MANAGER="$pm"
        break
    fi
done

if [[ -z "$PKG_MANAGER" ]]; then
    print_red "No se detectó un gestor de paquetes compatible."
    exit 1
fi

case "$PKG_MANAGER" in
    apt-get)       INSTALL_CMD=(sudo apt-get install -y) ;;
    dnf)           INSTALL_CMD=(sudo dnf install -y) ;;
    yum)           INSTALL_CMD=(sudo yum install -y) ;;
    pacman)        INSTALL_CMD=(sudo pacman -S --needed --noconfirm) ;;
    zypper)        INSTALL_CMD=(sudo zypper --non-interactive install) ;;
    apk)           INSTALL_CMD=(sudo apk add) ;;
    xbps-install)  INSTALL_CMD=(sudo xbps-install -y) ;;
    emerge)        INSTALL_CMD=(sudo emerge -n) ;;
esac

install_packages() {
    if [[ ${#@} -gt 0 ]]; then
        print_yellow "Instalando dependencias: $*"
        "${INSTALL_CMD[@]}" "$@" || \
            print_red "No se pudieron instalar algunas dependencias: $*"
    fi
}

# Asegura un comando instalando su paquete solo si falta.#
# Uso: ensure_cmd <comando> <paquete> [paquete alternativo...]
ensure_cmd() {
    local cmd="$1"; shift
    command -v "$cmd" >/dev/null 2>&1 && return 0
    local pkg
    for pkg in "$@"; do
        install_packages "$pkg"
        command -v "$cmd" >/dev/null 2>&1 && return 0
    done
    print_red "No se pudo instalar '$cmd' (probados: $*)."
    return 1
}

#--------------------------------------------------------------------#
# Dependencias base                                                  #
#--------------------------------------------------------------------#
print_banner "             《·───────────────·》 SCRIPT POST INSTALL XFCE 《·───────────────·》"

ensure_cmd git      git      || true
ensure_cmd wget     wget     || true
ensure_cmd unzip    unzip    || true
ensure_cmd zsh      zsh      || true
ensure_cmd curl     curl     || true
ensure_cmd fc-cache fontconfig fontconfig1 || true

# lolcat es opcional (no rompe si no existe en el repo)
if ! command -v lolcat >/dev/null 2>&1; then
    "${INSTALL_CMD[@]}" lolcat 2>/dev/null || \
        print_yellow "lolcat no disponible en los repositorios; se usará salida sin color."
fi

#--------------------------------------------------------------------#
# Instalación de fuentes                                             #
#--------------------------------------------------------------------#
print_banner "         <============================= Installing fonts / Instalando fuentes ==================================>"

mkdir -p "$FONT_DIR" "$WORK_DIR/fonts"

fetch_font() {
    local url="$1" out="$2"
    wget -q --show-progress -O "$WORK_DIR/fonts/$out" "$url" || \
        print_red "No se pudo descargar $out"
}

# MesloLGS NF #
fetch_font "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf"       "MesloLGS NF Regular.ttf"
fetch_font "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf"          "MesloLGS NF Bold.ttf"
fetch_font "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf"        "MesloLGS NF Italic.ttf"
fetch_font "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf" "MesloLGS NF Bold Italic.ttf"

# Hack Nerd Font #
wget -q --show-progress -O "$WORK_DIR/fonts/Hack.zip" \
    "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/Hack.zip" || \
    print_red "No se pudo descargar Hack Nerd Font"

if [[ -f "$WORK_DIR/fonts/Hack.zip" ]]; then
    unzip -q -o "$WORK_DIR/fonts/Hack.zip" -d "$WORK_DIR/fonts/Hack"
fi

cp -f "$WORK_DIR/fonts"/*.ttf "$FONT_DIR/" 2>/dev/null || true
find "$WORK_DIR/fonts/Hack" -iname '*.ttf' -exec cp -f {} "$FONT_DIR/" \; 2>/dev/null || true

if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f "$FONT_DIR" >/dev/null 2>&1 || true
    print_green "Fuentes instaladas en $FONT_DIR"
else
    print_yellow "fc-cache no disponible; instala 'fontconfig' y ejecútalo manualmente."
fi

#--------------------------------------------------------------------#
# powerlevel10k                                                      #
#--------------------------------------------------------------------#
print_banner "         <============================= Installing powerlevel10k ==================================>"

if [[ ! -d "$HOME/powerlevel10k" ]]; then
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$HOME/powerlevel10k"
else
    print_yellow "powerlevel10k ya está instalado, se omite."
fi

ZSH_THEME_LINE='source ~/powerlevel10k/powerlevel10k.zsh-theme'
touch "$HOME/.zshrc"
if ! grep -qxF "$ZSH_THEME_LINE" "$HOME/.zshrc"; then
    printf '\n%s\n' "$ZSH_THEME_LINE" >> "$HOME/.zshrc"
fi

#--------------------------------------------------------------------#
# XFCE: bordes redondeados del panel                                 #
#--------------------------------------------------------------------#
print_banner "         <============================= Setting round edges of XFCE bar ==============================>"

GTK_DIR="$HOME/.config/gtk-3.0"
mkdir -p "$GTK_DIR"
GTK_CSS="$GTK_DIR/gtk.css"
ROUND_CSS='.xfce4-panel {
   border-bottom-left-radius: 10px;
   border-bottom-right-radius: 10px;
   border-top-left-radius: 10px;
   border-top-right-radius: 10px;
}'

if ! grep -qF '.xfce4-panel {' "$GTK_CSS" 2>/dev/null; then
    printf '%s\n' "$ROUND_CSS" >> "$GTK_CSS"
fi

#--------------------------------------------------------------------#
# Fondos de pantalla                                                 #
#--------------------------------------------------------------------#
print_banner "         <=========================== Downloading cool wallpapers ================================>"

if command -v xdg-user-dir >/dev/null 2>&1; then
    PICTURES_DIR="$(xdg-user-dir PICTURES)"
else
    PICTURES_DIR="$HOME/Pictures"
fi
# Fallback a "Imágenes" (entornos en español)
if [[ ! -d "$PICTURES_DIR" && -d "$HOME/Imágenes" ]]; then
    PICTURES_DIR="$HOME/Imágenes"
fi
mkdir -p "$PICTURES_DIR"

WALL_DIR="$WORK_DIR/Wallpapers"
if [[ ! -d "$WALL_DIR" ]]; then
    git clone --depth=1 https://github.com/antoniosarosi/Wallpapers.git "$WALL_DIR"
fi
cp -rf "$WALL_DIR"/* "$PICTURES_DIR/" 2>/dev/null || true

# Establecer fondo si estamos en una sesión XFCE #
set_wallpaper() {
    local img="$1"
    local prop
    mapfile -t prop < <(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep '/last-image' || true)
    if [[ ${#prop[@]} -eq 0 ]]; then
        xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/last-image -s "$img" 2>/dev/null || true
        return
    fi
    for p in "${prop[@]}"; do
        xfconf-query -c xfce4-desktop -p "$p" -s "$img" 2>/dev/null || true
    done
}

if command -v xfconf-query >/dev/null 2>&1 && [[ -f "$PICTURES_DIR/50.jpg" ]]; then
    set_wallpaper "$PICTURES_DIR/50.jpg"
elif ! command -v xfconf-query >/dev/null 2>&1; then
    print_yellow "xfconf-query no disponible; configura el fondo manualmente."
fi

#--------------------------------------------------------------------#
# Candy Icons                                                        #
#--------------------------------------------------------------------#
print_banner "          <=========================== Downloading Candy Icons ====================================>"

ICON_BASE="$WORK_DIR/candy-icons"
ICON_TARGET="$HOME/.local/share/icons"
mkdir -p "$ICON_BASE" "$ICON_TARGET"

wget -q --show-progress -O "$ICON_BASE/master.zip" \
    "https://github.com/EliverLara/candy-icons/archive/refs/heads/master.zip" || \
    print_red "No se pudieron descargar los Candy Icons."

if [[ -f "$ICON_BASE/master.zip" ]]; then
    unzip -q -o "$ICON_BASE/master.zip" -d "$ICON_BASE"
    SRC_ICONS="$(find "$ICON_BASE" -maxdepth 1 -type d -name 'candy-icons-*' | head -n1)"
    if [[ -n "$SRC_ICONS" ]]; then
        rm -rf "$ICON_TARGET/candy-icons"
        cp -rf "$SRC_ICONS" "$ICON_TARGET/candy-icons"
    fi
fi

#--------------------------------------------------------------------#
# Tema Adwaita-dark                                                  #
#--------------------------------------------------------------------#
print_banner "           <======================= Setting up Adwaita Dark Theme ================================>"

if command -v xfconf-query >/dev/null 2>&1; then
    if xfconf-query -c xsettings -p /Net/ThemeName >/dev/null 2>&1; then
        xfconf-query -c xsettings -p /Net/ThemeName -s "Adwaita-dark" || true
    else
        xfconf-query -c xsettings -p /Net/ThemeName -s "Adwaita-dark" --create -t string || true
    fi
    # Iconos Candy si el paquete se instaló
    if [[ -d "$HOME/.local/share/icons/candy-icons" ]]; then
        xfconf-query -c xsettings -p /Net/IconThemeName >/dev/null 2>&1 \
            && xfconf-query -c xsettings -p /Net/IconThemeName -s "candy-icons" \
            || xfconf-query -c xsettings -p /Net/IconThemeName -s "candy-icons" --create -t string || true
    fi
else
    print_yellow "xfconf-query no disponible; ajusta el tema manualmente."
fi

#---------------------------------------------------------------------
# Shell por defecto: zsh
#---------------------------------------------------------------------
if command -v zsh >/dev/null 2>&1; then
    ZSH_BIN="$(command -v zsh)"
    if command -v getent >/dev/null 2>&1; then
        CURRENT_SHELL="$(getent passwd "$USER" | cut -d: -f7)"
    else
        CURRENT_SHELL="$(grep "^${USER}:" /etc/passwd | cut -d: -f7)"
    fi
    if [[ "$CURRENT_SHELL" != "$ZSH_BIN" ]]; then
        sudo chsh -s "$ZSH_BIN" "$USER" \
            && print_green "Shell por defecto cambiado a zsh." \
            || print_red "No se pudo cambiar el shell por defecto."
    fi
else
    print_red "zsh no está instalado, no se cambió el shell."
fi

#---------------------------------------------------------------------
# Fin
#---------------------------------------------------------------------
print_banner "         <============================= script completed successfully ===============================>"
print_banner "         <============================= script completado con éxito ==============================>"
echo "                                                                                           "
print_banner "                  《·───────────────·》  PLEASE REBOOT YOUR SYSTEM  《·───────────────·》"
print_banner "                  《·───────────────·》  POR FAVOR REINICIA TU SISTEMA  《·───────────────·》"
echo "                                                                                           "
print_banner "                                        《·───────────────·》                          "
print_banner "              You must change the font of your terminal to one of the MESLO fonts          "
print_banner "              to configure correctly the p10k terminal, and you should set the icons       "
print_banner "                  with Candy Icons, the rest depend on your taste, have fun             "
print_banner "                                        《·───────────────·》                              "
print_banner "              Debes cambiar la fuente de tu terminal a una de las fuentes MESLO           "
print_banner "              para configurar correctamente la terminal p10k, y deberías establecer        "
print_banner "              los iconos con Candy Icons; el resto depende de tu gusto, ¡diviértete!       "
print_banner "                                        《·───────────────·》"
