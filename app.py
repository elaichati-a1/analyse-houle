import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="SmartGuard Data Analyzer", layout="wide", page_icon="🌊")

st.title("🌊 Analyseur de Données Bouée SmartGuard")

@st.cache_data
def process_smartguard_file(uploaded_file):
    # 1. Lecture des bytes une seule fois
    bytes_data = uploaded_file.read()
    content = None
    
    # Tentative de décodage robuste
    encoding_found = None
    for enc in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
        try:
            # On essaye de décoder
            decoded = bytes_data.decode(enc)
            # Petit test : si on trouve "Date" ou "Time", c'est probablement le bon encodage
            if "Date" in decoded or "Time" in decoded or "Hm0" in decoded:
                content = decoded.splitlines()
                encoding_found = enc
                break
        except UnicodeDecodeError:
            continue
    
    if not content:
        st.error("Impossible de lire l'encodage du fichier.")
        return None

    # 2. Localisation de la ligne d'en-tête
    header_idx = -1
    for i, line in enumerate(content[:50]): # On cherche dans les 50 premières lignes
        if "Date" in line and ("Time" in line or "time" in line):
            header_idx = i
            break
    
    if header_idx == -1:
        st.error("Format non reconnu : Ligne d'en-tête introuvable.")
        return None

    # 3. Extraction et Nettoyage
    data_lines = content[header_idx:]
    
    # Utilisation de sep=None avec engine='python' pour détecter auto (tab ou espaces)
    try:
        df = pd.read_csv(
            io.StringIO("\n".join(data_lines)),
            sep=None, 
            engine='python',
            skip_blank_lines=True
        )
    except Exception as e:
        st.error(f"Erreur de lecture CSV : {e}")
        return None

    # 4. Nettoyage des noms de colonnes (très important)
    # On enlève les [9], les espaces en trop, et on standardise
    df.columns = [c.split('[')[0].strip() for c in df.columns]

    # 5. Conversion de la Date
    # On cherche la colonne qui contient "Date"
    date_col = next((c for c in df.columns if "Date" in c), None)
    
    if date_col:
        df[date_col] = pd.to_numeric(df[date_col], errors='coerce') # Sécurité si mélange
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df = df.sort_values(date_col)
        # On renomme pour simplifier la suite
        df = df.rename(columns={date_col: 'Date'})
    else:
        st.error("Colonne Date introuvable.")
        return None

    # 6. Conversion numérique forcée
    for col in df.columns:
        if col != 'Date':
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

# --- Interface ---
uploaded_file = st.sidebar.file_uploader("Charger le fichier .txt de la bouée", type=['txt', 'csv'])

if uploaded_file:
    df = process_smartguard_file(uploaded_file)
    
    if df is not None and not df.empty:
        st.success(f"Données chargées : {df.shape[0]} mesures du {df['Date'].min().date()} au {df['Date'].max().date()}")
        
        # Filtres de visualisation
        st.sidebar.header("Paramètres Graphiques")
        
        # On exclut la colonne Date et les colonnes vides des choix
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        # Choix intelligent de la variable par défaut (Hm0 si dispo)
        default_idx = 0
        for i, col in enumerate(numeric_cols):
            if "Hm0" in col or "Significant" in col:
                default_idx = i
                break
                
        y_axis = st.sidebar.selectbox("Variable à visualiser (Y)", numeric_cols, index=default_idx)
        
        # --- Affichage des graphiques ---
        col1, col2 = st.columns([3, 1]) # Plus de place pour le graphique
        
        with col1:
            st.subheader(f"📈 Série Temporelle : {y_axis}")
            fig = px.line(df, x="Date", y=y_axis, template="plotly_white")
            fig.update_traces(line_color='#1f77b4')
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            st.subheader("📊 Résumé")
            desc = df[y_axis].describe()
            st.metric("Maximum", f"{desc['max']:.2f}")
            st.metric("Moyenne", f"{desc['mean']:.2f}")
            st.metric("Minimum", f"{desc['min']:.2f}")

        # --- Rose des vents (Section Sécurisée) ---
        # On cherche une colonne qui ressemble à une direction
        dir_cols = [c for c in df.columns if "Dir" in c or "deg" in c]
        
        if dir_cols:
            st.markdown("---")
            st.subheader("🧭 Analyse Directionnelle (Rose des Vents)")
            
            c_rose1, c_rose2 = st.columns(2)
            
            with c_rose1:
                selected_dir = st.selectbox("Source de Direction", dir_cols)
            
            with c_rose2:
                # On essaie de trouver la colonne de hauteur automatiquement pour le rayon (r)
                # Sinon on prend la variable sélectionnée en Y
                possible_heights = [c for c in df.columns if "Hm0" in c or "Height" in c]
                default_height = possible_heights[0] if possible_heights else y_axis
                radius_col = st.selectbox("Métrique d'intensité (Rayon)", numeric_cols, index=numeric_cols.index(default_height) if default_height in numeric_cols else 0)

            # Création de la Rose
            # On filtre les NaN pour éviter les bugs graphiques
            df_rose = df.dropna(subset=[selected_dir, radius_col])
            
            if not df_rose.empty:
                df_rose['Dir_Sector'] = (df_rose[selected_dir] // 10) * 10
                
                fig_rose = px.bar_polar(
                    df_rose, 
                    r=radius_col, 
                    theta="Dir_Sector", 
                    color=radius_col,
                    template="plotly_dark",
                    color_continuous_scale=px.colors.sequential.Viridis,
                    title=f"Distribution : {radius_col} vs {selected_dir}"
                )
                st.plotly_chart(fig_rose, use_container_width=True)
            else:
                st.warning("Pas assez de données valides pour la rose des vents.")

        # Aperçu des données
        with st.expander("Voir le tableau de données"):
            st.dataframe(df)
            
else:
    st.info("👋 Bonjour ! Veuillez importer le fichier texte de la bouée via le menu de gauche.")
