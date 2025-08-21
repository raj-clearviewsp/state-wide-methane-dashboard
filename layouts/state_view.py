# layouts/state_view.py

from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime
from data_aggregator import generate_real_county_data

# --- Data Generation for State-Level Analysis ---
def create_state_compliance_data():
    """
    Generate state-level data. This function now mixes real data for
    Farmington with the previous dummy data for other counties.
    """
    
    # --- REAL DATA INJECTION ---
    # Define the list of facility IDs for the county you want to analyze.
    farmington_facility_ids = [1008540, 1012724, 1007484]
    
    # Call the aggregator to generate real data for Farmington
    # This will trigger the scraping and analysis process when the app starts.
    farmington_real_data = generate_real_county_data(farmington_facility_ids)
    # --- END REAL DATA INJECTION ---
    
    # Total facilities in New Mexico
    total_facilities = 1823
    
    # Compliance data by regulation and equipment type
    compliance_matrix = {
        # Totals are now drastically reduced to reflect a much smaller facility population.
        'EPA OOOOb/c': {
            'Pneumatic Controllers': {'compliant': 22, 'non_compliant': 28, 'total': 50},
            'Storage Tanks': {'compliant': 27, 'non_compliant': 18, 'total': 45},
            'LDAR Program': {'compliant': 18, 'non_compliant': 42, 'total': 60},
            'Well Completions': {'compliant': 20, 'non_compliant': 15, 'total': 35},
            'Compressors': {'compliant': 14, 'non_compliant': 21, 'total': 35},
            'Associated Gas': {'compliant': 9, 'non_compliant': 6, 'total': 15}
        },
        'NM Ozone Precursor': {
            'Pneumatic Controllers': {'compliant': 28, 'non_compliant': 22, 'total': 50},
            'Storage Tanks': {'compliant': 32, 'non_compliant': 13, 'total': 45},
            'LDAR Program': {'compliant': 27, 'non_compliant': 33, 'total': 60},
            'Well Completions': {'compliant': 25, 'non_compliant': 10, 'total': 35},
            'Compressors': {'compliant': 21, 'non_compliant': 14, 'total': 35},
            'Associated Gas': {'compliant': 11, 'non_compliant': 4, 'total': 15}
        },
        'EU Methane Reg': {
            # Very low compliance to match the stricter regulations theme.
            'Pneumatic Controllers': {'compliant': 8, 'non_compliant': 42, 'total': 50},
            'Storage Tanks': {'compliant': 14, 'non_compliant': 31, 'total': 45},
            'LDAR Program': {'compliant': 12, 'non_compliant': 48, 'total': 60},
            'Well Completions': {'compliant': 12, 'non_compliant': 23, 'total': 35},
            'Compressors': {'compliant': 7, 'non_compliant': 28, 'total': 35},
            'Associated Gas': {'compliant': 3, 'non_compliant': 12, 'total': 15}
        }
    }

    # Reworked County-level data with much smaller facility counts.
    county_data = {
        'Lea': {
            'facilities': 18,
            'methane_emissions': 92000, # Still high emissions, but from fewer sites
            'avg_compliance': 0.48,
            'critical_facilities': 11,   # High percentage are critical
            'economic_impact': 18.4
        },
        'Eddy': {
            'facilities': 15,
            'methane_emissions': 75000,
            'avg_compliance': 0.55,
            'critical_facilities': 8,
            'economic_impact': 15.0
        },
        'San Juan': {
            'facilities': 11,
            'methane_emissions': 68000,
            'avg_compliance': 0.41,
            'critical_facilities': 7,
            'economic_impact': 13.6
        },
        # This key will be populated by your real data function for Farmington
        'Farmington': farmington_real_data,
        'Chaves': {
            'facilities': 5,
            'methane_emissions': 21000,
            'avg_compliance': 0.62,
            'critical_facilities': 2,
            'economic_impact': 4.2
        },
        'Others': {
            'facilities': 8,
            'methane_emissions': 35000,
            'avg_compliance': 0.58,
            'critical_facilities': 4,
            'economic_impact': 7.0
        }
    }
    
    return compliance_matrix, county_data, total_facilities

# Generate data
compliance_matrix, county_data, total_facilities = create_state_compliance_data()

# --- Helper Functions ---
def calculate_overall_compliance(compliance_matrix, regulation):
    """Calculate overall compliance rate for a regulation"""
    total_applicable = 0
    total_compliant = 0
    
    for equipment, data in compliance_matrix[regulation].items():
        total_applicable += data['total']
        total_compliant += data['compliant']
    
    return (total_compliant / total_applicable * 100) if total_applicable > 0 else 0

