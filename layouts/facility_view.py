# layouts/facility_view.py
from dash import html, dcc, Input, Output, State, callback, no_update, ALL
import plotly.graph_objects as go
import plotly.express as px
from collections import defaultdict
import numpy as np
import pandas as pd
from datetime import datetime
import json

# Import the actual comparison engine
from comparison_engine import load_all_rules, run_compliance_check, pre_process_facility_data

# ==============================================================================
# FACILITY SEARCH COMPONENT
# ==============================================================================

def create_facility_search():
    """Create a clean facility search interface"""
    return html.Div(className="facility-search-container", children=[
        html.Div(className="search-content", children=[
            # Simple header
            html.Div(className="search-header", children=[
                html.I(className="fas fa-search search-icon"),
                html.H1("Facility Compliance Analysis", className="search-title"),
                html.P("Enter a facility ID to analyze emissions and regulatory compliance", 
                       className="search-description")
            ]),
            
            # Search input section
            html.Div(className="search-input-group", children=[
                dcc.Input(
                    id="facility-id-input",
                    type="text",
                    placeholder="Enter Facility ID (e.g., 1008052)",
                    className="facility-input",
                    debounce=True
                ),
                html.Button(
                    id="fetch-facility-btn",
                    className="fetch-button",
                    children=[
                        html.I(className="fas fa-chart-line"),
                        html.Span("Analyze")
                    ]
                )
            ]),
            
            # Example IDs
            html.Div(className="example-ids", children=[
                html.Span("Examples: ", className="example-label"),
                html.Button("1008052", className="example-btn", id={"type": "quick-facility", "index": "1008052"}),
                html.Button("1008053", className="example-btn", id={"type": "quick-facility", "index": "1008053"}),
                html.Button("1008054", className="example-btn", id={"type": "quick-facility", "index": "1008054"})
            ]),
            
            # Status indicator
            dcc.Loading(
                id="loading-facility",
                type="default",
                children=[
                    html.Div(id="facility-load-status")
                ]
            )
        ]),
        
        # Hidden stores
        dcc.Store(id="facility-data-store"),
        dcc.Store(id="compliance-data-store")
    ])

# ==============================================================================
# FACILITY OVERVIEW COMPONENTS
# ==============================================================================

def create_facility_information_section(facility_id, ghg_data):
    """Create beautiful facility information header with site details"""
    
    # Extract facility site details
    facility_details = ghg_data.get("FacilitySiteDetails") or {}
    facility_name = facility_details.get("facility_name", f"Facility {facility_id}")
    location = facility_details.get("location_address") or {}
    parent_company = facility_details.get("parent_company") or {}
    naics_code = facility_details.get("primary_naics_code")
    year = ghg_data.get("year", 2023)
    
    # Format address
    address_parts = []
    if location.get("street_address"):
        address_parts.append(location["street_address"])
    if location.get("city") and location.get("state_code"):
        city_state = f"{location['city']}, {location['state_code']}"
        if location.get("zip_code"):
            city_state += f" {location['zip_code']}"
        address_parts.append(city_state)
    
    full_address = " • ".join(address_parts) if address_parts else "Address not available"
    
    # NAICS description mapping
    naics_descriptions = {
        "211130": "Natural Gas Extraction",
        "211120": "Crude Petroleum Extraction", 
        "213111": "Drilling Oil and Gas Wells",
        "213112": "Support Activities for Oil and Gas Operations"
    }
    naics_desc = naics_descriptions.get(naics_code, "Oil & Gas Operations")
    
    return html.Div(className="facility-information-section", children=[
        # Main facility card
        html.Div(className="facility-main-card", children=[
            # Left side - Facility details
            html.Div(className="facility-primary-info", children=[
                # Facility name and ID
                html.Div(className="facility-title-group", children=[
                    html.H1(facility_name or f"Facility {facility_id}", className="facility-title"),
                    html.Div(className="facility-subtitle", children=[
                        html.Span(f"ID: {facility_id}", className="facility-id-badge"),
                        html.Span(f"Reporting Year: {year}", className="year-badge")
                    ])
                ]),
                
                # Location information
                html.Div(className="facility-location", children=[
                    html.Div(className="location-item", children=[
                        html.I(className="fas fa-map-marker-alt location-icon"),
                        html.Span(full_address, className="location-text")
                    ]),
                    html.Div(className="location-item", children=[
                        html.I(className="fas fa-industry location-icon"),
                        html.Span(f"NAICS {naics_code}: {naics_desc}" if naics_code else naics_desc, 
                                className="location-text")
                    ])
                ])
            ]),
            
            # Right side - Parent company info (if available)
            html.Div(className="facility-secondary-info", children=[
                html.Div(className="parent-company-section", children=[
                    html.H3("Parent Company", className="section-subtitle"),
                    html.Div(className="company-details", children=[
                        html.Div(className="company-name", children=[
                            html.I(className="fas fa-building company-icon"),
                            html.Span(parent_company.get("legal_name", "Not Available"), 
                                    className="company-text")
                        ]),
                        # Parent company address (if different from facility)
                        create_parent_company_address(parent_company, location)
                    ] if parent_company.get("legal_name") else [
                        html.Div(className="no-parent-info", children=[
                            html.I(className="fas fa-info-circle"),
                            html.Span("Parent company information not available")
                        ])
                    ])
                ])
            ])
        ]),
        
        # Quick stats bar
        create_facility_quick_stats(ghg_data)
    ])

