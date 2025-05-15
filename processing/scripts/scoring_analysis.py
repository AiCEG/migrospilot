import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LocationScore:
    branch_id: str
    branch_name: str
    branch_type: str
    city: str
    inner_population: float  # 0-10 min population
    outer_population: float  # 10-20 min population
    population_score: float  # Combined weighted population score
    area_coverage: float
    reach_factor: float
    total_score: float

class LocationScorer:
    def __init__(self, isochrone_data_path: str):
        self.isochrone_data_path = isochrone_data_path
        self.scores: List[LocationScore] = []
        
        # Constants for scoring
        self.INNER_RADIUS_MINUTES = 10
        self.OUTER_RADIUS_MINUTES = 20
        self.INNER_WEIGHT = 1.0
        self.OUTER_WEIGHT = 0.5  # Linear decay from inner to outer
    
    def load_isochrone_data(self) -> List[Dict]:
        """Load the isochrone data from JSON file."""
        with open(self.isochrone_data_path, 'r') as f:
            return json.load(f)
    
    def calculate_population_score(self, inner_pop: float, outer_pop: float) -> float:
        """Calculate population score using weighted inner and outer populations."""
        # Normalize populations (using 25k for inner and 50k for outer as reference)
        inner_score = min(inner_pop / 25000, 1.0) * self.INNER_WEIGHT
        outer_score = min(outer_pop / 50000, 1.0) * self.OUTER_WEIGHT
        
        # Combine scores (max possible is 1.0 + 0.5 = 1.5, so normalize to 1.0)
        return min((inner_score + outer_score) / 1.5, 1.0)
    
    def calculate_scores(self) -> List[LocationScore]:
        """Calculate scores for each location based on isochrone data."""
        data = self.load_isochrone_data()
        
        for location in data:
            try:
                # Get both 10min and 20min isochrone data
                isochrone_10min = location['isochrone_data_10min']['features'][0]['properties']
                isochrone_20min = location['isochrone_data_20min']['features'][0]['properties']
                
                # Extract metrics
                inner_pop = isochrone_10min.get('total_pop', 0)
                total_pop_20min = isochrone_20min.get('total_pop', 0)
                # Calculate outer ring population (20min area minus 10min area)
                outer_pop = max(0, total_pop_20min - inner_pop)
                
                # Get area and reach factor from 20min isochrone
                area = isochrone_20min.get('area', 0)
                reach_factor = isochrone_20min.get('reachfactor', 0)
                
                # Calculate population score
                population_score = self.calculate_population_score(inner_pop, outer_pop)
                
                # Calculate area score
                area_score = min(area / 75000000, 1.0)  # Normalize to 75km²
                
                # Calculate total score (weighted average)
                total_score = (
                    0.5 * population_score +  # Population weight: 50%
                    0.3 * area_score +        # Area weight: 30%
                    0.2 * reach_factor        # Reach factor weight: 20%
                )
                
                score = LocationScore(
                    branch_id=location['branch_id'],
                    branch_name=location['branch_name'],
                    branch_type=location['branch_type'],
                    city=location['city'],
                    inner_population=inner_pop,
                    outer_population=outer_pop,
                    population_score=population_score,
                    area_coverage=area_score,
                    reach_factor=reach_factor,
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
                'inner_population': score.inner_population,
                'outer_population': score.outer_population,
                'population_score': score.population_score,
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
        
        # Print top 20 locations with detailed scores
        print("\nTop 20 Locations:")
        top_scores = sorted(scores, key=lambda x: x.total_score, reverse=True)[:20]
        for score in top_scores:
            print(f"\n{score.branch_name} ({score.city}):")
            print(f"  Total Score: {score.total_score:.2f}")
            print(f"  Inner Population (0-10min): {score.inner_population:,.0f}")
            print(f"  Outer Population (10-20min): {score.outer_population:,.0f}")
            print(f"  Population Score: {score.population_score:.2f}")
            print(f"  Area Coverage: {score.area_coverage:.2f}")
            print(f"  Reach Factor: {score.reach_factor:.2f}")

if __name__ == "__main__":
    analyze_locations() 