def create_regulation_card(regulation_name, regulation_key, compliance_data, icon, color):
    """Create a detailed regulation compliance card"""
    overall_compliance = calculate_overall_compliance(compliance_data, regulation_key)
    
    # Calculate total non-compliant facilities
    total_non_compliant = sum(data['non_compliant'] for data in compliance_data[regulation_key].values())
    
    # Find most problematic equipment
    worst_equipment = max(compliance_data[regulation_key].items(), 
                          key=lambda x: x[1]['non_compliant'])
    
    return html.Div(className="regulation-detail-card glass-card", children=[
        html.Div(className="regulation-card-header", children=[
            html.Div(className="regulation-title-section", children=[
                html.I(className=f"{icon} regulation-card-icon", style={'color': color}),
                html.Div(children=[
                    html.H3(regulation_name, className="regulation-card-title"),
                    html.Span(f"{overall_compliance:.1f}% Overall Compliance", 
                             className="regulation-compliance-rate",
                             style={'color': '#4CAF50' if overall_compliance >= 80 else '#FF5252'})
                ])
            ]),
            html.Div(className="regulation-stats", children=[
                html.Div(className="stat-item", children=[
                    html.Div(className="stat-number", children=str(total_non_compliant)),
                    html.Div(className="stat-label", children="Non-Compliant")
                ])
            ])
        ]),
        
        # Equipment breakdown
        html.Div(className="equipment-breakdown", children=[
            html.H4("Equipment Compliance Breakdown", className="breakdown-title"),
            html.Div(className="equipment-bars", children=[
                html.Div(className="equipment-bar-item", children=[
                    html.Div(className="equipment-name", children=equipment),
                    html.Div(className="compliance-bar-container", children=[
                        html.Div(className="compliance-bar-fill",
                                style={'width': f"{(data['compliant']/data['total']*100):.0f}%",
                                      'backgroundColor': '#4CAF50' if (data['compliant']/data['total']) >= 0.8 else '#FFA726'}),
                        html.Span(className="compliance-bar-text",
                                 children=f"{data['compliant']}/{data['total']} ({(data['compliant']/data['total']*100):.0f}%)")
                    ])
                ]) for equipment, data in sorted(compliance_data[regulation_key].items(), 
                                               key=lambda x: x[1]['compliant']/x[1]['total'])
            ])
        ]),
        
        # Critical insight
        html.Div(className="regulation-insight", children=[
            html.I(className="fas fa-lightbulb insight-icon"),
            html.Span(f"Priority: {worst_equipment[0]} has {worst_equipment[1]['non_compliant']} non-compliant facilities")
        ])
    ])

def create_county_impact_card(county_name, data):
    """Create a county impact assessment card"""
    compliance_color = '#4CAF50' if data['avg_compliance'] >= 0.8 else '#FFA726' if data['avg_compliance'] >= 0.7 else '#FF5252'
    
    return html.Div(className="county-impact-card", children=[
        html.Div(className="county-header", children=[
            html.H4(county_name),
            html.Span(f"{data['avg_compliance']:.0%}", 
                     className="county-compliance",
                     style={'color': compliance_color})
        ]),
        html.Div(className="county-metrics", children=[
            html.Div(className="county-metric", children=[
                html.Span(className="metric-value", children=str(data['facilities'])),
                html.Span(className="metric-label", children="Facilities")
            ]),
            html.Div(className="county-metric", children=[
                html.Span(className="metric-value", children=f"{data['methane_emissions']:,}"),
                html.Span(className="metric-label", children="mt CH₄/yr")
            ]),
            html.Div(className="county-metric", children=[
                html.Span(className="metric-value critical", children=str(data['critical_facilities'])),
                html.Span(className="metric-label", children="Critical")
            ])
        ]),
        html.Div(className="economic-impact", children=[
            html.Span("Economic Impact: "),
            html.Strong(f"${data['economic_impact']}M/yr")
        ])
    ])

# --- Create Visualizations ---

# 1. Statewide Compliance Overview Chart
fig_overview = go.Figure()

regulations = ['EPA OOOOb/c', 'NM Ozone Precursor', 'EU Methane Reg']
compliance_rates = [calculate_overall_compliance(compliance_matrix, reg) for reg in regulations]
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

