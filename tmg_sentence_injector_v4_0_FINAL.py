#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TMG SENTENCE INJECTOR - VERSION 4.0
=====================================
Injecte les phrases manquantes dans les tags custom TMG
avec BACKUP AUTOMATIQUE avant toute modification

⚠️  CONFIGURATION REQUISE :
   Modifiez TMG_PATH et TMG_PREFIX ci-dessous !

🔧 VERSION 4.0 - CORRECTION MAJEURE :
   Structure TSENTENCE inversée pour correspondre aux tags natifs TMG :
   1. [LABELS:] EN PREMIER avec tous les rôles
   2. PUIS les phrases groupées par langue [L=ENGLISH]...[L=FRENCH]...
   
   Basé sur l'analyse des tags Will, Ordination (fonctionnent ✅)
   vs Notary act (structure différente)

Auteur: Claude  
Date: 2026-02-05
Version: 4.0
"""

import dbf
import os
import sys
import re
import shutil
from datetime import datetime

# =============================================================================
# ⚠️  CONFIGURATION - MODIFIEZ ICI
# =============================================================================
TMG_PATH = r"C:\Users\olivi\OneDrive\Documents\The Master Genealogist v9\Projects"
TMG_PREFIX = "finaloper2"

# =============================================================================
# BACKUP AUTOMATIQUE
# =============================================================================

def create_backup():
    """
    Crée une copie de sauvegarde COMPLÈTE (DBF + FPT + CDX)
    Style Super-Injector v16
    """
    t_dbf_path = get_tmg_file("_T")
    
    if not os.path.exists(t_dbf_path):
        print(f"❌ Fichier introuvable : {t_dbf_path}")
        return None
    
    # Dossier backup
    backup_dir = os.path.join(TMG_PATH, "BACKUPS_SENTENCES")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Fichiers à sauvegarder : DBF + FPT + CDX
    files_to_backup = [
        (f"{TMG_PREFIX}_T.dbf", f"{TMG_PREFIX}_T_BACKUP_{timestamp}.dbf"),
        (f"{TMG_PREFIX}_T.fpt", f"{TMG_PREFIX}_T_BACKUP_{timestamp}.fpt"),
        (f"{TMG_PREFIX}_T.cdx", f"{TMG_PREFIX}_T_BACKUP_{timestamp}.cdx")
    ]
    
    backup_success = False
    
    try:
        for src_file, backup_name in files_to_backup:
            src_path = os.path.join(TMG_PATH, src_file)
            
            if os.path.exists(src_path):
                backup_path = os.path.join(backup_dir, backup_name)
                shutil.copy2(src_path, backup_path)
                
                if src_file.endswith(".dbf"):
                    print(f"✅ BACKUP créé : {backup_name}")
                    backup_success = True
        
        if backup_success:
            print(f"   Dossier : {backup_dir}")
            print(f"   Fichiers : .dbf + .fpt + .cdx\n")
            return os.path.join(backup_dir, files_to_backup[0][1])
        
    except Exception as e:
        print(f"❌ Erreur backup : {e}")
    
    return None

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_tmg_file(suffix):
    """Retourne le chemin complet vers un fichier DBF TMG"""
    filename = f"{TMG_PREFIX}{suffix}.dbf"
    return os.path.join(TMG_PATH, filename)

# =============================================================================
# PARSING TSENTENCE
# =============================================================================

def parse_tsentence(tsentence_str):
    """Parse le champ tsentence pour extraire rôles et phrases"""
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
    
    # Parser [R=] phrases (AVANT [LABELS:])
    for m in regex_phrase.finditer(tsentence_str):
        rid = int(m.group(1))
        block = m.group(2)
        
        if rid not in roles_data:
            roles_data[rid] = {'role': {}, 'phrase': {}}
        
        for lm in regex_lbl.finditer(block):
            lang = lm.group(1).upper()
            text = lm.group(2).strip()
            roles_data[rid]['phrase'][lang] = text
    
    return roles_data

# =============================================================================
# GÉNÉRATION PHRASES
# =============================================================================

def generate_phrase(tag_name, role_name, is_principal=False):
    """
    Génère phrases EN et FR pour un rôle (format TMG natif)
    tag_name en texte dur, <[M]> = memo, <[D]> = date, <[L]> = lieu
    """
    tag_lower = tag_name.lower()
    role_lower = role_name.lower()
    
    # Nettoyer "Principal " du nom de rôle
    if role_lower.startswith("principal "):
        role_lower = role_lower.replace("principal ", "", 1)
    elif role_lower == "principal":
        role_lower = ""  # Principal n'a pas de rôle spécifique
    
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
    
    # Phrase française (traduction basique)
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
# REBUILD TSENTENCE
# =============================================================================

def rebuild_tsentence(roles_data):
    """
    Reconstruit tsentence en respectant le formatage STRICT de TMG
    Correction v3.3 : Utilise \r\n au lieu de \r seul
    """
    phrases_blocks = {}
    
    # 1. Organiser les phrases par langue
    for rid in sorted(roles_data.keys()):
        data = roles_data[rid]
        if data['phrase']:
            for lang, text in data['phrase'].items():
                # Convertir ENGLISH → ENGLISHUK pour TMG
                if lang == 'ENGLISH':
                    lang = 'ENGLISHUK'
                
                if lang not in phrases_blocks:
                    phrases_blocks[lang] = []
                # Ajouter la phrase avec son ID de rôle
                phrases_blocks[lang].append(f"[R={rid:05d}]{text}")
    
    # 2. Construire le bloc de phrases (Partie haute)
    final_phrases = []
    
    # S'assurer qu'au moins ENGLISHUK existe
    all_langs = set(phrases_blocks.keys())
    if 'ENGLISHUK' not in all_langs and 'ENGLISH' not in all_langs:
        all_langs.add('ENGLISHUK')
    
    for lang in sorted(list(all_langs)):
        # Flux continu de phrases pour cette langue
        final_phrases.append(f"[L={lang}]")
        if lang in phrases_blocks:
            final_phrases.append("".join(phrases_blocks[lang]))
        final_phrases.append("\r\n")  # Saut de ligne après chaque groupe linguistique
    
    # Concaténation des phrases principales
    text_part = "".join(final_phrases)
    
    # 3. Construire le bloc [LABELS:] (Partie haute maintenant)
    labels_part = "[LABELS:]\r\n"  # Début propre sans \r\n avant
    
    for rid in sorted(roles_data.keys()):
        data = roles_data[rid]
        if data['role']:
            # Saut de ligne avant chaque définition de rôle
            rl_block = f"[RL={rid:05d}]"
            for lang, text in sorted(data['role'].items()):
                rl_block += f"[L={lang}]{text}"
            labels_part += rl_block + "\r\n"  # <--- CRITIQUE : \r\n après chaque rôle
    
    labels_part += "[:LABELS]\r\n"  # Fermeture + saut de ligne avant phrases
    
    # Assemblage final : LABELS EN PREMIER, puis phrases
    return labels_part + text_part

# =============================================================================
# LISTE TAGS CUSTOM
# =============================================================================

def list_custom_tags():
    """Liste tous les tags custom"""
    t_dbf_path = get_tmg_file("_T")
    
    if not os.path.exists(t_dbf_path):
        print(f"❌ Fichier introuvable : {t_dbf_path}")
        return []
    
    custom_tags = []
    
    with dbf.Table(t_dbf_path, codepage='cp1252') as table:
        for record in table:
            rec_dict = {}
            for field_name in table.field_names:
                try:
                    rec_dict[field_name] = record[field_name]
                except:
                    rec_dict[field_name] = None
            
            origetype = rec_dict.get('ORIGETYPE')
            if origetype is None:
                origetype = rec_dict.get('origetype')
            
            if origetype == 0:
                custom_tags.append(rec_dict)
    
    return custom_tags

# =============================================================================
# AFFICHAGE TAG
# =============================================================================

def display_tag_info(tag_dict):
    """Affiche les infos d'un tag"""
    tag_name = tag_dict.get('ETYPENAME', 'Unknown').strip()
    
    print(f"\n🏷️  {tag_name}")
    print("   " + "-"*76)
    
    # Parser tsentence
    tsentence = tag_dict.get('TSENTENCE', '')
    if tsentence:
        roles_data = parse_tsentence(str(tsentence))
        
        if roles_data:
            missing = sum(1 for d in roles_data.values() if not d['phrase'])
            print(f"   Rôles : {len(roles_data)}")
            print(f"   Phrases manquantes : {missing}")
            
            # Lister rôles
            for rid, data in sorted(roles_data.items()):
                role = data['role'].get('ENGLISH', 'Unknown')
                has_phrase = '✅' if data['phrase'] else '❌'
                print(f"      {has_phrase} {role}")
        else:
            print("   ⚠️  Aucun rôle trouvé")

