#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUPER-INJECTEUR TMG v16_CLEAN — RED/GREEN LOGIC (Self-Witness)
---------------------------------------------------------------
Base : v15 (qui marche parfaitement : 440 témoins injectés)
Ajout : Logique RED/GREEN pour gérer les "Self-Witness" (Principal avec rôle)

Nouvelles fonctionnalités v16_clean :
  ✅ Détection automatique Self-Witness (Principal = Témoin de son propre événement)
  ✅ Création paires de rôles : "Buyer" (témoin) + "Principal Buyer" (principal)
  ✅ Flag PRIMARY dans E.DBF (True pour principal, False pour témoin)
  ✅ Activation PRINROLE/WITROLE dans T.DBF

Conservation v15 (robustesse) :
  ✅ extract_prefix_from_dbf_files() (pas de bug double underscore)
  ✅ Double mapping REFN ($.DBF → GEDCOM)
  ✅ Log orphelins détaillé
  ✅ Backup complet
  ✅ EVENT_MAPPING normalisé

Workflow :
  1. python mapping_tool.py G   →  génère mapping_master.xlsx
  2. Validez l'Excel
  3. python mapping_tool.py C   →  produit mapping.json
  4. python super_injecteur_v16_clean.py

Auteur: Claude + Olivier + Gemini (logique RED/GREEN)
Date: 2026-02-03
"""

import dbf
import re
import os
import sys
import unidecode
import shutil
from datetime import datetime
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox
import platform
import subprocess

print("=" * 80)
print("   SUPER-INJECTEUR TMG v16_CLEAN — RED/GREEN LOGIC")
print("=" * 80)
print()

import json

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

def normalize_role_id(val):
    """
    Normalise un ID de rôle en chaîne '00000'.
    
    TMG peut stocker les rôles comme int (3) ou string ("3" ou "00003").
    Cette fonction normalise tout vers "00003" pour comparaison cohérente.
    
    Args:
        val: Valeur du rôle (int, str, ou autre)
    
    Returns:
        str: Rôle normalisé au format "00000"
    """
    try:
        if isinstance(val, int):
            return f"{val:05d}"
        s = str(val).strip()
        if s.isdigit():
            return s.zfill(5)
        return s  # Cas rare où ce n'est pas un chiffre
    except:
        return "00000"

# --- CONFIGURATION ---
DEFAULT_TMG_PATH = r"C:\Users\olivi\OneDrive\Documents\The Master Genealogist v9\Projects"
DEFAULT_TMG_PREFIX = "vierge_"
DEFAULT_GEDCOM = r"G:\my fam tree\My Project Std ANSI.ged"
MAPPING_FILE = "mapping.json"

# =============================================================================
# NORMALISATION — doit être définie avant load_mapping()
# =============================================================================
def normalize(txt):
    """Normalisation : MAJUSCULES + sans accents"""
    if not txt: return ""
    return unidecode.unidecode(txt).upper().strip()

# =============================================================================
# CHARGEMENT DU MAPPING depuis mapping.json
# =============================================================================
def load_mapping():
    """
    Charge mapping.json et retourne deux dicts prêts à l'emploi :
      EVENTS : {normalize(ged_key): tmg_name}   ex: {"MARR": "Marriage", "NOTARY ACT": "deed"}
      ROLES  : {normalize(ged_key): {eng, fra}} ex: {"WITNESS": {"eng":"Witness","fra":"Témoin"}}
    """
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ FATAL ERROR: {MAPPING_FILE} not found!")
        print(f"   First run: python mapping_tool.py G  →  validate Excel  →  python mapping_tool.py C")
        sys.exit(1)

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Normaliser les clés une seule fois au chargement
    EVENTS = {}
    for k, v in data.get('events', {}).items():
        if v.get('tmg_name'):
            EVENTS[normalize(k)] = v['tmg_name']

    ROLES = {}
    for k, v in data.get('roles', {}).items():
        if v.get('eng'):
            ROLES[normalize(k)] = {'eng': v['eng'], 'fra': v.get('fra', v['eng'])}

    return EVENTS, ROLES

# Chargement au démarrage — remplace EVENT_MAPPING et ROLES_DB
EVENT_MAPPING, ROLES_DB = load_mapping()

# Variables globales
TMG_PROJECT_PATH = DEFAULT_TMG_PATH
TMG_PREFIX = DEFAULT_TMG_PREFIX
GEDCOM_PATH = DEFAULT_GEDCOM
DRY_RUN = False
LOG_FILE = None
LOG_CALLBACK = None  # Pour mode GUI

def log(message, level="INFO"):
    global LOG_CALLBACK
    
    # Convertir message en string si nécessaire
    if not isinstance(message, str):
        message = str(message)
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    
    # Mode GUI : envoyer au callback
    if LOG_CALLBACK:
        LOG_CALLBACK(message, level)
    else:
        try:
            print(log_line)
        except UnicodeEncodeError:
            print(log_line.encode('utf-8', errors='replace').decode('utf-8'))
    
    if LOG_FILE:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')


def create_backup():
    """
    Sauvegarde COMPLÈTE du projet TMG (DBF, FPT, CDX, PJC, etc.)
    CRITIQUE: Sans .FPT (mémos) et .CDX (index), le backup est inutilisable
    """
    log("=" * 80)
    log("CREATING COMPLETE SECURITY BACKUP", "BACKUP")
    log("=" * 80)
    
    # SÉCURITÉ: garantir que le préfixe se termine par underscore
    safe_prefix = TMG_PREFIX if TMG_PREFIX.endswith('_') else TMG_PREFIX + '_'
    
    backup_dir = os.path.join(TMG_PROJECT_PATH, f"BACKUP_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        os.makedirs(backup_dir, exist_ok=True)
        log(f"Backup folder: {backup_dir}", "BACKUP")
        log(f"Filtered prefix: {safe_prefix}", "BACKUP")
        
        files_copied = 0
        for file in os.listdir(TMG_PROJECT_PATH):
            src = os.path.join(TMG_PROJECT_PATH, file)
            
            # Ne copier que les fichiers (pas les sous-dossiers)
            if not os.path.isfile(src):
                continue
            
            # Filtre STRICT: le fichier doit commencer EXACTEMENT par safe_prefix
            # Ex: safe_prefix="testcase_" → OK: testcase_G.DBF, SKIP: testcase2_G.DBF
            if file.lower().startswith(safe_prefix.lower()):
                dst = os.path.join(backup_dir, file)
                shutil.copy2(src, dst)
                files_copied += 1
                log(f"  ✓ {file}", "BACKUP")
        
        log(f"✅ Backup created: {files_copied} files (DBF+FPT+CDX+PJC+...)", "BACKUP")
        log("=" * 80)
        return backup_dir
    except Exception as e:
        log(f"❌ BACKUP ERROR: {e}", "ERROR")
        sys.exit(1)

def get_tmg_file(suffix):
    path = os.path.join(TMG_PROJECT_PATH, f"{TMG_PREFIX}{suffix}.dbf")
    if not os.path.exists(path):
        log(f"Fichier introuvable : {path}", "ERROR")
        sys.exit(1)
    return path

def extract_year_tmg(edate_str):
    """
    Extrait l'année d'une date TMG
    Format TMG : 1YYYYMMDD (ex: 117501010 = 10 Oct 1750)
              ou 0(...) pour dates floues
    """
    if not edate_str: return None
    
    # Cas 1: Date précise "1YYYYMMDD"
    if edate_str.startswith('1') and len(edate_str) >= 5:
        return edate_str[1:5]
    
    # Cas 2: Date floue "0(...)" - cherche 4 chiffres
    if edate_str.startswith('0'):
        m = re.search(r'\d{4}', edate_str)
        if m: return m.group(0)
    
    return None

def scan_role_usage():
    """
    PASSE 1 - Logique RED/GREEN
    Détermine pour chaque rôle s'il est utilisé en mode :
    - 🟢 NORMAL : par un tiers (témoin classique)
    - 🔴 PRINCIPAL : par le propriétaire de l'événement (self-witness)
    """
    log("=" * 80)
    log("[1/5] GEDCOM SCAN — DETECTING ROLE USAGE (🟢 Normal vs 🔴 Principal)")
    log("=" * 80)
    
    role_usage = {}
    
    try:
        with open(GEDCOM_PATH, 'r', encoding='ansi') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(GEDCOM_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    current_indi_id = None
    current_event_tag = None
    current_event_type = None
    current_event_name_norm = None
    current_shars = []  # Liste de {'id': 'I123', 'role': 'Buyer'}
    
    for line in lines:
        parts = line.strip().split(' ', 2)
        if len(parts) < 2:
            continue
            
        level = int(parts[0])
        tag = parts[1]
        val = parts[2] if len(parts) > 2 else ""
        
        # Nouveau INDI
        if level == 0 and tag.startswith('@I'):
            # Analyser l'événement précédent avant de changer d'INDI
            if current_indi_id and current_shars and current_event_name_norm:
                _analyze_role_usage(current_indi_id, current_event_name_norm, current_shars, role_usage)
            
            current_indi_id = tag.strip('@')
            current_event_tag = None
            current_event_type = None
            current_event_name_norm = None
            current_shars = []
        
        # Nouvel événement (level 1)
        elif level == 1 and current_indi_id:
            # Analyser l'événement précédent
            if current_shars and current_event_name_norm:
                _analyze_role_usage(current_indi_id, current_event_name_norm, current_shars, role_usage)
            
            # Détecter si c'est un événement mappable
            if tag in ['BIRT', 'DEAT', 'MARR', 'EVEN', 'FACT', 'OCCU', 'BAPM', 'BURI', 'CHR', 'CENS', 'GRAD', 'RESI']:
                current_event_tag = tag
                current_event_type = val if tag in ['EVEN', 'FACT', 'OCCU'] else None
                current_shars = []
                
                # Déterminer le nom normalisé de l'événement
                if current_event_type:
                    # EVEN avec TYPE → utiliser TYPE
                    current_event_name_norm = normalize(EVENT_MAPPING.get(normalize(current_event_type), current_event_type))
                else:
                    # Tag direct
                    current_event_name_norm = normalize(EVENT_MAPPING.get(normalize(tag), tag))
            else:
                current_event_tag = None
                current_event_name_norm = None
                current_shars = []
        
        # TYPE pour EVEN/FACT/OCCU
        elif level == 2 and tag == 'TYPE' and current_event_tag:
            current_event_type = val
            current_event_name_norm = normalize(EVENT_MAPPING.get(normalize(val), val))
        
        # _SHAR
        elif level == 2 and tag == '_SHAR' and current_event_tag:
            wit_id = val.strip('@')
            current_shars.append({'id': wit_id, 'role': 'Witness'})  # Default
        
        # ROLE
        elif level == 3 and tag == 'ROLE' and current_shars:
            current_shars[-1]['role'] = val
    
    # Analyser le dernier événement
    if current_indi_id and current_shars and current_event_name_norm:
        _analyze_role_usage(current_indi_id, current_event_name_norm, current_shars, role_usage)
    
    # --- CORRECTION ICI : La conversion se fait APRES la boucle principale ---
    for r in role_usage.values():
        if isinstance(r['events'], set):
            r['events'] = sorted(list(r['events']))
    
    # Affichage résumé
    log(f"✓ Roles detected: {len(role_usage)}")
    
    count_normal = sum(1 for r in role_usage.values() if r['normal'])
    count_principal = sum(1 for r in role_usage.values() if r['principal'])
    count_both = sum(1 for r in role_usage.values() if r['normal'] and r['principal'])
    
    log(f"  → 🟢 Used as witnesses: {count_normal}")
    log(f"  → 🔴 Used as principals: {count_principal}")
    log(f"  → 🟡 Both: {count_both}")
    
    # Afficher détails pour debug
    for role_norm, data in sorted(role_usage.items()):
        modes = []
        if data['normal']: modes.append("🟢")
        if data['principal']: modes.append("🔴")
        events_str = ", ".join(data['events'][:3])
        if len(data['events']) > 3:
            events_str += f" (+{len(data['events'])-3} more)"
        log(f"     {' '.join(modes)} {data['eng']:<20} → {events_str}")
    
    return role_usage

def _analyze_role_usage(owner_id, event_name_norm, shars, role_usage):
    """
    Analyse les _SHAR d'un événement pour déterminer usage normal vs principal
    """
    for shar in shars:
        role_raw = shar['role']
        role_norm = normalize(role_raw)
        
        # Initialiser si nouveau rôle
        if role_norm not in role_usage:
            # Chercher labels dans ROLES_DB
            role_info = ROLES_DB.get(role_norm, {"eng": role_raw.title(), "fra": role_raw.title()})
            
            role_usage[role_norm] = {
                'normal': False,
                'principal': False,
                'eng': role_info['eng'],
                'fra': role_info['fra'],
                'events': set()  # Set pour éviter doublons et permettre .add()
            }
        
        # Ajouter l'événement
        # Ceci ne plantera plus car on garantit que 'events' est un set ici
        role_usage[role_norm]['events'].add(event_name_norm)
        
        # Déterminer si normal ou principal
        if shar['id'] == owner_id:
            # 🔴 Self-witness (Principal)
            role_usage[role_norm]['principal'] = True
        else:
            # 🟢 Témoin tiers
            role_usage[role_norm]['normal'] = True

def update_tmg_structure(role_usage):
    """
    PASSE 2 - Mise à jour T.DBF
    Pour chaque événement qui utilise des rôles :
    1. Crée les rôles NORMAL (ex: "Buyer") si usage normal
    2. Crée les rôles PRINCIPAL (ex: "Principal Buyer") si usage principal
    3. Active PRINROLE=True et WITROLE=True
    
    Retourne:
        event_ids: {event_name_norm: etype}
        role_codes: {etype: {role_norm: {'NORMAL': code, 'PRINCIPAL': code}}}
    """
    log("=" * 80)
    log("[2/5] UPDATING T.DBF (NORMAL/PRINCIPAL role pairs)")
    log("=" * 80)
    
    if DRY_RUN:
        log("⚠️  SIMULATION MODE - No changes will be saved", "DRYRUN")
    
    event_ids = {}
    role_codes = {}  # {etype: {role_norm: {'NORMAL': 101, 'PRINCIPAL': 102}}}
    
    t = dbf.Table(get_tmg_file("T"))
    t.open(dbf.READ_WRITE if not DRY_RUN else dbf.READ_ONLY)
    
    regex_full_role = re.compile(r'\[RL=(\d+)\](.*?)(?=\[RL=|\[:LABELS\]|$)', re.DOTALL)
    regex_lbl = re.compile(r'(?:\[L=[^\]]+\])?([^\[\r\n]+)')
    
    modifications = []
    
    for rec in t:
        ename = rec.etypename.strip()
        ename_norm = normalize(ename)
        eid = rec.etypenum
        sent = rec.tsentence.strip()
        
        # Stocker l'ID de l'événement
        event_ids[ename_norm] = eid
        role_codes[eid] = {}
        
        # Parser les rôles existants dans cet événement
        existing_roles = {}  # {role_norm: role_id}
        max_role_id = 0
        
        if "[LABELS:]" not in sent:
            sent += "\r[LABELS:]\r[:LABELS]"
        
        if "[LABELS:]" in sent:
            try:
                labels_content = sent.split("[LABELS:]")[1].split("[:LABELS]")[0]
                for m in regex_full_role.finditer(labels_content):
                    rid = int(m.group(1))
                    max_role_id = max(max_role_id, rid)
                    block = m.group(2)
                    for lm in regex_lbl.finditer(block):
                        existing_roles[normalize(lm.group(1))] = rid
            except:
                pass
        
        # Déterminer quels rôles sont utilisés par CET événement
        roles_for_this_event = []
        for role_norm, data in role_usage.items():
            if ename_norm in data['events']:
                roles_for_this_event.append((role_norm, data))
        
        if not roles_for_this_event:
            # Pas de rôles pour cet événement
            continue
        
        # Créer les rôles manquants (paires NORMAL + PRINCIPAL si nécessaire)
        roles_to_create = []
        needs_prinrole = False
        needs_witrole = False
        
        for role_norm, data in roles_for_this_event:
            base_eng = data['eng']
            base_fra = data['fra']
            
            # Rôle NORMAL (🟢 témoin tiers)
            if data['normal']:
                needs_witrole = True
                if normalize(base_eng) in existing_roles:
                    # Déjà existe
                    role_codes[eid].setdefault(role_norm, {})['NORMAL'] = existing_roles[normalize(base_eng)]
                else:
                    # À créer
                    roles_to_create.append({
                        'eng': base_eng,
                        'fra': base_fra,
                        'key': role_norm,
                        'type': 'NORMAL'
                    })
            
            # Rôle PRINCIPAL (🔴 self-witness)
            if data['principal']:
                needs_prinrole = True
                prin_eng = f"Principal {base_eng}"
                prin_fra = f"Principal {base_fra}"
                
                if normalize(prin_eng) in existing_roles:
                    # Déjà existe
                    role_codes[eid].setdefault(role_norm, {})['PRINCIPAL'] = existing_roles[normalize(prin_eng)]
                else:
                    # À créer
                    roles_to_create.append({
                        'eng': prin_eng,
                        'fra': prin_fra,
                        'key': role_norm,
                        'type': 'PRINCIPAL'
                    })
        
        # Injection dans T.DBF
        if roles_to_create or (needs_prinrole and not rec.prinrole) or (needs_witrole and not rec.witrole):
            log(f"  → Event '{ename}' (ETYPE={eid}):")
            
            if roles_to_create:
                log(f"     Roles to create: {len(roles_to_create)}")
            
            insertion_str = ""
            current_id = max_role_id
            
            for new_role in roles_to_create:
                current_id += 1
                insertion_str += f"\r[RL={current_id:05d}][L=ENGLISH]{new_role['eng']}[L=FRENCH]{new_role['fra']}"
                
                # Stocker dans role_codes
                role_codes[eid].setdefault(new_role['key'], {})[new_role['type']] = current_id
                
                symbol = "🔴" if new_role['type'] == 'PRINCIPAL' else "🟢"
                log(f"     + {symbol} Code {current_id:05d} = {new_role['eng']}/{new_role['fra']}")
            
            # Construire nouveau TSENTENCE
            if insertion_str:
                parts = sent.split("[:LABELS]")
                new_sent = parts[0] + insertion_str + "\r[:LABELS]" + (parts[1] if len(parts) > 1 else "")
            else:
                new_sent = sent
            
            # Activer PRINROLE et WITROLE si nécessaire
            if not DRY_RUN:
                dbf.write(rec, 
                         tsentence=new_sent,
                         prinrole=needs_prinrole or rec.prinrole,
                         witrole=needs_witrole or rec.witrole)
                modifications.append(ename)
                
                if needs_prinrole and not rec.prinrole:
                    log(f"     ✓ PRINROLE enabled")
                if needs_witrole and not rec.witrole:
                    log(f"     ✓ WITROLE enabled")
            else:
                log(f"     [SIMULATION] Changes not saved", "DRYRUN")
    
    t.close()
    
    if modifications:
        log(f"✅ {len(modifications)} events modified in T.DBF")
    else:
        log("✓ No modifications needed in T.DBF")
    
    log("=" * 80)
    
    return event_ids, role_codes

def load_persons_and_events():
    log("=" * 80)
    log("[3/5] MEMORY INDEXING ($.DBF, G.DBF, E.DBF)")
    log("=" * 80)
    
    # 1. PERSONNES ($.DBF)
    log("  → Loading persons ($.DBF)...")
    refn_to_perno = {}
    dsid = 1
    
    try:
        with dbf.Table(get_tmg_file("$")) as t:
            t.open(dbf.READ_ONLY)
            for r in t:
                if dsid == 1 and hasattr(r, 'dsid') and r.dsid > 0:
                    dsid = r.dsid
                if hasattr(r, 'reference'):
                    ref = r.reference.strip()
                    if ref:
                        refn_to_perno[ref] = r.per_no
    except Exception as e:
        log(f"$.DBF Error: {e}", "ERROR")
        sys.exit(1)
    
    log(f"  ✓ {len(refn_to_perno)} persons indexed")
    log(f"  ✓ DSID detected: {dsid}")
    
    # 2. ÉVÉNEMENTS (G.DBF) - Indexation RAM
    log("  → Indexing events (G.DBF)...")
    events_index = {}
    event_count = 0
    
    try:
        with dbf.Table(get_tmg_file("G")) as t:
            t.open(dbf.READ_ONLY)
            for r in t:
                evt_data = {'recno': r.recno, 'edate': r.edate, 'per1': r.per1, 'per2': r.per2}
                event_count += 1
                
                # Index PER1
                if r.per1 > 0:
                    key1 = (r.per1, r.etype)
                    if key1 not in events_index:
                        events_index[key1] = []
                    events_index[key1].append(evt_data)
                
                # Index PER2 (pour mariages)
                if r.per2 > 0:
                    key2 = (r.per2, r.etype)
                    if key2 not in events_index:
                        events_index[key2] = []
                    events_index[key2].append(evt_data)
    except Exception as e:
        log(f"G.DBF Error: {e}", "ERROR")
        sys.exit(1)
    
    log(f"  ✓ {event_count} events indexed in memory")
    log(f"  ✓ {len(events_index)} unique keys (person, type)")
    
    # 3. TÉMOINS EXISTANTS (E.DBF) - Cache avec clé normalisée 4-tuple
    log("  → Loading existing witnesses (E.DBF) in RAM...")
    existing_witnesses = set()
    
    try:
        with dbf.Table(get_tmg_file("E")) as t:
            t.open(dbf.READ_ONLY)
            for r in t:
                if r.gnum > 0 and r.eper > 0:
                    # 1. Normalisation Rôle (int → "00003", "3" → "00003")
                    role_norm = normalize_role_id(r.role)
                    
                    # 2. Normalisation Primary (Force en booléen Python)
                    is_prim = bool(r.primary)
                    
                    # 3. Clé à 4 facteurs (GNUM, EPER, ROLE, PRIMARY)
                    key = (r.gnum, r.eper, role_norm, is_prim)
                    existing_witnesses.add(key)
    except Exception as e:
        log(f"E.DBF Error: {e}", "ERROR")
        sys.exit(1)
    
    log(f"  ✓ {len(existing_witnesses)} existing witnesses in cache (Strict 4-tuple key)")
    
    # 4. MAP GEDCOM → TMG
    log("  → Mapping GEDCOM → TMG...")
    ged_to_perno = {}
    
    with open(GEDCOM_PATH, 'r', encoding='ansi') as f:
        gid = None
        for line in f:
            if line.startswith('0 @I'):
                gid = line.split()[1].strip('@')
            elif line.startswith('1 REFN') and gid:
                refn = line.split()[2].strip()
                if refn in refn_to_perno:
                    ged_to_perno[gid] = refn_to_perno[refn]
                gid = None
    
    log(f"  ✓ {len(ged_to_perno)} GEDCOM persons mapped")
    log("=" * 80)
    
    return ged_to_perno, dsid, events_index, existing_witnesses

def inject_witnesses(evt_ids, role_codes, ged_to_perno, dsid, events_index, existing_witnesses):
    log("=" * 80)
    log("[4/5] INJECTING WITNESSES INTO E.DBF (with RED/GREEN logic)")
    log("=" * 80)
    
    if DRY_RUN:
        log("⚠️  SIMULATION MODE - No data will be saved", "DRYRUN")
    
    tw = dbf.Table(get_tmg_file("E"))
    tw.open(dbf.READ_WRITE if not DRY_RUN else dbf.READ_ONLY)
    
    stats = {'ok': 0, 'principal': 0, 'skip': 0, 'error': 0}
    last_logged = 0
    
    # Parser le GEDCOM par blocs (@I et @F)
    with open(GEDCOM_PATH, 'r', encoding='ansi') as f:
        block = []
        for line in f:
            # Détecter début de bloc INDI ou FAM
            if line.startswith('0 @I') or line.startswith('0 @F'):
                # Traiter le bloc précédent
                if block:
                    process_block(block, evt_ids, role_codes, ged_to_perno, 
                                events_index, tw, dsid, stats, existing_witnesses)
                    
                    # Log batch tous les 50 témoins
                    total_injected = stats['ok'] + stats['principal']
                    if total_injected >= last_logged + 50:
                        log(f"   ✓ {total_injected} witnesses injected (🟢 {stats['ok']} + 🔴 {stats['principal']})...")
                        last_logged = total_injected
                
                # Commencer nouveau bloc
                block = [line]
            else:
                block.append(line)
        
        # Traiter le dernier bloc
        if block:
            process_block(block, evt_ids, role_codes, ged_to_perno, 
                        events_index, tw, dsid, stats, existing_witnesses)
    
    tw.close()
    
    log("=" * 80)
    log("[5/5] INJECTION SUMMARY")
    log("=" * 80)
    log(f"  🟢 Witnesses (others)  : {stats['ok']}")
    log(f"  🔴 Principals (self)   : {stats['principal']}")
    log(f"  ⏭️  Skipped witnesses   : {stats['skip']} (duplicates)")
    log(f"  ❌ Errors              : {stats['error']}")
    log(f"  📊 TOTAL injected      : {stats['ok'] + stats['principal']}")
    log("=" * 80)
    
    if not DRY_RUN and (stats['ok'] + stats['principal']) > 0:
        log("")
        log("🎯 MANDATORY NEXT STEP:")
        log("   1. Open TMG")
        log("   2. File → Maintenance → Reindex All Files")
        log("   3. Check witnesses in your events")
        log("   4. For 🔴 Principals: Verify PRIMARY=True in E.DBF")
        log("")
    elif DRY_RUN:
        log("")
        log("✅ SIMULATION COMPLETED")
        log("   To perform real injection, re-run without --dry-run")
        log("")

def process_block(lines, evt_ids, role_codes, ged_to_perno, events_index, tw, dsid, stats, existing_witnesses):
    """
    Traite un bloc GEDCOM (individu @I ou famille @F)
    Pour @F (mariages), extrait HUSB ou WIFE pour attacher les témoins
    """
    head = lines[0]
    pper = None
    
    if head.startswith('0 @I'):
        # Bloc individu : récupérer directement la personne
        gid = head.split()[1].strip('@')
        if gid in ged_to_perno:
            pper = ged_to_perno[gid]
    
    elif head.startswith('0 @F'):
        # Bloc famille : chercher HUSB (mari) ou WIFE (femme)
        husb_gid = None
        wife_gid = None
        
        for l in lines:
            if l.startswith('1 HUSB'):
                parts = l.split('@')
                if len(parts) > 1:
                    husb_gid = parts[1]
            elif l.startswith('1 WIFE'):
                parts = l.split('@')
                if len(parts) > 1:
                    wife_gid = parts[1]
        
        # Priorité : HUSB puis WIFE
        if husb_gid and husb_gid in ged_to_perno:
            pper = ged_to_perno[husb_gid]
        elif wife_gid and wife_gid in ged_to_perno:
            pper = ged_to_perno[wife_gid]
    
    # Traiter les événements si on a trouvé une personne
    if pper:
        process_events(lines, pper, evt_ids, role_codes, ged_to_perno, 
                      events_index, tw, dsid, stats, existing_witnesses)

def process_events(lines, pper, evt_ids, role_codes, ged_to_perno, events_index, tw, dsid, stats, existing_witnesses):
    """Traite tous les événements d'un bloc (INDI ou FAM)"""
    
    current_evt = {'tag': None, 'eid': None, 'date': None, 'witnesses': []}
    
    for l in lines:
        p = l.strip().split(' ', 2)
        if len(p) < 2: continue
        
        lvl, tag, val = int(p[0]), p[1], p[2] if len(p) > 2 else ""
        
        if lvl == 1:
            # Sauvegarder l'événement précédent
            flush_event(current_evt, pper, evt_ids, role_codes, ged_to_perno, 
                       events_index, tw, dsid, stats, existing_witnesses)
            
            # Nouveau événement — lookup dans mapping.json via clé normalisée
            norm_tag = normalize(EVENT_MAPPING.get(normalize(tag), tag))
            eid = evt_ids.get(norm_tag)
            
            # Gérer EVEN/FACT/OCCU avec TYPE
            if not eid and tag in ['FACT', 'EVEN', 'OCCU'] and val:
                target = EVENT_MAPPING.get(normalize(val), normalize(val))
                eid = evt_ids.get(normalize(target))
            
            current_evt = {'tag': tag, 'eid': eid, 'date': None, 'witnesses': []}
        
        elif lvl == 2:
            if tag == 'DATE':
                current_evt['date'] = val.strip()
            elif tag == 'TYPE' and current_evt['tag'] in ['EVEN', 'FACT', 'OCCU']:
                # Re-chercher l'EID avec le TYPE
                target = EVENT_MAPPING.get(normalize(val), normalize(val))
                eid = evt_ids.get(normalize(target))
                if eid:
                    current_evt['eid'] = eid
            elif tag == '_SHAR':
                wit_id = val.strip('@')
                current_evt['witnesses'].append({'wit_ged': wit_id, 'role': 'Witness', 'note': ''})
        
        elif lvl == 3 and current_evt['witnesses']:
            if tag == 'ROLE':
                current_evt['witnesses'][-1]['role'] = val.strip()
            elif tag == 'NOTE':
                current_evt['witnesses'][-1]['note'] += " " + val.strip()
    
    # Sauvegarder le dernier événement
    flush_event(current_evt, pper, evt_ids, role_codes, ged_to_perno, 
               events_index, tw, dsid, stats, existing_witnesses)

