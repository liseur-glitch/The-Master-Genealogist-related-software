# CHANGELOG - TMG Suite

## Version 3.0 (2026-02-05) 🎉

### ✨ Nouveautés
- **Sentence Injection** : Nouveau moteur d'injection automatique de phrases
  - Traitement en masse de tous les tags custom
  - Génération bilingue (EN + FR)
  - Structure TSENTENCE optimisée (conforme aux tags natifs TMG)
  - Backup automatique complet (DBF + FPT + CDX)
  
- **Interface graphique mise à jour**
  - Bouton "▶ 3. Run Sentence Injection" (Ctrl+3)
  - Logs détaillés pour chaque opération
  - Statistiques complètes après injection

### 🔧 Architecture
- Nouveau moteur : `TMGSentenceInjectorEngine` dans `tmg_core_v3.py`
- Intégration transparente avec les moteurs existants
- Callbacks unifiés pour logs et progression

### 📝 Corrections importantes
- Structure TSENTENCE : `[LABELS:]` maintenant en premier (conforme TMG)
- Phrases groupées par langue au lieu de mélangées ligne par ligne
- Sauts de ligne Windows (`\r\n`) pour compatibilité TMG
- Encodage cp1252 (Windows-1252) forcé pour tous les accès DBF

### 🎯 Fonctionnalités techniques
- Détection automatique des phrases manquantes
- Préservation des phrases existantes (multilingue)
- Support `[L=ENGLISHUK]` pour phrases anglaises (spécificité TMG)
- Génération de templates avec placeholders TMG (`<[M]>`, `<[D]>`, `<[L]>`)

---

## Version 2.0 (2026-02-04)

### ✨ Nouveautés
- Interface graphique unifiée pour Mapping Tool + Witness Injector
- Configuration sauvegardée automatiquement
- Logs avec codes couleur
- Barre de progression en temps réel
- Exécution multi-thread (interface non bloquante)

### 🔧 Architecture
- Séparation moteur métier (`tmg_core.py`) et interface (`tmg_gui.py`)
- Classes moteur avec callbacks
- Support CLI et GUI avec même code métier

---

## Version 1.x (Historique)

### Super Injector v16 (2026-02-01)
- Injection de témoins FH → TMG
- Backup automatique avant modification
- Détection des témoins auto-référencés
- Correspondance année ±5 ans

### Mapping Tool (2026-01-30)
- Génération mapping GEDCOM → TMG
- Analyse statistique des tags
- Export JSON formaté

---

**Auteur:** Claude (Anthropic) pour Olivier  
**Dernière mise à jour:** 2026-02-05
