import os
import sys
import shutil
import threading
import subprocess
import urllib.request
import urllib.error
import ctypes
import time
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path

# --- CONFIGURACIÓN ---
GITHUB_INI_URL = "https://raw.githubusercontent.com/IzMileZ/the-sims-4/refs/heads/main/g_The%20Sims%204.ini"
INI_TS4 = "g_The Sims 4.ini"
INI_TS3 = "g_The Sims 3.ini"
CONFIG_INI = "config.ini"
VERSION_DLL = "version.dll"

# Directorio exacto donde anadius unlocker busca sus configuraciones
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser("~")), 'anadius', 'EA DLC Unlocker v2')

# Posibles ubicaciones donde el unlocker puede haber instalado el DLL
EA_APP_PATHS = [
    os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'EA Games', 'EA app', 'EA Desktop', 'EA Desktop'),
    os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'EA Games', 'EA app', 'EA Desktop', 'EA Desktop'),
    os.path.join(os.environ.get('LocalAppData', os.environ.get('USERPROFILE', '')), 'Programs', 'EA app', 'EA Desktop', 'EA Desktop'),
]

ORIGIN_PATHS = [
    os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'Origin'),
    os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'Origin'),
]

def get_base_dir():
    """Obtiene el directorio base del ejecutable o script."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def is_admin():
    """Verifica si el programa se ejecuta como administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Reinicia el programa con permisos de administrador."""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

class UnlockerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Unlocker Pro Auto-Setup")
        self.geometry("680x480")
        self.resizable(False, False)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)

        # --- Panel Izquierdo ---
        self.left_panel = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray85", "gray16"))
        self.left_panel.grid(row=0, column=0, sticky="nsew")
        self.left_panel.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self.left_panel, 
            text="Instrucciones", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        instrucciones_texto = (
            "1. Selecciona los juegos\n"
            "   que deseas desbloquear.\n\n"
            "2. El programa instalará el\n"
            "   Unlocker base y luego\n"
            "   añadirá las configs.\n\n"
            "   (The Sims 4 se bajará\n"
            "   siempre actualizado\n"
            "   desde GitHub).\n\n"
            "3. Haz clic en 'Instalar'\n"
            "   para iniciar.\n\n"
            "   ✓ 100% automático.\n\n"
            "   ⚠ Se requieren permisos\n"
            "     de Administrador\n\n"
            "   🗑️ Usa 'Desinstalar' para\n"
            "     eliminar el Unlocker"
        )
        self.info_label = ctk.CTkLabel(
            self.left_panel, 
            text=instrucciones_texto, 
            justify="left",
            font=ctk.CTkFont(size=13)
        )
        self.info_label.grid(row=1, column=0, padx=20, pady=10, sticky="n")

        # --- Panel Derecho ---
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.right_panel.grid_rowconfigure(0, weight=0) 
        self.right_panel.grid_rowconfigure(1, weight=1) 
        self.right_panel.grid_rowconfigure(2, weight=0) 
        self.right_panel.grid_rowconfigure(3, weight=0) 
        self.right_panel.grid_rowconfigure(4, weight=0)
        self.right_panel.grid_rowconfigure(5, weight=1) 

        # Opciones (Checkboxes)
        self.options_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.options_frame.grid(row=0, column=0, pady=(0, 10), sticky="n")

        self.sims4_var = ctk.BooleanVar(value=True)
        self.sims3_var = ctk.BooleanVar(value=False)

        self.chk_sims4 = ctk.CTkCheckBox(
            self.options_frame, 
            text="The Sims 4 (Auto-update nube)", 
            variable=self.sims4_var,
            font=ctk.CTkFont(weight="bold")
        )
        self.chk_sims4.grid(row=0, column=0, pady=10, sticky="w")

        self.chk_sims3 = ctk.CTkCheckBox(
            self.options_frame, 
            text="The Sims 3 (Archivo local)", 
            variable=self.sims3_var,
            font=ctk.CTkFont(weight="bold")
        )
        self.chk_sims3.grid(row=1, column=0, pady=10, sticky="w")

        self.status_label = ctk.CTkLabel(
            self.right_panel, 
            text="Selecciona tus juegos y presiona Instalar.", 
            font=ctk.CTkFont(size=14),
            wraplength=350
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="s")

        self.progressbar = ctk.CTkProgressBar(self.right_panel, mode="indeterminate", width=250)
        self.progressbar.grid(row=2, column=0, padx=20, pady=10)
        self.progressbar.set(0)
        self.progressbar.grid_remove() 

        # Frame para botones
        self.button_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.button_frame.grid(row=3, column=0, padx=20, pady=10)

        self.install_button = ctk.CTkButton(
            self.button_frame, 
            text="📦 Instalar", 
            command=self.start_process_thread,
            font=ctk.CTkFont(size=15, weight="bold"),
            height=45,
            width=180,
            fg_color="#2e7d32",
            hover_color="#1b5e20"
        )
        self.install_button.grid(row=0, column=0, padx=5)

        self.uninstall_button = ctk.CTkButton(
            self.button_frame, 
            text="🗑️ Desinstalar", 
            command=self.start_uninstall_thread,
            font=ctk.CTkFont(size=15, weight="bold"),
            height=45,
            width=180,
            fg_color="#c62828",
            hover_color="#8e0000"
        )
        self.uninstall_button.grid(row=0, column=1, padx=5)

        # Estado de instalación
        self.status_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.status_frame.grid(row=4, column=0, pady=10)

        self.install_status_label = ctk.CTkLabel(
            self.status_frame,
            text="",
            font=ctk.CTkFont(size=12)
        )
        self.install_status_label.grid(row=0, column=0)

        # Actualizar estado al iniciar
        self.update_installation_status()

    def log_status(self, text):
        """Actualiza el label de estado."""
        self.status_label.configure(text=text)
        self.update_idletasks()

    def update_installation_status(self):
        """Verifica y muestra si el unlocker está instalado."""
        is_installed = self.check_if_unlocker_installed()
        if is_installed:
            self.install_status_label.configure(
                text="✅ Unlocker detectado en el sistema",
                text_color="green"
            )
        else:
            self.install_status_label.configure(
                text="❌ Unlocker no detectado",
                text_color="red"
            )

    def check_if_unlocker_installed(self):
        """Verifica si el unlocker está instalado en alguna ubicación."""
        # Verificar en EA App paths
        for path in EA_APP_PATHS:
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                return True
        
        # Verificar en Origin paths
        for path in ORIGIN_PATHS:
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                return True
        
        return False

    def find_unlocker_locations(self):
        """Encuentra todas las ubicaciones donde está instalado el unlocker."""
        locations = []
        
        # Buscar en EA App
        for path in EA_APP_PATHS:
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                locations.append(dll_path)
        
        # Buscar en Origin
        for path in ORIGIN_PATHS:
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                locations.append(dll_path)
        
        # Verificar también en directorio de configuración
        config_dll = os.path.join(APPDATA_DIR, VERSION_DLL)
        if os.path.exists(config_dll):
            locations.append(config_dll)
        
        return locations

    # 🔧 CORREGIDO: Ahora es método de la clase (con self)
    def find_dll_file(self):
        """Busca el archivo version.dll en múltiples ubicaciones posibles."""
        base_dir = get_base_dir()
        
        # Posibles ubicaciones del DLL (orden de búsqueda)
        possible_paths = [
            # Dentro de las carpetas específicas
            os.path.join(base_dir, "ea_app", VERSION_DLL),
            os.path.join(base_dir, "origin", VERSION_DLL),
            # En la raíz
            os.path.join(base_dir, VERSION_DLL),
            # En subcarpetas (por si acaso)
            os.path.join(base_dir, "EA App", VERSION_DLL),
            os.path.join(base_dir, "Origin", VERSION_DLL),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ DLL encontrado en: {path}")
                return path
        
        # Si no encuentra, lanza error con información útil
        error_msg = f"No se encontró {VERSION_DLL} en:\n"
        for path in possible_paths[:4]:  # Mostrar solo las primeras 4 rutas
            error_msg += f"- {path}\n"
        raise FileNotFoundError(error_msg)

    def check_admin_and_continue(self):
        """Verifica permisos de admin antes de continuar."""
        if not is_admin():
            response = messagebox.askyesno(
                "Permisos de Administrador",
                "Esta operación necesita permisos de administrador.\n\n"
                "¿Deseas reiniciar con permisos de administrador?"
            )
            if response:
                run_as_admin()
            else:
                return False
        return True

    def start_process_thread(self):
        """Inicia el proceso de instalación en un hilo separado."""
        if not self.sims4_var.get() and not self.sims3_var.get():
            messagebox.showwarning("Atención", "¡Selecciona al menos un juego para desbloquear!")
            return
        
        # Verificar permisos de administrador
        if not self.check_admin_and_continue():
            return
        
        # Confirmar instalación
        if self.check_if_unlocker_installed():
            response = messagebox.askyesno(
                "Unlocker Detectado",
                "El Unlocker ya está instalado en el sistema.\n\n"
                "¿Deseas reinstalarlo?"
            )
            if not response:
                return
            
        self.install_button.configure(state="disabled")
        self.uninstall_button.configure(state="disabled")
        self.chk_sims4.configure(state="disabled")
        self.chk_sims3.configure(state="disabled")
        self.progressbar.grid()
        self.progressbar.start()
        
        thread = threading.Thread(target=self.run_install_process, daemon=True)
        thread.start()

    def start_uninstall_thread(self):
        """Inicia el proceso de desinstalación en un hilo separado."""
        # Verificar si hay algo que desinstalar
        if not self.check_if_unlocker_installed():
            messagebox.showinfo("Información", "No se encontró el Unlocker instalado en el sistema.")
            return
        
        # Verificar permisos de administrador
        if not self.check_admin_and_continue():
            return
        
        # Confirmar desinstalación
        response = messagebox.askyesno(
            "Confirmar Desinstalación",
            "¿Estás seguro de que deseas desinstalar el Unlocker?\n\n"
            "Esto eliminará todos los archivos del Unlocker y sus configuraciones.\n"
            "Los juegos volverán a su estado original sin DLCs desbloqueados.",
            icon="warning"
        )
        if not response:
            return
        
        self.install_button.configure(state="disabled")
        self.uninstall_button.configure(state="disabled")
        self.chk_sims4.configure(state="disabled")
        self.chk_sims3.configure(state="disabled")
        self.progressbar.grid()
        self.progressbar.start()
        
        thread = threading.Thread(target=self.run_uninstall_process, daemon=True)
        thread.start()

    def run_install_process(self):
        """Ejecuta el proceso de instalación."""
        try:
            # PASO 1: Verificar archivos - 🔧 CORREGIDO: ahora usa self.find_dll_file()
            self.log_status("Verificando archivos del Unlocker...")
            dll_path = self.find_dll_file()  # ✅ AHORA SÍ con self
            self.log_status(f"✅ DLL encontrado: {os.path.basename(os.path.dirname(dll_path)) if 'ea_app' in dll_path or 'origin' in dll_path else 'raíz'}")

            # PASO 2: Crear directorio de configuración
            self.log_status("Creando directorio de configuración...")
            os.makedirs(APPDATA_DIR, exist_ok=True)

            # PASO 3: Copiar config.ini
            self.log_status("Copiando configuración del Unlocker...")
            self.install_local_file(CONFIG_INI, APPDATA_DIR)

            # PASO 4: Ejecutar setup.bat (necesita el DLL en la misma carpeta)
            self.log_status("Preparando archivos para instalación...")
            
            # Copiar el DLL encontrado al directorio base temporal si es necesario
            base_dir = get_base_dir()
            dll_dest = os.path.join(base_dir, VERSION_DLL)
            
            # Si el DLL no está en la raíz, lo copiamos temporalmente
            if not os.path.exists(dll_dest):
                shutil.copy2(dll_path, dll_dest)
                self.log_status("✅ DLL copiado temporalmente a la raíz")
            
            # Ejecutar setup.bat
            self.log_status("Instalando el Unlocker en EA App/Origin...")
            self.run_setup_bat_install()

            # PASO 5: Configurar juegos
            time.sleep(2)
            
            if self.sims4_var.get():
                self.log_status("Actualizando config de The Sims 4...")
                self.check_and_update_ini(INI_TS4, GITHUB_INI_URL)

            if self.sims3_var.get():
                self.log_status("Instalando config de The Sims 3...")
                self.install_local_file(INI_TS3, APPDATA_DIR)

            # PASO 6: Limpiar DLL temporal si lo copiamos
            if os.path.exists(dll_dest) and dll_dest != dll_path:
                try:
                    os.remove(dll_dest)
                except:
                    pass  # No importa si no se puede eliminar

            # PASO 7: Verificar instalación
            self.log_status("Verificando instalación...")
            self.verify_installation()

            self.log_status("¡Instalación completada con éxito!")
            self.update_installation_status()
            
            messagebox.showinfo(
                "Éxito", 
                "El Unlocker y las configuraciones se instalaron correctamente.\n\n"
                "Al abrir tu juego, los DLCs estarán disponibles.\n\n"
                "Si el juego no detecta los DLCs, reinicia tu PC."
            )
            
        except Exception as e:
            self.log_status("Error en la instalación.")
            self.show_error_message(e)
        finally:
            self.progressbar.stop()
            self.progressbar.grid_remove()
            self.install_button.configure(state="normal")
            self.uninstall_button.configure(state="normal")
            self.chk_sims4.configure(state="normal")
            self.chk_sims3.configure(state="normal")

    def run_uninstall_process(self):
        """Ejecuta el proceso de desinstalación."""
        try:
            # PASO 1: Encontrar ubicaciones del unlocker
            self.log_status("Buscando instalaciones del Unlocker...")
            locations = self.find_unlocker_locations()
            
            if not locations:
                self.log_status("No se encontró el Unlocker.")
                return

            # PASO 2: Eliminar archivos DLL
            self.log_status("Eliminando archivos del Unlocker...")
            for dll_path in locations:
                try:
                    os.remove(dll_path)
                    self.log_status(f"✓ Eliminado: {dll_path}")
                except Exception as e:
                    self.log_status(f"⚠ No se pudo eliminar: {dll_path}")

            # PASO 3: Ejecutar setup.bat con uninstall si existe
            base_dir = get_base_dir()
            bat_path = os.path.join(base_dir, "setup.bat")
            
            if os.path.exists(bat_path):
                self.log_status("Ejecutando limpieza con setup.bat...")
                try:
                    process = subprocess.Popen(
                        [bat_path, "uninstall"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=base_dir,
                        shell=True,
                        universal_newlines=True
                    )
                    process.communicate(timeout=30)
                except:
                    pass

            # PASO 4: Preguntar si eliminar configuraciones
            response = messagebox.askyesno(
                "Eliminar Configuraciones",
                "¿Deseas eliminar también las configuraciones del Unlocker?\n\n"
                "Esto borrará todos los archivos .ini guardados."
            )
            
            if response:
                self.log_status("Eliminando configuraciones...")
                if os.path.exists(APPDATA_DIR):
                    try:
                        shutil.rmtree(APPDATA_DIR)
                        self.log_status("✓ Configuraciones eliminadas")
                    except Exception as e:
                        self.log_status(f"⚠ No se pudo eliminar configuraciones: {e}")

            # PASO 5: Verificar resultado
            self.log_status("Verificando desinstalación...")
            time.sleep(1)
            
            if self.check_if_unlocker_installed():
                self.log_status("⚠ Algunos archivos no pudieron ser eliminados")
                remaining = self.find_unlocker_locations()
                if remaining:
                    messagebox.showwarning(
                        "Desinstalación Parcial",
                        f"Algunos archivos no pudieron ser eliminados:\n\n" +
                        "\n".join(remaining) +
                        "\n\nPuedes eliminarlos manualmente o reiniciar tu PC e intentar de nuevo."
                    )
            else:
                self.log_status("✓ Unlocker desinstalado correctamente")
                self.update_installation_status()
                messagebox.showinfo(
                    "Éxito",
                    "El Unlocker ha sido desinstalado correctamente.\n\n"
                    "Los juegos volverán a su estado original."
                )
            
        except Exception as e:
            self.log_status("Error en la desinstalación.")
            self.show_error_message(e)
        finally:
            self.progressbar.stop()
            self.progressbar.grid_remove()
            self.install_button.configure(state="normal")
            self.uninstall_button.configure(state="normal")
            self.chk_sims4.configure(state="normal")
            self.chk_sims3.configure(state="normal")
            self.update_installation_status()

    def show_error_message(self, error):
        """Muestra mensaje de error formateado."""
        error_msg = f"Se produjo un error:\n\n{str(error)}"
        
        if "Acceso denegado" in str(error) or "Permission denied" in str(error):
            error_msg += "\n\nEsto puede deberse a falta de permisos de administrador o antivirus bloqueando la operación."
        elif "No se encontró" in str(error) and "version.dll" in str(error):
            error_msg += "\n\nAsegúrate de que el archivo version.dll está en la carpeta 'ea_app' o 'origin' junto al programa."
        
        messagebox.showerror("Error", error_msg)

    def verify_unlocker_files(self):
        """Verifica que todos los archivos necesarios existen (versión mejorada)."""
        try:
            # 🔧 CORREGIDO: ahora usa self.find_dll_file()
            dll_path = self.find_dll_file()  # ✅ AHORA SÍ con self
            self.log_status(f"✅ DLL encontrado en: {os.path.dirname(dll_path)}")
            
            # Verificar otros archivos
            base_dir = get_base_dir()
            required_files = ["setup.bat", CONFIG_INI]
            missing_files = []
            
            for file in required_files:
                if not os.path.exists(os.path.join(base_dir, file)):
                    # Intentar buscar en carpetas alternativas
                    alt_path = os.path.join(base_dir, "ea_app", file)
                    if not os.path.exists(alt_path):
                        alt_path = os.path.join(base_dir, "origin", file)
                    
                    if not os.path.exists(alt_path):
                        missing_files.append(file)
            
            if missing_files:
                raise FileNotFoundError(
                    f"Archivos requeridos no encontrados: {', '.join(missing_files)}"
                )
                
        except FileNotFoundError as e:
            raise e

    def run_setup_bat_install(self):
        """Ejecuta setup.bat con el argumento 'install'."""
        base_dir = get_base_dir()
        bat_path = os.path.join(base_dir, "setup.bat")
        log_path = os.path.join(os.environ.get('TEMP', base_dir), "unlocker_install_log.txt")
        
        try:
            process = subprocess.Popen(
                [bat_path, "install"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=base_dir,
                shell=True,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate(timeout=60)
            
            with open(log_path, "w", encoding="utf-8") as log_f:
                log_f.write(f"Comando: {bat_path} install\n")
                log_f.write(f"CWD: {base_dir}\n")
                log_f.write(f"Return code: {process.returncode}\n\n")
                log_f.write(f"--- STDOUT ---\n{stdout}\n\n--- STDERR ---\n{stderr}")
            
            if process.returncode != 0:
                error_msg = f"setup.bat terminó con código de error: {process.returncode}"
                if "Acceso denegado" in stderr:
                    error_msg += "\n\nPosible falta de permisos de administrador."
                raise Exception(error_msg)
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("setup.bat tardó demasiado. Puede que el antivirus lo esté bloqueando.")
        except Exception as e:
            raise Exception(f"Fallo al ejecutar setup.bat install:\n{str(e)}")

    def verify_installation(self):
        """Verifica que la instalación se completó correctamente."""
        ini_files_copied = []
        
        if self.sims4_var.get():
            ts4_ini_path = os.path.join(APPDATA_DIR, INI_TS4)
            if os.path.exists(ts4_ini_path):
                ini_files_copied.append(f"✓ {INI_TS4}")
        
        if self.sims3_var.get():
            ts3_ini_path = os.path.join(APPDATA_DIR, INI_TS3)
            if os.path.exists(ts3_ini_path):
                ini_files_copied.append(f"✓ {INI_TS3}")
        
        config_ini_path = os.path.join(APPDATA_DIR, CONFIG_INI)
        if os.path.exists(config_ini_path):
            ini_files_copied.append(f"✓ {CONFIG_INI}")
        
        if ini_files_copied:
            self.log_status(f"Archivos instalados: {', '.join(ini_files_copied)}")

    def check_and_update_ini(self, filename, url):
        """Descarga el .ini desde GitHub y lo instala."""
        target_path = os.path.join(APPDATA_DIR, filename)
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 UnlockerBot/1.0'})
            response = urllib.request.urlopen(req, timeout=10)
            content = response.read()
            
            with open(target_path, 'wb') as f:
                f.write(content)
            self.log_status(f"✓ {filename} actualizado desde GitHub")
            
        except urllib.error.URLError:
            print(f"[!] Sin internet. Usando versión local de {filename}")
            self.install_local_file(filename, APPDATA_DIR)
        except Exception as e:
            print(f"[!] Error descargando {filename}: {e}")
            self.install_local_file(filename, APPDATA_DIR)

    def install_local_file(self, filename, target_dir):
        """Copia un archivo empaquetado al directorio destino."""
        base_dir = get_base_dir()
        
        # Buscar el archivo en múltiples ubicaciones
        possible_sources = [
            os.path.join(base_dir, filename),
            os.path.join(base_dir, "ea_app", filename),
            os.path.join(base_dir, "origin", filename),
        ]
        
        source_path = None
        for path in possible_sources:
            if os.path.exists(path):
                source_path = path
                break
        
        if not source_path:
            raise FileNotFoundError(
                f"No se encontró el archivo '{filename}'\n"
                f"Buscado en:\n" + "\n".join(possible_sources)
            )
        
        target_path = os.path.join(target_dir, filename)
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(source_path, target_path)
        
        if not os.path.exists(target_path):
            raise Exception(f"Error al copiar {filename} a {target_dir}")
        
        self.log_status(f"✓ {filename} copiado correctamente")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue") 
    
    app = UnlockerApp()
    app.mainloop()