def flush_event(evt_ctx, pper, evt_ids, role_codes, ged_to_perno, events_index, tw, dsid, stats, existing_witnesses):
    """Injecte les témoins d'un événement"""
    
    if not evt_ctx or not evt_ctx['eid'] or not evt_ctx['witnesses']:
        return
    
    # Extraire l'année du GEDCOM
    y_ged = None
    if evt_ctx['date']:
        for x in evt_ctx['date'].split():
            if x.isdigit() and len(x) == 4:
                y_ged = x
                break
    
    # Chercher l'événement dans G.DBF via l'index RAM
    candidates = events_index.get((pper, evt_ctx['eid']), [])
    
    target_gnum = None
    for cand in candidates:
        match = True
        if y_ged:
            y_tmg = extract_year_tmg(cand['edate'])
            # Si TMG a une année valide, elle doit matcher GEDCOM
            if y_tmg and y_tmg != '0000' and y_tmg != y_ged:
                match = False
        
        if match:
            target_gnum = cand['recno']
            break
    
    if not target_gnum:
        stats['error'] += len(evt_ctx['witnesses'])
        return
    
    # Récupérer PER1/PER2 du candidat pour le check anti-auto-référence
    target_per1 = 0
    target_per2 = 0
    for cand in candidates:
        if cand['recno'] == target_gnum:
            target_per1 = cand.get('per1', 0)
            target_per2 = cand.get('per2', 0)
            break
    
    # Injecter chaque témoin
    for wit in evt_ctx['witnesses']:
        res = insert_single_witness(wit, evt_ctx['eid'], target_gnum, role_codes, 
                                    ged_to_perno, existing_witnesses, tw, dsid,
                                    target_per1, target_per2)
        stats[res] += 1

