# layouts/regulation_view.py

from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px

# --- Comprehensive Regulatory Data with Direct Comparisons ---
REGULATION_DATA = {
    "Pneumatic Devices": {
        "icon": "fas fa-tools",
        "description": "Rules governing controllers and pumps that use natural gas pressure to operate valves and level gauges.",
        "nm_highlight": "NM requires 100% zero-bleed by 2030 - the most aggressive timeline globally",
        "compliance_gap": 57,
        "comparison": [
            {
                "Feature": "Applicability",
                "EPA OOOOb": "Covers every pneumatic controller affected facility at well sites, centralized production facilities, compressor stations and gas processing plants that is newly built, modified or reconstructed on or after 6 Dec 2022 (§60.5365b, §60.5390b).",
                "NM Ozone Rule": "Applies to all natural gas driven controllers & pumps at well sites, tank batteries, gathering/boosting sites, processing plants and transmission compressor stations in nine high ozone counties; rule effective 5 Aug 2022 (§20.2.50.122).",
                "NM Gas Waste Rule": "Equipment specific limits absent; however any gas vented from pneumatics is reported as 'lost gas' and counts against the operator's mandatory 98% gas capture benchmark (§19.15.27.8 & .9).",
                "EU Methane Reg": "Art 1 & 15 apply the Regulation to all on/offshore upstream production and gas infrastructure; existing pneumatics must meet the rule by 5 Feb 2026 (18 mo after 15 Jul 2024 entry into force).",
                "nm_stricter": True
            },
            {
                "Feature": "Controller Standard",
                "EPA OOOOb": "Zero emitting controllers (instrument air, electric, or self contained) required at all covered sites (§60.5390b(a)). Remote Alaska option: low bleed ≤ 6 scfh or ≥ 95% control if technical need is demonstrated (§60.5390b(b)).",
                "NM Ozone Rule": "New or replacement controllers must be zero emission (§20.2.50.122 B(4)(a)). Existing controllers may keep operating only until the phased retrofit milestones (see below) and must be logged & tagged.",
                "NM Gas Waste Rule": "No explicit bleed rate cap, but venting > 500,000 scf/yr from pneumatics is debited to the operator's lost gas ledger (§19.15.27.8 G(2)(i)).",
                "EU Methane Reg": "New installations/refurbishments: only commercially available zero emitting controllers may be installed (Art 15 § 7). Existing venting controllers must be replaced where such alternatives are commercially available (Art 15 § 5-6).",
                "nm_stricter": True
            },
            {
                "Feature": "Controller Retrofit",
                "EPA OOOOb": "Not applicable – OOOOb governs only new, modified or reconstructed facilities.",
                "NM Ozone Rule": "Fleet wide retrofit schedule (§20.2.50.122 C):\n• ≥ 25% zero bleed by 1 Jan 2024\n• ≥ 60% by 1 Jan 2027\n• 100% by 1 Jan 2030 (earlier if operator reaches 75% by 2025).",
                "NM Gas Waste Rule": "No direct mandate; operators are driven to early conversion because routine pneumatic venting jeopardises the 98% capture score.",
                "EU Methane Reg": "Existing controllers must be replaced or a documented 'no feasible alternative' justification filed by 5 Feb 2026 (Art 15 § 8).",
                "nm_stricter": True
            },
            {
                "Feature": "Pneumatic Pumps",
                "EPA OOOOb": "Zero emitting required at gas processing plants and any site with line power (§60.5393b(a)(1)). Unpowered sites may route pump vents to a control device or process achieving ≥ 95% destruction (§60.5393b(b)). Full compliance mandatory by 7 May 2025 (§60.5370b(i)).",
                "NM Ozone Rule": "New pumps at powered sites must be zero emission; existing pumps must reach ≥ 95% control within 3 years (§20.2.50.122 B(5)). Pumps at unpowered sites: route to 95% control if technically feasible (§20.2.50.122 B(5)(d)).",
                "NM Gas Waste Rule": "Pump venting volume is added to lost gas accounting; < 500,000 scf/yr is deemed de minimis for enforcement, but still reportable (§19.15.27.8 G).",
                "EU Methane Reg": "Art 15 applies the same zero bleed & retrofit test to pneumatic pumps as to controllers; 'venting devices' must be replaced by non emitters where available.",
                "nm_stricter": False
            },
        ],
    },

    "Leak Detection (LDAR)": {
        "icon": "fas fa-search-location",
        "description": "Requirements for finding and fixing unintended fugitive emissions from equipment leaks.",
        "nm_highlight": "NM's ALARM program offers unique credits for advanced continuous monitoring technology",
        "compliance_gap": 31,
        "comparison": [
            {
                "Feature": "Program Requirement",
                "EPA OOOOb": "Site specific Fugitive Emissions Monitoring Plan laying out component inventory, technologies, survey schedule and repair protocol (§60.5397b(c)-(d)).",
                "NM Ozone Rule": "Equipment Leak Monitoring Plan plus electronic Compliance Database Report filings; deviations trigger default monitoring (§20.2.50.112, .116).",
                "NM Gas Waste Rule": "Natural Gas Management Plan & optional ALARM programme for advanced, continuous or aerial detection tied to creditable 48h isolation/15d repair (§19.15.27.9 B).",
                "EU Methane Reg": "LDAR Programme must be lodged with the regulator by 5 May 2025 and updated annually (Art 14 § 1).",
                "nm_stricter": False
            },
            {
                "Feature": "Survey Frequency",
                "EPA OOOOb": "Quarterly OGI/Method 21 for large well & compressor sites; Semi annual for medium; Annual for low equipment count (Table 1). Alternative advanced screening allowed if threshold ≤ 3 kg/h (§60.5397b(f)-(g)).",
                "NM Ozone Rule": "AVO inspections: weekly (large) or monthly (small). OGI/Method 21: • Quarterly if PTE ≥ 5 tpy VOC • Semi annual (2–5 tpy) • Annual (< 2 tpy) (§20.2.50.116 C).",
                "NM Gas Waste Rule": "No fixed cadence; operators may earn ALARM credits for continuous/aerial/satellite systems that meet 48h isolation + 15d repair (§19.15.27.9 B).",
                "EU Methane Reg": "Type 1 (detailed OGI/Hi-Flow) every 4mo at compressor/LNG/UGS sites; every 6mo elsewhere. Type 2 (screening) every 12mo for all components (Annex I Part 1).",
                "nm_stricter": True
            },
            {
                "Feature": "Definition of a Leak",
                "EPA OOOOb": "Any OGI plume or Method 21 reading ≥ 500ppm (§60.5397b(c)(8)).",
                "NM Ozone Rule": "Uses the same 500 ppm Method 21 criterion (§20.2.50.116 C(4)).",
                "NM Gas Waste Rule": "No numeric definition; any un-captured gas is 'lost gas' for capture accounting (§19.15.27.8).",
                "EU Methane Reg": "Leak/repair thresholds will be specified in future Commission implementing acts; interim duty is to fix all leaks found (Art 14 § 8).",
                "nm_stricter": False
            },
            {
                "Feature": "Repair Deadlines",
                "EPA OOOOb": "First repair attempt ≤ 5d; completion + verification ≤ 30d unless shutdown required (§60.5397b(h)).",
                "NM Ozone Rule": "Leaks tagged; repair within 15d except OGI-detected plumes, which may follow 30d schedule (§20.2.50.116 E).",
                "NM Gas Waste Rule": "For ALARM credit: isolate leak ≤ 48h & repair ≤ 15d (§19.15.27.9B(1)).",
                "EU Methane Reg": "Obligatory fix 'without delay'; any postponement must be justified to the authority (Art 14 § 9).",
                "nm_stricter": True
            },
        ],
    },

    "Storage Tanks": {
        "icon": "fas fa-database",
        "description": "Rules for controlling emissions from storage vessels that hold crude, condensate or produced water.",
        "nm_highlight": "NM requires 98% control for high-emitting tanks - the strictest standard globally",
        "compliance_gap": 42,
        "comparison": [
            {
                "Feature": "Control Standard",
                "EPA OOOOb": "≥ 95% CH₄ & VOC reduction or keep emissions < 14 tpy CH₄ and < 4 tpy VOC; must use cover + closed vent system (§60.5395b(a)).",
                "NM Ozone Rule": "Existing tanks: 2-10 tpy VOC → 95% control in 3yr; ≥ 10 tpy VOC → 98% control in 1yr. New tanks meet 95/98% on start-up (§20.2.50.123 B).",
                "NM Gas Waste Rule": "No per tank limit; all uncontrolled tank vapour volumes are debited against the operator's 98% statewide capture metric and reported monthly (Form C 115B) (§19.15.27.8 A, G).",
                "EU Methane Reg": "Art 15 § 7: 'commercially available zero emitting storage tanks' required for new/refurb sites. Venting only when unavoidable & strictly necessary, and subject to Art 16 event reporting.",
                "nm_stricter": True
            },
            {
                "Feature": "Monitoring",
                "EPA OOOOb": "Monthly emissions determination; if uncontrolled emissions rise above 4/14 tpy limits operator has 30d to install control (§60.5395b(a)(3) & (i)). Annual closed vent system inspection (§60.5416b).",
                "NM Ozone Rule": "Weekly AVO + monthly electronic monitoring technology scan (if installed); closed vent inspected with OGI semi annual (§20.2.50.123 C).",
                "NM Gas Waste Rule": "Tanks are part of the operator's LDAR or ALARM programme; leaks repaired ≤ 15d for capture credit (§19.15.27.9 B).",
                "EU Methane Reg": "LDAR Type 1 every 6mo + Type 2 annually for above ground tanks (Annex I). Any tank vent/flare event ≥ 8h must be reported within 48h (Art 16 § 2).",
                "nm_stricter": True
            },
        ],
    },

    "Compressors": {
        "icon": "fas fa-cogs",
        "description": "Emission standards for compressor wet seal vents and reciprocating compressor rod packing.",
        "nm_highlight": "NM requires rod packing replacement every 26,000 hours - more frequent than other standards",
        "compliance_gap": 48,
        "comparison": [
            {
                "Feature": "Applicability",
                "EPA OOOOb": "All new/modified centrifugal (wet & dry seal) and reciprocating compressors across production, gathering & boosting, processing and compression segments commencing ≥ 6 Dec 2022 (§60.5380b, §60.5385b).",
                "NM Ozone Rule": "§20.2.50.114 applies to wet seal centrifugals and all reciprocating compressors at tank batteries, gathering/boosting & processing plants; well site compressors excluded.",
                "NM Gas Waste Rule": "Compressors not singled out; any vent counts toward 98% capture and must be flared if safe (§19.15.27.8 A).",
                "EU Methane Reg": "Covers every centrifugal and reciprocating unit from well pads through LNG terminals; subject both to Art 15 zero vent rules and Annex I LDAR cadence.",
                "nm_stricter": False
            },
            {
                "Feature": "Control Standard (Centrifugal)",
                "EPA OOOOb": "Wet seal: capture & destroy ≥ 95% of degassing vent flow (§60.5380b(a)(1)). Dry seal: must meet stringent volumetric vent flow limits per seal (§60.5380b(a)(3)).",
                "NM Ozone Rule": "Existing wet seal units → 95% control within 2yr; new units = 95% (processing) or 98% (other) on start up (§20.2.50.114 B).",
                "NM Gas Waste Rule": "Requires routing to flare rather than vent where safe; all volumes debited against capture ratio (§19.15.27.8 A).",
                "EU Methane Reg": "New/refurbished sites must install zero emitting compressors; existing units replaced 'where commercially available' by 5 Feb 2026 (Art 15 § 5-8).",
                "nm_stricter": True
            },
            {
                "Feature": "Control Standard (Reciprocating)",
                "EPA OOOOb": "Rod packing vent flow ≤ 2 scfm per cylinder; exceedance triggers repair/packing replacement ≤ 90d (§60.5385b(a)).",
                "NM Ozone Rule": "Replace rod packing every 26,000 operating hours or 36 months, or route to 95% control (§20.2.50.114 B(2-4)).",
                "NM Gas Waste Rule": "No numeric limit; rod packing leaks count toward lost gas & 98% capture duty.",
                "EU Methane Reg": "Same zero vent requirement as for centrifugals (Art 15 § 7).",
                "nm_stricter": True
            },
            {
                "Feature": "Monitoring & Repair",
                "EPA OOOOb": "Annual high volume sampler test for seal or rod packing flow; re test within 15d after repair (§60.5380b(a)(7-9); §60.5385b(a)(1-3)).",
                "NM Ozone Rule": "Non resettable hour meter (recips) and monthly closed vent inspection (centrifugals); rod packing collection inspected semi annual (§20.2.50.114 C).",
                "NM Gas Waste Rule": "Leaks detected by either AVO or ALARM must be repaired ≤ 15d for capture credit (§19.15.27.9 B).",
                "EU Methane Reg": "Type 1 LDAR every 4mo at compressor stations; repairs required 'without delay' (Art 14 § 2-3, Annex I).",
                "nm_stricter": False
            }
        ],
    },

    "Well Operations & Flaring": {
        "icon": "fas fa-fire-alt",
        "description": "Rules covering completions, workovers, liquids unloading and venting/flaring restrictions.",
        "nm_highlight": "NM's 98% gas capture rule effectively bans routine flaring - unique globally",
        "compliance_gap": 73,
        "comparison": [
            {
                "Feature": "Liquids Unloading",
                "EPA OOOOb": "If unloading vents, operator must follow BMP plan (pressure draw down, separator use, close vents ASAP) or route gas to ≥ 95% control; records of duration & volume required (§60.5376b(b)-(f)).",
                "NM Ozone Rule": "At least one BMP (plunger lift, artificial lift, auto surf choke, etc.) required to avoid venting; if venting occurs, operator must monitor & log (§20.2.50.117 B-D).",
                "NM Gas Waste Rule": "Venting permitted solely to unload liquids; operator must be on site (if manual), stop venting once stabilised; volume debited to lost gas tally (§19.15.27.8 D(3)).",
                "EU Methane Reg": "Liquids unloading venting deemed unavoidable only if minimised & reported; otherwise prohibited (Art 15 § 3(b) & § 4).",
                "nm_stricter": True
            },
            {
                "Feature": "Well Completions",
                "EPA OOOOb": "Green completion: route initial flowback to separator & sales line; if infeasible, combust; detailed logs + annual e-report (§60.5375b).",
                "NM Ozone Rule": "Not specifically addressed – emissions managed via tank & LDAR rules.",
                "NM Gas Waste Rule": "Mirrors EPA logic: separator ASAP; flaring allowed only when routing to sales not feasible; reporting on Form C 115B (§19.15.27.8 C).",
                "EU Methane Reg": "Routine flaring banned. Flowback gas may be flared/vented only if unavoidable; must justify & report (Art 15 § 1-4).",
                "nm_stricter": False
            },
            {
                "Feature": "General Venting & Flaring",
                "EPA OOOOb": "No routine venting from new pneumatics or tanks; flaring governed by completion rules and other subparts.",
                "NM Ozone Rule": "Flaring addressed via separate NMED permits; Part 50 focuses on VOC controls rather than waste.",
                "NM Gas Waste Rule": "Routine venting & flaring prohibited if it impedes the operator's ability to meet the 98% gas capture mandate (§19.15.27.8 A).",
                "EU Methane Reg": "Art 15: Routine flaring prohibited; venting prohibited except for emergencies or strictly necessary, with event reporting under Art 16.",
                "nm_stricter": True
            },
        ],
    },
}

