# TMG SUITE v3.0 - Interface Graphique Intégrée
**Date:** 2026-02-05  
**Auteur:** Claude

## 🆕 NOUVEAU DANS v3.0
- **Sentence Injection** : Injection automatique de phrases dans tous les tags custom TMG
- Backup automatique (DBF + FPT + CDX)
- Structure TSENTENCE optimisée selon les tags natifs TMG
- Support multilingue (Anglais + Français)

## 📦 CONTENU DU PACKAGE

```
tmg_suite_v3.0/
├── tmg_gui_v3.py           ← Interface graphique principale
├── tmg_core_v3.py          ← Moteurs métier (3 moteurs intégrés)
├── README_v3.md            ← Ce fichier
└── CHANGELOG_v3.md         ← Historique des changements
```

## 🎯 FONCTIONNALITÉS

### 1. Mapping Tool
Génère le fichier `mapping.json` qui associe les tags GEDCOM aux tags TMG.

**Entrée :** Fichier GEDCOM  
**Sortie :** `mapping.json`

### 2. Role Injection (Witness Injector)
Injecte les témoins de Family Historian vers TMG en utilisant le mapping.

**Entrée :** GEDCOM + mapping.json + Projet TMG  
**Sortie :** Base TMG modifiée (témoins ajoutés)

### 3. Sentence Injection ✨ NOUVEAU v3.0
Génère et injecte automatiquement les phrases manquantes dans TOUS les tags custom TMG.

**Entrée :** Projet TMG  
**Sortie :** Base TMG modifiée (phrases ajoutées)

**Fonctionnalités :**
- Détection automatique des rôles sans phrases
- Génération bilingue (EN + FR)
- Structure conforme aux tags natifs TMG
- Backup automatique avant injection
- Traitement en masse de tous les tags

## 🚀 INSTALLATION

### Prérequis
- Python 3.7+
- Bibliothèques : `dbf`, `unidecode`, `tkinter`

### Installation des dépendances
```bash
pip install dbf unidecode
```

*(tkinter est inclus avec Python sur Windows)*

## 📖 UTILISATION

### Lancement
```bash
python tmg_gui_v3.py
```

### Configuration initiale
1. **GEDCOM File** : Sélectionnez votre fichier `.ged`
2. **TMG Project Folder** : Dossier contenant vos fichiers TMG (ex: `C:\...\Projects`)
3. **TMG Prefix** : Préfixe de vos fichiers TMG (ex: `finaloper2` pour `finaloper2_T.dbf`)
4. **Mapping File** : Nom du fichier de mapping (défaut : `mapping.json`)

*La configuration est sauvegardée automatiquement.*

### Workflow recommandé

#### Workflow complet (Mapping + Rôles + Phrases)
1. **▶ 1. Run Mapping Tool**
   - Génère `mapping.json` depuis votre GEDCOM
   - Durée : 1-2 minutes

2. **▶ 2. Run Role Injection**
   - Injecte les témoins dans TMG
   - Nécessite `mapping.json`
   - Durée : 2-5 minutes selon la taille

3. **▶ 3. Run Sentence Injection** ✨
   - Injecte les phrases dans tous les tags custom
   - **Ne nécessite PAS de GEDCOM**
   - Durée : quelques secondes
   - ⚠️ **IMPORTANT : Après injection, ouvrez TMG et lancez**  
     **File > Maintenance > Reindex**

#### Workflow phrases uniquement
Si vous avez déjà fait le mapping et l'injection de rôles :

1. Configurez seulement :
   - TMG Project Folder
   - TMG Prefix

2. **▶ 3. Run Sentence Injection**

3. **Ouvrez TMG > File > Maintenance > Reindex**

### Interface

#### Boutons principaux
- **▶ 1. Run Mapping Tool** (Ctrl+1)
- **▶ 2. Run Role Injection** (Ctrl+2)
- **▶ 3. Run Sentence Injection** (Ctrl+3) ✨ NOUVEAU
- **⏹ Stop** : Arrête l'opération en cours

#### Zone de logs
Affiche les opérations en temps réel avec codes couleur :
- **Bleu** : En-têtes de section
- **Noir** : Informations
- **Vert** : Succès
- **Orange** : Avertissements
- **Rouge** : Erreurs

#### Barre de progression
Indique l'avancement de l'opération en cours.

## 📁 BACKUPS

### Automatiques avant chaque injection
- **Role Injection** : `BACKUPS/` dans le dossier projet
- **Sentence Injection** : `BACKUPS_SENTENCES/` dans le dossier projet

### Fichiers sauvegardés
- `*_T.dbf` (table principale)
- `*_T.fpt` (champs memo)
- `*_T.cdx` (index)

### Format des backups
`{prefix}_T_BACKUP_YYYYMMDD_HHMMSS.{ext}`

Exemple : `finaloper2_T_BACKUP_20260205_153045.dbf`

## ⚙️ FONCTIONNEMENT TECHNIQUE

