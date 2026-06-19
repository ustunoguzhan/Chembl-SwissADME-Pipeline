import re
import time
import requests
import pandas as pd
from io import StringIO

class SwissADMEScraper:
    """
    A robust web scraper for the SIB SwissADME tool. 
    It features:
    1. CRLF line endings formatting (mandatory for SwissADME multi-line processing).
    2. Real-time HTML JavaScript string parsing (bypassing the asynchronous empty-CSV bug).
    3. Self-healing/adaptive sub-batching (automatically isolates and skips crash-causing macrocycles).
    """
    def __init__(self, request_timeout=90, rate_limit_sleep=15):
        self.url = "https://www.swissadme.ch/index.php"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.swissadme.ch/index.php"
        }
        self.request_timeout = request_timeout
        self.rate_limit_sleep = rate_limit_sleep
        self.failed_drugs = []

    def _submit_batch_to_server(self, batch_items):
        """
        Sends a single batch list of (name, smiles) to SwissADME.
        Formats line endings with CRLF (\r\n) and returns parsed raw CSV data rows.
        """
        smiles_lines = []
        for name, smiles in batch_items:
            # Salt Stripping: Select the largest molecular fragment if multiple components exist
            clean_smiles = smiles
            if smiles and isinstance(smiles, str) and '.' in smiles:
                parts = smiles.split('.')
                clean_smiles = max(parts, key=len)
                print(f"    [Salt Stripping]: Stripped salts/solvates from '{name}' SMILES: '{smiles}' -> '{clean_smiles}'")
                
            clean_name = name.replace(" ", "_")
            smiles_lines.append(f"{clean_smiles} {clean_name}")
            
        # SwissADME specifically requires CRLF line endings to parse text areas correctly
        smiles_input = "\r\n".join(smiles_lines)
        payload = {"smiles": smiles_input}
        
        retries = 3
        while retries > 0:
            try:
                r = requests.post(self.url, data=payload, headers=self.headers, timeout=self.request_timeout)
                if r.status_code == 200:
                    # 1. Primary parsing: Look for the specific 'textForClipBoard' variable
                    matches = re.findall(r'textForClipBoard\s*=\s*textForClipBoard\s*\+\s*(.*?);', r.text, re.DOTALL)
                    
                    # 2. Robust Fallback: If variable is renamed, look for any self-concatenating variable
                    if not matches:
                        # Find all patterns of varname = varname + ...;
                        var_matches = re.findall(r'([a-zA-Z0-9_]+)\s*=\s*\1\s*\+\s*(.*?);', r.text, re.DOTALL)
                        # Filter to find the variable accumulating the CSV contents
                        for var_name, content in var_matches:
                            if "Molecule" in content or "SMILES" in content or "GI absorption" in content:
                                # Found the clipboard variable! Retrieve all its occurrences
                                matches = re.findall(rf'{var_name}\s*=\s*{var_name}\s*\+\s*(.*?);', r.text, re.DOTALL)
                                if matches:
                                    print(f"    [Scraper Alert]: Detected renamed clipboard variable: '{var_name}'")
                                    break
                                    
                    # 3. Informative error logging if all extraction methods fail
                    if not matches:
                        print("    [Scraper Error]: Failed to locate clipboard variable (e.g. 'textForClipBoard') in HTML script tags.")
                        print("    [Troubleshooting]: The SwissADME web page structure might have changed. Please verify the response script content.")
                        
                    if len(matches) > 1:
                        # Extract the comma-separated text blocks
                        batch_rows = []
                        for m in matches:
                            tokens = re.findall(r'"((?:[^"\\]|\\.)*)"', m)
                            row_text = "".join(tokens).replace(r"\n", "").replace(r"\t", "")
                            batch_rows.append(row_text)
                        
                        if len(batch_rows) > 1:
                            return batch_rows
                retries -= 1
                if retries > 0:
                    time.sleep(10)
            except Exception as e:
                print(f"    [HTTP Error]: {e}. Retrying in 10s...")
                retries -= 1
                if retries > 0:
                    time.sleep(10)
        return None

    def process_adaptive(self, batch_items, batch_id):
        """
        Processes a list of molecules. If a molecule crashes the SwissADME server, 
        it recursively splits the batch, isolates the culprit, skips it, and runs the rest.
        """
        print(f"  Adaptive run for Batch '{batch_id}' (Size: {len(batch_items)})...")
        res_rows = self._submit_batch_to_server(batch_items)
        
        if res_rows is not None and len(res_rows) > 1:
            header = res_rows[0]
            data_rows = res_rows[1:]
            
            # Verify if all submitted molecules are in the response
            returned_names = set()
            for row in data_rows:
                parts = row.split(",")
                if parts:
                    returned_names.add(parts[0].replace("_", " ").lower())
                    
            submitted_names = [item[0].lower() for item in batch_items]
            missing = [name for name in submitted_names if name not in returned_names]
            
            if not missing:
                print(f"    Success: All {len(batch_items)} processed successfully.")
                return header, data_rows
            else:
                print(f"    Warning: Partial success. Processed {len(data_rows)}/{len(batch_items)}. Missing: {missing}")
                
                # Locate the index of the first missing molecule (which caused the server-side cutoff)
                first_missing_idx = -1
                for idx, item in enumerate(batch_items):
                    if item[0].lower() in missing:
                        first_missing_idx = idx
                        break
                
                culprit = batch_items[first_missing_idx]
                print(f"    [Culprit Identified]: '{culprit[0]}' crashed the server. Skipping structure.")
                self.failed_drugs.append(culprit)
                
                # Process the remaining molecules recursively
                remaining_items = batch_items[first_missing_idx + 1:]
                if remaining_items:
                    time.sleep(self.rate_limit_sleep)
                    sub_header, sub_data = self.process_adaptive(remaining_items, f"{batch_id}_rec_{first_missing_idx}")
                    return header, data_rows + sub_data
                else:
                    return header, data_rows
        else:
            print(f"    Failed completely or returned no data.")
            if len(batch_items) == 1:
                culprit = batch_items[0]
                print(f"    [Failure]: '{culprit[0]}' failed. Skipping.")
                self.failed_drugs.append(culprit)
                return None, []
            else:
                # Split the batch in half and run both halves
                half = len(batch_items) // 2
                print(f"    Splitting batch into halves: {half} and {len(batch_items)-half}...")
                
                time.sleep(self.rate_limit_sleep)
                h1_header, h1_data = self.process_adaptive(batch_items[:half], f"{batch_id}_h1")
                
                time.sleep(self.rate_limit_sleep)
                h2_header, h2_data = self.process_adaptive(batch_items[half:], f"{batch_id}_h2")
                
                header = h1_header if h1_header else h2_header
                return header, h1_data + h2_data

    def run_pipeline(self, drug_items, batch_size=20):
        """
        Runs the full SwissADME scraping pipeline over all drug items in batches.
        """
        all_parsed_rows = []
        header_row = None
        total_items = len(drug_items)
        
        print(f"\nStarting SwissADME Scraping for {total_items} drugs in batches of {batch_size}...")
        
        for i in range(0, total_items, batch_size):
            batch = drug_items[i:i+batch_size]
            batch_idx = i // batch_size + 1
            total_batches = ((total_items - 1) // batch_size) + 1
            
            print(f"\n--- Processing Batch {batch_idx}/{total_batches} ---")
            header, data = self.process_adaptive(batch, str(batch_idx))
            
            if header:
                header_row = header
            if data:
                all_parsed_rows.extend(data)
                
            time.sleep(self.rate_limit_sleep)
            
        if not all_parsed_rows or not header_row:
            print("\nError: No results were retrieved from SwissADME.")
            return None
            
        csv_data = header_row + "\n" + "\n".join(all_parsed_rows)
        df = pd.read_csv(StringIO(csv_data))
        return df
