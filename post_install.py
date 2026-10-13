#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#--------------------------------#
# Author: Alejandro Horsmann     #
# 03/05/2024                     #
# Optimized & multi-distro       #
# Python version                 #
#--------------------------------#
"""Script de post-instalación para XFCE en múltiples distribuciones de Linux.

Equivalente en Python de `post_install.sh`. Instala fuentes, el prompt
(Powerlevel10k u Oh My Zsh), sus plugins, fondos de pantalla, un set de
iconos (Candy Icons o BeautyBeam), el tema Adwaita-dark y deja zsh como
shell por defecto.

Solo usa la librería estándar de Python 3.8+.
"""

from __future__ import annotations

import os
import re
import sys
import pwd
import shutil
import tarfile
import tempfile
import zipfile
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime

#---------------------------------------------------------------------
# Constantes
#---------------------------------------------------------------------
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

PACKAGE_MANAGERS = ["apt-get", "dnf", "yum", "pacman", "zypper",
                    "apk", "xbps-install", "emerge"]

INSTALL_CMDS = {
    "apt-get": ["sudo", "apt-get", "install", "-y"],
    "dnf": ["sudo", "dnf", "install", "-y"],
    "yum": ["sudo", "yum", "install", "-y"],
    "pacman": ["sudo", "pacman", "-S", "--needed", "--noconfirm"],
    "zypper": ["sudo", "zypper", "--non-interactive", "install"],
    "apk": ["sudo", "apk", "add"],
    "xbps-install": ["sudo", "xbps-install", "-y"],
    "emerge": ["sudo", "emerge", "-n"],
}

MESLO_FONTS = {
    "MesloLGS NF Regular.ttf":
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Regular.ttf",
    "MesloLGS NF Bold.ttf":
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold.ttf",
    "MesloLGS NF Italic.ttf":
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Italic.ttf",
    "MesloLGS NF Bold Italic.ttf":
        "https://github.com/romkatv/powerlevel10k-media/raw/master/MesloLGS%20NF%20Bold%20Italic.ttf",
}

HACK_FONT_URL = ("https://github.com/ryanoasis/nerd-fonts/releases/"
                 "download/v3.0.2/Hack.zip")

P10K_REPO = "https://github.com/romkatv/powerlevel10k.git"
OMZ_INSTALL_URL = ("https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/"
                   "master/tools/install.sh")

ZSH_PLUGINS = {
    "zsh-autosuggestions":
        "https://github.com/zsh-users/zsh-autosuggestions",
    "zsh-syntax-highlighting":
        "https://github.com/zsh-users/zsh-syntax-highlighting.git",
}

WALLPAPERS_REPO = "https://github.com/antoniosarosi/Wallpapers.git"
CANDY_ICONS_URL = ("https://github.com/EliverLara/candy-icons/archive/"
                   "refs/heads/master.zip")
BEAUTYBEAM_API = "https://api.kde-look.org/ocs/v1/content/data/2357069"

ROUND_CSS = """.xfce4-panel {
   border-bottom-left-radius: 10px;
   border-bottom-right-radius: 10px;
   border-top-left-radius: 10px;
   border-top-right-radius: 10px;
}
"""

FINAL_MESSAGES = [
    "         <============================= script completed successfully ===============================>",
    "         <============================= script completado con éxito ==============================>",
    "                  《·───────────────·》  PLEASE REBOOT YOUR SYSTEM  《·───────────────·》",
    "                  《·───────────────·》  POR FAVOR REINICIA TU SISTEMA  《·───────────────·》",
    "              You must change the font of your terminal to one of the MESLO fonts          ",
    "              to configure correctly the p10k terminal, and you should set the icons       ",
    "                  with Candy Icons or BeautyBeam, the rest depends on your taste, have fun ",
    "              Debes cambiar la fuente de tu terminal a una de las fuentes MESLO           ",
    "              para configurar correctamente la terminal p10k, y deberías establecer        ",
    "              los iconos con Candy Icons o BeautyBeam; el resto depende de tu gusto, ¡diviértete!",
]


#---------------------------------------------------------------------
# Log: duplica stdout/stderr a un archivo (equivalente a `tee`)
#---------------------------------------------------------------------
class Tee:
    def __init__(self, stream, logfile):
        self.stream = stream
        self.logfile = logfile

    def write(self, data):
        self.stream.write(data)
        self.logfile.write(data)
        self.logfile.flush()
        return len(data)

    def flush(self):
        self.stream.flush()
        self.logfile.flush()

    def isatty(self):
        return self.stream.isatty()


