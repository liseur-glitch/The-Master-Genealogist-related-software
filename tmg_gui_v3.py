#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMG SUITE - Interface Graphique Moderne
========================================
Interface unifiée pour Mapping Tool + Witness Injector + Sentence Injection

Fonctionnalités:
- Sélection GEDCOM et projet TMG
- Exécution Mapping Tool avec logs visuels
- Exécution Injection rôles avec progress bar
- Exécution Injection phrases avec progress bar (NOUVEAU v3.0)
- Configuration sauvegardée
- Logs avec couleurs (INFO/SUCCESS/WARNING/ERROR)

Auteur: Claude
Date: 2026-02-05
Version: 3.0
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import sys
import json
import threading
from pathlib import Path

# Import du moteur métier
try:
    from tmg_core_v3 import TMGInjectorEngine, TMGMappingEngine, TMGSentenceInjectorEngine
except ImportError:
    print("❌ ERREUR: tmg_core_v3.py introuvable!")
    print("   Assurez-vous que tmg_core_v3.py est dans le même dossier.")
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_FILE = "tmg_suite_config.json"

DEFAULT_CONFIG = {
    'gedcom_path': '',
    'tmg_project_path': r'C:\Users\olivi\OneDrive\Documents\The Master Genealogist v9\Projects',
    'tmg_prefix': 'vierge_',
    'mapping_file': 'mapping.json',
    'window_geometry': '1000x750'
}

# =============================================================================
# CLASSE PRINCIPALE
# =============================================================================

