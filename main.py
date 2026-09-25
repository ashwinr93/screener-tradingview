import pandas as pd
import numpy as np
from pathlib import Path

# --- File Paths ---
# Define file paths for clarity and easier modification
# The screener.in export is read from your Downloads folder, and the watchlist is written there too
DOWNLOADS = Path.home() / 'Downloads'
SCREENER_PATH = DOWNLOADS / 'query-results.csv'
BSE_MAPPING_PATH = Path(__file__).parent / 'bse_mapping.csv'
OUTPUT_PATH = DOWNLOADS / 'Weekend.txt'

# --- Step 1: Read and Prepare Screener Data ---
# Read the main data. Specify 'BSE Code' as string to prevent float/merge errors.
screener_df = pd.read_csv(SCREENER_PATH, dtype={'BSE Code': str})

# Select and sort by Market Capitalization
screener_df = screener_df[['Name', 'BSE Code', 'NSE Code', 'Market Capitalization']]
screener_df = screener_df.sort_values(by='Market Capitalization', ascending=False)

# --- Step 2: Read, Filter, and Prepare BSE Mapping Data ---
# Read the mapping file. Specify 'Security Code' as string.
bse_mapping_df = pd.read_csv(BSE_MAPPING_PATH, dtype={'Security Code': str})

# Filter for 'Active' status
bse_mapping_df = bse_mapping_df[bse_mapping_df['Status'] == 'Active']

# Remove the extra '#' from 'Security Id' before merging
bse_mapping_df['Security Id'] = bse_mapping_df['Security Id'].str.replace('#', '', regex=False)

# Select only the required columns for merging
bse_mapping_cols = bse_mapping_df[['Security Code', 'Security Id']]

# --- Step 3: Merge DataFrames ---
# Merge screener data with active BSE codes using a left join.
merged_df = screener_df.merge(bse_mapping_cols,
                              left_on='BSE Code',
                              right_on='Security Code',
                              how='left')

# --- Step 4: Clean and Standardize Data for Output ---
# Convert 'NSE Code' to string and replace 'nan' with an empty string.
merged_df['NSE Code'] = merged_df['NSE Code'].astype(str).replace('nan', '', regex=False)

# Fill any missing values for 'Security Id' and 'Security Code' with an empty string.
merged_df['Security Id'] = merged_df['Security Id'].fillna('')
merged_df['Security Code'] = merged_df['Security Code'].fillna('')

# **CRITICAL CHANGE: Filter out rows where both NSE Code and Security Id are missing.**
# We use a boolean mask to keep rows where EITHER code is NOT an empty string.
merged_df = merged_df[(merged_df['NSE Code'] != '') | (merged_df['Security Id'] != '')].copy()


# --- Step 5: Get User Input and Define Output Logic ---
try:
    output_type = int(input("Enter 1 for TradingView output, 2 for Google Finance output, or 3 for Yahoo Finance output: "))
except ValueError:
    print("Invalid input. Defaulting to TradingView output (1).")
    output_type = 1

def create_output_row(row, output_type):
    """Generates the formatted stock code string based on output type."""
    # Note: Since we've pre-filtered the DataFrame, this function should always return a valid ticker.

    if output_type == 1:
        # TradingView output (Handles special characters in NSE/BSE codes)
        nse_code = row['NSE Code'].replace('&', '_').replace('-', '_')
        bse_id = row['Security Id'].replace('&', '_').replace('-', '_')
        return f"NSE:{nse_code}" if nse_code else f"BSE:{bse_id}"

    elif output_type == 2:
        # Google Finance output (Uses BOM:Security Code for BSE)
        # Security Code is used here as it's the 6-digit number that Google Finance often expects for BSE/BOM.
        return f"NSE:{row['NSE Code']}" if row['NSE Code'] else f"BOM:{row['Security Code']}"

    elif output_type == 3:
        # Yahoo Finance output (Uses .NS for NSE and .BOM for Security Id/BSE)
        # Security Id is used here as it's the scrip short name that Yahoo Finance often expects for .BOM.
        return f"{row['NSE Code']}.NS" if row['NSE Code'] else f"{row['Security Id']}.BOM"

    else:
        # Default fallback
        return ""


# --- Step 6: Apply Logic and Export ---
# Apply the function to create the 'Output' column
merged_df['Output'] = merged_df.apply(lambda row: create_output_row(row, output_type), axis=1)

# Export the 'Output' column to the specified text file without header or index
output_df = merged_df[['Output']]
output_df.to_csv(OUTPUT_PATH, index=False, header=False)

print(f"\nOutput successfully saved to {OUTPUT_PATH}")