def print_green(msg):
    print(f"{GREEN}{msg}{RESET}")


def print_yellow(msg):
    print(f"{YELLOW}{msg}{RESET}")


def print_red(msg):
    print(f"{RED}{msg}{RESET}", file=sys.stderr)


def print_banner(msg):
    """Muestra un mensaje con lolcat si está disponible, si no en verde."""
    if shutil.which("lolcat"):
        try:
            result = subprocess.run(["lolcat"], input=msg, text=True,
                                    capture_output=True)
            sys.stdout.write(result.stdout)
            if result.stdout and not result.stdout.endswith("\n"):
                print()
            return
        except Exception:
            pass
    print_green(msg)


#---------------------------------------------------------------------
# Clase principal
#---------------------------------------------------------------------
class PostInstall:
    def __init__(self):
        self.home = Path.home()
        self.script_dir = Path(__file__).resolve().parent
        self.work_dir = Path(tempfile.mkdtemp(prefix="POST_INSTALL."))
        self.log_path = self.script_dir / "POST_INSTALL.log"
        self.font_dir = self.home / ".local/share/fonts"
        self.shell_config_dir = self.script_dir / "shell_config"

        self.config_p10k = self.shell_config_dir / "zshrc.powerlevel10k"
        self.config_omz = self.shell_config_dir / "zshrc.oh-my-zsh"
        self.p10k_theme_file = self.shell_config_dir / "p10k.zsh"

        self.distro_id = ""
        self.distro_like = ""
        self.pkg_manager = ""
        self.selected_icon_theme = ""
        self._logfile = None

    #-------------------------------------------------------------
    # Utilidades
    #-------------------------------------------------------------
    def run(self, cmd, **kwargs):
        """Ejecuta un comando heredando la terminal (para sudo, git, etc.)."""
        try:
            return subprocess.run(cmd, **kwargs)
        except FileNotFoundError:
            print_red(f"Comando no encontrado: {cmd[0]}")
            return None

    def download(self, url, dest):
        """Descarga una URL a un archivo usando urllib."""
        dest = Path(dest)
        req = urllib.request.Request(url, headers={"User-Agent": "post-install-xfce"})
        try:
            with urllib.request.urlopen(req) as response, open(dest, "wb") as fh:
                shutil.copyfileobj(response, fh)
            return True
        except Exception as exc:
            print_red(f"No se pudo descargar {url}: {exc}")
            return False

    @staticmethod
    def extract_zip(archive, dest):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)

    @staticmethod
    def extract_tar(archive, dest):
        with tarfile.open(archive, "r:gz") as tf:
            try:
                tf.extractall(dest, filter="data")
            except TypeError:
                tf.extractall(dest)

    #-------------------------------------------------------------
    # Detección de entorno
    #-------------------------------------------------------------
    def detect_distro(self):
        os_release = Path("/etc/os-release")
        if os_release.is_file():
            for line in os_release.read_text(errors="replace").splitlines():
                if line.startswith("ID="):
                    self.distro_id = line[3:].strip().strip('"')
                elif line.startswith("ID_LIKE="):
                    self.distro_like = line[8:].strip().strip('"')

    def detect_pkg_manager(self):
        for pm in PACKAGE_MANAGERS:
            if shutil.which(pm):
                self.pkg_manager = pm
                return
        print_red("No se detectó un gestor de paquetes compatible.")
        sys.exit(1)

    #-------------------------------------------------------------
    # Paquetes
    #-------------------------------------------------------------
    def install_packages(self, packages):
        packages = list(packages)
        if not packages:
            print_red("No se indicaron paquetes a instalar.")
            return
        print_yellow(f"Instalando dependencias: {' '.join(packages)}")
        cmd = INSTALL_CMDS[self.pkg_manager] + packages
        if self.run(cmd).returncode != 0:
            print_red(f"No se pudieron instalar algunas dependencias: {' '.join(packages)}")

    def ensure_cmd(self, command, *packages):
        """Instala el paquete si el comando no está disponible."""
        if shutil.which(command):
            return True
        for pkg in packages:
            self.install_packages([pkg])
            if shutil.which(command):
                return True
        print_red(f"No se pudo instalar '{command}' (probados: {' '.join(packages)}).")
        return False

    #-------------------------------------------------------------
    # Fuentes
    #-------------------------------------------------------------
    def install_fonts(self):
        print_banner("         <============================= Installing fonts / Instalando fuentes ==================================>")

        fonts_work = self.work_dir / "fonts"
        hack_dir = fonts_work / "Hack"
        fonts_work.mkdir(parents=True, exist_ok=True)
        self.font_dir.mkdir(parents=True, exist_ok=True)

        for name, url in MESLO_FONTS.items():
            if not self.download(url, fonts_work / name):
                print_red(f"No se pudo descargar {name}")

        hack_zip = fonts_work / "Hack.zip"
        if self.download(HACK_FONT_URL, hack_zip):
            try:
                self.extract_zip(hack_zip, hack_dir)
            except Exception as exc:
                print_red(f"No se pudo extraer Hack Nerd Font: {exc}")
        else:
            print_red("No se pudo descargar Hack Nerd Font")

        for ttf in fonts_work.glob("*.ttf"):
            shutil.copy2(ttf, self.font_dir / ttf.name)
        if hack_dir.is_dir():
            for ttf in hack_dir.rglob("*.ttf"):
                shutil.copy2(ttf, self.font_dir / ttf.name)

        if shutil.which("fc-cache"):
            self.run(["fc-cache", "-f", str(self.font_dir)])
            print_green(f"Fuentes instaladas en {self.font_dir}")
        else:
            print_yellow("fc-cache no disponible; instala 'fontconfig' y ejecútalo manualmente.")

    #-------------------------------------------------------------
    # Shell prompt
    #-------------------------------------------------------------
    def backup_zshrc(self):
        zshrc = self.home / ".zshrc"
        if zshrc.is_file():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            bak = self.home / f".zshrc.post_install.{stamp}.bak"
            shutil.copy2(zshrc, bak)
            print_yellow(f"Backup de .zshrc guardado en {bak}")

    def render_config(self, src, dst):
        """Copia un .zshrc normalizando rutas absolutas del usuario a $HOME."""
        content = Path(src).read_text(errors="replace")
        content = content.replace(str(self.home), "$HOME")
        Path(dst).write_text(content)

    def preview_file(self, path):
        path = Path(path)
        if not path.is_file():
            print_red(f"No se encontró el archivo de previsualización: {path}")
            return
        print_yellow(f"----- Vista previa: {path.name} -----")
        tty = Path("/dev/tty")
        if shutil.which("less") and tty.exists():
            try:
                with open("/dev/tty", "r") as tin, open("/dev/tty", "w") as tout:
                    subprocess.run(["less", "-R", str(path)],
                                   stdin=tin, stdout=tout, stderr=tout)
                print_yellow("--------------------------------------------")
                return
            except Exception:
                pass
        print(path.read_text(errors="replace"))
        print_yellow("--------------------------------------------")

    def install_zsh_plugins(self):
        custom = Path(os.environ.get("ZSH_CUSTOM") or (self.home / ".oh-my-zsh/custom"))
        plugins_dir = custom / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        for name, repo in ZSH_PLUGINS.items():
            target = plugins_dir / name
            if target.is_dir():
                print_yellow(f"El plugin {name} ya está instalado, se omite.")
                continue
            print_green(f"Instalando plugin {name}...")
            if self.run(["git", "clone", "--depth=1", repo, str(target)]).returncode != 0:
                print_red(f"No se pudo clonar el plugin {name}.")

    def install_powerlevel10k(self):
        p10k_dir = self.home / "powerlevel10k"
        if not p10k_dir.is_dir():
            self.run(["git", "clone", "--depth=1", P10K_REPO, str(p10k_dir)])
        else:
            print_yellow("powerlevel10k ya está instalado, se omite la clonación.")

        self.install_zsh_plugins()

        if self.p10k_theme_file.is_file():
            shutil.copy2(self.p10k_theme_file, self.home / ".p10k.zsh")
            print_green("Configuración de p10k copiada a ~/.p10k.zsh")

        if self.config_p10k.is_file():
            self.backup_zshrc()
            self.render_config(self.config_p10k, self.home / ".zshrc")
            print_green("Configuración .zshrc de Powerlevel10k aplicada.")
        else:
            line = "source ~/powerlevel10k/powerlevel10k.zsh-theme"
            zshrc = self.home / ".zshrc"
            zshrc.touch()
            content = zshrc.read_text(errors="replace")
            if line not in content.splitlines():
                with open(zshrc, "a") as fh:
                    fh.write(f"\n{line}\n")

    def install_ohmyzsh(self):
        omz_dir = self.home / ".oh-my-zsh"
        if not omz_dir.is_dir():
            env = dict(os.environ, RUNZSH="no", KEEP_ZSHRC="yes", CHSH="no")
            script = self._fetch(OMZ_INSTALL_URL)
            if script:
                result = self.run(["sh", "-c", script], env=env)
                if result is None or result.returncode != 0:
                    print_red("No se pudo instalar Oh My Zsh.")
            else:
                print_red("No se pudo instalar Oh My Zsh.")
        else:
            print_yellow("Oh My Zsh ya está instalado, se omite la instalación.")

        self.install_zsh_plugins()

        if self.config_omz.is_file():
            self.backup_zshrc()
            self.render_config(self.config_omz, self.home / ".zshrc")
            print_green("Configuración .zshrc de Oh My Zsh aplicada.")

    @staticmethod
    def _fetch(url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "post-install-xfce"})
            with urllib.request.urlopen(req) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            print_red(f"No se pudo descargar {url}: {exc}")
            return ""

    def select_shell_prompt(self):
        print_banner("         <============================= Selecting shell prompt ==================================>")

        if not sys.stdin.isatty():
            print_yellow("Ejecución no interactiva: se instalará Powerlevel10k por defecto.")
            self.install_powerlevel10k()
            return

        while True:
            print()
            print("  Elige el entorno de tu shell:")
            print("    1) Powerlevel10k  - prompt rápido, informativo y personalizable (recomendado)")
            print("    2) Oh My Zsh only - prompt clásico sin Powerlevel10k (config actual del proyecto)")
            print("    3) Ver previsualizaciones")
            print("    4) Omitir este paso")
            choice = input("  Opción [1]: ").strip() or "1"

            if choice == "1":
                self.preview_file(self.config_p10k)
                self.preview_file(self.p10k_theme_file)
                if input("  ¿Aplicar Powerlevel10k? [S/n]: ").strip().lower() == "n":
                    continue
                self.install_powerlevel10k()
                break
            elif choice == "2":
                self.preview_file(self.config_omz)
                if input("  ¿Aplicar Oh My Zsh only? [S/n]: ").strip().lower() == "n":
                    continue
                self.install_ohmyzsh()
                break
            elif choice == "3":
                self.preview_file(self.config_p10k)
                self.preview_file(self.p10k_theme_file)
                self.preview_file(self.config_omz)
            elif choice == "4":
                print_yellow("Se omitió la instalación del prompt.")
                break
            else:
                print_red("Opción inválida.")

    #-------------------------------------------------------------
    # Panel XFCE
    #-------------------------------------------------------------
    def setup_xfce_panel(self):
        print_banner("         <============================= Setting round edges of XFCE bar ==============================>")

        gtk_dir = self.home / ".config/gtk-3.0"
        gtk_dir.mkdir(parents=True, exist_ok=True)
        gtk_css = gtk_dir / "gtk.css"

        existing = gtk_css.read_text(errors="replace") if gtk_css.is_file() else ""
        if ".xfce4-panel {" not in existing:
            with open(gtk_css, "a") as fh:
                fh.write(ROUND_CSS)

    #-------------------------------------------------------------
    # Fondos de pantalla
    #-------------------------------------------------------------
    def get_pictures_dir(self):
        pictures = None
        if shutil.which("xdg-user-dir"):
            try:
                result = subprocess.run(["xdg-user-dir", "PICTURES"],
                                        capture_output=True, text=True)
                if result.stdout.strip():
                    pictures = Path(result.stdout.strip())
            except Exception:
                pictures = None
        if pictures is None:
            pictures = self.home / "Pictures"
        if not pictures.is_dir() and (self.home / "Imágenes").is_dir():
            pictures = self.home / "Imágenes"
        pictures.mkdir(parents=True, exist_ok=True)
        return pictures

    def set_wallpaper(self, img):
        try:
            props = subprocess.run(["xfconf-query", "-c", "xfce4-desktop", "-l"],
                                   capture_output=True, text=True).stdout.splitlines()
        except Exception:
            props = []
        last_image = [p for p in props if "/last-image" in p]
        if not last_image:
            self.run(["xfconf-query", "-c", "xfce4-desktop",
                      "-p", "/backdrop/screen0/monitor0/workspace0/last-image",
                      "-s", str(img)])
            return
        for prop in last_image:
            self.run(["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(img)])

    def install_wallpapers(self):
        print_banner("         <=========================== Downloading cool wallpapers ================================>")

        pictures = self.get_pictures_dir()
        wall_dir = self.work_dir / "Wallpapers"
        if not wall_dir.is_dir():
            self.run(["git", "clone", "--depth=1", WALLPAPERS_REPO, str(wall_dir)])

        if wall_dir.is_dir():
            for item in wall_dir.iterdir():
                dest = pictures / item.name
                try:
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
                except Exception as exc:
                    print_red(f"No se pudo copiar {item.name}: {exc}")

        default_wall = pictures / "50.jpg"
        if shutil.which("xfconf-query") and default_wall.is_file():
            self.set_wallpaper(default_wall)
        elif not shutil.which("xfconf-query"):
            print_yellow("xfconf-query no disponible; configura el fondo manualmente.")

    #-------------------------------------------------------------
    # Iconos
    #-------------------------------------------------------------
    def install_icon_dir(self, src, name):
        src = Path(src) if src else None
        if src is None or not src.is_dir():
            print_red(f"No se encontró el directorio del tema de iconos '{name}'.")
            return False
        target = self.home / ".local/share/icons" / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)
        print_green(f"Tema de iconos '{name}' instalado en {target.parent}.")
        return True

    def install_candy_icons(self):
        base = self.work_dir / "candy-icons"
        base.mkdir(parents=True, exist_ok=True)
        zip_path = base / "master.zip"
        if not self.download(CANDY_ICONS_URL, zip_path):
            print_red("No se pudieron descargar los Candy Icons.")
            return False
        try:
            self.extract_zip(zip_path, base)
        except Exception as exc:
            print_red(f"No se pudieron extraer los Candy Icons: {exc}")
            return False
        candidates = sorted(base.glob("candy-icons-*"))
        if not candidates:
            print_red("No se encontró el directorio de Candy Icons.")
            return False
        return self.install_icon_dir(candidates[0], "candy-icons")

    def install_beautybeam(self):
        base = self.work_dir / "beautybeam"
        base.mkdir(parents=True, exist_ok=True)

        try:
            req = urllib.request.Request(BEAUTYBEAM_API,
                                         headers={"User-Agent": "post-install-xfce"})
            with urllib.request.urlopen(req) as response:
                xml = response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            print_red(f"No se pudo consultar la API de BeautyBeam: {exc}")
            return False

        match = re.search(r"<downloadlink1>([^<]*)</downloadlink1>", xml)
        if not match:
            print_red("No se pudo obtener el enlace de descarga de BeautyBeam.")
            return False
        url = match.group(1)

        tar_path = base / "BeautyBeam.tar.gz"
        if not self.download(url, tar_path):
            print_red("No se pudo descargar BeautyBeam.")
            return False
        try:
            self.extract_tar(tar_path, base)
        except Exception as exc:
            print_red(f"No se pudo extraer BeautyBeam: {exc}")
            return False

        theme_dir = None
        for index_theme in base.rglob("index.theme"):
            theme_dir = index_theme.parent
            break
        return self.install_icon_dir(theme_dir, "BeautyBeam")

    def select_icon_theme(self):
        print_banner("          <=========================== Selecting icon theme ====================================>")

        self.home_icons = self.home / ".local/share/icons"
        self.home_icons.mkdir(parents=True, exist_ok=True)

        if not sys.stdin.isatty():
            print_yellow("Ejecución no interactiva: se instalarán Candy Icons por defecto.")
            if self.install_candy_icons():
                self.selected_icon_theme = "candy-icons"
            return

        while True:
            print()
            print("  Elige el set de iconos:")
            print("    1) Candy Icons - coloridos y redondeados (recomendado)")
            print("    2) BeautyBeam  - con degradados, ideal para temas oscuros")
            print("    3) Omitir este paso")
            choice = input("  Opción [1]: ").strip() or "1"

            if choice == "1":
                if input("  ¿Instalar Candy Icons? [S/n]: ").strip().lower() == "n":
                    continue
                if self.install_candy_icons():
                    self.selected_icon_theme = "candy-icons"
                break
            elif choice == "2":
                if input("  ¿Instalar BeautyBeam? [S/n]: ").strip().lower() == "n":
                    continue
                if self.install_beautybeam():
                    self.selected_icon_theme = "BeautyBeam"
                break
            elif choice == "3":
                print_yellow("Se omitió la instalación de iconos.")
                break
            else:
                print_red("Opción inválida.")

    #-------------------------------------------------------------
    # Tema Adwaita-dark e iconos
    #-------------------------------------------------------------
    def setup_theme(self):
        print_banner("           <======================= Setting up Adwaita Dark Theme ================================>")

        if not shutil.which("xfconf-query"):
            print_yellow("xfconf-query no disponible; ajusta el tema manualmente.")
            return

        if subprocess.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            self.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName",
                      "-s", "Adwaita-dark"])
        else:
            self.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName",
                      "-s", "Adwaita-dark", "--create", "-t", "string"])

        if self.selected_icon_theme:
            if subprocess.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                self.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName",
                          "-s", self.selected_icon_theme])
            else:
                self.run(["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName",
                          "-s", self.selected_icon_theme, "--create", "-t", "string"])

    #-------------------------------------------------------------
    # Shell por defecto: zsh
    #-------------------------------------------------------------
    def set_default_shell(self):
        zsh_bin = shutil.which("zsh")
        if not zsh_bin:
            print_red("zsh no está instalado, no se cambió el shell.")
            return
        try:
            current = pwd.getpwuid(os.getuid()).pw_shell
        except KeyError:
            current = ""
        if current == zsh_bin:
            return
        result = self.run(["sudo", "chsh", "-s", zsh_bin, pwd.getpwuid(os.getuid()).pw_name])
        if result is not None and result.returncode == 0:
            print_green("Shell por defecto cambiado a zsh.")
        else:
            print_red("No se pudo cambiar el shell por defecto.")

    #-------------------------------------------------------------
    # Flujo principal
    #-------------------------------------------------------------
    def _setup_log(self):
        self._logfile = open(self.log_path, "a")
        sys.stdout = Tee(sys.__stdout__, self._logfile)
        sys.stderr = Tee(sys.__stderr__, self._logfile)

    def _check_user(self):
        if os.geteuid() == 0:
            print_red("# Dont't run this script as root. No ejecutar como root #.")
            sys.exit(1)
        if os.environ.get("SUDO_USER"):
            print_red("# No uses sudo para lanzar el script. Don't use sudo to run this script #")
            sys.exit(1)

    def install_dependencies(self):
        print_banner("             《·───────────────·》 SCRIPT POST INSTALL XFCE 《·───────────────·》")

        self.ensure_cmd("git", "git")
        self.ensure_cmd("wget", "wget")
        self.ensure_cmd("unzip", "unzip")
        self.ensure_cmd("zsh", "zsh")
        self.ensure_cmd("curl", "curl")
        self.ensure_cmd("lsd", "lsd")
        self.ensure_cmd("less", "less")
        self.ensure_cmd("tar", "tar")
        self.ensure_cmd("fc-cache", "fontconfig", "fontconfig1")

        if not shutil.which("lolcat"):
            cmd = INSTALL_CMDS[self.pkg_manager] + ["lolcat"]
            if self.run(cmd).returncode != 0:
                print_yellow("lolcat no disponible en los repositorios; se usará salida sin color.")

    def run_all(self):
        self._setup_log()
        self._check_user()
        self.detect_distro()
        self.detect_pkg_manager()

        self.install_dependencies()
        self.install_fonts()
        self.select_shell_prompt()
        self.setup_xfce_panel()
        self.install_wallpapers()
        self.select_icon_theme()
        self.setup_theme()
        self.set_default_shell()

        for line in FINAL_MESSAGES:
            print_banner(line)

    def cleanup(self):
        shutil.rmtree(self.work_dir, ignore_errors=True)
        if self._logfile:
            self._logfile.close()


def main():
    app = PostInstall()
    try:
        app.run_all()
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
