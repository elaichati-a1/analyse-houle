import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io

# Configuration de la page
st.set_page_config(page_title="Analyseur de Houle", layout="wide", page_icon="🌊")

# Initialisation de la variable globale pour éviter le NameError
df = None

st.title("🌊 Tableau de Bord d'Analyse de Houle")
st.markdown("""
Cette application permet de visualiser et d'analyser les données hydrographiques (Hm0, Tp, Direction).
Téléchargez votre fichier de bouée (.txt ou .csv) pour commencer.
""")

# --- FONCTION DE CHARGEMENT ROBUSTE ---
@st.cache_data
def load_data(uploaded_file):
    try:
        # 1. Lecture brute pour trouver la ligne d'en-tête automatiquement
        # Cela évite l'erreur "Expected 1 fields" si le nombre de lignes d'intro change
        content = uploaded_file.getvalue().decode("utf-8", errors='replace')
        buffer = io.StringIO(content)
        lines = buffer.readlines()
        
        header_row_index = 0
        found_header = False
        
        # On cherche la ligne qui contient "Date and time" ou "Hm0"
        for i, line in enumerate(lines):
            if "Date and time" in line or "Hm0" in line:
                header_row_index = i
                found_header = True
                break
        
        if not found_header:
            st.error("Impossible de trouver la ligne d'en-tête (Date and time) dans le fichier.")
            return None

        # 2. Revenir au début du fichier virtuel
        buffer.seek(0)
        
        # 3. Chargement avec Pandas en sautant le bon nombre de lignes
        # On utilise engine='python' qui est plus tolérant aux erreurs de séparateurs que le moteur C
        df = pd.read_csv(buffer, sep='\t', header=header_row_index, engine='python')
        
        # Nettoyage des noms de colonnes
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mapping des colonnes (Adaptation aux variations de noms)
        # On cherche des correspondances partielles si le nom exact change
        renaming_map = {}
        for col in df.columns:
            if "Date" in col: renaming_map[col] = 'Date'
            elif "Hm0" in col and "Swell" not in col and "Wind" not in col: renaming_map[col] = 'Hm0' # Hm0 global
            elif "Peak Direction" in col and "Swell" not in col: renaming_map[col] = 'Dir_Pic'
            elif "Peak Period" in col and "Swell" not in col: renaming_map[col] = 'Tp'
        
        df = df.rename(columns=renaming_map)
        
        # Vérification que les colonnes essentielles sont là
        required_cols = ['Date', 'Hm0', 'Dir_Pic', 'Tp']
        if not all(col in df.columns for col in required_cols):
             st.warning(f"Attention : Certaines colonnes semblent manquantes. Colonnes trouvées : {list(df.columns)}")

        # Conversion Date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        # On supprime les lignes où la date n'a pas pu être lue (souvent la ligne d'unités sous l'en-tête)
        df = df.dropna(subset=['Date'])
        
        # Conversion numérique (au cas où il y a du texte parasite)
        for col in ['Hm0', 'Tp', 'Dir_Pic']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
        
    except Exception as e:
        st.error(f"Erreur technique lors de la lecture : {e}")
        return None

# --- SIDEBAR : IMPORT ET FILTRES ---
with st.sidebar:
    st.header("1. Données")
    uploaded_file = st.file_uploader("Charger un fichier de données", type=['txt', 'csv'])
    
    if uploaded_file is not None:
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None and not df_raw.empty:
            st.success("Fichier chargé avec succès !")
            
            st.header("2. Période d'analyse")
            min_date = df_raw['Date'].min()
            max_date = df_raw['Date'].max()
            
            start_date = st.date_input("Date de début", min_date)
            end_date = st.date_input("Date de fin", max_date)
            
            # Filtrage des données
            mask = (df_raw['Date'] >= pd.to_datetime(start_date)) & (df_raw['Date'] <= pd.to_datetime(end_date))
            df = df_raw.loc[mask]
            
            st.info(f"Nombre de mesures : {len(df)}")
        else:
            st.warning("Le fichier a été lu mais ne contient pas de données valides ou exploitables.")
    # Pas de 'else df = None' ici, car df est déjà initialisé tout en haut

# --- MAIN DASHBOARD ---
if df is not None and not df.empty:
    
    # KPIs
    st.subheader("📊 Statistiques Globales sur la période")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        val = df['Hm0'].max()
        st.metric("Hm0 Max", f"{val:.2f} m")
    with kpi2:
        val = df['Hm0'].mean()
        st.metric("Hm0 Moyenne", f"{val:.2f} m")
    with kpi3:
        val = df['Tp'].max()
        st.metric("Période Pic (Tp) Max", f"{val:.1f} s")
    with kpi4:
        val = df['Dir_Pic'].mean()
        st.metric("Direction Dominante (Moy)", f"{val:.0f}°")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Évolution Temporelle", "🧭 Rose des Houles", "📊 Distribution", "📥 Données"])

    with tab1:
        st.subheader("Série Temporelle")
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=df['Date'], y=df['Hm0'], mode='lines', name='Hm0 (m)', line=dict(color='#1f77b4')))
        fig_ts.update_layout(title="Hauteur Significative (Hm0)", yaxis_title="Hauteur (m)", template="plotly_white")
        st.plotly_chart(fig_ts, use_container_width=True)
        
        fig_tp = go.Figure()
        fig_tp.add_trace(go.Scatter(x=df['Date'], y=df['Tp'], mode='lines', name='Tp (s)', line=dict(color='#ff7f0e')))
        fig_tp.update_layout(title="Période de Pic (Tp)", yaxis_title="Période (s)", template="plotly_white")
        st.plotly_chart(fig_tp, use_container_width=True)

    with tab2:
        st.subheader("Rose des Houles")
        if 'Dir_Pic' in df.columns and 'Hm0' in df.columns:
            # Nettoyage des NaNs pour le graphique
            df_rose = df.dropna(subset=['Dir_Pic', 'Hm0'])
            if not df_rose.empty:
                df_rose['Dir_Bin'] = (df_rose['Dir_Pic'] // 10) * 10
                fig_rose = px.bar_polar(df_rose, r="Hm0", theta="Dir_Bin", 
                                        color="Hm0", template="plotly_dark",
                                        color_continuous_scale=px.colors.sequential.Viridis,
                                        title="Distribution Énergie/Direction")
                st.plotly_chart(fig_rose, use_container_width=True)
            else:
                st.warning("Pas assez de données de direction pour la rose.")

    with tab3:
        st.subheader("Distribution")
        col1, col2 = st.columns(2)
        with col1:
            fig_hist = px.histogram(df, x="Hm0", nbins=50, title="Histogramme Hm0")
            st.plotly_chart(fig_hist, use_container_width=True)
        with col2:
            fig_scat = px.scatter(df, x="Tp", y="Hm0", color="Dir_Pic", title="Tp vs Hm0")
            st.plotly_chart(fig_scat, use_container_width=True)

    with tab4:
        st.subheader("Export")
        st.dataframe(df.head(50))
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger CSV", data=csv, file_name='donnees_houle_filtrees.csv', mime='text/csv')

elif uploaded_file is None:
    st.info("👈 Veuillez charger un fichier dans le menu de gauche.")
