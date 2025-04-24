import json
import pandas as pd
from typing import Dict, List

# Type mapping
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
    'fm': {
        'name': 'Fachmarkt',
        'description': 'Spezialisierte Non-Food-Filiale'
    },
    'mr': {
        'name': 'Migros-Restaurant',
        'description': 'Verpflegungseinheit'
    },
    'dmp': {
        'name': 'Migros-Partner',
        'description': 'Unabhängige Partnerfiliale mit Migros-Produkten'
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

def check_unknown_types(facilities: List[Dict]) -> Dict[str, List[Dict]]:
    """Check for facilities with unknown types and return them grouped by type."""
    unknown_types = {}
    for facility in facilities:
        if facility['type'] not in TYPE_MAP:
            if facility['type'] not in unknown_types:
                unknown_types[facility['type']] = []
            unknown_types[facility['type']].append(facility)
    return unknown_types

def create_dataframe(facilities: List[Dict]) -> pd.DataFrame:
    """Create a pandas DataFrame from the facilities data."""
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

def analyze_data(df: pd.DataFrame, unknown_types: Dict[str, List[Dict]]):
    """Perform basic analysis on the Migros facilities data."""
    print("\n=== Basic Statistics ===")
    print(f"Total number of facilities: {len(df)}")
    
    print("\n=== Distribution by Type ===")
    type_counts = df['type_name'].value_counts()
    print(type_counts)
    
    print("\n=== Distribution by City ===")
    city_counts = df['city'].value_counts().head(10)
    print(city_counts)
    
    if unknown_types:
        print("\n=== Unknown Types Found ===")
        for type_code, facilities in unknown_types.items():
            print(f"\nType code: '{type_code}'")
            print(f"Number of facilities: {len(facilities)}")
            print("Example facilities:")
            for facility in facilities[:3]:  # Show first 3 examples
                print(f"- {facility['name']} ({facility['id']}) in {facility['location']['city']}")

def main():
    # Load and process the data
    facilities = load_migros_data('migrosfilialen.json')
    
    # Check for unknown types
    unknown_types = check_unknown_types(facilities)
    
    # Create DataFrame
    df = create_dataframe(facilities)
    
    # Perform analysis
    analyze_data(df, unknown_types)
    
    # Save processed data to CSV
    df.to_csv('processed_migros_facilities.csv', index=False)
    print("\nProcessed data saved to 'processed_migros_facilities.csv'")

if __name__ == "__main__":
    main() 