def insert_single_witness(wit_data, eid, gnum, role_codes, ged_to_perno, existing_witnesses, tw, dsid, evt_per1=0, evt_per2=0):
    """
    Insère un témoin unique avec logique RED/GREEN
    
    🟢 NORMAL (témoin tiers) : PRIMARY=False, utilise rôle standard
    🔴 PRINCIPAL (self-witness) : PRIMARY=True, utilise rôle "Principal X"
    """
    
    # Vérifier que le témoin existe dans TMG
    wper = ged_to_perno.get(wit_data['wit_ged'])
    if not wper:
        return 'error'
    
    # ✅ LOGIQUE RED/GREEN : Détecter si self-witness
    is_self = (wper == evt_per1 or (evt_per2 and wper == evt_per2))
    
    # Déterminer le code du rôle approprié (NORMAL vs PRINCIPAL)
    role_ged_norm = normalize(wit_data['role'])
    role_info = ROLES_DB.get(role_ged_norm, {"eng": wit_data['role'].title(), "fra": wit_data['role'].title()})
    
    # role_codes[eid] = {role_norm: {'NORMAL': 101, 'PRINCIPAL': 102}}
    roles_this_evt = role_codes.get(eid, {})
    role_map = roles_this_evt.get(role_ged_norm, {})
    
    # Choisir le bon code selon is_self
    if is_self:
        # 🔴 Self-witness → utiliser rôle PRINCIPAL
        final_code = role_map.get('PRINCIPAL')
        context = "PRINCIPAL"
    else:
        # 🟢 Témoin tiers → utiliser rôle NORMAL
        final_code = role_map.get('NORMAL')
        context = "NORMAL"
    
    memo = wit_data['note']
    
    if not final_code:
        # Fallback si le rôle spécifique n'existe pas
        # Chercher "Witness" standard
        witness_map = roles_this_evt.get('WITNESS', {})
        if is_self:
            final_code = witness_map.get('PRINCIPAL') or witness_map.get('NORMAL')
        else:
            final_code = witness_map.get('NORMAL') or witness_map.get('PRINCIPAL')
        
        if not final_code:
            # Dernier fallback
            final_code = 2  # Code par défaut Witness
        
        # Ajouter le rôle au memo si fallback
        memo = f"[{role_info['eng']}] {memo}"
    
    role_formatted = f"{final_code:05d}"
    
    # --- GARDE-FOU ANTI-DOUBLON (PATCH v16.1 - Gemini) ---
    
    # On normalise pour être sûr de comparer des pommes avec des pommes
    role_to_check = normalize_role_id(role_formatted)
    
    # On construit la MÊME clé que lors du chargement (4-tuple normalisé)
    check_key = (gnum, wper, role_to_check, is_self)
    
    if check_key in existing_witnesses:
        # DÉJÀ PRÉSENT : ON NE FAIT RIEN
        return 'skip'
    
    # --- FIN GARDE-FOU ---
    
    # Calculer SEQUENCE
    if DRY_RUN:
        new_seq = 1
    else:
        max_seq = 0
        for row in tw:
            if row.gnum == gnum and row.sequence > max_seq:
                max_seq = row.sequence
        new_seq = max_seq + 1
    
    # ✅ INJECTION avec PRIMARY flag
    try:
        if not DRY_RUN:
            tw.append({
                'EPER': wper,
                'GNUM': gnum,
                'DSID': dsid,
                'SEQUENCE': new_seq,
                'PRIMARY': is_self,  # ← LE FLAG CRITIQUE !
                'ROLE': role_formatted,
                'WITMEMO': memo[:60000]
            })
        
        # Ajouter au cache RAM
        existing_witnesses.add(check_key)
        
        # Retourner le bon statut pour stats
        if is_self:
            return 'principal'  # Nouveau statut
        else:
            return 'ok'
    except:
        return 'error'