def create_parent_company_address(parent_company, facility_location):
    """Create parent company address display if different from facility"""
    
    if not parent_company:
        return html.Div()
    
    # Build parent company address
    parent_address_parts = []
    if parent_company.get("street_address"):
        parent_address_parts.append(parent_company["street_address"])
    if parent_company.get("city") and parent_company.get("state"):
        city_state = f"{parent_company['city']}, {parent_company['state']}"
        if parent_company.get("zip_code"):
            city_state += f" {parent_company['zip_code']}"
        parent_address_parts.append(city_state)
    
    parent_address = " • ".join(parent_address_parts)
    
    # Check if parent address is different from facility address
    facility_address_parts = []
    if facility_location.get("street_address"):
        facility_address_parts.append(facility_location["street_address"])
    if facility_location.get("city") and facility_location.get("state_code"):
        city_state = f"{facility_location['city']}, {facility_location['state_code']}"
        if facility_location.get("zip_code"):
            city_state += f" {facility_location['zip_code']}"
        facility_address_parts.append(city_state)
    
    facility_address = " • ".join(facility_address_parts)
    
    # Only show parent address if it's different and available
    if parent_address and parent_address != facility_address:
        return html.Div(className="company-address", children=[
            html.I(className="fas fa-map-pin company-icon"),
            html.Span(parent_address, className="company-text small")
        ])
    
    return html.Div()

def create_facility_quick_stats(ghg_data):
    """Create quick stats bar with key facility metrics"""
    
    # Calculate key metrics
    total_ch4 = calculate_total_methane(ghg_data)
    total_co2e = total_ch4 * 25  # GWP conversion
    
    # Get facility characteristics
    well_details = ghg_data.get("OnshoreProductionWellDetails") or {}
    well_totals = well_details.get("totals") or {}
    total_wells = well_totals.get("total_wells_producing_eoy", 0)
    
    # Tank information
    tank_summary = ghg_data.get("AtmosphericTanks_Combined_Totals") or {}
    total_tanks = tank_summary.get("total_tank_count", 0)
    
    # Compressor information
    recip_data = ghg_data.get("ReciprocatingCompressorsDetails") or {}
    centri_data = ghg_data.get("CentrifugalCompressorsDetails") or {}
    has_compressors = recip_data.get("present") or centri_data.get("present")
    
    # Pneumatic devices
    pneumatic_data = ghg_data.get("PneumaticDeviceVentingDetails") or {}
    has_high_bleed = pneumatic_data.get("has_high_bleed")
    has_low_bleed = pneumatic_data.get("has_low_bleed")
    
    return html.Div(className="facility-quick-stats", children=[
        html.Div(className="stats-grid", children=[
            # Emissions
            html.Div(className="quick-stat emissions", children=[
                html.I(className="fas fa-smog stat-icon"),
                html.Div(className="stat-content", children=[
                    html.Span(f"{total_ch4:,.1f}", className="stat-value"),
                    html.Span("mt CH₄/year", className="stat-label")
                ])
            ]),
            
            # CO2 equivalent
            html.Div(className="quick-stat co2e", children=[
                html.I(className="fas fa-globe stat-icon"),
                html.Div(className="stat-content", children=[
                    html.Span(f"{total_co2e:,.0f}", className="stat-value"),
                    html.Span("mt CO₂e", className="stat-label")
                ])
            ]),
            
            # Wells
            html.Div(className="quick-stat wells", children=[
                html.I(className="fas fa-oil-well stat-icon"),
                html.Div(className="stat-content", children=[
                    html.Span(f"{total_wells:,.0f}" if total_wells else "N/A", className="stat-value"),
                    html.Span("Active Wells", className="stat-label")
                ])
            ]),
            
            # Tanks
            html.Div(className="quick-stat tanks", children=[
                html.I(className="fas fa-database stat-icon"),
                html.Div(className="stat-content", children=[
                    html.Span(f"{total_tanks:,.0f}" if total_tanks else "N/A", className="stat-value"),
                    html.Span("Storage Tanks", className="stat-label")
                ])
            ]),
            
            # Equipment status
            html.Div(className="quick-stat equipment", children=[
                html.I(className="fas fa-cogs stat-icon"),
                html.Div(className="stat-content", children=[
                    html.Div(className="equipment-indicators", children=[
                        html.Span(className=f"indicator {'active' if has_compressors else 'inactive'}", 
                                children="Compressors"),
                        html.Span(className=f"indicator {'active' if has_high_bleed else 'inactive'}", 
                                children="High-Bleed"),
                        html.Span(className=f"indicator {'active' if has_low_bleed else 'inactive'}", 
                                children="Low-Bleed")
                    ])
                ])
            ])
        ])
    ])

def create_facility_overview_header(facility_id, ghg_data):
    """Updated facility overview header that works with the new facility info section"""
    
    # Calculate emissions by category for the metrics
    leak_emissions = get_leak_emissions(ghg_data)
    venting_emissions = get_venting_emissions(ghg_data)
    flaring_emissions = get_flaring_emissions(ghg_data)
    tank_emissions = get_component_emissions("Storage Tanks", ghg_data)
    
    return html.Div(className="facility-overview-header", children=[
        html.H2("Emissions Breakdown", className="section-title"),
        
        # Emissions category cards
        html.Div(className="emissions-category-grid", children=[
            html.Div(className="emission-category-card leaks", children=[
                html.Div(className="category-header", children=[
                    html.I(className="fas fa-exclamation-triangle category-icon"),
                    html.H3("Equipment Leaks", className="category-title")
                ]),
                html.Div(className="category-value", children=f"{leak_emissions:,.1f}"),
                html.Div(className="category-unit", children="mt CH₄/year"),
                html.Div(className="category-description", children="Fugitive emissions from components")
            ]),
            
            html.Div(className="emission-category-card venting", children=[
                html.Div(className="category-header", children=[
                    html.I(className="fas fa-wind category-icon"),
                    html.H3("Venting", className="category-title")
                ]),
                html.Div(className="category-value", children=f"{venting_emissions:,.1f}"),
                html.Div(className="category-unit", children="mt CH₄/year"),
                html.Div(className="category-description", children="Planned releases and pneumatics")
            ]),
            
            html.Div(className="emission-category-card tanks", children=[
                html.Div(className="category-header", children=[
                    html.I(className="fas fa-database category-icon"),
                    html.H3("Storage Tanks", className="category-title")
                ]),
                html.Div(className="category-value", children=f"{tank_emissions:,.1f}"),
                html.Div(className="category-unit", children="mt CH₄/year"),
                html.Div(className="category-description", children="Tank flash and working losses")
            ]),
            
            html.Div(className="emission-category-card flaring", children=[
                html.Div(className="category-header", children=[
                    html.I(className="fas fa-fire category-icon"),
                    html.H3("Flaring", className="category-title")
                ]),
                html.Div(className="category-value", children=f"{flaring_emissions:,.1f}"),
                html.Div(className="category-unit", children="mt CH₄/year"),
                html.Div(className="category-description", children="Incomplete combustion emissions")
            ])
        ])
    ])