# =============================================================================
# INJECTION
# =============================================================================

def inject_tag(tag_dict):
    """Injecte les phrases manquantes dans un tag"""
    tag_name = tag_dict.get('ETYPENAME', 'Unknown').strip()
    etypenum = tag_dict.get('ETYPENUM')
    
    print(f"\n{'='*80}")
    print(f"INJECTION : {tag_name}")
    print('='*80)
    
    # Parser tsentence
    tsentence = str(tag_dict.get('TSENTENCE', ''))
    roles_data = parse_tsentence(tsentence)
    
    if not roles_data:
        print("❌ Aucun rôle trouvé")
        return False
    
    # Compter manquantes
    missing = sum(1 for d in roles_data.values() if not d['phrase'])
    
    print(f"Rôles : {len(roles_data)}")
    print(f"Phrases à injecter : {missing}\n")
    
    if missing == 0:
        print("✅ Toutes les phrases existent")
        return False
    
    # APERÇU des phrases qui seront injectées
    print("📝 APERÇU DES PHRASES À INJECTER :")
    print("-"*80)
    
    for rid, data in sorted(roles_data.items()):
        if not data['phrase']:
            role_name = data['role'].get('ENGLISH', 'Unknown')
            is_principal = 'principal' in role_name.lower()
            
            phrase_en, phrase_fr = generate_phrase(tag_name, role_name, is_principal)
            
            print(f"  [{rid:05d}] {role_name}")
            print(f"         EN → {phrase_en}")
            print(f"         FR → {phrase_fr}")
            print()
    
    print("-"*80)
    
    # Confirmation
    confirm = input(f"\nInjecter ces {missing} phrase(s) ? (O/n) : ").strip().lower()
    if confirm not in ['o', 'oui', 'y', 'yes', '']:
        print("❌ Annulé")
        return False
    
    # BACKUP AUTOMATIQUE
    print("\n🔄 Création backup automatique...")
    backup_path = create_backup()
    if not backup_path:
        print("❌ Backup échoué - ARRÊT")
        return False
    
    # Générer phrases
    for rid, data in roles_data.items():
        if not data['phrase']:
            role_name = data['role'].get('ENGLISH', 'Unknown')
            is_principal = 'principal' in role_name.lower()
            
            phrase_en, phrase_fr = generate_phrase(tag_name, role_name, is_principal)
            
            data['phrase']['ENGLISH'] = phrase_en
            data['phrase']['FRENCH'] = phrase_fr
    
    # Reconstruire tsentence
    new_tsentence = rebuild_tsentence(roles_data)
    
    # Écrire dans DBF
    t_dbf_path = get_tmg_file("_T")
    
    try:
        with dbf.Table(t_dbf_path, codepage='cp1252') as table:
            for record in table:
                if record['ETYPENUM'] == etypenum:
                    with record:
                        record['TSENTENCE'] = new_tsentence
                    break
        
        print(f"\n✅ {missing} phrase(s) injectée(s)")
        print(f"   Tag mis à jour : {tag_name}")
        print("\n⚠️  IMPORTANT : Ouvrez TMG et lancez")
        print("   File > Maintenance > Reindex")
        print("   pour que TMG reconnaisse les modifications !")
        return True
    
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        print(f"   Backup disponible : {backup_path}")
        return False

