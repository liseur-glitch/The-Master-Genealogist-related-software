# TMG Suite v3.0

**Integrated tools for The Master Genealogist (TMG) genealogy software**

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

TMG Suite is a collection of integrated tools designed to enhance and automate workflows in The Master Genealogist (TMG), a genealogy software. It provides three main functionalities through a unified graphical interface.

## ✨ Features

### 1. **Mapping Tool**
Generates mapping between GEDCOM tags and TMG custom tags.
- Analyzes GEDCOM file structure
- Creates `mapping.json` for tag correspondence
- Statistical analysis of tag usage

### 2. **Role Injection (Witness Injector)**
Imports witnesses from Family Historian to TMG.
- Uses GEDCOM + mapping.json
- Automatic backup before modifications
- Handles self-referencing witnesses
- Year matching (±5 years tolerance)

### 3. **Sentence Injection** ✨ NEW in v3.0
Automatically generates and injects sentence structures for all custom TMG tags.
- Batch processing of all custom tags
- Bilingual support (English + French)
- TMG-compliant TSENTENCE structure
- Automatic backup (DBF + FPT + CDX)

## 📦 Installation

### Prerequisites
- Python 3.7 or higher
- The Master Genealogist v9 (or compatible version)

### Install dependencies
```bash
pip install dbf unidecode
```

*Note: `tkinter` is included with Python on Windows*

### Quick start
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/tmg-suite.git
cd tmg-suite

# Run the GUI
python tmg_gui_v3.py
```

## 🚀 Usage

### Graphical Interface

1. Launch the interface:
   ```bash
   python tmg_gui_v3.py
   ```

2. Configure paths:
   - **GEDCOM File**: Your `.ged` file (required for Mapping and Role Injection)
   - **TMG Project Folder**: Directory containing TMG database files
   - **TMG Prefix**: Prefix of your TMG files (e.g., `finaloper2` for `finaloper2_T.dbf`)

3. Run tools in sequence:
   - **▶ 1. Run Mapping Tool** → Generates `mapping.json`
   - **▶ 2. Run Role Injection** → Imports witnesses
   - **▶ 3. Run Sentence Injection** → Adds sentence structures

### Command Line

Standalone sentence injector:
```bash
python tmg_sentence_injector_v4_0_FINAL.py
```

## 📖 Documentation

- [Complete User Guide](docs/README_TMG_SUITE_v3.md)
- [Changelog](docs/CHANGELOG_v3.md)
- [Technical Architecture](docs/ARCHITECTURE.md)

## 🔧 Workflow Examples

### Full workflow (all tools)
```
GEDCOM → Mapping Tool → mapping.json
                ↓
       Role Injection → TMG Database (with witnesses)
                ↓
    Sentence Injection → TMG Database (with sentences)
                ↓
       TMG Reindex → Done!
```

### Sentence injection only
```
TMG Database → Sentence Injection → TMG Database (with sentences)
                        ↓
                  TMG Reindex → Done!
```

## ⚠️ Important Notes

### Before using
- ✅ **Always close TMG** before running injections
- ✅ Test on a **backup project** first
- ✅ Backups are created automatically in `BACKUPS/` and `BACKUPS_SENTENCES/`

### After sentence injection
- ⚠️ **Open TMG and run:** File > Maintenance > **Reindex**
- This step is **mandatory** for TMG to recognize the changes

## 🏗️ Architecture

```
tmg-suite/
├── tmg_gui_v3.py                    # Main GUI application
├── tmg_core_v3.py                   # Business logic engines
│   ├── TMGMappingEngine             # GEDCOM → TMG mapping
│   ├── TMGInjectorEngine            # Witness injection
│   └── TMGSentenceInjectorEngine    # Sentence injection (NEW)
└── tmg_sentence_injector_v4_0_FINAL.py  # Standalone CLI tool
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development setup
```bash
git clone https://github.com/YOUR_USERNAME/tmg-suite.git
cd tmg-suite
pip install -r requirements.txt
```

## 📝 Technical Details

### Sentence Structure (v3.0+)
The sentence injector generates TMG-compliant TSENTENCE structures:

```
[LABELS:]
[RL=00001][L=ENGLISH]Principal[L=FRENCH]Protagoniste
[RL=00002][L=ENGLISH]Witness[L=FRENCH]Témoin
[:LABELS]
[L=ENGLISHUK][R=00001][P] <was|and [PO] were> tag_name <[M]> <[D]> <[L]>
[L=FRENCH][R=00001][P] <était|et [PO] étaient> tag_name <[M]> <[D]> <[L]>
```

Key features:
- `[LABELS:]` section comes first (roles definition)
- Sentences grouped by language (not interleaved)
- Windows line breaks (`\r\n`)
- cp1252 encoding (Windows-1252)
- TMG placeholders: `<[M]>` (memo), `<[D]>` (date), `<[L]>` (place)

## 🐛 Troubleshooting

### Common issues

**Sentences not visible in TMG**
→ Run File > Maintenance > Reindex in TMG (mandatory step)

**"Backup failed" error**
→ Close TMG before running injection

**"tmg_core_v3.py not found"**
→ Ensure `tmg_core_v3.py` is in the same folder as `tmg_gui_v3.py`

See [Full Troubleshooting Guide](docs/README_TMG_SUITE_v3.md#-dépannage)

## 📊 Statistics Example

After sentence injection:
```
Tags custom total      : 46
Tags processed        : 28
Phrases injected      : 112
Tags skipped          : 18
Errors                : 0
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Developed with Claude (Anthropic) and ChatGpt for genealogy research
- Inspired by the TMG user community
- Based on extensive testing with real genealogical databases

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Version:** 3.0  
**Last Updated:** 2026-02-05  
**Status:** Active Development
