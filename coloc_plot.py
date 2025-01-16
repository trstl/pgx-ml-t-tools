# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 11:50:34 2025 for pgx-ml-lab

Colocalization Plot

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
import sys

from matplotlib.ticker import MaxNLocator, FuncFormatter, ScalarFormatter


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
        sys.exit(f"The file '{file_path}' was not found. Please check the path.")
        
    # Function to check which tested delimiter correctly produces a 'chromosome' column
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
        
        sys.exit(f"None of the tested delimiters matched the column '{target_column}', or required column '{target_column}' does not exist.")
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
def plot_summary_statistics(df_A, df_B, chromosome, lower, upper, x_lines, y_lines, threshold, symmetric=False, filename=None):
    
    #  Add standard 'ID' column
    df_A['ID'] = create_variant_id_df(df_A, 'chromosome', 'base_pair_location', 'effect_allele', 'other_allele')
    df_A.set_index('ID', inplace=True)
    df_B['ID'] = create_variant_id_df(df_B, 'chromosome', 'base_pair_location', 'effect_allele', 'other_allele')
    df_B.set_index('ID', inplace=True)
    
    
    # Check if 'neg_log_10_p_value' exists, if not, calculate it
    if 'neg_log_10_p_value' not in df_A.columns:
        df_A['neg_log_10_p_value'] = -np.log10(df_A['p_value'])
    
    if 'neg_log_10_p_value' not in df_B.columns:
        df_B['neg_log_10_p_value'] = -np.log10(df_B['p_value'])
    
    # Reflect df_B y-values below the x-axis
    df_B['neg_log_10_p_value'] = df_B['neg_log_10_p_value'] * -1
    
    
    # Retain common variants only
    # Merge df_A and df_B based on index
    common_indices = df_A.index.intersection(df_B.index)
    merged_df = df_A.loc[common_indices].merge(df_B.loc[common_indices], left_index=True, right_index=True, suffixes=('_A', '_B'))
    
    print(f"Dataset A has {len(df_A)} variants.")
    df_A = df_A[df_A.index.isin(common_indices)]
    print(f"{len(df_A)} of these variants are also found in Dataset B.")
    print(f"Dataset B has {len(df_B)} variants.")
    df_B = df_B[df_B.index.isin(common_indices)]
    print(f"{len(df_B)} of these variants are also found in Dataset A.")
    
    # TEMP LINES TO WORK WITH AUTO EQTLGEN ***********************************************
    #df_B['beta'] = df_B['Zscore'].apply(lambda x: 1 if  x > 0 else -1)
    
    
    # Create the figure and gridspec layout
    fig = plt.figure(figsize=(9, 9))
    gs = gridspec.GridSpec(3, 2, width_ratios=[1.5, 1], height_ratios=[1, 2, 1], wspace=0.5)
    
    
    # Left scatter plot
    ax1 = plt.subplot(gs[1, 0])
    axB = ax1.twinx()
    if threshold != None:
        # Create a color list based on the condition
        colors = ['red' if df_B.loc[idx, 'neg_log_10_p_value'] <= threshold * -1 else 'black' for idx in df_A.index]
        ax1.scatter(df_A['base_pair_location'], df_A['neg_log_10_p_value'], color=colors, s=1)
        colors = ['red' if df_A.loc[idx, 'neg_log_10_p_value'] >= threshold else 'black' for idx in df_B.index]
        axB.scatter(df_B['base_pair_location'], df_B['neg_log_10_p_value'], color=colors, s=1)
    else:
        ax1.scatter(df_A['base_pair_location'], df_A['neg_log_10_p_value'], color='black', s=1)
        axB.scatter(df_B['base_pair_location'], df_B['neg_log_10_p_value'], color='black', s=1)
    
    # Mark max value in df_A and min value in df_B
    max_df_A = df_A.loc[df_A['neg_log_10_p_value'].idxmax()]
    min_df_B = df_B.loc[df_B['neg_log_10_p_value'].idxmin()]
    
    
    marker = '^' if max_df_A['beta'] > 0 else ('v' if max_df_A['beta'] < 0 else 'o') # Check if beta is positive or negative for the specific point
    ax1.scatter(max_df_A['base_pair_location'], max_df_A['neg_log_10_p_value'], color='orange', s=35, alpha=0.8, marker=marker)
    marker = '^' if min_df_B['beta'] > 0 else ('v' if min_df_B['beta'] < 0 else 'o') # Check if beta is positive or negative for the specific point
    axB.scatter(min_df_B['base_pair_location'], min_df_B['neg_log_10_p_value'], color='blue', s=35, alpha=0.7, marker=marker)
    
    # Mark max value in df_A and min value in df_B in the other dataset's plot for comparison
    max_df_A = df_A.loc[df_B['neg_log_10_p_value'].idxmin()]
    min_df_B = df_B.loc[df_A['neg_log_10_p_value'].idxmax()]
    
    marker = '^' if max_df_A['beta'] > 0 else ('v' if max_df_A['beta'] < 0 else 'o') # Check if beta is positive or negative for the specific point
    ax1.scatter(max_df_A['base_pair_location'], max_df_A['neg_log_10_p_value'], color='blue', s=35, alpha=0.7, marker=marker)
    marker = '^' if min_df_B['beta'] > 0 else ('v' if min_df_B['beta'] < 0 else 'o') # Check if beta is positive or negative for the specific point
    axB.scatter(min_df_B['base_pair_location'], min_df_B['neg_log_10_p_value'], color='orange', s=35, alpha=0.8, marker=marker)
    
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)  # Solid line at y=0
    
    
    # Adjust y-axis limits based on symmetric flag
    # Calculate maximum positive and minimum negative values
    max_A = df_A['neg_log_10_p_value'].max()  # Maximum positive value
    min_B = df_B['neg_log_10_p_value'].min()  # Minimum negative value
    max_y = max(abs(max_A), abs(min_B))
    if symmetric:
        ax1.set_ylim(-max_y * 1.1, max_y * 1.1)
        ax1.set_yticks(np.round(np.linspace(0, max_y, 5), 1)) # 5 ticks
        axB.set_ylim(-max_y * 1.1, max_y * 1.1)
        axB.set_yticks(np.round(np.linspace(max_y, 0, 5), 1))
    else:

        ax1.set_ylim(-max_A * 1.1, max_A * 1.1)
        ax1.set_yticks(np.round(np.linspace(0, max_A, 5), 1))
        axB.set_ylim(min_B * 1.1, -min_B * 1.1)
        axB.set_yticks(np.round(np.linspace(min_B, 0, 5), 1))
        

    ax1.tick_params(axis='y', labelsize=8)
    axB.tick_params(axis='y', labelsize=8)
    
    # Remove borders for aesthetics
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_visible(False)
    axB.spines['top'].set_visible(False)
    axB.spines['bottom'].set_visible(False)
    
    ax1.set_xlabel('Base Pair Location')
    ax1.set_ylabel(r"$-\log_{10}(p)$")
    axB.set_ylabel(r"$\log_{10}(p)$", rotation=90)
    
    
    # Generate tick positions within the range
    ax1.set_xlim(lower, upper)
    
    # Use MaxNLocator to set 5 ticks
    ax1.xaxis.set_major_locator(MaxNLocator(nbins=7))
    ax1.tick_params(axis='x', labelsize=8)
    ax1.xaxis.set_major_formatter(ScalarFormatter())
    
    # Draw lines defined in arguments
    if x_lines != None:
        for bp_value in x_lines:
            ax1.axvline(x=bp_value, color='black', linestyle='--', linewidth=0.5)
    if y_lines != None:
        for neg_log10_p_value in y_lines:
            if neg_log10_p_value < 0:
                axB.axhline(y=neg_log10_p_value, color='black', linestyle='--', linewidth=0.5)
            else:
                ax1.axhline(y=neg_log10_p_value, color='black', linestyle='--', linewidth=0.5)
            
    
    
    ####################
    # Correlation plot #
    ####################
    
    ax2 = plt.subplot(gs[1, 1])
    
    ax2.scatter(merged_df['neg_log_10_p_value_B'] * -1, merged_df['neg_log_10_p_value_A'], alpha=0.4, color='purple', s=5)  # Use reflected df_B values
  
    # Add coloured points for top variants
    max_A_index = merged_df['neg_log_10_p_value_A'].idxmax()
    ax2.scatter(merged_df.loc[max_A_index, 'neg_log_10_p_value_B'] * -1, merged_df.loc[max_A_index, 'neg_log_10_p_value_A'], color='orange', s=35, alpha=0.8, label=f"Top variant for dataset A ({df_A['neg_log_10_p_value'].idxmax()})")
    min_B_index = merged_df['neg_log_10_p_value_B'].idxmin()
    ax2.scatter(merged_df.loc[min_B_index, 'neg_log_10_p_value_B'] * -1, merged_df.loc[min_B_index, 'neg_log_10_p_value_A'], color='blue', s=35, alpha=0.7, label=f"Top variant for dataset B ({df_B['neg_log_10_p_value'].idxmin()})")
    
    
    ax2.set_xlabel(r"$-\log_{10}(p)$ for Dataset B")
    ax2.set_ylabel(r"$-\log_{10}(p)$ for Dataset A")
    #ax2.set_title('Correlation between Datasets A and B')
    
    ax2.set_ylim(ymin=0, ymax=max_y + 0.5)
    ax2.set_xlim(xmin=0, xmax=max_y + 0.5)
    
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    ax2.legend(loc=(0, -0.4),  fontsize=8)
    
    
    # Save the plot as an SVG file
    if filename != None:
        output_file = f'plots/{filename}.svg'
    else:
        output_file = 'plots/coloc_plot.svg'
    plt.savefig(output_file, format='svg')
    print(f"Plot has been saved as an SVG file: {output_file} in subfolder plots/")
    


