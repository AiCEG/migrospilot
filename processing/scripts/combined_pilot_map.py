import pandas as pd
import folium
from folium.plugins import HeatMap, FeatureGroupSubGroup
import branca.colormap as cm
import os
import json

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
    geo_df['radius_10min'] = 2.5  # km
    geo_df['radius_20min'] = 5.0  # km
    merged_df = pd.merge(
        scores_df,
        geo_df[['id', 'latitude', 'longitude', 'radius_10min', 'radius_20min']],
        left_on='branch_id',
        right_on='id',
        how='left'
    )
    return merged_df

# Helper to load selected branch IDs
def load_selected_branch_ids():
    output_dir = '../output/pilot_analysis'
    try:
        with open(os.path.join(output_dir, 'selected_branches.json'), 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

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

    # Branch markers
    for _, branch in selected_branches.iterrows():
        popup_text = f"""
        <b>{branch['branch_name']}</b><br>
        Type: {branch['branch_type']}<br>
        Score: {branch['total_score']:.2f}<br>
        Population (10min): {branch['inner_population']:.0f}<br>
        Population (20min): {branch['outer_population']:.0f}<br>
        Income: {branch['income_per_capita']:.0f} CHF
        """
        folium.CircleMarker(
            location=[branch['latitude'], branch['longitude']],
            radius=8,
            color=BRANCH_COLORS.get(branch['branch_type'], 'gray'),
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(fg_branches)

        # Service areas
        folium.Circle(
            location=[branch['latitude'], branch['longitude']],
            radius=branch['radius_20min'] * 1000,
            color=BRANCH_COLORS.get(branch['branch_type'], 'gray'),
            fill=True,
            fill_opacity=0.08,
            weight=1
        ).add_to(fg_service_areas)
        folium.Circle(
            location=[branch['latitude'], branch['longitude']],
            radius=branch['radius_10min'] * 1000,
            color=BRANCH_COLORS.get(branch['branch_type'], 'gray'),
            fill=True,
            fill_opacity=0.18,
            weight=2
        ).add_to(fg_service_areas)

        # Income overlay (inner area)
        folium.Circle(
            location=[branch['latitude'], branch['longitude']],
            radius=branch['radius_10min'] * 1000,
            color=income_colormap(branch['income_per_capita']),
            fill=True,
            fill_opacity=0.25,
            weight=0.5
        ).add_to(fg_income)

    # Population coverage heatmap
    heat_data = []
    for _, branch in selected_branches.iterrows():
        heat_data.extend([
            [branch['latitude'], branch['longitude'], branch['inner_population']]
            for _ in range(10)
        ])
        heat_data.extend([
            [branch['latitude'], branch['longitude'], branch['outer_population'] * 0.5]
            for _ in range(5)
        ])
    HeatMap(heat_data, radius=15, blur=10, min_opacity=0.3).add_to(fg_heatmap)

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