import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="SmartGuard Data Analyzer", layout="wide")

st.title("🌊 Analyseur de Données Bouée SmartGuard")

@st.cache_data
def process_smartguard_file(uploaded_file):
    # 1. Gestion de l'encodage (UTF-16 est fréquent sur SmartGuard)
    bytes_data = uploaded_file.read()
    content = None
    for enc in ['utf-16', 'utf-8', 'latin-1']:
        try:
            content = bytes_data.decode(enc).splitlines()
            break
        except UnicodeDecodeError:
            continue
    
    if not content:
        st.error("Impossible de lire l'encodage du fichier.")
        return None

    # 2. Localisation de la ligne d'en-tête et des données
    # On cherche la ligne qui contient "Date and time"
    header_idx = -1
    for i, line in enumerate(content):
        if "Date and time" in line:
            header_idx = i
            break
    
    if header_idx == -1:
        st.error("Format non reconnu : ligne d'en-tête 'Date and time' introuvable.")
        return None

    # 3. Extraction et Nettoyage
    # On récupère les données à partir de l'en-tête
    data_lines = content[header_idx:]
    
    # On utilise sep='\t' car votre échantillon montre des tabulations ou espaces larges
    df = pd.read_csv(
        io.StringIO("\n".join(data_lines)),
        sep='\t', 
        engine='python',
        skip_blank_lines=True
    )

    # 4. Nettoyage des noms de colonnes
    # Supprime les espaces blancs et les suffixes comme "[9]"
    df.columns = [c.split('[')[0].strip() for c in df.columns]

    # 5. Conversion de la Date
    if "Date and time" in df.columns:
        df['Date and time'] = pd.to_datetime(df['Date and time'], errors='coerce')
        df = df.dropna(subset=['Date and time'])
        df = df.sort_values('Date and time')

    # 6. Conversion numérique forcée pour toutes les colonnes de mesures
    cols_to_fix = [c for c in df.columns if c != 'Date and time']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

# --- Interface Sidebar ---
uploaded_file = st.sidebar.file_uploader("Charger le fichier .txt de la bouée", type=['txt', 'csv'])

if uploaded_file:
    df = process_smartguard_file(uploaded_file)
    
    if df is not None:
        st.success(f"Données chargées : {df.shape[0]} lignes détectées.")
        
        # Filtres de visualisation
        st.sidebar.header("Paramètres")
        all_cols = df.columns.tolist()
        y_axis = st.sidebar.selectbox("Variable à visualiser (Y)", 
                                    [c for c in all_cols if "Height" in c or "Period" in c or "Direction" in c],
                                    index=0)
        
        # --- Affichage des graphiques ---
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"Série Temporelle : {y_axis}")
            fig = px.line(df, x="Date and time", y=y_axis, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.subheader("Résumé Statistique")
            st.write(df[y_axis].describe())

        # Rose des vents si la direction est présente
        dir_cols = [c for c in df.columns if "Direction" in c]
        if dir_cols:
            st.markdown("---")
            st.subheader("Distribution Directionnelle")
            selected_dir = st.selectbox("Choisir la colonne de direction", dir_cols)
            
            # Création de secteurs (bins) pour la rose
            df['Dir_Sector'] = (df[selected_dir] // 10) * 10
            fig_rose = px.bar_polar(df, r="Significant Wave Height Hm0", theta="Dir_Sector", 
                                   color="Significant Wave Height Hm0",
                                   template="plotly_dark",
                                   color_continuous_scale=px.colors.sequential.Viridis)
            st.plotly_chart(fig_rose, use_container_width=True)

        # Aperçu des données
        with st.expander("Voir les données brutes nettoyées"):
            st.dataframe(df)
else:
    st.info("Veuillez importer le fichier texte pour commencer l'analyse.")
