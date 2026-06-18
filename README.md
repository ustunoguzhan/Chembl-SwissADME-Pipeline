# ChEMBL-SwissADME BBB Permeability Pipeline

An open-source Python tool to automate the retrieval of SMILES strings and the evaluation of Blood-Brain Barrier (BBB/KBB) permeability. It takes a list of compound or drug names, queries their canonical SMILES strings from the ChEMBL API, and evaluates their BBB permeability via SIB's SwissADME web tool.

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