# =============================================================================
# GUI — CONFIG + DIALOGUES
# =============================================================================

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".tmg_injector_v16_clean_config.json")

def save_config(gedcom_path, pjc_path, tmg_prefix):
    config = {
        'gedcom_path': gedcom_path,
        'pjc_path': pjc_path,
        'tmg_prefix': tmg_prefix,
        'last_used': datetime.now().isoformat()
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except:
        pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def ask_use_last_config():
    config = load_config()
    if not config:
        return None
    if not os.path.exists(config['gedcom_path']) or not os.path.exists(config['pjc_path']):
        return None

    root = tk.Tk()
    root.withdraw()
    message = (
        "Last files used:\n\n"
        f"GEDCOM : {config['gedcom_path']}\n"
        f"Project: {config['pjc_path']}\n"
        f"Prefix : {config['tmg_prefix']}\n\n"
        "Use these files?"
    )
    response = messagebox.askyesno("Last configuration", message, default=messagebox.YES)
    root.destroy()
    return config if response else None

def select_gedcom_file():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select GEDCOM file",
        filetypes=[("GEDCOM files", "*.ged"), ("All files", "*.*")],
        initialdir=os.path.expanduser("~")
    )
    root.destroy()
    return path

def select_tmg_project_file():
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select TMG project file (.PJC)",
        filetypes=[("TMG Projects", "*.PJC"), ("All files", "*.*")],
        initialdir=os.path.expanduser("~")
    )
    root.destroy()
    return path