# --- Create Visualizations ---

# 1. Compliance Gap Analysis - Enhanced Bar Chart
categories = list(REGULATION_DATA.keys())
gaps = [REGULATION_DATA[cat]['compliance_gap'] for cat in categories]

# Create gradient colors based on gap severity
def get_color_for_gap(gap):
    if gap < 30:
        return '#4CAF50'
    elif gap < 50:
        return '#FFC107'
    elif gap < 70:
        return '#FF9800'
    else:
        return '#FF5252'

colors = [get_color_for_gap(gap) for gap in gaps]

fig_gaps = go.Figure()

fig_gaps.add_trace(go.Bar(
    x=categories,
    y=gaps,
    marker=dict(
        color=colors,
        line=dict(color='white', width=2)
    ),
    text=[f"{gap}%" for gap in gaps],
    textposition='outside',
    textfont=dict(size=14, color='#c9d1d9'),
    hovertemplate='<b>%{x}</b><br>%{y}% of facilities not meeting<br>NM standards<extra></extra>'
))

# Add annotations for critical areas
fig_gaps.add_annotation(
    x="Well Operations & Flaring", y=73,
    text="Critical Gap",
    showarrow=True,
    arrowhead=2,
    arrowcolor="#FF5252",
    ax=0, ay=-30,
    font=dict(size=12, color="#FF5252"),
)

