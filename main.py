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
screener_df = pd.read_csv(SCREENER_PATH, dtype={'BSE Code': str})

# FIX: Strip out the hidden '.0' float artifact that Pandas adds to the string, which breaks the merge.
screener_df['BSE Code'] = screener_df['BSE Code'].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')

# Identify REITs using name keywords OR a specific list of known REIT NSE tickers
known_reit_tickers = ['EMBASSY', 'MINDSPACE', 'BIRET', 'NXST', 'BAGMANE']
is_reit_name = screener_df['Name'].str.contains(r'\bREIT\b|Real Estate Investment Trust', case=False, na=False,
                                                regex=True)
is_reit_ticker = screener_df['NSE Code'].isin(known_reit_tickers)

# Flag as True if it matches either condition
screener_df['Is_REIT'] = is_reit_name | is_reit_ticker

# Select and sort by Market Capitalization
screener_df = screener_df[['Name', 'BSE Code', 'NSE Code', 'Market Capitalization', 'Is_REIT']]
screener_df = screener_df.sort_values(by='Market Capitalization', ascending=False)

# --- Step 2: Read, Filter, and Prepare BSE Mapping Data ---
bse_mapping_df = pd.read_csv(BSE_MAPPING_PATH, dtype={'Security Code': str})
bse_mapping_df = bse_mapping_df[bse_mapping_df['Status'] == 'Active']

# Remove the extra '#' from 'Security Id' before merging
bse_mapping_df['Security Id'] = bse_mapping_df['Security Id'].str.replace('#', '', regex=False)

bse_mapping_cols = bse_mapping_df[['Security Code', 'Security Id']]

# --- Step 3: Merge DataFrames ---
# Merge screener data with active BSE codes using a left join.
merged_df = screener_df.merge(bse_mapping_cols,
                              left_on='BSE Code',
                              right_on='Security Code',
                              how='left')

# --- Step 4: Clean and Standardize Data for Output ---
merged_df['NSE Code'] = merged_df['NSE Code'].astype(str).replace('nan', '', regex=False)
merged_df['Security Id'] = merged_df['Security Id'].fillna('')
merged_df['Security Code'] = merged_df['Security Code'].fillna('')

# Filter out rows where both NSE Code and Security Id are missing.
merged_df = merged_df[(merged_df['NSE Code'] != '') | (merged_df['Security Id'] != '')].copy()

# --- Step 5: Get User Input and Define Output Logic ---
try:
    output_type = int(
        input("Enter 1 for TradingView output, 2 for Google Finance output, or 3 for Yahoo Finance output: "))
except ValueError:
    print("Invalid input. Defaulting to TradingView output (1).")
    output_type = 1


def create_output_row(row, output_type):
    """Generates the formatted stock code string based on output type."""
    is_reit = row.get('Is_REIT', False)

    if output_type == 1:
        # TradingView output
        nse_code = row['NSE Code'].replace('&', '_').replace('-', '_')
        bse_id = row['Security Id'].replace('&', '_').replace('-', '_')

        if nse_code:
            # Append .RR suffix if the asset is a REIT on the NSE
            return f"NSE:{nse_code}.RR" if is_reit else f"NSE:{nse_code}"
        else:
            return f"BSE:{bse_id}"

    elif output_type == 2:
        # Google Finance output
        # Force route REITs to BSE. Failsafe: check original Screener 'BSE Code' if mapping 'Security Code' fails.
        if is_reit:
            bse_target = row['Security Code'] if row['Security Code'] else row['BSE Code']
            if bse_target:
                return f"BOM:{bse_target}"

        return f"NSE:{row['NSE Code']}" if row['NSE Code'] else f"BOM:{row['Security Code']}"

    elif output_type == 3:
        # Yahoo Finance output
        return f"{row['NSE Code']}.NS" if row['NSE Code'] else f"{row['Security Id']}.BOM"

    else:
        return ""


# --- Step 6: Apply Logic and Export ---
merged_df['Output'] = merged_df.apply(lambda row: create_output_row(row, output_type), axis=1)

output_df = merged_df[['Output']]
output_df.to_csv(OUTPUT_PATH, index=False, header=False)

print(f"\nOutput successfully saved to {OUTPUT_PATH}")