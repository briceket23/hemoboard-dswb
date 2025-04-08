# objectives/advanced_map.py

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
from typing import Optional

# Global cache for the map DataFrame
_CACHED_MAP_DF: Optional[pd.DataFrame] = None

def load_data(file_path: str = "data/blood_data_geocoded.csv") -> pd.DataFrame:
    """
    Load and clean the geocoded blood donation data.
    
    Expected columns: 'lat', 'lon', 'ÉLIGIBILITÉ_AU_DON.', 'Age', 'Genre_', 'Taux_d’hémoglobine_'
    
    Args:
        file_path: Path to the CSV file.
    
    Returns:
        A pandas DataFrame with cleaned donor map data.
    """
    global _CACHED_MAP_DF
    if _CACHED_MAP_DF is not None:
        return _CACHED_MAP_DF.copy()
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise FileNotFoundError(f"Error loading {file_path}: {e}")

    # Create a boolean 'eligible' column by standardizing the eligibility text.
    df['eligible'] = df['ÉLIGIBILITÉ_AU_DON.'].str.strip().str.lower() == "eligible"
    # Drop rows missing latitude or longitude.
    df = df.dropna(subset=["lat", "lon"])
    # Ensure that numeric columns are properly typed.
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["Taux_d’hémoglobine_"] = pd.to_numeric(df["Taux_d’hémoglobine_"], errors="coerce")
    
    _CACHED_MAP_DF = df.copy()
    return df.copy()

def get_advanced_map_layout(start_date: Optional[str] = None, end_date: Optional[str] = None) -> html.Div:
    """
    Build the Dash layout for the advanced interactive donor map.
    
    Args:
        start_date: (Not used yet) Optionally filter by start date.
        end_date: (Not used yet) Optionally filter by end date.
    
    Returns:
        A Dash HTML layout (Div) containing filters and the map graph.
    """
    df = load_data()
    
    # Build filter controls for age, gender, eligibility, hemoglobin level, clustering, and map style
    layout = dbc.Container([
        dbc.Row(html.H1("Advanced Donor Map with Clustering and Interactive Filters"), className="my-3"),
        dbc.Row([
            dbc.Col([
                html.H4("Filters"),
                
                # Age filter
                html.Label("Age Range"),
                dcc.RangeSlider(
                    id="age-slider",
                    min=int(df["Age"].min()),
                    max=int(df["Age"].max()),
                    value=[int(df["Age"].min()), int(df["Age"].max())],
                    marks={i: str(i) for i in range(int(df["Age"].min()), int(df["Age"].max())+1, 5)}
                ),
                html.Br(),
                
                # Hemoglobin filter
                html.Label("Hemoglobin Level"),
                dcc.RangeSlider(
                    id="hemoglobin-slider",
                    min=int(df["Taux_d’hémoglobine_"].min()),
                    max=int(df["Taux_d’hémoglobine_"].max()),
                    value=[int(df["Taux_d’hémoglobine_"].min()), int(df["Taux_d’hémoglobine_"].max())],
                    marks={i: str(i) for i in range(int(df["Taux_d’hémoglobine_"].min()),
                                                      int(df["Taux_d’hémoglobine_"].max())+1, 5)}
                ),
                html.Br(),
                
                # Gender filter
                html.Label("Gender"),
                dcc.Dropdown(
                    id="gender-dropdown",
                    options=[{"label": g, "value": g} for g in sorted(df["Genre_"].dropna().unique())],
                    value=sorted(df["Genre_"].dropna().unique()),
                    multi=True
                ),
                html.Br(),
                
                # Eligibility filter
                html.Label("Eligibility"),
                dcc.RadioItems(
                    id="eligibility-radio",
                    options=[
                        {"label": "All", "value": "all"},
                        {"label": "Eligible", "value": "eligible"},
                        {"label": "Not Eligible", "value": "not_eligible"}
                    ],
                    value="all",
                    labelStyle={"display": "inline-block", "margin-right": "10px"}
                ),
                html.Br(),
                
                # Clustering toggle
                html.Label("Point Clustering"),
                dcc.RadioItems(
                    id="clustering-toggle",
                    options=[
                        {"label": "Enable Clustering", "value": "enable"},
                        {"label": "Disable Clustering", "value": "disable"}
                    ],
                    value="enable",
                    labelStyle={"display": "inline-block", "margin-right": "10px"}
                ),
                html.Br(),
                
                # Map style selector
                html.Label("Map Style"),
                dcc.Dropdown(
                    id="map-style-dropdown",
                    options=[
                        {"label": "Carto Positron", "value": "carto-positron"},
                        {"label": "Open Street Map", "value": "open-street-map"},
                        {"label": "Stamen Terrain", "value": "stamen-terrain"}
                    ],
                    value="carto-positron",
                    clearable=False
                )
            ], width=3),
            dbc.Col([
                html.Div(id="donor-count", style={"marginBottom": "10px", "fontWeight": "bold"}),
                dcc.Graph(id="advanced-map-graph")
            ], width=9)
        ])
    ], fluid=True)
    
    return layout

