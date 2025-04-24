import json
import pandas as pd
from typing import Dict, List
import os

# Type mapping for allowed branch types
ALLOWED_TYPES = ['m', 'mm', 'mmm', 'voi']

TYPE_MAP = {
    'm': {
        'name': 'M-Migros',
        'description': 'Kleine Filiale mit Grundsortiment'
    },
    'mm': {
        'name': 'MM-Migros',
        'description': 'Mittlere Filiale mit erweitertem Sortiment'
    },
    'mmm': {
        'name': 'MMM-Migros',
        'description': 'Grosse Filiale mit Vollsortiment'
    },
    'voi': {
        'name': 'VOI',
        'description': 'Kleiner Nahversorger für Quartiere oder ländliche Orte'
    }
}

def load_migros_data(file_path: str) -> List[Dict]:
    """Load and parse the Migros filial data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['data']['facilities']['results']

def filter_branches(facilities: List[Dict]) -> List[Dict]:
    """Filter branches to only include allowed types."""
    return [f for f in facilities if f['type'] in ALLOWED_TYPES]

def create_branches_dataframe(facilities: List[Dict]) -> pd.DataFrame:
    """Create a pandas DataFrame from the filtered facilities data."""
    rows = []
    for facility in facilities:
        row = {
            'id': facility['id'],
            'name': facility['name'],
            'type': facility['type'],
            'type_name': TYPE_MAP.get(facility['type'], {}).get('name', 'Unknown'),
            'type_description': TYPE_MAP.get(facility['type'], {}).get('description', 'Unknown'),
            'address': facility['location']['address'],
            'zip_code': facility['location']['zip'],
            'city': facility['location']['city'],
            'country': facility['location']['country'],
            'latitude': facility['location']['geo']['lat'],
            'longitude': facility['location']['geo']['lon']
        }
        rows.append(row)
    
    return pd.DataFrame(rows)

def analyze_branches(df: pd.DataFrame):
    """Perform basic analysis on the Migros branches data."""
    print("\n=== Migros Branches Statistics ===")
    print(f"Total number of branches: {len(df)}")
    
    print("\n=== Distribution by Type ===")
    type_counts = df['type_name'].value_counts()
    print(type_counts)
    
    print("\n=== Distribution by City ===")
    city_counts = df['city'].value_counts().head(10)
    print(city_counts)

def main():
    # Create output directory if it doesn't exist
    os.makedirs('../output', exist_ok=True)
    
    # Load and process the data
    facilities = load_migros_data('../../migrosfilialen.json')
    filtered_facilities = filter_branches(facilities)
    df = create_branches_dataframe(filtered_facilities)
    
    # Perform analysis
    analyze_branches(df)
    
    # Save processed data
    output_path = '../output/processed_migros_branches.csv'
    df.to_csv(output_path, index=False)
    print(f"\nProcessed data saved to {output_path}")

if __name__ == "__main__":
    main() 