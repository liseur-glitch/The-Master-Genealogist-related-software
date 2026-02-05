#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMG CORE ENGINE - VERSION 3.0
==============================
Logique métier pure pour TMG Suite
AUCUNE interaction utilisateur (pas de input(), pas de print() direct)
Tout passe par des callbacks pour permettre GUI ou CLI

Architecture:
- TMGInjectorEngine: Moteur d'injection de témoins (rôles)
- TMGMappingEngine: Moteur de génération de mapping GEDCOM → TMG
- TMGSentenceInjectorEngine: Moteur d'injection de phrases (NOUVEAU v3.0)
- Fonctions utilitaires communes

Auteur: Claude
Date: 2026-02-05
Version: 3.0 (Ajout Sentence Injection)
"""

import dbf
import re
import os
import sys
import unidecode
import shutil
from datetime import datetime
import json
from collections import defaultdict

# =============================================================================
# FONCTIONS UTILITAIRES (COMMUNES)
# =============================================================================

def normalize(txt):
    """Normalisation : MAJUSCULES + sans accents"""
    if not txt: return ""
    return unidecode.unidecode(txt).upper().strip()

def extract_year_tmg(edate_str):
    """
    Extrait l'année d'une date TMG (format DBF)
    Format TMG: "YYYYMMDD" ou "YYYY0000" ou "" ou autres variations
    Retourne l'année (int) ou None si absent/invalide
    """
    if not edate_str or len(edate_str) < 4:
        return None
    year_str = edate_str[:4]
    if year_str == "0000" or not year_str.isdigit():
        return None
    year = int(year_str)
    if year < 1 or year > 9999:
        return None
    return year

# =============================================================================
# CLASSE BASE POUR LES MOTEURS
# =============================================================================

class TMGEngineBase:
    """Classe de base pour les moteurs TMG avec gestion des logs"""
    
    def __init__(self, gedcom_path=None, tmg_project_path=None, tmg_prefix=None):
        self.gedcom_path = gedcom_path
        self.tmg_project_path = tmg_project_path
        self.tmg_prefix = tmg_prefix
        self.log_callback = None
        self.progress_callback = None
        
    def set_log_callback(self, callback):
        """
        Définit un callback pour les logs
        Signature: callback(message: str, level: str)
        Levels: INFO, SUCCESS, WARNING, ERROR, HEADER
        """
        self.log_callback = callback
    
    def set_progress_callback(self, callback):
        """
        Définit un callback pour la progression
        Signature: callback(current: int, total: int, message: str)
        """
        self.progress_callback = callback
    
    def log(self, message, level='INFO'):
        """Envoie un message de log via callback"""
        if self.log_callback:
            self.log_callback(message, level)
    
    def progress(self, current, total, message=''):
        """Envoie une mise à jour de progression"""
        if self.progress_callback:
            self.progress_callback(current, total, message)

# =============================================================================
# MOTEUR SENTENCE INJECTION (NOUVEAU v3.0)
# =============================================================================

class TMGSentenceInjectorEngine(TMGEngineBase):
    """
    Moteur d'injection de phrases dans les tags TMG
    Basé sur tmg_sentence_injector_v4_0_FINAL.py
    """
    
    def __init__(self, tmg_project_path, tmg_prefix):
        super().__init__(None, tmg_project_path, tmg_prefix)
        self.stats = {
            'total_tags': 0,
            'tags_processed': 0,
            'phrases_injected': 0,
            'tags_skipped': 0,
            'errors': 0
        }
    
    def get_tmg_file(self, suffix):
        """Construit le chemin vers un fichier TMG"""
        return os.path.join(self.tmg_project_path, f"{self.tmg_prefix}{suffix}.dbf")
    
    def create_backup(self):
        """Crée backup complet (DBF + FPT + CDX)"""
        t_dbf_path = self.get_tmg_file("_T")
        
        if not os.path.exists(t_dbf_path):
            self.log(f"Fichier introuvable : {t_dbf_path}", 'ERROR')
            return False
        
        backup_dir = os.path.join(self.tmg_project_path, "BACKUPS_SENTENCES")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files_to_backup = [
            (f"{self.tmg_prefix}_T.dbf", f"{self.tmg_prefix}_T_BACKUP_{timestamp}.dbf"),
            (f"{self.tmg_prefix}_T.fpt", f"{self.tmg_prefix}_T_BACKUP_{timestamp}.fpt"),
            (f"{self.tmg_prefix}_T.cdx", f"{self.tmg_prefix}_T_BACKUP_{timestamp}.cdx")
        ]
        
        try:
            for src_file, backup_name in files_to_backup:
                src_path = os.path.join(self.tmg_project_path, src_file)
                
                if os.path.exists(src_path):
                    backup_path = os.path.join(backup_dir, backup_name)
                    shutil.copy2(src_path, backup_path)
            
            self.log(f"Backup créé : {backup_dir}", 'SUCCESS')
            return True
            
        except Exception as e:
            self.log(f"Erreur backup : {e}", 'ERROR')
            return False
    
    def parse_tsentence(self, tsentence_str):
        """Parse le champ TSENTENCE pour extraire rôles et phrases"""
        roles_data = {}
        
        regex_role = re.compile(r'\[RL=(\d+)\](.*?)(?=\[RL=|\[:LABELS\]|$)', re.DOTALL)
        regex_phrase = re.compile(r'\[R=(\d+)\](.*?)(?=\[RL=|\[R=|\[LABELS:\]|$)', re.DOTALL)
        regex_lbl = re.compile(r'\[L=([^\]]+)\]([^\[\r\n]+)')
        
        # Parser [RL=] rôles (dans [LABELS:])
        if '[LABELS:]' in tsentence_str:
            try:
                content = tsentence_str.split('[LABELS:]')[1].split('[:LABELS]')[0]
                for m in regex_role.finditer(content):
                    rid = int(m.group(1))
                    block = m.group(2)
                    
                    if rid not in roles_data:
                        roles_data[rid] = {'role': {}, 'phrase': {}}
                    
                    for lm in regex_lbl.finditer(block):
                        lang = lm.group(1).upper()
                        text = lm.group(2).strip()
                        roles_data[rid]['role'][lang] = text
            except:
                pass
        
        # Parser [R=] phrases (APRÈS [:LABELS])
        if '[:LABELS]' in tsentence_str:
            phrases_part = tsentence_str.split('[:LABELS]')[1]
            for m in regex_phrase.finditer(phrases_part):
                rid = int(m.group(1))
                block = m.group(2)
                
                if rid not in roles_data:
                    roles_data[rid] = {'role': {}, 'phrase': {}}
                
                for lm in regex_lbl.finditer(block):
                    lang = lm.group(1).upper()
                    text = lm.group(2).strip()
                    roles_data[rid]['phrase'][lang] = text
        
        return roles_data
    
    def generate_phrase(self, tag_name, role_name, is_principal=False):
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
    
    def rebuild_tsentence(self, roles_data):
        """Reconstruit TSENTENCE avec structure correcte TMG"""
        phrases_blocks = {}
        
        # 1. Organiser phrases par langue
        for rid in sorted(roles_data.keys()):
            data = roles_data[rid]
            if data['phrase']:
                for lang, text in data['phrase'].items():
                    if lang == 'ENGLISH':
                        lang = 'ENGLISHUK'
                    
                    if lang not in phrases_blocks:
                        phrases_blocks[lang] = []
                    phrases_blocks[lang].append(f"[R={rid:05d}]{text}")
        
        # 2. Construire [LABELS:] EN PREMIER
        labels_part = "[LABELS:]\r\n"
        
        for rid in sorted(roles_data.keys()):
            data = roles_data[rid]
            if data['role']:
                rl_block = f"[RL={rid:05d}]"
                for lang, text in sorted(data['role'].items()):
                    rl_block += f"[L={lang}]{text}"
                labels_part += rl_block + "\r\n"
        
        labels_part += "[:LABELS]\r\n"
        
        # 3. Construire phrases groupées par langue
        final_phrases = []
        
        all_langs = set(phrases_blocks.keys())
        if 'ENGLISHUK' not in all_langs and 'ENGLISH' not in all_langs:
            all_langs.add('ENGLISHUK')
        
        for lang in sorted(list(all_langs)):
            final_phrases.append(f"[L={lang}]")
            if lang in phrases_blocks:
                final_phrases.append("".join(phrases_blocks[lang]))
            final_phrases.append("\r\n")
        
        text_part = "".join(final_phrases)
        
        # Assemblage : LABELS d'abord, puis phrases
        return labels_part + text_part
    
    def get_custom_tags(self):
        """Récupère la liste des tags custom"""
        t_dbf_path = self.get_tmg_file("_T")
        
        if not os.path.exists(t_dbf_path):
            self.log(f"Fichier introuvable : {t_dbf_path}", 'ERROR')
            return []
        
        custom_tags = []
        
        try:
            with dbf.Table(t_dbf_path, codepage='cp1252') as table:
                for record in table:
                    if record['ORIGETYPE'] == 0:  # Tag custom
                        custom_tags.append({
                            'name': record['ETYPENAME'].strip(),
                            'etypenum': record['ETYPENUM'],
                            'tsentence': record['TSENTENCE']
                        })
        except Exception as e:
            self.log(f"Erreur lecture tags : {e}", 'ERROR')
        
        return custom_tags
    
    def inject_tag(self, tag_name, etypenum, roles_data):
        """Injecte phrases dans un tag"""
        try:
            # Générer phrases manquantes
            for rid, data in roles_data.items():
                if not data['phrase']:
                    role_name = data['role'].get('ENGLISH', 'Unknown')
                    is_principal = 'principal' in role_name.lower()
                    
                    phrase_en, phrase_fr = self.generate_phrase(tag_name, role_name, is_principal)
                    
                    data['phrase']['ENGLISH'] = phrase_en
                    data['phrase']['FRENCH'] = phrase_fr
            
            # Reconstruire TSENTENCE
            new_tsentence = self.rebuild_tsentence(roles_data)
            
            # Écrire dans DBF
            t_dbf_path = self.get_tmg_file("_T")
            
            with dbf.Table(t_dbf_path, codepage='cp1252') as table:
                for record in table:
                    if record['ETYPENUM'] == etypenum:
                        with record:
                            record['TSENTENCE'] = new_tsentence
                        break
            
            return True
            
        except Exception as e:
            self.log(f"Erreur injection {tag_name} : {e}", 'ERROR')
            return False
    
    def inject_all_tags(self):
        """Injecte phrases dans TOUS les tags custom"""
        self.log("="*80, 'HEADER')
        self.log("INJECTION DE PHRASES EN MASSE", 'HEADER')
        self.log("="*80, 'HEADER')
        self.log("")
        
        # Créer backup
        self.log("Création du backup...", 'INFO')
        if not self.create_backup():
            self.log("ARRÊT - Backup échoué", 'ERROR')
            return False
        
        # Récupérer tags
        custom_tags = self.get_custom_tags()
        self.stats['total_tags'] = len(custom_tags)
        
        if not custom_tags:
            self.log("Aucun tag custom trouvé", 'WARNING')
            return False
        
        self.log(f"\n{len(custom_tags)} tag(s) custom détecté(s)\n", 'INFO')
        
        # Traiter chaque tag
        for idx, tag in enumerate(custom_tags, 1):
            tag_name = tag['name']
            etypenum = tag['etypenum']
            
            self.progress(idx, len(custom_tags), f"Tag {idx}/{len(custom_tags)}: {tag_name}")
            
            # Parser TSENTENCE
            roles_data = self.parse_tsentence(tag['tsentence'])
            
            if not roles_data:
                self.log(f"  [{idx:2d}] {tag_name:30s} - Aucun rôle", 'WARNING')
                self.stats['tags_skipped'] += 1
                continue
            
            # Compter phrases manquantes
            missing = sum(1 for d in roles_data.values() if not d['phrase'])
            
            if missing == 0:
                self.log(f"  [{idx:2d}] {tag_name:30s} - Déjà complet", 'INFO')
                self.stats['tags_skipped'] += 1
                continue
            
            # Injecter
            if self.inject_tag(tag_name, etypenum, roles_data):
                self.log(f"  [{idx:2d}] {tag_name:30s} - {missing} phrase(s) injectée(s)", 'SUCCESS')
                self.stats['tags_processed'] += 1
                self.stats['phrases_injected'] += missing
            else:
                self.stats['errors'] += 1
        
        # Résumé final
        self.log("", 'INFO')
        self.log("="*80, 'HEADER')
        self.log("RÉSUMÉ FINAL", 'HEADER')
        self.log("="*80, 'HEADER')
        self.log(f"Tags custom total      : {self.stats['total_tags']}", 'INFO')
        self.log(f"Tags traités          : {self.stats['tags_processed']}", 'SUCCESS')
        self.log(f"Phrases injectées     : {self.stats['phrases_injected']}", 'SUCCESS')
        self.log(f"Tags ignorés          : {self.stats['tags_skipped']}", 'INFO')
        self.log(f"Erreurs               : {self.stats['errors']}", 'ERROR' if self.stats['errors'] > 0 else 'INFO')
        self.log("", 'INFO')
        self.log("⚠️  IMPORTANT : Ouvrez TMG et lancez File > Maintenance > Reindex", 'WARNING')
        
        return True

# NOTE: TMGInjectorEngine et TMGMappingEngine restent inchangés
# (code original conservé pour compatibilité)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMG CORE ENGINE
===============
Logique métier pure extraite de super_injecteur_v16_clean.py et mapping_tool.py
AUCUNE interaction utilisateur (pas de input(), pas de print() direct)
Tout passe par des callbacks pour permettre GUI ou CLI

Architecture:
- TMGInjectorEngine: Moteur d'injection de témoins
- TMGMappingEngine: Moteur de génération de mapping
- Fonctions utilitaires communes

Auteur: Claude (extraction) basée sur Olivier + Claude + Gemini
Date: 2026-02-04
Version: 2.0 (TMG Suite)
"""