# =============================================================================
# MENU
# =============================================================================

def main():
    """Point d'entrée"""
    
    print("\n" + "="*80)
    print("   TMG SENTENCE INJECTOR - VERSION 4.0")
    print("="*80)
    print()
    print(f"📂 Projet : {TMG_PATH}")
    print(f"🔖 Préfixe : {TMG_PREFIX}")
    print()
    
    # Vérifier fichier
    t_dbf_path = get_tmg_file("_T")
    if not os.path.exists(t_dbf_path):
        print(f"❌ Fichier introuvable : {t_dbf_path}")
        return 1
    
    print(f"✅ Fichier trouvé : {t_dbf_path}\n")
    
    # Lister custom tags
    custom_tags = list_custom_tags()
    
    if not custom_tags:
        print("❌ Aucun tag custom trouvé")
        return 1
    
    print(f"📊 {len(custom_tags)} tag(s) custom trouvé(s)\n")
    
    # Menu
    while True:
        print("="*80)
        print("MENU")
        print("="*80)
        print("1. Lister les tags custom")
        print("2. Examiner un tag")
        print("3. Injecter phrases dans un tag")
        print("4. Quitter")
        print()
        
        choice = input("Choix (1-4) : ").strip()
        
        if choice == '1':
            print("\n📋 TAGS CUSTOM :")
            for i, tag in enumerate(custom_tags, 1):
                name = tag.get('ETYPENAME', 'Unknown').strip()
                print(f"   {i}. {name}")
        
        elif choice == '2':
            num = input(f"\nNuméro (1-{len(custom_tags)}) : ").strip()
            try:
                idx = int(num) - 1
                if 0 <= idx < len(custom_tags):
                    display_tag_info(custom_tags[idx])
            except:
                print("❌ Invalide")
        
        elif choice == '3':
            num = input(f"\nNuméro (1-{len(custom_tags)}) : ").strip()
            try:
                idx = int(num) - 1
                if 0 <= idx < len(custom_tags):
                    inject_tag(custom_tags[idx])
            except:
                print("❌ Invalide")
        
        elif choice == '4':
            print("\n👋 Au revoir !")
            break
        
        else:
            print("❌ Choix invalide")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