# Add target line
fig_gaps.add_hline(y=20, line_dash="dash", line_color="#4CAF50", opacity=0.6)
fig_gaps.add_annotation(
    x=4.5, y=20,
    text="Target: <20%",
    showarrow=False,
    font=dict(size=12, color='#4CAF50'),
    xanchor="left"
)

fig_gaps.update_layout(
    height=400,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(
        showgrid=False,
        tickfont=dict(size=12, color='#c9d1d9'),
        tickangle=-25
    ),
    yaxis=dict(
        title="Facilities Not Meeting NM Standards (%)",
        showgrid=True,
        gridcolor='rgba(48, 54, 61, 0.3)',
        tickfont=dict(size=11, color='#c9d1d9'),
        titlefont=dict(size=12, color='#c9d1d9'),
        range=[0, 80]
    ),
    margin=dict(l=60, r=20, t=20, b=100)
)

# 2. Implementation Timeline - Enhanced Gantt Chart
timeline_data = [
    # EPA
    {'Regulation': 'EPA OOOOb', 'Task': 'New facility compliance', 'Start': '2022-12-06', 'End': '2025-05-07', 'Color': '#FF6B6B'},
    {'Regulation': 'EPA OOOOb', 'Task': 'Annual monitoring begins', 'Start': '2025-05-07', 'End': '2030-12-31', 'Color': '#FFB6C1'},
    
    # NM
    {'Regulation': 'NM Rules', 'Task': '25% pneumatic retrofit', 'Start': '2022-08-05', 'End': '2024-01-01', 'Color': '#4ECDC4'},
    {'Regulation': 'NM Rules', 'Task': '60% pneumatic retrofit', 'Start': '2024-01-01', 'End': '2027-01-01', 'Color': '#45B7D1'},
    {'Regulation': 'NM Rules', 'Task': '100% pneumatic retrofit', 'Start': '2027-01-01', 'End': '2030-01-01', 'Color': '#1E88E5'},
    {'Regulation': 'NM Rules', 'Task': '98% gas capture (ongoing)', 'Start': '2022-08-05', 'End': '2030-12-31', 'Color': '#96CEB4'},
    
    # EU
    {'Regulation': 'EU Methane', 'Task': 'LDAR program submission', 'Start': '2024-07-15', 'End': '2025-05-05', 'Color': '#9C27B0'},
    {'Regulation': 'EU Methane', 'Task': 'Existing equipment retrofit', 'Start': '2024-07-15', 'End': '2026-02-05', 'Color': '#BA68C8'},
]

