import pandas as pd
import numpy as np

def load_population_data(file_path: str) -> pd.DataFrame:
    """Load and process the population data CSV file."""
    # Read the CSV with semicolon separator
    df = pd.read_csv(file_path, sep=';')
    
    # Select and rename relevant columns
    df = df[['ERHJAHR', 'GDENR', 'GDEHISTID', 'GTOT']]
    df = df.rename(columns={
        'ERHJAHR': 'year',
        'GDENR': 'municipality_id',
        'GDEHISTID': 'municipality_hist_id',
        'GTOT': 'total_population'
    })
    
    return df

def analyze_population_data(df: pd.DataFrame):
    """Perform basic analysis on the population data."""
    print("\n=== Population Data Statistics ===")
    print(f"Number of municipalities: {len(df)}")
    
    print("\n=== Population Distribution ===")
    print(f"Total population: {df['total_population'].sum():,}")
    print(f"Average population per municipality: {df['total_population'].mean():.2f}")
    print(f"Median population per municipality: {df['total_population'].median():.2f}")
    print(f"Minimum population: {df['total_population'].min()}")
    print(f"Maximum population: {df['total_population'].max()}")
    
    print("\n=== Top 10 Municipalities by Population ===")
    top_10 = df.nlargest(10, 'total_population')
    print(top_10.to_string(index=False))
    
    print("\n=== Bottom 10 Municipalities by Population ===")
    bottom_10 = df.nsmallest(10, 'total_population')
    print(bottom_10.to_string(index=False))

def main():
    # Load and process the data
    pop_df = load_population_data('bevölkerungsdichte/GWS2023_GMDE.csv')
    
    # Perform analysis
    analyze_population_data(pop_df)
    
    # Save processed data
    pop_df.to_csv('processed_population_data.csv', index=False)
    print("\nProcessed population data saved to 'processed_population_data.csv'")

if __name__ == "__main__":
    main() 