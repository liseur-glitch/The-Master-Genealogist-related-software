# 📘 GUIDE COMPLET - PUBLICATION SUR GITHUB

## 🎯 Objectif
Publier TMG Suite v3.0 sur GitHub avec structure professionnelle.

---

## 📋 ÉTAPE 1 : Créer le repository sur GitHub.com

1. Allez sur **https://github.com**
2. Connectez-vous
3. Cliquez **"+"** (en haut à droite) → **"New repository"**

**Configuration :**
- **Repository name:** `tmg-suite`
- **Description:** `Integrated tools for The Master Genealogist (TMG) genealogy software`
- **Public** ✅ (ou Private si vous préférez)
- **Initialize this repository with:**
  - ✅ **Add a README file** (on va le remplacer)
  - ✅ **Add .gitignore** : choisir **Python**
  - ✅ **Choose a license** : choisir **MIT License**

4. Cliquez **"Create repository"**

---

## 📁 ÉTAPE 2 : Préparer la structure locale

### A. Créer le dossier

```bash
mkdir C:\GitHub\tmg-suite
cd C:\GitHub\tmg-suite
```

### B. Structure recommandée

```
tmg-suite/
├── README.md                              ← Description principale
├── LICENSE                                ← Licence MIT
├── .gitignore                             ← Fichiers à ignorer
├── requirements.txt                       ← Dépendances Python
│
├── tmg_gui_v3.py                         ← Interface graphique
├── tmg_core_v3.py                        ← Moteurs métier
├── tmg_sentence_injector_v4_0_FINAL.py  ← Script CLI standalone
│
├── docs/
│   ├── README_TMG_SUITE_v3.md           ← Documentation complète
│   ├── CHANGELOG_v3.md                   ← Historique versions
│   ├── ARCHITECTURE.md                   ← Architecture technique
│   └── SCREENSHOTS/                      ← Captures d'écran
│       ├── gui_main.png
│       ├── gui_injection.png
│       └── tmg_sentence_structure.png
│
├── examples/
│   ├── mapping.json.example              ← Exemple de mapping
│   └── config.json.example               ← Exemple config
│
└── tests/                                 ← (Optionnel) Tests unitaires
    └── test_core.py
```

---

## ⬇️ ÉTAPE 3 : Cloner le repository

```bash
cd C:\GitHub
git clone https://github.com/VOTRE_USERNAME/tmg-suite.git
cd tmg-suite
```

**Remplacez `VOTRE_USERNAME` par votre nom d'utilisateur GitHub.**

---

## 📦 ÉTAPE 4 : Ajouter vos fichiers

### A. Copier les fichiers

Depuis le dossier où vous avez téléchargé les fichiers :

```bash
# Fichiers principaux
copy tmg_gui_v3.py C:\GitHub\tmg-suite\
copy tmg_core_v3.py C:\GitHub\tmg-suite\
copy tmg_sentence_injector_v4_0_FINAL.py C:\GitHub\tmg-suite\

# Documentation
mkdir C:\GitHub\tmg-suite\docs
copy README_TMG_SUITE_v3.md C:\GitHub\tmg-suite\docs\
copy CHANGELOG_v3.md C:\GitHub\tmg-suite\docs\

# Fichiers GitHub générés
copy README_GITHUB.md C:\GitHub\tmg-suite\README.md
copy LICENSE C:\GitHub\tmg-suite\
copy .gitignore C:\GitHub\tmg-suite\
copy requirements.txt C:\GitHub\tmg-suite\
```

### B. Créer exemples (optionnel)

```bash
mkdir C:\GitHub\tmg-suite\examples
```

Créez `examples/mapping.json.example` :
```json
{
  "Birth": "Birth",
  "Death": "Death",
  "Marriage": "Marriage",
  "MyCustomEvent": "notary act"
}
```

---

## 🚀 ÉTAPE 5 : Premier commit

```bash
cd C:\GitHub\tmg-suite

# Vérifier les fichiers
git status

# Ajouter tous les fichiers
git add .

# Créer le commit
git commit -m "Initial commit - TMG Suite v3.0

- Integrated GUI for Mapping, Role Injection, and Sentence Injection
- TMG-compliant sentence structure generation
- Bilingual support (EN/FR)
- Automatic backup system
- Complete documentation"

# Pousser vers GitHub
git push origin main
```

*(Si vous avez une erreur "main" vs "master", utilisez `git push origin master`)*

---

## ✅ ÉTAPE 6 : Vérifier sur GitHub

