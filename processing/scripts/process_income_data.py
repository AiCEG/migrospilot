import pandas as pd
import numpy as np
import os

def load_income_data(file_path: str) -> pd.DataFrame:
    """Load and process the income data CSV file."""
    # Read the CSV with semicolon separator
    df = pd.read_csv(file_path, sep=';')
    
    # Filter for per capita income data
    df = df[df['VARIABLE'] == 'Steuerbares Einkommen pro Einwohner/-in, in Franken']
    
    # Select and rename relevant columns
    df = df[['GEO_ID', 'GEO_NAME', 'VALUE']]
    df = df.rename(columns={
        'GEO_ID': 'municipality_id',
        'GEO_NAME': 'municipality',
        'VALUE': 'income_per_capita'
    })
    
    return df

def analyze_income_data(df: pd.DataFrame):
    """Perform basic analysis on the income data."""
    print("\n=== Income Data Statistics ===")
    print(f"Number of municipalities: {len(df)}")
    
    print("\n=== Income Distribution ===")
    print(f"Average income per capita: {df['income_per_capita'].mean():.2f} CHF")
    print(f"Median income per capita: {df['income_per_capita'].median():.2f} CHF")
    print(f"Minimum income per capita: {df['income_per_capita'].min():.2f} CHF")
    print(f"Maximum income per capita: {df['income_per_capita'].max():.2f} CHF")
    
    print("\n=== Top 10 Municipalities by Income ===")
    top_10 = df.nlargest(10, 'income_per_capita')
    print(top_10[['municipality', 'income_per_capita']].to_string(index=False))
    
    print("\n=== Bottom 10 Municipalities by Income ===")
    bottom_10 = df.nsmallest(10, 'income_per_capita')
    print(bottom_10[['municipality', 'income_per_capita']].to_string(index=False))

def main():
    # Create output directory if it doesn't exist
    os.makedirs('../output', exist_ok=True)
    
    # Load and process the data
    income_df = load_income_data('../../Durchschnittliches steuerbares Einkommen.csv')
    
    # Perform analysis
    analyze_income_data(income_df)
    
    # Save processed data
    output_path = '../output/processed_income_data.csv'
    income_df.to_csv(output_path, index=False)
    print(f"\nProcessed income data saved to {output_path}")

if __name__ == "__main__":
    main() 