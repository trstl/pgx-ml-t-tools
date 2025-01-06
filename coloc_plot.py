# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 11:50:34 2025 for pgx-ml-lab

Colocalisation Plot

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


"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import argparse
import os


#%%

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

#%%
def load_dataset(file_path, chromosome, bp_lower, bp_upper):
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist. Please check the path.")
        
    def find_correct_delimiter(file_path, target_column="chromosome", delimiters=["\t", ",", "\s+"]):
        for delimiter in delimiters:
            try:
                # Attempt to read the file with the current delimiter
                sample = pd.read_csv(file_path, sep=delimiter, nrows=5)       
                # Check if the target column exists
                if target_column in sample.columns:
                    return delimiter
            except Exception as e:
                print(f"Delimiter '{delimiter}' caused an error: {e}")
        
        print(f"None of the tested delimiters matched the column '{target_column}'.")
        return None

    delimiter = find_correct_delimiter(file_path)

    filtered_rows = []
    try:
        dtypes = {'chromosome': 'str', 'base_pair_location': 'int'}
        
        # Open the file in chunks and pre-filter rows
        with pd.read_csv(file_path, sep=delimiter, dtype=dtypes, chunksize=10000) as reader:
            for chunk in reader:
                filtered_chunk = chunk[
                    (chunk['chromosome'] == chromosome) &
                    (chunk['base_pair_location'] >= bp_lower) &
                    (chunk['base_pair_location'] <= bp_upper)
                ]
                if not filtered_chunk.empty:
                    filtered_rows.append(filtered_chunk)
        
        # Combine the filtered rows into a single DataFrame
        if filtered_rows:
            df = pd.concat(filtered_rows, ignore_index=True)
        else:
            return pd.DataFrame()  # Return empty DataFrame if no matches found

    except Exception as e:
        raise RuntimeError(f"An error occurred while processing the file: {e}")

    return df


