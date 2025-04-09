import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster
from typing import Optional
import re
import os
import time
from geopy.geocoders import Nominatim

#############################################
# UTILITIES & HELPER FUNCTIONS
#############################################
def clean_numeric_column(series: pd.Series) -> pd.Series:
    """
    Convert numeric strings that may use commas as a decimal separator.
    """
    return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce')

#############################################
# MAP DATA FUNCTIONS (FIRST Script – only the map uses this)
#############################################
def load_map_data(file_path: str = "data/blood_data_geocoded.csv") -> pd.DataFrame:
    """
    Loads and cleans the blood donation geocoded data used for the map.
    
    Expected columns include:
      - 'lat'
      - 'lon'
      - 'ÉLIGIBILITÉ_AU_DON.'
      - (optional) 'Age', 'Genre_', etc.
      
    Returns:
        A cleaned pandas DataFrame.
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except Exception as e:
        raise FileNotFoundError(f"Error loading {file_path}: {e}")

    df.columns = [col.strip() for col in df.columns]

    # Standardize the eligibility column if available.
    if "ÉLIGIBILITÉ_AU_DON." in df.columns:
        df['eligible'] = df["ÉLIGIBILITÉ_AU_DON."].str.strip().str.lower() == "eligible"
    else:
        df['eligible'] = False

    # Drop rows missing coordinates.
    df = df.dropna(subset=["lat", "lon"])

    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    if "Taux_d’hémoglobine_" in df.columns:
        df["Taux_d’hémoglobine_"] = clean_numeric_column(df["Taux_d’hémoglobine_"])
    if "Genre_" in df.columns:
        df["Genre_"] = df["Genre_"].str.strip().str.lower()

    return df.copy()

def create_folium_map(df: pd.DataFrame) -> str:
    """
    Creates a Folium map from the DataFrame, using MarkerCluster
    to cluster points. Each marker is styled with an icon whose color 
    depends on the donor’s eligibility (from "ÉLIGIBILITÉ_AU_DON."). 
    Markers with an eligibility of "Eligible" (case-insensitive) are green,
    all others are red.
    
    Returns:
        HTML representation of the Folium map.
    """
    if df.empty:
        m = folium.Map(location=[0, 0], zoom_start=2)
    else:
        # Center the map over the data points.
        map_center = [df["lat"].mean(), df["lon"].mean()]
        m = folium.Map(location=map_center, zoom_start=6)
        
        # Create a MarkerCluster instance.
        marker_cluster = MarkerCluster(disableClusteringAtZoom=12).add_to(m)
        
        for _, row in df.iterrows():
        # Determine icon color based on eligibility.
            eligibility_text = row.get("ÉLIGIBILITÉ_AU_DON.", "N/A").strip()
            if eligibility_text.lower() == "eligible":
                icon_color = "green"
                colored_eligibility = f"<span style='color: green;'>{eligibility_text}</span>"
            else:
                icon_color = "red"
                colored_eligibility = f"<span style='color: red;'>{eligibility_text}</span>"
            
        # Clean extra spaces in the 'profession' field if present.
            profession = row.get("profession", "Inconnu")
            profession = re.sub(r'\s+', ' ', str(profession)).strip()
        
        # Build popup content with conditional formatting on "Éligibilité"
            popup_content = (
                f"<b>Age:</b> {row.get('Age', 'N/A')}<br>"
                f"<b>Genre:</b> {row.get('Genre_', 'N/A')}<br>"
                f"<b>Hémoglobine:</b> {row.get('Taux_d’hémoglobine_', 'N/A')}<br>"
                f"<b>Éligibilité:</b> {colored_eligibility}<br>"
                f"<b>Arrondissement:</b> {row.get('Arrondissement_de_résidence_', 'N/A')}<br>"
                f"<b>Groupe sanguin:</b> <span style='color: red;'>à compléter</span><br>"
            )
        
        # Create a marker with the determined icon color.
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=popup_content,
                icon=folium.Icon(color=icon_color, icon="info-sign")
            ).add_to(marker_cluster)

    return m._repr_html_()

#############################################
# KPI DATA FUNCTIONS (SECOND Script – all other sections use this)
#############################################
def nettoyer_arrondissement(val):
    """
    Clean and standardize arrondissement names.
    """
    if pd.isna(val):
        return "Douala 1"
    
    val = val.strip().lower()
    douala_1 = ["douala", "douala non precise", "douala (non précisé )", "pas précisé",
                "pas precise", "pas precise ", "pas mentionné", "non précisé",
                "non precise", "non precisé", "ras", "ras ", "r a s", "r a s ",
                "r a s ", "dcankongmondo", "deido", "pas mentionne"]
    douala_2 = ["douala 2"]
    douala_3 = ["douala 3", "bomono ba mbegue", "oyack", "ngodi bakoko", "ngodi bakoko "]
    douala_4 = ["douala 4", "boko"]
    douala_5 = ["douala 5"]
    douala_6 = ["douala 6"]

    mapping = {
        **dict.fromkeys(douala_1, "Douala 1"),
        **dict.fromkeys(douala_2, "Douala 2"),
        **dict.fromkeys(douala_3, "Douala 3"),
        **dict.fromkeys(douala_4, "Douala 4"),
        **dict.fromkeys(douala_5, "Douala 5"),
        **dict.fromkeys(douala_6, "Douala 6"),
        "bafoussam": "Bafoussam",
        "dschang": "Dschang",
        "buea": "Buea",
        "kribi": "Kribi",
        "njombe": "Njombe",
        "tiko": "Tiko",
        "edea": "Edea",
        "manjo": "Manjo",
        "west": "Région de l'Ouest",
        "yaoundé": "Yaoundé",
        "nkouabang": "Yaoundé",
        "yaounde": "Yaoundé",
        "meiganga": "Meiganga",
        "batie": "Batié",
        "sud ouest tombel": "Tombel",
        "limbe": "Limbe",
        "limbe ": "Limbe"
    }
    return mapping.get(val, val.title())

def geocode_location(location):
    """
    Geocodes a given location using Nominatim.
    A short delay is included to avoid overwhelming the geocoding service.
    """
    geolocator = Nominatim(user_agent="blood_donation_app")
    try:
        time.sleep(2)  # Avoid service blocking.
        geo = geolocator.geocode(location + ", Cameroun")
        return (geo.latitude, geo.longitude) if geo else (None, None)
    except Exception as e:
        return (None, None)

def load_and_prepare_kpi_data(start_date=None, end_date=None):
    """
    Loads the cleaned donor data (from 2019) and prepares the KPI statistics.
    Also performs intelligent caching of arrondissement geocoding.
    
    Returns:
        df: DataFrame with donor data.
        district_stats: Aggregated stats per arrondissement.
    """
    df = pd.read_csv('data/Candidat_au_don_2019_cleaned.csv', sep=';')
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("’", "'")
    df['arrondissement_de_résidence'] = df['arrondissement_de_résidence'].apply(nettoyer_arrondissement)
    cache_path = 'data/geocoded_coords.csv'

    if os.path.exists(cache_path):
        coords_df = pd.read_csv(cache_path)
    else:
        coords_df = pd.DataFrame(columns=["arrondissement_de_résidence", "latitude", "longitude"])

    arrondissements_existants = set(coords_df["arrondissement_de_résidence"].dropna())
    arrondissements_dans_data = set(df["arrondissement_de_résidence"].dropna())
    nouveaux = list(arrondissements_dans_data - arrondissements_existants)

    if nouveaux:
        print(f"Geocoding {len(nouveaux)} new arrondissement(s)...")
        nouveaux_coords = []
        for loc in nouveaux:
            lat, lon = geocode_location(loc)
            nouveaux_coords.append({
                "arrondissement_de_résidence": loc,
                "latitude": lat,
                "longitude": lon
            })
        nouveaux_df = pd.DataFrame(nouveaux_coords)
        coords_df = pd.concat([coords_df, nouveaux_df], ignore_index=True)
        coords_df.to_csv(cache_path, index=False)
        print("Cache updated.")

    df = pd.merge(df, coords_df, on='arrondissement_de_résidence', how='left')
    df = df.dropna(subset=['latitude', 'longitude'])

    district_stats = df.groupby('arrondissement_de_résidence').agg(
        total_candidats=('éligibilité_au_don.', 'count'),
        pourcentage_eligibles=('éligibilité_au_don.', lambda x: (x == 'eligible').mean() * 100),
        nombre_hommes=('genre', lambda x: (x == 'homme').sum()),
        latitude=('latitude', 'first'),
        longitude=('longitude', 'first')
    ).reset_index()
    print("KPI data loaded:", district_stats.shape)
    return df, district_stats

#############################################
# COMBINED DASH LAYOUT
#############################################
def get_map_layout(start_date=None, end_date=None):
    """
    Build the combined dashboard layout:
      - KPI cards/statistics from the second data source.
      - A Folium map (embedded via an iframe) using the first data source that clusters markers.
    """
    # Load and compute KPI stats using the second script’s data.
    df_kpi, district_stats = load_and_prepare_kpi_data(start_date, end_date)
    total_donors = len(df_kpi)
    taux_eligibilite = round((df_kpi["éligibilité_au_don."] == "eligible").mean() * 100, 1)
    total_hommes = (df_kpi["genre"] == "homme").sum()
    total_femmes = (df_kpi["genre"] == "femme").sum()
    
    # Load map data from the first script’s CSV.
    df_map = load_map_data("data/blood_data_geocoded.csv")
    folium_map_html = create_folium_map(df_map)
    
    layout = html.Div([
        html.H3('Donor Distribution Dashboard'),
        dcc.DatePickerRange(
            id='date-picker-range',
            display_format='DD-MM-YYYY',
            start_date_placeholder_text='Date début',
            end_date_placeholder_text='Date fin',
            style={"margin-bottom": "20px"}
        ),
        # KPI Cards Section
        html.Div([
            html.Div([
                html.H4("🧍‍ Total Donors"),
                html.H2(f"{total_donors}")
            ], className="card", style={
                "padding": "10px", "border": "1px solid #ddd", "border-radius": "5px"
            }),
            html.Div([
                html.H4("🩸 Eligibility Rate"),
                html.H2(f"{taux_eligibilite}%")
            ], className="card", style={
                "padding": "10px", "border": "1px solid #ddd", "border-radius": "5px"
            }),
            html.Div([
                html.H4("👨 Men / 👩 Women"),
                html.H2(f"{total_hommes} / {total_femmes}")
            ], className="card", style={
                "padding": "10px", "border": "1px solid #ddd", "border-radius": "5px"
            })
        ], style={"display": "flex", "gap": "20px"}),
        html.Br(),
        # Folium Map Section with clustering
        html.Div([
            html.Iframe(
                srcDoc=folium_map_html,
                width="100%",
                height="600",
                style={"border": "none"}
            )
        ], className="graph-container"),
        # Legend Section
        html.Div([
            html.H4('Legend', style={"font-size": "16px", "margin-bottom": "5px"}),
            html.P("This map shows donor locations using a clustering feature to group nearby points.",
                   style={"font-size": "14px", "margin": "0"}),
            html.P("Markers are colored based on eligibility (green = Eligible, red = Non-eligible).",
                   style={"font-size": "14px", "margin": "0"}),
            html.P("Click on a cluster to zoom in and reveal individual markers.",
                   style={"font-size": "14px", "margin": "0"})
        ], className="legend", style={
            "background-color": "#f9f9f9",
            "padding": "10px",
            "border-radius": "5px",
            "margin-top": "20px",
            "font-size": "14px",
            "max-width": "600px"
        })
    ])
    return layout

#############################################
# MAIN: INITIALIZE THE DASH APP
#############################################
if __name__ == "__main__":
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = get_map_layout()
    app.run_server(debug=True)
