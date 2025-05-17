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
    income_per_capita: float  # Average income in the municipality
    income_score: float  # Normalized income score
    pop_income_score: float  # Combined population-income relationship score
    branch_type_score: float  # Score based on branch type
    total_score: float

class LocationScorer:
    def __init__(self, isochrone_10min_path: str, isochrone_20min_path: str, income_data_path: str):
        self.isochrone_10min_path = isochrone_10min_path
        self.isochrone_20min_path = isochrone_20min_path
        self.income_data_path = income_data_path
        self.scores: List[LocationScore] = []
        
        # Constants for scoring
        self.INNER_RADIUS_MINUTES = 10
        self.OUTER_RADIUS_MINUTES = 20
        self.INNER_WEIGHT = 1.0
        self.OUTER_WEIGHT = 0.5  # Linear decay from inner to outer
        
        # Income scoring parameters
        self.MIN_INCOME = 25000  # Minimum income threshold
        self.MAX_INCOME = 90000  # Maximum income threshold for normalization
        self.INCOME_WEIGHT = 0.15  # Weight of income in final score
        
        # Population-income relationship parameters
        self.POP_INCOME_WEIGHT = 0.15  # Weight of population-income relationship in final score
        self.MIN_POP_DENSITY = 1000  # Minimum population density per km²
        self.MAX_POP_DENSITY = 10000  # Maximum population density per km²
        
        # Branch type scoring parameters
        self.BRANCH_TYPE_WEIGHT = 0.2  # Weight of branch type in final score
        self.BRANCH_TYPE_SCORES = {
            'M': 0.4,      # Small neighborhood stores
            'MM': 0.6,     # Medium-sized stores
            'MMM': 0.8,    # Large stores
            'MMMM': 0.9,   # Extra large stores
            'MMMM+': 1.0   # Flagship stores
        }
    
    def calculate_branch_type_score(self, branch_type: str) -> float:
        """Calculate score based on branch type."""
        # Clean and standardize branch type
        branch_type = branch_type.strip().upper()
        
        # Handle special cases
        if 'FLAGSHIP' in branch_type or 'FLAG' in branch_type:
            return self.BRANCH_TYPE_SCORES['MMMM+']
        
        # Get base score from mapping
        base_score = self.BRANCH_TYPE_SCORES.get(branch_type, 0.3)  # Default to 0.3 for unknown types
        
        # Additional bonus for special locations (e.g., train stations, airports)
        if any(keyword in branch_type.upper() for keyword in ['BAHN', 'SBB', 'AIRPORT', 'FLUGHAFEN']):
            base_score = min(base_score + 0.1, 1.0)
        
        return base_score
    
    def load_income_data(self) -> Dict[str, float]:
        """Load income data and create a municipality to income mapping."""
        df = pd.read_csv(self.income_data_path)
        # Create a mapping of municipality name to income
        return dict(zip(df['municipality'], df['income_per_capita']))
    
    def calculate_income_score(self, income: float) -> float:
        """Calculate normalized income score."""
        if pd.isna(income) or income < self.MIN_INCOME:
            return 0.0
        # Normalize income between MIN_INCOME and MAX_INCOME
        normalized = min(max((income - self.MIN_INCOME) / (self.MAX_INCOME - self.MIN_INCOME), 0), 1)
        return normalized
    
    def calculate_population_income_score(self, inner_pop: float, outer_pop: float, 
                                        area: float, income: float) -> float:
        """Calculate a combined score based on population density and income."""
        # Calculate population density (people per km²)
        total_pop = inner_pop + outer_pop
        if area <= 0:
            return 0.0
        
        pop_density = total_pop / (area / 1000000)  # Convert area from m² to km²
        
        # Normalize population density
        if pop_density < self.MIN_POP_DENSITY:
            density_score = 0.0
        elif pop_density > self.MAX_POP_DENSITY:
            density_score = 1.0
        else:
            density_score = (pop_density - self.MIN_POP_DENSITY) / (self.MAX_POP_DENSITY - self.MIN_POP_DENSITY)
        
        # Calculate income score
        income_score = self.calculate_income_score(income)
        
        # Combine scores using geometric mean to favor balanced scores
        # This means both high population density AND high income are needed for a good score
        combined_score = np.sqrt(density_score * income_score)
        
        return combined_score
    
    def load_isochrone_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Load both 10min and 20min isochrone data from JSON files."""
        with open(self.isochrone_10min_path, 'r') as f:
            data_10min = json.load(f)
        with open(self.isochrone_20min_path, 'r') as f:
            data_20min = json.load(f)
        return data_10min, data_20min
    
    def calculate_population_score(self, inner_pop: float, outer_pop: float) -> float:
        """Calculate population score using weighted inner and outer populations."""
        # Normalize populations (using 25k for inner and 50k for outer as reference)
        inner_score = min(inner_pop / 25000, 1.0) * self.INNER_WEIGHT
        outer_score = min(outer_pop / 50000, 1.0) * self.OUTER_WEIGHT
        
        # Combine scores (max possible is 1.0 + 0.5 = 1.5, so normalize to 1.0)
        return min((inner_score + outer_score) / 1.5, 1.0)
    
    def calculate_scores(self) -> List[LocationScore]:
        """Calculate scores for each location based on isochrone data."""
        data_10min, data_20min = self.load_isochrone_data()
        income_data = self.load_income_data()
        
        # Create lookup dictionaries for faster access
        data_10min_dict = {item['branch_id']: item for item in data_10min}
        data_20min_dict = {item['branch_id']: item for item in data_20min}
        
        # Process all unique branch IDs
        all_branch_ids = set(data_10min_dict.keys()) | set(data_20min_dict.keys())
        
        for branch_id in all_branch_ids:
            try:
                # Get data for both time ranges
                location_10min = data_10min_dict.get(branch_id)
                location_20min = data_20min_dict.get(branch_id)
                
                if not location_10min or not location_20min:
                    print(f"Skipping branch {branch_id}: Missing data for one or both time ranges")
                    continue
                
                # Extract metrics
                inner_pop = location_10min['isochrone_data']['features'][0]['properties'].get('total_pop', 0)
                total_pop_20min = location_20min['isochrone_data']['features'][0]['properties'].get('total_pop', 0)
                # Calculate outer ring population (20min area minus 10min area)
                outer_pop = max(0, total_pop_20min - inner_pop)
                
                # Get area and reach factor from 20min isochrone
                area = location_20min['isochrone_data']['features'][0]['properties'].get('area', 0)
                reach_factor = location_20min['isochrone_data']['features'][0]['properties'].get('reachfactor', 0)
                
                # Get income data for the municipality
                city = location_20min['city']
                income = income_data.get(city, 0)
                income_score = self.calculate_income_score(income)
                
                # Calculate population-income relationship score
                pop_income_score = self.calculate_population_income_score(
                    inner_pop, outer_pop, area, income
                )
                
                # Calculate branch type score
                branch_type = location_20min['branch_type']
                branch_type_score = self.calculate_branch_type_score(branch_type)
                
                # Calculate population score
                population_score = self.calculate_population_score(inner_pop, outer_pop)
                
                # Calculate area score
                area_score = min(area / 75000000, 1.0)  # Normalize to 75km²
                
                # Calculate total score (weighted average)
                total_score = (
                    0.25 * population_score +     # Population weight: 25%
                    0.2 * area_score +            # Area weight: 20%
                    0.1 * reach_factor +          # Reach factor weight: 10%
                    self.INCOME_WEIGHT * income_score +  # Income weight: 15%
                    self.POP_INCOME_WEIGHT * pop_income_score +  # Population-income weight: 15%
                    self.BRANCH_TYPE_WEIGHT * branch_type_score  # Branch type weight: 20%
                )
                
                score = LocationScore(
                    branch_id=branch_id,
                    branch_name=location_20min['branch_name'],
                    branch_type=branch_type,
                    city=city,
                    inner_population=inner_pop,
                    outer_population=outer_pop,
                    population_score=population_score,
                    area_coverage=area_score,
                    reach_factor=reach_factor,
                    income_per_capita=income,
                    income_score=income_score,
                    pop_income_score=pop_income_score,
                    branch_type_score=branch_type_score,
                    total_score=total_score
                )
                
                self.scores.append(score)
                
            except Exception as e:
                print(f"Error processing branch {branch_id}: {str(e)}")
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
                'income_per_capita': score.income_per_capita,
                'income_score': score.income_score,
                'pop_income_score': score.pop_income_score,
                'branch_type_score': score.branch_type_score,
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
    
    # Initialize scorer with both isochrone files and income data
    scorer = LocationScorer(
        '../output/isochrone_results_10min.json',
        '../output/isochrone_results_20min.json',
        '../output/processed_income_data.csv'
    )
    
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
            print(f"  Branch Type: {score.branch_type} (Score: {score.branch_type_score:.2f})")
            print(f"  Inner Population (0-10min): {score.inner_population:,.0f}")
            print(f"  Outer Population (10-20min): {score.outer_population:,.0f}")
            print(f"  Population Score: {score.population_score:.2f}")
            print(f"  Area Coverage: {score.area_coverage:.2f}")
            print(f"  Reach Factor: {score.reach_factor:.2f}")
            print(f"  Income per Capita: {score.income_per_capita:,.0f}")
            print(f"  Income Score: {score.income_score:.2f}")
            print(f"  Population-Income Score: {score.pop_income_score:.2f}")

if __name__ == "__main__":
    analyze_locations() 