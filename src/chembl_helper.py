import requests
import pandas as pd
import time

class ChEMBLHelper:
    """
    A helper class to query the public ChEMBL API to resolve drug names/synonyms 
    to ChEMBL IDs and retrieve their canonical SMILES strings.
    """
    def __init__(self, timeout=15):
        self.base_url = "https://www.ebi.ac.uk/chembl/api/data/molecule"
        self.timeout = timeout

    def get_smiles_by_name(self, drug_name):
        """
        Query ChEMBL API for a drug name or synonym and retrieve its ChEMBL ID and SMILES.
        Returns (chembl_id, smiles) or (None, None).
        """
        clean_name = drug_name.strip().lower()
        
        # Querying ChEMBL API by pref_name
        url = f"{self.base_url}?pref_name={clean_name}&format=json"
        try:
            r = requests.get(url, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                mols = data.get('molecules', [])
                if mols:
                    # Found exact match by preferred name
                    mol = mols[0]
                    chembl_id = mol.get('molecule_chembl_id')
                    smiles = mol.get('molecule_structures', {}).get('canonical_smiles')
                    return chembl_id, smiles
        except Exception as e:
            print(f"  [ChEMBL API Warning]: Error querying preferred name for '{drug_name}': {e}")

        # If pref_name query yields no results, query by synonym
        url = f"{self.base_url}.json?molecule_synonyms__synonyms__iexact={clean_name}"
        try:
            r = requests.get(url, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                mols = data.get('molecules', [])
                if mols:
                    # Found match by synonym
                    mol = mols[0]
                    chembl_id = mol.get('molecule_chembl_id')
                    smiles = mol.get('molecule_structures', {}).get('canonical_smiles')
                    return chembl_id, smiles
        except Exception as e:
            print(f"  [ChEMBL API Warning]: Error querying synonyms for '{drug_name}': {e}")

        return None, None

    def resolve_drug_list(self, drug_names):
        """
        Takes a list of drug names and resolves them in bulk.
        Returns a pandas DataFrame with columns: [Drug_Name, ChEMBL_ID, SMILES]
        """
        results = []
        total = len(drug_names)
        print(f"\nResolving {total} drug names via ChEMBL API...")
        
        for idx, name in enumerate(drug_names):
            print(f"  [{idx+1}/{total}] Querying: '{name}'...")
            chembl_id, smiles = self.get_smiles_by_name(name)
            results.append({
                "Drug_Name": name,
                "ChEMBL_ID": chembl_id if chembl_id else "Not Found",
                "SMILES": smiles if smiles else "Not Found"
            })
            # Respectful rate limiting for public EBI API
            time.sleep(0.5)
            
        return pd.DataFrame(results)

if __name__ == "__main__":
    # Small test
    helper = ChEMBLHelper()
    test_drugs = ["Ibuprofen", "Imatinib", "NonExistentDrugXYZ"]
    df = helper.resolve_drug_list(test_drugs)
    print("\nTest Results:")
    print(df.to_string())