def create_emissions_analysis_section(ghg_data):
    """Create clean emissions analysis with visualizations"""
    
    return html.Div(className="emissions-section", children=[
        html.H2("Emissions Analysis", className="section-title"),
        
        html.Div(className="emissions-grid", children=[
            # Emissions by source
            html.Div(className="chart-card", children=[
                html.H3("Distribution by Source", className="chart-title"),
                create_emissions_donut_chart(ghg_data)
            ]),
            
            # Top emitters
            html.Div(className="chart-card", children=[
                html.H3("Top Emission Sources", className="chart-title"),
                create_well_formation_chart(ghg_data)
            ])
        ]),
        
        # Leak analysis
        html.Div(className="chart-card full-width", children=[
            html.H3("Leak Analysis by Component", className="chart-title"),
            create_leak_analysis_chart(ghg_data)
        ])
    ])

def create_emissions_donut_chart(ghg_data):
    """Create clean donut chart for emissions distribution"""
    
    sources_data = get_emissions_by_source(ghg_data)
    
    if not sources_data:
        return html.Div(className="no-data", children=[
            html.I(className="fas fa-info-circle"),
            html.P("No emissions data available")
        ])
    
    fig = go.Figure(data=[go.Pie(
        labels=sources_data['labels'],
        values=sources_data['values'],
        hole=0.6,
        marker=dict(
            colors=['#F5222D', '#FA8C16', '#FAAD14', '#52C41A', '#1890FF', '#722ED1', '#13C2C2'],
            line=dict(color='#1A1F3A', width=2)
        ),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='<b>%{label}</b><br>%{value:.1f} mt CH₄<br>%{percent}<extra></extra>'
    )])
    
    total_emissions = sum(sources_data['values'])
    
    fig.update_layout(
        showlegend=False,
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#B8C0E0'),
        annotations=[
            dict(
                text=f'<b>{total_emissions:.0f}</b><br>mt CH₄',
                x=0.5, y=0.5,
                font=dict(size=20, color='#FFFFFF'),
                showarrow=False
            )
        ]
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

def create_well_formation_chart(ghg_data):
    """
    Creates an elegant and polished vertical bar chart displaying the 
    breakdown of wells by their geological formation type.
    """
    
    # Call the data-shaping function (this function remains the same).
    well_data = get_well_breakdown_by_formation(ghg_data)
    
    # Handle the case where no well data is available.
    if not well_data or not well_data.get('values'):
        return html.Div(className="no-data", children=[
            html.I(className="fas fa-info-circle"),
            html.P("No well formation data available")
        ])
    
    # --- Create the vertical bar chart figure ---
    fig = go.Figure(data=[
        go.Bar(
            x=well_data['labels'],   # Swapped for vertical orientation
            y=well_data['values'],   # Swapped for vertical orientation
            
            # --- Visual Enhancements ---
            marker=dict(
                color=well_data['values'],  # Use values for a gradient
                colorscale='Viridis',       # A vibrant, professional color scale
                showscale=False,            # Hide the color bar legend
                line=dict(
                    color='rgba(255,255,255,0.1)', # Subtle border for each bar
                    width=1
                )
            ),
            
            # --- Text and Hover Improvements ---
            texttemplate='%{y:,.0f}', # Display value on top of bar, formatted
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>%{y:,.0f} wells<extra></extra>',
            
            # --- Interactive Polish ---
            hoverlabel=dict(
                bgcolor="rgba(10, 20, 40, 0.9)",
                font_size=12,
                font_family="Arial"
            )
        )
    ])
    
    # --- Layout Customization for a Nicer Look ---
    fig.update_layout(
        title=dict(
            text='<b>Well Distribution by Formation Type</b>',
            y=0.95,
            x=0.5,
            xanchor='center',
            yanchor='top',
            font=dict(size=16, color='#E0E0E0')
        ),
        height=400, # Increased height for better vertical readability
        margin=dict(l=60, r=40, t=60, b=120), # Increased bottom margin for rotated labels
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#B8C0E0', size=11),
        
        # --- X-Axis (Formation Types) ---
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            title="",
            tickangle=-45, # Rotate labels to prevent overlap
            automargin=True
        ),
        
        # --- Y-Axis (Number of Wells) ---
        yaxis=dict(
            showgrid=True, # Vertical gridlines help guide the eye
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=False,
            title="Number of Wells"
        ),
        
        # Remove the default Plotly mode bar for a cleaner look
        showlegend=False
    )
    
    # Update trace to add a slight rounding effect to the bars
    # fig.update_traces(marker_cornerradius=3)
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


