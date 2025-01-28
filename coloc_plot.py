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

from matplotlib.ticker import MaxNLocator, ScalarFormatter


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
    
    # Add standard 'ID' column and set it as the index
    for df in (df_A, df_B):
        df['ID'] = create_variant_id_df(df, 'chromosome', 'base_pair_location', 'effect_allele', 'other_allele')
        df.set_index('ID', inplace=True)

    # Calculate 'neg_log_10_p_value' if it doesn't exist
    for df in (df_A, df_B):
        if 'neg_log_10_p_value' not in df.columns:
            df['neg_log_10_p_value'] = -np.log10(df['p_value'])

    # Reflect df_B y-values below the x-axis
    df_B['neg_log_10_p_value'] *= -1

    # Retain common variants only
    common_indices = df_A.index.intersection(df_B.index)
    df_A = df_A.loc[common_indices]
    df_B = df_B.loc[common_indices]

    # Merge datasets
    merged_df = df_A.merge(df_B, left_index=True, right_index=True, suffixes=('_A', '_B'))

    # Log variant counts
    print(f"{len(df_A)} common variants retained.")
     
    # Create the figure and gridspec layout
    fig = plt.figure(figsize=(9, 9))
    gs = gridspec.GridSpec(3, 2, width_ratios=[1.5, 1], height_ratios=[1, 2, 1], wspace=0.5)
    ax1 = plt.subplot(gs[1, 0])
    axB = ax1.twinx()
    
    # Color points red if it is significant in the other dataset
    if threshold is not None:
        colors_A = [
            'red' if df_B.loc[idx, 'neg_log_10_p_value'] <= -threshold else 'black'
            for idx in df_A.index
        ]
        ax1.scatter(df_A['base_pair_location'], df_A['neg_log_10_p_value'], color=colors_A, s=1)

        colors_B = [
            'red' if df_A.loc[idx, 'neg_log_10_p_value'] >= threshold else 'black'
            for idx in df_B.index
        ]
        axB.scatter(df_B['base_pair_location'], df_B['neg_log_10_p_value'], color=colors_B, s=1)
    else:
        ax1.scatter(df_A['base_pair_location'], df_A['neg_log_10_p_value'], color='black', s=1)
        axB.scatter(df_B['base_pair_location'], df_B['neg_log_10_p_value'], color='black', s=1)

    # Highlight max value in df_A and min value in df_B with triangles
    def highlight_point(df, axis, color, marker):
        axis.scatter(
            df['base_pair_location'], df['neg_log_10_p_value'],
            color=color, s=35, alpha=0.8, marker=marker
        )

    max_df_A = df_A.loc[df_A['neg_log_10_p_value'].idxmax()]
    min_df_B = df_B.loc[df_B['neg_log_10_p_value'].idxmin()]

    highlight_point(max_df_A, ax1, 'orange', '^' if max_df_A['beta'] > 0 else 'v' if max_df_A['beta'] < 0 else 'o')
    highlight_point(min_df_B, axB, 'blue', '^' if min_df_B['beta'] > 0 else 'v' if min_df_B['beta'] < 0 else 'o')

    # Mark reciprocal points for comparison
    max_in_B = df_A.loc[df_B['neg_log_10_p_value'].idxmin()]
    min_in_A = df_B.loc[df_A['neg_log_10_p_value'].idxmax()]

    highlight_point(max_in_B, ax1, 'blue', '^' if max_in_B['beta'] > 0 else 'v' if max_in_B['beta'] < 0 else 'o')
    highlight_point(min_in_A, axB, 'orange', '^' if min_in_A['beta'] > 0 else 'v' if min_in_A['beta'] < 0 else 'o')

    # Add horizontal line at y=0
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)

    # Adjust y-axis limits
    max_A = df_A['neg_log_10_p_value'].max()
    min_B = df_B['neg_log_10_p_value'].min()
    max_y = max(abs(max_A), abs(min_B))

    if symmetric:
        ax1.set_ylim(-max_y * 1.1, max_y * 1.1)
        ax1.set_yticks(np.round(np.linspace(0, max_y, 5), 1))
        axB.set_ylim(-max_y * 1.1, max_y * 1.1)
        axB.set_yticks(np.round(np.linspace(-max_y, 0, 5), 1))
    else:
        ax1.set_ylim(-max_A * 1.1, max_A * 1.1)
        ax1.set_yticks(np.round(np.linspace(0, max_A, 5), 1))
        axB.set_ylim(min_B * 1.1, -min_B * 1.1)
        axB.set_yticks(np.round(np.linspace(min_B, 0, 5), 1))

    # Adjust tick parameters
    ax1.tick_params(axis='y', labelsize=8)
    axB.tick_params(axis='y', labelsize=8)

    # Remove borders for aesthetics
    for spine in ['top', 'right', 'bottom']:
        ax1.spines[spine].set_visible(False)
        axB.spines[spine].set_visible(False)

    # Set labels
    ax1.set_xlabel('Base Pair Location')
    ax1.set_ylabel(r"$-\log_{10}(p)$", labelpad=5)
    axB.set_ylabel(r"$\log_{10}(p)$", labelpad=15, rotation=-90)

    # Set x-axis limits and format ticks
    ax1.set_xlim(lower, upper)
    ax1.xaxis.set_major_locator(MaxNLocator(nbins=7))
    ax1.tick_params(axis='x', labelsize=8)
    ax1.xaxis.set_major_formatter(ScalarFormatter())

    # Add vertical and horizontal guide lines
    if x_lines:
        for bp_value in x_lines:
            ax1.axvline(x=bp_value, color='black', linestyle='--', linewidth=0.5)

    if y_lines:
        for neg_log10_p_value in y_lines:
            axis = axB if neg_log10_p_value < 0 else ax1
            axis.axhline(y=neg_log10_p_value, color='black', linestyle='--', linewidth=0.5)
            
    
    ####################
    # Correlation plot #
    ####################
    
    # Scatter plot for correlation
    ax2 = plt.subplot(gs[1, 1])
    ax2.scatter(
        -merged_df['neg_log_10_p_value_B'], merged_df['neg_log_10_p_value_A'],
        alpha=0.4, color='purple', s=5
    )

    # Highlight top variants
    max_A_idx = merged_df['neg_log_10_p_value_A'].idxmax()
    min_B_idx = merged_df['neg_log_10_p_value_B'].idxmin()

    ax2.scatter(
        -merged_df.loc[max_A_idx, 'neg_log_10_p_value_B'],
        merged_df.loc[max_A_idx, 'neg_log_10_p_value_A'],
        color='orange', s=35, alpha=0.8,
        label=f"Top variant for dataset A ({df_A['neg_log_10_p_value'].idxmax()})"
    )

    ax2.scatter(
        -merged_df.loc[min_B_idx, 'neg_log_10_p_value_B'],
        merged_df.loc[min_B_idx, 'neg_log_10_p_value_A'],
        color='blue', s=35, alpha=0.7,
        label=f"Top variant for dataset B ({df_B['neg_log_10_p_value'].idxmin()})"
    )

    # Set axis labels
    ax2.set_xlabel(r"$-\log_{10}(p)$ for Dataset B")
    ax2.set_ylabel(r"$-\log_{10}(p)$ for Dataset A")

    # Adjust axis limits
    max_A = merged_df['neg_log_10_p_value_A'].max()
    min_B = merged_df['neg_log_10_p_value_B'].min()
    max_y = max_A if symmetric else abs(min_B)

    if symmetric:
        ax2.set_xlim(0, max_y * 1.1)
        ax2.set_ylim(0, max_y * 1.1)
    else:
        ax2.set_xlim(0, abs(min_B) * 1.1)
        ax2.set_ylim(0, max_A * 1.1)

    # Remove top and right spines
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # Add legend
    ax2.legend(loc=(0, -0.4), fontsize=8)

    # Save the plot
    os.makedirs("plots", exist_ok=True)
    output_file = f"plots/{filename or 'coloc_plot'}.svg"
    plt.savefig(output_file, format='svg')
    print(f"Plot saved as: {output_file}")

    
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