def extract_prefix_from_dbf_files(tmg_dir, pjc_filename=None):
    dbf_files = [f for f in os.listdir(tmg_dir) if f.upper().endswith('.DBF')]
    if not dbf_files:
        raise FileNotFoundError(f"No .DBF file found in {tmg_dir}")

    essential_suffixes = ['$.DBF', 'G.DBF', 'E.DBF', 'T.DBF']
    prefixes_found = set()

    for dbf_file in dbf_files:
        for suffix in essential_suffixes:
            if dbf_file.upper().endswith(suffix):
                prefixes_found.add(dbf_file[:len(dbf_file) - len(suffix)])
                break

    if not prefixes_found:
        raise FileNotFoundError(f"Aucun fichier essentiel ($.DBF, G.DBF, E.DBF, T.DBF) dans {tmg_dir}")

    if len(prefixes_found) == 1:
        prefix = prefixes_found.pop()
    elif pjc_filename:
        pjc_base = os.path.splitext(pjc_filename)[0].rstrip('_')
        matching = [p for p in prefixes_found if p.lower().startswith(pjc_base.lower())]
        if len(matching) == 1:
            prefix = matching[0]
        elif len(matching) > 1:
            prefix = min(matching, key=len)
        else:
            raise ValueError(f"Prefix not found for {pjc_filename}. Available prefixes: {sorted(prefixes_found)}")
    else:
        raise ValueError(f"Multiple prefixes detected: {sorted(prefixes_found)}")

    # Vérification fichiers essentiels
    missing = [f"{prefix}{s}" for s in essential_suffixes if not os.path.exists(os.path.join(tmg_dir, f"{prefix}{s}"))]
    if missing:
        raise FileNotFoundError(f"Fichiers manquants: {missing}")

    return prefix