### Sentence Injection

**Structure TSENTENCE correcte :**
```
[LABELS:]
[RL=00001][L=ENGLISH]Principal[L=FRENCH]Protagoniste
[RL=00002][L=ENGLISH]Witness[L=FRENCH]Témoin
[:LABELS]
[L=ENGLISHUK][R=00001][P] <was|and [PO] were> tag_name <[M]> <[D]> <[L]>
[R=00002][W] <was|and [WO] were> witness at tag_name <[M]> <[D]> <[L]>
[L=FRENCH][R=00001][P] <était|et [PO] étaient> tag_name <[M]> <[D]> <[L]>
[R=00002][W] <était|et [WO] étaient> witness à tag_name <[M]> <[D]> <[L]>
```

**Caractéristiques :**
1. `[LABELS:]` en premier avec tous les rôles
2. Puis phrases groupées par langue (`[L=ENGLISHUK]`, `[L=FRENCH]`)
3. Sauts de ligne Windows (`\r\n`)
4. Encodage cp1252 (Windows-1252)

**Génération automatique :**
- Phrases Principal : `[P] <was|and [PO] were> role at tag <[M]> <[D]> <[L]>`
- Phrases Witness : `[W] <was|and [WO] were> role at tag <[M]> <[D]> <[L]>`
- Support des placeholders TMG : `<[M]>` (memo), `<[D]>` (date), `<[L]>` (lieu)

## 🔧 DÉPANNAGE

### Sentence Injection

**Q: Les phrases ne sont pas visibles dans TMG après injection**  
R: Lancez **File > Maintenance > Reindex** dans TMG. C'est obligatoire.

**Q: Erreur "Backup échoué"**  
R: 
- Fermez TMG avant l'injection
- Vérifiez que le dossier projet existe
- Vérifiez les permissions d'écriture

**Q: Certains tags sont ignorés**  
R: Normal. Le script ignore les tags qui ont déjà toutes leurs phrases.

**Q: Comment vérifier que l'injection a fonctionné ?**  
R: Dans TMG :
1. File > Preferences > Tag Types
2. Sélectionnez un tag custom
3. Cliquez "Sentence"
4. Vérifiez que les phrases sont présentes pour chaque rôle

**Q: Puis-je annuler une injection ?**  
R: Oui, restaurez le backup :
1. Fermez TMG
2. Copiez les fichiers `*_BACKUP_*.{dbf,fpt,cdx}` depuis `BACKUPS_SENTENCES/`
3. Renommez-les en supprimant le timestamp
4. Rouvrez TMG

### Problèmes généraux

**Q: "tmg_core_v3.py introuvable"**  
R: Placez `tmg_core_v3.py` dans le même dossier que `tmg_gui_v3.py`.

**Q: L'interface ne se lance pas**  
R: Vérifiez que tkinter est installé : `python -m tkinter`

**Q: Erreur "dbf module not found"**  
R: `pip install dbf`

## 📊 STATISTIQUES

### Sentence Injection affiche :
- **Tags custom total** : Nombre total de tags détectés
- **Tags traités** : Tags où des phrases ont été injectées
- **Phrases injectées** : Nombre total de phrases ajoutées
- **Tags ignorés** : Tags déjà complets
- **Erreurs** : Nombre d'échecs

Exemple :
```
Tags custom total      : 46
Tags traités          : 28
Phrases injectées     : 112
Tags ignorés          : 18
Erreurs               : 0
```

## 🎨 RACCOURCIS CLAVIER

- **Ctrl+1** : Run Mapping Tool
- **Ctrl+2** : Run Role Injection
- **Ctrl+3** : Run Sentence Injection ✨
- **Ctrl+L** : Clear Logs
- **Ctrl+Q** : Quit

## 📝 NOTES IMPORTANTES

### Sentence Injection
1. ⚠️ **Fermez toujours TMG avant l'injection**
2. ⚠️ **Lancez toujours File > Maintenance > Reindex après**
3. 💾 Les backups sont dans `BACKUPS_SENTENCES/`
4. 🌍 Phrases générées en anglais ET français
5. ✅ Compatible avec tous les tags custom TMG

### Limitations
- Les phrases générées sont basiques (templates génériques)
- Pour des phrases personnalisées, modifiez-les manuellement dans TMG après injection
- Ne touche pas aux tags standard TMG (seulement les custom)

## 🆘 SUPPORT

Pour toute question :
1. Consultez les logs dans l'interface
2. Vérifiez le fichier de backup
3. Testez sur un projet TMG de test d'abord

## 📜 LICENCE

Développé par Claude (Anthropic) pour Olivier
Usage personnel et professionnel autorisé

## 🔄 CHANGELOG

Voir `CHANGELOG_v3.md` pour l'historique complet des modifications.

---

**Version:** 3.0  
**Date:** 2026-02-05  
**Moteurs intégrés:** Mapping Tool + Role Injection + Sentence Injection