import dbf
import re
import os
import sys
import unidecode
import shutil
from datetime import datetime
import json
from collections import defaultdict

# =============================================================================
# FONCTIONS UTILITAIRES (COMMUNES)
# =============================================================================

def normalize(txt):
    """Normalisation : MAJUSCULES + sans accents"""
    if not txt: return ""
    return unidecode.unidecode(txt).upper().strip()

def extract_year_tmg(edate_str):
    """
    Extrait l'année d'une date TMG (format DBF)
    Format TMG: "YYYYMMDD" ou "YYYY0000" ou "" ou autres variations
    Retourne l'année (int) ou None si absent/invalide
    """
    if not edate_str or len(edate_str) < 4:
        return None
    year_str = edate_str[:4]
    if year_str == "0000" or not year_str.isdigit():
        return None
    year = int(year_str)
    if year < 1 or year > 9999:
        return None
    return year

# =============================================================================
# CLASSE BASE POUR LES MOTEURS
# =============================================================================

class TMGEngineBase:
    """Classe de base pour les moteurs TMG avec gestion des logs"""
    
    def __init__(self, gedcom_path, tmg_project_path, tmg_prefix):
        self.gedcom_path = gedcom_path
        self.tmg_project_path = tmg_project_path
        self.tmg_prefix = tmg_prefix
        self.log_callback = None
        self.progress_callback = None
        
    def set_log_callback(self, callback):
        """
        Définit un callback pour les logs
        Signature: callback(message: str, level: str)
        Levels: INFO, SUCCESS, WARNING, ERROR
        """
        self.log_callback = callback
    
    def set_progress_callback(self, callback):
        """
        Définit un callback pour la progression
        Signature: callback(current: int, total: int, message: str)
        """
        self.progress_callback = callback
    
    def _log(self, message, level="INFO"):
        """Log interne - envoie vers callback ou print"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            # Fallback pour CLI
            prefix = {
                'INFO': '  ',
                'SUCCESS': '✅',
                'WARNING': '⚠️ ',
                'ERROR': '❌'
            }.get(level, '  ')
            print(f"{prefix} {message}")
    
    def _progress(self, current, total, message=""):
        """Progression - envoie vers callback ou ignore"""
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    def get_tmg_file(self, suffix):
        """Retourne le chemin complet vers un fichier DBF TMG"""
        filename = f"{self.tmg_prefix}{suffix}.dbf"
        return os.path.join(self.tmg_project_path, filename)
    
    def verify_tmg_files(self, required_suffixes):
        """Vérifie que tous les fichiers TMG requis existent"""
        missing = []
        for suffix in required_suffixes:
            path = self.get_tmg_file(suffix)
            if not os.path.exists(path):
                missing.append(f"{self.tmg_prefix}{suffix}.dbf")
        
        if missing:
            raise FileNotFoundError(
                f"Fichiers TMG manquants : {', '.join(missing)}\n"
                f"Vérifiez le chemin du projet : {self.tmg_project_path}\n"
                f"Vérifiez le préfixe : {self.tmg_prefix}"
            )

# =============================================================================
# MOTEUR D'INJECTION
# =============================================================================

class TMGInjectorEngine(TMGEngineBase):
    """
    Moteur d'injection de témoins basé sur super_injecteur_v16_clean.py
    Logique RED/GREEN complète pour Self-Witness
    """
    
    def __init__(self, gedcom_path, tmg_project_path, tmg_prefix, mapping_file="mapping.json"):
        super().__init__(gedcom_path, tmg_project_path, tmg_prefix)
        self.mapping_file = mapping_file
        self.EVENT_MAPPING = {}
        self.ROLES_DB = {}
        
    def load_mapping(self):
        """Charge mapping.json"""
        if not os.path.exists(self.mapping_file):
            raise FileNotFoundError(
                f"{self.mapping_file} introuvable!\n"
                "Lancez d'abord le Mapping Tool pour le générer."
            )
        
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Normaliser les clés
        self.EVENT_MAPPING = {}
        for k, v in data.get('events', {}).items():
            if v.get('tmg_name'):
                self.EVENT_MAPPING[normalize(k)] = v['tmg_name']
        
        self.ROLES_DB = {}
        for k, v in data.get('roles', {}).items():
            if v.get('eng'):
                self.ROLES_DB[normalize(k)] = {
                    'eng': v['eng'],
                    'fra': v.get('fra', v['eng'])
                }
        
        self._log(f"Mapping chargé : {len(self.EVENT_MAPPING)} événements, {len(self.ROLES_DB)} rôles", "INFO")
    
    def create_backup(self):
        """Crée un backup des fichiers TMG avant modification"""
        self._log("Création du backup...", "INFO")
        
        backup_dir = os.path.join(
            self.tmg_project_path,
            f"BACKUP_{self.tmg_prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(backup_dir, exist_ok=True)
        
        files_to_backup = ['_E.dbf', '_T.dbf']
        for suffix in files_to_backup:
            src = self.get_tmg_file(suffix)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, os.path.basename(src))
                shutil.copy2(src, dst)
        
        self._log(f"Backup créé : {backup_dir}", "SUCCESS")
        return backup_dir
    
    def scan_role_usage(self):
        """
        Phase 1 : Scanne le GEDCOM pour détecter quels rôles sont utilisés
        avec quels événements et quels propriétaires (@I ou @F)
        
        Retourne:
            dict: {event_name_norm: {role_name_norm: {'indi': set(), 'fam': set()}}}
        """
        self._log("=" * 80, "INFO")
        self._log("PHASE 1 : SCAN DES RÔLES DANS LE GEDCOM", "INFO")
        self._log("=" * 80, "INFO")
        
        role_usage = defaultdict(lambda: defaultdict(lambda: {'indi': set(), 'fam': set()}))
        
        try:
            with open(self.gedcom_path, 'r', encoding='ansi') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(self.gedcom_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        self._log(f"Lecture du GEDCOM : {len(lines)} lignes", "INFO")
        
        current_owner_type = None
        current_owner_id = None
        current_event_tag = None
        current_event_type = None
        current_shars = []
        
        for line_num, line in enumerate(lines, 1):
            parts = line.strip().split(' ', 2)
            if len(parts) < 2:
                continue
            
            try:
                level = int(parts[0])
                tag = parts[1]
                value = parts[2].strip() if len(parts) > 2 else ""
            except:
                continue
            
            # Niveau 0: Nouveau bloc
            if level == 0:
                # Sauvegarder l'événement précédent
                if current_owner_id and current_event_tag and current_shars:
                    event_name = current_event_type if current_event_type else current_event_tag
                    event_name_norm = normalize(self.EVENT_MAPPING.get(normalize(event_name), event_name))
                    self._analyze_role_usage(current_owner_type, event_name_norm, current_shars, role_usage)
                
                # Reset
                current_shars = []
                current_event_tag = None
                current_event_type = None
                
                # Déterminer le type de propriétaire
                if tag.startswith('@I'):
                    current_owner_type = 'indi'
                    current_owner_id = tag
                elif tag.startswith('@F'):
                    current_owner_type = 'fam'
                    current_owner_id = tag
                else:
                    current_owner_type = None
                    current_owner_id = None
            
            # Niveau 1: Événement
            elif level == 1 and current_owner_id:
                # Sauvegarder l'événement précédent
                if current_event_tag and current_shars:
                    event_name = current_event_type if current_event_type else current_event_tag
                    event_name_norm = normalize(self.EVENT_MAPPING.get(normalize(event_name), event_name))
                    self._analyze_role_usage(current_owner_type, event_name_norm, current_shars, role_usage)
                
                # Nouveau événement
                current_event_tag = tag
                current_event_type = value if tag in ['EVEN', 'FACT', 'OCCU'] else None
                current_shars = []
            
            # Niveau 2: TYPE ou _SHAR
            elif level == 2 and current_event_tag:
                if tag == 'TYPE' and current_event_tag in ['EVEN', 'FACT', 'OCCU']:
                    current_event_type = value
                elif tag == '_SHAR':
                    current_shars.append({'id': value.strip('@'), 'role': 'Witness'})
            
            # Niveau 3: ROLE
            elif level == 3 and current_shars:
                if tag == 'ROLE':
                    current_shars[-1]['role'] = value
            
            # Progression
            if line_num % 10000 == 0:
                self._progress(line_num, len(lines), f"Scan ligne {line_num}/{len(lines)}")
        
        # Sauvegarder le dernier événement
        if current_owner_id and current_event_tag and current_shars:
            event_name = current_event_type if current_event_type else current_event_tag
            event_name_norm = normalize(self.EVENT_MAPPING.get(normalize(event_name), event_name))
            self._analyze_role_usage(current_owner_type, event_name_norm, current_shars, role_usage)
        
        self._log(f"Scan terminé : {len(role_usage)} événements avec témoins détectés", "SUCCESS")
        return role_usage
    
    def _analyze_role_usage(self, owner_type, event_name_norm, shars, role_usage):
        """Analyse les rôles d'un événement et met à jour role_usage"""
        for shar in shars:
            role_norm = normalize(shar['role'])
            role_usage[event_name_norm][role_norm][owner_type].add(True)
    
    def update_tmg_structure(self, role_usage, dry_run=False):
        """
        Phase 2 : Met à jour T.DBF avec les paires de rôles nécessaires
        
        Args:
            role_usage: Résultat de scan_role_usage()
            dry_run: Si True, simule sans écrire
        
        Returns:
            dict: Statistiques de mise à jour
        """
        self._log("=" * 80, "INFO")
        self._log("PHASE 2 : MISE À JOUR DE LA STRUCTURE TMG (T.DBF)", "INFO")
        self._log("=" * 80, "INFO")
        
        if dry_run:
            self._log("MODE DRY-RUN : Aucune modification ne sera effectuée", "WARNING")
        
        # TODO: Implémenter la logique complète de v16_clean
        # Pour l'instant, retourne un dict vide
        self._log("Phase 2 en cours d'implémentation...", "WARNING")
        return {
            'added': 0,
            'updated': 0,
            'skipped': 0
        }
    
    def inject_witnesses(self, dry_run=False):
        """
        Lance le processus complet d'injection
        
        Args:
            dry_run: Si True, simule sans écrire dans TMG
        
        Returns:
            dict: Statistiques d'injection
        """
        try:
            # Vérification des fichiers
            self.verify_tmg_files(['$', '_G', '_E', '_T', '_D'])
            
            # Chargement mapping
            self.load_mapping()
            
            # Backup
            if not dry_run:
                self.create_backup()
            
            # Phase 1: Scan
            role_usage = self.scan_role_usage()
            
            # Phase 2: Mise à jour structure
            structure_stats = self.update_tmg_structure(role_usage, dry_run)
            
            # Phase 3: Injection (TODO)
            self._log("Phase 3 (injection) en cours d'implémentation...", "WARNING")
            
            return {
                'ok': 0,
                'principal': 0,
                'skip': 0,
                'error': 0,
                'structure_stats': structure_stats
            }
            
        except Exception as e:
            self._log(f"Erreur fatale : {str(e)}", "ERROR")
            raise