fig_overview.add_trace(go.Bar(
    x=regulations,
    y=compliance_rates,
    marker_color=colors,
    text=[f"{rate:.1f}%" for rate in compliance_rates],
    textposition='auto',
    hovertemplate='<b>%{x}</b><br>Compliance Rate: %{y:.1f}%<extra></extra>'
))

# Add target line
fig_overview.add_hline(y=98, line_dash="dash", line_color="#58a6ff", opacity=0.5)
fig_overview.add_annotation(
    x=2, y=98,
    text="98% Target",
    showarrow=False,
    font=dict(size=10, color='#58a6ff'),
    xanchor="left"
)

fig_overview.update_layout(
    height=250,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(
        tickfont=dict(size=12, color='#c9d1d9')
    ),
    yaxis=dict(
        title="Compliance Rate (%)",
        range=[0, 100],
        tickfont=dict(size=11, color='#c9d1d9'),
        showgrid=True,
        gridcolor='rgba(48, 54, 61, 0.3)'
    ),
    margin=dict(l=50, r=20, t=20, b=40)
)

# 2. Geographic Distribution of Critical Facilities
county_names = list(county_data.keys())
critical_facilities = [data['critical_facilities'] for data in county_data.values()]
total_facilities_by_county = [data['facilities'] for data in county_data.values()]

fig_geographic = go.Figure()

# Create stacked bar chart
fig_geographic.add_trace(go.Bar(
    name='Compliant',
    x=county_names,
    y=[total - critical for total, critical in zip(total_facilities_by_county, critical_facilities)],
    marker_color='#4CAF50',
    hovertemplate='<b>%{x}</b><br>Compliant: %{y}<extra></extra>'
))

fig_geographic.add_trace(go.Bar(
    name='Critical Non-Compliance',
    x=county_names,
    y=critical_facilities,
    marker_color='#FF5252',
    text=critical_facilities,
    textposition='auto',
    hovertemplate='<b>%{x}</b><br>Critical: %{y}<extra></extra>'
))

fig_geographic.update_layout(
    barmode='stack',
    height=300,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(
        tickfont=dict(size=11, color='#c9d1d9')
    ),
    yaxis=dict(
        title="Number of Facilities",
        tickfont=dict(size=11, color='#c9d1d9'),
        showgrid=True,
        gridcolor='rgba(48, 54, 61, 0.3)'
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, color='#c9d1d9')
    ),
    margin=dict(l=50, r=20, t=40, b=50)
)

