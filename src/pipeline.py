import os
import argparse
import pandas as pd
from chembl_helper import ChEMBLHelper
from swissadme_scraper import SwissADMEScraper

COLUMNS_GROUPING = {
    # Molecule Info
    'Molecule': ('Molecule Info', 'Molecule'),
    'Canonical SMILES': ('Molecule Info', 'Canonical SMILES'),
    'Formula': ('Molecule Info', 'Formula'),
    'ChEMBL_ID': ('Molecule Info', 'ChEMBL ID'),
    'Drug_Name': ('Molecule Info', 'Drug Name'),
    'SMILES': ('Molecule Info', 'SMILES'),
    
    # Physicochemical Properties
    'MW': ('Physicochemical Properties', 'Molecular Weight'),
    '#Heavy atoms': ('Physicochemical Properties', 'Heavy Atoms'),
    '#Aromatic heavy atoms': ('Physicochemical Properties', 'Aromatic Heavy Atoms'),
    'Fraction Csp3': ('Physicochemical Properties', 'Fraction Csp3'),
    '#Rotatable bonds': ('Physicochemical Properties', 'Rotatable Bonds'),
    '#H-bond acceptors': ('Physicochemical Properties', 'H-bond Acceptors'),
    '#H-bond donors': ('Physicochemical Properties', 'H-bond Donors'),
    'MR': ('Physicochemical Properties', 'Molar Refractivity'),
    'TPSA': ('Physicochemical Properties', 'TPSA'),
    
    # Lipophilicity
    'iLOGP': ('Lipophilicity', 'iLOGP'),
    'XLOGP3': ('Lipophilicity', 'XLOGP3'),
    'WLOGP': ('Lipophilicity', 'WLOGP'),
    'MLOGP': ('Lipophilicity', 'MLOGP'),
    'Silicos-IT Log P': ('Lipophilicity', 'Silicos-IT Log P'),
    'Consensus Log P': ('Lipophilicity', 'Consensus Log P'),
    
    # Water Solubility
    'ESOL Log S': ('Water Solubility', 'ESOL Log S'),
    'ESOL Solubility (mg/ml)': ('Water Solubility', 'ESOL Solubility (mg/ml)'),
    'ESOL Solubility (mol/l)': ('Water Solubility', 'ESOL Solubility (mol/l)'),
    'ESOL Class': ('Water Solubility', 'ESOL Class'),
    'Ali Log S': ('Water Solubility', 'Ali Log S'),
    'Ali Solubility (mg/ml)': ('Water Solubility', 'Ali Solubility (mg/ml)'),
    'Ali Solubility (mol/l)': ('Water Solubility', 'Ali Solubility (mol/l)'),
    'Ali Class': ('Water Solubility', 'Ali Class'),
    'Silicos-IT LogSw': ('Water Solubility', 'Silicos-IT LogSw'),
    'Silicos-IT Solubility (mg/ml)': ('Water Solubility', 'Silicos-IT Solubility (mg/ml)'),
    'Silicos-IT Solubility (mol/l)': ('Water Solubility', 'Silicos-IT Solubility (mol/l)'),
    'Silicos-IT class': ('Water Solubility', 'Silicos-IT Class'),
    
    # Pharmacokinetics (ADME)
    'GI absorption': ('Pharmacokinetics (ADME)', 'GI Absorption'),
    'BBB permeant': ('Pharmacokinetics (ADME)', 'BBB Permeant'),
    'Pgp substrate': ('Pharmacokinetics (ADME)', 'P-gp Substrate'),
    'CYP1A2 inhibitor': ('Pharmacokinetics (ADME)', 'CYP1A2 Inhibitor'),
    'CYP2C19 inhibitor': ('Pharmacokinetics (ADME)', 'CYP2C19 Inhibitor'),
    'CYP2C9 inhibitor': ('Pharmacokinetics (ADME)', 'CYP2C9 Inhibitor'),
    'CYP2D6 inhibitor': ('Pharmacokinetics (ADME)', 'CYP2D6 Inhibitor'),
    'CYP3A4 inhibitor': ('Pharmacokinetics (ADME)', 'CYP3A4 Inhibitor'),
    'log Kp (cm/s)': ('Pharmacokinetics (ADME)', 'Skin Permeation (log Kp)'),
    'BBB_Permeant': ('Pharmacokinetics (ADME)', 'BBB Permeant'),
    'GI_Absorption': ('Pharmacokinetics (ADME)', 'GI Absorption'),
    
    # Drug-likeness
    'Lipinski #violations': ('Drug-likeness', 'Lipinski Violations'),
    'Ghose #violations': ('Drug-likeness', 'Ghose Violations'),
    'Veber #violations': ('Drug-likeness', 'Veber Violations'),
    'Egan #violations': ('Drug-likeness', 'Egan Violations'),
    'Muegge #violations': ('Drug-likeness', 'Muegge Violations'),
    'Bioavailability Score': ('Drug-likeness', 'Bioavailability Score'),
    
    # Medicinal Chemistry
    'PAINS #alerts': ('Medicinal Chemistry', 'PAINS Alerts'),
    'Brenk #alerts': ('Medicinal Chemistry', 'Brenk Alerts'),
    'Leadlikeness #violations': ('Medicinal Chemistry', 'Lead-likeness Violations'),
    'Synthetic Accessibility': ('Medicinal Chemistry', 'Synthetic Accessibility')
}