fig_timeline = go.Figure()

# Add tasks
for idx, item in enumerate(timeline_data):
    fig_timeline.add_trace(go.Scatter(
        x=[item['Start'], item['End']],
        y=[item['Task'], item['Task']],
        mode='lines',
        line=dict(color=item['Color'], width=20),
        showlegend=False,
        hovertemplate='<b>%{y}</b><br>Start: %{x}<br>End: ' + item['End'] + '<extra></extra>',
        name=item['Task']
    ))
    
    # Add task labels
    fig_timeline.add_annotation(
        x=item['Start'], y=item['Task'],
        text=item['Task'].split(' - ')[-1] if ' - ' in item['Task'] else '',
        showarrow=False,
        font=dict(size=10, color='white'),
        xanchor='left',
        xshift=5
    )

# Add current date marker
fig_timeline.add_vline(x='2024-12-15', line_dash="dash", line_color="white", opacity=0.8)
fig_timeline.add_annotation(
    x='2024-12-15', y=7.5,
    text="Today",
    showarrow=True,
    arrowhead=2,
    arrowcolor="white",
    ax=0, ay=-30,
    font=dict(size=12, color='white'),
    bgcolor="rgba(88, 166, 255, 0.9)",
    bordercolor="#58a6ff"
)

# Add critical deadline callouts
critical_dates = [
    {'date': '2024-01-01', 'text': '25% Retrofit\nDeadline Passed', 'y': 2.5},
    {'date': '2027-01-01', 'text': '60% Retrofit\nDeadline', 'y': 3.5},
    {'date': '2030-01-01', 'text': '100% Zero-Bleed\nRequired', 'y': 4.5}
]

