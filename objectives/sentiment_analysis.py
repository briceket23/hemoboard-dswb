import io
import base64
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from textblob import TextBlob
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

# ----------------------------------------------------
# CONFIGURABLE PARAMETERS & FRENCH STOPWORDS
# ----------------------------------------------------
CSV_FILE_PATH = "data/Candidat_au_don_2019_cleaned.csv"
CSV_DELIMITER = ";"
SENTIMENT_POSITIVE_THRESHOLD = 0.1
SENTIMENT_NEGATIVE_THRESHOLD = -0.1

# Extend the default stopwords with additional French words.
FRENCH_STOPWORDS = set(STOPWORDS)
FRENCH_STOPWORDS.update({
    'le', 'la', 'les', 'un', 'une', 'de', 'des', 'du', 'en',
    'et', 'à', 'au', 'aux', 'ce', 'ces', 'dans', 'par', 'pour',
    'avec', 'mais', 'ou', 'donc', 'or', 'ni', 'car', 'sur', 'se'
})

# ----------------------------------------------------
# DATA LOADING AND SENTIMENT ANALYSIS FUNCTIONS
# ----------------------------------------------------
def load_sentiment_data():
    """
    Charge les commentaires depuis le CSV, nettoie les données,
    calcule les sentiments en tentant une traduction en anglais,
    et agrège des statistiques pour le graphique.
    """
    try:
        df = pd.read_csv(CSV_FILE_PATH, sep=CSV_DELIMITER)
    except FileNotFoundError:
        raise Exception(f"Le fichier {CSV_FILE_PATH} n'a pas été trouvé.")
    except Exception as e:
        raise Exception(f"Erreur lors de la lecture du fichier CSV: {e}")

    # Nettoyer les noms de colonnes.
    df.columns = df.columns.str.strip()
    
    # Utiliser la colonne de feedback "Si_autres_raison_préciser" (ou son alternative).
    if "Si_autres_raison_préciser" in df.columns:
        feedback_col = "Si_autres_raison_préciser"
    elif "Si_autres_raison_préciser_" in df.columns:
        feedback_col = "Si_autres_raison_préciser_"
    else:
        raise Exception("Aucune colonne de feedback appropriée trouvée.")

    # Remplir les valeurs manquantes par une chaîne vide afin de marquer "Neutre".
    df[feedback_col] = df[feedback_col].fillna("")

    # Supprimer les lignes dont le texte est vide uniquement pour l'affichage du word cloud.
    # Pour le calcul des sentiments, un texte vide retournera "Neutre".
    df["Sentiment"] = df[feedback_col].apply(compute_sentiment)
    
    # Gérer la colonne "Profession".
    if "Profession" in df.columns:
        df["Profession"] = df["Profession"].fillna("Inconnu")
    else:
        df["Profession"] = "Inconnu"
    
    # Agrégation pour le graphique en barres (par Profession et Sentiment).
    sentiment_stats = df.groupby(["Profession", "Sentiment"]).size().reset_index(name="Count")
    
    # Statistiques globales pour le diagramme circulaire.
    sentiment_global = df["Sentiment"].value_counts().reset_index()
    sentiment_global.columns = ["Sentiment", "Count"]
    
    return df, sentiment_stats, sentiment_global, feedback_col

def compute_sentiment(text):
    """
    Calcule la polarité du texte. Si le texte est vide, retourne "Neutre".
    Tente de traduire le texte en anglais pour une meilleure analyse.
    """
    if not text.strip():
        return "Neutre"
    
    try:
        translated_text = TextBlob(text).translate(to='en')
        polarity = translated_text.sentiment.polarity
    except Exception:
        polarity = TextBlob(text).sentiment.polarity

    if polarity > SENTIMENT_POSITIVE_THRESHOLD:
        return "Positif"
    elif polarity < SENTIMENT_NEGATIVE_THRESHOLD:
        return "Négatif"
    else:
        return "Neutre"

def generate_wordcloud_image(text_list):
    """
    Génère un word cloud à partir d'une liste de textes non vides,
    utilisant une liste étendue de stopwords pour le français,
    et retourne l'image encodée en base64.
    """
    # Filtrer et joindre uniquement les textes non vides.
    non_empty_texts = [txt for txt in text_list if txt.strip()]
    all_text = " ".join(non_empty_texts)
    if not all_text:
        return None

    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        stopwords=FRENCH_STOPWORDS
    ).generate(all_text)
    
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    buf.seek(0)
    encoded_image = base64.b64encode(buf.getvalue()).decode("utf-8")
    return encoded_image

# ----------------------------------------------------
# CHART CREATION FUNCTIONS
# ----------------------------------------------------
def create_sentiment_charts(sentiment_stats, sentiment_global):
    """
    Crée un graphique en barres et un diagramme circulaire pour l'analyse des sentiments.
    """
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
    
    fig_pie = px.pie(
        sentiment_global,
        names="Sentiment",
        values="Count",
        title="Répartition Globale des Sentiments",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    return fig_bar, fig_pie

def create_feedback_table(df, feedback_col):
    """
    Crée un tableau HTML affichant 10 exemples de feedback et leur sentiment associé.
    """
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
# DASH LAYOUT
# ----------------------------------------------------
def get_sentiment_layout():
    # Charge et prépare les données
    df, sentiment_stats, sentiment_global, feedback_col = load_sentiment_data()
    
    # Crée les graphiques
    fig_bar, fig_pie = create_sentiment_charts(sentiment_stats, sentiment_global)
    
    # Génère le word cloud pour les feedback non vides.
    wordcloud_encoded = generate_wordcloud_image(df[feedback_col].tolist())
    
    # Crée le tableau des feedbacks
    feedback_table = create_feedback_table(df, feedback_col)
    
    layout = html.Div([
        html.H3("Analyse des Sentiments des Donneurs"),
        # Section pour les graphiques
        html.Div([
            html.Div([dcc.Graph(figure=fig_bar)], style={"flex": "1", "margin": "10px"}),
            html.Div([dcc.Graph(figure=fig_pie)], style={"flex": "1", "margin": "10px"})
        ], style={"display": "flex", "flexWrap": "wrap"}),
        # Section Word Cloud
        html.Div([
            html.H4("Word Cloud des Feedback"),
            html.Div(
                html.Img(src=f"data:image/png;base64,{wordcloud_encoded}", style={"width": "100%"})
                if wordcloud_encoded else "Aucune donnée pour générer un word cloud."
            )
        ], style={"marginTop": "20px", "padding": "10px"}),
        # Section Exemples de Feedback
        html.Div([
            html.H4("Exemples de Feedback"),
            feedback_table
        ], style={"marginTop": "20px", "padding": "10px"}),
        # Section d'Interprétation
        html.Div([
            html.H4("Interprétation"),
            html.P("Le graphique à barres montre les sentiments exprimés par les donneurs selon leur profession."),
            html.P("Le diagramme circulaire illustre la répartition globale des retours positifs, neutres et négatifs.")
        ], style={"marginTop": "20px", "padding": "10px"})
    ], className="tab-content")
    
    return layout

# ----------------------------------------------------
# MAIN: Création et lancement de l'application Dash
# ----------------------------------------------------
if __name__ == '__main__':
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.layout = get_sentiment_layout()
    app.run_server(debug=True)
