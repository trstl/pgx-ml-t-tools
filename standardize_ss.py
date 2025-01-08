# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 10:16:05 2025

@author: trstl

The data format for stored summary statistics follows the GWAS Catalog format
https://www.ebi.ac.uk/gwas/docs/summary-statistics-format#format

Specifically, we use a tab delimited format with the following fields
(ordered):

0. chromosome
1. base_pair_location
2. effect_allele
3. other_allele
4. effect_estimate (beta, odds_ratio, hazard_ratio)
5. std_error
6. effect_allele_frequency
7. p (can be p_value, or neg_log_10_p_value as specified in header)

This script should handle tab, comma, and space-delimited datasets automatically 
as long as the other delimiters aren't present in column names.

The output is a dataset with the standard GWAS format column names and order,
with extra columns simply moved to the end (no column loss).

command: python standardize_ss.py PATH_TO_DATASET

optional arguments: --overwrite

--overwrite: output will overwrite the input file, this is false by default and the
output file will retain the input name and have an _std prefix



"""

import pandas as pd
import argparse
import os
import sys

def find_correct_delimiter(file_path, delimiters=["\t", ",", "\s+"]):
    for delimiter in delimiters:
        try:
            # Attempt to read the file with the current delimiter
            sample = pd.read_csv(file_path, sep=delimiter, nrows=5)
            # Check if the delimiter results in multiple columns
            if len(sample.columns) > 1:
                return delimiter
        except Exception as e:
            print(f"Delimiter '{delimiter}' caused an error: {e}")
    
    sys.exit("None of the tested delimiters produced multiple columns.")
    return None

# Define a function to load a small chunk of the dataset
def load_sample(filepath):
    # Check if the file exists
    if not os.path.exists(filepath):
        sys.exit(f"The file '{filepath}' was not found. Please check the path.")
    
    delimiter = find_correct_delimiter(filepath)
    
    return pd.read_csv(filepath, sep=delimiter, engine='python', nrows=5), delimiter

# Define a function to prompt user for column identification
def prompt_user_for_columns(df):
    print("Data preview:")
    print(df.head())

    columns = {}
    column_names = df.columns.tolist()

    # Display column names with indices for selection
    print("\nSelect the appropriate column by entering its number:")
    for i, col_name in enumerate(column_names):
        print(f"{i}: {col_name}")

    def get_column(prompt):
        while True:
            try:
                col_index = int(input(prompt))
                if 0 <= col_index < len(column_names):
                    return column_names[col_index]
                else:
                    print("Invalid number. Please select a valid column number.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    # Get user inputs for required columns
    columns["chromosome"] = get_column("Chromosome column number: ")
    columns["base_pair_location"] = get_column("Base pair location column number: ")
    columns["effect_allele"] = get_column("Effect allele column number: ")
    columns["other_allele"] = get_column("Other allele column number: ")
    
    # Effect estimate column
    effect_estimate_col = get_column("Effect estimate column number (beta, odds_ratio, or hazard_ratio): ")
    print("\nSelect the type of effect estimate:")
    print("1: beta\n2: odds_ratio\n3: hazard_ratio")
    while True:
        effect_estimate_type = input("Enter the number corresponding to the effect estimate type: ")
        if effect_estimate_type in ["1", "2", "3"]:
            effect_estimate_type = {"1": "beta", "2": "odds_ratio", "3": "hazard_ratio"}[effect_estimate_type]
            break
        else:
            print("Invalid input. Please select a valid number.")
    columns["effect_estimate"] = (effect_estimate_col, effect_estimate_type)
    
    # Standard error column
    columns["std_error"] = get_column("Standard error column number: ")
    columns["effect_allele_frequency"] = get_column("Effect allele frequency column number: ")
    
    # P-value column
    p_value_col = get_column("P-value column number (p_value or neg_log_10_p_value): ")
    print("\nSelect the type of p-value column:")
    print("1: p_value\n2: neg_log_10_p_value")
    while True:
        p_value_type = input("Enter the number corresponding to the p-value type: ")
        if p_value_type in ["1", "2"]:
            p_value_type = {"1": "p_value", "2": "neg_log_10_p_value"}[p_value_type]
            break
        else:
            print("Invalid input. Please select a valid number.")
    columns["p"] = (p_value_col, p_value_type)


    return columns


# Define a function to rename and reorder columns
def process_full_dataset(filepath, columns, delimiter, overwrite=False):
    # Load the full dataset
    print('\rNow importing dataset...    ', end="")
    df = pd.read_csv(filepath, sep=delimiter, engine='python')
    print('\rImporting done.            ', end="")
    
    print('\rFormatting...            ', end="")
    # Rename columns based on user input
    rename_map = {
        columns["chromosome"]: "chromosome",
        columns["base_pair_location"]: "base_pair_location",
        columns["effect_allele"]: "effect_allele",
        columns["other_allele"]: "other_allele",
        columns["effect_estimate"][0]: columns['effect_estimate'][1],
        columns["std_error"]: "std_error",
        columns["effect_allele_frequency"]: "effect_allele_frequency",
        columns["p"][0]: columns['p'][1],
    }
    
    df.rename(columns=rename_map, inplace=True)

    # Reorder columns (required first, then extras)
    required_columns = [
        "chromosome", "base_pair_location", "effect_allele", "other_allele",
        columns['effect_estimate'][1], "std_error",
        "effect_allele_frequency", columns['p'][1]
    ]
    ordered_columns = [col for col in required_columns if col in df.columns]
    extra_columns = [col for col in df.columns if col not in ordered_columns]
    df = df[ordered_columns + extra_columns]

    # Save the processed dataset
    print('\rSaving dataset...            ', end="")
    if overwrite == True:
        output_filepath = filepath
    else:
        output_filepath = os.path.splitext(filepath)[0] + "_std.csv"
    df.to_csv(output_filepath, index=False)
    print(f"\rStandardized dataset saved to {output_filepath}         ", end="")

# Main function
def main():
    
    parser = argparse.ArgumentParser(description="Standardize a summary statistics dataset to match the recommended GWAS format (column names and order).")
    parser.add_argument("filepath", type=str, help="Path to the summary statistics dataset")
    parser.add_argument("--overwrite", action='store_true', help="If set, input file be be directly overwritten")
    args = parser.parse_args()
    
    # Load a sample of the dataset
    sample_df, delimiter = load_sample(args.filepath)

    # Prompt user for column identification
    columns = prompt_user_for_columns(sample_df)

    # Process the full dataset
    process_full_dataset(args.filepath, columns, delimiter, args.overwrite)

if __name__ == "__main__":
    main()