def confirm_dry_run():
    root = tk.Tk()
    root.withdraw()
    response = messagebox.askyesno(
        "Test mode",
        "Run in TEST MODE (Dry-Run)?\n\n"
        "YES = Simulation without modification\n"
        "NO  = REAL injection into TMG",
        default=messagebox.YES
    )
    root.destroy()
    return response

# =============================================================================
# MAIN
# =============================================================================

def main():
    global TMG_PROJECT_PATH, TMG_PREFIX, GEDCOM_PATH, DRY_RUN, LOG_FILE

    # --- SÉCURITÉ : Vérifier que TMG n'est pas ouvert ---
    if is_tmg_running():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "⛔ TMG is Running!",
            "The Master Genealogist (TMG.EXE) is currently running.\n\n"
            "Please close TMG before running Role Injection.\n\n"
            "Modifying database files while TMG is open can cause corruption."
        )
        root.destroy()
        sys.exit(1)

    # --- Vérification mapping.json AVANT tout ---
    if not os.path.exists(MAPPING_FILE):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "mapping.json missing",
            f"File {MAPPING_FILE} not found!\n\n"
            "Required workflow before injection:\n"
            "  1. python mapping_tool.py G\n"
            "  2. Validate Excel\n"
            "  3. python mapping_tool.py C\n\n"
            "Then re-run this script."
        )
        root.destroy()
        sys.exit(1)

    # --- Parser args (compatibilité CLI) ---
    parser = argparse.ArgumentParser(description='Super-Injecteur TMG v16_CLEAN — RED/GREEN Logic')
    parser.add_argument('--gedcom', help='Chemin vers le fichier GEDCOM')
    parser.add_argument('--pjc', help='Fichier projet TMG (.PJC)')
    parser.add_argument('--dry-run', action='store_true', help='Mode simulation')
    parser.add_argument('--no-gui', action='store_true', help='Pas de dialogues GUI')
    parser.add_argument('--no-backup', action='store_true', help='Ne pas créer de backup')
    args = parser.parse_args()

    # --- SÉLECTION FICHIERS ---
    if args.no_gui:
        # Mode ligne de commande
        GEDCOM_PATH = args.gedcom or DEFAULT_GEDCOM
        if args.pjc:
            TMG_PROJECT_PATH = os.path.dirname(args.pjc)
            try:
                TMG_PREFIX = extract_prefix_from_dbf_files(TMG_PROJECT_PATH, os.path.basename(args.pjc))
            except:
                TMG_PREFIX = DEFAULT_TMG_PREFIX
        DRY_RUN = args.dry_run

    else:
        # Mode GUI
        print(f"✅ mapping.json detected ({len(EVENT_MAPPING)} events, {len(ROLES_DB)} roles)")
        print()

        last_config = ask_use_last_config()

        if last_config:
            GEDCOM_PATH = last_config['gedcom_path']
            TMG_PROJECT_PATH = os.path.dirname(last_config['pjc_path'])
            TMG_PREFIX = last_config['tmg_prefix']
            print("✓ Previous configuration loaded:")
            print(f"  GEDCOM : {GEDCOM_PATH}")
            print(f"  Project: {last_config['pjc_path']}")
            print(f"  Prefix : {TMG_PREFIX}")
            print()
        else:
            # Sélection manuelle
            print("🖱️  Selecting GEDCOM file...")
            GEDCOM_PATH = select_gedcom_file()
            if not GEDCOM_PATH:
                print("❌ No GEDCOM file selected. Aborting.")
                return
            print(f"✓ GEDCOM: {GEDCOM_PATH}\n")

            print("🖱️  Selecting TMG project (.PJC)...")
            pjc_path = select_tmg_project_file()
            if not pjc_path:
                print("❌ No .PJC file selected. Aborting.")
                return
            print(f"✓ Project: {pjc_path}\n")

            TMG_PROJECT_PATH = os.path.dirname(pjc_path)
            pjc_filename = os.path.basename(pjc_path)

            print("🔍 Auto-detecting TMG prefix...")
            try:
                TMG_PREFIX = extract_prefix_from_dbf_files(TMG_PROJECT_PATH, pjc_filename)
                print(f"✅ Prefix detected: {TMG_PREFIX}")
            except Exception as e:
                print(f"❌ Prefix detection error: {e}")
                TMG_PREFIX = input("TMG prefix (e.g. vierge_): ").strip()
            print()

            save_config(GEDCOM_PATH, pjc_path, TMG_PREFIX)

        # Demander dry-run
        DRY_RUN = confirm_dry_run()

    # --- AFFICHAGE CONFIG ---
    print("=" * 80)
    print("CONFIGURATION — SUPER-INJECTOR v16_CLEAN (RED/GREEN)")
    print("=" * 80)
    print(f"  mapping.json : ✅ {len(EVENT_MAPPING)} events, {len(ROLES_DB)} roles")
    print(f"  TMG Folder   : {TMG_PROJECT_PATH}")
    print(f"  TMG Prefix   : {TMG_PREFIX}")
    print(f"  GEDCOM       : {GEDCOM_PATH}")
    print(f"  Mode         : {'DRY-RUN (simulation)' if DRY_RUN else 'REAL'}")
    print("=" * 80)
    print()

    if not DRY_RUN:
        input("⚠️  Press ENTER to continue REAL injection...")

    # --- LOG FILE ---
    LOG_FILE = os.path.join(
        TMG_PROJECT_PATH,
        f"injection_v16_clean_{'dryrun' if DRY_RUN else 'real'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    log("Configuration:")
    log(f"  TMG Path   : {TMG_PROJECT_PATH}")
    log(f"  TMG Prefix : {TMG_PREFIX}")
    log(f"  GEDCOM     : {GEDCOM_PATH}")
    log(f"  mapping.json : {len(EVENT_MAPPING)} events, {len(ROLES_DB)} roles")
    log(f"  Mode       : {'SIMULATION' if DRY_RUN else 'REAL'}")
    log(f"  Log        : {LOG_FILE}")
    log("")

    # Vérifications
    if not os.path.exists(GEDCOM_PATH):
        log(f"GEDCOM file not found: {GEDCOM_PATH}", "ERROR")
        sys.exit(1)

    # Backup
    if not DRY_RUN and not args.no_backup:
        create_backup()

    # --- MOTEUR v16_CLEAN (avec RED/GREEN) ---
    role_usage = scan_role_usage()
    evt_ids, role_codes = update_tmg_structure(role_usage)
    ged_to_perno, dsid, events_index, existing_witnesses = load_persons_and_events()
    inject_witnesses(evt_ids, role_codes, ged_to_perno, dsid, events_index, existing_witnesses)

    log("")
    log("=" * 80)
    log("COMPLETED!")
    log("=" * 80)
    log("")
    log("Super-Injector v16_CLEAN — RED/GREEN Logic:")
    log("  ✅ Base v15 (works: 440 witnesses)")
    log("  ✅ + RED/GREEN Logic (Self-Witness)")
    log("  ✅ Auto-detection 🟢 Normal vs 🔴 Principal")
    log("  ✅ Role pairs in T.DBF (Buyer + Principal Buyer)")
    log("  ✅ PRIMARY flag in E.DBF (True for principal)")
    log("  ✅ PRINROLE/WITROLE enabled automatically")
    log("  ✅ Mapping from mapping.json")
    log("  ✅ GUI with memory")
    log("  ✅ Automatic backup")
    log("  ✅ Detailed logs")
    log("")
    print(f"📄 Log saved: {LOG_FILE}")
    print()
    
    # PAUSE FINALE: empêche la fermeture automatique de la console
    print("=" * 80)
    input("✅ Completed! Press ENTER to close this window...")

if __name__ == "__main__":
    main()
# =============================================================================
# MODE GUI - Pour intégration dans TMG Suite
# =============================================================================
LOG_CALLBACK = None

def inject_roles_mode(gedcom_path, tmg_project_path, tmg_prefix, 
                      mapping_file="mapping.json", log_callback=None, dry_run=False):
    """
    Mode GUI pour injection des rôles
    
    Args:
        gedcom_path: Chemin vers GEDCOM
        tmg_project_path: Dossier projet TMG
        tmg_prefix: Préfixe TMG
        mapping_file: Fichier mapping.json
        log_callback: Fonction callback pour logs
        dry_run: Mode simulation
    
    Returns:
        dict: Statistiques d'injection
    """
    global TMG_PROJECT_PATH, TMG_PREFIX, GEDCOM_PATH, DRY_RUN, LOG_FILE, EVENT_MAPPING, ROLES_DB, LOG_CALLBACK
    
    LOG_CALLBACK = log_callback
    TMG_PROJECT_PATH = tmg_project_path
    TMG_PREFIX = tmg_prefix
    GEDCOM_PATH = gedcom_path
    DRY_RUN = dry_run
    
    # SÉCURITÉ : Vérifier que TMG n'est pas en cours d'exécution
    if is_tmg_running():
        error_msg = "⛔ TMG.EXE is currently running!\n\n" + \
                    "Please close The Master Genealogist before running Role Injection.\n\n" + \
                    "Modifying database files while TMG is open can cause corruption."
        log(error_msg, "ERROR")
        return {'success': False, 'error': error_msg}
    
    # Vérifier mapping.json
    if not os.path.exists(mapping_file):
        log(f"File not found: {mapping_file}", "ERROR")
        return {'success': False, 'error': 'mapping.json not found'}
    
    # Charger mapping
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraire les valeurs correctement (comme dans load_mapping)
        EVENT_MAPPING = {}
        for k, v in data.get('events', {}).items():
            if isinstance(v, dict) and v.get('tmg_name'):
                EVENT_MAPPING[normalize(k)] = v['tmg_name']
            elif isinstance(v, str):
                EVENT_MAPPING[normalize(k)] = v
        
        ROLES_DB = {}
        for k, v in data.get('roles', {}).items():
            if isinstance(v, dict) and v.get('eng'):
                ROLES_DB[normalize(k)] = {'eng': v['eng'], 'fra': v.get('fra', v['eng'])}
            elif isinstance(v, str):
                ROLES_DB[normalize(k)] = {'eng': v, 'fra': v}
        
        log(f"Mapping loaded: {len(EVENT_MAPPING)} events, {len(ROLES_DB)} roles", "SUCCESS")
    except Exception as e:
        log(f"Error loading mapping: {e}", "ERROR")
        return {'success': False, 'error': str(e)}
    
    # Log file
    LOG_FILE = os.path.join(
        TMG_PROJECT_PATH,
        f"role_injection_{'dryrun' if DRY_RUN else 'real'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    
    log("Configuration:")
    log(f"  TMG Path   : {TMG_PROJECT_PATH}")
    log(f"  TMG Prefix : {TMG_PREFIX}")
    log(f"  GEDCOM     : {GEDCOM_PATH}")
    log(f"  Mapping    : {len(EVENT_MAPPING)} events, {len(ROLES_DB)} roles")
    log(f"  Mode       : {'SIMULATION' if DRY_RUN else 'REAL'}")
    log("")
    
    # Vérifier GEDCOM existe
    if not os.path.exists(GEDCOM_PATH):
        log(f"GEDCOM file not found: {GEDCOM_PATH}", "ERROR")
        return {'success': False, 'error': 'GEDCOM not found'}
    
    # Backup
    if not DRY_RUN:
        backup_path = create_backup()
        if not backup_path:
            log("Backup failed - ABORTING", "ERROR")
            return {'success': False, 'error': 'Backup failed'}
    
    try:
        # Exécution des 4 étapes
        log("Step 1/4: Scanning role usage...")
        role_usage = scan_role_usage()
        
        log("Step 2/4: Updating TMG structure...")
        evt_ids, role_codes = update_tmg_structure(role_usage)
        
        log("Step 3/4: Loading persons and events...")
        ged_to_perno, dsid, events_index, existing_witnesses = load_persons_and_events()
        
        log("Step 4/4: Injecting witnesses...")
        inject_witnesses(evt_ids, role_codes, ged_to_perno, dsid, events_index, existing_witnesses)
        
        log("")
        log("=" * 80, "SUCCESS")
        log("ROLE INJECTION COMPLETED!", "SUCCESS")
        log("=" * 80, "SUCCESS")
        log("")
        log(f"Log file: {LOG_FILE}")
        log("")
        log("⚠️ IMPORTANT: Open TMG and run File > Maintenance > Reindex", "WARNING")
        
        return {
            'success': True,
            'log_file': LOG_FILE
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        log(f"Error during injection: {e}", "ERROR")
        log(f"Full traceback:\n{error_detail}", "ERROR")
        return {'success': False, 'error': str(e), 'traceback': error_detail}