def format_excel_grouped(df, index_col):
    """
    Groups DataFrame columns under MultiIndex headers and sets the key column as the index.
    """
    df_copy = df.copy()
    if index_col in df_copy.columns:
        df_copy.set_index(index_col, inplace=True)
    
    multi_cols = []
    for col in df_copy.columns:
        if col in COLUMNS_GROUPING:
            multi_cols.append(COLUMNS_GROUPING[col])
        else:
            multi_cols.append(('Other Info', col))
    df_copy.columns = pd.MultiIndex.from_tuples(multi_cols)
    return df_copy

def parse_args():
    parser = argparse.ArgumentParser(description="ChEMBL SMILES retrieval and SwissADME BBB Permeability Pipeline")
    parser.add_argument("--input", type=str, default="data/sample_drugs.xlsx", help="Path to input Excel file containing drug list")
    parser.add_argument("--out-dir", type=str, default="results", help="Directory path to save results")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for SwissADME queries")
    parser.add_argument("--sleep", type=int, default=15, help="Sleep time in seconds between requests")
    return parser.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found!")
        return
        
    print(f"Loading input file: {args.input}...")
    # Supports both excel and csv
    if args.input.endswith((".xlsx", ".xls")):
        df_input = pd.read_excel(args.input)
    else:
        df_input = pd.read_csv(args.input)
        
    # Ensure we have a column named 'Drug_Name'
    if "Drug_Name" not in df_input.columns:
        print("Error: Input file must contain a 'Drug_Name' column!")
        return
        
    # Step 1: Query ChEMBL for missing SMILES codes
    resolved_df = df_input.copy()
    if "SMILES" not in resolved_df.columns:
        resolved_df["SMILES"] = None
    if "ChEMBL_ID" not in resolved_df.columns:
        resolved_df["ChEMBL_ID"] = None
        
    chembl_helper = ChEMBLHelper()
    
    missing_smiles_mask = resolved_df["SMILES"].isna() | (resolved_df["SMILES"] == "") | (resolved_df["SMILES"].astype(str).str.lower() == "nan")
    missing_drugs = resolved_df.loc[missing_smiles_mask, "Drug_Name"].tolist()
    
    if missing_drugs:
        print(f"\n[Step 1]: Querying ChEMBL API for {len(missing_drugs)} missing SMILES codes...")
        chembl_res = chembl_helper.resolve_drug_list(missing_drugs)
        
        # Map back ChEMBL ID and SMILES
        for _, row in chembl_res.iterrows():
            drug_name = row["Drug_Name"]
            chembl_id = row["ChEMBL_ID"]
            smiles = row["SMILES"]
            
            idx = resolved_df[resolved_df["Drug_Name"].str.lower() == drug_name.lower()].index
            if not idx.empty:
                resolved_df.loc[idx, "ChEMBL_ID"] = chembl_id
                resolved_df.loc[idx, "SMILES"] = smiles
    else:
        print("\n[Step 1]: All drugs already have SMILES codes in input file. Skipping ChEMBL queries.")
        
    # Step 2: Prepare drug list for SwissADME
    # We only query drugs with valid SMILES
    valid_drugs = resolved_df[~resolved_df["SMILES"].isna() & (resolved_df["SMILES"].astype(str).str.lower() != "nan") & (resolved_df["SMILES"] != "Not Found")].copy()
    print(f"\n[Step 2]: Found {len(valid_drugs)} drugs with valid SMILES to query SwissADME.")
    
    if len(valid_drugs) == 0:
        print("Error: No valid SMILES codes found to test with SwissADME.")
        return
        
    drug_items = list(zip(valid_drugs["Drug_Name"], valid_drugs["SMILES"]))
    
    # Step 3: Scraping SwissADME properties
    print("\n[Step 3]: Querying SwissADME for BBB permeability...")
    scraper = SwissADMEScraper(rate_limit_sleep=args.sleep)
    predictions_df = scraper.run_pipeline(drug_items, batch_size=args.batch_size)
    
    if predictions_df is None or len(predictions_df) == 0:
        print("Error: SwissADME calculations returned no results.")
        return
        
    # Step 4: Map predictions and save outputs
    print("\n[Step 4]: Generating pipeline reports...")
    
    # Map back to original dataset (do mapping while flat to avoid KeyError)
    predictions_df['Drug_Name_Lower'] = predictions_df['Molecule'].astype(str).str.replace("_", " ").str.lower()
    bbb_mapping = dict(zip(predictions_df['Drug_Name_Lower'], predictions_df['BBB permeant']))
    gi_mapping = dict(zip(predictions_df['Drug_Name_Lower'], predictions_df['GI absorption']))
    
    resolved_df['Drug_Name_Lower'] = resolved_df['Drug_Name'].astype(str).str.lower()
    resolved_df['BBB_Permeant'] = resolved_df['Drug_Name_Lower'].map(bbb_mapping)
    resolved_df['GI_Absorption'] = resolved_df['Drug_Name_Lower'].map(gi_mapping)
    resolved_df.drop(columns=['Drug_Name_Lower'], inplace=True)
    
    # Group and Save full predictions to file (using Molecule as Excel index)
    save_pred_df = predictions_df.drop(columns=['Drug_Name_Lower']).copy()
    grouped_pred_df = format_excel_grouped(save_pred_df, 'Molecule')
    predictions_path = os.path.join(args.out_dir, "predictions_full.xlsx")
    grouped_pred_df.to_excel(predictions_path, index=True)
    print(f"  Saved full ADME predictions (grouped) to: {predictions_path}")
    
    # Filter for KBB (BBB) permeant == Yes
    filtered_bbb_df = resolved_df[resolved_df['BBB_Permeant'].astype(str).str.lower() == 'yes'].copy()
    
    # Group and Save BBB Permeant (BBB+) drugs to file (using Drug_Name as Excel index)
    grouped_bbb_df = format_excel_grouped(filtered_bbb_df, 'Drug_Name')
    bbb_path = os.path.join(args.out_dir, "predictions_bbb_permeant.xlsx")
    grouped_bbb_df.to_excel(bbb_path, index=True)
    print(f"  Saved BBB Permeant (BBB+) drugs (grouped) to: {bbb_path}")
    
    # Save failed/skipped drugs log
    if scraper.failed_drugs:
        failed_path = os.path.join(args.out_dir, "failed_molecules.txt")
        with open(failed_path, "w") as f:
            for name, smiles in scraper.failed_drugs:
                f.write(f"{name}\t{smiles}\n")
        print(f"  Logged {len(scraper.failed_drugs)} crashed/failed structures to: {failed_path}")
        
    # Final Statistics
    print(f"\n==========================================")
    print(f"PIPELINE RUN COMPLETED")
    print(f"==========================================")
    print(f"Total input drugs: {len(resolved_df)}")
    print(f"Successfully evaluated by SwissADME: {len(predictions_df)}")
    print(f"BBB Permeant (BBB+): {len(filtered_bbb_df)}")
    print(f"Failed/Skipped (crashed server): {len(scraper.failed_drugs)}")
    
if __name__ == "__main__":
    main()