def create_leak_analysis_chart(ghg_data):
    """
    Creates a polished horizontal bar chart of the top leaking components
    using the new, structured leak data.
    """
    
    # Get the breakdown from the corrected helper function.
    # We can slice here if we only want to show the top N components.
    leak_data = get_leak_breakdown(ghg_data)[:5] # Show top 5
    
    if not leak_data:
        return html.Div(className="no-data", children=[
            html.I(className="fas fa-info-circle"),
            html.P("No component leak data available")
        ])
    
    fig = go.Figure(data=[
        go.Bar(
            # --- Swapped for horizontal orientation ---
            x=[d['value'] for d in leak_data],
            y=[d['name'] for d in leak_data],
            orientation='h',
            
            # --- Visual Polish ---
            marker=dict(
                color='#F5B02D', # A distinct warning/amber color for leaks
                opacity=0.9,
                line=dict(color='rgba(255,255,255,0.1)', width=1)
            ),
            texttemplate='%{x:.2f}', # Display value next to the bar
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>%{x:.2f} mt CH₄<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=dict(
            text='<b>Top Leaking Component Types</b>',
            x=0.5,
            xanchor='center',
            font=dict(size=14, color='#E0E0E0')
        ),
        height=300,
        margin=dict(l=120, r=40, t=50, b=40), # Left margin for component names
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#B8C0E0', size=11),
        
        # --- X-Axis (Emissions) ---
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=False,
            title="Methane Emissions (mt CH₄)"
        ),
        
        # --- Y-Axis (Component Types) ---
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            title="",
            # Reverses the order to show the highest emitter at the top
            autorange="reversed" 
        ),
        showlegend=False
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})

# ==============================================================================
# COMPLIANCE DASHBOARD COMPONENTS
# ==============================================================================

def create_compliance_dashboard(compliance_results, ghg_data):
    """Create clean compliance dashboard with regulation breakdowns"""
    
    # Process compliance results by regulation
    epa_results = [r for r in compliance_results if "EPA" in r.get("regulation", "")]
    nm_results = [r for r in compliance_results if "NM" in r.get("regulation", "")]
    eu_results = [r for r in compliance_results if "EU" in r.get("regulation", "")]
    
    return html.Div(className="compliance-dashboard", children=[
        html.H2("Regulatory Compliance", className="section-title"),
        
        # Compliance overview cards
        html.Div(className="compliance-cards-grid", children=[
            create_regulation_status_card(
                "EPA OOOOb/c",
                epa_results,
                "fas fa-flag-usa",
                "Federal methane regulations"
            ),
            create_regulation_status_card(
                "New Mexico",
                nm_results,
                "fas fa-mountain",
                "State ozone precursor rules"
            ),
            create_regulation_status_card(
                "EU Methane",
                eu_results,
                "fas fa-globe-europe",
                "European methane standards"
            )
        ]),
        
        # Compliance matrix
        html.Div(className="compliance-matrix-section", children=[
            html.H3("Component Compliance Matrix", className="matrix-title"),
            create_compliance_matrix(compliance_results)
        ])
    ])

def create_regulation_status_card(name, results, icon, description):
    """Create clean regulation compliance status card"""
    
    if not results:
        compliant = 0
        total = 0
        percentage = 0
    else:
        compliant = sum(1 for r in results if r["status"] == "In Compliance")
        total = len(results)
        percentage = (compliant / total * 100) if total > 0 else 0
    
    status_class = "success" if percentage >= 90 else "warning" if percentage >= 70 else "danger"
    
    return html.Div(className=f"regulation-status-card {status_class}", children=[
        html.Div(className="status-header", children=[
            html.I(className=f"{icon} status-icon"),
            html.Div(className="status-info", children=[
                html.H3(name, className="regulation-name"),
                html.P(description, className="regulation-desc")
            ])
        ]),
        
        html.Div(className="status-metrics", children=[
            # Simple percentage display
            html.Div(className="percentage-display", children=[
                html.Div(className="percentage-value", children=f"{percentage:.0f}%"),
                html.Div(className="percentage-label", children="Compliant"),
                # Progress bar
                html.Div(className="progress-bar", children=[
                    html.Div(className="progress-fill", style={"width": f"{percentage}%"})
                ])
            ]),
            
            # Compliance details
            html.Div(className="compliance-breakdown", children=[
                html.Div(className="breakdown-item", children=[
                    html.Span(str(compliant), className="value success"),
                    html.Span("Compliant", className="label")
                ]),
                html.Div(className="breakdown-item", children=[
                    html.Span(str(total - compliant), className="value danger"),
                    html.Span("Non-Compliant", className="label")
                ]),
                html.Div(className="breakdown-item", children=[
                    html.Span(str(total), className="value"),
                    html.Span("Total Checks", className="label")
                ])
            ])
        ])
    ])

def create_compliance_matrix(compliance_results):
    """Create interactive compliance matrix showing all components vs regulations"""
    
    # Group results by component and regulation
    matrix_data = defaultdict(lambda: defaultdict(str))
    components = set()
    regulations = set()
    
    for result in compliance_results:
        component = result.get('component', 'Unknown')
        if component == "Well Completions/Workovers":
            pass
        else:
            regulation = result.get('regulation', 'Unknown').split(' - ')[0]
            status = result.get('status', 'Unknown')
            
            components.add(component)
            regulations.add(regulation)
            matrix_data[component][regulation] = status
    
    # Create matrix visualization
    matrix_rows = []
    for component in sorted(components):
        row_cells = [html.Td(component, className="component-name")]
        for regulation in sorted(regulations):
            status = matrix_data[component][regulation]
            cell_class = "compliant" if status == "In Compliance" else "non-compliant" if status == "Out of Compliance" else "unknown"
            icon = "fa-check" if status == "In Compliance" else "fa-times" if status == "Out of Compliance" else "fa-question"
            row_cells.append(
                html.Td(className=f"status-cell {cell_class}", children=[
                    html.I(className=f"fas {icon}")
                ])
            )
        matrix_rows.append(html.Tr(row_cells))
    
    return html.Table(className="compliance-matrix", children=[
        html.Thead([
            html.Tr([
                html.Th("Component", className="header-cell"),
                *[html.Th(reg, className="header-cell") for reg in sorted(regulations)]
            ])
        ]),
        html.Tbody(matrix_rows)
    ])

