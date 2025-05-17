import pandas as pd
import folium
from folium.plugins import HeatMap
import branca.colormap as cm
from geopy.distance import geodesic
import numpy as np
import os
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json

@dataclass
class ServiceArea:
    inner_radius: float  # 10 minutes in km
    outer_radius: float  # 20 minutes in km
    inner_population: float
    outer_population: float
    inner_income: float
    outer_income: float

class PilotAreaVisualizer:
    def __init__(self):
        self.colors = {
            'M': '#FF5733',    # Orange
            'MM': '#33FF57',   # Green
            'MMM': '#3357FF',  # Blue
            'VOI': '#F333FF'   # Purple
        }
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load scoring and geospatial data."""
        scores_df = pd.read_csv('../output/location_scores.csv')
        geo_df = pd.read_csv('../output/geospatial_branches_data.csv')
        
        # Calculate inner and outer radii (assuming average cycling speed of 15 km/h)
        # 10 minutes = 2.5 km, 20 minutes = 5 km
        geo_df['radius_10min'] = 2.5  # km
        geo_df['radius_20min'] = 5.0  # km
        
        # Merge data
        merged_df = pd.merge(
            scores_df,
            geo_df[['id', 'latitude', 'longitude', 'radius_10min', 'radius_20min']],
            left_on='branch_id',
            right_on='id',
            how='left'
        )
        
        return merged_df, geo_df
    
    def create_service_area_map(self, selected_branches: pd.DataFrame, output_dir: str):
        """Create an interactive map showing service areas of selected branches."""
        # Create base map centered on Switzerland
        m = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
        
        # Create colormap for scores
        score_colormap = cm.LinearColormap(
            colors=['red', 'yellow', 'green'],
            vmin=selected_branches['total_score'].min(),
            vmax=selected_branches['total_score'].max()
        )
        score_colormap.add_to(m)
        
        # Add each branch and its service areas
        for _, branch in selected_branches.iterrows():
            # Create popup with branch information
            popup_text = f"""
            <b>{branch['branch_name']}</b><br>
            Type: {branch['branch_type']}<br>
            Score: {branch['total_score']:.2f}<br>
            Population (10min): {branch['inner_population']:.0f}<br>
            Population (20min): {branch['outer_population']:.0f}<br>
            Income: {branch['income_per_capita']:.0f} CHF
            """
            
            # Add inner service area (10min)
            folium.Circle(
                location=[branch['latitude'], branch['longitude']],
                radius=branch['radius_10min'] * 1000,  # Convert to meters
                color=self.colors.get(branch['branch_type'], 'gray'),
                fill=True,
                fill_opacity=0.2,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
            
            # Add outer service area (20min)
            folium.Circle(
                location=[branch['latitude'], branch['longitude']],
                radius=branch['radius_20min'] * 1000,  # Convert to meters
                color=self.colors.get(branch['branch_type'], 'gray'),
                fill=True,
                fill_opacity=0.1,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
            
            # Add branch marker
            folium.CircleMarker(
                location=[branch['latitude'], branch['longitude']],
                radius=8,
                color=self.colors.get(branch['branch_type'], 'gray'),
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Save the map
        m.save(os.path.join(output_dir, 'pilot_service_areas.html'))
    
    def create_coverage_heatmap(self, selected_branches: pd.DataFrame, output_dir: str):
        """Create a heatmap showing population coverage."""
        m = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
        
        # Create heatmap data
        heat_data = []
        for _, branch in selected_branches.iterrows():
            # Add points for inner radius with higher weight
            heat_data.extend([
                [branch['latitude'], branch['longitude'], branch['inner_population']]
                for _ in range(10)  # More points for inner radius
            ])
            # Add points for outer radius with lower weight
            heat_data.extend([
                [branch['latitude'], branch['longitude'], branch['outer_population'] * 0.5]
                for _ in range(5)  # Fewer points for outer radius
            ])
        
        # Add heatmap layer
        HeatMap(heat_data, radius=15, blur=10).add_to(m)
        
        # Save the map
        m.save(os.path.join(output_dir, 'pilot_coverage_heatmap.html'))
    
    def create_income_distribution_map(self, selected_branches: pd.DataFrame, output_dir: str):
        """Create a map showing income distribution in service areas."""
        m = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
        
        # Create colormap for income levels
        income_colormap = cm.LinearColormap(
            colors=['blue', 'green', 'yellow', 'red'],
            vmin=selected_branches['income_per_capita'].min(),
            vmax=selected_branches['income_per_capita'].max()
        )
        income_colormap.add_to(m)
        
        # Add each branch with income-based coloring
        for _, branch in selected_branches.iterrows():
            popup_text = f"""
            <b>{branch['branch_name']}</b><br>
            Income: {branch['income_per_capita']:.0f} CHF<br>
            Population: {branch['inner_population']:.0f}
            """
            
            folium.Circle(
                location=[branch['latitude'], branch['longitude']],
                radius=branch['radius_10min'] * 1000,
                color=income_colormap(branch['income_per_capita']),
                fill=True,
                fill_opacity=0.3,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
        
        # Save the map
        m.save(os.path.join(output_dir, 'pilot_income_distribution.html'))
    
    def create_branch_type_map(self, selected_branches: pd.DataFrame, output_dir: str):
        """Create a map showing distribution of branch types."""
        m = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
        
        # Add each branch with type-based coloring
        for _, branch in selected_branches.iterrows():
            popup_text = f"""
            <b>{branch['branch_name']}</b><br>
            Type: {branch['branch_type']}<br>
            Score: {branch['total_score']:.2f}
            """
            
            folium.CircleMarker(
                location=[branch['latitude'], branch['longitude']],
                radius=10,
                color=self.colors.get(branch['branch_type'], 'gray'),
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
        
        # Add legend
        legend_html = """
        <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; padding: 10px; border: 2px solid grey; border-radius: 5px">
        <p><strong>Branch Types</strong></p>
        """
        for branch_type, color in self.colors.items():
            legend_html += f'<p><span style="color:{color}">●</span> {branch_type}</p>'
        legend_html += '</div>'
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Save the map
        m.save(os.path.join(output_dir, 'pilot_branch_types.html'))

def main():
    # Create output directory
    output_dir = '../output/pilot_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize visualizer
    visualizer = PilotAreaVisualizer()
    
    # Load data
    print("Loading branch data...")
    merged_df, _ = visualizer.load_data()
    
    # Load selected branches from pilot selection
    try:
        with open(os.path.join(output_dir, 'selected_branches.json'), 'r') as f:
            selected_branch_ids = json.load(f)
        selected_branches = merged_df[merged_df['branch_id'].isin(selected_branch_ids)]
    except FileNotFoundError:
        print("No selected branches found. Using all branches for visualization.")
        selected_branches = merged_df
    
    # Create visualizations
    print("Creating service area map...")
    visualizer.create_service_area_map(selected_branches, output_dir)
    
    print("Creating coverage heatmap...")
    visualizer.create_coverage_heatmap(selected_branches, output_dir)
    
    print("Creating income distribution map...")
    visualizer.create_income_distribution_map(selected_branches, output_dir)
    
    print("Creating branch type map...")
    visualizer.create_branch_type_map(selected_branches, output_dir)
    
    print(f"\nVisualizations saved to {output_dir}/")
    print("Generated files:")
    print("- pilot_service_areas.html")
    print("- pilot_coverage_heatmap.html")
    print("- pilot_income_distribution.html")
    print("- pilot_branch_types.html")

if __name__ == "__main__":
    main() 