1. Allez sur **https://github.com/VOTRE_USERNAME/tmg-suite**
2. Vérifiez que tous les fichiers sont présents
3. Vérifiez que le README.md s'affiche correctement

---

## 🎨 ÉTAPE 7 : Améliorer le repository (optionnel)

### A. Ajouter des topics (tags)

Sur GitHub, cliquez ⚙️ à côté de "About" :
- `genealogy`
- `tmg`
- `python`
- `database-tools`
- `automation`

### B. Ajouter une description

Dans "About" :
- Description : `Integrated tools for The Master Genealogist (TMG)`
- Website : `https://github.com/VOTRE_USERNAME/tmg-suite`

### C. Créer une Release

1. Onglet **"Releases"** → **"Create a new release"**
2. **Tag version:** `v3.0.0`
3. **Release title:** `TMG Suite v3.0 - Sentence Injection`
4. **Description:**
```markdown
## 🎉 TMG Suite v3.0

### ✨ New Features
- Sentence Injection: Automatic sentence structure generation for all custom tags
- Bilingual support (English + French)
- TMG-compliant TSENTENCE structure

### 📦 Files
- `tmg_gui_v3.py` - Main GUI application
- `tmg_core_v3.py` - Business logic engines
- Complete documentation in `docs/`

### 🚀 Installation
```bash
pip install -r requirements.txt
python tmg_gui_v3.py
```

### ⚠️ Important
After sentence injection, always run File > Maintenance > Reindex in TMG.
```

5. **Attach files** : Vous pouvez joindre le ZIP
6. Cliquez **"Publish release"**

---

## 🔄 ÉTAPE 8 : Workflow pour futures mises à jour

### Modifier et pousser

```bash
cd C:\GitHub\tmg-suite

# Éditer vos fichiers...

# Voir les changements
git status
git diff

# Ajouter et commiter
git add .
git commit -m "Description courte des changements"
git push
```

### Créer une branche pour développement

```bash
# Créer et switcher vers branche dev
git checkout -b develop

# Faire vos modifications...
git add .
git commit -m "Work in progress"
git push -u origin develop

# Quand c'est prêt, merger dans main
git checkout main
git merge develop
git push
```

---

## 📸 ÉTAPE 9 : Ajouter des screenshots (recommandé)

1. Créer `docs/SCREENSHOTS/`
2. Prendre captures d'écran :
   - Interface principale
   - Logs d'injection
   - Exemple TMG avec phrases
3. Les ajouter au repository
4. Les référencer dans README.md :

```markdown
## 📸 Screenshots

### Main Interface
![TMG Suite GUI](docs/SCREENSHOTS/gui_main.png)

### Sentence Injection
![Injection Progress](docs/SCREENSHOTS/gui_injection.png)
```

---

## 🎓 COMMANDES GIT ESSENTIELLES

```bash
# Statut
git status                    # Voir les modifications

# Historique
git log --oneline            # Historique simplifié
git log --graph --all        # Historique graphique

# Annuler des changements
git checkout -- fichier.py   # Annuler modifs d'un fichier
git reset HEAD fichier.py    # Retirer du staging

# Branches
git branch                   # Lister branches
git branch nom_branche       # Créer branche
git checkout nom_branche     # Changer de branche
git branch -d nom_branche    # Supprimer branche

# Remote
git remote -v               # Voir les remotes
git pull                    # Récupérer changements
git push                    # Pousser changements

# Tags
git tag v3.0.1              # Créer tag
git push --tags             # Pousser tags
```

---

## ✅ CHECKLIST FINALE

Avant de rendre le repository public :

- [ ] README.md clair et complet
- [ ] LICENSE présente (MIT)
- [ ] .gitignore configuré
- [ ] requirements.txt à jour
- [ ] Documentation dans docs/
- [ ] Exemples dans examples/
- [ ] Pas de fichiers sensibles (passwords, DBF)
- [ ] Pas de chemins personnels dans le code
- [ ] Code commenté et lisible
- [ ] Version tag créée (v3.0.0)

---

## 🎉 FÉLICITATIONS !

Votre projet est maintenant sur GitHub !

**URL :** `https://github.com/VOTRE_USERNAME/tmg-suite`

**Partagez-le :**
- Sur des forums généalogiques
- Sur Twitter/X avec #genealogy #TMG
- Sur des groupes Facebook de généalogie

---

## 📧 SUPPORT

Si vous avez des questions :
1. Vérifiez la documentation
2. Cherchez dans les Issues GitHub
3. Ouvrez une nouvelle Issue si nécessaire

**Bon courage ! 🚀**