# ==============================================================================
# COMPLIANCE GAPS ANALYSIS
# ==============================================================================

def create_compliance_gaps_analysis(compliance_results, ghg_data):
    """Create organized compliance gaps analysis grouped by component"""
    
    # Group non-compliant items by component
    gaps_by_component = defaultdict(list)
    
    for result in compliance_results:
        if result['status'] == "Out of Compliance":
            component = result['component']
            regulation = result['regulation'].split(' - ')[0] if ' - ' in result['regulation'] else result['regulation']
            
            gaps_by_component[component].append({
                'regulation': regulation,
                'details': result['details'],
                'rule_id': result.get('rule_id', '')
            })
    
    if not gaps_by_component:
        return html.Div(className="no-gaps-found", children=[
            html.I(className="fas fa-check-circle"),
            html.H3("Full Compliance"),
            html.P("All components meet regulatory requirements")
        ])
    
    # Create component cards with emissions and all failed regulations
    component_cards = []
    for component, gaps in gaps_by_component.items():
        emissions = get_component_emissions(component, ghg_data)
        severity = calculate_severity(emissions, "")
        
        component_cards.append({
            'component': component,
            'gaps': gaps,
            'emissions': emissions,
            'severity': severity
        })
    
    # Sort by emissions (highest first)
    component_cards.sort(key=lambda x: x['emissions'], reverse=True)
    
    # Count total unique components with issues
    total_components = len(gaps_by_component)
    
    # Count gaps by regulation
    epa_gaps = sum(1 for comp in gaps_by_component.values() for g in comp if "EPA" in g['regulation'])
    nm_gaps = sum(1 for comp in gaps_by_component.values() for g in comp if "NM" in g['regulation'])
    eu_gaps = sum(1 for comp in gaps_by_component.values() for g in comp if "EU" in g['regulation'])
    
    return html.Div(className="gaps-analysis-section", children=[
        html.H2("Compliance Gap Analysis", className="section-title"),
        
        # Summary stats
        html.Div(className="gaps-summary", children=[
            html.Div(className="summary-stat", children=[
                html.Span(str(total_components), className="stat-value"),
                html.Span("Components Non-Compliant", className="stat-label")
            ]),
            html.Div(className="summary-stat", children=[
                html.Span(str(epa_gaps), className="stat-value epa"),
                html.Span("EPA Violations", className="stat-label")
            ]),
            html.Div(className="summary-stat", children=[
                html.Span(str(nm_gaps), className="stat-value nm"),
                html.Span("NM Violations", className="stat-label")
            ]),
            html.Div(className="summary-stat", children=[
                html.Span(str(eu_gaps), className="stat-value eu"),
                html.Span("EU Violations", className="stat-label")
            ])
        ]),
        
        # Component cards
        html.Div(className="component-gaps-grid", children=[
            create_component_gap_card(card) for card in component_cards
        ])
    ])


def create_component_gap_card(card_data):
    """Create comprehensive gap card showing all regulation violations for one component"""
    component = card_data['component']
    gaps = card_data['gaps']
    emissions = card_data['emissions']
    severity = card_data['severity']
    
    # Create regulation badges for each failed regulation
    regulation_sections = []
    for gap in gaps:
        reg_class = "epa" if "EPA" in gap['regulation'] else "nm" if "NM" in gap['regulation'] else "eu"
        regulation_sections.append(
            html.Div(className=f"regulation-section {reg_class}", children=[
                html.Div(className="regulation-header", children=[
                    html.Span(gap['regulation'], className=f"regulation-badge {reg_class}"),
                    html.I(className="fas fa-times-circle fail-icon")
                ]),
                html.P(gap['details'], className="regulation-details")
            ])
        )
    
    # Get unified actions for this component
    actions = get_required_actions(component, "")
    
    return html.Div(className=f"component-gap-card {severity}", children=[
        # Component header
        html.Div(className="component-header", children=[
            html.Div(className="component-info", children=[
                html.I(className=f"fas {get_component_icon(component)} component-icon"),
                html.H3(component, className="component-name")
            ]),
            html.Div(className="component-metrics", children=[
                html.Div(className="emissions-display", children=[
                    html.Span(f"{emissions:.1f}", className="emissions-value"),
                    html.Span("mt CH₄", className="emissions-unit")
                ]),
                html.Span(severity.upper(), className=f"severity-indicator {severity}")
            ])
        ]),
        
        # Regulations that component fails
        html.Div(className="regulations-container", children=[
            html.H4("Non-Compliant Regulations", className="regulations-title"),
            html.Div(className="regulations-list", children=regulation_sections)
        ]),
        
        # Required actions
        html.Div(className="actions-container", children=[
            html.H4("Corrective Actions Required", className="actions-title"),
            html.Ul(className="actions-list", children=[
                html.Li(action) for action in actions
            ])
        ])
    ])

# ==============================================================================
# RECOMMENDATIONS AND TIMELINE
# ==============================================================================

def create_recommendations_section(compliance_results, ghg_data):
    """Create clean recommendations and compliance timeline"""
    
    return html.Div(className="recommendations-section", children=[
        html.H2("Recommendations & Timeline", className="section-title"),
        
        html.Div(className="recommendations-grid", children=[
            # Timeline
            html.Div(className="timeline-card", children=[
                html.H3("Compliance Timeline", className="chart-title"),
                create_compliance_timeline()
            ]),
            
        ])
    ])

