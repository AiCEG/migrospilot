import pandas as pd
import folium
from folium.plugins import HeatMap, FeatureGroupSubGroup
import branca.colormap as cm
import os
import json
import geopandas as gpd
from shapely.geometry import shape
import numpy as np

# Color mapping for branch types
BRANCH_COLORS = {
    'M': '#FF5733',    # Orange
    'MM': '#33FF57',   # Green
    'MMM': '#3357FF',  # Blue
    'VOI': '#F333FF'   # Purple
}

# Helper to load and merge data
def load_data():
    scores_df = pd.read_csv('../output/location_scores.csv')
    geo_df = pd.read_csv('../output/geospatial_branches_data.csv')
    
    # Load isochrone data
    with open('../output/isochrone_results_10min.json', 'r') as f:
        isochrone_10min = json.load(f)
    with open('../output/isochrone_results_20min.json', 'r') as f:
        isochrone_20min = json.load(f)
    
    # Create lookup dictionaries for isochrone data
    isochrone_10min_dict = {item['branch_id']: item for item in isochrone_10min}
    isochrone_20min_dict = {item['branch_id']: item for item in isochrone_20min}
    
    # Merge data
    merged_df = pd.merge(
        scores_df,
        geo_df[['id', 'latitude', 'longitude']],
        left_on='branch_id',
        right_on='id',
        how='left'
    )
    
    # Add isochrone data to merged dataframe
    merged_df['isochrone_10min'] = merged_df['branch_id'].map(lambda x: isochrone_10min_dict.get(x, {}).get('isochrone_data', {}))
    merged_df['isochrone_20min'] = merged_df['branch_id'].map(lambda x: isochrone_20min_dict.get(x, {}).get('isochrone_data', {}))
    
    return merged_df

