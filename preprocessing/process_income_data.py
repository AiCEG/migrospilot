import pandas as pd
import numpy as np

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

def load_migros_data(file_path: str) -> pd.DataFrame:
    """Load the processed Migros facilities data."""
    return pd.read_csv(file_path)

def analyze_income_data(income_df: pd.DataFrame):
    """Perform basic analysis on the income data."""
    print("\n=== Income Data Statistics ===")
    print(f"Number of municipalities: {len(income_df)}")
    
    print("\n=== Income Distribution ===")
    print(f"Average income per capita: {income_df['income_per_capita'].mean():.2f} CHF")
    print(f"Median income per capita: {income_df['income_per_capita'].median():.2f} CHF")
    print(f"Minimum income per capita: {income_df['income_per_capita'].min():.2f} CHF")
    print(f"Maximum income per capita: {income_df['income_per_capita'].max():.2f} CHF")
    
    print("\n=== Top 10 Municipalities by Income ===")
    top_10 = income_df.nlargest(10, 'income_per_capita')
    print(top_10[['municipality', 'income_per_capita']].to_string(index=False))
    
    print("\n=== Bottom 10 Municipalities by Income ===")
    bottom_10 = income_df.nsmallest(10, 'income_per_capita')
    print(bottom_10[['municipality', 'income_per_capita']].to_string(index=False))

def main():
    # Load and process the data
    income_df = load_income_data('Durchschnittliches steuerbares Einkommen.csv')
    migros_df = load_migros_data('processed_migros_facilities.csv')
    
    # Perform analysis
    analyze_income_data(income_df)
    
    # Save processed income data
    income_df.to_csv('processed_income_data.csv', index=False)
    print("\nProcessed income data saved to 'processed_income_data.csv'")

if __name__ == "__main__":
    main() 