#%%
def main():
    parser = argparse.ArgumentParser(description="Plot summary statistics from two datasets for colocalization.")
    
    # Positional arguments
    parser.add_argument('df_A', type=str, help="Path to the first dataset")
    parser.add_argument('df_B', type=str, help="Path to the second dataset")
    parser.add_argument('chromosome', type=str, help="Chromosome to filter")
    parser.add_argument('lower', type=int, help="Lower bound of the base pair location")
    parser.add_argument('upper', type=int, help="Upper bound of the base pair location")
    
    # Optional arguments
    parser.add_argument('--x_line', nargs='+', type=int, help="Optional list of dashed vertical lines to draw (i.e., gene boundries), separated by spaces at given base pair values")
    parser.add_argument('--y_line', nargs='+', type=float, help="Optional list of dashed horizontal lines to draw (i.e., significance values), separated by spaces at given -log10(p-value) values")
    parser.add_argument('--threshold', type=float, help="Threshold for significance (expressed in -log10(P))."
                        " Red points are used to denote signficance in the complementary dataset. Use --yline"
                        " to define horizontal lines to viusalize significance thresholds.")
    parser.add_argument('--symmetric', action='store_true', help="If set, y-axis scales for both datasets will be identical (auto-scales each axis without this option).")
    parser.add_argument('--filename', type=str, help="Choose filename for file export (without the extension).")
    
    args = parser.parse_args()
    
    # Load datasets
    df_A = load_dataset(args.df_A, args.chromosome, args.lower, args.upper)
    df_B = load_dataset(args.df_B, args.chromosome, args.lower, args.upper)
    
    # Check if DataFrames are empty
    empty_datasets = [name for name, df in [(f'\nDataset A: ({args.df_A})', df_A), (f'\nDataset B: ({args.df_B})', df_B)] if df.empty]
    if empty_datasets:
        sys.exit(f"Datasets are empty with given chromosome and coordinates range: {', '.join(empty_datasets)}")
    
    # Call the plotting function
    plot_summary_statistics(df_A, df_B, args.chromosome, args.lower, args.upper, args.x_line, args.y_line, args.threshold, args.symmetric, args.filename)

if __name__ == '__main__':
    main()
