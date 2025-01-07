# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20, 2024

@author: trstl
"""

import os
import pandas as pd
import subprocess

# Function to safely convert to upper case whether character is alphabetic or not
def safe_upper(value): 
    return value.upper() if isinstance(value, str) and value.isalpha() else value

def create_variant_id_df(df, chrom_col, pos_col, a1_col, a2_col):
    """
    Create a new variant ID column for a DataFrame.
    The format is as follows: 
        
        chr:position:a1/a2
        
        Example: 1:9000:A/G
    
    """
    a_first = df.apply(lambda row: min(safe_upper(row[a1_col]), safe_upper(row[a2_col])), axis=1)
    a_second = df.apply(lambda row: max(safe_upper(row[a1_col]), safe_upper(row[a2_col])), axis=1)

    df[chrom_col] = df[chrom_col].apply(lambda x: str(int(x)) if isinstance(x, float) and x.is_integer() else str(x).upper())

    _id_column = (df[chrom_col].astype(str) + ":" + df[pos_col].astype(int).astype(str) + ":" + a_first.astype(str) + "/" + a_second.astype(str))
    return _id_column

def process_bim_file(bim_file):
    """Process the .bim file to create new variant IDs and run PLINK commands."""
    if not os.path.exists(bim_file):
        raise FileNotFoundError(f"The file {bim_file} does not exist.")

    # Read the .bim file into a DataFrame
    df = pd.read_csv(bim_file, delim_whitespace=True, header=None, names=["chrom", "id", "cm", "pos", "a1", "a2"])

    # Create new variant IDs
    df["new_id"] = create_variant_id_df(df, chrom_col="chrom", pos_col="pos", a1_col="a1", a2_col="a2")

    # Export old and new IDs to a space-delimited file
    temp_file = "temp.txt"
    df[["id", "new_id"]].to_csv(temp_file, sep=" ", header=False, index=False)

    # Run the PLINK commands
    base_name = os.path.splitext(bim_file)[0]
    output_name = base_name + "_std"

    try:
        subprocess.run(["module", "load", "plink"], check=True)
    except subprocess.CalledProcessError:
        pass

    plink_command = [
        "plink",
        "--bfile", base_name,
        "--update-name", temp_file,
        "--make-bed",
        "--out", output_name
    ]

    try:
        subprocess.run(plink_command, check=True)
        # Remove temp.txt if the command runs without errors
        os.remove(temp_file)
        print(f"Standard ID bfiles exported to {output_name}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"PLINK command failed: {e}")

if __name__ == "__main__":
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process a .bim file to standardize variant IDs for plink bfiles.")
    parser.add_argument("bim_file", help="Path to the .bim file")

    args = parser.parse_args()

    # Process the .bim file
    process_bim_file(args.bim_file)