# TMG Suite v3.0

**Integrated tools for The Master Genealogist (TMG) genealogy software**

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

TMG Suite automates Family Historian → TMG imports of **witnesses** and creates **sentences for all roles** (requires previous import of FH-generated GEDCOM and creation of custom events).

**Primary source:** Family Historian GEDCOM exports  
**Potential compatibility:** Other GEDCOM sources (RootsMagic, etc.) if they include `_SHAR` witness tags and proper `REFN` references *(to be tested)*

## ⚠️ Prerequisites

### Before Using TMG Suite

#### 1. **Export GEDCOM from Family Historian with witnesses**

Preferably using GEDCOM Export File Tool, with these settings:

**Gedcom destination:**
- Standard GEDCOM release 5.5

**Character set coding:**
- ANSI

**Extra options:**
- Witness Role _SHAR: **Keep Custom Tags** ✅
- Custom attribute 1 FACT: **Custom event & Value** ✅

This generates `_SHAR` tags in the GEDCOM for witness data.

#### 2. **Import your GEDCOM into TMG**

- Use **Advanced Wizard** if you have custom events
- Import FH's GEDCOM file
- Assign new or existing tags to your custom events
- Finish the GEDCOM Import
- Check that all your events are correctly set up in TMG

*TMG Suite does NOT do this initial import - use TMG's built-in import first.*

## ✨ Features

### 1. **Mapping Tool**
Generates mapping between GEDCOM tags and TMG custom tags.
- Analyzes GEDCOM file structure
- Creates `mapping.json` for tag correspondence
- Statistical analysis of tag usage

### 2. **Role Injection (Witness Injector)**
Imports witnesses from Family Historian to TMG.
- Uses GEDCOM `_SHAR` tags + mapping.json
- Automatic backup before modifications
- Handles self-referencing witnesses
- Smart event matching by person and date

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
- Family Historian (for GEDCOM export) or compatible genealogy software

### Install dependencies
```bash
pip install dbf unidecode
```

*Note: `tkinter` is included with Python on Windows*

### Quick start
```bash
# Clone the repository
git clone https://github.com/liseur-glitch/The-Master-Genealogist-related-software.git
cd The-Master-Genealogist-related-software

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
   - **GEDCOM File**: Your `.ged` file exported from Family Historian
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

## 🔧 Complete Workflow

```
1. Family Historian
   ↓
   Export GEDCOM (ANSI, 5.5, Keep Custom Tags, _SHAR enabled)
   ↓
2. TMG Standard Import (manual)
   → Imports: Individuals, Families, Events
   → Assign tags to custom events
   ↓
   
╔═══════════════════════════════════╗
║      TMG SUITE STARTS HERE        ║
╚═══════════════════════════════════╝
   ↓
3. Mapping Tool
   → Creates mapping.json
   ↓
4. Role Injection
   → Adds witnesses to existing events
   ↓
5. Sentence Injection
   → Generates sentence structures
   ↓
6. TMG Reindex (manual)
   → File > Maintenance > Reindex
   ↓
✅ DONE!
```

## ⚠️ Important Notes

### Before using
- ✅ **Always close TMG** before running injections
- ✅ Test on a **backup project** first
- ✅ Backups are created automatically in `BACKUPS/` and `BACKUPS_SENTENCES/`
- ✅ Complete TMG's standard GEDCOM import first
- ✅ Export GEDCOM from FH with proper settings (see Prerequisites)

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

## 📝 Technical Details

### GEDCOM Requirements

**For witness import to work, your GEDCOM must contain:**
- `_SHAR` tags indicating witnesses for events
- `REFN` (reference numbers) for all individuals
- Event dates for proper matching

**Example GEDCOM structure:**
```gedcom
0 @I001@ INDI
1 NAME John /Doe/
1 REFN 123

0 @I002@ INDI  
1 NAME Jane /Smith/
1 REFN 456
1 MARR
2 DATE 1850
2 _SHAR @I001@     ← Witness reference
3 ROLE Witness     ← Witness role
```

### Event Matching Algorithm (Role Injection)

The role injector matches events between GEDCOM and TMG using:
1. **Person reference (REFN)** - Primary identifier
2. **Event type** (from mapping.json) - Event category
3. **Event year** - Exact match or ±1 year tolerance for date imprecision

*The date tolerance handles cases where dates are approximate ("about 1850"), 
calendars differ slightly, or data entry variations exist.*

### Sentence Structure (Sentence Injection)

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development setup
```bash
git clone https://github.com/liseur-glitch/The-Master-Genealogist-related-software.git
cd The-Master-Genealogist-related-software
pip install -r requirements.txt
```

## 🐛 Troubleshooting

### Common issues

**Sentences not visible in TMG**
→ Run File > Maintenance > Reindex in TMG (mandatory step)

**"Backup failed" error**
→ Close TMG before running injection

**"No witnesses found in GEDCOM"**
→ Ensure GEDCOM was exported from Family Historian with:
  - Witness Role _SHAR: Keep Custom Tags ✅
  - Standard GEDCOM 5.5
  - ANSI encoding

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

- Developed with Claude (Anthropic) for genealogy research
- Inspired by the TMG user community
- Based on extensive testing with real genealogical databases
- Designed for Family Historian → TMG workflow

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Version:** 3.0  
**Last Updated:** 2026-02-06  
**Status:** Active Development
