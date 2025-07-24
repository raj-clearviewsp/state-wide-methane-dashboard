# layouts/facility_view.py

from dash import html, dcc
import plotly.graph_objects as go
from collections import defaultdict
import numpy as np
from comparison_engine import load_all_rules, run_compliance_check

# ==============================================================================
# DATA PRE-PROCESSING & ENGINE EXECUTION
# ==============================================================================
facility_data_for_engine = {
    # === General & UI-related Data ===
    "site_type": "Onshore petroleum and natural gas production",
    "startup_year": 2023,
    "operating_hours": 20000,

    # === Pneumatic Controller Data ===
    "mt_CH4_pneumatics": 45.5,
    "high_bleed_pneumatic_device_count": 1,
    "intermittent_bleed_pneumatic_device_count": 3,
    "low_bleed_pneumatic_device_count": 8,
    "total_controllers": 12,
    "non_emitting_controllers": 0,
    "site_group": "Table 1",
    "grid_power_available": False,

    # === Storage Tank Data ===
    "storage_mt_CH4": 13.0,
    "count_tanks_vented": 0,
    "count_tanks_no_control": 0,

    # === Well Completion & Workover Data ===
    "number_of_reduced_emissions_completions": 3,
    "number_of_vented_completions": 0,
    "number_of_reduced_emissions_workovers": 1,
    "is_flare_present": True,

    # === Liquids Unloading Data ===
    "well_venting_emissions": 22.0,
    "number_of_venting_wells": 2,
    "unloading_mt_CH4": 22.0,

    # === Compressor Data ===
    "reciprocating_compressor_mt_ch4": 8.7,
    "centrifugal_compressor_mt_ch4": 0,
    "reciprocating_compressor_emissions": 8.7,
    "centrifugal_compressor_emissions": 0,

    # === Flare & Control Device Data ===
    "flare_combustion_efficiency": 97.5,
    "control_device_design_eff": 98.0,

    # === Associated Gas Data ===
    "associated_gas_ch4": 0.0,
}

master_rulebook = load_all_rules()
engine_results = [run_compliance_check(rule, facility_data_for_engine) for rule in master_rulebook.values()]

compliance_data_by_component = defaultdict(dict)
regulation_key_map = {
    "EPA OOOOb/c": "EPA", "EPA OOOOb": "EPA", "NM Ozone Precursor Rule": "NM",
    "NM Natural-Gas Waste Rule": "NM_Waste", "EU Methane Regulation 2024/1787": "EU"
}

for result in engine_results:
    component = result['component']
    regulation_full_name = result['regulation']
    
    reg_key = None
    if regulation_full_name:
        reg_key = next((key for name, key in regulation_key_map.items() if name in regulation_full_name), None)
    
    if component and reg_key:
        compliance_data_by_component[component][reg_key] = {
            'status': result['status'], 
            'finding': result['details'],
            'regulation_full': regulation_full_name
        }

# ==============================================================================
# ENHANCED COMPLIANCE DETAILS DATA STRUCTURE
# ==============================================================================

