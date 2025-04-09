import io
import base64
import pandas as pd
import plotly.express as px
from dash import dcc, html
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ----------------------------------------------------
# DATA LOADING AND SENTIMENT ANALYSIS FUNCTIONS
# ----------------------------------------------------
def load_sentiment_data():
    """Charge les commentaires, calcule les sentiments et agrège les statistiques."""
    # Charge le CSV et nettoie les noms de colonnes
    df = pd.read_csv("data/Candidat_au_don_2019_cleaned.csv", sep=";")
    df.columns = df.columns.str.strip()
    
    # Détermine la colonne de feedback à utiliser
    feedback_col = "Si_autres_raison_préciser" if "Si_autres_raison_préciser" in df.columns else "Si_autres_raison_préciser_"
    
    # Garder uniquement les lignes avec un texte non vide
    df = df.dropna(subset=[feedback_col])
    df = df[df[feedback_col].str.strip() != ""]
    
    # Fonction pour calculer le sentiment en se basant sur la polarité
    def detect_sentiment(text):
        polarity = TextBlob(str(text)).sentiment.polarity
        if polarity > 0.1:
            return "Positif"
        elif polarity < -0.1:
            return "Négatif"
        else:
            return "Neutre"
    
    df["Sentiment"] = df[feedback_col].apply(detect_sentiment)
    
    # Sécurité pour la colonne "Profession"
    df["Profession"] = df["Profession"].fillna("Inconnu")
    
    # Agrégation pour le graphique en barres par Profession et Sentiment
    sentiment_stats = df.groupby(["Profession", "Sentiment"]).size().reset_index(name="Count")
    # Statistiques globales pour le diagramme circulaire
    sentiment_global = df["Sentiment"].value_counts().reset_index()
    sentiment_global.columns = ["Sentiment", "Count"]
    
    return df, sentiment_stats, sentiment_global, feedback_col

# ----------------------------------------------------
# CHART CREATION FUNCTIONS
# ----------------------------------------------------
def create_sentiment_charts(sentiment_stats, sentiment_global):
    """Crée un graphique en barres et un camembert pour l'analyse des sentiments."""
    # Graphique en barres par Profession
    fig_bar = px.bar(
        sentiment_stats,
        x="Profession",
        y="Count",
        color="Sentiment",
        title="Analyse des Sentiments par Profession",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_bar.update_layout(
        xaxis_title="Profession",
        yaxis_title="Nombre",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # Diagramme circulaire global des sentiments
    fig_pie = px.pie(
        sentiment_global,
        names="Sentiment",
        values="Count",
        title="Répartition Globale des Sentiments",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    return fig_bar, fig_pie

def generate_wordcloud_image(df, feedback_col):
    """Génère et encode un word cloud à partir des feedbacks."""
    all_text = " ".join(df[feedback_col].dropna().tolist())
    if not all_text:
        return None

    # Génère le WordCloud
    wc = WordCloud(width=800, height=400, background_color="white").generate(all_text)
    
    # Sauvegarder l'image dans un buffer en mémoire
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    buf.seek(0)
    
    # Encode l'image en base64 pour l'inclure dans Dash
    encoded_image = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded_image}"

def create_feedback_table(df, feedback_col):
    """Crée un tableau HTML contenant 10 exemples de feedback et leurs sentiments."""
    sample_df = df[[feedback_col, "Sentiment"]].head(10)
    header = [html.Th(col) for col in sample_df.columns]
    rows = []
    for _, row in sample_df.iterrows():
        rows.append(html.Tr([html.Td(row[col]) for col in sample_df.columns]))
    table = html.Table(
        [html.Thead(html.Tr(header)), html.Tbody(rows)], 
        className="card",
        style={"width": "100%", "border": "1px solid #ccc", "borderCollapse": "collapse"}
    )
    return table

# ----------------------------------------------------
# SENTIMENT ANALYSIS DASH LAYOUT
# ----------------------------------------------------
def get_sentiment_layout():
    # Charge et prépare les données de sentiment
    df, sentiment_stats, sentiment_global, feedback_col = load_sentiment_data()
    
    # Crée les graphiques en barres et circulaire
    fig_bar, fig_pie = create_sentiment_charts(sentiment_stats, sentiment_global)
    
    # Génère l'image du word cloud
    wordcloud_src = generate_wordcloud_image(df, feedback_col)
    
    # Crée le tableau des feedbacks
    feedback_table = create_feedback_table(df, feedback_col)
    
    layout = html.Div([
        html.H3("Analyse des Sentiments des Donneurs"),
        
        # Section des graphiques (barres et camembert)
        html.Div(
            className="graph-container",
            children=[
                html.Div([dcc.Graph(figure=fig_bar)], className="card", style={"flex": "1", "margin": "10px"}),
                html.Div([dcc.Graph(figure=fig_pie)], className="card", style={"flex": "1", "margin": "10px"})
            ],
            style={"display": "flex", "flexWrap": "wrap"}
        ),
        
        # Section Word Cloud
        html.Div(
            className="card",
            children=[
                html.H4("Word Cloud des Feedback"),
                html.Div(
                    html.Img(src=wordcloud_src, style={"width": "100%"})
                    if wordcloud_src else "Aucune donnée pour générer un word cloud."
                )
            ],
            style={"marginTop": "20px", "padding": "10px"}
        ),
        
        # Section d'exemples de feedback
        html.Div(
            className="card",
            children=[
                html.H4("Exemples de Feedback"),
                feedback_table
            ],
            style={"marginTop": "20px", "padding": "10px"}
        ),
        
        # Section d'interprétation/legend
        html.Div(
            className="legend",
            children=[
                html.H4("Interprétation"),
                html.P("Le graphique à barres montre les sentiments exprimés par les donneurs selon leur profession."),
                html.P("Le diagramme circulaire illustre la répartition globale des retours positifs, neutres et négatifs.")
            ],
            style={"marginTop": "20px", "padding": "10px"}
        )
    ], className="tab-content")
    
    return layout

# ----------------------------------------------------
# Si vous souhaitez tester cette page dans une application Dash :
# ----------------------------------------------------
if __name__ == '__main__':
    import dash
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    # Pour la démonstration, nous utilisons ce layout directement.
    app.layout = get_sentiment_layout()
    app.run(debug=True)
