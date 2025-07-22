import streamlit as st
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from streamlit_folium import folium_static

# Initialiser la variable prediction à None
prediction = None

# Configuration de la page
st.set_page_config(
    page_title="Prédiction de loyer à Antananarivo",
    page_icon="🏠",
    layout="wide"
)

# Titre de l'application
st.title("🏠 Prédiction du prix de location de logements à Antananarivo")
st.markdown("Cette application permet de prédire le loyer mensuel d'un logement à Antananarivo en fonction de ses caractéristiques.")

# Chargement du modèle
@st.cache_resource
def load_model():
    try:
        return joblib.load('modele_loyer_optimise.joblib')
    except Exception as e:
        st.error(f"Le modèle n'a pas été trouvé ou problème de compatibilité. Erreur: {str(e)}")
        st.info("Si l'erreur est liée à la compatibilité des versions de scikit-learn, vous devrez réentraîner le modèle avec votre version actuelle.")
        return None

model = load_model()

# Chargement des données pour les statistiques
@st.cache_data
def load_data():
    try:
        return pd.read_csv('data_mock/logement.csv')
    except:
        st.error("Le fichier de données n'a pas été trouvé.")
        return None

data = load_data()

# Création des colonnes pour la mise en page
col1, col2 = st.columns([1, 1])

# Formulaire de saisie
with col1:
    st.header("Caractéristiques du logement")
    
    quartier = st.selectbox(
        "Quartier",
        sorted(data['quartier'].unique()) if data is not None else []
    )
    
    superficie = st.slider(
        "Superficie (m²)",
        min_value=20,
        max_value=200,
        value=80
    )
    
    nombre_chambres = st.slider(
        "Nombre de chambres",
        min_value=1,
        max_value=6,
        value=2
    )
    
    douche_wc = st.radio(
        "Type de douche/WC",
        options=["interieur", "exterieur"]
    )
    
    type_d_acces = st.selectbox(
        "Type d'accès",
        options=["sans", "moto", "voiture", "voiture_avec_par_parking"]
    )
    
    meuble = st.radio(
        "Meublé",
        options=["oui", "non"]
    )
    
    etat_general = st.selectbox(
        "État général",
        options=["mauvais", "moyen", "bon"]
    )
    
    # Calcul de la variable dérivée
    superficie_par_chambre = superficie / nombre_chambres