# Define detailed compliance requirements and timelines
compliance_timelines = {
    "Pneumatic Controllers": {
        "EPA": {
            "requirement": "Zero-bleed pneumatic controllers required",
            "timeline": "By January 2026 for new sources, January 2028 for existing sources",
            "exceptions": "Sites without access to electrical power may use low-bleed controllers"
        },
        "NM": {
            "requirement": "Retrofit or replace high-bleed controllers",
            "timeline": "Within 1 year of rule effective date",
            "exceptions": "None"
        },
        "EU": {
            "requirement": "Zero methane venting from pneumatic devices",
            "timeline": "By 2027 for all facilities exporting to EU",
            "exceptions": "Limited exemptions for remote sites"
        }
    },
    "Storage Tanks": {
        "EPA": {
            "requirement": "95% control efficiency for tanks >6 tons VOC/year",
            "timeline": "Immediate for new sources, by 2026 for existing",
            "exceptions": "Tanks below threshold exempt"
        },
        "NM": {
            "requirement": "98% control efficiency for all tanks",
            "timeline": "Within 6 months",
            "exceptions": "None"
        }
    },
    "Well Venting for Liquids Unloading": {
        "EPA": {
            "requirement": "Minimize venting, use best management practices",
            "timeline": "Immediate implementation required",
            "exceptions": "Safety exemptions only"
        },
        "NM": {
            "requirement": "Automated plunger lifts or other non-venting methods",
            "timeline": "Within 2 years",
            "exceptions": "Technical infeasibility documentation required"
        },
        "EU": {
            "requirement": "Zero routine venting",
            "timeline": "By 2026",
            "exceptions": "Emergency situations only"
        }
    },
    "Reciprocating Compressors": {
        "EPA": {
            "requirement": "Rod packing replacement every 36 months or 26,000 hours",
            "timeline": "Starting 2025",
            "exceptions": "None"
        },
        "NM": {
            "requirement": "Continuous monitoring and quarterly inspections",
            "timeline": "Immediate",
            "exceptions": "None"
        }
    }
}

# ==============================================================================
# UI GENERATION
# ==============================================================================

facility_info = {
    "name": "San Juan Basin (580)", 
    "operator": "HILCORP ENERGY CO", 
    "total_co2e": 1561951,
    "total_ch4": 43956, 
    "total_wells": 10328, 
    "gas_produced_mscf": 300201344.89,
    "latitude": 36.7283,
    "longitude": -108.2187,
    "permit_number": "NM-2023-0580",
    "last_inspection": "October 15, 2024"
}

methane_intensity = (facility_info["total_ch4"] * 1000) / facility_info["gas_produced_mscf"]

# Calculate compliance summary
total_components = len(compliance_data_by_component)
epa_compliant = sum(1 for data in compliance_data_by_component.values() if "EPA" in data and data["EPA"]["status"] == "In Compliance")
nm_compliant = sum(1 for data in compliance_data_by_component.values() if "NM" in data and data["NM"]["status"] == "In Compliance")
eu_compliant = sum(1 for data in compliance_data_by_component.values() if "EU" in data and data["EU"]["status"] == "In Compliance")

# Identify compliance gaps with detailed info
compliance_gaps = []
for component, data in compliance_data_by_component.items():
    gaps_for_component = []
    for reg, details in data.items():
        if details['status'] == "Out of Compliance":
            gaps_for_component.append({
                'regulation': reg,
                'regulation_full': details.get('regulation_full', reg),
                'finding': details['finding']
            })
    
    if gaps_for_component:
        compliance_gaps.append({
            'component': component,
            'gaps': gaps_for_component
        })

# Sort by number of non-compliant regulations
compliance_gaps.sort(key=lambda x: len(x['gaps']), reverse=True)

# --- Helper Functions ---

