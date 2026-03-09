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

# Posibles ubicaciones donde el unlocker PUEDE estar instalado (sistema)
def get_ea_app_paths():
    """Obtiene rutas de EA App (versión corregida)"""
    program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    local_app_data = os.environ.get('LocalAppData', '')
    
    paths = [
        # Ruta principal de EA Desktop (la correcta)
        os.path.join(program_files, 'Electronic Arts', 'EA Desktop', 'EA Desktop'),
        os.path.join(program_files_x86, 'Electronic Arts', 'EA Desktop', 'EA Desktop'),
        # También mantener la ruta antigua por si acaso (algunas versiones antiguas)
        os.path.join(program_files, 'EA Games', 'EA Desktop'),
        os.path.join(program_files_x86, 'EA Games', 'EA Desktop'),
    ]
    
    if local_app_data:
        paths.append(os.path.join(local_app_data, 'Programs', 'EA Desktop'))
    
    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique_paths = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    return unique_paths

def get_origin_paths():
    """Obtiene rutas de Origin (sin filtrar)"""
    program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
    program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    
    return [
        os.path.join(program_files_x86, 'Origin'),
        os.path.join(program_files, 'Origin'),
    ]

def get_base_dir():
    """Obtiene el directorio base donde están los ARCHIVOS EMPAQUETADOS."""
    if getattr(sys, 'frozen', False):
        # Cuando está empaquetado con PyInstaller, los archivos están en _MEIPASS
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_executable_dir():
    """Obtiene el directorio DONDE ESTÁ EL EJECUTABLE (no los archivos temporales)"""
    if getattr(sys, 'frozen', False):
        # El ejecutable está en una carpeta temporal, pero necesitamos la ubicación REAL
        return os.path.dirname(sys.executable)
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
            "   Unlocker base (si no está)\n"
            "   y añadirá las configs.\n\n"
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
        is_installed = self.is_unlocker_installed()
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

    def is_unlocker_installed(self):
        """Verifica si el unlocker está instalado en alguna ubicación del sistema."""
        return self.find_installed_dll() is not None

    def find_installed_dll(self):
        """Busca el DLL YA INSTALADO en el sistema (EA App/Origin)"""
        # Buscar en EA App
        for path in get_ea_app_paths():
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                print(f"✅ DLL instalado encontrado en EA App: {dll_path}")
                return dll_path
        
        # Buscar en Origin
        for path in get_origin_paths():
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                print(f"✅ DLL instalado encontrado en Origin: {dll_path}")
                return dll_path
        
        return None

    def get_packaged_dll(self):
        """Obtiene el DLL DESDE EL PAQUETE (para instalación inicial)"""
        base_dir = get_base_dir()
        exe_dir = get_executable_dir()
        
        possible_paths = [
            # Buscar en el paquete (cuando está empaquetado)
            os.path.join(base_dir, "ea_app", VERSION_DLL),
            os.path.join(base_dir, "origin", VERSION_DLL),
            os.path.join(base_dir, VERSION_DLL),
            # Buscar junto al ejecutable (por si acaso)
            os.path.join(exe_dir, "ea_app", VERSION_DLL),
            os.path.join(exe_dir, "origin", VERSION_DLL),
            os.path.join(exe_dir, VERSION_DLL),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ DLL encontrado en paquete: {path}")
                return path
        
        return None

    def find_unlocker_locations(self):
        """Encuentra todas las ubicaciones donde está instalado el unlocker (para desinstalar)."""
        locations = []
        
        # Buscar en EA App
        for path in get_ea_app_paths():
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                locations.append(dll_path)
        
        # Buscar en Origin
        for path in get_origin_paths():
            dll_path = os.path.join(path, VERSION_DLL)
            if os.path.exists(dll_path):
                locations.append(dll_path)
        
        return locations

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
        
        # Confirmar instalación/reinstalación
        if self.is_unlocker_installed():
            response = messagebox.askyesno(
                "Unlocker Detectado",
                "El Unlocker ya está instalado en el sistema.\n\n"
                "¿Deseas reinstalarlo o solo actualizar las configuraciones?"
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
        if not self.is_unlocker_installed():
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
            # PASO 1: Verificar si el unlocker YA está instalado en el sistema
            self.log_status("Verificando instalación existente...")
            installed_dll = self.find_installed_dll()
            
            if not installed_dll:
                # El unlocker NO está instalado, necesitamos instalarlo desde nuestro paquete
                self.log_status("Unlocker base no detectado. Instalando desde paquete...")
                
                # Verificar que tenemos el DLL en nuestro paquete
                dll_source = self.get_packaged_dll()
                if not dll_source:
                    raise FileNotFoundError(
                        f"No se encontró {VERSION_DLL} en el paquete.\n"
                        "Asegúrate de que los archivos están en las carpetas 'ea_app' y 'origin'."
                    )
                
                # Preparar para instalación - usar directorio temporal
                temp_dir = os.environ.get('TEMP', os.path.expanduser("~"))
                temp_dll = os.path.join(temp_dir, VERSION_DLL)
                
                # Copiar el DLL al directorio temporal para setup.bat
                self.log_status("Preparando archivos para instalación...")
                shutil.copy2(dll_source, temp_dll)
                
                # Ejecutar setup.bat para instalar
                self.log_status("Instalando el Unlocker en EA App/Origin...")
                success = self.run_setup_bat_install()
                
                # Limpiar archivo temporal
                if os.path.exists(temp_dll):
                    try:
                        os.remove(temp_dll)
                    except:
                        pass
                
                if success:
                    self.log_status("✅ Unlocker instalado correctamente")
                    # Pequeña pausa para que el sistema registre los cambios
                    time.sleep(2)
                else:
                    raise Exception("setup.bat no completó la instalación correctamente")
            else:
                self.log_status(f"✅ Unlocker ya instalado en: {os.path.dirname(installed_dll)}")
            
            # PASO 2: Crear directorio de configuración (siempre)
            self.log_status("Creando directorio de configuración...")
            os.makedirs(APPDATA_DIR, exist_ok=True)
            
            # PASO 3: Copiar config.ini (siempre)
            self.log_status("Copiando configuración base del Unlocker...")
            self.install_local_file(CONFIG_INI, APPDATA_DIR)
            
            # PASO 4: Configurar juegos seleccionados
            time.sleep(1)  # Pequeña pausa para que el usuario vea el progreso
            
            if self.sims4_var.get():
                self.log_status("Actualizando/configurando The Sims 4...")
                self.check_and_update_ini(INI_TS4, GITHUB_INI_URL)
            
            if self.sims3_var.get():
                self.log_status("Instalando configuración de The Sims 3...")
                self.install_local_file(INI_TS3, APPDATA_DIR)
            
            # PASO 5: Verificar instalación de configuraciones
            self.log_status("Verificando archivos de configuración...")
            self.verify_config_files()
            
            # PASO 6: VERIFICAR NUEVAMENTE SI EL UNLOCKER ESTÁ INSTALADO
            self.log_status("Verificando instalación final...")
            time.sleep(1)
            self.update_installation_status()
            
            if self.is_unlocker_installed():
                self.log_status("¡Instalación completada con éxito!")
                messagebox.showinfo(
                    "Éxito", 
                    "El Unlocker y las configuraciones se instalaron correctamente.\n\n"
                    "Al abrir tu juego, los DLCs estarán disponibles.\n\n"
                    "Si el juego no detecta los DLCs, reinicia tu PC y asegúrate de que\n"
                    "el antivirus no haya bloqueado el archivo version.dll."
                )
            else:
                self.log_status("⚠ Instalación completada pero no se detectó el Unlocker")
                messagebox.showwarning(
                    "Verificación",
                    "La instalación de configuraciones se completó, pero no se detecta el Unlocker.\n\n"
                    "Esto puede deberse a:\n"
                    "- El antivirus bloqueó la instalación del DLL\n"
                    "- EA App/Origin no está instalado en la ubicación esperada\n\n"
                    "Puedes intentar ejecutar como administrador o desactivar el antivirus temporalmente."
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
                # Aún así, preguntar si quiere eliminar configuraciones
                self.ask_delete_configs_only()
                return

            # PASO 2: Ejecutar setup.bat con uninstall primero (más limpio)
            self.log_status("Ejecutando desinstalación con setup.bat...")
            
            # Para setup.bat, usamos el directorio temporal
            temp_dir = os.environ.get('TEMP', os.path.expanduser("~"))
            temp_dll = os.path.join(temp_dir, VERSION_DLL)
            
            # Necesitamos el DLL para la desinstalación también
            dll_source = self.get_packaged_dll()
            if dll_source:
                shutil.copy2(dll_source, temp_dll)
            
            # Ejecutar setup.bat
            self.run_setup_bat_uninstall()
            
            # Limpiar DLL temporal
            if os.path.exists(temp_dll):
                try:
                    os.remove(temp_dll)
                except:
                    pass

            # PASO 3: Eliminar archivos DLL manualmente (por si acaso)
            self.log_status("Eliminando archivos del Unlocker...")
            for dll_path in locations:
                try:
                    # Intentar múltiples veces en caso de que el archivo esté bloqueado
                    for _ in range(3):
                        try:
                            os.remove(dll_path)
                            self.log_status(f"✓ Eliminado: {dll_path}")
                            break
                        except:
                            time.sleep(1)
                            continue
                except Exception as e:
                    self.log_status(f"⚠ No se pudo eliminar: {dll_path}")

            # PASO 4: Preguntar si eliminar configuraciones
            self.ask_delete_configs()
            
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

    def ask_delete_configs_only(self):
        """Pregunta si eliminar solo configuraciones (cuando no hay unlocker)"""
        response = messagebox.askyesno(
            "Eliminar Configuraciones",
            "No se encontró el Unlocker instalado.\n\n"
            "¿Deseas eliminar las configuraciones de todas formas?"
        )
        
        if response:
            self.log_status("Eliminando configuraciones...")
            if os.path.exists(APPDATA_DIR):
                try:
                    shutil.rmtree(APPDATA_DIR)
                    self.log_status("✓ Configuraciones eliminadas")
                    messagebox.showinfo("Éxito", "Configuraciones eliminadas correctamente.")
                except Exception as e:
                    self.log_status(f"⚠ No se pudo eliminar configuraciones: {e}")
                    messagebox.showerror("Error", f"No se pudieron eliminar las configuraciones:\n{e}")
            else:
                self.log_status("No hay configuraciones para eliminar")
                messagebox.showinfo("Información", "No se encontraron configuraciones para eliminar.")

    def ask_delete_configs(self):
        """Pregunta si eliminar configuraciones después de desinstalar"""
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

        # Verificar resultado final
        time.sleep(1)
        if self.is_unlocker_installed():
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

    def show_error_message(self, error):
        """Muestra mensaje de error formateado."""
        error_msg = f"Se produjo un error:\n\n{str(error)}"
        
        error_str = str(error).lower()
        
        if "acceso denegado" in error_str or "permission denied" in error_str:
            error_msg += "\n\nEsto puede deberse a falta de permisos de administrador o antivirus bloqueando la operación."
        elif "no se encontró" in error_str and "version.dll" in error_str:
            error_msg += "\n\nAsegúrate de que los archivos están en las carpetas correctas:\n"
            error_msg += "- ea_app/version.dll\n- origin/version.dll\n- setup.bat\n- config.ini"
        elif "timed out" in error_str:
            error_msg += "\n\nEl antivirus puede estar bloqueando la instalación. Desactívalo temporalmente."
        elif "setup.bat" in error_str:
            error_msg += "\n\nEl instalador (setup.bat) falló. Puede deberse a:\n"
            error_msg += "- Falta de permisos de administrador\n"
            error_msg += "- Antivirus bloqueando la ejecución\n"
            error_msg += "- EA App/Origin no instalado"
        
        messagebox.showerror("Error", error_msg)

    def verify_config_files(self):
        """Verifica que los archivos de configuración se copiaron correctamente."""
        config_files = []
        
        # Verificar config.ini
        if os.path.exists(os.path.join(APPDATA_DIR, CONFIG_INI)):
            config_files.append(CONFIG_INI)
        
        # Verificar según selección
        if self.sims4_var.get():
            if os.path.exists(os.path.join(APPDATA_DIR, INI_TS4)):
                config_files.append(INI_TS4)
        
        if self.sims3_var.get():
            if os.path.exists(os.path.join(APPDATA_DIR, INI_TS3)):
                config_files.append(INI_TS3)
        
        if config_files:
            self.log_status(f"✅ Archivos instalados: {', '.join(config_files)}")
            return True
        else:
            self.log_status("⚠ No se instalaron archivos de configuración")
            return False

    def run_setup_bat_install(self):
        """Ejecuta setup.bat con el argumento 'install'."""
        # Buscar setup.bat en los lugares correctos
        base_dir = get_base_dir()
        exe_dir = get_executable_dir()
        
        possible_bat_paths = [
            os.path.join(base_dir, "setup.bat"),
            os.path.join(exe_dir, "setup.bat"),
        ]
        
        bat_path = None
        for path in possible_bat_paths:
            if os.path.exists(path):
                bat_path = path
                break
        
        if not bat_path:
            raise FileNotFoundError(
                f"No se encontró setup.bat en:\n- {base_dir}\n- {exe_dir}"
            )
        
        # Usar TEMP como directorio de trabajo
        work_dir = os.environ.get('TEMP', os.path.expanduser("~"))
        log_path = os.path.join(work_dir, "unlocker_install_log.txt")
        
        try:
            self.log_status("Ejecutando instalador... (esto puede tomar unos segundos)")
            
            process = subprocess.Popen(
                [bat_path, "install"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                shell=True,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate(timeout=60)
            
            # Guardar log para depuración
            with open(log_path, "w", encoding="utf-8") as log_f:
                log_f.write(f"Comando: {bat_path} install\n")
                log_f.write(f"CWD: {work_dir}\n")
                log_f.write(f"Return code: {process.returncode}\n\n")
                log_f.write(f"--- STDOUT ---\n{stdout}\n\n--- STDERR ---\n{stderr}")
            
            if process.returncode != 0:
                error_msg = f"setup.bat terminó con código de error: {process.returncode}"
                if "acceso denegado" in stderr.lower():
                    error_msg += "\n\nFalta de permisos de administrador."
                elif "antivirus" in stderr.lower():
                    error_msg += "\n\nPosible bloqueo del antivirus."
                self.log_status(f"⚠ Error en instalador (código {process.returncode})")
                return False
            
            self.log_status("✅ Instalador ejecutado correctamente")
            return True
            
        except subprocess.TimeoutExpired:
            process.kill()
            self.log_status("⚠ Instalador tardó demasiado")
            raise Exception("setup.bat tardó demasiado. El antivirus puede estar bloqueándolo.")
        except Exception as e:
            self.log_status(f"⚠ Error ejecutando instalador: {str(e)}")
            raise Exception(f"Fallo al ejecutar setup.bat install:\n{str(e)}")

    def run_setup_bat_uninstall(self):
        """Ejecuta setup.bat con el argumento 'uninstall'."""
        # Buscar setup.bat en los lugares correctos
        base_dir = get_base_dir()
        exe_dir = get_executable_dir()
        
        possible_bat_paths = [
            os.path.join(base_dir, "setup.bat"),
            os.path.join(exe_dir, "setup.bat"),
        ]
        
        bat_path = None
        for path in possible_bat_paths:
            if os.path.exists(path):
                bat_path = path
                break
        
        if not bat_path:
            # Si no hay setup.bat, solo continuar (no es crítico para desinstalar)
            print("setup.bat no encontrado, continuando con desinstalación manual")
            return True
        
        # Usar TEMP como directorio de trabajo
        work_dir = os.environ.get('TEMP', os.path.expanduser("~"))
        
        try:
            process = subprocess.Popen(
                [bat_path, "uninstall"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=work_dir,
                shell=True,
                universal_newlines=True
            )
            process.communicate(timeout=30)
            return True
        except Exception as e:
            print(f"setup.bat uninstall error: {e}")
            return False

    def check_and_update_ini(self, filename, url):
        """Descarga el .ini desde GitHub y lo instala."""
        target_path = os.path.join(APPDATA_DIR, filename)
        
        try:
            self.log_status(f"Descargando {filename} desde GitHub...")
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 UnlockerBot/1.0'})
            response = urllib.request.urlopen(req, timeout=10)
            content = response.read()
            
            with open(target_path, 'wb') as f:
                f.write(content)
            self.log_status(f"✓ {filename} actualizado desde GitHub")
            return True
            
        except urllib.error.URLError:
            print(f"[!] Sin internet o GitHub no disponible. Usando versión local de {filename}")
            return self.install_local_file(filename, APPDATA_DIR)
        except Exception as e:
            print(f"[!] Error descargando {filename}: {e}")
            return self.install_local_file(filename, APPDATA_DIR)

    def install_local_file(self, filename, target_dir):
        """Copia un archivo empaquetado al directorio destino."""
        base_dir = get_base_dir()
        exe_dir = get_executable_dir()
        
        # Buscar el archivo en múltiples ubicaciones
        possible_sources = [
            os.path.join(base_dir, filename),
            os.path.join(base_dir, "ea_app", filename),
            os.path.join(base_dir, "origin", filename),
            os.path.join(exe_dir, filename),
            os.path.join(exe_dir, "ea_app", filename),
            os.path.join(exe_dir, "origin", filename),
        ]
        
        source_path = None
        for path in possible_sources:
            if os.path.exists(path):
                source_path = path
                break
        
        if not source_path:
            raise FileNotFoundError(
                f"No se encontró el archivo '{filename}'\n"
                f"Buscado en:\n" + "\n".join(possible_sources[:4])
            )
        
        target_path = os.path.join(target_dir, filename)
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy2(source_path, target_path)
        
        if not os.path.exists(target_path):
            raise Exception(f"Error al copiar {filename} a {target_dir}")
        
        self.log_status(f"✓ {filename} copiado correctamente")
        return True


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue") 
    
    app = UnlockerApp()
    app.mainloop()
