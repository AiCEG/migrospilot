import pandas as pd
import numpy as np
import os

def load_processed_data():
    """Load all processed data files."""
    # Load Migros branches data
    branches_df = pd.read_csv('../output/processed_migros_branches.csv')
    
    # Load population data
    population_df = pd.read_csv('../output/processed_population_data.csv')
    
    # Load income data
    income_df = pd.read_csv('../output/processed_income_data.csv')
    
    return branches_df, population_df, income_df

def combine_data(branches_df: pd.DataFrame, population_df: pd.DataFrame, income_df: pd.DataFrame):
    """Combine all data sources and prepare for analysis."""
    # First, combine population and income data
    # Note: We'll need to handle municipality ID matching carefully
    combined_df = pd.merge(
        population_df,
        income_df,
        on='municipality_id',
        how='outer'
    )
    
    # Add municipality name if available
    if 'municipality' in income_df.columns:
        combined_df['municipality'] = income_df['municipality']
    
    # Calculate population density (if we have area data)
    # This will be added later when we have the area data
    
    return combined_df, branches_df

def analyze_combined_data(combined_df: pd.DataFrame, branches_df: pd.DataFrame):
    """Perform analysis on the combined data."""
    print("\n=== Combined Data Statistics ===")
    print(f"Number of municipalities with complete data: {len(combined_df)}")
    
    print("\n=== Population and Income Correlation ===")
    correlation = combined_df['total_population'].corr(combined_df['income_per_capita'])
    print(f"Correlation between population and income: {correlation:.2f}")
    
    print("\n=== Branches Distribution ===")
    print(f"Total number of branches: {len(branches_df)}")
    print("\nBranch types distribution:")
    print(branches_df['type_name'].value_counts())
    
    # Calculate branches per capita (rough estimate)
    total_population = combined_df['total_population'].sum()
    branches_per_capita = len(branches_df) / total_population * 100000
    print(f"\nBranches per 100,000 people: {branches_per_capita:.2f}")

def prepare_geospatial_data(branches_df: pd.DataFrame):
    """Prepare data for OpenRouteService integration."""
    # Create a simplified version of branches data for geospatial processing
    geospatial_df = branches_df[[
        'id',
        'name',
        'type',
        'latitude',
        'longitude',
        'city'
    ]].copy()
    
    # Add a column for the radius (20 minutes by bicycle)
    # This will be used by OpenRouteService
    geospatial_df['radius_minutes'] = 20
    
    return geospatial_df

def main():
    # Create output directory if it doesn't exist
    os.makedirs('../output', exist_ok=True)
    
    # Load all processed data
    branches_df, population_df, income_df = load_processed_data()
    
    # Combine the data
    combined_df, branches_df = combine_data(branches_df, population_df, income_df)
    
    # Perform analysis
    analyze_combined_data(combined_df, branches_df)
    
    # Prepare geospatial data
    geospatial_df = prepare_geospatial_data(branches_df)
    
    # Save combined data
    combined_df.to_csv('../output/combined_municipality_data.csv', index=False)
    geospatial_df.to_csv('../output/geospatial_branches_data.csv', index=False)
    
    print("\nData processing complete!")
    print("Saved files:")
    print("- combined_municipality_data.csv: Combined population and income data")
    print("- geospatial_branches_data.csv: Prepared data for OpenRouteService integration")

if __name__ == "__main__":
    main() 