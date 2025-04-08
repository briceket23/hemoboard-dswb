# donor_retention.py

import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output, callback
import dash
import dash_bootstrap_components as dbc
from typing import Optional, Tuple

# Global cache for the donor retention DataFrame
_CACHED_RETENTION_DF: Optional[pd.DataFrame] = None

def load_retention_data(file_path: str = "data/Candidat_au_don_2019_cleaned.csv") -> pd.DataFrame:
    """
    Load and clean the donor retention data.
    
    Args:
        file_path: Path to the CSV file.
    
    Returns:
        Cleaned pandas DataFrame with donor data.
    """
    global _CACHED_RETENTION_DF
    if _CACHED_RETENTION_DF is not None:
        return _CACHED_RETENTION_DF.copy()
    
    try:
        df_cand = pd.read_csv(file_path, sep=";")
    except Exception as e:
        raise FileNotFoundError(f"Error loading {file_path}: {e}")

    # Normalize column names using a helper function
    df_cand.columns = [normalize_column_name(c) for c in df_cand.columns]

    # Convert the date column and extract month-year period
    df_cand["date_de_remplissage_de_la_fiche"] = pd.to_datetime(
        df_cand["date_de_remplissage_de_la_fiche"], errors="coerce"
    )
    df_cand["mois"] = df_cand["date_de_remplissage_de_la_fiche"].dt.to_period("M").astype(str)

    # Standardize genre column
    df_cand["genre"] = df_cand["genre"].str.lower()

    # Create indicator columns for eligibility and donor fidelity
    df_cand["eligibilite"] = df_cand["eligibilite_au_don."].str.lower().str.strip() == "eligible"
    df_cand["fidele"] = df_cand["a-t-il_(elle)_deja_donne_le_sang"].str.lower().str.strip() == "oui"

    # Process the age column; convert to numeric and filter for valid ages
    df_cand["age"] = pd.to_numeric(df_cand["age"], errors="coerce")
    df_cand = df_cand[df_cand["age"].between(15, 80)]
    
    # Create age bins
    df_cand["tranche_age"] = pd.cut(
        df_cand["age"],
        bins=[15, 25, 35, 45, 55, 65, 80],
        labels=["15-25", "26-35", "36-45", "46-55", "56-65", "66-80"]
    )

    _CACHED_RETENTION_DF = df_cand.copy()
    return df_cand.copy()

def normalize_column_name(col: str) -> str:
    """
    Normalize a column name by stripping spaces, lowercasing, and replacing accented characters.
    
    Args:
        col: Original column name.
    
    Returns:
        Normalized column name.
    """
    return (col.strip().lower()
            .replace("’", "'")
            .replace("é", "e").replace("É", "e")
            .replace("à", "a").replace("â", "a")
            .replace("î", "i").replace("ô", "o")
            .replace("û", "u").replace("ù", "u"))

def create_retention_charts(df: pd.DataFrame) -> Tuple[px.bar, px.pie, px.bar]:
    """
    Create charts visualizing donor retention aspects.
    
    Args:
        df: The filtered donor retention DataFrame.
    
    Returns:
        A tuple of Plotly figures: (monthly bar chart, gender pie chart, age-based fidelity bar chart).
    """
    # 1. Monthly Chart: Total donors and eligible donors by month
    donneurs_mois = df.groupby("mois", observed=False).agg(
        total_donneurs=("date_de_remplissage_de_la_fiche", "count"),
        eligibles=("eligibilite", "sum")
    ).reset_index()

    fig1 = px.bar(
        donneurs_mois,
        x="mois",
        y=["total_donneurs", "eligibles"],
        barmode="group",
        title="📅 Donneurs Reçus et Éligibles par Mois",
        labels={"value": "Nombre", "variable": "Statut"}
    )

    # 2. Gender Distribution Pie Chart
    sexe_counts = df["genre"].value_counts().reset_index()
    sexe_counts.columns = ["sexe", "nombre"]
    fig2 = px.pie(
        sexe_counts,
        names="sexe",
        values="nombre",
        title="🚻 Répartition des Donneurs par Sexe"
    )

    # 3. Fidelity by Age Group: Bar chart showing loyal vs non-loyal donors per age bin
    fidelite = df.groupby(["tranche_age", "fidele"], observed=False).size().reset_index(name="count")
    fig3 = px.bar(
        fidelite,
        x="tranche_age",
        y="count",
        color="fidele",
        barmode="group",
        title="🧬 Fidélité au Don selon les Tranches d’Âge",
        labels={"tranche_age": "Tranche d’âge", "fidele": "Fidèle"}
    )

    return fig1, fig2, fig3