def create_compliance_timeline():
    """Create readable horizontal compliance timeline"""
    
    events = [
        {"date": "2024 Q1", "event": "EPA OOOOb Effective", "type": "epa"},
        {"date": "2024 Q3", "event": "Pneumatic Retrofits", "type": "action"},
        {"date": "2025 Q1", "event": "NM Inspections", "type": "nm"},
        {"date": "2025 Q3", "event": "LDAR Enhancement", "type": "action"},
        {"date": "2026", "event": "Zero-Bleed Required", "type": "epa"},
        {"date": "2027", "event": "EU Compliance", "type": "eu"}
    ]
    
    return html.Div(className="timeline-horizontal", children=[
        html.Div(className="timeline-track-horizontal"),
        html.Div(className="timeline-items", children=[
            html.Div(className=f"timeline-item {event['type']}", children=[
                html.Div(className="timeline-date", children=event['date']),
                html.Div(className="timeline-marker", children=[
                    html.Div(className="marker-dot"),
                    html.Div(className="marker-line")
                ]),
                html.Div(className="timeline-label", children=event['event'])
            ]) for event in events
        ])
    ])

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def calculate_total_methane(ghg_data):
    """
    Calculate total methane emissions from all sources, handling missing
    or None data structures gracefully.
    """
    # Ensure ghg_data is a dictionary to prevent top-level errors.
    if not isinstance(ghg_data, dict):
        ghg_data = {}

    total = 0

    # Add emissions from all major sources
    sources = [
        ("PneumaticDeviceVentingDetails", "mt_ch4"),
        ("WellVentingDetails", "mt_ch4"),
        ("AssociatedGasVentingFlaringDetails", "mt_ch4"),
        ("CentrifugalCompressorsDetails", "mt_ch4"),
        ("ReciprocatingCompressorsDetails", "mt_ch4"),
        ("UniqueFlareStacks_Summary", "total_ch4_emissions_mt"),
        ("WellsWithFracturingDetails", "mt_ch4"),
        ("WellsWithoutFracturingDetails", "mt_ch4"),
        ("AtmosphericTanks_Summary", "mt_ch4")
    ]

    for source, field in sources:
        # Safely access nested data, defaulting to 0 if missing
        if source == "AtmosphericTanks_Summary":
            print(ghg_data.get(source))
        total += (ghg_data.get(source) or {}).get(field, 0) or 0

    # Add leak emissions
    leaks = ghg_data.get("LeaksCalculatedWithCountsFactors_SummaryBySourceType") or []
    if isinstance(leaks, list):
        for leak in leaks:
            if isinstance(leak, dict):
                total += leak.get("ch4_emissions_mt", 0) or 0

    return round(total, 2)

def get_leak_emissions(ghg_data):
    """
    Get total leak emissions, handling missing or None data gracefully.
    """
    if not isinstance(ghg_data, dict):
        return 0
    
    total = 0
    leaks = ghg_data.get("LeaksCalculatedWithCountsFactors_SummaryBySourceType") or []
    
    if isinstance(leaks, list):
        for leak in leaks:
            if isinstance(leak, dict):
                total += leak.get("ch4_emissions_mt", 0) or 0
                
    return total

def get_venting_emissions(ghg_data):
    """
    Get total venting emissions, handling missing or None data gracefully.
    """
    if not isinstance(ghg_data, dict):
        return 0
        
    total = 0
    total += (ghg_data.get("WellVentingDetails") or {}).get("mt_ch4", 0) or 0
    total += (ghg_data.get("AssociatedGasVentingFlaringDetails") or {}).get("mt_ch4", 0) or 0
    
    return total

def get_flaring_emissions(ghg_data):
    """
    Get total flaring emissions, handling missing or None data gracefully.
    """
    if not isinstance(ghg_data, dict):
        return 0
        
    total = 0
    total += (ghg_data.get("UniqueFlareStacks_Summary") or {}).get("total_ch4_emissions_mt", 0) or 0
    
    tanks = (ghg_data.get("AtmosphericTanks_CalcMethod_1_2_SubBasinRows") or {}).get("totals") or {}
    total += tanks.get("flaring_ch4_mt", 0) or 0
    
    return total

def get_emissions_by_source(ghg_data):
    """
    Get emissions breakdown by source for visualization, updated to use the new,
    structured scraper data for atmospheric tanks.
    """
    if not isinstance(ghg_data, dict):
        return {}

    sources = []
    values = []

    # The source_map is updated to point to the new, reliable summary key for tanks.
    source_map = [
        ("Pneumatic Controllers", "PneumaticDeviceVentingDetails", "mt_ch4"),
        ("Well Venting", "WellVentingDetails", "mt_ch4"),
        
        # --- THIS IS THE CORRECTED LINE ---
        ("Storage Tanks", "AtmosphericTanks_Summary", "mt_ch4"),
        # --- END OF CORRECTION ---
        
        ("Flaring", "UniqueFlareStacks_Summary", "total_ch4_emissions_mt"),
        ("Centrifugal Compressors", "CentrifugalCompressorsDetails", "mt_ch4"),
        ("Reciprocating Compressors", "ReciprocatingCompressorsDetails", "mt_ch4"),
        ("Associated Gas", "AssociatedGasVentingFlaringDetails", "mt_ch4"),
        ("Leaks", "LeaksCalculatedWithCountsFactors_SummaryBySourceType", "sum"),
        ("Well Completions", "WellsWithFracturingDetails", "mt_ch4")
    ]

    for name, source_key, field in source_map:
        value = 0
        
        if source_key == "LeaksCalculatedWithCountsFactors_SummaryBySourceType" and field == "sum":
            leaks_list = ghg_data.get(source_key) or []
            if isinstance(leaks_list, list):
                value = sum(l.get("ch4_emissions_mt", 0) or 0 for l in leaks_list if isinstance(l, dict))
        elif "." in field:
            parts = field.split(".")
            data = ghg_data.get(source_key) or {}
            # Traverse nested dictionaries safely
            for part in parts:
                if isinstance(data, dict):
                    data = data.get(part)
                else:
                    data = 0
                    break
            value = data or 0
        else:
            # This logic block now correctly handles the updated "Storage Tanks" entry
            value = (ghg_data.get(source_key) or {}).get(field, 0) or 0
        
        # Ensure value is a number before comparison
        if not isinstance(value, (int, float)):
            value = 0
            
        if value > 0:
            sources.append(name)
            values.append(value)

    # Combine compressors if both types exist (this logic remains correct)
    if "Centrifugal Compressors" in sources and "Reciprocating Compressors" in sources:
        cent_idx = sources.index("Centrifugal Compressors")
        recip_idx = sources.index("Reciprocating Compressors")
        combined_value = values[cent_idx] + values[recip_idx]
        
        sources_to_remove = {"Centrifugal Compressors", "Reciprocating Compressors"}
        
        new_sources = [s for s in sources if s not in sources_to_remove]
        new_values = [v for s, v in zip(sources, values) if s not in sources_to_remove]

        new_sources.append("Compressors (All)")
        new_values.append(combined_value)
        
        sources, values = new_sources, new_values

    return {'labels': sources, 'values': values} if sources else {}

