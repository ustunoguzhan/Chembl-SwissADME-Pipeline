# ChEMBL-SwissADME Drug Repurposing Pipeline

An open-source Python tool to automate drug repurposing workflows. It takes a list of drug names, queries their canonical SMILES strings from the ChEMBL API, and evaluates their Blood-Brain Barrier (BBB/KBB) permeability via SIB's SwissADME web tool.

This pipeline features a **self-healing, error-tolerant scraping algorithm** specifically designed to overcome the strict structural limitations and rate-limiting bugs of the SwissADME web server.

---

## ✨ Features and Technical Highlights

### 1. The CRLF Line Ending Requirement
The SwissADME server ignores standard Unix line endings (`\n`) for multi-line textarea submissions. It specifically expects Windows format CRLF (`\r\n`) to parse the SMILES input. If LF is used, SwissADME treats the entire list as a single line, causing the query to fail. This pipeline automatically formats all multi-line inputs with `\r\n`.

### 2. Bypassing the Asynchronous CSV Generation Bug
When submitting queries in bulk, downloading the `.csv` file via the generated results URL immediately after submission yields only the header row (0 molecules) due to asynchronous calculations on the SIB backend. This pipeline solves the issue by directly parsing the HTML response. The predicted ADME properties are extracted in real-time from the JavaScript string concatenations (`textForClipBoard = textForClipBoard + ...;`) using regular expressions (Regex).

### 3. Self-Healing / Adaptive Sub-Batching (The Core Algorithm)
SwissADME calculates molecules sequentially on their server. If a batch contains a complex macrocycle or a cyclic peptide (e.g., *Sirolimus, Everolimus, Amphotericin B, Dactinomycin*), the server-side calculation crashes or times out mid-batch. This drops all subsequent molecules in the same packet.

To bypass this limit, our **Adaptive Pipeline** does the following:
*   Submits molecules in small batches (default size: 20).
*   If a batch returns fewer molecules than expected, it automatically locates the first missing molecule (the **culprit**).
*   Logs the culprit molecule as failed/skipped.
*   **Recursively submits the remaining healthy molecules in that batch** so they are not lost.
*   If a sub-batch fails completely, it dynamically splits it in half and retries.

This ensures a near-100% completion rate for healthy candidates while isolating server-crashing structures.

---

## 🚀 Installation and Usage

### Prerequisites
*   Python 3.8 or higher

### 1. Clone the repository and install requirements
```bash
git clone https://github.com/YOUR_USERNAME/Chembl-SwissADME-Pipeline.git
cd Chembl-SwissADME-Pipeline
pip install -r requirements.txt
```

### 2. Run the pipeline with the sample dataset
```bash
python src/pipeline.py --input data/sample_drugs.xlsx --out-dir results --batch-size 20 --sleep 15
```

### Options
*   `--input`: Path to input Excel or CSV file. It must contain a `Drug_Name` column. If a `SMILES` column is already present, the pipeline will skip the ChEMBL API step for those drugs.
*   `--out-dir`: Folder path to save the Excel reports.
*   `--batch-size`: Batch size for SwissADME queries (default: 20). Lower sizes reduce recursive steps if a failure occurs.
*   `--sleep`: Sleep time in seconds between batches to respect SIB SwissADME rate limits (default: 15s).

---

## 📁 Project Structure

*   `src/chembl_helper.py`: Connects to EBI ChEMBL REST API to fetch SMILES codes by preferred name or synonyms.
*   `src/swissadme_scraper.py`: Handles connection, Regex parsing of results, and the self-healing adaptive batch split logic.
*   `src/pipeline.py`: Orchestrates the entire workflow from input reading to ChEMBL querying, SwissADME scraping, filtering, and report generation.
*   `data/sample_drugs.xlsx`: A test list of 12 drugs:
    *   **BBB+ controls:** *Citalopram, Diazepam, Fluoxetine, Ibuprofen*
    *   **BBB- controls:** *Afatinib, Azacitidine, Metformin, Penicillin G*
    *   **Server crashers (isolated automatically):** *Sirolimus, Everolimus, Amphotericin B, Dactinomycin*

---

## 📊 Output Reports

The pipeline generates the following reports in your output directory:
*   `predictions_full.xlsx`: The complete set of 49 chemical, physical, and ADME properties computed by SwissADME for all successful drugs.
*   `predictions_bbb_permeant.xlsx`: A filtered list containing only the candidates that pass the blood-brain barrier (`BBB permeant == Yes`).
*   `failed_molecules.txt`: A list of names and SMILES of the massive macrocycles/compounds that failed to process (isolated by the self-healing algorithm).

---

## ⚖️ License
This project is licensed under the MIT License.