def generate_retention_summary(df: pd.DataFrame) -> str:
    """
    Generate a textual summary of donor retention statistics.
    
    Args:
        df: The filtered donor retention DataFrame.
    
    Returns:
        Summary string.
    """
    total = df.shape[0]
    hommes = (df["genre"] == "homme").sum()
    femmes = (df["genre"] == "femme").sum()
    eligibles = df["eligibilite"].sum()
    fideles = df["fidele"].sum()

    return (
        f"📝 Durant cette période, nous avons reçu {total} donneurs "
        f"({hommes} hommes et {femmes} femmes). "
        f"{eligibles} étaient éligibles et {fideles} étaient des donneurs fidèles."
    )

def get_retention_layout() -> html.Div:
    """
    Build the Dash layout for an interactive donor retention analytics page.
    
    Returns:
        A Dash HTML layout (Div) containing interactive filters, graphs, and a summary.
    """
    df = load_retention_data()
    
    # Determine the date range for the date picker
    min_date = df["date_de_remplissage_de_la_fiche"].min().date()
    max_date = df["date_de_remplissage_de_la_fiche"].max().date()
    
    layout = dbc.Container([
        dbc.Row(html.H1("Donor Retention Dashboard with Interactive Filters"), className="my-3"),
        dbc.Row([
            dbc.Col([
                html.H4("Filters"),
                
                # Date range filter based on donor form fill date
                html.Label("Date Range"),
                dcc.DatePickerRange(
                    id="date-picker-range",
                    start_date=min_date,
                    end_date=max_date,
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    display_format='YYYY-MM-DD'
                ),
                html.Br(), html.Br(),
                
                # Age slider
                html.Label("Age Range"),
                dcc.RangeSlider(
                    id="age-slider",
                    min=int(df["age"].min()),
                    max=int(df["age"].max()),
                    value=[int(df["age"].min()), int(df["age"].max())],
                    marks={i: str(i) for i in range(int(df["age"].min()), int(df["age"].max())+1, 5)}
                ),
                html.Br(),
                
                # Gender filter
                html.Label("Gender"),
                dcc.Dropdown(
                    id="gender-dropdown",
                    options=[{"label": g, "value": g} for g in sorted(df["genre"].dropna().unique())],
                    value=sorted(df["genre"].dropna().unique()),
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
                
                # Fidelity filter
                html.Label("Fidelity"),
                dcc.RadioItems(
                    id="fidelity-radio",
                    options=[
                        {"label": "All", "value": "all"},
                        {"label": "Fidèle", "value": "fidele"},
                        {"label": "Non Fidèle", "value": "non_fidele"}
                    ],
                    value="all",
                    labelStyle={"display": "inline-block", "margin-right": "10px"}
                )
            ], width=3),
            dbc.Col([
                # A live-updating summary text
                html.Div(id="summary-text", style={"marginBottom": "20px", "fontWeight": "bold"}),

                # Graph outputs
                dcc.Graph(id="monthly-chart"),
                dcc.Graph(id="gender-chart"),
                dcc.Graph(id="fidelity-chart")
            ], width=9)
        ])
    ], fluid=True)
    
    return layout

def init_callbacks(app: dash.Dash) -> None:
    """
    Initialize Dash callbacks for updating charts and summary based on interactive filters.
    
    Args:
        app: The Dash application instance.
    """
    @app.callback(
        [Output("monthly-chart", "figure"),
         Output("gender-chart", "figure"),
         Output("fidelity-chart", "figure"),
         Output("summary-text", "children")],
        [Input("date-picker-range", "start_date"),
         Input("date-picker-range", "end_date"),
         Input("age-slider", "value"),
         Input("gender-dropdown", "value"),
         Input("eligibility-radio", "value"),
         Input("fidelity-radio", "value")]
    )
    def update_retention_charts(start_date, end_date, age_range, genders, eligibility_filter, fidelity_filter):
        df = load_retention_data()
        
        # Combine filters: date, age, gender
        mask = (
            df["date_de_remplissage_de_la_fiche"].between(start_date, end_date) &
            df["age"].between(age_range[0], age_range[1]) &
            df["genre"].isin(genders)
        )
        
        # Apply eligibility filter if needed
        if eligibility_filter == "eligible":
            mask &= (df["eligibilite"] == True)
        elif eligibility_filter == "not_eligible":
            mask &= (df["eligibilite"] == False)
        
        # Apply fidelity filter if needed
        if fidelity_filter == "fidele":
            mask &= (df["fidele"] == True)
        elif fidelity_filter == "non_fidele":
            mask &= (df["fidele"] == False)
            
        filtered_df = df[mask]
        
        # Generate updated charts based on the filtered dataset.
        fig1, fig2, fig3 = create_retention_charts(filtered_df)
        summary = generate_retention_summary(filtered_df)
        return fig1, fig2, fig3, summary

if __name__ == "__main__":
    # Standalone execution for testing the donor retention dashboard.
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = get_retention_layout()
    init_callbacks(app)
    app.run(debug=True)