def create_compliance_gap_card(gap_info):
    component = gap_info['component']
    gaps = gap_info['gaps']
    
    # Get component-specific data
    component_data = {}
    if component == "Pneumatic Controllers":
        component_data = {
            'current_emissions': facility_data_for_engine.get('mt_CH4_pneumatics', 0),
            'details': {
                'High-bleed devices': facility_data_for_engine.get('high_bleed_pneumatic_device_count', 0),
                'Intermittent-bleed devices': facility_data_for_engine.get('intermittent_bleed_pneumatic_device_count', 0),
                'Low-bleed devices': facility_data_for_engine.get('low_bleed_pneumatic_device_count', 0),
                'Zero-bleed devices': facility_data_for_engine.get('non_emitting_controllers', 0)
            },
            'icon': 'fas fa-valve'
        }
    elif component == "Storage Tanks":
        component_data = {
            'current_emissions': facility_data_for_engine.get('storage_mt_CH4', 0),
            'details': {
                'Uncontrolled tanks': facility_data_for_engine.get('count_tanks_no_control', 0),
                'Vented tanks': facility_data_for_engine.get('count_tanks_vented', 0)
            },
            'icon': 'fas fa-database'
        }
    elif component == "Well Venting for Liquids Unloading":
        component_data = {
            'current_emissions': facility_data_for_engine.get('unloading_mt_CH4', 0),
            'details': {
                'Venting wells': facility_data_for_engine.get('number_of_venting_wells', 0),
                'Annual venting events': 'Data needed'
            },
            'icon': 'fas fa-oil-well'
        }
    elif component == "Reciprocating Compressors":
        component_data = {
            'current_emissions': facility_data_for_engine.get('reciprocating_compressor_mt_ch4', 0),
            'details': {
                'Operating hours': facility_data_for_engine.get('operating_hours', 0),
                'Last rod packing replacement': 'Data needed'
            },
            'icon': 'fas fa-compress'
        }
    else:
        component_data = {
            'current_emissions': 0,
            'details': {},
            'icon': 'fas fa-cog'
        }
    
    # Create timeline visualization for this component
    timeline_items = []
    for gap in gaps:
        reg = gap['regulation']
        if component in compliance_timelines and reg in compliance_timelines[component]:
            timeline_info = compliance_timelines[component][reg]
            timeline_items.append(
                html.Div(className="timeline-item", children=[
                    html.Div(className=f"timeline-marker {reg.lower()}-marker"),
                    html.Div(className="timeline-content", children=[
                        html.Div(className="timeline-regulation", children=gap['regulation_full']),
                        html.Div(className="timeline-requirement", children=timeline_info['requirement']),
                        html.Div(className="timeline-date", children=[
                            html.I(className="fas fa-calendar-alt"),
                            html.Span(timeline_info['timeline'])
                        ])
                    ])
                ])
            )
    
    return html.Div(className="compliance-gap-card glass-card", children=[
        # Component Header
        html.Div(className="gap-card-header", children=[
            html.Div(className="gap-component-info", children=[
                html.I(className=f"{component_data.get('icon', 'fas fa-cog')} component-icon"),
                html.Div(children=[
                    html.H3(component, className="gap-component-name"),
                    html.Div(className="gap-regulations", children=[
                        html.Span(className=f"regulation-tag {gap['regulation'].lower()}-tag", 
                                children=gap['regulation']) for gap in gaps
                    ])
                ])
            ]),
            html.Div(className="gap-emissions", children=[
                html.Div(className="emissions-value", children=f"{component_data['current_emissions']:.1f}"),
                html.Div(className="emissions-label", children="mt CH₄/year")
            ])
        ]),
        
        # Current Status Details
        html.Div(className="gap-current-status", children=[
            html.H4("Current Equipment Status", className="subsection-title"),
            html.Div(className="equipment-details", children=[
                html.Div(className="detail-item", children=[
                    html.Span(className="detail-label", children=label),
                    html.Span(className="detail-value", children=str(value))
                ]) for label, value in component_data.get('details', {}).items()
            ])
        ]),
        
        # Compliance Requirements Timeline
        html.Div(className="gap-timeline", children=[
            html.H4("Compliance Requirements & Timeline", className="subsection-title"),
            html.Div(className="timeline-container", children=timeline_items)
        ]),
        
        # Action Required
        html.Div(className="gap-actions", children=[
            html.H4("Required Actions", className="subsection-title"),
            html.Div(className="action-items", children=[
                html.Div(className="action-item", children=[
                    html.I(className="fas fa-chevron-right action-icon"),
                    html.Span(gap['finding'])
                ]) for gap in gaps
            ])
        ])
    ])

# --- Main Layout ---

