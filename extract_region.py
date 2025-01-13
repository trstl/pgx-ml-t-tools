#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 10 09:06:51 2025

"""


import argparse
import os
import requests
import sys
import subprocess

import pandas as pd


def extract_by_pos(filename, chromosome:str, start:int, end:int):
    try:
        # Construct the tabix command
        command = ["tabix", filename, f"{chromosome}:{start}-{end}"]
        
        # Run the command and capture the output
        result = subprocess.run(command, capture_output=True, text=True,
                                check=True)
        
        # Split the output into lines and create a DataFrame
        data = [line.split("\t") for line in result.stdout.strip().split("\n")]
        df = pd.DataFrame(data, columns=[
            "chromosome",
            "base_pair_location",
            "effect_allele",
            "other_allele",
            "beta",
            "std_error",
            "effect_allele_frequency",
            "p_value",
        ])
        
        return df
    
    except subprocess.CalledProcessError as e:
        print(f"Error running tabix: {e.stderr}")
        return None


# Function to retrieve genomic position using Ensembl REST API
def fetch_gene_region(build:str, gene:str) -> dict:
    base_url = "https://rest.ensembl.org"
    
    # Construct the endpoint
    endpoint = f"/lookup/symbol/homo_sapiens/{gene}?content-type=application/json;expand=1"
    url = base_url + endpoint
    
    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP issues
        
        # Parse the JSON response
        gene_data = response.json()
        
        # Extract relevant information
        if 'seq_region_name' in gene_data and 'start' in gene_data and 'end' in gene_data:
            return {
                "chromosome": gene_data['seq_region_name'],
                "start": gene_data['start'],
                "end": gene_data['end'],
            }
        else:
            print(f"Gene '{gene}' not found in build '{build}'.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error querying Ensembl API: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Extract genomic region based on --gene or --pos"
    )

    # Required argument
    parser.add_argument(
        "--filename",
        type=str,
        required=True,
        help="Standardized .gz dataset",
    )  

    # Arguments to extract by gene name
    parser.add_argument(
        "--gene",
        type=str,
        help="A single string representing the gene",
    )
    
    parser.add_argument(
        "--build",
        type=str,
        help="Specify build of dataset (e.g., GRCh38, GRCh37) to extract"
        " region from ensembl",
    )
    
    parser.add_argument(
        "--buffer",
        type=int,
        help="Specify number of base pairs before and after gene region to"
        " include in the extraction",
    )


    # Arguments to extract by position
    parser.add_argument(
        "--pos",
        nargs=3,
        type=str,
        metavar=("CHR", "START", "END"),
        help="Position specified by chromosome followed by start and end in bp",
    )

    args = parser.parse_args()
    
    filename = args.filename
    if not os.path.exists(filename):
        sys.exit("Error: Filename not found.")

    # Error handling
    if args.gene and args.pos:
        print("Error: Cannot use --gene and --pos simultaneously.",
              file=sys.stderr)
        sys.exit(1)

    if not args.gene and not args.pos:
        print("Error: Either --gene or --pos must be provided.",
              file=sys.stderr)
        sys.exit(1)
        
    # Run with position arguments
    if args.pos:
        chromosome, start, end = args.pos
        if args.buffer:
            print("--buffer argument not valid for extraction by position."
                  "Skipping.")
        if args.build:
            print("--build argument not valid for extraction by position."
                  "Skipping.")
        try:
            start = int(start)
            end = int(end)
        except ValueError:
            print("Error: --pos requires two integers for START and END.",
                  file=sys.stderr)
            sys.exit(1)

        if start >= end:
            print("Error: START must be less than END for --pos.",
                  file=sys.stderr)
            sys.exit(1)

        df = extract_by_pos(filename, chromosome, start, end)
        
    # Run with gene arguments
    if args.gene:
        if args.build:
            gene_info = fetch_gene_region(args.build, args.gene)
            
            chromosome = gene_info['chromosome']
            start = gene_info['start']
            end = gene_info['end']
            
            if gene_info != None:
                buffer = 0 if not args.buffer else args.buffer
                df = extract_by_pos(filename, chromosome,
                                        start - buffer, end + buffer)
            else:
                sys.exit()
                
        else:
            print("Error: Build must be specified with --build.",
                  file=sys.stderr)
            sys.exit(1)
            
    return df

if __name__ == "__main__":
    df = main()