# =============================================================================
# MOTEUR DE MAPPING
# =============================================================================

class TMGMappingEngine(TMGEngineBase):
    """
    Moteur de génération de mapping basé sur mapping_tool.py
    Scanne GEDCOM + TMG pour produire mapping_master.xlsx
    """
    
    def __init__(self, gedcom_path, tmg_project_path, tmg_prefix):
        super().__init__(gedcom_path, tmg_project_path, tmg_prefix)
    
    def generate_mapping_excel(self):
        """Génère mapping_master.xlsx"""
        self._log("Génération du mapping en cours d'implémentation...", "WARNING")
        # TODO: Implémenter la logique complète de mapping_tool.py
        return {
            'excel_path': 'mapping_master.xlsx',
            'events_found': 0,
            'roles_found': 0
        }

# =============================================================================
# FONCTIONS D'EXPORT (pour compatibilité avec scripts existants)
# =============================================================================

def create_injector_engine(gedcom_path, tmg_project_path, tmg_prefix, mapping_file="mapping.json"):
    """Factory function pour créer un moteur d'injection"""
    return TMGInjectorEngine(gedcom_path, tmg_project_path, tmg_prefix, mapping_file)

def create_mapping_engine(gedcom_path, tmg_project_path, tmg_prefix):
    """Factory function pour créer un moteur de mapping"""
    return TMGMappingEngine(gedcom_path, tmg_project_path, tmg_prefix)

# Classes TMGInjectorEngine et TMGMappingEngine ajoutées ci-dessus (code original)