for deadline in critical_dates:
    fig_timeline.add_vline(x=deadline['date'], line_dash="dot", line_color="#FFC107", opacity=0.5)

fig_timeline.update_layout(
    height=350,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(
        showgrid=True,
        gridcolor='rgba(48, 54, 61, 0.3)',
        tickfont=dict(size=11, color='#c9d1d9'),
        type='date',
        range=['2022-01-01', '2031-12-31']
    ),
    yaxis=dict(
        showgrid=False,
        tickfont=dict(size=11, color='#c9d1d9'),
        autorange='reversed',
        fixedrange=True
    ),
    margin=dict(l=200, r=20, t=20, b=40)
)

# --- Helper Functions ---
def create_detailed_comparison_card(category, data):
    """Creates an enhanced comparison card with detailed tables"""
    
    # Count NM stricter features
    nm_stricter_count = sum(1 for comp in data['comparison'] if comp.get('nm_stricter', False))
    total_features = len(data['comparison'])
    
    return html.Div(className="detailed-comparison-card glass-card", children=[
        # Header with icon and description
        html.Div(className="comparison-header", children=[
            html.I(className=f"{data['icon']} category-icon-large"),
            html.Div(className="header-content", children=[
                html.H3(category),
                html.P(data['description'], className="category-description"),
                # NM Highlight
                html.Div(className="nm-special-highlight", children=[
                    html.I(className="fas fa-star"),
                    html.Span(data['nm_highlight'])
                ])
            ])
        ]),
        
        # Compliance Gap Indicator
        html.Div(className="gap-indicator-bar", children=[
            html.Div(className="gap-info", children=[
                html.Span("Compliance Gap:", className="gap-label"),
                html.Span(f"{data['compliance_gap']}%", className="gap-percentage")
            ]),
            html.Div(className="gap-bar", children=[
                html.Div(
                    className="gap-fill",
                    style={
                        'width': f"{data['compliance_gap']}%",
                        'backgroundColor': get_color_for_gap(data['compliance_gap'])
                    }
                )
            ])
        ]),
        
        # Detailed Comparison Table
        html.Div(className="comparison-table-wrapper", children=[
            html.Table(className="detailed-comparison-table", children=[
                html.Thead(html.Tr([
                    html.Th("Requirement", className="requirement-header"),
                    html.Th("EPA OOOOb", className="regulation-header"),
                    html.Th("NM Ozone Rule", className="regulation-header nm-ozone"),
                    html.Th("NM Gas Waste Rule", className="regulation-header nm-waste"),
                    html.Th("EU Methane Reg", className="regulation-header")
                ])),
                html.Tbody([
                    html.Tr([
                        html.Td(comp['Feature'], className="feature-name"),
                        html.Td(comp['EPA OOOOb'], className="regulation-detail"),
                        html.Td(
                            comp['NM Ozone Rule'], 
                            className="regulation-detail nm-detail" + (" stricter" if comp.get('nm_stricter', False) else "")
                        ),
                        html.Td(
                            comp['NM Gas Waste Rule'], 
                            className="regulation-detail nm-detail"
                        ),
                        html.Td(comp['EU Methane Reg'], className="regulation-detail")
                    ]) for comp in data['comparison']
                ])
            ])
        ]),
        
        # NM Stringency Summary
        html.Div(className="stringency-summary", children=[
            html.Span(f"NM Requirements Stricter in {nm_stricter_count} of {total_features} Areas", 
                     className="stringency-text"),
            html.Div(className="mini-bar", children=[
                html.Div(
                    className="mini-fill",
                    style={'width': f"{(nm_stricter_count/total_features)*100}%"}
                )
            ])
        ])
    ])

