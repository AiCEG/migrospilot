import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import folium
from folium.plugins import HeatMap
import branca.colormap as cm

def load_scores(file_path: str) -> pd.DataFrame:
    """Load the scoring results from CSV."""
    scores_df = pd.read_csv(file_path)
    
    # Load geospatial data
    geospatial_df = pd.read_csv('../output/geospatial_branches_data.csv')
    
    # Merge the dataframes
    merged_df = pd.merge(
        scores_df,
        geospatial_df[['id', 'latitude', 'longitude']],
        left_on='branch_id',
        right_on='id',
        how='left'
    )
    
    return merged_df

def create_score_distribution_plot(df: pd.DataFrame, output_dir: str):
    """Create a distribution plot of total scores."""
    plt.figure(figsize=(12, 6))
    sns.histplot(data=df, x='total_score', bins=30)
    plt.title('Distribution of Location Scores')
    plt.xlabel('Total Score')
    plt.ylabel('Number of Locations')
    plt.savefig(os.path.join(output_dir, 'score_distribution.png'))
    plt.close()

def create_score_components_plot(df: pd.DataFrame, output_dir: str):
    """Create a box plot of individual score components."""
    score_components = [
        'population_score', 'area_coverage', 'reach_factor',
        'income_score', 'pop_income_score', 'total_score'
    ]
    
    plt.figure(figsize=(15, 8))
    df_melted = pd.melt(df[score_components])
    sns.boxplot(data=df_melted, x='variable', y='value')
    plt.title('Distribution of Score Components')
    plt.xlabel('Score Component')
    plt.ylabel('Score Value')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'score_components.png'))
    plt.close()

def create_branch_type_analysis(df: pd.DataFrame, output_dir: str):
    """Create visualizations for branch type analysis."""
    # Average scores by branch type
    plt.figure(figsize=(12, 6))
    branch_type_means = df.groupby('branch_type')['total_score'].mean().sort_values(ascending=False)
    sns.barplot(x=branch_type_means.index, y=branch_type_means.values)
    plt.title('Average Scores by Branch Type')
    plt.xlabel('Branch Type')
    plt.ylabel('Average Score')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'branch_type_scores.png'))
    plt.close()
    
    # Branch type distribution
    plt.figure(figsize=(10, 6))
    df['branch_type'].value_counts().plot(kind='pie', autopct='%1.1f%%')
    plt.title('Distribution of Branch Types')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'branch_type_distribution.png'))
    plt.close()

def create_correlation_heatmap(df: pd.DataFrame, output_dir: str):
    """Create a correlation heatmap of score components."""
    score_components = [
        'population_score', 'area_coverage', 'reach_factor',
        'income_score', 'pop_income_score', 'total_score'
    ]
    
    plt.figure(figsize=(12, 10))
    correlation_matrix = df[score_components].corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0)
    plt.title('Correlation between Score Components')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'score_correlations.png'))
    plt.close()

def create_top_locations_analysis(df: pd.DataFrame, output_dir: str):
    """Create visualizations for top scoring locations."""
    # Get top 20 locations
    top_20 = df.nlargest(20, 'total_score')
    
    # Create radar chart for top 5 locations
    score_components = [
        'population_score', 'area_coverage', 'reach_factor',
        'income_score', 'pop_income_score'
    ]
    
    # Number of variables
    N = len(score_components)
    
    # Create angle for each component
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop
    
    # Create figure
    fig, ax = plt.subplots(figsize=(15, 15), subplot_kw=dict(projection='polar'))
    
    # Plot top 5 locations
    for i, (_, location) in enumerate(top_20.head(5).iterrows()):
        values = location[score_components].values
        values = np.concatenate((values, [values[0]]))  # Close the loop
        
        ax.plot(angles, values, linewidth=2, label=location['branch_name'])
        ax.fill(angles, values, alpha=0.1)
    
    # Set labels
    plt.xticks(angles[:-1], score_components)
    plt.ylim(0, 1)
    plt.title('Score Components for Top 5 Locations')
    plt.legend(loc='upper right', bbox_to_anchor=(0.3, 0.3))
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'top_locations_radar.png'))
    plt.close()
    
    # Create bar chart of top 20 locations
    plt.figure(figsize=(15, 8))
    sns.barplot(data=top_20, x='branch_name', y='total_score')
    plt.title('Top 20 Scoring Locations')
    plt.xlabel('Branch Name')
    plt.ylabel('Total Score')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'top_20_locations.png'))
    plt.close()

