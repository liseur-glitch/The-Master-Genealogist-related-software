#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sentence_injector.py - VERSION 5.0
===================================
Injection de phrases manquantes dans les tags custom TMG.

NOUVEAU v5.0:
- Menu interactif complet (1-5)
- Option "Traiter TOUS" avec sous-menu
- Mode OVERRIDE : Régénérer toutes les phrases
- Mode dual : CLI standalone OU intégration GUI
- Stats enrichies (injectées vs remplacées)

Usage:
  python sentence_injector.py   →  Mode interactif

Auteur: Claude
Date: 2026-02-06
Version: 5.0
"""

import sys
import os
import re
import shutil
from datetime import datetime
import platform
import subprocess

try:
    import dbf
except ImportError:
    print("ERREUR: pip install dbf.py")
    sys.exit(1)

import tkinter as tk
from tkinter import filedialog

# =============================================================================
# CONFIGURATION
# =============================================================================
TMG_PATH = None
TMG_PREFIX = None
LOG_CALLBACK = None  # Callback optionnel pour logs vers GUI
LANGUAGE = 'EN'  # Langue par défaut (EN ou FR)

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
        except Exception as e:
            # Si la vérification échoue, on continue (mieux que bloquer)
            print(f"⚠️  Warning: Cannot check if TMG is running: {e}")
            return False
    return False  # Sur non-Windows, on assume que c'est OK

# =============================================================================
# TRADUCTIONS
# =============================================================================
TEXTS = {
    'EN': {
        # Menu principal
        'menu_title': 'MAIN MENU',
        'menu_1': '1. List custom tags',
        'menu_2': '2. Examine a tag',
        'menu_3': '3. Inject sentences in ONE tag',
        'menu_4': '4. Process ALL tags',
        'menu_5': '5. Quit',
        'menu_choice': 'Choice (1-5): ',
        
        # Sous-menu traiter tous
        'submenu_title': 'PROCESS ALL TAGS',
        'submenu_1': '1. Inject MISSING sentences only (default)',
        'submenu_2': '2. REGENERATE ALL sentences (overwrites existing)',
        'submenu_3': '3. Back to main menu',
        'submenu_choice': 'Choice (1-3): ',
        
        # Messages généraux
        'project': 'Project',
        'prefix': 'Prefix',
        'file_found': 'File found',
        'file_not_found': 'File not found',
        'custom_tags_found': 'custom tag(s) found',
        'no_custom_tags': 'No custom tags found',
        'goodbye': 'Goodbye!',
        'invalid_choice': 'Invalid choice',
        'cancelled': 'Cancelled',
        
        # Sélection projet
        'select_pjc': '🖱️  Select your TMG project file (.PJC)...',
        'select_pjc_title': 'Select TMG project file (.PJC)',
        'tmg_project': 'TMG Project',
        'all_files': 'All files',
        'prefix_detected': '✓ Prefix',
        'project_path': '✓ Project',
        'cannot_determine_prefix': 'Cannot determine project prefix.',
        'file_not_found_error': 'not found.',
        
        # Liste tags
        'custom_tags_list': 'CUSTOM TAGS:',
        
        # Examiner tag
        'tag': 'TAG',
        'roles': 'ROLES',
        'no_roles': 'No roles defined',
        'sentence_ok': 'Sentence OK',
        'sentence_missing': 'Sentence MISSING',
        
        # Injection individuelle
        'tag_complete': 'Tag already complete',
        'sentences': 'sentence(s)',
        'existing_sentences_warning': 'This tag already has',
        'existing_sentence': 'existing sentence(s).',
        'missing_will_be_added': 'missing sentence(s) will be added.',
        'skip_tag': 'Skip this tag',
        'inject_missing': 'Inject missing sentences',
        'regenerate_all': 'REGENERATE ALL sentences',
        'choice': 'Choice',
        'tag_skipped': 'Tag skipped',
        'override_mode': 'OVERRIDE mode activated - All sentences will be regenerated!',
        
        # Aperçu phrases
        'sentence_preview': 'SENTENCE PREVIEW:',
        'inject': 'INJECT',
        'regenerate': 'REGENERATE',
        'modify_sentences': 'Modify',
        'confirm_yn': '(Y/n): ',
        
        # Backup
        'creating_backup': 'Creating automatic backup...',
        'backup_created': 'Backup created',
        'backup_failed': 'Backup failed - STOPPED',
        
        # Résultats
        'tag_updated': 'Tag updated',
        'sentences_injected': 'sentence(s) injected',
        'sentences_regenerated': 'sentence(s) regenerated',
        'important': 'IMPORTANT: Open TMG and run',
        'reindex': 'File > Maintenance > Reindex',
        'error': 'ERROR',
        'backup_available': 'Backup available',
        
        # Injection en masse
        'mass_injection_title': 'MISSING SENTENCES INJECTION',
        'mass_regeneration_title': 'REGENERATE ALL SENTENCES',
        'override_warning_1': 'WARNING: OVERRIDE mode activated!',
        'override_warning_2': '→ All existing sentences will be REPLACED',
        'override_warning_3': '→ Custom sentences will be LOST',
        'override_warning_4': '→ A backup will be created automatically',
        'confirm_regeneration': 'Confirm regeneration? (yes/no): ',
        'tags_detected': 'custom tag(s) detected',
        'no_roles_found': 'No roles',
        'already_complete': 'Already complete',
        
        # Statistiques finales
        'final_summary': 'FINAL SUMMARY',
        'total_custom_tags': 'Total custom tags',
        'tags_processed': 'Tags processed',
        'sentences_injected_stat': 'Sentences injected',
        'sentences_regenerated_stat': 'Sentences regenerated',
        'tags_skipped': 'Tags skipped',
        'errors': 'Errors',
        
        # Numéro
        'number': 'Number',
    },
    'FR': {
        # Menu principal
        'menu_title': 'MENU PRINCIPAL',
        'menu_1': '1. Lister les tags custom',
        'menu_2': '2. Examiner un tag',
        'menu_3': '3. Injecter phrases dans UN tag',
        'menu_4': '4. Traiter TOUS les tags',
        'menu_5': '5. Quitter',
        'menu_choice': 'Choix (1-5) : ',
        
        # Sous-menu traiter tous
        'submenu_title': 'TRAITER TOUS LES TAGS',
        'submenu_1': '1. Injecter phrases MANQUANTES seulement (défaut)',
        'submenu_2': '2. RÉGÉNÉRER TOUTES les phrases (écrase existantes)',
        'submenu_3': '3. Retour au menu principal',
        'submenu_choice': 'Choix (1-3) : ',
        
        # Messages généraux
        'project': 'Projet',
        'prefix': 'Préfixe',
        'file_found': 'Fichier trouvé',
        'file_not_found': 'Fichier introuvable',
        'custom_tags_found': 'tag(s) custom trouvé(s)',
        'no_custom_tags': 'Aucun tag custom trouvé',
        'goodbye': 'Au revoir !',
        'invalid_choice': 'Choix invalide',
        'cancelled': 'Annulé',
        
        # Sélection projet
        'select_pjc': '🖱️  Sélectionnez votre fichier projet TMG (.PJC)...',
        'select_pjc_title': 'Sélectionnez le fichier projet TMG (.PJC)',
        'tmg_project': 'Projet TMG',
        'all_files': 'Tous',
        'prefix_detected': '✓ Préfixe',
        'project_path': '✓ Projet',
        'cannot_determine_prefix': 'Impossible de déterminer le préfixe du projet.',
        'file_not_found_error': 'introuvable.',
        
        # Liste tags
        'custom_tags_list': 'TAGS CUSTOM :',
        
        # Examiner tag
        'tag': 'TAG',
        'roles': 'RÔLES',
        'no_roles': 'Aucun rôle défini',
        'sentence_ok': 'Phrase OK',
        'sentence_missing': 'Phrase MANQUANTE',
        
        # Injection individuelle
        'tag_complete': 'Tag déjà complet',
        'sentences': 'phrase(s)',
        'existing_sentences_warning': 'Ce tag a déjà',
        'existing_sentence': 'phrase(s) existante(s).',
        'missing_will_be_added': 'phrase(s) manquante(s) seront ajoutées.',
        'skip_tag': 'Sauter ce tag',
        'inject_missing': 'Injecter phrases manquantes',
        'regenerate_all': 'RÉGÉNÉRER TOUTES les phrases',
        'choice': 'Choix',
        'tag_skipped': 'Tag sauté',
        'override_mode': 'Mode OVERRIDE activé - Toutes les phrases seront régénérées !',
        
        # Aperçu phrases
        'sentence_preview': 'APERÇU DES PHRASES :',
        'inject': 'INJECTER',
        'regenerate': 'RÉGÉNÉRER',
        'modify_sentences': 'Modifier',
        'confirm_yn': '(O/n) : ',
        
        # Backup
        'creating_backup': 'Création backup automatique...',
        'backup_created': 'Backup créé',
        'backup_failed': 'Backup échoué - ARRÊT',
        
        # Résultats
        'tag_updated': 'Tag mis à jour',
        'sentences_injected': 'phrase(s) injectée(s)',
        'sentences_regenerated': 'phrase(s) régénérée(s)',
        'important': 'IMPORTANT : Ouvrez TMG et lancez',
        'reindex': 'File > Maintenance > Reindex',
        'error': 'ERREUR',
        'backup_available': 'Backup disponible',
        
        # Injection en masse
        'mass_injection_title': 'INJECTION PHRASES MANQUANTES',
        'mass_regeneration_title': 'RÉGÉNÉRATION TOUTES LES PHRASES',
        'override_warning_1': 'ATTENTION : Mode OVERRIDE activé !',
        'override_warning_2': '→ Toutes les phrases existantes seront REMPLACÉES',
        'override_warning_3': '→ Les phrases personnalisées seront PERDUES',
        'override_warning_4': '→ Un backup sera créé automatiquement',
        'confirm_regeneration': 'Confirmer la régénération ? (yes/no) : ',
        'tags_detected': 'tag(s) custom détecté(s)',
        'no_roles_found': 'Aucun rôle',
        'already_complete': 'Déjà complet',
        
        # Statistiques finales
        'final_summary': 'RÉSUMÉ FINAL',
        'total_custom_tags': 'Tags custom total',
        'tags_processed': 'Tags traités',
        'sentences_injected_stat': 'Phrases injectées',
        'sentences_regenerated_stat': 'Phrases régénérées',
        'tags_skipped': 'Tags ignorés',
        'errors': 'Erreurs',
        
        # Numéro
        'number': 'Numéro',
    }
}

def t(key):
    """Retourne le texte traduit selon la langue courante"""
    return TEXTS.get(LANGUAGE, TEXTS['EN']).get(key, key)

def ask_language():
    """Demande la langue au démarrage (CLI uniquement)"""
    print("\n" + "="*50)
    print("TMG SENTENCE INJECTOR v5.0")
    print("="*50)
    print("\n1. English")
    print("2. Français")
    print()
    
    choice = input("Language / Langue (1-2): ").strip()
    
    global LANGUAGE
    if choice == '2':
        LANGUAGE = 'FR'
    else:
        LANGUAGE = 'EN'
    
    return LANGUAGE

def log(message, level='INFO'):
    """Log message - utilise callback si fourni, sinon print()"""
    if LOG_CALLBACK:
        LOG_CALLBACK(message, level)
    else:
        print(message)

# =============================================================================
# SÉLECTION PROJET TMG
# =============================================================================
def _extract_prefix(pjc_path):
    """Déduit le préfixe depuis le nom du fichier .PJC"""
    basename = os.path.splitext(os.path.basename(pjc_path))[0]
    if basename.endswith('__'):
        prefix = basename[:-1]
    elif basename.endswith('_'):
        prefix = basename
    else:
        prefix = basename + '_'
    
    tmg_dir = os.path.dirname(pjc_path)
    tdbf = os.path.join(tmg_dir, f"{prefix}T.DBF")
    if not os.path.exists(tdbf):
        return None
    return prefix

def select_tmg_project_gui():
    """Ouvre dialogue GUI pour choisir projet TMG"""
    global TMG_PATH, TMG_PREFIX
    
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    log(f"\n{t('select_pjc')}")
    pjc_path = filedialog.askopenfilename(
        title=t('select_pjc_title'),
        filetypes=[(t('tmg_project'), "*.PJC"), (t('all_files'), "*.*")]
    )
    
    if not pjc_path:
        log(f"❌ {t('cancelled')}", 'ERROR')
        sys.exit(0)
    
    TMG_PATH = os.path.dirname(pjc_path)
    log(f"   {t('project_path')} : {pjc_path}", 'SUCCESS')
    
    root.destroy()
    
    TMG_PREFIX = _extract_prefix(pjc_path)
    if not TMG_PREFIX:
        log(f"❌ {t('cannot_determine_prefix')}", 'ERROR')
        sys.exit(1)
    log(f"   {t('prefix_detected')} : {TMG_PREFIX}", 'SUCCESS')
    
    tdbf = os.path.join(TMG_PATH, f"{TMG_PREFIX}T.DBF")
    if not os.path.exists(tdbf):
        log(f"❌ {tdbf} {t('file_not_found_error')}", 'ERROR')
        sys.exit(1)

def get_tmg_file(suffix):
    """Construit chemin fichier TMG"""
    return os.path.join(TMG_PATH, f"{TMG_PREFIX}{suffix}.DBF")

# =============================================================================
# BACKUP
# =============================================================================
def create_backup():
    """Crée backup complet (DBF + FPT + CDX)"""
    t_dbf_path = get_tmg_file("T")
    
    if not os.path.exists(t_dbf_path):
        log(f"Fichier introuvable : {t_dbf_path}", 'ERROR')
        return None
    
    backup_dir = os.path.join(TMG_PATH, "BACKUPS_SENTENCES")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [
        (f"{TMG_PREFIX}T.dbf", f"{TMG_PREFIX}T_BACKUP_{timestamp}.dbf"),
        (f"{TMG_PREFIX}T.fpt", f"{TMG_PREFIX}T_BACKUP_{timestamp}.fpt"),
        (f"{TMG_PREFIX}T.cdx", f"{TMG_PREFIX}T_BACKUP_{timestamp}.cdx")
    ]
    
    try:
        for src_file, backup_name in files_to_backup:
            src_path = os.path.join(TMG_PATH, src_file)
            
            if os.path.exists(src_path):
                backup_path = os.path.join(backup_dir, backup_name)
                shutil.copy2(src_path, backup_path)
        
        log(f"✅ Backup créé : {backup_dir}", 'SUCCESS')
        return backup_dir
        
    except Exception as e:
        log(f"❌ Erreur backup : {e}", 'ERROR')
        return None

# =============================================================================
# PARSING TSENTENCE
# =============================================================================
def parse_tsentence(tsentence_str):
    """
    Parse le champ TSENTENCE pour extraire rôles et phrases
    Format TMG : [L=LANG] suivi de [R=00001]phrase [R=00002]phrase
    """
    roles_data = {}
    
    # 1. Parser les RÔLES dans [LABELS:]..[:LABELS]
    if '[LABELS:]' in tsentence_str and '[:LABELS]' in tsentence_str:
        labels_section = tsentence_str.split('[LABELS:]')[1].split('[:LABELS]')[0]
        
        # [RL=00001][L=ENGLISH]Name[L=FRENCH]Nom
        regex_role = re.compile(r'\[RL=(\d+)\](.*?)(?=\[RL=|$)', re.DOTALL)
        regex_lbl = re.compile(r'\[L=([^\]]+)\]([^\[]+)')
        
        for m in regex_role.finditer(labels_section):
            rid = int(m.group(1))
            block = m.group(2)
            
            if rid not in roles_data:
                roles_data[rid] = {'role': {}, 'phrase': {}}
            
            for lm in regex_lbl.finditer(block):
                lang = lm.group(1).upper()
                text = lm.group(2).strip()
                roles_data[rid]['role'][lang] = text
    
    # 2. Parser les PHRASES - par blocs de langue [L=...]
    # Les phrases sont APRÈS [:LABELS]
    if '[:LABELS]' in tsentence_str:
        phrases_section = tsentence_str.split('[:LABELS]')[1]
    else:
        phrases_section = tsentence_str
    
    # Découper par marqueurs de langue [L=...]
    lang_blocks = re.split(r'(\[L=[^\]]+\])', phrases_section)
    current_lang = None
    
    for block in lang_blocks:
        # Si c'est un marqueur de langue [L=FRENCH]
        if block.startswith('[L='):
            m = re.match(r'\[L=([^\]]+)\]', block)
            if m:
                current_lang = m.group(1).upper()
                if current_lang == 'ENGLISH':
                    current_lang = 'ENGLISHUK'
        # Sinon c'est du contenu avec des [R=...]
        elif current_lang and block.strip():
            # CORRECTION : Capturer jusqu'au prochain [R= ou [L= ou fin
            # Pas [^\[] car les phrases contiennent [P], [M], [D], [L] !
            regex_phrase = re.compile(r'\[R=(\d+)\](.*?)(?=\[R=|\[L=|$)', re.DOTALL)
            for m in regex_phrase.finditer(block):
                rid = int(m.group(1))
                text = m.group(2).strip()
                
                if text:  # Seulement si phrase non vide
                    if rid not in roles_data:
                        roles_data[rid] = {'role': {}, 'phrase': {}}
                    roles_data[rid]['phrase'][current_lang] = text
    
    return roles_data

# =============================================================================
# GÉNÉRATION DE PHRASES
# =============================================================================
def generate_phrase(tag_name, role_name, is_principal=False):
    """Génère phrases EN et FR pour un rôle"""
    tag_lower = tag_name.lower()
    role_lower = role_name.lower()
    
    if role_lower.startswith("principal "):
        role_lower = role_lower.replace("principal ", "", 1)
    elif role_lower == "principal":
        role_lower = ""
    
    # Phrase anglaise
    if is_principal:
        if role_lower:
            phrase_en = f"[P] <was|and [PO] were> {role_lower} at {tag_lower} <[M]> <[D]> <[L]>"
        else:
            phrase_en = f"[P] <was|and [PO] were> {tag_lower} <[M]> <[D]> <[L]>"
    else:
        if role_lower:
            phrase_en = f"[W] <was|and [WO] were> {role_lower} at {tag_lower} <[M]> <[D]> <[L]>"
        else:
            phrase_en = f"[W] witnessed the {tag_lower} of [P] <and [PO]> <[M]> <[D]> <[L]>"
    
    # Phrase française
    if is_principal:
        if role_lower:
            phrase_fr = f"[P] <était|et [PO] étaient> {role_lower} à {tag_lower} <[M]> <[D]> <[L]>"
        else:
            phrase_fr = f"[P] <était|et [PO] étaient> {tag_lower} <[M]> <[D]> <[L]>"
    else:
        if role_lower:
            phrase_fr = f"[W] <était|et [WO] étaient> {role_lower} à {tag_lower} <[M]> <[D]> <[L]>"
        else:
            phrase_fr = f"[W] a témoigné lors de {tag_lower} de [P] <et [PO]> <[M]> <[D]> <[L]>"
    
    return phrase_en, phrase_fr

# =============================================================================
# RECONSTRUCTION TSENTENCE
# =============================================================================
def rebuild_tsentence(roles_data):
    """
    Reconstruit TSENTENCE avec structure correcte TMG
    CRITIQUE : LABELS D'ABORD, puis PHRASES !
    """
    
    # 1. Construire [LABELS:] EN PREMIER
    labels_part = "[LABELS:]\r\n"
    
    for rid in sorted(roles_data.keys()):
        data = roles_data[rid]
        if data['role']:
            rl_block = f"[RL={rid:05d}]"
            for lang, text in sorted(data['role'].items()):
                rl_block += f"[L={lang}]{text}"
            labels_part += rl_block + "\r\n"
    
    labels_part += "[:LABELS]\r\n"
    
    # 2. Construire les PHRASES groupées par langue (EN SECOND)
    phrases_blocks = {}
    
    for rid in sorted(roles_data.keys()):
        data = roles_data[rid]
        if data['phrase']:
            for lang, text in data['phrase'].items():
                if lang == 'ENGLISH':
                    lang = 'ENGLISHUK'
                
                if lang not in phrases_blocks:
                    phrases_blocks[lang] = []
                phrases_blocks[lang].append(f"[R={rid:05d}]{text}")
    
    # Construire section phrases
    phrases_part = ""
    
    all_langs = set(phrases_blocks.keys())
    if 'ENGLISHUK' not in all_langs and 'ENGLISH' not in all_langs:
        all_langs.add('ENGLISHUK')
    
    for lang in sorted(list(all_langs)):
        phrases_part += f"[L={lang}]"
        if lang in phrases_blocks:
            phrases_part += "".join(phrases_blocks[lang])
        phrases_part += "\r\n"
    
    # ASSEMBLAGE CRITIQUE : LABELS D'ABORD, PUIS PHRASES !
    return labels_part + phrases_part

# =============================================================================
# LECTURE TAGS CUSTOM
# =============================================================================
def list_custom_tags():
    """Liste tous les tags custom"""
    t_dbf_path = get_tmg_file("T")
    
    if not os.path.exists(t_dbf_path):
        log(f"Fichier introuvable : {t_dbf_path}", 'ERROR')
        return []
    
    custom_tags = []
    
    try:
        with dbf.Table(t_dbf_path, codepage='cp1252') as table:
            for record in table:
                # Filtre: ORIGETYPE == 0 ET ETYPENUM > 1123
                # <= 1123 = Tags standard TMG (ne pas toucher)
                # > 1123 = Tags custom utilisateur (modifiables)
                if record['ORIGETYPE'] == 0 and record['ETYPENUM'] > 1123:
                    custom_tags.append({
                        'ETYPENAME': record['ETYPENAME'].strip(),
                        'ETYPENUM': record['ETYPENUM'],
                        'TSENTENCE': record['TSENTENCE']
                    })
    except Exception as e:
        log(f"Erreur lecture tags : {e}", 'ERROR')
    
    # Tri alphabétique par nom
    custom_tags.sort(key=lambda x: x['ETYPENAME'].upper())
    
    return custom_tags

def display_tag_info(tag):
    """Affiche infos détaillées sur un tag"""
    tag_name = tag['ETYPENAME']
    etypenum = tag['ETYPENUM']
    
    log(f"\n{'='*80}")
    log(f"TAG : {tag_name} (ID: {etypenum})")
    log(f"{'='*80}")
    
    # Parser TSENTENCE
    roles_data = parse_tsentence(tag['TSENTENCE'])
    
    if not roles_data:
        log("❌ Aucun rôle défini", 'WARNING')
        return
    
    # Afficher rôles
    log(f"\n📋 RÔLES ({len(roles_data)}) :")
    for rid, data in sorted(roles_data.items()):
        role_name = data['role'].get('ENGLISH', 'Unknown')
        has_phrase = bool(data['phrase'])
        status = "✅ Phrase OK" if has_phrase else "❌ Phrase MANQUANTE"
        
        log(f"   [{rid:05d}] {role_name:30s} {status}")
        
        if has_phrase:
            phrase_en = data['phrase'].get('ENGLISH', data['phrase'].get('ENGLISHUK', ''))
            if phrase_en:
                log(f"            EN: {phrase_en[:60]}...")

# =============================================================================
# INJECTION TAG INDIVIDUEL
# =============================================================================
def inject_single_tag(tag, override=False, interactive=True):
    """
    Injecte phrases dans UN tag
    
    override=False : Injecte seulement si manquant
    override=True  : Régénère TOUTES les phrases
    interactive=True : Mode CLI avec dialogues (défaut)
    interactive=False : Mode GUI sans input()
    """
    # SÉCURITÉ : Vérifier que TMG n'est pas en cours d'exécution
    if is_tmg_running():
        error_msg = "⛔ TMG.EXE is currently running!\n\n" + \
                    "Please close The Master Genealogist before running Sentence Injection.\n\n" + \
                    "Modifying database files while TMG is open can cause corruption."
        log(error_msg, 'ERROR')
        return False
    
    tag_name = tag['ETYPENAME']
    etypenum = tag['ETYPENUM']
    
    log(f"\n{'='*80}")
    log(f"TAG : {tag_name}")
    log(f"{'='*80}\n")
    
    # Parser TSENTENCE
    roles_data = parse_tsentence(tag['TSENTENCE'])
    
    if not roles_data:
        log("❌ Aucun rôle défini", 'WARNING')
        return False
    
    # Compter phrases manquantes / existantes
    missing = sum(1 for d in roles_data.values() if not d['phrase'])
    existing = sum(1 for d in roles_data.values() if d['phrase'])
    
    if missing == 0 and not override:
        if not interactive:
            # Mode GUI/non-interactif : on sort
            log(f"✅ Tag déjà complet ({existing} phrases)", 'SUCCESS')
            return True
        else:
            # Mode CLI : on propose quand même l'option override
            log(f"✅ Tag complet ({existing} phrases)", 'INFO')
            log("   Voulez-vous quand même régénérer toutes les phrases ?")
            choice = input("\n   [S] Sauter ce tag\n   [R] RÉGÉNÉRER TOUTES les phrases\n\n   Choix (S/R) : ").strip().upper()
            
            if choice == 'S':
                log("⏭️  Tag sauté", 'INFO')
                return True
            elif choice == 'R':
                override = True
                log("\n⚠️  Mode OVERRIDE activé - Toutes les phrases seront régénérées !", 'WARNING')
            else:
                log("❌ Annulé", 'ERROR')
                return False
    
    # Warning si phrases existantes et pas override
    if existing > 0 and not override and interactive:
        # Mode CLI uniquement - en GUI, le dialogue a déjà été montré
        log(f"⚠️  Ce tag a déjà {existing} phrase(s) existante(s).", 'WARNING')
        log(f"   {missing} phrase(s) manquante(s) seront ajoutées.\n")
        
        choice = input("   [S] Sauter ce tag\n   [I] Injecter phrases manquantes\n   [R] RÉGÉNÉRER TOUTES les phrases\n\n   Choix (S/I/R) : ").strip().upper()
        
        if choice == 'S':
            log("⏭️  Tag sauté", 'INFO')
            return True
        elif choice == 'R':
            override = True
            log("\n⚠️  Mode OVERRIDE activé - Toutes les phrases seront régénérées !", 'WARNING')
        elif choice != 'I':
            log("❌ Annulé", 'ERROR')
            return False
    
    # Aperçu des phrases
    log("\n📝 APERÇU DES PHRASES :")
    log("-"*80)
    
    for rid, data in sorted(roles_data.items()):
        if not data['phrase'] or override:
            role_name = data['role'].get('ENGLISH', 'Unknown')
            is_principal = 'principal' in role_name.lower()
            
            phrase_en, phrase_fr = generate_phrase(tag_name, role_name, is_principal)
            
            action = "RÉGÉNÉRER" if (data['phrase'] and override) else "INJECTER"
            log(f"  [{rid:05d}] {role_name} [{action}]")
            log(f"         EN → {phrase_en}")
            log(f"         FR → {phrase_fr}")
            log("")
    
    log("-"*80)
    
    # Confirmation (mode CLI uniquement)
    if interactive:
        total_to_modify = sum(1 for d in roles_data.values() if not d['phrase'] or override)
        confirm = input(f"\nModifier {total_to_modify} phrase(s) ? (O/n) : ").strip().lower()
        if confirm not in ['o', 'oui', 'y', 'yes', '']:
            log("❌ Annulé", 'ERROR')
            return False
    
    # BACKUP
    log("\n🔄 Création backup automatique...")
    backup_path = create_backup()
    if not backup_path:
        log("❌ Backup échoué - ARRÊT", 'ERROR')
        return False
    
    # Générer phrases
    injected = 0
    replaced = 0
    
    for rid, data in roles_data.items():
        if not data['phrase'] or override:
            role_name = data['role'].get('ENGLISH', 'Unknown')
            is_principal = 'principal' in role_name.lower()
            
            phrase_en, phrase_fr = generate_phrase(tag_name, role_name, is_principal)
            
            if data['phrase']:
                replaced += 1
            else:
                injected += 1
            
            # FIX: Vider le dict avant d'écrire pour vraiment overwrite
            data['phrase'] = {}
            data['phrase']['ENGLISH'] = phrase_en
            data['phrase']['FRENCH'] = phrase_fr
    
    # Reconstruire TSENTENCE
    new_tsentence = rebuild_tsentence(roles_data)
    
    # Écrire dans DBF
    t_dbf_path = get_tmg_file("T")
    
    try:
        with dbf.Table(t_dbf_path, codepage='cp1252') as table:
            for record in table:
                if record['ETYPENUM'] == etypenum:
                    with record:
                        record['TSENTENCE'] = new_tsentence
                    break
        
        log(f"\n✅ Tag mis à jour : {tag_name}", 'SUCCESS')
        if injected > 0:
            log(f"   → {injected} phrase(s) injectée(s)", 'SUCCESS')
        if replaced > 0:
            log(f"   → {replaced} phrase(s) régénérée(s)", 'SUCCESS')
        
        log("\n⚠️  IMPORTANT : Ouvrez TMG et lancez", 'WARNING')
        log("   File > Maintenance > Reindex", 'WARNING')
        
        return True
    
    except Exception as e:
        log(f"\n❌ ERREUR : {e}", 'ERROR')
        log(f"   Backup disponible : {backup_path}", 'INFO')
        return False

# =============================================================================
# INJECTION EN MASSE
# =============================================================================
def inject_all_tags(override=False, progress_callback=None, interactive=True):
    """
    Injecte phrases dans TOUS les tags custom
    
    override=False : Injecte seulement phrases manquantes
    override=True  : Régénère TOUTES les phrases
    interactive=True : Mode CLI avec dialogues (défaut)
    interactive=False : Mode GUI sans input()
    """
    # SÉCURITÉ : Vérifier que TMG n'est pas en cours d'exécution
    if is_tmg_running():
        error_msg = "⛔ TMG.EXE is currently running!\n\n" + \
                    "Please close The Master Genealogist before running Sentence Injection.\n\n" + \
                    "Modifying database files while TMG is open can cause corruption."
        log(error_msg, 'ERROR')
        return {
            'total_tags': 0,
            'tags_processed': 0,
            'phrases_injected': 0,
            'phrases_replaced': 0,
            'tags_skipped': 0,
            'errors': 1
        }
    
    stats = {
        'total_tags': 0,
        'tags_processed': 0,
        'phrases_injected': 0,
        'phrases_replaced': 0,
        'tags_skipped': 0,
        'errors': 0
    }
    
    log("\n" + "="*80, 'HEADER')
    if override:
        log("RÉGÉNÉRATION TOUTES LES PHRASES", 'HEADER')
    else:
        log("INJECTION PHRASES MANQUANTES", 'HEADER')
    log("="*80 + "\n", 'HEADER')
    
    # Warning si override
    if override:
        log("⚠️  ATTENTION : Mode OVERRIDE activé !", 'WARNING')
        log("   → Toutes les phrases existantes seront REMPLACÉES", 'WARNING')
        log("   → Les phrases personnalisées seront PERDUES", 'WARNING')
        log("   → Un backup sera créé automatiquement\n", 'WARNING')
        
        # Confirmation seulement en mode CLI
        if interactive:
            confirm = input("   Confirmer la régénération ? (yes/no) : ").strip().lower()
            if confirm not in ['yes', 'oui']:
                log("\n❌ Annulé", 'ERROR')
                return stats
            log("")
    
    # Backup
    log("🔄 Création backup automatique...")
    backup_path = create_backup()
    if not backup_path:
        log("❌ Backup échoué - ARRÊT", 'ERROR')
        return stats
    log("")
    
    # Récupérer tags
    custom_tags = list_custom_tags()
    stats['total_tags'] = len(custom_tags)
    
    if not custom_tags:
        log("❌ Aucun tag custom trouvé", 'WARNING')
        return stats
    
    log(f"📊 {len(custom_tags)} tag(s) custom détecté(s)\n")
    
    # Traiter chaque tag
    for idx, tag in enumerate(custom_tags, 1):
        tag_name = tag['ETYPENAME']
        etypenum = tag['ETYPENUM']
        
        # Progress callback
        if progress_callback:
            progress_callback(idx, len(custom_tags), f"Tag {idx}/{len(custom_tags)}: {tag_name}")
        
        # Parser TSENTENCE
        roles_data = parse_tsentence(tag['TSENTENCE'])
        
        if not roles_data:
            log(f"  [{idx:2d}] {tag_name:30s} - Aucun rôle", 'WARNING')
            stats['tags_skipped'] += 1
            continue
        
        # Compter phrases
        missing = sum(1 for d in roles_data.values() if not d['phrase'])
        existing = sum(1 for d in roles_data.values() if d['phrase'])
        
        if missing == 0 and not override:
            log(f"  [{idx:2d}] {tag_name:30s} - Déjà complet", 'INFO')
            stats['tags_skipped'] += 1
            continue
        
        # Générer phrases
        injected = 0
        replaced = 0
        
        try:
            for rid, data in roles_data.items():
                if not data['phrase'] or override:
                    role_name = data['role'].get('ENGLISH', 'Unknown')
                    is_principal = 'principal' in role_name.lower()
                    
                    phrase_en, phrase_fr = generate_phrase(tag_name, role_name, is_principal)
                    
                    if data['phrase']:
                        replaced += 1
                    else:
                        injected += 1
                    
                    # FIX: Vider le dict avant d'écrire pour vraiment overwrite
                    data['phrase'] = {}
                    data['phrase']['ENGLISH'] = phrase_en
                    data['phrase']['FRENCH'] = phrase_fr
            
            # Reconstruire TSENTENCE
            new_tsentence = rebuild_tsentence(roles_data)
            
            # Écrire dans DBF
            t_dbf_path = get_tmg_file("T")
            
            with dbf.Table(t_dbf_path, codepage='cp1252') as table:
                for record in table:
                    if record['ETYPENUM'] == etypenum:
                        with record:
                            record['TSENTENCE'] = new_tsentence
                        break
            
            # Log résultat
            msg = f"  [{idx:2d}] {tag_name:30s}"
            if injected > 0:
                msg += f" - {injected} injectée(s)"
            if replaced > 0:
                msg += f" - {replaced} régénérée(s)"
            
            log(msg, 'SUCCESS')
            
            stats['tags_processed'] += 1
            stats['phrases_injected'] += injected
            stats['phrases_replaced'] += replaced
        
        except Exception as e:
            log(f"  [{idx:2d}] {tag_name:30s} - ERREUR : {e}", 'ERROR')
            stats['errors'] += 1
    
    # Résumé final
    log("\n" + "="*80, 'HEADER')
    log("RÉSUMÉ FINAL", 'HEADER')
    log("="*80, 'HEADER')
    log(f"Tags custom total     : {stats['total_tags']}", 'INFO')
    log(f"Tags traités          : {stats['tags_processed']}", 'SUCCESS')
    log(f"Phrases injectées     : {stats['phrases_injected']}", 'SUCCESS')
    if stats['phrases_replaced'] > 0:
        log(f"Phrases régénérées    : {stats['phrases_replaced']}", 'SUCCESS')
    log(f"Tags ignorés          : {stats['tags_skipped']}", 'INFO')
    log(f"Erreurs               : {stats['errors']}", 'ERROR' if stats['errors'] > 0 else 'INFO')
    log("\n⚠️  IMPORTANT : Ouvrez TMG et lancez File > Maintenance > Reindex", 'WARNING')
    
    return stats

# =============================================================================
# MODE DUAL POUR GUI
# =============================================================================
def analyze_tag_mode(tag, tmg_project_path=None, tmg_prefix=None):
    """
    Mode GUI pour analyser un tag (sans injection)
    
    Returns:
        dict: {
            'roles': {
                role_id: {'name': str, 'has_phrase': bool}
            }
        }
    """
    global TMG_PATH, TMG_PREFIX
    
    if tmg_project_path and tmg_prefix:
        TMG_PATH = tmg_project_path
        TMG_PREFIX = tmg_prefix
    else:
        select_tmg_project_gui()
    
    print(f"DEBUG analyze_tag_mode: Looking for tag '{tag['ETYPENAME']}'")
    
    # Ouvrir fichiers TMG
    t_dbf_path = get_tmg_file("T")
    print(f"DEBUG: T.DBF path = {t_dbf_path}")
    
    # Trouver le record du tag
    tag_record = None
    with dbf.Table(t_dbf_path, codepage='cp1252') as table:
        count = 0
        for rec in table:
            if rec.origetype == 0:
                count += 1
                # IMPORTANT: Strip pour enlever les espaces de padding
                tag_name_in_db = rec.etypename.strip() if rec.etypename else ''
                tag_name_search = tag['ETYPENAME'].strip()
                
                
                if tag_name_in_db == tag_name_search:
                    print(f"DEBUG: MATCH! Found tag {tag_name_in_db}")
                    tag_record = rec
                    break
        print(f"DEBUG: Scanned {count} custom tags")
    
    if not tag_record:
        print(f"DEBUG: Tag '{tag['ETYPENAME']}' NOT FOUND in database")
        return {'roles': {}}
    
    print(f"DEBUG: Tag found, parsing TSENTENCE...")
    
    # Parser TSENTENCE
    tsentence_str = tag_record.tsentence
    roles_data = parse_tsentence(tsentence_str) if tsentence_str else {}
    
    print(f"DEBUG: Parsed {len(roles_data)} roles from TSENTENCE")
    
    # Construire résultat
    result = {'roles': {}}
    
    for rid, data in roles_data.items():
        role_name = data['role'].get('ENGLISHUK', data['role'].get('ENGLISH', f"Role {rid}"))
        has_phrase = bool(data['phrase'].get('ENGLISHUK') or data['phrase'].get('ENGLISH'))
        
        result['roles'][rid] = {
            'name': role_name,
            'has_phrase': has_phrase
        }
    
    return result

def list_custom_tags_mode(tmg_project_path=None, tmg_prefix=None):
    """
    Mode dual CLI/GUI pour lister les tags custom
    
    Returns:
        list: Liste des tags custom
    """
    global TMG_PATH, TMG_PREFIX
    
    if tmg_project_path and tmg_prefix:
        TMG_PATH = tmg_project_path
        TMG_PREFIX = tmg_prefix
    else:
        select_tmg_project_gui()
    
    return list_custom_tags()

def inject_single_tag_mode(tag, tmg_project_path=None, tmg_prefix=None, 
                          override=False, log_callback=None, language='EN'):
    """
    Mode dual CLI/GUI pour injection UN tag
    
    Args:
        tag: Dictionnaire tag custom
        override: True = régénérer toutes phrases, False = injecter manquantes
        language: 'EN' ou 'FR'
    
    Returns:
        dict: Statistiques d'injection
    """
    global TMG_PATH, TMG_PREFIX, LOG_CALLBACK, LANGUAGE
    
    LOG_CALLBACK = log_callback
    LANGUAGE = language
    
    if tmg_project_path and tmg_prefix:
        TMG_PATH = tmg_project_path
        TMG_PREFIX = tmg_prefix
    else:
        select_tmg_project_gui()
    
    # Appeler inject_single_tag avec override et interactive=False
    inject_single_tag(tag, override=override, interactive=False)
    
    # Retourner stats simples
    return {'sentences_injected': 1}  # Simplifié pour l'instant

def inject_all_tags_mode(tmg_project_path=None, tmg_prefix=None, override=False, 
                         log_callback=None, progress_callback=None, language='EN'):
    """
    Mode dual CLI/GUI pour injection en masse
    
    Args:
        language: 'EN' ou 'FR' (pour GUI, CLI demande au démarrage)
    """
    global TMG_PATH, TMG_PREFIX, LOG_CALLBACK, LANGUAGE
    
    LOG_CALLBACK = log_callback
    LANGUAGE = language  # Défini par le GUI ou CLI
    
    if tmg_project_path and tmg_prefix:
        TMG_PATH = tmg_project_path
        TMG_PREFIX = tmg_prefix
    else:
        select_tmg_project_gui()
    
    # Déterminer si mode interactif
    interactive = (log_callback is None)  # CLI = interactive, GUI = non-interactive
    
    return inject_all_tags(override=override, progress_callback=progress_callback, 
                          interactive=interactive)

# =============================================================================
# MENU PRINCIPAL
# =============================================================================
def show_menu():
    """Affiche menu principal"""
    print("\n" + "="*80)
    print(t('menu_title'))
    print("="*80)
    print(t('menu_1'))
    print(t('menu_2'))
    print(t('menu_3'))
    print(t('menu_4'))
    print(t('menu_5'))
    print()

def show_submenu_all():
    """Affiche sous-menu 'Traiter TOUS'"""
    print("\n" + "="*80)
    print(t('submenu_title'))
    print("="*80)
    print(t('submenu_1'))
    print(t('submenu_2'))
    print(t('submenu_3'))
    print()

def main():
    """Point d'entrée CLI"""
    # SÉCURITÉ : Vérifier que TMG n'est pas en cours d'exécution
    if is_tmg_running():
        print("\n" + "="*80)
        print("⛔ TMG.EXE IS CURRENTLY RUNNING!")
        print("="*80)
        print("\nPlease close The Master Genealogist before running Sentence Injection.")
        print("\nModifying database files while TMG is open can cause corruption.")
        print("\n" + "="*80)
        input("\nPress ENTER to exit...")
        return 1
    
    # Choix de la langue
    ask_language()
    
    # Sélection projet
    select_tmg_project_gui()
    
    print(f"\n📂 {t('project')} : {TMG_PATH}")
    print(f"🔖 {t('prefix')} : {TMG_PREFIX}")
    
    # Vérifier fichier
    t_dbf_path = get_tmg_file("T")
    if not os.path.exists(t_dbf_path):
        print(f"\n❌ {t('file_not_found')} : {t_dbf_path}")
        return 1
    
    print(f"✅ {t('file_found')} : {t_dbf_path}")
    
    # Lister tags
    custom_tags = list_custom_tags()
    
    if not custom_tags:
        print(f"\n❌ {t('no_custom_tags')}")
        return 1
    
    print(f"\n📊 {len(custom_tags)} {t('custom_tags_found')}")
    
    # Menu principal
    while True:
        show_menu()
        
        choice = input(t('menu_choice')).strip()
        
        if choice == '1':
            # Lister tags
            print(f"\n📋 {t('custom_tags_list')}")
            for i, tag in enumerate(custom_tags, 1):
                name = tag['ETYPENAME']
                print(f"   {i:2d}. {name}")
        
        elif choice == '2':
            # Examiner un tag
            num = input(f"\n{t('number')} (1-{len(custom_tags)}) : ").strip()
            try:
                idx = int(num) - 1
                if 0 <= idx < len(custom_tags):
                    display_tag_info(custom_tags[idx])
            except:
                print(f"❌ {t('invalid_choice')}")
        
        elif choice == '3':
            # Injecter UN tag
            num = input(f"\n{t('number')} (1-{len(custom_tags)}) : ").strip()
            try:
                idx = int(num) - 1
                if 0 <= idx < len(custom_tags):
                    inject_single_tag(custom_tags[idx])
            except:
                print(f"❌ {t('invalid_choice')}")
        
        elif choice == '4':
            # Sous-menu Traiter TOUS
            while True:
                show_submenu_all()
                
                sub_choice = input(t('submenu_choice')).strip()
                
                if sub_choice == '1':
                    # Phrases manquantes seulement
                    inject_all_tags(override=False)
                    break
                
                elif sub_choice == '2':
                    # Régénérer TOUTES
                    inject_all_tags(override=True)
                    break
                
                elif sub_choice == '3':
                    # Retour
                    break
                
                else:
                    print(f"❌ {t('invalid_choice')}")
        
        elif choice == '5':
            # Quitter
            print(f"\n👋 {t('goodbye')}")
            break
        
        else:
            print(f"❌ {t('invalid_choice')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