def get_well_breakdown_by_formation(ghg_data):
    """
    Extracts and formats well count data by formation type for visualization.
    
    This function processes the new 'OnshoreProductionWellDetails' data,
    sorts the formations by the number of wells in descending order, and
    returns a dictionary suitable for creating a bar chart.
    """
    # Safely access the nested data structure.
    well_details = ghg_data.get("OnshoreProductionWellDetails") or {}
    formation_data = well_details.get("by_formation_type")

    # Return an empty dict if the required data is missing.
    if not formation_data:
        return {}

    # Sort the data so the chart is ordered from most wells to least.
    sorted_data = sorted(formation_data, key=lambda x: x.get('well_count', 0), reverse=True)

    # Extract the labels (formation types) and values (well counts).
    labels = [item.get('formation_type', 'Unknown') for item in sorted_data]
    values = [item.get('well_count', 0) for item in sorted_data]

    return {'labels': labels, 'values': values}

def get_leak_breakdown(ghg_data):
    """
    Gets a breakdown of leak emissions by component type from the new
    'EquipmentLeakDetails' structure. It also simplifies the component names
    for cleaner chart labels.
    """
    if not isinstance(ghg_data, dict):
        return []
        
    leak_details = ghg_data.get("EquipmentLeakDetails") or {}
    # The scraper already sorts the components by emissions, so we just need to read them.
    components = leak_details.get("components") or []

    breakdown_data = []
    for component in components:
        # --- Simplify the long component name for readability ---
        full_name = component.get("component_type", "Unknown")
        # Splits "Service - Valve" into "Valve"
        simple_name = full_name.split(' - ')[-1] if ' - ' in full_name else full_name

        breakdown_data.append({
            'name': simple_name,
            'value': component.get("ch4_emissions_mt", 0) or 0
        })
                
    return breakdown_data

def get_leak_emissions(ghg_data):
    """
    Gets the total methane emissions from equipment leaks by reading the
    summary value from the new 'EquipmentLeakDetails' structure.
    """
    if not isinstance(ghg_data, dict):
        return 0
    
    # Safely navigate to the summary dictionary and get the total methane.
    leak_details = ghg_data.get("EquipmentLeakDetails") or {}
    summary = leak_details.get("summary") or {}
    total_ch4 = summary.get("mt_ch4", 0)
    
    return total_ch4 or 0

def get_component_emissions(component, ghg_data):
    """
    Get emissions for a specific component, updated to use the new,
    structured facility data format.
    """
    if not isinstance(ghg_data, dict):
        ghg_data = {}
        
    component_lower = component.lower()

    if "pneumatic" in component_lower:
        return (ghg_data.get("PneumaticDeviceVentingDetails") or {}).get("mt_ch4", 0) or 0
    
    elif "tank" in component_lower or "storage" in component_lower:
        # Safely access the new combined totals summary for tanks.
        combined_totals = ghg_data.get("AtmosphericTanks_Combined_Totals") or {}
        
        # Prioritize the facility's self-reported total emissions figure.
        # This value comes directly from the top-level XML tag for the section.
        reported_ch4 = combined_totals.get("total_ch4_emissions_mt_reported")
        
        if reported_ch4 is not None:
            # Return the reported value, even if it's 0.0
            return reported_ch4
        else:
            # If the reported total is missing, fall back to our calculated sum.
            return combined_totals.get("total_ch4_emissions_mt", 0) or 0

    elif "leak" in component_lower:
        return get_leak_emissions(ghg_data)
        
    elif "liquids" in component_lower or "unloading" in component_lower or "well venting" in component_lower:
        return (ghg_data.get("WellVentingDetails") or {}).get("mt_ch4", 0) or 0
        
    elif "reciprocating" in component_lower:
        return (ghg_data.get("ReciprocatingCompressorsDetails") or {}).get("mt_ch4", 0) or 0
        
    elif "centrifugal" in component_lower:
        return (ghg_data.get("CentrifugalCompressorsDetails") or {}).get("mt_ch4", 0) or 0
        
    elif "compressor" in component_lower:
        centrif = (ghg_data.get("CentrifugalCompressorsDetails") or {}).get("mt_ch4", 0) or 0
        recip = (ghg_data.get("ReciprocatingCompressorsDetails") or {}).get("mt_ch4", 0) or 0
        return centrif + recip
        
    elif "flare" in component_lower or "flaring" in component_lower:
        return (ghg_data.get("UniqueFlareStacks_Summary") or {}).get("total_ch4_emissions_mt", 0) or 0
        
    elif "associated" in component_lower:
        return (ghg_data.get("AssociatedGasVentingFlaringDetails") or {}).get("mt_ch4", 0) or 0
        
    elif "completion" in component_lower or "workover" in component_lower:
        completions = (ghg_data.get("WellsWithFracturingDetails") or {}).get("mt_ch4", 0) or 0
        wo = (ghg_data.get("WellsWithoutFracturingDetails") or {}).get("mt_ch4", 0) or 0
        return completions + wo
        
    else:
        return 0