facility_detail_layout = html.Div([
    # --- Section 1: Facility Overview ---
    html.Div(className="facility-overview-section", children=[
        html.Div(className="facility-info-card glass-card", children=[
            html.Div(className="facility-header-content", children=[
                html.Div(children=[
                    html.H1(facility_info['name'], className="facility-name"),
                    html.Div(className="facility-operator", children=[
                        html.I(className="fas fa-building"),
                        html.Span(facility_info['operator'])
                    ])
                ]),
                html.Div(className="facility-key-metrics", children=[
                    html.Div(className="metric-item", children=[
                        html.Div(className="metric-number", children=f"{facility_info['total_ch4']:,}"),
                        html.Div(className="metric-label", children="mt CH₄/year")
                    ]),
                    html.Div(className="metric-divider"),
                    html.Div(className="metric-item", children=[
                        html.Div(className="metric-number", children=f"{methane_intensity:.2f}"),
                        html.Div(className="metric-label", children="kg CH₄/Mscf")
                    ]),
                    html.Div(className="metric-divider"),
                    html.Div(className="metric-item", children=[
                        html.Div(className="metric-number", children=f"{facility_info['total_wells']:,}"),
                        html.Div(className="metric-label", children="Active Wells")
                    ])
                ])
            ]),
            html.Div(className="facility-metadata", children=[
                html.Span([html.I(className="fas fa-file-alt"), f" Permit: {facility_info['permit_number']}"]),
                html.Span([html.I(className="fas fa-map-marker-alt"), f" {facility_info['latitude']:.4f}, {facility_info['longitude']:.4f}"]),
                html.Span([html.I(className="fas fa-calendar-check"), f" Last Inspection: {facility_info['last_inspection']}"])
            ])
        ])
    ]),
    
    # --- Section 2: Compliance Summary Dashboard ---
    html.Div(className="compliance-dashboard-section", children=[
        html.H2("Compliance Overview", className="section-header"),
        html.Div(className="compliance-summary-grid", children=[
            # Overall Compliance Score
            html.Div(className="overall-compliance-card glass-card", children=[
                html.H3("Overall Compliance Status", className="card-title"),
                html.Div(className="compliance-score-visual", children=[
                    html.Div(className="score-ring", children=[
                        html.Div(className="score-percentage", 
                                children=f"{((epa_compliant + nm_compliant + eu_compliant) / (total_components * 3) * 100):.0f}%"),
                        html.Div(className="score-label", children="Compliant")
                    ]),
                    html.Div(className="score-breakdown", children=[
                        html.Div(className="breakdown-item", children=[
                            html.Span(className="breakdown-label", children="EPA OOOOb/c:"),
                            html.Span(className="breakdown-value", 
                                     style={'color': '#4CAF50' if epa_compliant/total_components >= 0.98 else '#FF5252'},
                                     children=f"{epa_compliant}/{total_components}")
                        ]),
                        html.Div(className="breakdown-item", children=[
                            html.Span(className="breakdown-label", children="NM State Rules:"),
                            html.Span(className="breakdown-value",
                                     style={'color': '#4CAF50' if nm_compliant/total_components >= 0.98 else '#FF5252'},
                                     children=f"{nm_compliant}/{total_components}")
                        ]),
                        html.Div(className="breakdown-item", children=[
                            html.Span(className="breakdown-label", children="EU Methane Reg:"),
                            html.Span(className="breakdown-value",
                                     style={'color': '#4CAF50' if eu_compliant/total_components >= 0.98 else '#FFA726'},
                                     children=f"{eu_compliant}/{total_components}")
                        ])
                    ])
                ])
            ]),
            
            # Key Metrics
            html.Div(className="key-metrics-card glass-card", children=[
                html.H3("Impact Assessment", className="card-title"),
                html.Div(className="impact-metrics", children=[
                    html.Div(className="impact-item", children=[
                        html.I(className="fas fa-exclamation-triangle impact-icon warning"),
                        html.Div(children=[
                            html.Div(className="impact-number", children=str(len(compliance_gaps))),
                            html.Div(className="impact-label", children="Components with Gaps")
                        ])
                    ]),
                    html.Div(className="impact-item", children=[
                        html.I(className="fas fa-cloud impact-icon danger"),
                        html.Div(children=[
                            html.Div(className="impact-number", 
                                    children=f"{sum([facility_data_for_engine.get('mt_CH4_pneumatics', 0), facility_data_for_engine.get('storage_mt_CH4', 0), facility_data_for_engine.get('unloading_mt_CH4', 0), facility_data_for_engine.get('reciprocating_compressor_mt_ch4', 0)]):.1f}"),
                            html.Div(className="impact-label", children="mt CH₄ at Risk")
                        ])
                    ]),
                    html.Div(className="impact-item", children=[
                        html.I(className="fas fa-calendar-times impact-icon info"),
                        html.Div(children=[
                            html.Div(className="impact-number", children="2026"),
                            html.Div(className="impact-label", children="First Deadline")
                        ])
                    ])
                ])
            ])
        ])
    ]),
    
    # --- Section 3: Detailed Compliance Gaps ---
    html.Div(className="compliance-gaps-section", children=[
        html.Div(className="section-header-with-count", children=[
            html.H2("Compliance Gap Analysis", className="section-header"),
            html.Span(className="gap-count", children=f"{len(compliance_gaps)} components requiring action")
        ]),
        html.P("Detailed breakdown of non-compliant components with specific requirements and timelines", 
               className="section-subtitle"),
        
        # Compliance Gap Cards
        html.Div(className="compliance-gaps-container", children=[
            create_compliance_gap_card(gap) for gap in compliance_gaps
        ])
    ]),
    
    # --- Section 4: Quick Reference Matrix ---
    html.Div(className="quick-reference-section glass-card", children=[
        html.H3("Quick Compliance Reference", className="card-title"),
        html.P("At-a-glance view of all components and their compliance status", className="card-subtitle"),
        html.Div(className="reference-matrix", children=[
            html.Div(className="matrix-legend", children=[
                html.Span(className="legend-item", children=[
                    html.I(className="fas fa-check-circle compliant-icon"),
                    html.Span("Compliant")
                ]),
                html.Span(className="legend-item", children=[
                    html.I(className="fas fa-times-circle non-compliant-icon"),
                    html.Span("Non-Compliant")
                ]),
                html.Span(className="legend-item", children=[
                    html.I(className="fas fa-minus-circle na-icon"),
                    html.Span("Not Applicable")
                ])
            ]),
            html.Table(className="compliance-reference-table", children=[
                html.Thead(children=[
                    html.Tr(children=[
                        html.Th("Component"),
                        html.Th("EPA", className="reg-column"),
                        html.Th("NM", className="reg-column"),
                        html.Th("EU", className="reg-column")
                    ])
                ]),
                html.Tbody(children=[
                    html.Tr(children=[
                        html.Td(component),
                        html.Td(className="reg-column", children=[
                            html.I(className="fas fa-check-circle compliant-icon") 
                            if data.get("EPA", {}).get("status") == "In Compliance"
                            else html.I(className="fas fa-times-circle non-compliant-icon")
                            if data.get("EPA", {}).get("status") == "Out of Compliance"
                            else html.I(className="fas fa-minus-circle na-icon")
                        ]),
                        html.Td(className="reg-column", children=[
                            html.I(className="fas fa-check-circle compliant-icon")
                            if data.get("NM", {}).get("status") == "In Compliance"
                            else html.I(className="fas fa-times-circle non-compliant-icon")
                            if data.get("NM", {}).get("status") == "Out of Compliance"
                            else html.I(className="fas fa-minus-circle na-icon")
                        ]),
                        html.Td(className="reg-column", children=[
                            html.I(className="fas fa-check-circle compliant-icon")
                            if data.get("EU", {}).get("status") == "In Compliance"
                            else html.I(className="fas fa-times-circle non-compliant-icon")
                            if data.get("EU", {}).get("status") == "Out of Compliance"
                            else html.I(className="fas fa-minus-circle na-icon")
                        ])
                    ]) for component, data in sorted(compliance_data_by_component.items())
                ])
            ])
        ])
    ])
])