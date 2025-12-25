import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Analyseur de Houle", layout="wide", page_icon="🌊")

st.title("🌊 Tableau de Bord d'Analyse de Houle")
st.markdown("""
Cette application permet de visualiser et d'analyser les données hydrographiques (Hm0, Tp, Direction).
Téléchargez votre fichier de bouée (.txt ou .csv) pour commencer.
""")

# --- FONCTION DE CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data(uploaded_file):
    try:
        # On essaie de lire avec les paramètres standards du fichier bouée que vous avez montré
        # Skiprows=9 car les données commencent souvent après l'en-tête technique
        df = pd.read_csv(uploaded_file, sep='\t', skiprows=9)
        
        # Nettoyage des noms de colonnes (enlever les [9] et espaces)
        df.columns = [c.strip() for c in df.columns]
        
        # Renommer les colonnes clés pour faciliter l'usage
        # Adaptez ces clés si le format de fichier change
        col_mapping = {
            'Date and time': 'Date',
            'Significant Wave Height Hm0 [9]': 'Hm0',
            'Wave Peak Direction [9]': 'Dir_Pic',
            'Wave Peak Period [9]': 'Tp',
            'Wave Mean Period Tm02 [9]': 'Tm02'
        }
        # On renomme seulement si la colonne existe
        df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})
        
        # Conversion Date
        df['Date'] = pd.to_datetime(df['Date'])
        
        return df
    except Exception as e:
        st.error(f"Erreur de lecture du fichier : {e}")
        return None

# --- SIDEBAR : IMPORT ET FILTRES ---
with st.sidebar:
    st.header("1. Données")
    uploaded_file = st.file_uploader("Charger un fichier de données", type=['txt', 'csv'])
    
    if uploaded_file is not None:
        df_raw = load_data(uploaded_file)
        
        if df_raw is not None:
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
        df = None

# --- MAIN DASHBOARD ---
if df is not None:
    
    # KPIs (Indicateurs Clés)
    st.subheader("📊 Statistiques Globales sur la période")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric("Hm0 Max", f"{df['Hm0'].max():.2f} m")
    with kpi2:
        st.metric("Hm0 Moyenne", f"{df['Hm0'].mean():.2f} m")
    with kpi3:
        st.metric("Période Pic (Tp) Max", f"{df['Tp'].max():.1f} s")
    with kpi4:
        st.metric("Direction Dominante (Moy)", f"{df['Dir_Pic'].mean():.0f}°")

    st.markdown("---")

    # Onglets pour organiser l'analyse
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Évolution Temporelle", "🧭 Rose des Houles", "📊 Distribution (Histogrammes)", "📥 Données"])

    with tab1:
        st.subheader("Série Temporelle : Hauteur et Période")
        
        # Graphique Hm0 interactif
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=df['Date'], y=df['Hm0'], mode='lines', name='Hm0 (m)', line=dict(color='#1f77b4')))
        fig_ts.update_layout(title="Évolution de la Hauteur Significative (Hm0)", yaxis_title="Hauteur (m)", template="plotly_white")
        st.plotly_chart(fig_ts, use_container_width=True)
        
        # Graphique Tp interactif
        fig_tp = go.Figure()
        fig_tp.add_trace(go.Scatter(x=df['Date'], y=df['Tp'], mode='lines', name='Tp (s)', line=dict(color='#ff7f0e')))
        fig_tp.update_layout(title="Évolution de la Période de Pic (Tp)", yaxis_title="Période (s)", template="plotly_white")
        st.plotly_chart(fig_tp, use_container_width=True)

    with tab2:
        st.subheader("Analyse Directionnelle (Rose des Houles)")
        col_rose1, col_rose2 = st.columns([2, 1])
        
        with col_rose1:
            # Création d'une Rose des vents simplifiée avec Plotly Express
            # On discretise la direction pour mieux voir les secteurs
            df['Dir_Bin'] = (df['Dir_Pic'] // 10) * 10
            
            fig_rose = px.bar_polar(df, r="Hm0", theta="Dir_Bin", 
                                    color="Hm0", template="plotly_dark",
                                    color_continuous_scale=px.colors.sequential.Viridis,
                                    title="Distribution de l'énergie (Direction vs Hauteur)")
            st.plotly_chart(fig_rose, use_container_width=True)
        
        with col_rose2:
            st.markdown("""
            **Interprétation :**
            Ce graphique montre d'où vient l'énergie.
            - La **direction** indique l'origine de la houle.
            - La **couleur** indique la hauteur des vagues.
            - La **longueur** des barres indique la fréquence.
            """)

    with tab3:
        st.subheader("Distribution Statistique")
        
        col_hist1, col_hist2 = st.columns(2)
        
        with col_hist1:
            fig_hist = px.histogram(df, x="Hm0", nbins=50, title="Distribution des Hauteurs (Hm0)", marginal="box")
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with col_hist2:
            fig_scat = px.scatter(df, x="Tp", y="Hm0", color="Dir_Pic", 
                                  title="Corrélation Période (Tp) vs Hauteur (Hm0)")
            st.plotly_chart(fig_scat, use_container_width=True)

    with tab4:
        st.subheader("Téléchargement des données filtrées")
        st.dataframe(df.head(100))
        
        # Convertir le dataframe filtré en CSV pour téléchargement
        csv = df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="Télécharger les données filtrées (CSV)",
            data=csv,
            file_name='donnees_houle_filtrees.csv',
            mime='text/csv',
        )

else:
    st.info("Veuillez charger un fichier dans le panneau latéral pour commencer l'analyse.")
