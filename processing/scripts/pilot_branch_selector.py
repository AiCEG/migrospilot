import pandas as pd
import numpy as np
from collections import Counter
from typing import List, Dict, Tuple
import folium
from folium.plugins import HeatMap
import branca.colormap as cm
from geopy.distance import geodesic
import random
from dataclasses import dataclass
import os
import json

@dataclass
class Branch:
    branch_id: int
    branch_name: str
    branch_type: str
    city: str
    latitude: float
    longitude: float
    inner_population: float
    outer_population: float
    income_per_capita: float
    total_score: float

class PilotBranchSelector:
    def __init__(self, num_branches: int, min_distance_km: float = 10.0):
        self.num_branches = num_branches
        self.min_distance_km = min_distance_km
        self.regions = {
            'north': {'lat': (47.5, 48.0), 'lon': (8.0, 9.0)},
            'east': {'lat': (47.0, 47.5), 'lon': (9.0, 10.0)},
            'south': {'lat': (46.0, 47.0), 'lon': (8.0, 9.0)},
            'west': {'lat': (47.0, 47.5), 'lon': (7.0, 8.0)},
            'central': {'lat': (46.5, 47.0), 'lon': (7.0, 8.0)}
        }
    
    def load_data(self) -> List[Branch]:
        """Load and prepare branch data."""
        # Load scoring data
        scores_df = pd.read_csv('../output/location_scores.csv')
        
        # Load geospatial data
        geo_df = pd.read_csv('../output/geospatial_branches_data.csv')
        
        # Merge data
        merged_df = pd.merge(
            scores_df,
            geo_df[['id', 'latitude', 'longitude']],
            left_on='branch_id',
            right_on='id',
            how='left'
        )
        
        # Convert to Branch objects
        branches = []
        for _, row in merged_df.iterrows():
            if pd.isna(row['latitude']) or pd.isna(row['longitude']):
                continue
                
            branch = Branch(
                branch_id=row['branch_id'],
                branch_name=row['branch_name'],
                branch_type=row['branch_type'],
                city=row['city'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                inner_population=row['inner_population'],
                outer_population=row['outer_population'],
                income_per_capita=row['income_per_capita'],
                total_score=row['total_score']
            )
            branches.append(branch)
            
        return branches
    
    def calculate_distance(self, branch1: Branch, branch2: Branch) -> float:
        """Calculate distance between two branches in kilometers."""
        return geodesic(
            (branch1.latitude, branch1.longitude),
            (branch2.latitude, branch2.longitude)
        ).kilometers
    
    def get_region(self, branch: Branch) -> str:
        """Determine the region of a branch based on coordinates."""
        for region, bounds in self.regions.items():
            if (bounds['lat'][0] <= branch.latitude <= bounds['lat'][1] and
                bounds['lon'][0] <= branch.longitude <= bounds['lon'][1]):
                return region
        return 'other'
    
    def calculate_coverage_score(self, selected_branches: List[Branch]) -> float:
        """Calculate population coverage score with overlap penalty."""
        total_population = 0
        overlap_penalty = 0
        
        # Calculate population coverage
        for branch in selected_branches:
            total_population += branch.inner_population
            # Add outer population with distance-based weighting
            total_population += branch.outer_population * 0.5
        
        # Calculate overlap penalty
        for i, branch1 in enumerate(selected_branches):
            for branch2 in selected_branches[i+1:]:
                distance = self.calculate_distance(branch1, branch2)
                if distance < self.min_distance_km:
                    overlap_penalty += (self.min_distance_km - distance) * 1000
        
        return total_population - overlap_penalty
    
    def calculate_diversity_score(self, selected_branches: List[Branch]) -> float:
        """Calculate diversity score based on branch types and regions."""
        # Branch type diversity
        type_counts = Counter(b.branch_type for b in selected_branches)
        type_diversity = 1 - (max(type_counts.values()) / len(selected_branches))
        
        # Geographic spread
        regions = set(self.get_region(b) for b in selected_branches)
        region_diversity = len(regions) / len(self.regions)
        
        # Income level diversity
        income_levels = [b.income_per_capita for b in selected_branches]
        income_diversity = 1 - (np.std(income_levels) / np.mean(income_levels))
        
        return (type_diversity + region_diversity + income_diversity) / 3
    
    def calculate_performance_score(self, selected_branches: List[Branch]) -> float:
        """Calculate average performance score of selected branches."""
        return np.mean([b.total_score for b in selected_branches])
    
    def evaluate_fitness(self, selected_branches: List[Branch]) -> float:
        """Evaluate the fitness of a combination of branches."""
        coverage_score = self.calculate_coverage_score(selected_branches)
        diversity_score = self.calculate_diversity_score(selected_branches)
        performance_score = self.calculate_performance_score(selected_branches)
        
        return (0.4 * coverage_score + 
                0.3 * diversity_score + 
                0.3 * performance_score)
    
    def initialize_population(self, all_branches: List[Branch], 
                            population_size: int) -> List[List[Branch]]:
        """Initialize population for genetic algorithm."""
        population = []
        for _ in range(population_size):
            individual = random.sample(all_branches, self.num_branches)
            population.append(individual)
        return population
    
    def select_parents(self, population: List[List[Branch]], 
                      fitness_scores: List[float]) -> List[List[Branch]]:
        """Select parents for next generation using tournament selection."""
        parents = []
        for _ in range(len(population)):
            # Tournament selection
            tournament = random.sample(list(zip(population, fitness_scores)), 3)
            winner = max(tournament, key=lambda x: x[1])[0]
            parents.append(winner)
        return parents
    
    def crossover(self, parent1: List[Branch], parent2: List[Branch]) -> Tuple[List[Branch], List[Branch]]:
        """Perform crossover between two parents."""
        # Single point crossover
        point = random.randint(1, self.num_branches - 1)
        child1 = parent1[:point] + [b for b in parent2 if b not in parent1[:point]]
        child2 = parent2[:point] + [b for b in parent1 if b not in parent2[:point]]
        return child1[:self.num_branches], child2[:self.num_branches]
    
    def mutate(self, individual: List[Branch], all_branches: List[Branch]) -> List[Branch]:
        """Mutate an individual by replacing a random branch."""
        if random.random() < 0.1:  # 10% mutation rate
            idx = random.randint(0, len(individual) - 1)
            new_branch = random.choice([b for b in all_branches if b not in individual])
            individual[idx] = new_branch
        return individual
    
    def find_optimal_combination(self, all_branches: List[Branch]) -> List[Branch]:
        """Find the optimal combination of branches using genetic algorithm."""
        population_size = 100
        generations = 50
        
        # Initialize population
        population = self.initialize_population(all_branches, population_size)
        
        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = [self.evaluate_fitness(individual) 
                            for individual in population]
            
            # Select parents
            parents = self.select_parents(population, fitness_scores)
            
            # Create new generation
            new_population = []
            for i in range(0, len(parents), 2):
                child1, child2 = self.crossover(parents[i], parents[i+1])
                new_population.extend([
                    self.mutate(child1, all_branches),
                    self.mutate(child2, all_branches)
                ])
            
            population = new_population
        
        # Return best solution
        return max(population, key=self.evaluate_fitness)
    
    def visualize_selection(self, selected_branches: List[Branch], output_dir: str):
        """Create visualizations for the selected branches."""
        # Create base map
        m = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
        
        # Add selected branches
        for branch in selected_branches:
            popup_text = f"""
            <b>{branch.branch_name}</b><br>
            Type: {branch.branch_type}<br>
            Score: {branch.total_score:.2f}<br>
            Population (10min): {branch.inner_population:.0f}<br>
            Population (20min): {branch.outer_population:.0f}<br>
            Income: {branch.income_per_capita:.0f} CHF
            """
            
            folium.CircleMarker(
                location=[branch.latitude, branch.longitude],
                radius=8,
                popup=folium.Popup(popup_text, max_width=300),
                color='red',
                fill=True,
                fill_opacity=0.7
            ).add_to(m)
        
        # Save the map
        m.save(os.path.join(output_dir, 'pilot_branches.html'))
        
        # Create summary statistics
        stats = {
            'Total Population Reached': sum(b.inner_population for b in selected_branches),
            'Average Score': np.mean([b.total_score for b in selected_branches]),
            'Branch Types': Counter(b.branch_type for b in selected_branches),
            'Regions': Counter(self.get_region(b) for b in selected_branches),
            'Average Income': np.mean([b.income_per_capita for b in selected_branches])
        }
        
        return stats

def main():
    # Create output directory
    output_dir = '../output/pilot_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize selector
    selector = PilotBranchSelector(num_branches=10)  # Adjust number as needed
    
    # Load data
    print("Loading branch data...")
    branches = selector.load_data()
    
    # Find optimal combination
    print("Finding optimal branch combination...")
    selected_branches = selector.find_optimal_combination(branches)
    
    # Save selected branch IDs
    selected_branch_ids = [branch.branch_id for branch in selected_branches]
    with open(os.path.join(output_dir, 'selected_branches.json'), 'w') as f:
        json.dump(selected_branch_ids, f)
    
    # Visualize results
    print("Creating visualizations...")
    stats = selector.visualize_selection(selected_branches, output_dir)
    
    # Print summary
    print("\nSelected Branches:")
    for branch in selected_branches:
        print(f"- {branch.branch_name} ({branch.branch_type})")
    
    print("\nSummary Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main() 