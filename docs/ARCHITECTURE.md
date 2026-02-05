# Architecture Technique - TMG Suite v3.0

## 📐 Vue d'ensemble

TMG Suite utilise une architecture en couches séparant interface et logique métier.

```
┌─────────────────────────────────────────┐
│         tmg_gui_v3.py (GUI)            │
│   - Interface Tkinter                   │
│   - Gestion événements                  │
│   - Logs visuels                        │
└──────────────┬──────────────────────────┘
               │ Callbacks
               ↓
┌─────────────────────────────────────────┐
│       tmg_core_v3.py (Engines)         │
│   - TMGMappingEngine                    │
│   - TMGInjectorEngine                   │
│   - TMGSentenceInjectorEngine          │
└──────────────┬──────────────────────────┘
               │ DBF Access
               ↓
┌─────────────────────────────────────────┐
│        TMG Database (FoxPro)           │
│   - *.dbf (tables)                      │
│   - *.fpt (memo fields)                 │
│   - *.cdx (indexes)                     │
└─────────────────────────────────────────┘
```

---

## 🧩 Composants

### 1. Interface Graphique (`tmg_gui_v3.py`)

**Responsabilités :**
- Affichage de l'interface Tkinter
- Gestion des événements utilisateur
- Configuration et sauvegarde des préférences
- Threads pour opérations longues
- Affichage des logs avec couleurs

**Classes principales :**
- `TMGSuiteGUI` : Fenêtre principale
  - `create_widgets()` : Construction de l'interface
  - `run_mapping_tool()` : Lance mapping
  - `run_injection()` : Lance injection rôles
  - `run_sentence_injection()` : Lance injection phrases
  - `append_log()` : Affiche messages
  - `update_progress()` : Met à jour barre

**Threading :**
```python
# Évite de bloquer l'interface
thread = threading.Thread(target=self._run_xxx_thread, daemon=True)
thread.start()
```

---

### 2. Moteurs Métier (`tmg_core_v3.py`)

#### A. Classe de base : `TMGEngineBase`

**Méthodes communes :**
- `set_log_callback(callback)` : Enregistre fonction de log
- `set_progress_callback(callback)` : Enregistre fonction progression
- `log(message, level)` : Envoie log via callback
- `progress(current, total, message)` : Envoie progression

**Pattern callbacks :**
```python
# Dans le moteur
self.log("Starting operation", 'INFO')

# Callback dans GUI
def append_log(self, message, level='INFO'):
    # Affiche dans interface
    self.log_text.insert(tk.END, message + '\n', level)
```

#### B. `TMGMappingEngine`

**Fonction :** Génère mapping GEDCOM → TMG

**Méthodes principales :**
- `parse_gedcom()` : Parse fichier GEDCOM
- `generate_mapping()` : Crée mapping.json
- `analyze_statistics()` : Stats sur les tags

**Sortie :**
```json
{
  "Birth": "Birth",
  "Death": "Death",
  "Marriage": "Marriage",
  "MyEvent": "notary act"
}
```

#### C. `TMGInjectorEngine`

**Fonction :** Injecte témoins FH → TMG

**Méthodes principales :**
- `parse_gedcom()` : Extrait témoins du GEDCOM
- `inject_witnesses(dry_run)` : Injecte dans TMG
- `create_backup()` : Sauvegarde DBF

**Processus :**
1. Parse GEDCOM (témoins dans `_WITN`)
2. Charge mapping.json
3. Pour chaque témoin :
   - Trouve personne TMG (via REFN)
   - Trouve événement (via année ±5)
   - Crée enregistrement dans E.DBF
4. Backup automatique

#### D. `TMGSentenceInjectorEngine` ✨ NOUVEAU

**Fonction :** Génère phrases pour tags custom

**Méthodes principales :**
- `get_custom_tags()` : Liste tags custom (ORIGETYPE=0)
- `parse_tsentence(tsentence)` : Parse structure existante
- `generate_phrase(tag, role, principal)` : Génère phrase EN+FR
- `rebuild_tsentence(roles_data)` : Reconstruit structure complète
- `inject_tag(tag, etypenum, roles_data)` : Injection dans DBF
- `inject_all_tags()` : Traitement en masse

**Processus :**
```
1. Lire T.DBF
2. Pour chaque tag custom :
   a. Parser TSENTENCE existant
   b. Identifier rôles sans phrase
   c. Générer phrase EN : [P] <was|and [PO] were> role at tag <[M]> <[D]> <[L]>
   d. Générer phrase FR : [P] <était|et [PO] étaient> role à tag <[M]> <[D]> <[L]>
   e. Reconstruire TSENTENCE complet
   f. Écrire dans T.DBF
3. Backup (DBF+FPT+CDX)
```

---

## 💾 Format TMG Database

### Structure des fichiers

**T.DBF (Tag Types)**
```
ETYPENUM    : ID unique du tag
ORIGETYPE   : 0=custom, >0=standard
ETYPENAME   : Nom du tag
TSENTENCE   : Structure phrases (MEMO)
```