def get_map_layout() -> html.Div:
    """
    Build a basic donor distribution map layout.
    
    Returns:
        A Dash HTML Div containing the donor map.
    """
    df = load_data()
    fig = px.scatter_mapbox(
        df,
        lat="lat",
        lon="lon",
        hover_name="Genre_",
        hover_data={"Age": True, "Taux_d’hémoglobine_": ":.1f", "eligible": True},
        color="eligible",
        color_discrete_map={True: "#2ecc71", False: "#e74c3c"},
        size="Taux_d’hémoglobine_",
        size_max=15,
        zoom=5,
        height=700
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_center={"lat": df["lat"].mean(), "lon": df["lon"].mean()},
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )
    return html.Div([
        html.H3("Donor Distribution Map"),
        dcc.Graph(figure=fig)
    ])

def init_callbacks(app: dash.Dash) -> None:
    """
    Initialize Dash callbacks for interactive filtering of the advanced map.
    
    Args:
        app: The Dash application instance.
    """
    @app.callback(
        [Output("advanced-map-graph", "figure"),
         Output("donor-count", "children")],
        [Input("age-slider", "value"),
         Input("hemoglobin-slider", "value"),
         Input("gender-dropdown", "value"),
         Input("eligibility-radio", "value"),
         Input("clustering-toggle", "value"),
         Input("map-style-dropdown", "value")]
    )
    def update_map(age_range, hemoglobin_range, genders, eligibility_filter, clustering_toggle, map_style):
        df = load_data()

        # Combine filter conditions into a single mask.
        mask = df["Age"].between(age_range[0], age_range[1]) & \
               df["Taux_d’hémoglobine_"].between(hemoglobin_range[0], hemoglobin_range[1]) & \
               df["Genre_"].isin(genders)
        if eligibility_filter == "eligible":
            mask &= (df["eligible"] == True)
        elif eligibility_filter == "not_eligible":
            mask &= (df["eligible"] == False)
        filtered = df[mask]

        donor_count_text = f"Total donors displayed: {len(filtered)}"

        # Create the scatter mapbox figure with filtered data.
        fig = px.scatter_mapbox(
            filtered,
            lat="lat",
            lon="lon",
            hover_name="Genre_",
            hover_data={"Age": True, "Taux_d’hémoglobine_": ":.1f", "eligible": True},
            color="eligible",
            color_discrete_map={True: "#2ecc71", False: "#e74c3c"},
            size="Taux_d’hémoglobine_",
            size_max=15,
            zoom=5,
            height=700
        )
        # Enable clustering if selected.
        if clustering_toggle == "enable":
            fig.update_traces(
                cluster={
                    'enabled': True,
                    'size': 20,
                    'step': [10, 30, 50],
                    'color': 'rgba(231, 76, 60, 0.3)'
                }
            )
        # Update layout with selected map style.
        fig.update_layout(
            mapbox_style=map_style,
            mapbox_center={"lat": df["lat"].mean(), "lon": df["lon"].mean()},
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig, donor_count_text

if __name__ == "__main__":
    # Standalone execution for testing the advanced map layout.
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = get_advanced_map_layout()
    init_callbacks(app)
    app.run(debug=True)
