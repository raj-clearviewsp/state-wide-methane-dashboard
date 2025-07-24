# app.py

import dash
from dash import Dash, dcc, html, Input, Output, State
import plotly.io as pio
from datetime import datetime

# --- App Initialization and Configuration ---
# Use a professional Plotly template for charts
pio.templates.default = "plotly_dark"

app = Dash(__name__, suppress_callback_exceptions=True,
           meta_tags=[{'name': 'viewport',
                       'content': 'width=device-width, initial-scale=1.0'}],
           external_stylesheets=['https://use.fontawesome.com/releases/v5.8.1/css/all.css'])

app.title = "New Mexico Methane Compliance Platform"
server = app.server

# --- Import Layouts ---
# Import the layout modules after the app is initialized
from layouts.regulation_view import regulation_comparison_layout
from layouts.state_view import state_summary_layout
from layouts.facility_view import facility_detail_layout

# --- Navigation Items ---
nav_items = [
    {
        'name': 'State Overview',
        'href': '/state-summary',
        'icon': 'fas fa-map-marked-alt',
        'description': 'Statewide compliance analysis'
    },
    {
        'name': 'Regulations',
        'href': '/regulations',
        'icon': 'fas fa-balance-scale',
        'description': 'Regulatory framework comparison'
    },
    {
        'name': 'Facility Analysis',
        'href': '/facility-detail',
        'icon': 'fas fa-industry',
        'description': 'Detailed facility compliance'
    }
]

# --- Main Application Layout ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    # Top Bar
    html.Div(className="top-bar", children=[
        html.Div(className="top-bar-content", children=[
            # Logo/Brand Section
            html.Div(className="brand-section", children=[
                html.I(className="fas fa-cloud brand-icon"),
                html.Div(className="brand-text", children=[
                    html.Span("New Mexico", className="brand-state"),
                    html.Span("Methane Compliance Platform", className="brand-title")
                ])
            ]),
            
            # Status Indicators
            html.Div(className="status-section", children=[
                html.Div(className="status-item", children=[
                    html.I(className="fas fa-database"),
                    html.Span("1,823 Facilities")
                ]),
                html.Div(className="status-item", children=[
                    html.I(className="fas fa-clock"),
                    html.Span(f"Updated {datetime.now().strftime('%b %d, %Y')}")
                ]),
                html.Div(className="status-item alert", children=[
                    html.I(className="fas fa-exclamation-triangle"),
                    html.Span("470 Critical")
                ])
            ])
        ])
    ]),
    
    # Main Container
    html.Div(className="main-container", children=[
        # Sidebar Navigation
        html.Nav(className="sidebar", children=[
            # Navigation Links
            html.Div(className="nav-links", children=[
                dcc.Link(
                    href=item['href'],
                    className="nav-item",
                    id=f"nav-{item['href']}",
                    children=[
                        html.I(className=item['icon']),
                        html.Div(className="nav-text", children=[
                            html.Span(item['name'], className="nav-title"),
                            html.Span(item['description'], className="nav-description")
                        ])
                    ]
                ) for item in nav_items
            ]),
            
            # Bottom Section
            html.Div(className="sidebar-bottom", children=[
                # Quick Stats
                html.Div(className="quick-stats", children=[
                    html.H4("Quick Stats", className="stats-title"),
                    html.Div(className="stat-row", children=[
                        html.Span("Overall Compliance"),
                        html.Span("71.3%", className="stat-value")
                    ]),
                    html.Div(className="stat-row", children=[
                        html.Span("EU Ready"),
                        html.Span("42%", className="stat-value warning")
                    ]),
                    html.Div(className="stat-row", children=[
                        html.Span("Monthly Impact"),
                        html.Span("$2.4M", className="stat-value danger")
                    ])
                ]),
                
                # Help Section
                html.Div(className="help-section", children=[
                    html.I(className="fas fa-question-circle"),
                    html.Span("Need help? "),
                    html.A("View Documentation", href="#", className="help-link")
                ])
            ])
        ]),
        
        # Content Area
        html.Div(className="content-area", children=[
            # Page Header (dynamic based on current page)
            html.Div(id="page-header", className="page-header"),
            
            # Page Content
            html.Div(id='page-content', className="page-content")
        ])
    ])
])

# --- Callbacks ---

# Update active navigation state and page content
@app.callback(
    [Output('page-content', 'children'),
     Output('page-header', 'children')] + 
    [Output(f"nav-{item['href']}", 'className') for item in nav_items],
    Input('url', 'pathname')
)
def update_page_and_nav(pathname):
    # Default to state summary if no path
    if not pathname or pathname == '/':
        pathname = '/state-summary'
    
    # Determine active page
    page_content = None
    page_header = None
    nav_classes = []
    
    for item in nav_items:
        if pathname == item['href']:
            nav_classes.append('nav-item active')
            
            # Set page content
            if pathname == '/state-summary':
                page_content = state_summary_layout
                page_header = create_page_header(
                    "State Overview",
                    "Monitor compliance across all New Mexico oil & gas facilities",
                    "fas fa-map-marked-alt"
                )
            elif pathname == '/facility-detail':
                page_content = facility_detail_layout
                page_header = create_page_header(
                    "Facility Analysis",
                    "Deep dive into facility-specific compliance details",
                    "fas fa-industry"
                )
            elif pathname == '/regulations':
                page_content = regulation_comparison_layout
                page_header = create_page_header(
                    "Regulatory Framework",
                    "Compare EPA, New Mexico, and EU methane regulations",
                    "fas fa-balance-scale"
                )
        else:
            nav_classes.append('nav-item')
    
    # Default fallback
    if page_content is None:
        page_content = state_summary_layout
        page_header = create_page_header(
            "State Overview",
            "Monitor compliance across all New Mexico oil & gas facilities",
            "fas fa-map-marked-alt"
        )
        nav_classes[0] = 'nav-item active'
    
    return [page_content, page_header] + nav_classes

def create_page_header(title, subtitle, icon):
    """Create a consistent page header"""
    return html.Div(className="page-header-content", children=[
        html.Div(className="page-title-section", children=[
            html.I(className=f"{icon} page-icon"),
            html.Div(children=[
                html.H1(title, className="page-title"),
                html.P(subtitle, className="page-subtitle")
            ])
        ]),
        # Action buttons (could be made page-specific)
        html.Div(className="page-actions", children=[
            html.Button(children=[
                html.I(className="fas fa-download"),
                html.Span("Export Report")
            ], className="btn btn-secondary"),
            html.Button(children=[
                html.I(className="fas fa-filter"),
                html.Span("Filters")
            ], className="btn btn-primary")
        ])
    ])

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)