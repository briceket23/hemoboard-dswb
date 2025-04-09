# donor_retention.py

import pandas as pd
import plotly.express as px
from dash import dcc, html
from typing import Tuple, Optional

# Global cache for the retention DataFrame
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
        df: The cleaned donor retention DataFrame.
    
    Returns:
        A tuple of Plotly figures: (monthly bar chart, gender pie chart, age-based fidelity bar chart).
    """
    # Aggregate donors and eligible counts by month
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

    # Pie chart for gender distribution
    sexe_counts = df["genre"].value_counts().reset_index()
    sexe_counts.columns = ["sexe", "nombre"]
    fig2 = px.pie(
        sexe_counts,
        names="sexe",
        values="nombre",
        title="🚻 Répartition des Donneurs par Sexe"
    )

    # Bar chart for fidelity based on age bins
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
        df: The cleaned donor retention DataFrame.
    
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
        f"{eligibles} d’entre eux étaient éligibles, "
        f"et {fideles} étaient des donneurs fidèles."
    )

def get_retention_layout(start_date: Optional[str] = None, end_date: Optional[str] = None) -> html.Div:
    """
    Build the Dash layout for donor retention analytics.
    
    Args:
        start_date: Optional start date for filtering.
        end_date: Optional end date for filtering.
    
    Returns:
        A Dash HTML layout (Div) containing graphs and a summary.
    """
    df = load_retention_data()

    if start_date and end_date:
        df = df[
            (df["date_de_remplissage_de_la_fiche"] >= start_date) &
            (df["date_de_remplissage_de_la_fiche"] <= end_date)
        ]

    fig1, fig2, fig3 = create_retention_charts(df)
    commentaire = generate_retention_summary(df)

    layout = html.Div([
        html.H3("♻️ Fidélisation des Donneurs", style={"marginBottom": "30px"}),
        dcc.Graph(figure=fig1),
        dcc.Graph(figure=fig2),
        dcc.Graph(figure=fig3),
        html.Div([
            html.H4("📌 Interprétation"),
            html.P(commentaire, style={"fontStyle": "italic", "color": "green"})
        ], className="legend", style={"marginTop": "40px"})
    ], className="tab-content")
    return layout

if __name__ == "__main__":
    # Standalone execution for testing the retention layout.
    import dash
    app = dash.Dash(__name__)
    app.layout = get_retention_layout()
    app.run(debug=True)