def create_income_population_analysis(df: pd.DataFrame, output_dir: str):
    """Create visualizations for income and population analysis."""
    # Scatter plot of income vs population
    plt.figure(figsize=(12, 8))
    sns.scatterplot(data=df, x='inner_population', y='income_per_capita', 
                   hue='total_score', size='total_score', sizes=(20, 200))
    plt.title('Income vs Population (Inner Ring)')
    plt.xlabel('Inner Population (0-10 min)')
    plt.ylabel('Income per Capita')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'income_vs_population.png'))
    plt.close()
    
    # Population distribution by branch type
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='branch_type', y='inner_population')
    plt.title('Population Distribution by Branch Type')
    plt.xlabel('Branch Type')
    plt.ylabel('Inner Population (0-10 min)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'population_by_branch_type.png'))
    plt.close()

def create_geographic_analysis(df: pd.DataFrame, output_dir: str):
    """Create geographic visualizations of branch locations and scores."""
    # Create a base map centered on Switzerland
    m = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
    
    # Create a colormap for the scores
    colormap = cm.LinearColormap(
        colors=['red', 'yellow', 'green'],
        vmin=df['total_score'].min(),
        vmax=df['total_score'].max()
    )
    
    # Add branch locations with popups
    for _, row in df.iterrows():
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue
            
        popup_text = f"""
        <b>{row['branch_name']}</b><br>
        Type: {row['branch_type']}<br>
        Score: {row['total_score']:.2f}<br>
        Population (10min): {row['inner_population']:.0f}<br>
        Population (20min): {row['outer_population']:.0f}<br>
        Income: {row['income_per_capita']:.0f} CHF
        """
        
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=8,
            popup=folium.Popup(popup_text, max_width=300),
            color=colormap(row['total_score']),
            fill=True,
            fill_color=colormap(row['total_score']),
            fill_opacity=0.7
        ).add_to(m)
    
    # Add the colormap to the map
    colormap.add_to(m)
    
    # Save the map
    m.save(os.path.join(output_dir, 'branch_locations.html'))
    
    # Create a heatmap of branch scores
    heat_data = [[row['latitude'], row['longitude'], row['total_score']] 
                 for _, row in df.iterrows()
                 if not pd.isna(row['latitude']) and not pd.isna(row['longitude'])]
    
    m_heat = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
    HeatMap(heat_data).add_to(m_heat)
    m_heat.save(os.path.join(output_dir, 'score_heatmap.html'))
    
    # Create branch type distribution map
    m_types = folium.Map(location=[46.8182, 8.2275], zoom_start=8)
    
    # Define colors for different branch types
    type_colors = {
        'm': 'blue',
        'mm': 'green',
        'mmm': 'red',
        'voi': 'purple'
    }
    
    for _, row in df.iterrows():
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue
            
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=8,
            popup=f"{row['branch_name']} ({row['branch_type']})",
            color=type_colors.get(row['branch_type'], 'gray'),
            fill=True,
            fill_opacity=0.7
        ).add_to(m_types)
    
    m_types.save(os.path.join(output_dir, 'branch_types.html'))

def main():
    # Create output directory for visualizations
    output_dir = '../output/visualizations'
    os.makedirs(output_dir, exist_ok=True)
    
    # Load scoring data
    df = load_scores('../output/location_scores.csv')
    
    # Create geographic visualizations
    print("Creating geographic analysis...")
    create_geographic_analysis(df, output_dir)
    
    # Create other visualizations
    print("Creating score distribution plot...")
    create_score_distribution_plot(df, output_dir)
    
    print("Creating score components plot...")
    create_score_components_plot(df, output_dir)
    
    print("Creating branch type analysis...")
    create_branch_type_analysis(df, output_dir)
    
    print("Creating correlation heatmap...")
    create_correlation_heatmap(df, output_dir)
    
    print("Creating top locations analysis...")
    create_top_locations_analysis(df, output_dir)
    
    print("Creating income-population analysis...")
    create_income_population_analysis(df, output_dir)
    
    print(f"\nAll visualizations have been saved to {output_dir}")

if __name__ == "__main__":
    main() 