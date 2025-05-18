import pandas as pd
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from jinja2 import Template

def create_analysis_dashboard():
    # Load the analysis data
    analysis_file = '../output/pilot_analysis/pilot_branch_analysis.json'
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(analysis_data)
    
    # Calculate summary statistics
    summary_stats = {
        'total_branches': len(df),
        'total_population': df['total_population_served'].sum(),
        'avg_population': df['total_population_served'].mean(),
        'total_income_potential': df['total_income_potential'].sum(),
        'avg_income': df['avg_income_per_capita'].mean(),
        'avg_area_coverage': df['area_coverage'].mean(),
        'avg_reach_factor': df['reach_factor'].mean(),
        'branch_types': df['branch_type'].value_counts().to_dict()
    }
    
    # Create visualizations for each branch
    branch_figures = {}
    for branch in analysis_data:
        # Create a figure for each branch
        fig = go.Figure()
        
        # Add population bars
        fig.add_trace(go.Bar(
            name='Inner Area (0-10 min)',
            x=['Population'],
            y=[branch['inner_population']],
            marker_color='#2ecc71'
        ))
        fig.add_trace(go.Bar(
            name='Outer Area (10-20 min)',
            x=['Population'],
            y=[branch['outer_population']],
            marker_color='#3498db'
        ))
        
        # Update layout
        fig.update_layout(
            title=f"{branch['branch_name']} - Population Coverage",
            barmode='stack',
            showlegend=True,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        branch_figures[branch['branch_id']] = fig.to_html(full_html=False, include_plotlyjs=False)
    
    # Create HTML template
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Pilot Branch Analysis Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            .card { margin-bottom: 20px; }
            .stat-card { text-align: center; padding: 20px; }
            .stat-value { font-size: 24px; font-weight: bold; }
            .stat-label { color: #666; }
            .branch-card { margin-bottom: 30px; }
            .branch-header { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
            .metric-value { font-size: 18px; font-weight: bold; }
            .metric-label { color: #666; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container-fluid py-4">
            <h1 class="mb-4">Pilot Branch Analysis Dashboard</h1>
            
            <!-- Summary Statistics -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card stat-card">
                        <div class="stat-value">{{ "{:,.0f}".format(summary_stats.total_population) }}</div>
                        <div class="stat-label">Total Population Served</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card stat-card">
                        <div class="stat-value">{{ "{:,.0f}".format(summary_stats.total_income_potential) }} CHF</div>
                        <div class="stat-label">Total Income Potential</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card stat-card">
                        <div class="stat-value">{{ "{:.1%}".format(summary_stats.avg_area_coverage) }}</div>
                        <div class="stat-label">Average Area Coverage</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card stat-card">
                        <div class="stat-value">{{ "{:.2f}".format(summary_stats.avg_reach_factor) }}</div>
                        <div class="stat-label">Average Reach Factor</div>
                    </div>
                </div>
            </div>
            
            <!-- Individual Branch Analysis -->
            {% for branch in analysis_data %}
            <div class="card branch-card">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="branch-header">
                                <h3>{{ branch.branch_name }}</h3>
                                <p class="mb-1"><strong>Type:</strong> {{ branch.branch_type }}</p>
                                <p class="mb-1"><strong>City:</strong> {{ branch.city }}</p>
                                <p class="mb-0"><strong>Total Score:</strong> {{ "{:.2f}".format(branch.total_score) }}</p>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-6">
                                    <div class="metric-value">{{ "{:,.0f}".format(branch.total_population_served) }}</div>
                                    <div class="metric-label">Total Population</div>
                                </div>
                                <div class="col-6">
                                    <div class="metric-value">{{ "{:,.0f}".format(branch.avg_income_per_capita) }} CHF</div>
                                    <div class="metric-label">Income per Capita</div>
                                </div>
                            </div>
                            
                            <div class="row mt-3">
                                <div class="col-6">
                                    <div class="metric-value">{{ "{:.1%}".format(branch.area_coverage) }}</div>
                                    <div class="metric-label">Area Coverage</div>
                                </div>
                                <div class="col-6">
                                    <div class="metric-value">{{ "{:.2f}".format(branch.reach_factor) }}</div>
                                    <div class="metric-label">Reach Factor</div>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <h5>Nearby Branches</h5>
                                <ul class="list-unstyled">
                                    {% for nearby in branch.nearby_branches %}
                                    <li>{{ nearby.branch_name }} ({{ nearby.branch_type }}): {{ "{:.1f}".format(nearby.distance_km) }} km</li>
                                    {% endfor %}
                                </ul>
                            </div>
                        </div>
                        
                        <div class="col-md-8">
                            {{ branch_figures[branch.branch_id] | safe }}
                            
                            <div class="row mt-3">
                                <div class="col-6">
                                    <h5>Population Distribution</h5>
                                    <ul class="list-unstyled">
                                        <li>Inner Area (0-10 min): {{ "{:,.0f}".format(branch.inner_population) }}</li>
                                        <li>Outer Area (10-20 min): {{ "{:,.0f}".format(branch.outer_population) }}</li>
                                    </ul>
                                </div>
                                <div class="col-6">
                                    <h5>Income Analysis</h5>
                                    <ul class="list-unstyled">
                                        <li>Average Income: {{ "{:,.0f}".format(branch.avg_income_per_capita) }} CHF</li>
                                        <li>Total Potential: {{ "{:,.0f}".format(branch.total_income_potential) }} CHF</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    # Render template
    template = Template(template_str)
    html_content = template.render(
        summary_stats=summary_stats,
        analysis_data=analysis_data,
        branch_figures=branch_figures
    )
    
    # Save the dashboard with UTF-8 encoding
    output_file = '../output/pilot_analysis/pilot_branch_analysis_dashboard.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Analysis dashboard saved to {output_file}")

if __name__ == "__main__":
    create_analysis_dashboard()