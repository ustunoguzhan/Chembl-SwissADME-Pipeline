# ChEMBL-SwissADME BBB Permeability and ADME Pipeline

An open-source Python tool to automate the retrieval of canonical SMILES strings, execute automated Blood-Brain Barrier (BBB) permeability filtering, and generate hierarchical ADME prediction reports. 

This pipeline features a **self-healing, error-tolerant scraping algorithm** specifically designed to bypass SIB SwissADME web server rate limits and calculation crashes, combined with automated **salt stripping** and **MultiIndex column grouping** for structured reports.

---

## 📌 1. What Does This Repository Do? (Bu Repo Ne İşe Yarar?)

When conducting virtual screening or drug repurposing for central nervous system (CNS) diseases like Glioblastoma, evaluating a large library of compounds for blood-brain barrier permeability is crucial. However, querying public databases manually is slow, and SwissADME's bulk interface has server-side bugs and limitations.

This repository automates the entire process:
1. **Identifier Resolution:** Takes a list of drug/compound names and queries EBI's ChEMBL API to retrieve their canonical SMILES strings and ChEMBL IDs.
2. **Salt & Solvate Stripping:** Automatically parses SMILES strings and strips salts/solvates (e.g., `.HCl`, `.Na`, `.OCCO` solvates) by selecting the largest molecular component. This prevents SwissADME calculations from crashing due to multi-component SMILES.
3. **Automated Querying:** Submits molecules in batches to the SIB SwissADME web tool using formatted CRLF line endings.
4. **Adaptive Error Mitigation:** Bypasses asynchronous calculation download bugs by parsing JavaScript response scripts directly. If a large macrocycle crashes the batch, the **Adaptive Algorithm** isolates the culprit, logs it, and recursively processes the remaining healthy molecules.
5. **Grouped Reports:** Generates structured Excel spreadsheets with hierarchical column headers for easy analysis.

---

## 📥 2. Input Data Format (Girdi Verisi Nasıl Olmalı?)

The pipeline accepts both Excel (`.xlsx`, `.xls`) and CSV (`.csv`) files.

### Requirements:
* The input file **MUST** contain a column named `Drug_Name` (containing the common drug names or synonyms).
* **Optional column `SMILES`:** If a `SMILES` column is present in the input file, the pipeline will prioritize these SMILES directly and **skip** the ChEMBL API search for those entries. This is highly useful for querying custom, novel, or unpublished molecular structures.

### Example Input Table:
| Drug_Name | SMILES (Optional) |
| :--- | :--- |
| Ibuprofen | |
| Everolimus | CO[C@H]1C...OCCO |
| Paracetamol | |

---

## 📤 3. Output Data Format (Çıktı Verisi Nasıl Bir Formattta Alınacak?)

The pipeline outputs Excel (`.xlsx`) files inside the specified output directory (`results/` by default). The tables are formatted with **MultiIndex (double-level) column headers**, grouping all 40+ SwissADME parameters into logical categories:

### 1. File Structure:
* **`predictions_full.xlsx`:** The complete report containing all evaluated drugs and all ADME parameters grouped under hierarchical headers. The `Molecule` name is set as the starting index column.
* **`predictions_bbb_permeant.xlsx`:** A filtered subset containing only the compounds classified as **BBB Permeant (Yes)**, allowing immediate identification of brain-penetrating candidates. The `Drug_Name` is set as the index.
* **`failed_molecules.txt`:** A text log containing the names and SMILES of structures that crashed the SwissADME calculations (e.g., massive macrocycles).

### 2. Grouped Column Categories:
| Category Level 1 | Parameter Level 2 (Examples) |
| :--- | :--- |
| **Molecule Info** | Molecule Name (Index), Canonical SMILES, Formula, ChEMBL ID |
| **Physicochemical Properties** | Molecular Weight (MW), Heavy Atoms, Fraction Csp3, Rotatable Bonds, TPSA |
| **Lipophilicity** | iLOGP, XLOGP3, WLOGP, MLOGP, Consensus Log P |
| **Water Solubility** | Ali Log S, ESOL Log S, Solubility classes, Solubilities in mg/ml and mol/l |
| **Pharmacokinetics (ADME)** | GI Absorption, BBB Permeability, P-gp Substrate, CYP1A2/2C19/2C9/2D6/3A4 Inhibitors, Skin Permeation (log Kp) |
| **Drug-likeness** | Lipinski, Ghose, Veber, Egan, Muegge rule violations, Bioavailability Score |
| **Medicinal Chemistry** | PAINS alerts, Brenk alerts, Lead-likeness violations, Synthetic Accessibility (SA Score) |

---

## 🚀 Installation and Usage

### Prerequisites
* Python 3.9 or higher
* pandas, requests, openpyxl

### 1. Clone the repository and install requirements
```bash
git clone https://github.com/ustunoguzhan/Chembl-SwissADME-Pipeline.git
cd Chembl-SwissADME-Pipeline
pip install -r requirements.txt
```

### 2. Run the Pipeline
To test the pipeline on the sample dataset:
```bash
python src/pipeline.py --input data/sample_drugs.xlsx --out-dir results
```

### 3. Command Line Arguments
* `--input`: Path to input Excel/CSV file (default: `data/sample_drugs.xlsx`)
* `--out-dir`: Directory to save the output files (default: `results`)
* `--batch-size`: Number of molecules to query per SwissADME batch (default: `20`)
* `--sleep`: Sleep time in seconds between requests to respect rate limits (default: `15`)
