# central_app.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State

# App initialization with a responsive meta tag and external stylesheet.
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.FLATLY], 
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
)
app.title = "HEMOBOARD"

# Import page layouts
from objectives.map_donor_distribution import get_map_layout
from objectives.health_conditions import get_health_conditions_layout
from objectives.donor_clustering import get_clustering_layout
from objectives.campaign_effectiveness import get_campaign_layout
from objectives.donor_retention import get_retention_layout
from objectives.sentiment_analysis import get_sentiment_layout
from objectives.eligibility_prediction import get_prediction_layout

# Security Compliance Modal (unchanged)
compliance_modal = dbc.Modal(
    [
        dbc.ModalHeader(html.H3("Data Security Compliance v1.2.3", className="compliance-header")),
        dbc.ModalBody([
            html.Div([
                html.H4("Security Framework", className="compliance-subheader"),
                html.Ul([
                    html.Li("GDPR-compliant data processing", className="compliance-item"),
                    html.Li("HIPAA-compliant health data handling", className="compliance-item"),
                    html.Li("ISO 27001 certified infrastructure", className="compliance-item"),
                ], className="compliance-list"),
                html.Hr(className="compliance-divider"),
                html.H4("Encryption Standards", className="compliance-subheader"),
                html.Div([
                    dbc.Badge("AES-256", color="primary", className="security-badge"),
                    dbc.Badge("TLS 1.3", color="primary", className="security-badge"),
                    dbc.Badge("PBKDF2-HMAC", color="primary", className="security-badge"),
                ], className="badge-container"),
                html.Hr(className="compliance-divider"),
                html.Div([
                    html.H5("Audit Timeline", className="compliance-subheader"),
                    html.Div([
                        html.P("Last Audit: 2024-02-15 (v1.2.3)", className="audit-item"),
                        html.P("Next Audit: 2024-05-15", className="audit-item"),
                        html.P("Certification Expiry: 2025-01-01", className="audit-item"),
                    ], className="audit-timeline")
                ])
            ], className="compliance-content")
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-compliance", className="ml-auto", outline=True, color="primary")
        )
    ],
    id="compliance-modal",
    size="lg",
    className="compliance-modal"
)

# App layout
app.layout = html.Div([
    dcc.Location(id="url"),
    compliance_modal,
    
    # Store for sidebar visibility state; True = visible, False = hidden.
    dcc.Store(id='sidebar-visible', data=True),
    
    # Sidebar wrapper: We use its className to toggle visibility.
    html.Div(
        [
            html.Img(src="/assets/banner.png", className="sidebar-banner"),
            html.H2("HEMOBOARD-DSWB", className="app-title"),
            html.Hr(className="sidebar-divider"),
            dbc.Nav(
                [
                    dbc.NavLink(html.Span(["🗺️ Donor Map"], className="nav-text"),
                                href="/", active="exact", className="nav-link"),
                    dbc.NavLink(html.Span(["🩺 Health Conditions"], className="nav-text"),
                                href="/health", active="exact", className="nav-link"),
                    dbc.NavLink(html.Span(["👥 Donor Clustering"], className="nav-text"),
                                href="/clustering", active="exact", className="nav-link"),
                    dbc.NavLink(html.Span(["📊 Campaign Analytics"], className="nav-text"),
                                href="/campaign", active="exact", className="nav-link"),
                    dbc.NavLink(html.Span(["♻️ Retention Analysis"], className="nav-text"),
                                href="/retention", active="exact", className="nav-link"),
                    dbc.NavLink(html.Span(["💬 Feedback Analysis"], className="nav-text"),
                                href="/sentiment", active="exact", className="nav-link"),
                    dbc.NavLink(html.Span(["🔮 Eligibility Predictor"], className="nav-text"),
                                href="/prediction", active="exact", className="nav-link"),
                ],
                vertical=True,
                pills=True,
                className="nav-container"
            ),
            html.Div(
                [
                    html.Img(src="/assets/down.png", className="sidebar-footer-img", 
                             style={"width": "50%", "height": "auto"}),
                    html.Span("Data Security Compliance v1.2.3", id="compliance-footer",
                              className="footer-text", n_clicks=0)
                ],
                className="sidebar-footer"
            )
        ],
        id="app-sidebar",
        className="app-sidebar"  # The visible/hidden state will be toggled via className.
    ),
    
    # Fixed sidebar toggle arrow.
    html.Div(
        id="sidebar-toggle-arrow",
        children="←",  # Initially, the sidebar is visible so use left arrow (click to hide).
        n_clicks=0,
        className="sidebar-toggle-arrow"
    ),
    
    # Main content section
    html.Div(
        [
            dcc.Loading(
                id="loading-content",
                type="circle",
                children=html.Div(id="page-content", className="page-content")
            )
        ],
        className="main-content-container"
    ),
    
    dcc.Store(id='global-filters-store')
])

# Callback to toggle the compliance modal on clicking the footer or close button.
@app.callback(
    Output("compliance-modal", "is_open"),
    [Input("compliance-footer", "n_clicks"),
     Input("close-compliance", "n_clicks")],
    [State("compliance-modal", "is_open")]
)
def toggle_compliance_modal(n_footer, n_close, is_open):
    if n_footer or n_close:
        return not is_open
    return is_open

# Callback to update the sidebar-visible store.
@app.callback(
    Output("sidebar-visible", "data"),
    [Input("sidebar-toggle-arrow", "n_clicks")],
    [State("sidebar-visible", "data")]
)
def update_sidebar_store(n_clicks, current_state):
    if n_clicks:
        return not current_state
    return current_state

# Callback to update the sidebar toggle arrow text based on visibility.
@app.callback(
    Output("sidebar-toggle-arrow", "children"),
    [Input("sidebar-visible", "data")]
)
def update_toggle_arrow(is_visible):
    # When visible, display a left arrow (click to hide); when hidden, right arrow (click to show)
    return "←" if is_visible else "→"

# Callback to update the sidebar's className based on visibility.
@app.callback(
    Output("app-sidebar", "className"),
    [Input("sidebar-visible", "data")]
)
def update_sidebar_class(is_visible):
    base_class = "app-sidebar"
    if not is_visible:
        return f"{base_class} sidebar-hidden"
    return base_class

# Callback to update the toggle arrow's position based on sidebar visibility.
@app.callback(
    Output("sidebar-toggle-arrow", "style"),
    [Input("sidebar-visible", "data")]
)
def update_toggle_arrow_style(is_visible):
    # If sidebar is visible, position arrow to the right of sidebar,
    # Otherwise, near the left edge.
    if is_visible:
        return {"left": "280px", "top": "50%", "transform": "translateY(-50%)"}
    else:
        return {"left": "0", "top": "50%", "transform": "translateY(-50%)"}

# Routing callback: Render page content based on the URL.
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return html.Div([
            html.Div([
                html.Label("📅 Filtrer par date de remplissage :", style={"font-weight": "bold", "margin-right": "10px"}),
                dcc.DatePickerRange(
                    id='date-range-picker',
                    start_date_placeholder_text="Début",
                    end_date_placeholder_text="Fin",
                    display_format='YYYY-MM-DD',
                    style={"padding": "10px"}
                )
            ], style={"margin-bottom": "20px", "display": "flex", "align-items": "center", "gap": "10px"}),

            html.Div(id="map-container", children=get_map_layout(None, None))
        ])

    elif pathname == "/health":
        return html.Div([
            html.Div([
                html.Label("📅 Filtrer par date de remplissage :", style={"font-weight": "bold", "margin-right": "10px"}),
                dcc.DatePickerRange(
                    id='health-date-picker',
                    start_date_placeholder_text="Début",
                    end_date_placeholder_text="Fin",
                    display_format='YYYY-MM-DD',
                    style={"padding": "10px"}
                )
            ], style={"margin-bottom": "20px", "display": "flex", "align-items": "center", "gap": "10px"}),

            html.Div(id="health-container", children=get_health_conditions_layout(None, None))
        ])

    elif pathname == "/clustering":
        return html.Div([
            html.Div([
                html.Label("📅 Filtrer par date de remplissage :", style={"font-weight": "bold", "margin-right": "10px"}),
                dcc.DatePickerRange(
                    id='cluster-date-picker',
                    start_date_placeholder_text="Début",
                    end_date_placeholder_text="Fin",
                    display_format='YYYY-MM-DD',
                    style={"padding": "10px"}
                )
            ], style={"margin-bottom": "20px", "display": "flex", "align-items": "center", "gap": "10px"}),

            html.Div(id="cluster-container")
        ])
    elif pathname == "/campaign":
        return get_campaign_layout()
    elif pathname == "/retention":
        return html.Div([
            html.Div([
                html.Label("📅 Filtrer par date :", style={"font-weight": "bold", "margin-right": "10px"}),
                dcc.DatePickerRange(
                    id='retention-date-picker',
                    start_date_placeholder_text="Début",
                    end_date_placeholder_text="Fin",
                    display_format='YYYY-MM-DD',
                    style={"padding": "10px"}
                )
            ], style={"margin-bottom": "20px", "display": "flex", "align-items": "center", "gap": "10px"}),
    
            html.Div(id="retention-container", children=get_retention_layout(None, None))
        ])
        

    elif pathname == "/sentiment":
        return get_sentiment_layout()
    elif pathname == "/prediction":
        return get_prediction_layout()
    else:
        return html.H1("404: Page introuvable")

@app.callback(
    Output("map-container", "children"),
    Input("date-range-picker", "start_date"),
    Input("date-range-picker", "end_date")
)
def update_map_layout(start_date, end_date):
    return get_map_layout(start_date, end_date)

@app.callback(
    Output("health-container", "children"),
    Input("health-date-picker", "start_date"),
    Input("health-date-picker", "end_date")
)
def update_health_layout(start_date, end_date):
    return get_health_conditions_layout(start_date, end_date)

@app.callback(
    Output("cluster-container", "children"),
    Input("cluster-date-picker", "start_date"),
    Input("cluster-date-picker", "end_date")
)
def update_cluster_layout(start_date, end_date):
    return get_clustering_layout(start_date, end_date)

@app.callback(
    Output("retention-container", "children"),
    Input("retention-date-picker", "start_date"),
    Input("retention-date-picker", "end_date")
)
def update_retention_layout(start_date, end_date):
    return get_retention_layout(start_date, end_date)

if __name__ == "__main__":
    app.run(debug=True, dev_tools_props_check=False)
