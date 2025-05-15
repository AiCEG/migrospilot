import pandas as pd
import numpy as np
import os
import requests
import json
from typing import Dict, List, Set
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
    
    def batch_process_locations(self, locations: List[Dict], output_file_20min: str, output_file_10min: str,
                              processed_20min: Set[str], processed_10min: Set[str]):
        """Process multiple locations and save results for both 10 and 20 minute ranges."""
        results_20min = []
        results_10min = []
        
        # Load existing results if they exist
        existing_20min = []
        existing_10min = []
        if os.path.exists(output_file_20min):
            with open(output_file_20min, 'r') as f:
                existing_20min = json.load(f)
        if os.path.exists(output_file_10min):
            with open(output_file_10min, 'r') as f:
                existing_10min = json.load(f)
        
        for idx, loc in enumerate(locations):
            print(f"Processing location {idx + 1}/{len(locations)}: {loc['name']}")
            
            try:
                # Process 20-minute isochrone if needed
                if loc['id'] not in processed_20min:
                    isochrone_20min = self.get_isochrone(
                        lat=loc['latitude'],
                        lon=loc['longitude'],
                        range=20 * 60  # 20 minutes in seconds
                    )
                    
                    result_20min = {
                        'branch_id': loc['id'],
                        'branch_name': loc['name'],
                        'branch_type': loc['type'],
                        'city': loc['city'],
                        'isochrone_data': isochrone_20min
                    }
                    results_20min.append(result_20min)
                    time.sleep(4)  # Delay after first request
                
                # Process 10-minute isochrone if needed
                if loc['id'] not in processed_10min:
                    isochrone_10min = self.get_isochrone(
                        lat=loc['latitude'],
                        lon=loc['longitude'],
                        range=10 * 60  # 10 minutes in seconds
                    )
                    
                    result_10min = {
                        'branch_id': loc['id'],
                        'branch_name': loc['name'],
                        'branch_type': loc['type'],
                        'city': loc['city'],
                        'isochrone_data': isochrone_10min
                    }
                    results_10min.append(result_10min)
                    time.sleep(4)  # Delay after second request
                
                # Save intermediate results every 5 locations
                if (idx + 1) % 5 == 0:
                    if results_20min:
                        all_results_20min = existing_20min + results_20min
                        self._save_results(all_results_20min, output_file_20min)
                        existing_20min = all_results_20min
                        results_20min = []
                    
                    if results_10min:
                        all_results_10min = existing_10min + results_10min
                        self._save_results(all_results_10min, output_file_10min)
                        existing_10min = all_results_10min
                        results_10min = []
                
            except Exception as e:
                print(f"Error processing {loc['name']}: {str(e)}")
                continue
        
        # Save final results
        if results_20min:
            all_results_20min = existing_20min + results_20min
            self._save_results(all_results_20min, output_file_20min)
        
        if results_10min:
            all_results_10min = existing_10min + results_10min
            self._save_results(all_results_10min, output_file_10min)
    
    def _save_results(self, results: List[Dict], output_file: str):
        """Save results to a JSON file."""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

def load_branches_data(file_path: str) -> List[Dict]:
    """Load branches data for geospatial processing."""
    df = pd.read_csv(file_path)
    return df.to_dict('records')

def get_processed_branches(file_path: str) -> Set[str]:
    """Get set of branch IDs that have already been processed."""
    processed = set()
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
                for branch in data:
                    # Try both 'branch_id' and 'id' fields
                    branch_id = branch.get('branch_id')
                    if branch_id is None:
                        branch_id = branch.get('id')
                    if branch_id is not None:
                        processed.add(str(branch_id))
                print(f"Found {len(processed)} processed branches in {file_path}")
            except json.JSONDecodeError:
                print(f"Warning: Could not read {file_path}. File might be empty or corrupted.")
    return processed

def process_geospatial_data(api_key: str):
    """Main function to process geospatial data."""
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    # Define output files for both ranges
    output_file_20min = 'output/isochrone_results_20min.json'
    output_file_10min = 'output/isochrone_results_10min.json'
    
    # Get processed branches from both files
    processed_20min = get_processed_branches(output_file_20min)
    processed_10min = get_processed_branches(output_file_10min)
    
    # Load branches data
    branches_data = load_branches_data('output/geospatial_branches_data.csv')
    print(f"\nTotal branches in input data: {len(branches_data)}")
    
    # Debug: Print first few entries from each source
    if processed_20min:
        print("\nFirst few IDs from 20min file:", list(processed_20min)[:5])
    if branches_data:
        print("First few IDs from input data:", [str(b['id']) for b in branches_data[:5]])
    
    # Filter branches that need processing (missing from either file)
    branches_to_process = [
        branch for branch in branches_data 
        if str(branch['id']) not in processed_20min or str(branch['id']) not in processed_10min
    ]
    
    if not branches_to_process:
        print("All branches have been processed in both 10min and 20min files!")
        return
    
    print(f"Found {len(branches_to_process)} branches that need processing:")
    print(f"- Missing from 20min file: {len([b for b in branches_to_process if str(b['id']) not in processed_20min])}")
    print(f"- Missing from 10min file: {len([b for b in branches_to_process if str(b['id']) not in processed_10min])}")
    
    # Initialize OpenRouteService client
    ors = OpenRouteService(api_key)
    
    # Process locations
    ors.batch_process_locations(
        branches_to_process, 
        output_file_20min, 
        output_file_10min,
        processed_20min,
        processed_10min
    )
    
    print(f"\nGeospatial processing complete!")
    print(f"20-minute results saved to {output_file_20min}")
    print(f"10-minute results saved to {output_file_10min}")

if __name__ == "__main__":
    # You'll need to replace this with your actual OpenRouteService API key
    API_KEY = "5b3ce3597851110001cf62487c99fe6a43ed4e76ab7ff6715ade0102"
    JOEL_API_KEY = "5b3ce3597851110001cf62487d3994c67c8e495d939a9b1f2fa9a0dc"
    process_geospatial_data(JOEL_API_KEY) 