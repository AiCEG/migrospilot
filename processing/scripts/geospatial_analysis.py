import pandas as pd
import numpy as np
import os
import requests
import json
from typing import Dict, List
import time

class OpenRouteService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org"
    
    def get_isochrone(self, lat: float, lon: float, profile: str = "cycling-regular", 
                     range_type: str = "time", range: int = 1200) -> Dict:
        """Get isochrone (reachable area) for a given location."""
        url = f"{self.base_url}/v2/isochrones/{profile}"
        
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        body = {
            "locations": [[lon, lat]],
            "range_type": range_type,
            "range": [range],
            "attributes": ["area", "reachfactor", "total_pop"]
        }
        
        response = requests.post(url, headers=headers, json=body)
        return response.json()
    
    def batch_process_locations(self, locations: List[Dict], output_file: str):
        """Process multiple locations and save results."""
        results = []
        
        for idx, loc in enumerate(locations):
            print(f"Processing location {idx + 1}/{len(locations)}: {loc['name']}")
            
            try:
                isochrone = self.get_isochrone(
                    lat=loc['latitude'],
                    lon=loc['longitude'],
                    range=loc['radius_minutes'] * 60  # Convert minutes to seconds
                )
                
                # Extract relevant information
                result = {
                    'branch_id': loc['id'],
                    'branch_name': loc['name'],
                    'branch_type': loc['type'],
                    'city': loc['city'],
                    'isochrone_data': isochrone
                }
                
                results.append(result)
                
                # Save intermediate results every 10 locations
                if (idx + 1) % 10 == 0:
                    self._save_results(results, output_file)
                
                # Add delay to respect API rate limits
                time.sleep(4)
                
            except Exception as e:
                print(f"Error processing {loc['name']}: {str(e)}")
                continue
        
        # Save final results
        self._save_results(results, output_file)
    
    def _save_results(self, results: List[Dict], output_file: str):
        """Save results to a JSON file."""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

def load_branches_data(file_path: str) -> List[Dict]:
    """Load branches data for geospatial processing."""
    df = pd.read_csv(file_path)
    return df.to_dict('records')

def process_geospatial_data(api_key: str):
    """Main function to process geospatial data."""
    # Create output directory if it doesn't exist
    os.makedirs('../output', exist_ok=True)
    
    # Load branches data
    branches_data = load_branches_data('../output/geospatial_branches_data.csv')
    
    # Initialize OpenRouteService client
    ors = OpenRouteService(api_key)
    
    # Process locations and save results
    output_file = '../output/isochrone_results.json'

    # Remove already processed branches
    # there are already processed branches in the output file
    # so we need to remove them from the branches_data
    # read the output file, look for the branch_id and remove the corresponding branch from branches_data
    with open(output_file, 'r') as f:
        processed_branches = [branch['branch_id'] for branch in json.load(f)]
    branches_data = [branch for branch in branches_data if branch['id'] not in processed_branches]
    

    ors.batch_process_locations(branches_data, output_file)
    
    print(f"\nGeospatial processing complete!")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    # You'll need to replace this with your actual OpenRouteService API key
    API_KEY = "5b3ce3597851110001cf62487c99fe6a43ed4e76ab7ff6715ade0102"
    JOEL_API_KEY = "5b3ce3597851110001cf62487d3994c67c8e495d939a9b1f2fa9a0dc"
    process_geospatial_data(API_KEY) 