# --- Main Layout ---
regulation_comparison_layout = html.Div([
    # Header Section
    html.Div(className="regulation-header-section glass-card", children=[
        html.H1("Regulatory Comparison Analysis", className="page-title"),
        html.P("Direct comparison of methane regulations with focus on New Mexico's leadership position", 
               className="page-subtitle"),
        
        # Key Statistics
        html.Div(className="regulation-stats-grid", children=[
            html.Div(className="stat-card", children=[
                html.I(className="fas fa-percentage stat-icon"),
                html.Div(children=[
                    html.H3("98%"),
                    html.P("NM Gas Capture Requirement")
                ])
            ]),
            html.Div(className="stat-card", children=[
                html.I(className="fas fa-calendar-alt stat-icon"),
                html.Div(children=[
                    html.H3("2030"),
                    html.P("100% Zero-Bleed Deadline")
                ])
            ]),
            html.Div(className="stat-card", children=[
                html.I(className="fas fa-industry stat-icon"),
                html.Div(children=[
                    html.H3("1,823"),
                    html.P("Facilities Affected")
                ])
            ]),
            html.Div(className="stat-card", children=[
                html.I(className="fas fa-chart-line stat-icon"),
                html.Div(children=[
                    html.H3("73%"),
                    html.P("Max Compliance Gap")
                ])
            ])
        ])
    ]),
    
    # Visualizations Section
    html.Div(className="visualizations-section", children=[
        # Compliance Gap Analysis
        html.Div(className="viz-card glass-card", children=[
            html.H3("Compliance Gap by Category"),
            html.P("Percentage of facilities not meeting New Mexico standards", className="viz-subtitle"),
            dcc.Graph(figure=fig_gaps, config={'displayModeBar': False})
        ]),
        
        # Implementation Timeline
        html.Div(className="viz-card glass-card", children=[
            html.H3("Implementation Timeline"),
            html.P("Key compliance deadlines across all regulations", className="viz-subtitle"),
            dcc.Graph(figure=fig_timeline, config={'displayModeBar': False})
        ])
    ]),
    
    # Detailed Comparisons Section
    html.Div(className="detailed-comparisons-container", children=[
        html.H2("Detailed Regulatory Comparisons", className="section-title"),
        html.P("Click on any requirement to see full regulatory text and implementation guidance", 
               className="section-subtitle"),
        html.Div(className="comparison-cards-grid", children=[
            create_detailed_comparison_card(category, data) 
            for category, data in REGULATION_DATA.items()
        ])
    ])
])