**E.DBF (Events)**
```
ETYPE       : Référence vers T.ETYPENUM
PER1, PER2  : Principals
EDATE       : Date événement
PLACENUM    : Lieu
```

**TSENTENCE Structure (MEMO field):**
```
[LABELS:]
[RL=00001][L=ENGLISH]Principal[L=FRENCH]Protagoniste
[RL=00002][L=ENGLISH]Witness[L=FRENCH]Témoin
[:LABELS]
[L=ENGLISHUK][R=00001][P] phrase_en_principal
[R=00002][W] phrase_en_witness
[L=FRENCH][R=00001][P] phrase_fr_principal
[R=00002][W] phrase_fr_witness
```

**Particularités :**
- `\r\n` : Sauts de ligne Windows obligatoires
- `cp1252` : Encodage Windows-1252
- `[L=ENGLISHUK]` : Pas juste `ENGLISH` pour phrases
- Phrases **groupées par langue**, pas mélangées

---

## 🔄 Flux de données

### Sentence Injection détaillé

```
┌──────────────────┐
│  T.DBF (input)   │
│  Read custom tags│
└────────┬─────────┘
         │
         ↓
┌──────────────────────┐
│  Parse TSENTENCE     │
│  Extract roles_data  │
│  {role_id: {         │
│    'role': {...},    │
│    'phrase': {...}   │
│  }}                  │
└────────┬─────────────┘
         │
         ↓
┌──────────────────────┐
│  Generate missing    │
│  phrases (EN + FR)   │
│  Using templates     │
└────────┬─────────────┘
         │
         ↓
┌──────────────────────┐
│  Rebuild TSENTENCE   │
│  [LABELS:] first     │
│  Then phrases by lang│
└────────┬─────────────┘
         │
         ↓
┌──────────────────────┐
│  Write to T.DBF      │
│  cp1252 encoding     │
│  Update TSENTENCE    │
└──────────────────────┘
```

---

## 🧪 Tests et Validation

### Validation TSENTENCE

**Critères :**
```python
# Structure doit commencer par [LABELS:]
assert tsentence.startswith('[LABELS:]')

# Contenir [:LABELS] de fermeture
assert '[:LABELS]' in tsentence

# Avoir des phrases groupées par langue
assert '[L=ENGLISHUK]' in tsentence or '[L=ENGLISH]' in tsentence

# Avoir des sauts de ligne \r\n
assert '\r\n' in tsentence
```

### Tests recommandés

1. **Test unitaire** : `parse_tsentence()` sur exemples connus
2. **Test intégration** : Injection sur projet test TMG
3. **Test validation** : Vérifier dans TMG que phrases visibles

---

## ⚡ Performance

### Optimisations

**Sentence Injection :**
- Batch processing : ~50 tags en quelques secondes
- Pas de réindexation pendant injection (seulement à la fin)
- Backup incrémental (seulement si modifié)

**Mémoire :**
- Parse TSENTENCE à la volée (pas de cache global)
- Fermeture DBF après chaque opération
- Pas de chargement complet de la base

---

## 🔒 Sécurité

### Backups

**Avant chaque injection :**
```
BACKUPS_SENTENCES/
├── finaloper2_T_BACKUP_20260205_153045.dbf
├── finaloper2_T_BACKUP_20260205_153045.fpt
└── finaloper2_T_BACKUP_20260205_153045.cdx
```

**Restauration :**
```bash
# Fermer TMG
copy BACKUPS_SENTENCES\*_BACKUP_*.dbf finaloper2_T.dbf
copy BACKUPS_SENTENCES\*_BACKUP_*.fpt finaloper2_T.fpt
copy BACKUPS_SENTENCES\*_BACKUP_*.cdx finaloper2_T.cdx
# Rouvrir TMG
```

### Validation

**Checks avant écriture :**
- Fichier existe
- Permissions écriture
- TMG fermé (via try/except sur ouverture exclusive)

---

## 🐛 Debugging

### Logs niveaux

- `INFO` : Opérations normales
- `SUCCESS` : Opération réussie
- `WARNING` : Avertissement non bloquant
- `ERROR` : Erreur bloquante
- `HEADER` : Séparateurs de section

### Traces

**Activer verbose :**
```python
engine.set_log_callback(lambda msg, lvl: print(f"[{lvl}] {msg}"))
```

**Inspecter TSENTENCE :**
```python
with dbf.Table(path, codepage='cp1252') as table:
    for record in table:
        if record['ETYPENAME'] == 'MyTag':
            print(repr(record['TSENTENCE']))  # Voir \r\n
```

---

## 🚀 Évolutions futures

### v4.0 (idées)

- [ ] Support d'autres langues (DE, NL, ES)
- [ ] Templates de phrases personnalisables
- [ ] Export/Import de configurations
- [ ] Mode CLI complet (sans GUI)
- [ ] Tests unitaires automatisés
- [ ] Support de TMG v8.x
- [ ] Intégration directe avec Family Historian

---

**Version:** 3.0  
**Dernière mise à jour:** 2026-02-05