# Helper to load selected branch IDs
def load_selected_branch_ids():
    output_dir = '../output/pilot_analysis'
    try:
        with open(os.path.join(output_dir, 'selected_branches.json'), 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def generate_heatmap_points(geometry, population, num_points=100):
    """Generate points within a geometry for heatmap visualization."""
    if not geometry:
        return []
    
    # Convert to shapely geometry if it's a dict
    if isinstance(geometry, dict):
        geometry = shape(geometry)
    
    # Get bounds
    minx, miny, maxx, maxy = geometry.bounds
    
    points = []
    attempts = 0
    max_attempts = num_points * 10  # Allow more attempts to ensure we get enough points
    
    while len(points) < num_points and attempts < max_attempts:
        # Generate random point within bounds
        x = np.random.uniform(minx, maxx)
        y = np.random.uniform(miny, maxy)
        
        # Check if point is within geometry
        if geometry.contains(shape({'type': 'Point', 'coordinates': [x, y]})):
            points.append([y, x, population / num_points])  # Note: folium uses [lat, lon]
        
        attempts += 1
    
    return points

def create_combined_map():
    output_dir = '../output/pilot_analysis'
    os.makedirs(output_dir, exist_ok=True)
    merged_df = load_data()
    selected_ids = load_selected_branch_ids()
    if selected_ids:
        selected_branches = merged_df[merged_df['branch_id'].isin(selected_ids)]
    else:
        selected_branches = merged_df

    # Create base map
    m = folium.Map(location=[46.8182, 8.2275], zoom_start=8, control_scale=True)

    # Colormaps
    score_colormap = cm.LinearColormap(['red', 'yellow', 'green'], vmin=selected_branches['total_score'].min(), vmax=selected_branches['total_score'].max(), caption='Total Score')
    income_colormap = cm.LinearColormap(['blue', 'green', 'yellow', 'red'], vmin=selected_branches['income_per_capita'].min(), vmax=selected_branches['income_per_capita'].max(), caption='Income per Capita')

    # Feature groups for toggling
    fg_branches = folium.FeatureGroup(name='Pilot Branches', show=True)
    fg_service_areas = folium.FeatureGroup(name='Service Areas', show=True)
    fg_heatmap = folium.FeatureGroup(name='Population Coverage Heatmap', show=False)
    fg_income = folium.FeatureGroup(name='Income Distribution', show=False)

    # Branch markers and service areas
    heatmap_data = []
    for _, branch in selected_branches.iterrows():
        popup_text = f"""
        <b>{branch['branch_name']}</b><br>
        Type: {branch['branch_type']}<br>
        Score: {branch['total_score']:.2f}<br>
        Population (10min): {branch['inner_population']:.0f}<br>
        Population (20min): {branch['outer_population']:.0f}<br>
        Income: {branch['income_per_capita']:.0f} CHF
        """
        
        # Add branch marker
        folium.CircleMarker(
            location=[branch['latitude'], branch['longitude']],
            radius=8,
            color=BRANCH_COLORS.get(branch['branch_type'], 'gray'),
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(fg_branches)

        # Add service areas using actual isochrone data
        if branch['isochrone_20min'] and 'features' in branch['isochrone_20min']:
            # 20-minute service area
            geometry_20min = shape(branch['isochrone_20min']['features'][0]['geometry'])
            folium.GeoJson(
                geometry_20min.__geo_interface__,
                style_function=lambda x: {
                    'fillColor': BRANCH_COLORS.get(branch['branch_type'], 'gray'),
                    'color': BRANCH_COLORS.get(branch['branch_type'], 'gray'),
                    'fillOpacity': 0.08,
                    'weight': 1
                }
            ).add_to(fg_service_areas)
            
            # Add heatmap points for outer area (20min - 10min)
            if branch['isochrone_10min'] and 'features' in branch['isochrone_10min']:
                geometry_10min = shape(branch['isochrone_10min']['features'][0]['geometry'])
                outer_geometry = geometry_20min.difference(geometry_10min)
                outer_population = branch['outer_population'] - branch['inner_population']
                heatmap_data.extend(generate_heatmap_points(outer_geometry, outer_population, num_points=50))

        if branch['isochrone_10min'] and 'features' in branch['isochrone_10min']:
            # 10-minute service area
            geometry_10min = shape(branch['isochrone_10min']['features'][0]['geometry'])
            folium.GeoJson(
                geometry_10min.__geo_interface__,
                style_function=lambda x: {
                    'fillColor': BRANCH_COLORS.get(branch['branch_type'], 'gray'),
                    'color': BRANCH_COLORS.get(branch['branch_type'], 'gray'),
                    'fillOpacity': 0.18,
                    'weight': 2
                }
            ).add_to(fg_service_areas)
            
            # Add heatmap points for inner area (10min)
            heatmap_data.extend(generate_heatmap_points(geometry_10min, branch['inner_population'], num_points=100))

        # Income distribution using actual service areas
        if branch['isochrone_20min'] and 'features' in branch['isochrone_20min']:
            # 20-minute service area with income color
            geometry_20min = shape(branch['isochrone_20min']['features'][0]['geometry'])
            folium.GeoJson(
                geometry_20min.__geo_interface__,
                style_function=lambda x: {
                    'fillColor': income_colormap(branch['income_per_capita']),
                    'color': income_colormap(branch['income_per_capita']),
                    'fillOpacity': 0.15,
                    'weight': 1
                }
            ).add_to(fg_income)

            # 10-minute service area with higher opacity
            if branch['isochrone_10min'] and 'features' in branch['isochrone_10min']:
                geometry_10min = shape(branch['isochrone_10min']['features'][0]['geometry'])
                folium.GeoJson(
                    geometry_10min.__geo_interface__,
                    style_function=lambda x: {
                        'fillColor': income_colormap(branch['income_per_capita']),
                        'color': income_colormap(branch['income_per_capita']),
                        'fillOpacity': 0.3,
                        'weight': 1
                    }
                ).add_to(fg_income)

    # Add population coverage heatmap
    HeatMap(heatmap_data, radius=15, blur=10, min_opacity=0.3).add_to(fg_heatmap)

    # Add feature groups to map
    fg_branches.add_to(m)
    fg_service_areas.add_to(m)
    fg_heatmap.add_to(m)
    fg_income.add_to(m)

    # Add colormaps/legends
    score_colormap.add_to(m)
    income_colormap.add_to(m)

    # Branch type legend
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; padding: 10px; border: 2px solid grey; border-radius: 5px">
    <p><strong>Branch Types</strong></p>
    """
    for branch_type, color in BRANCH_COLORS.items():
        legend_html += f'<p><span style="color:{color}">●</span> {branch_type}</p>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

    # Layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Save map
    m.save(os.path.join(output_dir, 'combined_pilot_map.html'))
    print(f"Combined map saved to {output_dir}/combined_pilot_map.html")

if __name__ == "__main__":
    create_combined_map() 