# --- Main Layout ---
state_summary_layout = html.Div([
    # Header Section
    html.Div(className="state-header-section", children=[
        html.H1("New Mexico Methane Compliance Overview", className="state-title"),
        html.P("Statewide analysis of regulatory compliance gaps and economic impacts", className="state-subtitle"),
        html.Div(className="state-stats-summary", children=[
            html.Div(className="summary-stat", children=[
                html.Span(className="stat-value", children="1,823"),
                html.Span(className="stat-label", children="Total Facilities")
            ]),
            html.Div(className="summary-stat", children=[
                html.Span(className="stat-value warning", children="470"),
                html.Span(className="stat-label", children="Critical Non-Compliance")
            ]),
            html.Div(className="summary-stat", children=[
                html.Span(className="stat-value danger", children="$26.2M"),
                html.Span(className="stat-label", children="Annual Lost Revenue")
            ])
        ])
    ]),
    
    # Compliance Overview Section
    html.Div(className="compliance-overview-container", children=[
        html.Div(className="section-header-row", children=[
            html.H2("Regulatory Compliance Status", className="section-header"),
            html.Span("Click on any regulation below for detailed equipment breakdown", className="section-hint")
        ]),
        
        # Overview Chart
        html.Div(className="overview-chart-container glass-card", children=[
            dcc.Graph(figure=fig_overview, config={'displayModeBar': False})
        ]),
        
        # Detailed Regulation Cards
        html.Div(className="regulations-grid", children=[
            create_regulation_card("EPA OOOOb/c", "EPA OOOOb/c", compliance_matrix, 
                                 "fas fa-flag-usa", "#FF6B6B"),
            create_regulation_card("NM Ozone Precursor Rule", "NM Ozone Precursor", compliance_matrix,
                                 "fas fa-map", "#4ECDC4"),
            create_regulation_card("EU Methane Regulation", "EU Methane Reg", compliance_matrix,
                                 "fas fa-globe-europe", "#45B7D1")
        ])
    ]),
    
    # Geographic Analysis Section
    html.Div(className="geographic-analysis-section", children=[
        html.H2("Geographic Distribution & Impact", className="section-header"),
        
        html.Div(className="geographic-content-grid", children=[
            # Chart
            html.Div(className="geographic-chart glass-card", children=[
                html.H3("Critical Facilities by County", className="card-title"),
                dcc.Graph(
                    figure=fig_geographic,
                    config={'displayModeBar': False, 'responsive': False},
                    style={'height': '400px', 'width': '100%'}
                )
            ]),
            
            # County Cards
            html.Div(className="county-cards-container", children=[
                html.H3("County Impact Assessment", className="card-title"),
                html.Div(className="county-cards-grid", children=[
                    create_county_impact_card(county, data) 
                    for county, data in sorted(county_data.items(), 
                                              key=lambda x: x[1]['critical_facilities'], 
                                              reverse=True)
                ])
            ])
        ])
    ]),
    
    # Policy Recommendations Section
    html.Div(className="policy-recommendations-section", children=[
        html.H2("Strategic Policy Recommendations", className="section-header"),
        
        html.Div(className="recommendations-grid", children=[
            # Immediate Actions
            html.Div(className="recommendation-card glass-card priority-high", children=[
                html.Div(className="recommendation-header", children=[
                    html.I(className="fas fa-exclamation-circle"),
                    html.H3("Immediate Actions Required")
                ]),
                html.Ul(children=[
                    html.Li("Focus enforcement on 1,120 facilities non-compliant with EU pneumatic controller standards"),
                    html.Li("Prioritize Lea County (156 critical facilities) for immediate inspection surge"),
                    html.Li("Accelerate zero-bleed retrofit program - current 20% compliance threatens EU market access")
                ]),
                html.Div(className="recommendation-impact", children=[
                    html.Span("Potential Impact: "),
                    html.Strong("$18.4M annual revenue recovery")
                ])
            ]),
            
            # Medium-term Strategy
            html.Div(className="recommendation-card glass-card priority-medium", children=[
                html.Div(className="recommendation-header", children=[
                    html.I(className="fas fa-chart-line"),
                    html.H3("6-Month Strategic Priorities")
                ]),
                html.Ul(children=[
                    html.Li("Implement tiered compliance assistance program for 560 non-compliant compressor facilities"),
                    html.Li("Expand LDAR program frequency - 70% compliance shows improvement potential"),
                    html.Li("Create financial incentive program targeting San Juan County's 35% non-compliance rate")
                ]),
                html.Div(className="recommendation-impact", children=[
                    html.Span("Potential Impact: "),
                    html.Strong("85% compliance achievable")
                ])
            ]),
            
            # Long-term Vision
            html.Div(className="recommendation-card glass-card priority-low", children=[
                html.Div(className="recommendation-header", children=[
                    html.I(className="fas fa-lightbulb"),
                    html.H3("Long-term Strategic Vision")
                ]),
                html.Ul(children=[
                    html.Li("Develop automated compliance monitoring system for real-time tracking"),
                    html.Li("Establish regional methane capture infrastructure in high-density areas"),
                    html.Li("Create industry partnership program for technology sharing and best practices")
                ]),
                html.Div(className="recommendation-impact", children=[
                    html.Span("Potential Impact: "),
                    html.Strong("98% compliance by 2027")
                ])
            ])
        ])
    ]),
    
    # Economic Impact Summary
    html.Div(className="economic-impact-section glass-card", children=[
        html.H3("Economic Impact Summary", className="card-title"),
        html.Div(className="economic-grid", children=[
            html.Div(className="economic-item", children=[
                html.I(className="fas fa-dollar-sign economic-icon"),
                html.Div(children=[
                    html.Div(className="economic-value", children="$26.2M"),
                    html.Div(className="economic-label", children="Annual Lost Gas Revenue")
                ])
            ]),
            html.Div(className="economic-item", children=[
                html.I(className="fas fa-chart-pie economic-icon"),
                html.Div(children=[
                    html.Div(className="economic-value", children="$142M"),
                    html.Div(className="economic-label", children="EU Market at Risk")
                ])
            ]),
            html.Div(className="economic-item", children=[
                html.I(className="fas fa-coins economic-icon"),
                html.Div(children=[
                    html.Div(className="economic-value", children="$45M"),
                    html.Div(className="economic-label", children="Retrofit Investment Needed")
                ])
            ]),
            html.Div(className="economic-item", children=[
                html.I(className="fas fa-seedling economic-icon"),
                html.Div(children=[
                    html.Div(className="economic-value", children="3.2x"),
                    html.Div(className="economic-label", children="ROI on Compliance")
                ])
            ])
        ])
    ])
])