class TMGSuiteGUI(tk.Tk):
    """Interface graphique principale de la TMG Suite"""
    
    def __init__(self):
        super().__init__()
        
        # Configuration fenêtre
        self.title("TMG Suite v3.0 - Mapping • Role Injection • Sentence Injection")
        self.geometry(DEFAULT_CONFIG['window_geometry'])
        
        # Chargement configuration
        self.config = self.load_config()
        
        # Variables
        self.gedcom_path = tk.StringVar(value=self.config.get('gedcom_path', ''))
        self.tmg_project_path = tk.StringVar(value=self.config.get('tmg_project_path', ''))
        self.tmg_prefix = tk.StringVar(value=self.config.get('tmg_prefix', 'vierge_'))
        self.mapping_file = tk.StringVar(value=self.config.get('mapping_file', 'mapping.json'))
        
        # État
        self.is_running = False
        
        # Construction de l'interface
        self.create_menu()
        self.create_widgets()
        
        # Handler de fermeture
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Sauvegarde la configuration"""
        self.config['gedcom_path'] = self.gedcom_path.get()
        self.config['tmg_project_path'] = self.tmg_project_path.get()
        self.config['tmg_prefix'] = self.tmg_prefix.get()
        self.config['mapping_file'] = self.mapping_file.get()
        self.config['window_geometry'] = self.geometry()
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
    
    # =========================================================================
    # INTERFACE
    # =========================================================================
    
    def create_menu(self):
        """Crée la barre de menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menu Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="1. Mapping Tool", command=self.run_mapping_tool, accelerator="Ctrl+1")
        tools_menu.add_command(label="2. Role Injection", command=self.run_injection, accelerator="Ctrl+2")
        tools_menu.add_command(label="3. Sentence Injection", command=self.run_sentence_injection, accelerator="Ctrl+3")
        tools_menu.add_separator()
        tools_menu.add_command(label="Clear Logs", command=self.clear_logs, accelerator="Ctrl+L")
        tools_menu.add_separator()
        tools_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Menu Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_docs)
        
        # Raccourcis clavier
        self.bind('<Control-1>', lambda e: self.run_mapping_tool())
        self.bind('<Control-2>', lambda e: self.run_injection())
        self.bind('<Control-3>', lambda e: self.run_sentence_injection())
        self.bind('<Control-l>', lambda e: self.clear_logs())
        self.bind('<Control-q>', lambda e: self.on_closing())
    
    def create_widgets(self):
        """Crée tous les widgets de l'interface"""
        
        # =================================================================
        # FRAME CONFIGURATION
        # =================================================================
        config_frame = ttk.LabelFrame(self, text="Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Ligne 1: GEDCOM
        ttk.Label(config_frame, text="GEDCOM File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.gedcom_path, width=60).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(config_frame, text="Browse...", command=self.select_gedcom).grid(row=0, column=2, padx=5, pady=5)
        
        # Ligne 2: TMG Project
        ttk.Label(config_frame, text="TMG Project Folder:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.tmg_project_path, width=60).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(config_frame, text="Browse...", command=self.select_tmg_project).grid(row=1, column=2, padx=5, pady=5)
        
        # Ligne 3: TMG Prefix
        ttk.Label(config_frame, text="TMG Prefix:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.tmg_prefix, width=20).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(config_frame, text="(ex: vierge_, finalopera_, test_)", foreground='gray').grid(row=2, column=1, sticky=tk.E, padx=5)
        
        # Ligne 4: Mapping File
        ttk.Label(config_frame, text="Mapping File:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.mapping_file, width=30).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Configurer colonnes pour resize
        config_frame.columnconfigure(1, weight=1)
        
        # =================================================================
        # FRAME ACTIONS
        # =================================================================
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Boutons principaux
        self.btn_mapping = ttk.Button(
            action_frame,
            text="▶ 1. Run Mapping Tool",
            command=self.run_mapping_tool,
            width=25
        )
        self.btn_mapping.pack(side=tk.LEFT, padx=5)
        
        self.btn_injection = ttk.Button(
            action_frame,
            text="▶ 2. Run Role Injection",
            command=self.run_injection,
            width=25
        )
        self.btn_injection.pack(side=tk.LEFT, padx=5)
        
        self.btn_sentence = ttk.Button(
            action_frame,
            text="▶ 3. Run Sentence Injection",
            command=self.run_sentence_injection,
            width=25
        )
        self.btn_sentence.pack(side=tk.LEFT, padx=5)
        
        # Bouton Stop
        self.btn_stop = ttk.Button(
            action_frame,
            text="⏹ Stop",
            command=self.stop_operation,
            state=tk.DISABLED,
            width=15
        )
        self.btn_stop.pack(side=tk.RIGHT, padx=5)
        
        # =================================================================
        # PROGRESS BAR
        # =================================================================
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=100
        )
        self.progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready", width=30)
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # =================================================================
        # LOG AREA
        # =================================================================
        log_frame = ttk.LabelFrame(self, text="Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Zone de texte avec scrollbar
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=20,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configuration des tags pour couleurs
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('SUCCESS', foreground='#00AA00', font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('WARNING', foreground='#FF8800', font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('ERROR', foreground='#DD0000', font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('HEADER', foreground='#0066CC', font=('Consolas', 10, 'bold'))
        
        # =================================================================
        # STATUS BAR
        # =================================================================
        status_frame = ttk.Frame(self, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Message initial
        self.append_log("=" * 80, 'HEADER')
        self.append_log("TMG SUITE v2.0 - Integrated Tools", 'HEADER')
        self.append_log("=" * 80, 'HEADER')
        self.append_log("")
        self.append_log("Welcome! Configure your files above and select a tool to run.", 'INFO')
        self.append_log("")
    
    # =========================================================================
    # SÉLECTION DE FICHIERS
    # =========================================================================
    
    def select_gedcom(self):
        """Sélectionne le fichier GEDCOM"""
        filename = filedialog.askopenfilename(
            title="Select GEDCOM File",
            filetypes=[("GEDCOM files", "*.ged"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.gedcom_path.get()) or os.path.expanduser("~")
        )
        if filename:
            self.gedcom_path.set(filename)
            self.save_config()
    
    def select_tmg_project(self):
        """Sélectionne le dossier du projet TMG"""
        folder = filedialog.askdirectory(
            title="Select TMG Project Folder",
            initialdir=self.tmg_project_path.get() or os.path.expanduser("~")
        )
        if folder:
            self.tmg_project_path.set(folder)
            self.save_config()
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    def append_log(self, message, level='INFO'):
        """Ajoute un message au log avec couleur selon le niveau"""
        self.log_text.config(state=tk.NORMAL)
        
        # Préfixes selon niveau
        prefix = {
            'INFO': '  ',
            'SUCCESS': '✅ ',
            'WARNING': '⚠️  ',
            'ERROR': '❌ ',
            'HEADER': ''
        }.get(level, '  ')
        
        self.log_text.insert(tk.END, prefix + message + '\n', level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Mise à jour interface
        self.update_idletasks()
    
    def clear_logs(self):
        """Efface tous les logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.append_log("Logs cleared", 'INFO')
    
    def update_progress(self, current, total, message=""):
        """Met à jour la barre de progression"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress['value'] = percentage
        
        if message:
            self.progress_label.config(text=message)
            self.status_label.config(text=message)
        
        self.update_idletasks()
    
    # =========================================================================
    # EXÉCUTION DES OUTILS
    # =========================================================================
    
    def validate_configuration(self):
        """Valide que tous les fichiers/dossiers existent"""
        if not self.gedcom_path.get():
            messagebox.showerror("Error", "Please select a GEDCOM file")
            return False
        
        if not os.path.exists(self.gedcom_path.get()):
            messagebox.showerror("Error", f"GEDCOM file not found:\n{self.gedcom_path.get()}")
            return False
        
        if not self.tmg_project_path.get():
            messagebox.showerror("Error", "Please select TMG project folder")
            return False
        
        if not os.path.exists(self.tmg_project_path.get()):
            messagebox.showerror("Error", f"TMG project folder not found:\n{self.tmg_project_path.get()}")
            return False
        
        if not self.tmg_prefix.get():
            messagebox.showerror("Error", "Please enter TMG prefix")
            return False
        
        return True
    
    def set_running_state(self, running):
        """Active/désactive les boutons selon l'état d'exécution"""
        self.is_running = running
        
        state = tk.DISABLED if running else tk.NORMAL
        self.btn_mapping.config(state=state)
        self.btn_injection.config(state=state)
        
        stop_state = tk.NORMAL if running else tk.DISABLED
        self.btn_stop.config(state=stop_state)
    
    def run_mapping_tool(self):
        """Lance le Mapping Tool"""
        if not self.validate_configuration():
            return
        
        if self.is_running:
            messagebox.showwarning("Warning", "An operation is already running")
            return
        
        # Lancement dans un thread séparé
        thread = threading.Thread(target=self._run_mapping_tool_thread, daemon=True)
        thread.start()
    
    def _run_mapping_tool_thread(self):
        """Thread d'exécution du Mapping Tool"""
        self.set_running_state(True)
        
        try:
            self.append_log("", 'INFO')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("MAPPING TOOL", 'HEADER')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("", 'INFO')
            
            # Créer le moteur
            engine = TMGMappingEngine(
                self.gedcom_path.get(),
                self.tmg_project_path.get(),
                self.tmg_prefix.get()
            )
            
            # Connecter les callbacks
            engine.set_log_callback(self.append_log)
            engine.set_progress_callback(self.update_progress)
            
            # Exécution
            result = engine.generate_mapping_excel()
            
            self.append_log("", 'INFO')
            self.append_log(f"Excel file created: {result['excel_path']}", 'SUCCESS')
            self.append_log("", 'INFO')
            
        except Exception as e:
            self.append_log("", 'INFO')
            self.append_log(f"Fatal error: {str(e)}", 'ERROR')
            self.append_log("", 'INFO')
            messagebox.showerror("Error", f"Mapping Tool failed:\n\n{str(e)}")
        
        finally:
            self.set_running_state(False)
            self.update_progress(0, 100, "Ready")
    
    def run_injection(self):
        """Lance l'injection de témoins"""
        if not self.validate_configuration():
            return
        
        if self.is_running:
            messagebox.showwarning("Warning", "An operation is already running")
            return
        
        # Vérifier que mapping.json existe
        if not os.path.exists(self.mapping_file.get()):
            response = messagebox.askyesno(
                "Mapping File Missing",
                f"{self.mapping_file.get()} not found!\n\n"
                "You need to run the Mapping Tool first.\n\n"
                "Run Mapping Tool now?"
            )
            if response:
                self.run_mapping_tool()
            return
        
        # Confirmation
        response = messagebox.askyesno(
            "Confirm Injection",
            "This will modify your TMG database.\n"
            "A backup will be created automatically.\n\n"
            "Continue?"
        )
        
        if not response:
            return
        
        # Lancement dans un thread séparé
        thread = threading.Thread(target=self._run_injection_thread, daemon=True)
        thread.start()
    
    def _run_injection_thread(self):
        """Thread d'exécution de l'injection"""
        self.set_running_state(True)
        
        try:
            self.append_log("", 'INFO')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("WITNESS INJECTION", 'HEADER')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("", 'INFO')
            
            # Créer le moteur
            engine = TMGInjectorEngine(
                self.gedcom_path.get(),
                self.tmg_project_path.get(),
                self.tmg_prefix.get(),
                self.mapping_file.get()
            )
            
            # Connecter les callbacks
            engine.set_log_callback(self.append_log)
            engine.set_progress_callback(self.update_progress)
            
            # Exécution
            stats = engine.inject_witnesses(dry_run=False)
            
            self.append_log("", 'INFO')
            self.append_log("DONE!", 'SUCCESS')
            self.append_log(f"  Witnesses (normal)   : {stats['ok']}", 'SUCCESS')
            self.append_log(f"  Witnesses (self)     : {stats['principal']}", 'SUCCESS')
            self.append_log(f"  Skipped (duplicates) : {stats['skip']}", 'INFO')
            self.append_log(f"  Errors               : {stats['error']}", 'ERROR' if stats['error'] > 0 else 'INFO')
            self.append_log("", 'INFO')
            
            messagebox.showinfo(
                "Success",
                f"Injection completed!\n\n"
                f"Injected: {stats['ok']} + {stats['principal']} (self)\n"
                f"Skipped: {stats['skip']}\n"
                f"Errors: {stats['error']}"
            )
            
        except Exception as e:
            self.append_log("", 'INFO')
            self.append_log(f"Fatal error: {str(e)}", 'ERROR')
            self.append_log("", 'INFO')
            messagebox.showerror("Error", f"Injection failed:\n\n{str(e)}")
        
        finally:
            self.set_running_state(False)
            self.update_progress(0, 100, "Ready")
    
    def stop_operation(self):
        """Arrête l'opération en cours (non implémenté pour l'instant)"""
        messagebox.showinfo("Info", "Stop functionality not yet implemented")
    
    # =========================================================================
    # MENUS HELP
    # =========================================================================
    
    def run_sentence_injection(self):
        """Lance l'injection de phrases"""
        # Valider seulement TMG (pas besoin de GEDCOM)
        if not self.tmg_project_path.get() or not self.tmg_prefix.get():
            messagebox.showerror(
                "Configuration Error",
                "Please specify TMG Project Path and Prefix"
            )
            return
        
        if self.is_running:
            messagebox.showwarning("Warning", "An operation is already running")
            return
        
        # Confirmation
        response = messagebox.askyesno(
            "Confirm Sentence Injection",
            "This will inject missing sentence structures in ALL custom tags.\n"
            "A backup will be created automatically.\n\n"
            "Continue?"
        )
        
        if not response:
            return
        
        # Lancement dans un thread séparé
        thread = threading.Thread(target=self._run_sentence_injection_thread, daemon=True)
        thread.start()
    
    def _run_sentence_injection_thread(self):
        """Thread d'exécution de l'injection de phrases"""
        self.set_running_state(True)
        
        try:
            self.append_log("", 'INFO')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("SENTENCE INJECTION", 'HEADER')
            self.append_log("=" * 80, 'HEADER')
            self.append_log("", 'INFO')
            
            # Créer le moteur
            engine = TMGSentenceInjectorEngine(
                self.tmg_project_path.get(),
                self.tmg_prefix.get()
            )
            
            # Connecter les callbacks
            engine.set_log_callback(self.append_log)
            engine.set_progress_callback(self.update_progress)
            
            # Exécution
            success = engine.inject_all_tags()
            
            if success:
                stats = engine.stats
                
                self.append_log("", 'INFO')
                self.append_log("DONE!", 'SUCCESS')
                self.append_log("", 'INFO')
                
                messagebox.showinfo(
                    "Success",
                    f"Sentence injection completed!\n\n"
                    f"Tags processed: {stats['tags_processed']}\n"
                    f"Phrases injected: {stats['phrases_injected']}\n"
                    f"Tags skipped: {stats['tags_skipped']}\n"
                    f"Errors: {stats['errors']}\n\n"
                    f"⚠️ Important: Open TMG and run\n"
                    f"File > Maintenance > Reindex"
                )
            else:
                messagebox.showerror(
                    "Error",
                    "Sentence injection failed!\nCheck logs for details."
                )
            
        except Exception as e:
            self.append_log(f"FATAL ERROR: {e}", 'ERROR')
            messagebox.showerror(
                "Fatal Error",
                f"An unexpected error occurred:\n{e}"
            )
        
        finally:
            self.set_running_state(False)
            self.update_status("Sentence injection completed")
    
    def show_about(self):
        """Affiche la fenêtre About"""
        messagebox.showinfo(
            "About TMG Suite",
            "TMG Suite v2.0\n"
            "Integrated Mapping & Injection Tools\n\n"
            "Components:\n"
            "• Mapping Tool - Scan GEDCOM & TMG\n"
            "• Witness Injector - Inject witnesses into TMG\n\n"
            "Based on:\n"
            "• super_injecteur_v16_clean.py\n"
            "• mapping_tool.py\n\n"
            "Authors: Claude, Olivier, Gemini\n"
            "Date: 2026-02-04"
        )
    
    def show_docs(self):
        """Affiche la documentation"""
        docs = """
TMG SUITE - QUICK START GUIDE

1. CONFIGURATION
   - Select your GEDCOM file
   - Select TMG project folder
   - Enter TMG prefix (ex: vierge_)
   
2. MAPPING TOOL (First time)
   - Click "Run Mapping Tool"
   - Review generated mapping_master.xlsx
   - Validate event and role mappings
   
3. WITNESS INJECTION
   - Click "Run Injection"
   - A backup is created automatically
   - Witnesses are injected into TMG
   
4. VERIFY IN TMG
   - Open your TMG project
   - Check injected witnesses
   - Verify roles and relationships

For more information, see README_TMG_SUITE.md
        """
        
        # Créer une fenêtre popup
        docs_window = tk.Toplevel(self)
        docs_window.title("Documentation")
        docs_window.geometry("600x400")
        
        text = scrolledtext.ScrolledText(docs_window, wrap=tk.WORD, font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, docs)
        text.config(state=tk.DISABLED)
        
        ttk.Button(docs_window, text="Close", command=docs_window.destroy).pack(pady=10)
    
    # =========================================================================
    # FERMETURE
    # =========================================================================
    
    def on_closing(self):
        """Gère la fermeture de l'application"""
        if self.is_running:
            response = messagebox.askyesno(
                "Confirm Exit",
                "An operation is currently running.\n\n"
                "Are you sure you want to exit?"
            )
            if not response:
                return
        
        # Sauvegarder la configuration
        self.save_config()
        
        # Fermer
        self.destroy()

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main():
    """Lance l'application"""
    app = TMGSuiteGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