# Prédiction
if model is not None and data is not None:
    # Création du DataFrame pour la prédiction
    input_data = pd.DataFrame({
        'quartier': [quartier],
        'superficie': [superficie],
        'nombre_chambres': [nombre_chambres],
        'douche_wc': [douche_wc],
        'type_d_acces': [type_d_acces],
        'meublé': [meuble],
        'état_général': [etat_general],
        'superficie_par_chambre': [superficie_par_chambre]
    })
    
    # Prédiction
    prediction = model.predict(input_data)[0]
    
    # Affichage de la prédiction
    with col2:
        st.header("Résultat de la prédiction")
        
        # Style pour le résultat de la prédiction
        st.markdown(
            f"""
            <div style="background-color:#f0f2f6;padding:20px;border-radius:10px;text-align:center;">
                <h2 style="color:#1e88e5;">Loyer mensuel estimé</h2>
                <h1 style="color:#ff4b4b;font-size:3em;">{prediction:,.0f} Ar</h1>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Comparaison avec le loyer moyen du quartier
        loyer_moyen_quartier = data[data['quartier'] == quartier]['loyer_mensuel'].mean()
        
        st.markdown("### Comparaison")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric(
                label=f"Loyer moyen dans {quartier}",
                value=f"{loyer_moyen_quartier:,.0f} Ar",
                delta=f"{prediction - loyer_moyen_quartier:,.0f} Ar"
            )
        
        with col_b:
            loyer_moyen_global = data['loyer_mensuel'].mean()
            st.metric(
                label="Loyer moyen global",
                value=f"{loyer_moyen_global:,.0f} Ar",
                delta=f"{prediction - loyer_moyen_global:,.0f} Ar"
            )

# Visualisations
st.header("Visualisations")

tab1, tab2, tab3 = st.tabs(["Statistiques par quartier", "Influence des caractéristiques", "Carte"])

with tab1:
    if data is not None:
        # Loyer moyen par quartier
        st.subheader("Loyer moyen par quartier")
        fig, ax = plt.subplots(figsize=(12, 6))
        quartier_stats = data.groupby('quartier')['loyer_mensuel'].agg(['mean', 'count']).reset_index()
        quartier_stats = quartier_stats.sort_values('mean', ascending=False)
        
        sns.barplot(x='quartier', y='mean', data=quartier_stats, ax=ax)
        ax.set_title('Loyer moyen par quartier')
        ax.set_xlabel('Quartier')
        ax.set_ylabel('Loyer mensuel moyen (Ar)')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
        st.pyplot(fig)
        
        # Distribution des loyers
        st.subheader("Distribution des loyers")
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.histplot(data['loyer_mensuel'], kde=True, ax=ax)
        if prediction is not None:
            ax.axvline(prediction, color='red', linestyle='--', label='Prédiction')
            ax.legend()
        ax.set_title('Distribution des loyers mensuels')
        ax.set_xlabel('Loyer mensuel (Ar)')
        st.pyplot(fig)

with tab2:
    if data is not None and model is not None:
        st.subheader("Influence des caractéristiques sur le loyer")
        
        # Relation entre superficie et loyer
        st.write("#### Relation entre superficie et loyer")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.scatterplot(x='superficie', y='loyer_mensuel', data=data, alpha=0.5, ax=ax)
        if prediction is not None:
            ax.scatter(superficie, prediction, color='red', s=100, label='Prédiction')
            ax.legend()
        ax.set_title('Relation entre superficie et loyer mensuel')
        ax.set_xlabel('Superficie (m²)')
        ax.set_ylabel('Loyer mensuel (Ar)')
        st.pyplot(fig)
        
        # Loyer par nombre de chambres
        st.write("#### Loyer par nombre de chambres")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.boxplot(x='nombre_chambres', y='loyer_mensuel', data=data, ax=ax)
        if prediction is not None:
            ax.scatter(nombre_chambres - 1, prediction, color='red', s=100, label='Prédiction')
            ax.legend()
        ax.set_title('Loyer mensuel par nombre de chambres')
        ax.set_xlabel('Nombre de chambres')
        ax.set_ylabel('Loyer mensuel (Ar)')
        st.pyplot(fig)
        
        # Loyer par état général
        st.write("#### Loyer par état général")
        fig, ax = plt.subplots(figsize=(10, 6))
        order = ['mauvais', 'moyen', 'bon']
        sns.boxplot(x='état_général', y='loyer_mensuel', data=data, order=order, ax=ax)
        if prediction is not None:
            ax.scatter(order.index(etat_general), prediction, color='red', s=100, label='Prédiction')
            ax.legend()
        ax.set_title('Loyer mensuel par état général')
        ax.set_xlabel('État général')
        ax.set_ylabel('Loyer mensuel (Ar)')
        st.pyplot(fig)

with tab3:
    st.subheader("Carte des quartiers d'Antananarivo")
    
    # Coordonnées approximatives des quartiers d'Antananarivo
    # Ces coordonnées sont fictives et devraient être remplacées par des données réelles
    quartier_coords = {
        'Anosibe': [-18.9141, 47.5315],
        'Analamahitsy': [-18.8689, 47.5315],
        'Andoharanofotsy': [-18.9667, 47.5167],
        '67Ha': [-18.9000, 47.5167],
        'Analakely': [-18.9100, 47.5233],
        'Ambatobe': [-18.8833, 47.5333],
        'Ambanidia': [-18.9167, 47.5333],
        'Ambatonakanga': [-18.9167, 47.5250],
        'Ambatoroka': [-18.9000, 47.5333],
        'Ambodivona': [-18.9167, 47.5167],
        'Ambolokandrina': [-18.9333, 47.5167],
        'Ampandrana': [-18.9000, 47.5083],
        'Andraharo': [-18.8833, 47.5083],
        'Ankazobe': [-18.9333, 47.5083],
        'Ankadifotsy': [-18.9000, 47.5250],
        'Ivandry': [-18.8833, 47.5417],
        'Isoraka': [-18.9167, 47.5167],
        'Soanierana': [-18.9333, 47.5417],
        'Tanjombato': [-18.9833, 47.5167],
        'Tsaralalana': [-18.9000, 47.5167]
    }
    
    # Création de la carte
    m = folium.Map(location=[-18.9100, 47.5233], zoom_start=12)
    
    # Ajout des marqueurs pour chaque quartier
    for q, coords in quartier_coords.items():
        # Calcul du loyer moyen pour ce quartier
        if data is not None:
            loyer_moyen = data[data['quartier'] == q]['loyer_mensuel'].mean()
            popup_text = f"<b>{q}</b><br>Loyer moyen: {loyer_moyen:,.0f} Ar"
        else:
            popup_text = q
        
        # Couleur du marqueur (rouge pour le quartier sélectionné)
        color = 'red' if q == quartier else 'blue'
        
        folium.Marker(
            location=coords,
            popup=popup_text,
            tooltip=q,
            icon=folium.Icon(color=color)
        ).add_to(m)
    
    # Affichage de la carte
    folium_static(m)

# Informations supplémentaires
st.markdown("---")
st.markdown("""
### À propos de cette application
Cette application a été développée dans le cadre d'un TP sur la régression linéaire multiple.
Elle permet de prédire le loyer mensuel d'un logement à Antananarivo en fonction de ses caractéristiques.

**Variables utilisées pour la prédiction :**
- Quartier
- Superficie
- Nombre de chambres
- Type de douche/WC
- Type d'accès
- Meublé ou non
- État général
""")
