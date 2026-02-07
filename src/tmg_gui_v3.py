#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMG SUITE GUI v3.0
==================
Interface graphique pour TMG Tools

Auteur: Claude
Date: 2026-02-06
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import sys
import time
import json
import queue
import threading
import re
import subprocess
import platform

# Import modules
try:
    import mapping_tool
except ImportError:
    print("❌ ERREUR: mapping_tool.py introuvable!")
    sys.exit(1)

try:
    import sentence_injector
except ImportError:
    print("⚠️  WARNING: sentence_injector.py not found - Sentence Injection disabled")
    sentence_injector = None

# Role injector - LAZY LOADING (import seulement quand nécessaire)
# Évite le crash si mapping.json absent au démarrage
role_injector = None

# =============================================================================
# CONFIGURATION
# =============================================================================
CONFIG_FILE = "tmg_suite_config.json"

DEFAULT_CONFIG = {
    'gedcom_path': '',
    'tmg_project_path': ''
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def is_tmg_running():
    """
    Vérifie si The Master Genealogist est en cours d'exécution.
    Supporte TMG v7, v8, v9 (tmg7.exe, tmg8.exe, tmg9.exe).
    
    CRITIQUE : Modifier les fichiers DBF pendant que TMG est ouvert peut causer
    une corruption de base de données.
    
    Returns:
        bool: True si un processus TMG est détecté
    """
    if platform.system() == 'Windows':
        try:
            # Vérifier les 3 versions possibles
            for exe_name in ['tmg9.exe', 'tmg8.exe', 'tmg7.exe']:
                result = subprocess.run(
                    ['tasklist', '/FI', f'IMAGENAME eq {exe_name}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if exe_name in result.stdout:
                    return True
            return False
        except Exception:
            # Si la vérification échoue, on continue (mieux que bloquer)
            return False
    return False  # Sur non-Windows, on assume que c'est OK

class TMGSuiteGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("TMG Suite v3.0")
        self.geometry("1000x700")
        
        # Variables
        self.gedcom_path = tk.StringVar()
        self.tmg_project_path = tk.StringVar()
        self.tmg_prefix = tk.StringVar()  # Calculé automatiquement
        
        self.excel_mapping_path = None
        self.json_mapping_path = None
        
        # Interface
        self.create_widgets()
        
        # Menu (AVANT load_config pour que les références existent)
        self.create_menu()
        
        # Charger config (met à jour le menu automatiquement)
        self.load_config()
        
        # Thread-safe logging
        self.log_queue = queue.Queue()
        self.after(50, self._poll_log_queue)
    
    def create_menu(self):
        """Créer menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Sous-menu Files in use
        self.files_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Files in use", menu=self.files_menu)
        self.files_menu.add_command(label="GEDCOM: (not set)", state=tk.DISABLED)
        self.files_menu.add_command(label="TMG Project: (not set)", state=tk.DISABLED)
        self.files_menu.add_separator()
        self.files_menu.add_command(label="Excel (XLS): mapping_master.xlsx", state=tk.DISABLED)
        self.files_menu.add_command(label="JSON: mapping.json", state=tk.DISABLED)
        
        # Indices des entrées (pour mise à jour dynamique)
        self.menu_gedcom_index = 0
        self.menu_tmg_index = 1
        
        file_menu.add_separator()
        file_menu.add_command(label="Clear Logs", command=self.clear_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # 1. Mapping Tool
        mapping_menu = tk.Menu(tools_menu, tearoff=0)
        tools_menu.add_cascade(label="1. Mapping Tool", menu=mapping_menu)
        mapping_menu.add_command(label="Generate Excel", command=self.run_mapping_generate, accelerator="Ctrl+G")
        mapping_menu.add_command(label="Compile JSON", command=self.run_mapping_compile, accelerator="Ctrl+J")
        
        # 2. Role Injection
        tools_menu.add_command(label="2. Role Injection", command=self.run_role_injection, accelerator="Ctrl+R")
        
        # 3. Sentence Injection
        sentence_menu = tk.Menu(tools_menu, tearoff=0)
        tools_menu.add_cascade(label="3. Sentence Injection", menu=sentence_menu)
        sentence_menu.add_command(label="Inject ONE tag", command=self.toggle_tag_selector)
        sentence_menu.add_command(label="Inject MISSING only (all tags)", command=self.run_sentence_inject_missing)
        sentence_menu.add_command(label="REGENERATE ALL (all tags)", command=self.run_sentence_regenerate_all)
        
        # Shortcuts
        self.bind('<Control-g>', lambda e: self.run_mapping_generate())
        self.bind('<Control-j>', lambda e: self.run_mapping_compile())
        self.bind('<Control-r>', lambda e: self.run_role_injection())
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About TMG Suite", command=self.show_about)
        help_menu.add_command(label="GEDCOM Configuration Guide", command=self.show_gedcom_guide)
        help_menu.add_command(label="Quick Start Guide", command=self.show_quickstart)
        help_menu.add_separator()
        help_menu.add_command(label="Troubleshooting", command=self.show_troubleshooting)
    
    def create_widgets(self):
        """Créer interface"""
        # =================================================================
        # CONFIGURATION
        # =================================================================
        config_frame = ttk.LabelFrame(self, text="Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # GEDCOM
        ttk.Label(config_frame, text="GEDCOM File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.gedcom_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(config_frame, text="Browse", command=self.browse_gedcom).grid(row=0, column=2)
        
        # TMG Project (.PJC)
        ttk.Label(config_frame, text="TMG Project (.PJC):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.tmg_project_path, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(config_frame, text="Browse", command=self.browse_tmg).grid(row=1, column=2)
        
        # =================================================================
        # TOOLS
        # =================================================================
        tools_frame = ttk.LabelFrame(self, text="Tools", padding=10)
        tools_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Mapping Tool
        map_frame = ttk.Frame(tools_frame)
        map_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(map_frame, text="1. MAPPING TOOL:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.btn_mapping_generate = ttk.Button(map_frame, text="Generate Excel", command=self.run_mapping_generate)
        self.btn_mapping_generate.pack(side=tk.LEFT, padx=5)
        self.btn_mapping_compile = ttk.Button(map_frame, text="Compile JSON", command=self.run_mapping_compile)
        self.btn_mapping_compile.pack(side=tk.LEFT, padx=5)
        
        # Role Injection
        role_frame = ttk.Frame(tools_frame)
        role_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(role_frame, text="2. ROLE INJECTION:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.btn_role_inject = ttk.Button(role_frame, text="Inject Roles from Mapping", 
                                          command=self.run_role_injection)
        self.btn_role_inject.pack(side=tk.LEFT, padx=5)
        
        # Sentence Injection
        sent_frame = ttk.Frame(tools_frame)
        sent_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sent_frame, text="3. SENTENCE INJECTION:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        # Bouton Inject ONE tag
        btn_inject_one = ttk.Button(sent_frame, text="Inject ONE tag", 
                                    command=self.toggle_tag_selector)
        btn_inject_one.pack(side=tk.LEFT, padx=5)
        
        # Boutons pour tous les tags
        self.btn_inject_missing = ttk.Button(sent_frame, text="Inject MISSING only (all tags)", 
                                            command=self.run_sentence_inject_missing)
        self.btn_inject_missing.pack(side=tk.LEFT, padx=5)
        
        self.btn_regenerate_all = ttk.Button(sent_frame, text="REGENERATE ALL (all tags)", 
                                            command=self.run_sentence_regenerate_all)
        self.btn_regenerate_all.pack(side=tk.LEFT, padx=5)
        
        # Dropdown tag (affiché sur une nouvelle ligne quand activé)
        self.tag_selector_frame = ttk.Frame(tools_frame)
        self.tag_var = tk.StringVar()
        self.tag_combo = ttk.Combobox(self.tag_selector_frame, textvariable=self.tag_var, 
                                      width=30, state='readonly')
        ttk.Label(self.tag_selector_frame, text="    Select tag:").pack(side=tk.LEFT, padx=(10, 5))
        self.tag_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.tag_selector_frame, text="Inject", 
                  command=self.run_sentence_inject_one).pack(side=tk.LEFT, padx=5)
        # Caché par défaut
        
        # Désactiver si sentence_injector absent
        if not sentence_injector:
            btn_inject_one.config(state=tk.DISABLED)
            self.btn_inject_missing.config(state=tk.DISABLED)
            self.btn_regenerate_all.config(state=tk.DISABLED)
        
        # =================================================================
        # LOGS
        # =================================================================
        log_frame = ttk.LabelFrame(self, text="Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=20,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Compteur pour tags de liens uniques
        self._link_id = 0
        
        # Tags couleurs
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('SUCCESS', foreground='#00AA00', font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('WARNING', foreground='#FF8800', font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('ERROR', foreground='#DD0000', font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('HEADER', foreground='#0066CC', font=('Consolas', 10, 'bold'))
        
        # Tag hyperlink (liens cliquables) - style seulement
        self.log_text.tag_config('hyperlink', foreground='#0066FF', underline=True)
        
        # =================================================================
        # STATUS BAR
        # =================================================================
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Message initial
        self.append_log("=" * 80, 'HEADER')
        self.append_log("TMG SUITE v3.0", 'HEADER')
        self.append_log("=" * 80, 'HEADER')
        self.append_log("")
        self.append_log("Configure your files above and click a tool button.", 'INFO')
        self.append_log("")
    
    def browse_gedcom(self):
        """Sélectionner GEDCOM"""
        path = filedialog.askopenfilename(
            title="Select GEDCOM file",
            filetypes=[("GEDCOM", "*.ged"), ("All files", "*.*")]
        )
        if path:
            self.gedcom_path.set(path)
            self.save_config()
            self.update_files_menu()
    
    def browse_tmg(self):
        """Sélectionner fichier projet TMG (.PJC)"""
        path = filedialog.askopenfilename(
            title="Select TMG Project file (.PJC)",
            filetypes=[("TMG Project", "*.PJC"), ("All files", "*.*")]
        )
        if path:
            self.tmg_project_path.set(path)
            # Extraire automatiquement le préfixe
            self._extract_prefix_from_pjc(path)
            self.save_config()
            self.update_files_menu()
    
    def _extract_prefix_from_pjc(self, pjc_path):
        """Extrait le préfixe TMG depuis le nom du fichier .PJC"""
        basename = os.path.splitext(os.path.basename(pjc_path))[0]
        if basename.endswith('__'):
            prefix = basename[:-1]  # testcase__ → testcase_
        elif basename.endswith('_'):
            prefix = basename
        else:
            prefix = basename + '_'
        self.tmg_prefix.set(prefix)
    
    def append_log(self, message, level='INFO'):
        """Ajoute message au log avec liens cliquables"""
        # Convertir en string si nécessaire
        if not isinstance(message, str):
            message = str(message)
        
        self.log_text.config(state=tk.NORMAL)
        
        # Préfixes
        prefix = {
            'INFO': '  ',
            'SUCCESS': '✅ ',
            'WARNING': '⚠️  ',
            'ERROR': '❌ ',
            'HEADER': ''
        }.get(level, '  ')
        
        # Détecter URLs file:///
        url_pattern = r'(file:///[^\r\n]+)'
        parts = re.split(url_pattern, message)
        
        # Insérer préfixe
        self.log_text.insert(tk.END, prefix, level)
        
        # Insérer message avec URLs cliquables
        for part in parts:
            if part.startswith('file:///'):
                self._link_id += 1
                tag = f"hyperlink_{self._link_id}"
                
                # Insérer le texte du lien avec tags: level + hyperlink + tag unique
                self.log_text.insert(tk.END, part, (level, 'hyperlink', tag))
                
                # Bind sur CE lien (pas besoin de calculer @x,y)
                self.log_text.tag_bind(tag, "<Button-1>", lambda e, url=part: self._open_file_url(url))
            else:
                # Texte normal
                self.log_text.insert(tk.END, part, level)
        
        self.log_text.insert(tk.END, '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_idletasks()
    
    def thread_safe_log(self, message, level='INFO'):
        """Thread-safe version of append_log - puts message in queue"""
        self.log_queue.put((message, level))
    
    def _poll_log_queue(self):
        """Poll log queue and process messages (runs in main Tk thread)"""
        try:
            while True:
                msg, lvl = self.log_queue.get_nowait()
                self.append_log(msg, lvl)
        except queue.Empty:
            pass
        # Re-schedule polling
        self.after(50, self._poll_log_queue)
    
    def _open_file_url(self, file_url):
        """Ouvre fichier depuis URL file:///"""
        
        if file_url.startswith('file:///'):
            file_path = file_url[8:]  # Enlever file:///
            if platform.system() == 'Windows':
                file_path = file_path.replace('/', '\\')
            
            
            try:
                if platform.system() == 'Windows':
                    os.startfile(file_path)
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', file_path])
                else:
                    subprocess.run(['xdg-open', file_path])
                
                self.append_log(f"Opening: {os.path.basename(file_path)}", 'INFO')
            except Exception as e:
                self.append_log(f"Cannot open file: {e}", 'ERROR')
    
    def clear_logs(self):
        """Efface logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.append_log("Logs cleared", 'INFO')
    
    def update_files_menu(self):
        """Met à jour les chemins dans le menu File > Files in use"""
        gedcom = self.gedcom_path.get()
        tmg = self.tmg_project_path.get()
        
        # GEDCOM
        if gedcom:
            gedcom_short = os.path.basename(gedcom)
            self.files_menu.entryconfig(self.menu_gedcom_index, 
                                       label=f"GEDCOM: {gedcom_short}")
        else:
            self.files_menu.entryconfig(self.menu_gedcom_index, 
                                       label="GEDCOM: (not set)")
        
        # TMG Project
        if tmg:
            tmg_short = os.path.basename(tmg)
            self.files_menu.entryconfig(self.menu_tmg_index, 
                                       label=f"TMG Project: {tmg_short}")
        else:
            self.files_menu.entryconfig(self.menu_tmg_index, 
                                       label="TMG Project: (not set)")
    
    def set_running_state(self, running):
        """Active/désactive boutons"""
        state = tk.DISABLED if running else tk.NORMAL
        self.btn_mapping_generate.config(state=state)
        self.btn_mapping_compile.config(state=state)
        self.btn_role_inject.config(state=state)
        
        # Sentence injection buttons (si disponibles)
        if sentence_injector:
            self.btn_inject_missing.config(state=state)
            self.btn_regenerate_all.config(state=state)
    
    # =========================================================================
    # MAPPING TOOL
    # =========================================================================
    def run_mapping_generate(self):
        """Lance génération Excel"""
        if not self.gedcom_path.get() or not self.tmg_project_path.get():
            messagebox.showerror("Error", "Please configure GEDCOM and TMG Project files")
            return
        
        self.set_running_state(True)
        self.status_label.config(text="Generating Excel...")
        
        thread = threading.Thread(target=self._run_mapping_generate_thread, daemon=True)
        thread.start()
    
    def _run_mapping_generate_thread(self):
        """Thread génération Excel"""
        try:
            self.thread_safe_log("\n" + "=" * 80, 'HEADER')
            self.thread_safe_log("MAPPING TOOL - Generate Excel", 'HEADER')
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log("")
            
            # Extraire dossier et préfixe depuis le chemin PJC
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            
            # Appeler mapping_tool avec paramètres
            excel_path = mapping_tool.generate_excel_mode(
                gedcom_path=self.gedcom_path.get(),
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix,
                log_callback=self.thread_safe_log
            )
            
            # Afficher lien cliquable
            excel_full_path = os.path.abspath(excel_path)
            file_url = f"file:///{excel_full_path.replace(os.sep, '/')}"
            
            self.thread_safe_log("")
            self.thread_safe_log(f"Excel generated: {excel_path}", 'SUCCESS')
            self.thread_safe_log(f"   Click to open: {file_url}", 'INFO')
            self.thread_safe_log("")
            self.thread_safe_log("⚠️  Please validate the Excel, then click 'Compile JSON'", 'WARNING')
            
            self.excel_mapping_path = excel_path
            self.status_label.config(text="Excel generated successfully")
            
        except Exception as e:
            self.thread_safe_log(f"Error: {e}", 'ERROR')
            self.status_label.config(text="Error")
        finally:
            self.set_running_state(False)
    
    def run_mapping_compile(self):
        """Lance compilation JSON"""
        if not self.excel_mapping_path or not os.path.exists(self.excel_mapping_path):
            result = messagebox.askyesno("Excel File Missing",
                                        "Excel file not found. Run Generate now?")
            if result:
                self.run_mapping_generate()
            return
        
        self.set_running_state(True)
        self.status_label.config(text="Compiling JSON...")
        
        thread = threading.Thread(target=self._run_mapping_compile_thread, daemon=True)
        thread.start()
    
    def _run_mapping_compile_thread(self):
        """Thread compilation JSON"""
        try:
            self.thread_safe_log("\n" + "=" * 80, 'HEADER')
            self.thread_safe_log("MAPPING TOOL - Compile JSON", 'HEADER')
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log("")
            
            # Appeler mapping_tool
            json_path, errors = mapping_tool.compile_json_mode(
                excel_file=self.excel_mapping_path,
                json_file="mapping.json",
                log_callback=self.thread_safe_log
            )
            
            if errors:
                error_msg = f"❌ Compilation failed:\n\n{len(errors)} empty cells found:\n\n"
                for err in errors[:5]:
                    error_msg += f"  • {err}\n"
                if len(errors) > 5:
                    error_msg += f"\n  ... and {len(errors) - 5} more"
                error_msg += "\n\nPlease complete the Excel file and try again."
                
                self.thread_safe_log("Compilation failed - empty cells detected", 'ERROR')
                
                def show_error():
                    messagebox.showerror("Compilation Failed", error_msg)
                
                self.after(0, show_error)
                self.status_label.config(text="Compilation failed")
            else:
                self.json_mapping_path = json_path
                
                self.thread_safe_log("")
                self.thread_safe_log(f"JSON compiled: {json_path}", 'SUCCESS')
                self.thread_safe_log("✓ Ready for Role Injection (Phase 2)", 'SUCCESS')
                
                def show_success():
                    messagebox.showinfo("Success", "JSON compiled successfully!\n\nReady for Role Injection.")
                
                self.after(0, show_success)
                self.status_label.config(text="JSON compiled successfully")
            
        except Exception as e:
            self.thread_safe_log(f"Error: {e}", 'ERROR')
            self.status_label.config(text="Error")
        finally:
            self.set_running_state(False)
    
    # =========================================================================
    # ROLE INJECTION
    # =========================================================================
    def run_role_injection(self):
        """Lance l'injection des rôles"""
        # SÉCURITÉ : Vérifier TMG IMMÉDIATEMENT (avant toute autre vérification)
        if is_tmg_running():
            messagebox.showerror("⛔ TMG is Running!", 
                               "The Master Genealogist (TMG.EXE) is currently running.\n\n" +
                               "Please close TMG before running Role Injection.\n\n" +
                               "Modifying database files while TMG is open can cause corruption.")
            return
        
        if not self.gedcom_path.get() or not self.tmg_project_path.get():
            messagebox.showerror("Error", "Please configure GEDCOM and TMG Project files")
            return
        
        # Vérifier que mapping.json existe
        mapping_file = "mapping.json"
        if not os.path.exists(mapping_file):
            messagebox.showerror("Error", 
                               f"File {mapping_file} not found!\n\n" +
                               "You must first:\n" +
                               "1. Generate Excel (Phase 1)\n" +
                               "2. Compile JSON (Phase 1)\n\n" +
                               "Then run Role Injection.")
            return
        
        # LAZY IMPORT de role_injector (seulement maintenant que mapping.json existe)
        global role_injector
        if role_injector is None:
            try:
                import role_injector
            except SystemExit:
                # role_injector a fait sys.exit(1) car mapping.json problématique
                messagebox.showerror("Error", 
                                   "Cannot load role_injector module!\n\n" +
                                   "mapping.json may be corrupted.\n\n" +
                                   "Try regenerating it:\n" +
                                   "1. Generate Excel (Phase 1)\n" +
                                   "2. Compile JSON (Phase 1)")
                return
            except ImportError as e:
                messagebox.showerror("Error", 
                                   f"role_injector.py not found!\n\n{e}")
                return
        
        # Charger mapping pour afficher stats
        try:
            import json
            with open(mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            events_count = len(data.get('events', {}))
            roles_count = len(data.get('roles', {}))
        except:
            events_count = "?"
            roles_count = "?"
        
        # Dialogue de confirmation personnalisé
        dialog = tk.Toplevel(self)
        dialog.title("Confirm Role Injection")
        dialog.geometry("550x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        ttk.Label(main_frame, text="ROLE INJECTION - Configuration", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 8))
        
        # Configuration actuelle
        config_frame = ttk.LabelFrame(main_frame, text="Files to use", padding=6)
        config_frame.pack(fill=tk.X, pady=5)
        
        gedcom = self.gedcom_path.get()
        tmg = self.tmg_project_path.get()
        prefix = self.tmg_prefix.get()
        
        ttk.Label(config_frame, text="GEDCOM:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=1)
        ttk.Label(config_frame, text=gedcom, wraplength=450).grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(config_frame, text="TMG Project:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=1)
        ttk.Label(config_frame, text=tmg, wraplength=450).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(config_frame, text="TMG Prefix:", font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=1)
        ttk.Label(config_frame, text=prefix).grid(row=2, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(config_frame, text="Mapping:", font=('Arial', 9, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=1)
        ttk.Label(config_frame, text=f"{events_count} events, {roles_count} roles").grid(row=3, column=1, sticky=tk.W, padx=(5, 0))
        
        # Actions
        actions_frame = ttk.LabelFrame(main_frame, text="What will happen", padding=6)
        actions_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(actions_frame, text="• Create automatic backup of TMG database").pack(anchor=tk.W, pady=1)
        ttk.Label(actions_frame, text="• Scan GEDCOM for witness roles").pack(anchor=tk.W, pady=1)
        ttk.Label(actions_frame, text="• Update TMG structure (roles in T.DBF)").pack(anchor=tk.W, pady=1)
        ttk.Label(actions_frame, text="• Inject witnesses into TMG events").pack(anchor=tk.W, pady=1)
        
        # Warning
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(warning_frame, text="⚠️  Make sure TMG is closed before proceeding!", 
                 foreground='red', font=('Arial', 9, 'bold')).pack()
        
        # Boutons
        result_var = tk.BooleanVar(value=False)
        
        def on_ok():
            result_var.set(True)
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=8)
        
        ttk.Button(btn_frame, text="Cancel", command=on_cancel, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Continue", command=on_ok, width=15).pack(side=tk.LEFT, padx=5)
        
        # Attendre fermeture
        self.wait_window(dialog)
        
        # Si annulé
        if not result_var.get():
            return
        
        # Lancer le scan pour compter les témoins
        self.set_running_state(True)
        self.status_label.config(text="Scanning GEDCOM...")
        
        thread = threading.Thread(target=self._scan_and_confirm_role_injection, daemon=True)
        thread.start()
    
    def _scan_and_confirm_role_injection(self):
        """Scan GEDCOM, affiche stats, demande dry-run, puis lance injection"""
        try:
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            gedcom_path = self.gedcom_path.get()
            
            self.thread_safe_log("\n" + "=" * 80, 'HEADER')
            self.thread_safe_log("ROLE INJECTION - SCAN", 'HEADER')
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log("")
            
            # Charger mapping
            import json
            with open("mapping.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Scanner rapidement pour compter
            self.thread_safe_log("Scanning GEDCOM to count witnesses...", 'INFO')
            
            # Compter les _SHAR dans le GEDCOM
            witness_count = 0
            try:
                with open(gedcom_path, 'r', encoding='ansi') as f:
                    for line in f:
                        if '_SHAR @' in line:
                            witness_count += 1
            except:
                with open(gedcom_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '_SHAR @' in line:
                            witness_count += 1
            
            self.thread_safe_log(f"✓ Found {witness_count} witness references in GEDCOM", 'SUCCESS')
            self.thread_safe_log("")
            
            # Popup avec stats + question dry-run
            def show_dryrun_dialog():
                dialog = tk.Toplevel(self)
                dialog.title("Witnesses Found - Choose Mode")
                dialog.geometry("550x400")
                dialog.transient(self)
                dialog.grab_set()
                
                main_frame = ttk.Frame(dialog, padding=10)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # Stats
                ttk.Label(main_frame, text="GEDCOM Analysis Complete", 
                         font=('Arial', 12, 'bold')).pack(pady=(0, 6))
                
                stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding=6)
                stats_frame.pack(fill=tk.X, pady=5)
                
                ttk.Label(stats_frame, text=f"Witness references found: {witness_count}", 
                         font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=2)
                ttk.Label(stats_frame, text=f"Events mapped: {len(data.get('events', {}))}").pack(anchor=tk.W, pady=1)
                ttk.Label(stats_frame, text=f"Roles mapped: {len(data.get('roles', {}))}").pack(anchor=tk.W, pady=1)
                
                # Question
                question_frame = ttk.Frame(main_frame)
                question_frame.pack(fill=tk.BOTH, expand=True, pady=6)
                
                ttk.Label(question_frame, text="How do you want to proceed?", 
                         font=('Arial', 10, 'bold')).pack(pady=2)
                
                ttk.Label(question_frame, text="DRY-RUN: Simulate without modifying database (recommended first)",
                         wraplength=500).pack(pady=1)
                ttk.Label(question_frame, text="REAL: Inject witnesses into TMG database",
                         wraplength=500).pack(pady=1)
                
                # Résultat
                choice = tk.StringVar(value="")
                
                def on_dryrun():
                    choice.set("dryrun")
                    dialog.destroy()
                
                def on_real():
                    choice.set("real")
                    dialog.destroy()
                
                def on_cancel():
                    choice.set("cancel")
                    dialog.destroy()
                
                btn_frame = ttk.Frame(main_frame)
                btn_frame.pack(pady=6)
                
                ttk.Button(btn_frame, text="Cancel", command=on_cancel, width=15).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="DRY-RUN (Test)", command=on_dryrun, width=15).pack(side=tk.LEFT, padx=5)
                ttk.Button(btn_frame, text="REAL Injection", command=on_real, width=15).pack(side=tk.LEFT, padx=5)
                
                self.wait_window(dialog)
                return choice.get()
            
            # Afficher dialogue dans main thread
            choice = [None]
            def show():
                choice[0] = show_dryrun_dialog()
            
            self.after(0, show)
            
            # Attendre choix
            import time
            while choice[0] is None:
                time.sleep(0.1)
            
            if choice[0] == "cancel":
                self.thread_safe_log("✗ Injection cancelled by user", 'WARNING')
                self.status_label.config(text="Cancelled")
                self.set_running_state(False)
                return
            
            dry_run = (choice[0] == "dryrun")
            
            # Si mode REAL, dernière confirmation
            if not dry_run:
                confirm = [None]
                def show_final_warning():
                    result = messagebox.askyesno(
                        "⚠️ FINAL WARNING",
                        f"You are about to MODIFY your TMG database!\n\n" +
                        f"• {witness_count} witnesses will be injected\n" +
                        f"• Backup will be created automatically\n" +
                        f"• Database structure will be updated\n\n" +
                        f"This is your LAST CHANCE to cancel!\n\n" +
                        f"Continue with REAL injection?",
                        icon='warning'
                    )
                    confirm[0] = result
                
                self.after(0, show_final_warning)
                
                while confirm[0] is None:
                    time.sleep(0.1)
                
                if not confirm[0]:
                    self.thread_safe_log("✗ Injection cancelled at final confirmation", 'WARNING')
                    self.status_label.config(text="Cancelled")
                    self.set_running_state(False)
                    return
            
            # Lancer injection
            mode = "SIMULATION" if dry_run else "REAL"
            self.status_label.config(text=f"Injecting roles ({mode})...")
            
            self.thread_safe_log("\n" + "=" * 80, 'HEADER')
            self.thread_safe_log(f"ROLE INJECTION - {mode}", 'HEADER')
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log("")
            
            if dry_run:
                self.thread_safe_log("⚠️  DRY-RUN MODE: No changes will be made to TMG files", 'WARNING')
                self.thread_safe_log("")
            else:
                self.thread_safe_log("⏱️  Injection may take several minutes. Please be patient...", 'INFO')
                self.thread_safe_log("   The interface may appear frozen but is working.", 'INFO')
                self.thread_safe_log("")
            
            # Appeler role_injector directement (on est déjà dans un thread)
            result = role_injector.inject_roles_mode(
                gedcom_path=gedcom_path,
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix,
                mapping_file="mapping.json",
                log_callback=self.thread_safe_log,
                dry_run=dry_run
            )
            
            if result.get('success'):
                self.thread_safe_log("")
                self.thread_safe_log("✓ Role injection completed!", 'SUCCESS')
                self.thread_safe_log(f"Log file: {result.get('log_file', '')}", 'INFO')
                
                def show_success():
                    if not dry_run:
                        self.thread_safe_log("⚠️  IMPORTANT: Open TMG and run File > Maintenance > Reindex", 'WARNING')
                        messagebox.showinfo("Success", 
                                          "Role injection completed!\n\n" +
                                          "Remember to reindex in TMG:\n" +
                                          "File > Maintenance > Reindex")
                    else:
                        messagebox.showinfo("Dry-run Complete", 
                                          "Simulation completed successfully!\n\n" +
                                          "No changes were made to TMG database.\n\n" +
                                          "Review the log file.\n" +
                                          "If satisfied, return to Real mode to apply.")
                
                self.after(0, show_success)
                self.status_label.config(text=f"Role injection completed ({mode})")
            else:
                error = result.get('error', 'Unknown error')
                self.thread_safe_log(f"✗ Role injection failed: {error}", 'ERROR')
                
                def show_error():
                    messagebox.showerror("Error", f"Role injection failed:\n\n{error}")
                
                self.after(0, show_error)
                self.status_label.config(text="Role injection failed")
            
            self.set_running_state(False)
            
        except Exception as e:
            self.thread_safe_log(f"Error during scan: {e}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.set_running_state(False)
    
    def _run_role_injection_thread(self, dry_run=False):
        """Thread d'exécution injection rôles"""
        try:
            mode = "SIMULATION" if dry_run else "REAL"
            self.status_label.config(text=f"Injecting roles ({mode})...")
            
            self.append_log("\n" + "=" * 80, 'HEADER')
            self.append_log(f"ROLE INJECTION - {mode}", 'HEADER')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("")
            
            if dry_run:
                self.append_log("⚠️  DRY-RUN MODE: No changes will be made to TMG files", 'WARNING')
                self.append_log("")
            
            # Extraire paramètres
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            gedcom_path = self.gedcom_path.get()
            
            # Appeler role_injector
            result = role_injector.inject_roles_mode(
                gedcom_path=gedcom_path,
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix,
                mapping_file="mapping.json",
                log_callback=self.thread_safe_log,
                dry_run=dry_run
            )
            
            if result.get('success'):
                self.append_log("")
                self.append_log("✓ Role injection completed!", 'SUCCESS')
                self.append_log(f"Log file: {result.get('log_file', '')}", 'INFO')
                
                def show_success():
                    if not dry_run:
                        self.append_log("⚠️  IMPORTANT: Open TMG and run File > Maintenance > Reindex", 'WARNING')
                        messagebox.showinfo("Success", 
                                          "Role injection completed!\n\n" +
                                          "Remember to reindex in TMG:\n" +
                                          "File > Maintenance > Reindex")
                    else:
                        messagebox.showinfo("Dry-run Complete", 
                                          "Simulation completed successfully!\n\n" +
                                          "No changes were made to TMG database.\n\n" +
                                          "Review the log file.\n" +
                                          "If satisfied, return to Real mode to apply.")
                
                self.after(0, show_success)
                self.status_label.config(text=f"Role injection completed ({mode})")
            else:
                error = result.get('error', 'Unknown error')
                self.append_log(f"✗ Role injection failed: {error}", 'ERROR')
                
                def show_error():
                    messagebox.showerror("Error", f"Role injection failed:\n\n{error}")
                
                self.after(0, show_error)
                self.status_label.config(text="Role injection failed")
            
        except Exception as e:
            self.append_log(f"Error: {e}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.status_label.config(text="Error")
        finally:
            self.set_running_state(False)
    
    # =========================================================================
    # SENTENCE INJECTION
    # =========================================================================
    def toggle_tag_selector(self):
        """Affiche/cache le sélecteur de tag"""
        if self.tag_selector_frame.winfo_ismapped():
            self.tag_selector_frame.pack_forget()
        else:
            # Charger la liste des tags
            self.load_custom_tags()
            self.tag_selector_frame.pack(side=tk.LEFT, padx=5)
    
    def load_custom_tags(self):
        """Charge la liste des tags custom"""
        if not self.tmg_project_path.get():
            messagebox.showerror("Error", "Please configure TMG Project first")
            return
        
        try:
            # Extraire dossier et préfixe
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            
            # Appeler sentence_injector pour lister les tags
            custom_tags = sentence_injector.list_custom_tags_mode(
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix
            )
            
            if custom_tags:
                # Trier alphabétiquement
                custom_tags_sorted = sorted(custom_tags, key=lambda x: x['ETYPENAME'].upper())
                tag_names = [tag['ETYPENAME'] for tag in custom_tags_sorted]
                
                self.tag_combo['values'] = tag_names
                if tag_names:
                    self.tag_combo.current(0)
                self.custom_tags = custom_tags_sorted  # Stocker la version triée
            else:
                messagebox.showwarning("Warning", "No custom tags found")
                
        except Exception as e:
            messagebox.showerror("Error", f"Cannot load tags: {e}")
    
    def run_sentence_inject_one(self):
        """Lance injection pour UN tag"""
        # SÉCURITÉ : Vérifier TMG IMMÉDIATEMENT
        if is_tmg_running():
            messagebox.showerror("⛔ TMG is Running!", 
                               "The Master Genealogist (TMG.EXE) is currently running.\n\n" +
                               "Please close TMG before running Sentence Injection.\n\n" +
                               "Modifying database files while TMG is open can cause corruption.")
            return
        
        if not self.tag_var.get():
            messagebox.showerror("Error", "Please select a tag")
            return
        
        # Trouver le tag sélectionné
        selected_name = self.tag_var.get()
        selected_tag = None
        for tag in self.custom_tags:
            if tag['ETYPENAME'] == selected_name:
                selected_tag = tag
                break
        
        if not selected_tag:
            messagebox.showerror("Error", "Tag not found")
            return
        
        self.set_running_state(True)
        self.status_label.config(text=f"Injecting sentences for {selected_name}...")
        
        thread = threading.Thread(target=self._run_sentence_inject_one_thread, 
                                 args=(selected_tag,), daemon=True)
        thread.start()
    
    def _run_sentence_inject_one_thread(self, tag):
        """Thread pour afficher dialogue et injection UN tag"""
        try:
            # Extraire dossier et préfixe
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            
            # Parser TSENTENCE (déjà chargé dans le tag)
            tsentence_str = tag.get('TSENTENCE', '')
            
            if not tsentence_str:
                self.thread_safe_log(f"Tag {tag['ETYPENAME']} has no TSENTENCE data", 'ERROR')
                return
            
            # Parser avec la fonction de sentence_injector
            roles_data = sentence_injector.parse_tsentence(tsentence_str)
            
            # Construire tag_info
            tag_info = {'roles': {}}
            for rid, data in roles_data.items():
                role_name = data['role'].get('ENGLISHUK', data['role'].get('ENGLISH', f"Role {rid}"))
                has_phrase = bool(data['phrase'].get('ENGLISHUK') or data['phrase'].get('ENGLISH'))
                
                tag_info['roles'][rid] = {
                    'name': role_name,
                    'has_phrase': has_phrase
                }
            
            # Afficher dialogue avec les résultats
            self.after(0, lambda: self._show_tag_injection_dialog(tag, tag_info, tmg_dir, tmg_prefix))
            
        except Exception as e:
            print(f"Exception in analyze: {e}")
            import traceback
            traceback.print_exc()
            self.thread_safe_log(f"Error analyzing tag: {e}", 'ERROR')
        finally:
            self.set_running_state(False)
    
    def _show_tag_injection_dialog(self, tag, tag_info, tmg_dir, tmg_prefix):
        """Affiche dialogue SIMPLE pour confirmer injection"""
        # Compter
        missing = sum(1 for info in tag_info['roles'].values() if not info['has_phrase'])
        existing = sum(1 for info in tag_info['roles'].values() if info['has_phrase'])
        total = len(tag_info['roles'])
        
        # Message
        message = f"TAG: {tag['ETYPENAME']}\n\n"
        message += f"Roles: {total}\n"
        message += f"✅ Existing sentences: {existing}\n"
        message += f"❌ Missing sentences: {missing}\n\n"
        
        if missing == 0:
            message += "✓ This tag is complete!\n\n"
        
        message += "What do you want to do?"
        
        # Dialogue simple avec 3 boutons
        dialog = tk.Toplevel(self)
        dialog.title(f"Inject - {tag['ETYPENAME']}")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        # Message
        ttk.Label(dialog, text=message, justify=tk.LEFT, padding=10).pack()
        
        # Boutons
        btn_frame = ttk.Frame(dialog, padding=6)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        def on_skip():
            dialog.destroy()
            self.append_log(f"Skipped tag: {tag['ETYPENAME']}", 'INFO')
        
        def on_inject():
            # Générer aperçu des phrases à injecter
            preview = f"PREVIEW - Sentences to inject:\n\n"
            count = 0
            
            for role_id, info in sorted(tag_info['roles'].items()):
                if not info['has_phrase']:  # Phrase manquante
                    role_name = info['name']
                    is_principal = 'principal' in role_name.lower()
                    
                    # Générer phrases
                    phrase_en, phrase_fr = sentence_injector.generate_phrase(
                        tag['ETYPENAME'], role_name, is_principal
                    )
                    
                    count += 1
                    preview += f"[{role_id:05d}] {role_name}\n"
                    preview += f"  EN: {phrase_en}\n"
                    preview += f"  FR: {phrase_fr}\n\n"
            
            # Confirmation avec aperçu
            if messagebox.askyesno("Confirm Injection",
                                  preview + f"Inject {count} sentence(s)?",
                                  parent=dialog):
                dialog.destroy()
                self._execute_tag_injection(tag, tmg_dir, tmg_prefix, override=False)
        
        def on_regenerate():
            # Générer aperçu de TOUTES les phrases
            preview = f"⚠️ REGENERATE ALL - All sentences will be replaced:\n\n"
            count = 0
            
            for role_id, info in sorted(tag_info['roles'].items()):
                role_name = info['name']
                is_principal = 'principal' in role_name.lower()
                
                # Générer phrases
                phrase_en, phrase_fr = sentence_injector.generate_phrase(
                    tag['ETYPENAME'], role_name, is_principal
                )
                
                count += 1
                status = "REPLACE" if info['has_phrase'] else "NEW"
                preview += f"[{role_id:05d}] {role_name} [{status}]\n"
                preview += f"  EN: {phrase_en}\n"
                preview += f"  FR: {phrase_fr}\n\n"
            
            # Confirmation avec aperçu
            if messagebox.askyesno("⚠️ Confirm Regeneration",
                                  preview + f"⚠️ Regenerate {count} sentence(s)?\n\nExisting sentences will be REPLACED!",
                                  parent=dialog):
                dialog.destroy()
                self._execute_tag_injection(tag, tmg_dir, tmg_prefix, override=True)
        
        ttk.Button(btn_frame, text="Skip", command=on_skip).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Inject Missing", command=on_inject).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Regenerate ALL", command=on_regenerate).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    def _execute_tag_injection(self, tag, tmg_dir, tmg_prefix, override):
        """Exécute l'injection pour un tag"""
        self.set_running_state(True)
        mode = "REGENERATE" if override else "INJECT MISSING"
        self.status_label.config(text=f"{mode} for {tag['ETYPENAME']}...")
        
        thread = threading.Thread(
            target=self._execute_tag_injection_thread,
            args=(tag, tmg_dir, tmg_prefix, override),
            daemon=True
        )
        thread.start()
    
    def _execute_tag_injection_thread(self, tag, tmg_dir, tmg_prefix, override):
        """Thread d'exécution injection"""
        try:
            mode = "REGENERATE ALL" if override else "INJECT MISSING"
            self.append_log("\n" + "=" * 80, 'HEADER')
            self.append_log(f"SENTENCE INJECTION - {tag['ETYPENAME']} - {mode}", 'HEADER')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("")
            
            # Appeler sentence_injector
            stats = sentence_injector.inject_single_tag_mode(
                tag=tag,
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix,
                override=override,
                log_callback=self.thread_safe_log,
                language='EN'
            )
            
            self.append_log("")
            self.append_log(f"✓ Tag processed", 'SUCCESS')
            self.append_log("⚠️  IMPORTANT: Open TMG and run File > Maintenance > Reindex", 'WARNING')
            
            messagebox.showinfo("Success", 
                              f"Sentences processed for {tag['ETYPENAME']}!\n\n" +
                              "Remember to reindex in TMG.")
            self.status_label.config(text="Injection completed")
            
        except Exception as e:
            self.append_log(f"Error: {e}", 'ERROR')
            self.status_label.config(text="Error")
        finally:
            self.set_running_state(False)
    
    def run_sentence_inject_missing(self):
        """Lance injection phrases manquantes (tous tags)"""
        # SÉCURITÉ : Vérifier TMG IMMÉDIATEMENT
        if is_tmg_running():
            messagebox.showerror("⛔ TMG is Running!", 
                               "The Master Genealogist (TMG.EXE) is currently running.\n\n" +
                               "Please close TMG before running Sentence Injection.\n\n" +
                               "Modifying database files while TMG is open can cause corruption.")
            return
        
        if not self.tmg_project_path.get():
            messagebox.showerror("Error", "Please configure TMG Project")
            return
        
        # Charger tous les tags
        try:
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            
            custom_tags = sentence_injector.list_custom_tags_mode(
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix
            )
            
            # Analyser tous les tags pour trouver les manquantes
            tags_with_missing = []
            total_missing = 0
            
            for tag in custom_tags:
                tsentence_str = tag.get('TSENTENCE', '')
                if not tsentence_str:
                    continue
                
                roles_data = sentence_injector.parse_tsentence(tsentence_str)
                missing = sum(1 for d in roles_data.values() if not d['phrase'])
                
                if missing > 0:
                    tags_with_missing.append({
                        'tag': tag,
                        'missing': missing,
                        'roles_data': roles_data
                    })
                    total_missing += missing
            
            # Afficher aperçu
            if total_missing == 0:
                messagebox.showinfo("Info", "All tags are complete!\n\nNo missing sentences found.")
                return
            
            # Construire message aperçu
            preview = f"INJECT MISSING - Preview\n\n"
            preview += f"Tags with missing sentences: {len(tags_with_missing)}\n"
            preview += f"Total sentences to inject: {total_missing}\n\n"
            preview += "Tags:\n"
            
            for item in tags_with_missing[:10]:  # Montrer 10 premiers
                tag_name = item['tag']['ETYPENAME']
                preview += f"  • {tag_name}: {item['missing']} sentence(s)\n"
            
            if len(tags_with_missing) > 10:
                preview += f"  ... and {len(tags_with_missing) - 10} more tags\n"
            
            preview += f"\nProceed with injection?"
            
            result = messagebox.askyesno("Confirm Injection", preview)
            if not result:
                return
            
            # SECOND WARNING
            result2 = messagebox.askyesno("⚠️ Final Confirmation",
                                         f"You are about to inject {total_missing} sentences in {len(tags_with_missing)} tags.\n\n" +
                                         "Do you REALLY want to proceed?\n\n" +
                                         "Note: Restoring from backup is NOT easy!",
                                         icon='warning')
            if not result2:
                return
            
            # Lancer injection
            self.set_running_state(True)
            self.status_label.config(text="Injecting missing sentences...")
            
            thread = threading.Thread(target=self._run_sentence_inject_all_thread, 
                                     args=(False,), daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Cannot analyze tags: {e}")
    
    def run_sentence_regenerate_all(self):
        """Lance régénération TOUTES phrases (tous tags)"""
        # SÉCURITÉ : Vérifier TMG IMMÉDIATEMENT
        if is_tmg_running():
            messagebox.showerror("⛔ TMG is Running!", 
                               "The Master Genealogist (TMG.EXE) is currently running.\n\n" +
                               "Please close TMG before running Sentence Injection.\n\n" +
                               "Modifying database files while TMG is open can cause corruption.")
            return
        
        if not self.tmg_project_path.get():
            messagebox.showerror("Error", "Please configure TMG Project")
            return
        
        # Charger tous les tags
        try:
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            
            custom_tags = sentence_injector.list_custom_tags_mode(
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix
            )
            
            # Compter total de phrases
            total_sentences = 0
            total_tags = 0
            
            for tag in custom_tags:
                tsentence_str = tag.get('TSENTENCE', '')
                if not tsentence_str:
                    continue
                
                roles_data = sentence_injector.parse_tsentence(tsentence_str)
                if roles_data:
                    total_sentences += len(roles_data)
                    total_tags += 1
            
            # Construire message aperçu
            preview = f"⚠️ REGENERATE ALL - Preview\n\n"
            preview += f"Tags to process: {total_tags}\n"
            preview += f"Total sentences to regenerate: {total_sentences}\n\n"
            preview += "⚠️ ALL existing sentences will be REPLACED!\n"
            preview += "⚠️ Custom sentences will be LOST!\n"
            preview += "✓ Automatic backup will be created\n\n"
            preview += f"Proceed with regeneration?"
            
            result = messagebox.askyesno("⚠️ Confirm Regeneration", preview, icon='warning')
            if not result:
                return
            
            # SECOND WARNING
            result2 = messagebox.askyesno("⚠️⚠️ FINAL CONFIRMATION",
                                         f"LAST CHANCE TO CANCEL!\n\n" +
                                         f"You will REGENERATE {total_sentences} sentences in {total_tags} tags.\n\n" +
                                         "⚠️ ALL existing sentences will be REPLACED!\n" +
                                         "⚠️ Custom sentences will be PERMANENTLY LOST!\n\n" +
                                         "Restoring from backup is NOT easy!\n\n" +
                                         "Do you REALLY want to proceed?",
                                         icon='warning')
            if not result2:
                return
            
            # Lancer régénération
            self.set_running_state(True)
            self.status_label.config(text="Regenerating ALL sentences...")
            
            thread = threading.Thread(target=self._run_sentence_inject_all_thread, 
                                     args=(True,), daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Cannot analyze tags: {e}")
    
    def _run_sentence_inject_all_thread(self, override):
        """Thread injection TOUS les tags"""
        try:
            mode = "REGENERATE ALL" if override else "INJECT MISSING"
            self.thread_safe_log("\n" + "=" * 80, 'HEADER')
            self.thread_safe_log(f"SENTENCE INJECTION - {mode}", 'HEADER')
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log("")
            
            # Extraire dossier et préfixe
            pjc_path = self.tmg_project_path.get()
            tmg_dir = os.path.dirname(pjc_path)
            tmg_prefix = self.tmg_prefix.get()
            
            # Appeler sentence_injector
            stats = sentence_injector.inject_all_tags_mode(
                tmg_project_path=tmg_dir,
                tmg_prefix=tmg_prefix,
                override=override,
                log_callback=self.thread_safe_log,
                language='EN'
            )
            
            self.thread_safe_log("")
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log("FINAL SUMMARY", 'HEADER')
            self.thread_safe_log("=" * 80, 'HEADER')
            self.thread_safe_log(f"Tags processed: {stats.get('tags_processed', 0)}", 'INFO')
            if override:
                self.thread_safe_log(f"Sentences regenerated: {stats.get('phrases_replaced', 0)}", 'SUCCESS')
            else:
                self.thread_safe_log(f"Sentences injected: {stats.get('phrases_injected', 0)}", 'SUCCESS')
            self.thread_safe_log("")
            self.thread_safe_log("⚠️  IMPORTANT: Open TMG and run File > Maintenance > Reindex", 'WARNING')
            
            def show_success():
                messagebox.showinfo("Success", f"Sentence injection completed!\n\n" +
                                   f"Tags processed: {stats.get('tags_processed', 0)}\n" +
                                   f"Remember to reindex in TMG.")
            
            self.after(0, show_success)
            self.status_label.config(text="Injection completed")
            
        except Exception as e:
            self.thread_safe_log(f"Error: {e}", 'ERROR')
            self.status_label.config(text="Error")
        finally:
            self.set_running_state(False)
    
    # =========================================================================
    # CONFIG
    # =========================================================================
    def load_config(self):
        """Charge config"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                self.gedcom_path.set(config.get('gedcom_path', ''))
                pjc_path = config.get('tmg_project_path', '')
                self.tmg_project_path.set(pjc_path)
                if pjc_path:
                    self._extract_prefix_from_pjc(pjc_path)
                # Mettre à jour le menu avec les chemins chargés
                self.update_files_menu()
            except:
                pass
    
    def save_config(self):
        """Sauvegarde config"""
        config = {
            'gedcom_path': self.gedcom_path.get(),
            'tmg_project_path': self.tmg_project_path.get()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    
    # =========================================================================
    # HELP MENU FUNCTIONS
    # =========================================================================
    
    def show_about(self):
        """Show About dialog"""
        about_text = """TMG Suite v3.0

A comprehensive toolkit for importing genealogical data from Family Historian 
(or other GEDCOM sources) into The Master Genealogist (TMG).

FEATURES:
• Intelligent GEDCOM → TMG event and role mapping
• Witness injection with RED/GREEN logic (self-witness detection)
• Automated sentence structure generation for custom tags
• Bilingual support (English/French)
• Automatic backups before modifications
• TMG process detection (prevents database corruption)

WORKFLOW:
1. Export GEDCOM from Family Historian with proper settings
2. Import GEDCOM into TMG using standard import
3. Run Mapping Tool → Creates mapping.json
4. Run Role Injection → Imports witnesses into existing events
5. Run Sentence Injection → Generates sentence structures
6. Reindex TMG database (File > Maintenance > Reindex)

TECHNICAL:
• Python 3.8+ required
• Uses dbf.py for TMG database access
• Supports TMG v7, v8, and v9
• Cross-platform (Windows, macOS, Linux)

SECURITY:
• Idempotent injection (safe to run multiple times)
• Automatic backups in BACKUPS/ folders
• TMG process detection
• Dry-run mode for testing

LICENSE: MIT
DEVELOPED WITH: Claude (Anthropic)

For more information, visit:
https://github.com/your-repo/tmg-suite"""
        
        self._show_scrollable_dialog("About TMG Suite", about_text)
    
    def show_gedcom_guide(self):
        """Show GEDCOM configuration guide"""
        guide_text = """GEDCOM CONFIGURATION GUIDE

═══════════════════════════════════════════════════════════════

CRITICAL: Your GEDCOM file MUST be properly configured for witness 
import to work correctly.

═══════════════════════════════════════════════════════════════

FROM FAMILY HISTORIAN:
----------------------

1. File > Export GEDCOM

2. REQUIRED SETTINGS:
   ✅ GEDCOM Version: 5.5 (NOT 5.5.1)
   ✅ Character Set: ANSI (NOT UTF-8)
   ✅ Witness Role _SHAR: Keep Custom Tags ✅
   ✅ Include REFN: ✅ (Reference numbers - CRITICAL)
   
3. OPTIONAL BUT RECOMMENDED:
   ✅ Include sources
   ✅ Include notes
   ✅ Include media links

4. EXPORT LOCATION:
   Save to a dedicated folder (e.g., C:\\GEDCOM\\export.ged)

═══════════════════════════════════════════════════════════════

FROM OTHER SOFTWARE (Generic GEDCOM):
-------------------------------------

Your GEDCOM must contain:

1. _SHAR TAGS for witnesses:
   Example:
   1 BIRT
   2 DATE 1850
   2 _SHAR @I123@    ← Witness reference
   3 ROLE Witness    ← Role name

2. REFN (Reference Numbers) for ALL individuals:
   Example:
   0 @I001@ INDI
   1 NAME John /Doe/
   1 REFN 123        ← CRITICAL for matching

3. Event dates for proper event matching

4. ANSI encoding (Windows-1252 / CP1252)

═══════════════════════════════════════════════════════════════

AFTER EXPORT:
-------------

✅ VERIFY your GEDCOM contains _SHAR tags:
   Open the .ged file in a text editor and search for "_SHAR"
   
✅ CHECK that all persons have REFN:
   Search for "0 @I" and verify "1 REFN" follows

✅ VALIDATE encoding:
   File should display correctly with accented characters

═══════════════════════════════════════════════════════════════

COMMON ISSUES:
--------------

❌ "No witnesses found" → _SHAR tags not exported
   → Solution: Re-export with "Keep Custom Tags" enabled

❌ "Cannot match persons" → Missing REFN
   → Solution: Ensure REFN is included in export

❌ "Character encoding errors" → Wrong encoding
   → Solution: Use ANSI, not UTF-8

❌ "Events not matched" → Date format issues
   → Solution: Ensure dates are in standard format (DD MMM YYYY)

═══════════════════════════════════════════════════════════════"""
        
        self._show_scrollable_dialog("GEDCOM Configuration Guide", guide_text, width=700, height=600)
    
    def show_quickstart(self):
        """Show Quick Start guide"""
        quickstart_text = """QUICK START GUIDE

═══════════════════════════════════════════════════════════════

COMPLETE WORKFLOW FROM START TO FINISH

═══════════════════════════════════════════════════════════════

STEP 1: PREPARE YOUR GEDCOM
----------------------------
1. Open Family Historian
2. File > Export GEDCOM
3. Settings:
   • GEDCOM 5.5
   • ANSI encoding
   • Keep Custom Tags ✅
   • Include REFN ✅
4. Save as: C:\\GEDCOM\\myproject.ged

═══════════════════════════════════════════════════════════════

STEP 2: IMPORT INTO TMG (Standard Import)
------------------------------------------
⚠️ This step is done MANUALLY in TMG, not with this tool!

1. Open TMG
2. File > Import > GEDCOM
3. Follow TMG's import wizard:
   → Import individuals, families, basic events
   → DO NOT worry about witnesses yet
   → Assign TMG tags to custom events
4. Close TMG when import is complete

═══════════════════════════════════════════════════════════════

STEP 3: LAUNCH TMG SUITE
-------------------------
1. Run: python tmg_gui_v3.py
2. Configure paths:
   • GEDCOM File: C:\\GEDCOM\\myproject.ged
   • TMG Project: C:\\TMG\\Projects\\MyProject.PJC
   • Prefix will be detected automatically

═══════════════════════════════════════════════════════════════

STEP 4: PHASE 1 - MAPPING TOOL
-------------------------------
Purpose: Create mapping between GEDCOM and TMG events/roles

1. Click: Tools > 1. Mapping Tool > Generate Excel
   → Creates mapping_master.xlsx
   
2. ⚠️ VALIDATE the Excel file:
   • Open mapping_master.xlsx
   • Check "Events" tab: Verify GEDCOM → TMG mappings
   • Check "Roles" tab: Verify role translations
   • Fill in any empty cells in "TO VALIDATE" columns
   • Save and close Excel

3. Click: Tools > 1. Mapping Tool > Compile JSON
   → Creates mapping.json (used by injection)

✅ Phase 1 complete when you see: "JSON compiled successfully"

═══════════════════════════════════════════════════════════════

STEP 5: PHASE 2 - ROLE INJECTION
---------------------------------
Purpose: Import witnesses from GEDCOM into TMG events

⚠️ CLOSE TMG BEFORE THIS STEP!

1. Click: Tools > 2. Role Injection

2. Review the preview dialog:
   • Shows how many witnesses will be injected
   • Choose: [Dry-Run] to test, or [Real] to inject

3. If Dry-Run: Review log, then run again in Real mode

4. Wait for completion (may take 1-5 minutes)

✅ Phase 2 complete when you see: "ROLE INJECTION COMPLETED!"

═══════════════════════════════════════════════════════════════

STEP 6: PHASE 3 - SENTENCE INJECTION
-------------------------------------
Purpose: Generate sentence structures for custom TMG tags

⚠️ CLOSE TMG BEFORE THIS STEP!

Choose ONE of these options:

OPTION A - Inject ONE specific tag:
   1. Tools > 3. Sentence Injection > Inject ONE tag
   2. Select tag from dropdown
   3. Choose: [Skip] or [Regenerate]

OPTION B - Inject all missing sentences:
   1. Tools > 3. Sentence Injection > Inject MISSING only
   2. Review preview → Click [Continue]
   
OPTION C - Regenerate ALL sentences:
   1. Tools > 3. Sentence Injection > REGENERATE ALL
   2. ⚠️ This overwrites existing sentences!
   3. Review preview → Confirm → Click [Continue]

Wait for completion (may take 2-10 minutes for many tags)

✅ Phase 3 complete when you see sentences injected count

═══════════════════════════════════════════════════════════════

STEP 7: REINDEX TMG DATABASE (MANDATORY!)
------------------------------------------
⚠️ This is a MANUAL step in TMG - CANNOT be skipped!

1. Open TMG
2. File > Maintenance > Reindex All Files
3. Wait for reindex to complete
4. Check your events - witnesses should now be visible!

═══════════════════════════════════════════════════════════════

✅ YOU'RE DONE!

Your TMG database now contains:
• All witnesses imported from GEDCOM
• Proper sentence structures for custom tags
• Bilingual support (English/French)

═══════════════════════════════════════════════════════════════

TIPS:
-----
• Always test on a BACKUP project first
• Backups are created automatically
• You can re-run injections safely (idempotent)
• Check File > Files in use to see current paths
• Use File > Clear Logs to reset the log window

═══════════════════════════════════════════════════════════════"""
        
        self._show_scrollable_dialog("Quick Start Guide", quickstart_text, width=700, height=650)
    
    def show_troubleshooting(self):
        """Show troubleshooting guide"""
        troubleshooting_text = """TROUBLESHOOTING GUIDE

═══════════════════════════════════════════════════════════════

COMMON ISSUES AND SOLUTIONS

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "TMG is Running!" error
✅ SOLUTION:
   1. Close The Master Genealogist completely
   2. Check Task Manager (Ctrl+Shift+Esc)
   3. End any tmg7.exe, tmg8.exe, or tmg9.exe processes
   4. Try injection again

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "mapping.json not found"
✅ SOLUTION:
   1. Run Phase 1 first: Tools > Mapping Tool > Generate Excel
   2. Validate the Excel file
   3. Then: Tools > Mapping Tool > Compile JSON
   4. Check that mapping.json appears in the same folder

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "No witnesses found in GEDCOM"
✅ SOLUTION:
   1. Open your .ged file in a text editor
   2. Search for "_SHAR" - if not found, witnesses weren't exported
   3. Re-export GEDCOM from Family Historian:
      → GEDCOM 5.5
      → Keep Custom Tags ✅
      → Include _SHAR tags ✅
   4. Use the new GEDCOM file

═══════════════════════════════════════════════════════════════

❌ PROBLEM: Sentences not visible in TMG
✅ SOLUTION:
   This is the #1 issue - YOU MUST REINDEX!
   
   1. Open TMG
   2. File > Maintenance > Reindex All Files
   3. Wait for completion
   4. Check your events again
   
   WHY: TMG caches database structures. Reindex forces TMG
   to recognize the new sentence structures.

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "Backup failed" error
✅ SOLUTION:
   1. Close TMG completely
   2. Check you have write permissions to TMG project folder
   3. Check disk space (at least 100MB free)
   4. Try injection again

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "Cannot determine project prefix"
✅ SOLUTION:
   1. Make sure you selected a .PJC file (not a folder)
   2. The .PJC file must be inside the TMG project folder
   3. TMG .DBF files should be in the same folder
   4. Example structure:
      C:\\TMG\\Projects\\
         MyProject.PJC
         myproject_T.DBF
         myproject_G.DBF
         etc.

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "Events not matched" - Few witnesses injected
✅ SOLUTION:
   Events are matched by:
   • Person REFN (reference number)
   • Event type
   • Event date (±1 year tolerance)
   
   Check:
   1. All persons have REFN in GEDCOM
   2. Event types are mapped in mapping.json
   3. Dates are present and in standard format
   4. TMG import was completed successfully

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "Character encoding errors" / Strange characters
✅ SOLUTION:
   1. Re-export GEDCOM with ANSI encoding (NOT UTF-8)
   2. In Family Historian: Character Set = ANSI
   3. Check that accented characters display correctly

═══════════════════════════════════════════════════════════════

❌ PROBLEM: Injection is very slow
✅ SOLUTION:
   This is normal for large databases!
   
   • Role injection: ~30 seconds per 1000 events
   • Sentence injection: ~1 minute per 20 tags
   
   The interface may appear frozen - this is normal.
   Wait for the completion message.

═══════════════════════════════════════════════════════════════

❌ PROBLEM: Want to undo an injection
✅ SOLUTION:
   1. Go to your TMG project folder
   2. Look for BACKUPS/ or BACKUPS_SENTENCES/ folders
   3. Each backup has a timestamp
   4. Restore .DBF files from the backup folder
   5. Restart TMG

═══════════════════════════════════════════════════════════════

❌ PROBLEM: Python errors / Module not found
✅ SOLUTION:
   1. Check Python version: python --version (need 3.8+)
   2. Install requirements: pip install -r requirements.txt
   3. Required modules:
      • dbf.py
      • openpyxl
      • tkinter (usually included with Python)

═══════════════════════════════════════════════════════════════

❌ PROBLEM: "tmg_core_v3.py not found"
✅ SOLUTION:
   All these files must be in the same folder:
   • tmg_gui_v3.py
   • role_injector.py
   • sentence_injector.py
   • mapping_tool.py

═══════════════════════════════════════════════════════════════

STILL HAVING ISSUES?
--------------------

1. Check the log window in the GUI for detailed errors
2. Check the log file (shown at end of injection)
3. Enable dry-run mode to test without modifying data
4. Test on a BACKUP project first
5. Visit: https://github.com/your-repo/tmg-suite/issues

═══════════════════════════════════════════════════════════════"""
        
        self._show_scrollable_dialog("Troubleshooting", troubleshooting_text, width=700, height=650)
    
    def _show_scrollable_dialog(self, title, text, width=650, height=500):
        """Helper function to show scrollable text dialog"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry(f"{width}x{height}")
        
        # Frame with scrollbar
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget
        text_widget = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, 
                             font=("Courier New", 9), padx=10, pady=10)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=text_widget.yview)
        
        # Insert text
        text_widget.insert("1.0", text)
        text_widget.config(state=tk.DISABLED)  # Read-only
        
        # Close button
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy, width=15).pack()
        
        # Center dialog
        dialog.transient(self)
        dialog.grab_set()

if __name__ == "__main__":
    app = TMGSuiteGUI()
    app.mainloop()