def get_component_icon(component):
    """Get appropriate icon for component type"""
    icons = {
        "pneumatic": "fa-valve",
        "tank": "fa-database",
        "storage": "fa-database",
        "well": "fa-oil-well",
        "venting": "fa-wind",
        "compressor": "fa-compress",
        "flare": "fa-fire",
        "leak": "fa-exclamation-triangle",
        "associated": "fa-burn"
    }
    
    component_lower = component.lower()
    for key, icon in icons.items():
        if key in component_lower:
            return icon
    return "fa-cog"

def calculate_severity(emissions, regulation):
    """Calculate severity level based on emissions and regulation"""
    if emissions > 100:
        return "critical"
    elif emissions > 50:
        return "high"
    elif emissions > 10:
        return "medium"
    else:
        return "low"

def get_required_actions(component, regulation):
    """Get specific required actions for compliance"""
    actions = {
        "Pneumatic": [
            "Replace high-bleed controllers with zero-emission alternatives",
            "Install instrument air systems where grid power available"
        ],
        "Tank": [
            "Install 95% efficiency vapor recovery units",
            "Implement closed vent systems"
        ],
        "Leak": [
            "Implement comprehensive LDAR program",
            "Conduct quarterly OGI surveys"
        ],
        "Compressor": [
            "Replace rod packing every 26,000 hours",
            "Route emissions to process or control"
        ],
        "Flare": [
            "Ensure 95% destruction efficiency",
            "Install continuous pilot monitoring"
        ],
        "Well": [
            "Implement best management practices",
            "Install automated plunger lifts"
        ],
        "Associated": [
            "Route gas to sales or beneficial use",
            "Eliminate routine venting and flaring"
        ]
    }
    
    component_key = component.split()[0] if component else "Unknown"
    for key in actions:
        if key.lower() in component_key.lower():
            return actions[key]
    
    return ["Review regulatory requirements", "Implement best management practices"]

# ==============================================================================
# MAIN LAYOUT FUNCTION
# ==============================================================================

def create_facility_view():
    """Create the main facility view layout"""
    
    return html.Div(className="facility-view-main", children=[
        # Search interface
        create_facility_search(),
        
        # Results container (hidden initially)
        html.Div(id="facility-results-wrapper", style={"display": "none"}, children=[
            html.Div(id="facility-information-section"),
            html.Div(id="facility-overview-section"),
            html.Div(id="emissions-analysis-section"),
            html.Div(id="compliance-dashboard-section"),
            html.Div(id="gaps-analysis-section"),
            html.Div(id="recommendations-section")
        ])
    ])
# ==============================================================================
# CALLBACKS
# ==============================================================================

@callback(
    Output("facility-id-input", "value"),
    Input({"type": "quick-facility", "index": ALL}, "n_clicks"),
    State({"type": "quick-facility", "index": ALL}, "id"),
    prevent_initial_call=True
)
def handle_quick_access(n_clicks, ids):
    """Handle quick access button clicks"""
    if any(n_clicks):
        # Find which button was clicked
        for i, clicks in enumerate(n_clicks or []):
            if clicks:
                return ids[i]["index"]
    return no_update

@callback(
    [Output("facility-data-store", "data"),
     Output("compliance-data-store", "data"),
     Output("facility-load-status", "children"),
     Output("facility-results-wrapper", "style"),
     Output("facility-information-section", "children"),  # NEW OUTPUT
     Output("facility-overview-section", "children"),
     Output("emissions-analysis-section", "children"),
     Output("compliance-dashboard-section", "children"),
     Output("gaps-analysis-section", "children"),
     Output("recommendations-section", "children")],
    [Input("fetch-facility-btn", "n_clicks")],
    [State("facility-id-input", "value")],
    prevent_initial_call=True
)
def fetch_and_analyze_facility(n_clicks, facility_id):
    """Fetch facility data and run compliance analysis"""
    
    if not facility_id:
        return (no_update, no_update,
                html.Div(className="status-error", children=[
                    html.I(className="fas fa-exclamation-circle"),
                    html.Span(" Please enter a facility ID")
                ]),
                no_update, no_update, no_update, no_update, no_update, no_update, no_update)
    
    from epa_ghg_explorer import get_facility_data
    
    # Fetch data from API
    ghg_data = get_facility_data(int(facility_id), 2023)
    
    # Pre-process data for compliance engine
    facility_flat_data = pre_process_facility_data(ghg_data)
    
    # Load compliance rules
    master_rulebook = load_all_rules()
    
    # Run compliance checks
    compliance_results = []
    for rule_id, rule_obj in master_rulebook.items():
        result = run_compliance_check(rule_obj, facility_flat_data)
        compliance_results.append(result)
    
    # Create UI components
    facility_info = create_facility_information_section(facility_id, ghg_data)  # NEW
    overview = create_facility_overview_header(facility_id, ghg_data)  # UPDATED
    emissions = create_emissions_analysis_section(ghg_data)
    compliance = create_compliance_dashboard(compliance_results, ghg_data)
    gaps = create_compliance_gaps_analysis(compliance_results, ghg_data)
    recommendations = create_recommendations_section(compliance_results, ghg_data)
    
    return (
        ghg_data,
        compliance_results,
        html.Div(className="status-success", children=[
            html.I(className="fas fa-check-circle"),
            html.Span(" Analysis complete")
        ]),
        {"display": "block"},
        facility_info,
        overview,
        emissions,
        compliance,
        gaps,
        recommendations
    )

# Export the layout
facility_detail_layout = create_facility_view()