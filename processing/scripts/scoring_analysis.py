import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LocationScore:
    branch_id: str
    branch_name: str
    branch_type: str
    city: str
    population_coverage: float
    area_coverage: float
    reach_factor: float
    total_score: float

class LocationScorer:
    def __init__(self, isochrone_data_path: str):
        self.isochrone_data_path = isochrone_data_path
        self.scores: List[LocationScore] = []
    
    def load_isochrone_data(self) -> List[Dict]:
        """Load the isochrone data from JSON file."""
        with open(self.isochrone_data_path, 'r') as f:
            return json.load(f)
    
    def calculate_scores(self) -> List[LocationScore]:
        """Calculate scores for each location based on isochrone data."""
        data = self.load_isochrone_data()
        
        for location in data:
            try:
                isochrone = location['isochrone_data']
                
                # Extract metrics from isochrone data - now correctly accessing nested properties
                properties = isochrone['features'][0]['properties']
                population = properties.get('total_pop', 0)
                area = properties.get('area', 0)
                reach_factor = properties.get('reachfactor', 0)
                
                # Normalize scores with adjusted factors based on actual data ranges
                population_score = min(population / 50000, 1.0)  # Normalize to 50k population
                area_score = min(area / 75000000, 1.0)  # Normalize to 75km²
                reach_factor_score = reach_factor
                
                # Calculate total score (weighted average)
                total_score = (
                    0.5 * population_score +  # Population weight: 50%
                    0.3 * area_score +        # Area weight: 30%
                    0.2 * reach_factor_score  # Reach factor weight: 20%
                )
                
                score = LocationScore(
                    branch_id=location['branch_id'],
                    branch_name=location['branch_name'],
                    branch_type=location['branch_type'],
                    city=location['city'],
                    population_coverage=population_score,
                    area_coverage=area_score,
                    reach_factor=reach_factor_score,
                    total_score=total_score
                )
                
                self.scores.append(score)
                
            except Exception as e:
                print(f"Error processing {location.get('branch_name', 'unknown')}: {str(e)}")
                continue
        
        return self.scores
    
    def save_scores(self, output_path: str):
        """Save the calculated scores to a CSV file."""
        # Convert scores to DataFrame
        scores_df = pd.DataFrame([
            {
                'branch_id': score.branch_id,
                'branch_name': score.branch_name,
                'branch_type': score.branch_type,
                'city': score.city,
                'population_coverage': score.population_coverage,
                'area_coverage': score.area_coverage,
                'reach_factor': score.reach_factor,
                'total_score': score.total_score
            }
            for score in self.scores
        ])
        
        # Save to CSV
        scores_df.to_csv(output_path, index=False)
        print(f"Scores saved to {output_path}")

def analyze_locations():
    """Main function to analyze and score locations."""
    # Create output directory if it doesn't exist
    os.makedirs('../output', exist_ok=True)
    
    # Initialize scorer
    scorer = LocationScorer('../output/isochrone_results.json')
    
    # Calculate scores
    scores = scorer.calculate_scores()
    
    # Save results
    output_path = '../output/location_scores.csv'
    scorer.save_scores(output_path)
    
    # Print summary statistics
    if scores:
        total_scores = [score.total_score for score in scores]
        print("\nSummary Statistics:")
        print(f"Number of locations analyzed: {len(scores)}")
        print(f"Average score: {np.mean(total_scores):.2f}")
        print(f"Minimum score: {min(total_scores):.2f}")
        print(f"Maximum score: {max(total_scores):.2f}")
        
        # Print top 5 locations
        print("\nAll Locations:")
        top_scores = sorted(scores, key=lambda x: x.total_score, reverse=True)[:20]
        for score in top_scores:
            print(f"{score.branch_name} ({score.city}): {score.total_score:.2f}")

if __name__ == "__main__":
    analyze_locations() 