#%%
def plot_summary_statistics(df_A, df_B, chromosome, base_pair_location, symmetric=False):
    lower, upper = base_pair_location
    
    #  Add standard 'ID' column
    df_A['ID'] = create_variant_id_df(df_A, 'chromosome', 'base_pair_location', 'effect_allele', 'other_allele')
    df_A.set_index('ID', inplace=True)
    df_B['ID'] = create_variant_id_df(df_B, 'chromosome', 'base_pair_location', 'effect_allele', 'other_allele')
    df_B.set_index('ID', inplace=True)
    
    
    # Retain common only ? ####################################### (for now only correlation plot guarantees they are shared. Coloc plot could have different top variants from correlation plot)
    
    # Check if 'neg_log_10_p_value' exists, if not, calculate it
    if 'neg_log_10_p_value' not in df_A.columns:
        df_A['neg_log_10_p_value'] = -np.log10(df_A['p_value'])
    
    if 'neg_log_10_p_value' not in df_B.columns:
        df_B['neg_log_10_p_value'] = -np.log10(df_B['p_value'])
    
    # Reflect df_B y-values below the x-axis
    df_B['neg_log_10_p_value'] = df_B['neg_log_10_p_value'] * -1
    
    # Create the figure and gridspec layout
    fig = plt.figure(figsize=(9, 9))
    gs = gridspec.GridSpec(3, 2, width_ratios=[1.5, 1], height_ratios=[1, 2, 1])

    # Left scatter plot
    ax1 = plt.subplot(gs[1, 0])
    ax1.scatter(df_A['base_pair_location'], df_A['neg_log_10_p_value'], color='black', alpha=0.9, s=10)
    ax1.scatter(df_B['base_pair_location'], df_B['neg_log_10_p_value'], color='black', alpha=0.9, s=10)
    
    # Mark max value in df_A and min value in df_B
    max_df_A = df_A.loc[df_A['neg_log_10_p_value'].idxmax()]
    min_df_B = df_B.loc[df_B['neg_log_10_p_value'].idxmin()]
    
    ax1.scatter(max_df_A['base_pair_location'], max_df_A['neg_log_10_p_value'], color='orange', s=35, label=f"Top variant for dataset A ({df_A['neg_log_10_p_value'].idxmax()})")
    ax1.scatter(min_df_B['base_pair_location'], min_df_B['neg_log_10_p_value'], color='blue', s=35, label=f"Top variant for dataset B ({df_B['neg_log_10_p_value'].idxmin()})")
    
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)  # Solid line at y=0
    
    # Adjust y-axis limits based on symmetric flag
    max_y = max(abs(df_A['neg_log_10_p_value']).max(), abs(df_B['neg_log_10_p_value']).max())
    if symmetric:
        ax1.set_ylim(-max_y - 0.5, max_y + 0.5)
        y_label_pos = 0.5 # Centered
    else:
        max_A = df_A['neg_log_10_p_value'].max()
        min_B = df_B['neg_log_10_p_value'].min()
        ax1.set_ylim(min_B - 0.5, max_A + 0.5)
        # y_label position for offset due to differences in scales
        y_label_pos = 1 - max_A / (max_A - min_B)
    
    # Remove borders for aesthetics
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_visible(False)
    
    ax1.set_xlabel('Base Pair Location')
    ax1.set_ylabel('log10(p-value)     -log10(p-value) ')
    ax1.yaxis.set_label_coords(-0.1, y_label_pos)
    #ax1.set_title(f'Colocalisation plot at Chromosome {chromosome} between {lower} and {upper} bp')
    ax1.legend(loc=(0, -0.4),  fontsize=8,)
    
    
    ####################
    # Correlation plot #
    ####################
    
    ax2 = plt.subplot(gs[1, 1])
    # Merge df_A and df_B based on index
    common_indices = df_A.index.intersection(df_B.index)
    merged_df = df_A.loc[common_indices].merge(df_B.loc[common_indices], left_index=True, right_index=True, suffixes=('_A', '_B'))
    ax2.scatter(merged_df['neg_log_10_p_value_B'] * -1, merged_df['neg_log_10_p_value_A'], alpha=0.9, color='purple', s=10)  # Use reflected df_B values
  
    # Add coloured points for top variants
    max_A_index = merged_df['neg_log_10_p_value_A'].idxmax()
    ax2.scatter(merged_df.loc[max_A_index, 'neg_log_10_p_value_B'] * -1, merged_df.loc[max_A_index, 'neg_log_10_p_value_A'], color='orange', s=35)
    min_B_index = merged_df['neg_log_10_p_value_B'].idxmin()
    ax2.scatter(merged_df.loc[min_B_index, 'neg_log_10_p_value_B'] * -1, merged_df.loc[min_B_index, 'neg_log_10_p_value_A'], color='blue', s=35)
    
    
    ax2.set_xlabel('-log10(p-value) for Dataset B')
    ax2.set_ylabel('-log10(p-value) for Dataset A')
    #ax2.set_title('Correlation between Datasets A and B')
    
    ax2.set_ylim(ymin=0, ymax=max_y + 0.5)
    ax2.set_xlim(xmin=0, xmax=max_y + 0.5)
    
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # Show plot
    plt.savefig('test.png')
    plt.show()
    


#%%
def main():
    parser = argparse.ArgumentParser(description="Plot summary statistics from two datasets for colocalisation.")
    
    # Positional arguments
    parser.add_argument('df_A', type=str, help="Path to the first dataset")
    parser.add_argument('df_B', type=str, help="Path to the second dataset")
    parser.add_argument('chromosome', type=str, help="Chromosome to filter")
    parser.add_argument('lower', type=int, help="Lower bound of the base pair location")
    parser.add_argument('upper', type=int, help="Upper bound of the base pair location")
    
    # Optional argument
    parser.add_argument('--symmetric', action='store_true', help="If set, y axes for both datasets will be identical")
    
    args = parser.parse_args()
    
    # Load datasets
    df_A = load_dataset(args.df_A, args.chromosome, args.lower, args.upper)
    df_B = load_dataset(args.df_B, args.chromosome, args.lower, args.upper)
    
    # Call the plotting function
    plot_summary_statistics(df_A, df_B, args.chromosome, (args.lower, args.upper), args.symmetric)

if __name__ == '__main__':
    main()
