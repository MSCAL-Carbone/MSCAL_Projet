import streamlit as st
import pandas as pd
import datetime
import altair as alt
import io
import json

# ==============================================================================
# 1. CONFIGURATION & STYLE
# ==============================================================================
st.set_page_config(
    page_title="MSCAL Carbon ERP",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Style CSS Amélioré
st.markdown("""
    <style>
        /* Style général */
        .block-container {padding-top: 1rem;}
        h1 {color: #2c3e50;}
        h2 {color: #34495e;}
        h3 {color: #16a085;} /* Un joli vert pour les sous-titres */
        
        /* Style des "Cartes" de chiffres (Metrics) */
        [data-testid="stMetric"] {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05); /* Petite ombre douce */
            text-align: center;
        }
        
        /* Style des Onglets */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: white;
            border-radius: 5px;
            border: 1px solid #ddd;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: #e8f5e9; /* Vert très clair quand sélectionné */
            color: #1e8449;
            border: 1px solid #1e8449;
        }

        /* Footer et Impression (inchangé) */
        .footer {
            position: fixed; bottom: 0; left: 0; width: 20%;
            background-color: #f0f2f6; color: #555;
            text-align: center; padding: 10px; font-size: 11px;
            border-top: 1px solid #ddd; z-index: 999;
        }
        @media print {
            [data-testid="stSidebar"], .stButton, header {display: none;}
            .block-container {padding-top: 0 !important;}
        }
    </style>
""", unsafe_allow_html=True)

# --- SÉCURITÉ : MOT DE PASSE et GESTION DES RÔLES ---

def check_password():
    """Gère l'authentification Admin vs Visiteur."""
    if "user_role" not in st.session_state:
        st.session_state.user_role = None

    if st.session_state.user_role:
        return True  # Déjà connecté

    # Espace pour le titre
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    st.markdown("### 🔒 Accès Sécurisé MSCAL ERP")
    st.caption("Connectez-vous pour accéder à l'outil.")
    
    pwd = st.text_input("Mot de passe :", type="password")
    
    if st.button("Se connecter"):
        if pwd == "MSCAL2026":  # <--- MOT DE PASSE ADMIN
            st.session_state.user_role = "admin"
            st.success("Connexion Admin réussie !")
            st.rerun()
        elif pwd == "GUEST":    # <--- MOT DE PASSE VISITEUR
            st.session_state.user_role = "guest"
            st.info("Connexion Visiteur (Accès limité).")
            st.rerun()
        else:
            st.error("❌ Mot de passe incorrect")
            
    return False

if not check_password():
    st.stop()


# Style CSS (Signature + Titres + Ajustements)
st.markdown("""
    <style>
        .footer {
            position: fixed; bottom: 0; left: 0; width: 20%;
            background-color: #f0f2f6; color: #555;
            text-align: center; padding: 10px; font-size: 11px;
            border-top: 1px solid #ddd; z-index: 999;
        }
        .block-container {padding-top: 1rem;}
        h3 {color: #2c3e50; font-weight: 600;}
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px; }
        .stTabs [aria-selected="true"] { background-color: #e8f0fe; color: #1a73e8; }
        .stDataFrame {border: 1px solid #ddd; border-radius: 5px;}
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INITIALISATION MÉMOIRE & PARAMÈTRES (AUTO-RÉPARATION)
# ==============================================================================
DEFAULT_PARAMS = {
    'entity_name': 'Promo MSCAL 2026',
    'pop_etu': 20, 
    'pop_alt': 5, 
    'pop_prof': 2,
    'jours_ouverture': 160,
    'budget_co2': 3.5,
    'country_choice': "France 🇫🇷",
    
    # --- FINANCE ---
    'shadow_price': 100.0,
    
    # --- ÉNERGIE & EAU ---
    'fe_elec': 0.060,       # Mix France
    'fe_gaz': 0.227,        # Gaz naturel
    'fe_eau': 0.132,        # Eau potable (m3)
    'fe_dechet': 0.200,     # Déchets moyens
    
    # --- MOBILITÉ ---
    'fe_voit': 0.190,       # Voiture thermique
    'fe_voit_elec': 0.060,  # Voiture élec
    'fe_avion_court': 0.258,
    'fe_avion_long': 0.230,
    'fe_tgv': 0.002,        # TGV
    'fe_ter': 0.030,        # Train classique
    'fe_bus': 0.100,        # Bus urbain
    'fe_autocar': 0.030,    # Autocar
    
    # --- VIE & ACHATS ---
    'fe_boeuf': 7.0,        # Repas Bœuf
    'fe_volaille': 1.6,     # Repas Poulet
    'fe_vege': 0.5,         # Repas Végétarien
    'fe_cafe': 5.0,         # Café (kg)
    
    # --- NUMÉRIQUE (IT) ---
    'fe_it_laptop': 156.0,  # PC Portable
    'fe_it_desktop': 350.0, # PC Fixe
    'fe_it_screen': 200.0,  # Écran 24"
    'fe_it_smartphone': 60.0
}

# Initialisation des paramètres avec Sécurité
if 'params' not in st.session_state:
    st.session_state.params = DEFAULT_PARAMS.copy()
else:
    # Réparation : on injecte les clés manquantes
    for key, value in DEFAULT_PARAMS.items():
        if key not in st.session_state.params:
            st.session_state.params[key] = value

# Initialisation de la base de données des flux
if 'db_entries' not in st.session_state:
    st.session_state.db_entries = []

# Base de données des Pays
COUNTRY_DATA = {
    "France 🇫🇷": {"val": 0.060, "info": "Mix Nucléaire (Bas carbone)"},
    "Allemagne 🇩🇪": {"val": 0.380, "info": "Mix Charbon/Renouvelable"},
    "Europe (Moy) 🇪🇺": {"val": 0.255, "info": "Moyenne continentale"},
    "USA 🇺🇸": {"val": 0.370, "info": "Mix Fossile prédominant"},
    "Chine 🇨🇳": {"val": 0.550, "info": "Dominante Charbon"}
}

# Fonction de sauvegarde standardisée (Compatible Tableaux)
def save_flux(cat, item, val, unit, fe, incertitude, detail):
    impact = val * fe
    marge = impact * (incertitude / 100.0)
    st.session_state.db_entries.append({
        "Catégorie": cat,
        "Item": item,
        "Quantité": f"{val} {unit}",
        "Impact_kgCO2": float(impact), # Nom standardisé
        "Incertitude": int(incertitude),
        "Marge": float(marge),
        "Détail": detail,
        "Date": str(datetime.date.today())
    })

# ==============================================================================
# 3. BARRE LATÉRALE
# ==============================================================================
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.header("🌍 MSCAL ERP")
    # --- ZONE DE SAUVEGARDE/CHARGEMENT (Optimisée) ---
    st.sidebar.divider() # Une ligne de séparation propre
    
    # On met tout dans un menu déroulant pour gagner de la place
    with st.sidebar.expander("💾 Sauvegarde & Restauration", expanded=False):
        st.caption("Pour ne jamais perdre vos données.")
        col_save, col_load = st.columns(2)
        
        # Bouton SAUVEGARDER
        with col_save:
            session_data = {
                'params': st.session_state.params,
                'db': st.session_state.db_entries
            }
            session_json = json.dumps(session_data)
            st.download_button("⬇️ Sauver", session_json, f"mscal_bkp_{datetime.date.today()}.json", "application/json", use_container_width=True)

        # Bouton CHARGER
        with col_load:
            # Astuce visuelle : on utilise un bouton vide qui sert juste de label
            st.markdown("⬆️ **Ouvrir**") 
        
        # Le chargeur de fichier juste en dessous, plus discret
        uploaded_json = st.file_uploader("Chargez votre fichier JSON ici", type=["json"], label_visibility="collapsed")
        if uploaded_json is not None:
            try:
                data = json.load(uploaded_json)
                if 'params' in data: st.session_state.params = data['params']
                if 'db' in data: st.session_state.db_entries = data['db']
                st.success("✅ Chargé !")
                st.rerun()
            except:
                st.error("Fichier invalide")

    st.markdown("### 🧭 Menu de Navigation")
    # --- DÉFINITION DU MENU SELON LE RÔLE ---
    if st.session_state.user_role == "admin":
        # L'Admin voit tout
        menu_options = [
            "0. 📘 GUIDE & DÉFINITIONS",
            "1. ⚙️ DÉFINIR & PARAMÉTRER", 
            "2. 📝 MESURER (Saisie Flux)", 
            "3. 📊 ANALYSER (Cockpit & KPIs)",
            "4. 🚀 AMÉLIORER (Simulateur)",
            "5. 📄 CONTRÔLER (Rapport Final)"
        ]
    else:
        # Le Visiteur/Étudiant voit une version simplifiée
        menu_options = [
            "0. 📘 GUIDE & DÉFINITIONS",
            "2. 📝 MESURER (Saisie Flux)", 
            "3. 📊 ANALYSER (Cockpit & KPIs)",
            "4. 🚀 AMÉLIORER (Simulateur)"
        ]
        st.info(f"👤 Mode Visiteur")

    nav = st.radio("Séquence de travail", menu_options)
    
    st.divider()
    
    # Indicateur Ambition
    st.markdown("🎯 **Objectif Cible**")
    # Sécurité anti-crash pour le budget
    try:
        b_val = float(st.session_state.params.get('budget_co2', 3.5))
    except:
        b_val = 3.5
        st.session_state.params['budget_co2'] = 3.5
    
    if b_val <= 2.5: color = "green"
    elif b_val <= 5.0: color = "blue"
    elif b_val <= 9.0: color = "orange"
    else: color = "red"
    st.markdown(f":{color}[**{b_val:.1f} Tonnes / pers**]")

    # Bouton de nettoyage d'urgence (LA SOLUTION À TES PROBLÈMES)
    if st.session_state.db_entries:
        st.divider()
        if st.button("🗑️ Effacer toutes les données"):
            st.session_state.db_entries = []
            st.rerun()

    # Signature ACS
    st.sidebar.markdown("""
        <div class="footer">
            <b>© 2026 MSCAL CARBON ERP</b><br>
            <i>Solution Ingénieur</i><br>
            Developed by <b>Team ACS</b><br>
            (Abdel | Clara | Steve)<br>
            ENSAIA
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# PAGE 0 : GUIDE & DÉFINITIONS
# ==============================================================================
if "0." in nav:
    st.title("📘 Guide Utilisateur & Méthodologie")
    st.markdown("Bienvenue dans le **MSCAL Carbon ERP**. Ce guide vous explique les concepts clés et comment utiliser l'outil.")

    with st.expander("📖 Mode d'Emploi Rapide", expanded=True):
        st.markdown("""
        1.  **DÉFINIR :** Configurez les paramètres de votre école (nombre d'élèves, pays, calendrier).
        2.  **MESURER :** Saisissez vos équipements (inventaire) et les déplacements (flux).
        3.  **ANALYSER :** Visualisez vos impacts et identifiez les points critiques (Hotspots).
        4.  **AMÉLIORER :** Simulez des scénarios de réduction (ex: Télétravail, Isolation) pour 2030.
        5.  **CONTRÔLER :** Éditez le rapport officiel PDF/Excel pour la direction.
        """)

    with st.expander("🧐 Comprendre les Scopes (1, 2, 3)", expanded=True):
        st.info("""
        **Scope 1 (Direct) :** Émissions directes sur le site.  
        *Ex : Gaz brûlé par la chaudière, Carburant des véhicules de service.*
        
        **Scope 2 (Énergie Indirecte) :** Émissions liées à la production de l'électricité que vous consommez.  
        *Ex : L'électricité pour l'éclairage et les ordinateurs.*
        
        **Scope 3 (Autres Indirects) :** Tout le reste ! C'est souvent 80% du bilan.  
        *Ex : Déplacements domicile-travail, achats de PC, nourriture, déchets...*
        """)

    with st.expander("🧠 Définitions des KPIs & Termes Techniques"):
        st.markdown("""
        * **kgCO2e (Équivalent CO2) :** Unité de mesure universelle qui regroupe tous les gaz à effet de serre (CO2, Méthane, etc.).
        * **Facteur d'Émission (FE) :** Le coefficient qui transforme une donnée physique en CO2. *Ex: 1 kWh d'élec en France = 0.060 kgCO2e.*
        * **Shadow Price (Coût Fantôme) :** On donne un prix fictif à la tonne de CO2 (ex: 100€/T) pour visualiser le risque financier futur (taxe carbone).
        * **Incertitude :** Marge d'erreur de la donnée. Si vous estimez un kilométrage "à la louche", l'incertitude est haute (30-50%).
        * **Pareto (80/20) :** Principe selon lequel 20% des causes font 80% des dégâts. On cherche ces 20% pour agir vite.
        """)
# ==============================================================================
# PAGE 1 : DÉFINIR (CONFIGURATION)
# ==============================================================================

if "1." in nav:
    st.title("⚙️ Paramétrage du Projet")
    st.markdown("Définissez le contexte, la population et les hypothèses techniques.")

    # --- A. IDENTITÉ & POPULATION ---
    with st.container(border=True):
        st.subheader("1. Identité & Population")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.session_state.params['entity_name'] = st.text_input(
                "Nom de l'entité", 
                value=st.session_state.params['entity_name']
            )
            
            st.markdown("**Détail des Effectifs :**")
            col_a, col_b, col_c = st.columns(3)
            
            # Sécurité type
            p_etu = col_a.number_input("Étudiants", 0, 500, int(st.session_state.params.get('pop_etu', 20)))
            p_alt = col_b.number_input("Alternants", 0, 500, int(st.session_state.params.get('pop_alt', 5)))
            p_prof = col_c.number_input("Staff/Profs", 0, 100, int(st.session_state.params.get('pop_prof', 2)))
            
            st.session_state.params['pop_etu'] = p_etu
            st.session_state.params['pop_alt'] = p_alt
            st.session_state.params['pop_prof'] = p_prof
            
            total = p_etu + p_alt + p_prof
            st.metric("Population Totale", f"{total} personnes")

        with c2:
            st.markdown("**🎯 Ambition Climatique**")
            # Utilisation de slider simple (plus robuste que select_slider pour les conflits de mémoire)
            budget = st.slider(
                "Budget Cible (Tonnes CO2e/an/personne)",
                min_value=1.0, max_value=15.0, 
                value=float(st.session_state.params.get('budget_co2', 3.5)),
                step=0.5
            )
            st.session_state.params['budget_co2'] = budget
            
            if budget <= 2.0: 
                st.success("🏆 **Obj. 2050 (Accords de Paris)** - Idéal mais difficile")
            elif budget <= 5.0: 
                st.info("👍 **Transition Mondiale** - Moyenne Mondiale")
            elif budget <= 9.0: 
                st.warning("🇫🇷 **Moyenne Française** - Business as usual")
            else: 
                st.error("🚨 **Critique** - Niveau USA/Qatar")

    # --- B. CALENDRIER ---
    with st.container(border=True):
        st.subheader("2. Gestion du Temps (Calendrier)")
        
        t_calc, t_imp, t_man = st.tabs(["📅 Calculateur Univ.", "📂 Mode Expert (Excel)", "🎚️ Mode Manuel"])
        
        # 1. LE CALCULATEUR UNIVERSITAIRE
        with t_calc:
            st.info("Calculez les jours ouvrés en soustrayant les vacances.")
            c_dates, c_result = st.columns(2)
            with c_dates:
                d_start = st.date_input("Date de Rentrée", datetime.date(2025, 9, 1))
                d_end = st.date_input("Fin d'année", datetime.date(2026, 6, 30))
                
                nb_semaines_vac = st.number_input("Semaines de vacances (Noël, Hiver...)", 0, 20, 4)
                jours_par_semaine = st.slider("Jours de cours / semaine", 1, 6, 5)
            
            with c_result:
                total_days = (d_end - d_start).days
                if total_days > 0:
                    total_weeks = total_days / 7
                    weeks_presence = total_weeks - nb_semaines_vac
                    jours_presence_estimes = int(weeks_presence * jours_par_semaine)
                    
                    st.write(f"• Période Totale : **{total_weeks:.1f} sem.**")
                    st.write(f"• Vacances : **-{nb_semaines_vac} sem.**")
                    st.metric("Jours de Présence Estimés", f"{jours_presence_estimes} jours")
                    
                    if st.button("✅ Valider ce calcul"):
                        st.session_state.params['jours_ouverture'] = jours_presence_estimes
                        st.toast(f"Calendrier mis à jour : {jours_presence_estimes} jours")
                else:
                    st.error("La date de fin doit être après la date de début.")

        # 2. IMPORT EXCEL
        with t_imp:
            st.write("**Import Fichier Planning**")
            up_cal = st.file_uploader("Fichier Excel/CSV", type=["csv", "xlsx"])
            if up_cal:
                try:
                    if up_cal.name.endswith('.csv'): df_cal = pd.read_csv(up_cal)
                    else: df_cal = pd.read_excel(up_cal)
                    
                    st.success(f"✅ Fichier lu : {len(df_cal)} lignes détectées.")
                    # Analyse intelligente si colonne Type existe
                    cols_lower = [c.lower() for c in df_cal.columns]
                    if any(x in cols_lower for x in ['type', 'statut']):
                         col = next(x for x in df_cal.columns if x.lower() in ['type', 'statut'])
                         st.dataframe(df_cal[col].value_counts(), use_container_width=True)

                    if st.button("Appliquer ce fichier"):
                        st.session_state.params['jours_ouverture'] = len(df_cal)
                        st.rerun()
                except: st.error("Erreur de format fichier")
            else:
                # --- MODIFICATION EXCEL ICI ---
                buffer_modele = io.BytesIO()
                with pd.ExcelWriter(buffer_modele, engine='xlsxwriter') as writer:
                    df_modele = pd.DataFrame([{"Date": "2026-09-01", "Type": "Rentrée"}, {"Date": "2026-12-25", "Type": "Vacances"}])
                    df_modele.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Télécharger Modèle (.xlsx)",
                    data=buffer_modele,
                    file_name="modele_calendrier.xlsx",
                    mime="application/vnd.ms-excel"
                )
        # 3. MANUEL
        with t_man:
            j = st.slider("Ajustement direct", 0, 365, int(st.session_state.params['jours_ouverture']))
            if st.button("Forcer cette valeur"):
                st.session_state.params['jours_ouverture'] = j
                st.toast("Valeur forcée !")

    # --- C. CONFIGURATION TECHNIQUE (VERSION EXPERT COMPLETE) ---
    with st.container(border=True):
        st.subheader("3. Facteurs d'Émission & Hypothèses (Base ADEME)")
        st.caption("Modifiez ces valeurs uniquement si vous avez des données fournisseurs spécifiques.")
        
        # SÉLECTEUR PAYS
        c_pays, c_prix = st.columns(2)
        with c_pays:
            idx = 0
            # Sécurité si le pays en mémoire n'existe plus dans la liste
            current_country = st.session_state.params.get('country_choice')
            if current_country in COUNTRY_DATA:
                idx = list(COUNTRY_DATA.keys()).index(current_country)
            
            pays = st.selectbox("🌍 Localisation (Impacte le Mix Électrique)", list(COUNTRY_DATA.keys()), index=idx)
            
            st.session_state.params['country_choice'] = pays
            st.session_state.params['fe_elec'] = COUNTRY_DATA[pays]["val"]
            st.info(f"Facteur : **{COUNTRY_DATA[pays]['val']} kgCO2/kWh**")
            
        with c_prix:
            st.session_state.params['shadow_price'] = st.number_input("💶 Prix du Carbone (€/T)", value=float(st.session_state.params['shadow_price']), step=10.0)

        # ONGLETS DE FACTEURS DÉTAILLÉS (COMPLETS)
        t_en, t_mob, t_vie, t_it = st.tabs(["⚡ Énergie & Fluides", "🚗 Mobilité", "🍔 Vie & Restauration", "💻 Numérique"])
        
        with t_en:
            c1, c2 = st.columns(2)
            st.session_state.params['fe_gaz'] = c1.number_input("Gaz (kg/kWh)", value=float(st.session_state.params['fe_gaz']), format="%.3f")
            st.session_state.params['fe_eau'] = c2.number_input("Eau (kg/m3)", value=float(st.session_state.params['fe_eau']), format="%.3f")
            st.session_state.params['fe_dechet'] = c1.number_input("Déchets (kg/kg)", value=float(st.session_state.params['fe_dechet']), format="%.3f")

        with t_mob:
            st.markdown("##### 🚗 Transport Terrestre")
            c1, c2 = st.columns(2)
            st.session_state.params['fe_voit'] = c1.number_input("Voiture Thermique (kg/km)", value=float(st.session_state.params['fe_voit']), format="%.3f")
            st.session_state.params['fe_voit_elec'] = c2.number_input("Voiture Élec (kg/km)", value=float(st.session_state.params['fe_voit_elec']), format="%.3f")
            st.session_state.params['fe_bus'] = c1.number_input("Bus Urbain (kg/km)", value=float(st.session_state.params['fe_bus']), format="%.3f")
            st.session_state.params['fe_autocar'] = c2.number_input("Autocar (kg/km)", value=float(st.session_state.params['fe_autocar']), format="%.3f")
            
            st.divider()
            
            st.markdown("##### ✈️ Ferroviaire & Aérien")
            c3, c4 = st.columns(2)
            st.session_state.params['fe_tgv'] = c3.number_input("TGV (kg/km)", value=float(st.session_state.params['fe_tgv']), format="%.3f")
            st.session_state.params['fe_ter'] = c4.number_input("TER / Train (kg/km)", value=float(st.session_state.params['fe_ter']), format="%.3f")
            st.session_state.params['fe_avion_court'] = c3.number_input("Avion Court (kg/km)", value=float(st.session_state.params['fe_avion_court']), format="%.3f")
            st.session_state.params['fe_avion_long'] = c4.number_input("Avion Long (kg/km)", value=float(st.session_state.params['fe_avion_long']), format="%.3f")

        with t_vie:
            c1, c2 = st.columns(2)
            st.session_state.params['fe_boeuf'] = c1.number_input("Repas Bœuf (kg/u)", value=float(st.session_state.params['fe_boeuf']), format="%.2f")
            st.session_state.params['fe_volaille'] = c2.number_input("Repas Poulet (kg/u)", value=float(st.session_state.params['fe_volaille']), format="%.2f")
            st.session_state.params['fe_vege'] = c1.number_input("Repas Végé (kg/u)", value=float(st.session_state.params['fe_vege']), format="%.2f")
            st.session_state.params['fe_cafe'] = c2.number_input("Café (kg/kg)", value=float(st.session_state.params['fe_cafe']), format="%.2f")

        with t_it:
            c1, c2 = st.columns(2)
            st.session_state.params['fe_it_laptop'] = c1.number_input("Fabrication Laptop (kg)", value=float(st.session_state.params['fe_it_laptop']), format="%.1f")
            st.session_state.params['fe_it_desktop'] = c2.number_input("Fabrication PC Fixe (kg)", value=float(st.session_state.params['fe_it_desktop']), format="%.1f")
            st.session_state.params['fe_it_screen'] = c1.number_input("Fabrication Écran (kg)", value=float(st.session_state.params['fe_it_screen']), format="%.1f")
            st.session_state.params['fe_it_smartphone'] = c2.number_input("Fabrication Smartphone (kg)", value=float(st.session_state.params['fe_it_smartphone']), format="%.1f")

# ==============================================================================
# PAGE 2 : MESURER (SAISIE EXPERT DES FLUX)
# ==============================================================================
elif "2." in nav:
    st.title("📝 Mesure des Flux & Inventaires (Data Collection)")
    st.markdown("Approche 'Bottom-Up' : Saisie des inventaires physiques, des surfaces et des flux logistiques humains.")

    # --- ARCHITECTURE SUPPLY CHAIN (4 PILIERS) ---
    tab_bat, tab_log, tab_conso, tab_it = st.tabs([
        "🏭 Bâtiment & Inventaire", 
        "🔄 Logistique Humaine (TMS)", 
        "📦 Consommables & Surfaces",
        "💻 Parc Numérique"
    ])

    # 1. BÂTIMENT & INVENTAIRE
    with tab_bat:
        st.subheader("1. Asset Management (Équipements & Salles)")
        st.info("Ici, recensez tout le matériel présent dans les salles (Salle de classe, Bureaux Profs).")
        
        if 'inventory_df' not in st.session_state:
            st.session_state.inventory_df = pd.DataFrame(
                [
                    {"Objet": "Chaise Étudiant", "Qté": 30, "Poids/Conso": 5.0, "Type": "Mobilier (kg)", "Incertitude": 10},
                    {"Objet": "Bureau Prof", "Qté": 2, "Poids/Conso": 25.0, "Type": "Mobilier (kg)", "Incertitude": 10},
                    {"Objet": "Radiateur Élec", "Qté": 4, "Poids/Conso": 1500.0, "Type": "Élec (Watts)", "Incertitude": 5},
                ]
            )

        edited_inv = st.data_editor(
            st.session_state.inventory_df,
            num_rows="dynamic", 
            column_config={
                "Type": st.column_config.SelectboxColumn("Type Flux", options=["Mobilier (kg)", "Élec (Watts)", "Machine Spé (Watts)"]),
                "Incertitude": st.column_config.NumberColumn("Marge Erreur %", min_value=0, max_value=50, format="%d%%")
            },
            use_container_width=True
        )
        st.session_state.inventory_df = edited_inv 

        if st.button("💾 Enregistrer cet Inventaire au Bilan"):
            for i, row in edited_inv.iterrows():
                if "Mobilier" in row["Type"]:
                    impact = (row["Qté"] * row["Poids/Conso"] * 1.5) / 10 
                    save_flux("Bâtiment", row["Objet"], row["Qté"], "u", 1.0, row["Incertitude"], "Amortissement 10 ans")
                elif "Watts" in row["Type"]:
                    heures = 8 
                    kwh = (row["Qté"] * row["Poids/Conso"] * heures * st.session_state.params['jours_ouverture']) / 1000
                    save_flux("Énergie", f"Conso {row['Objet']}", kwh, "kWh", st.session_state.params['fe_elec'], row["Incertitude"], "Scope 2")
            st.success("Inventaire et Consommations énergétiques associés calculés !")

    # 2. LOGISTIQUE HUMAINE
    with tab_log:
        st.subheader("2. Gestion des Flux de Personnes")
        c_profil, c_detail = st.columns([1, 2])
        
        with c_profil:
            st.markdown("**Profil Voyageur**")
            user_type = st.radio("Sélectionnez le cas :", [
                "🎓 Étudiant Initiale (Continu)",
                "💼 Étudiant Alternant (Rythmé)",
                "🌍 Étudiant Échange",
                "👨‍🏫 Prof Fixe (ENSAIA)",
                "🎤 Intervenant Extérieur"
            ])
        
        with c_detail:
            with st.form("human_logistics"):
                st.markdown(f"**Configuration : {user_type}**")
                
                jours_presence = 0
                txt_context = ""

                if "Initiale" in user_type:
                    st.caption("Cas classique : Présent toute l'année scolaire (Pré-Spé + Spé).")
                    jours_presence = st.session_state.params['jours_ouverture']
                
                elif "Alternant" in user_type:
                    st.caption("Cas complexe : Période école vs Période entreprise.")
                    c_a, c_b = st.columns(2)
                    semaines_ecole = c_a.number_input("Semaines École (Total)", 1, 52, 20)
                    rythme = st.selectbox("Rythme Alternance", ["2 semaines / 2 semaines", "1 semaine / 3 semaines", "Autre"])
                    jours_presence = semaines_ecole * 5
                    txt_context = f"Rythme: {rythme}"

                elif "Échange" in user_type:
                    st.caption("Arrive après la pré-spécialisation.")
                    mois = st.slider("Durée présence (mois)", 1, 10, 6)
                    jours_presence = mois * 20
                
                elif "Prof" in user_type:
                    st.caption("Nos 2 profs fixes (Responsable Spé + Enseignant).")
                    jours_presence = st.number_input("Jours présence site / an", 1, 250, 160)
                
                elif "Intervenant" in user_type:
                    st.caption("Visiteurs ponctuels (Profs extérieurs, Pros).")
                    nb_visites = st.number_input("Nombre d'interventions / an", 1, 50, 2)
                    jours_presence = nb_visites

                st.divider()
                st.markdown("**Logistique de Déplacement**")
                c_t1, c_t2 = st.columns(2)
                mode = c_t1.selectbox("Moyen de Transport", ["Voiture Thermique", "Voiture Élec", "Train/TER", "TGV", "Bus", "Avion"])
                dist = c_t2.number_input("Distance A/R (km)", 1, 10000, 30)
                nb_pax = st.number_input("Nombre de personnes concernées", 1, 100, 1)
                
                incert = st.slider("Marge d'incertitude (Fiabilité donnée)", 0, 50, 10)

                if st.form_submit_button("Calculer Flux Humain"):
                    fe = 0.0
                    if "Thermique" in mode: fe = st.session_state.params['fe_voit']
                    elif "Voiture Élec" in mode: fe = st.session_state.params['fe_voit_elec']
                    elif "Train" in mode: fe = st.session_state.params['fe_ter']
                    elif "TGV" in mode: fe = st.session_state.params['fe_tgv']
                    elif "Bus" in mode: fe = st.session_state.params['fe_bus']
                    elif "Avion" in mode: fe = st.session_state.params['fe_avion_long']

                    total_km = dist * jours_presence * nb_pax
                    save_flux("Mobilité", f"Trajet {user_type}", total_km, "km.pax", fe, incert, f"{mode} | {jours_presence}j/an | {txt_context}")
                    st.success("Flux logistique ajouté !")

    # 3. CONSOMMABLES & SURFACES
    with tab_conso:
        st.subheader("3. Consommables & Surfaces")
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("##### 🧱 Surfaces & Bâtiment")
            with st.form("surf_form"):
                surface = st.number_input("Surface chauffée/utilisée (m²)", 1, 5000, 100)
                type_heat = st.selectbox("Source Chauffage", ["Gaz", "Électricité", "Réseau Urbain"])
                ratio = st.number_input("Ratio Conso (kWh/m²/an)", 10, 500, 110)
                
                if st.form_submit_button("Ajouter Bâtiment"):
                    fe = st.session_state.params['fe_gaz'] if "Gaz" in type_heat else st.session_state.params['fe_elec']
                    total_kwh = surface * ratio
                    save_flux("Bâtiment", f"Chauffage ({type_heat})", total_kwh, "kWh", fe, 10, f"{surface} m²")
                    st.success("Impact Bâtiment calculé.")

        with c2:
            st.markdown("##### 🍔 Vie de Campus (Consommables)")
            with st.form("conso_form"):
                item = st.selectbox("Item", ["Repas Bœuf", "Repas Végé", "Café", "Papier (Rames)", "Goodies Promo"])
                qte = st.number_input("Quantité Annuelle", 1, 10000, 500)
                incert_conso = st.slider("Marge Erreur %", 0, 50, 20)
                
                if st.form_submit_button("Ajouter Conso"):
                    fe = 1.0
                    if "Bœuf" in item: fe = st.session_state.params['fe_boeuf']
                    elif "Végé" in item: fe = st.session_state.params['fe_vege']
                    elif "Café" in item: fe = st.session_state.params['fe_cafe']
                    save_flux("Achats", item, qte, "u", fe, incert_conso, "Conso courante")
                    st.success("Ajouté.")

    # 4. PARC NUMÉRIQUE
    with tab_it:
        st.subheader("4. Impact du Numérique (ACV)")
        st.caption("Analyse Cycle de Vie : On compte la fabrication amortie sur la durée de vie.")
        
        with st.form("it_form"):
            c_it1, c_it2 = st.columns(2)
            mat = c_it1.selectbox("Matériel", ["PC Portable", "PC Fixe", "Écran", "Smartphone", "Vidéoprojecteur"])
            qte = c_it2.number_input("Nombre d'unités", 1, 500, 25)
            duree = st.slider("Durée de conservation (années)", 1, 8, 4)
            
            if st.form_submit_button("Calculer Impact IT"):
                fe = 100
                if "Portable" in mat: fe = st.session_state.params['fe_it_laptop']
                elif "Fixe" in mat: fe = st.session_state.params['fe_it_desktop']
                elif "Écran" in mat: fe = st.session_state.params['fe_it_screen']
                
                impact_annuel = (fe / duree) * qte
                save_flux("Numérique", f"Parc {mat}", qte, "u", (fe/duree), 10, f"Amortissement {duree} ans")
                st.success(f"Parc IT ajouté : {impact_annuel:.1f} kgCO2e/an")

    # --- TABLEAU DE CONTRÔLE FINAL ---
    st.divider()
    st.markdown("### 🔍 Journal des Flux (Contrôle Qualité)")
    
    if st.session_state.db_entries:
        df_flux = pd.DataFrame(st.session_state.db_entries)
        
        # SÉCURITÉ AFFICHAGE (Contre les vieilles données)
        if "Impact_kgCO2" in df_flux.columns and "Marge" in df_flux.columns:
            st.dataframe(
                df_flux,
                column_config={
                    "Impact_kgCO2": st.column_config.NumberColumn("Impact (kgCO2e)", format="%.1f kg"),
                    "Marge": st.column_config.NumberColumn("± Marge", format="%.1f kg"),
                    "Incertitude": st.column_config.ProgressColumn("Incertitude", min_value=0, max_value=50, format="%d%%"),
                },
                use_container_width=True
            )
            
            tot = df_flux["Impact_kgCO2"].sum()
            marge_tot = df_flux["Marge"].sum()
            
            c_res1, c_res2, c_res3 = st.columns(3)
            c_res1.metric("Impact Total Estimé", f"{tot/1000:.2f} Tonnes")
            c_res2.metric("Marge d'Erreur Global", f"± {marge_tot/1000:.2f} Tonnes")
            c_res3.metric("Fourchette Réelle", f"[{(tot-marge_tot)/1000:.2f} T - {(tot+marge_tot)/1000:.2f} T]")
        else:
            st.error("⚠️ Données incompatibles détectées. Veuillez cliquer sur le bouton 'Effacer toutes les données' dans la barre latérale à gauche.")
    else:
        st.info("Aucune donnée saisie. Commencez par l'inventaire ou les flux logistiques.")
#étape 3
# ==============================================================================
# PAGE 3 : ANALYSER (TABLEAU DE BORD DÉCISIONNEL & SCOPES)
# ==============================================================================
elif "3." in nav:
    import altair as alt 
    
    st.title("📊 Cockpit de Performance & Analyse")
    st.markdown("Analyse fine des impacts, identification des leviers et contrôle de la qualité de donnée.")

    if not st.session_state.db_entries:
        st.warning("⚠️ Aucune donnée disponible. Veuillez remplir l'étape 2 'MESURER' d'abord.")
    else:
        # 1. PRÉPARATION DE LA DATA (ETL)
        df = pd.DataFrame(st.session_state.db_entries)
        
        # Sécurité : On s'assure que les colonnes numériques sont bien des nombres
        df["Impact_kgCO2"] = pd.to_numeric(df["Impact_kgCO2"], errors='coerce').fillna(0)
        df["Marge"] = pd.to_numeric(df["Marge"], errors='coerce').fillna(0)
        
        # --- AJOUT INTELLIGENT : DÉTECTION DES SCOPES ---
        # (Sert à rendre le KPI "Part Scope 3" plus précis et à créer le graphique Scope)
        def get_scope(row):
            detail = str(row.get("Détail", ""))
            if "Scope 1" in detail: return "Scope 1"
            if "Scope 2" in detail: return "Scope 2"
            if "Scope 3" in detail: return "Scope 3"
            
            cat = str(row.get("Catégorie", ""))
            item = str(row.get("Item", ""))
            if "Bâtiment" in cat or "Énergie" in cat:
                if "Gaz" in item or "Fioul" in item: return "Scope 1"
                if "Élec" in item or "Chauffage" in item or "Radiateur" in item: return "Scope 2"
            return "Scope 3"

        df["Scope"] = df.apply(get_scope, axis=1)
        # ------------------------------------------------

        # --- MOTEUR DE CALCUL DES KPIs (Tes calculs originaux) ---
        # A. Totaux
        total_co2_t = df["Impact_kgCO2"].sum() / 1000.0
        total_marge_t = df["Marge"].sum() / 1000.0
        
        # B. Population & Ratios
        pop_totale = st.session_state.params['pop_etu'] + st.session_state.params['pop_alt'] + st.session_state.params['pop_prof']
        if pop_totale == 0: pop_totale = 1
        
        ratio_pers = total_co2_t / pop_totale
        budget_cible = float(st.session_state.params['budget_co2'])
        
        # C. Financier
        cout_carbone = total_co2_t * st.session_state.params['shadow_price']
        
        # D. Qualité de Donnée (DQI)
        if total_co2_t > 0:
            dqi_score = 10 - (df["Marge"].sum() / df["Impact_kgCO2"].sum() * 20) 
        else:
            dqi_score = 0
        dqi_score = max(0, min(10, dqi_score))

        # --- ZONE 1 : CONTROL TOWER (Tes 8 KPIs conservés) ---
        st.markdown("### 🎛️ Control Tower")
        
        # LIGNE 1 : PERFORMANCE ABSOLUE
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Empreinte Totale (Net)", f"{total_co2_t:.2f} T CO2e", f"± {total_marge_t:.2f} T (Incertitude)", delta_color="off")
        
        delta_obj = budget_cible - ratio_pers
        k2.metric("Ratio / Personne", f"{ratio_pers:.2f} T/pers", f"{delta_obj:+.2f} T vs Objectif {budget_cible}T", delta_color="normal")
        
        k3.metric("Coût Fantôme (Risque)", f"{cout_carbone:,.0f} €", f"Prix: {st.session_state.params['shadow_price']}€/T")
        
        intensite_jour = (total_co2_t * 1000) / st.session_state.params['jours_ouverture']
        k4.metric("Intensité Quotidienne", f"{intensite_jour:.0f} kgCO2e/j", "Jours ouvrés")

        # LIGNE 2 : PERFORMANCE SUPPLY CHAIN
        k5, k6, k7, k8 = st.columns(4)
        
        # AMÉLIORATION ICI : On utilise la nouvelle colonne Scope pour être plus précis
        scope3_items = df[df['Scope'] == 'Scope 3']['Impact_kgCO2'].sum() / 1000
        part_scope3 = (scope3_items / total_co2_t) * 100 if total_co2_t > 0 else 0
        
        k5.metric("Part du Scope 3", f"{part_scope3:.1f} %", "Dépendance Extérieure")
        
        dqi_color = "normal" if dqi_score > 7 else "inverse"
        k6.metric("Indice Qualité Donnée (DQI)", f"{dqi_score:.1f} / 10", "Fiabilité", delta_color=dqi_color)
        
        k7.metric("Nombre de Flux", len(df), "Lignes saisies")
        
        bat_impact = df[df['Catégorie'] == 'Bâtiment']['Impact_kgCO2'].sum()
        k8.metric("Impact Bâtiment Seul", f"{bat_impact/1000:.1f} T", "Scope 1 & 2")

        st.divider()

        # --- ZONE 2 : VISUALISATION AVANCÉE (Ajout de l'onglet Scopes) ---
        st.markdown("### 🔭 Analyse Visuelle & Stratégique")
        
        # AJOUT de l'onglet "🏗️ Scopes (ISO)" dans la liste
        t_rep, t_scope, t_pareto, t_matrix, t_pop = st.tabs(["🍩 Répartition", "🏗️ Scopes (ISO)", "📉 Pareto (80/20)", "🎯 Matrice Priorité", "👥 Par Population"])
        
        # GRAPHE 1 : DONUT (Amélioré par rapport au Pie Chart classique)
        with t_rep:
            c1, c2 = st.columns([2, 1])
            with c1:
                df_cat = df.groupby("Catégorie")["Impact_kgCO2"].sum().reset_index()
                chart_donut = alt.Chart(df_cat).mark_arc(innerRadius=60).encode(
                    theta=alt.Theta(field="Impact_kgCO2", type="quantitative"),
                    color=alt.Color(field="Catégorie", type="nominal", scale=alt.Scale(scheme='category10')),
                    order=alt.Order("Impact_kgCO2", sort="descending"),
                    tooltip=["Catégorie", alt.Tooltip("Impact_kgCO2", format=".1f")]
                ).properties(title="Répartition par Grand Poste")
                st.altair_chart(chart_donut, use_container_width=True)
            
            with c2:
                st.markdown("**Top 3 Contributeurs :**")
                top3 = df.groupby("Catégorie")["Impact_kgCO2"].sum().sort_values(ascending=False).head(3)
                for cat, val in top3.items():
                    st.write(f"• **{cat}** : {val/1000:.1f} T ({val/df['Impact_kgCO2'].sum()*100:.0f}%)")

        # GRAPHE 2 : SCOPES (NOUVEAU GRAPHE)
        with t_scope:
            st.caption("Répartition selon la norme ISO 14064 / GHG Protocol.")
            bar_scope = alt.Chart(df).mark_bar(cornerRadius=5).encode(
                x=alt.X('Scope', sort=['Scope 1', 'Scope 2', 'Scope 3'], axis=alt.Axis(title=None)),
                y=alt.Y('sum(Impact_kgCO2)', title='kg CO2e'),
                color=alt.Color('Scope', scale=alt.Scale(domain=['Scope 1', 'Scope 2', 'Scope 3'], range=['#e74c3c', '#f1c40f', '#3498db'])),
                tooltip=['Scope', 'sum(Impact_kgCO2)']
            ).properties(height=300)
            st.altair_chart(bar_scope, use_container_width=True)

        # GRAPHE 3 : PARETO (Ton code original)
        with t_pareto:
            st.caption("Le diagramme de Pareto permet d'identifier les 'Vital Few' : les 20% d'actions qui génèrent 80% de l'impact.")
            df_pareto = df.groupby("Item")["Impact_kgCO2"].sum().reset_index().sort_values("Impact_kgCO2", ascending=False)
            df_pareto["Cumul"] = df_pareto["Impact_kgCO2"].cumsum()
            df_pareto["Cumul_Pct"] = df_pareto["Cumul"] / df_pareto["Impact_kgCO2"].sum()
            
            base = alt.Chart(df_pareto.head(10)).encode(x=alt.X('Item', sort=None))
            bars = base.mark_bar().encode(y='Impact_kgCO2', tooltip=['Item', 'Impact_kgCO2'])
            line = base.mark_line(color='red').encode(y='Cumul_Pct', tooltip=[alt.Tooltip('Cumul_Pct', format='.0%')])
            st.altair_chart((bars + line).resolve_scale(y='independent'), use_container_width=True)

        # GRAPHE 4 : MATRICE (Ton code original)
        with t_matrix:
            st.markdown("#### Matrice Impact / Incertitude")
            st.caption("Ciblez la zone 'Haut-Droite' : Gros Impact & Grosse Incertitude -> Il faut affiner la donnée ici !")
            scatter = alt.Chart(df).mark_circle(size=100).encode(
                x=alt.X('Impact_kgCO2', title='Impact Carbone (kg)'),
                y=alt.Y('Incertitude', title='Incertitude (%)'),
                color='Catégorie',
                tooltip=['Item', 'Impact_kgCO2', 'Incertitude', 'Détail']
            ).interactive()
            st.altair_chart(scatter, use_container_width=True)

        # GRAPHE 5 : POPULATION (Ton code original)
        with t_pop:
            df_hum = df[df['Catégorie'].str.contains("Mobilité|Logistique", na=False)]
            if not df_hum.empty:
                chart_pop = alt.Chart(df_hum).mark_bar().encode(
                    x='Impact_kgCO2',
                    y=alt.Y('Item', sort='-x'),
                    color='Catégorie',
                    tooltip=['Détail', 'Impact_kgCO2']
                )
                st.altair_chart(chart_pop, use_container_width=True)
            else:
                st.info("Pas assez de données de mobilité pour ce graphique.")

        # --- ZONE 3 : EXPORT & RAPPORT (Ta section originale avec xlsxwriter) ---
        st.divider()
        st.subheader("📄 Export & Reporting")
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.info("💡 **Pour générer un PDF :** Utilisez la fonction 'Imprimer' de votre navigateur (Ctrl+P) et choisissez 'Enregistrer au format PDF'.")
            
        with col_ex2:
            buffer_analyse = io.BytesIO()
            with pd.ExcelWriter(buffer_analyse, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Données Calculées')
                
            st.download_button(
                label="📥 Télécharger Données (.xlsx)",
                data=buffer_analyse,
                file_name=f"Donnees_Analyse_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
        with st.expander("Voir le Tableau de Synthèse Complet", expanded=False):
            st.dataframe(df, use_container_width=True)
# ==============================================================================
# PAGE 4 : SIMULER (VERSION ROBUSTE V4)
# ==============================================================================
elif "4." in nav:
    import altair as alt 
    
    st.title("🚀 Simulateur de Transition & Plan d'Action")
    st.markdown("Pilotez la décarbonation : Démographie, Distanciel et Leviers techniques.")

    if not st.session_state.db_entries:
        st.warning("⚠️ Aucune donnée de référence. Veuillez saisir des flux à l'étape 2.")
    else:
        # --- 1. CALCUL DE LA BASELINE (SITUATION 2026) ---
        df_base = pd.DataFrame(st.session_state.db_entries)
        df_base["Impact_kgCO2"] = pd.to_numeric(df_base["Impact_kgCO2"], errors='coerce').fillna(0)
        
        # --- CORRECTION DES LIAISONS (Recherche élargie) ---
        # On s'assure de tout attraper, même si c'est écrit "Radiateur" ou "Fuel"
        
        # 1. MOBILITÉ
        # On cherche dans Catégorie OU Item
        mask_mob = df_base.apply(lambda x: any(k in str(x['Catégorie']).lower() for k in ['mobilit', 'logisti', 'transport', 'déplacement']) or any(k in str(x['Item']).lower() for k in ['voiture', 'train', 'avion', 'tgv', 'bus']), axis=1)
        ref_mob = df_base[mask_mob]['Impact_kgCO2'].sum()

        # 2. BÂTIMENT & ÉNERGIE
        # On sépare l'Élec du Chauffage pour appliquer les bons leviers
        df_bat = df_base[df_base.apply(lambda x: any(k in str(x['Catégorie']).lower() for k in ['bâtiment', 'batiment', 'énergie', 'energie']), axis=1)]
        
        ref_ener_elec = 0.0
        ref_ener_heat = 0.0
        
        for i, row in df_bat.iterrows():
            txt = (str(row['Item']) + " " + str(row['Détail'])).lower()
            # Si ça parle de Watt, KWh, Elec, Ampoule -> C'est de l'élec
            if any(k in txt for k in ['elec', 'élec', 'watt', 'kwh', 'led', 'ampoule', 'ordinateur', 'ecran']):
                ref_ener_elec += row['Impact_kgCO2']
            else:
                # Tout le reste du bâtiment est considéré comme du chauffage (Gaz, Fioul, Radiateur, Eau chaude...)
                ref_ener_heat += row['Impact_kgCO2']

        # 3. IT & RESSOURCES
        mask_it = df_base['Catégorie'].str.contains("Numérique|IT|Informatique|Digital", case=False, na=False)
        ref_it = df_base[mask_it]['Impact_kgCO2'].sum()
        
        mask_food = df_base.apply(lambda x: any(k in str(x['Item']).lower() for k in ['repas', 'café', 'boisson', 'snack', 'restau']), axis=1)
        ref_food = df_base[mask_food]['Impact_kgCO2'].sum()
        
        mask_waste = df_base['Catégorie'].str.contains("Déchet|Achat|Fourniture", case=False, na=False)
        ref_waste = df_base[mask_waste]['Impact_kgCO2'].sum()
        
        total_ref = df_base["Impact_kgCO2"].sum()

        # --- 2. TABLEAU DE BORD DES LEVIERS ---
        with st.container(border=True):
            st.subheader("🎛️ Cockpit de Pilotage")
            
            # Organisation en onglets
            t_strat, t_mob, t_bat, t_res = st.tabs(["👥 Stratégie & Pop.", "🚗 Mobilité", "⚡ Bâtiment", "💻 IT & Achats"])
            
            # ONGLET 1 : STRATÉGIE
            with t_strat:
                c1, c2 = st.columns(2)
                sim_pop_growth = c1.slider("📈 Évolution Effectifs", -20, 50, 0, format="%+d%%", help="Impact structurel de la croissance de l'école.")
                sim_remote_days = c2.slider("💻 Jours en Distanciel / sem", 0, 5, 0, format="%d j", help="Agit massivement sur les trajets domicile-travail.")
                st.caption(f"Note : Le distanciel réduit les trajets quotidiens de {sim_remote_days*20}% mécaniquement.")

            # ONGLET 2 : MOBILITÉ (J'ai remis ton slider de Sobriété !)
            with t_mob:
                c1, c2 = st.columns(2)
                sim_mob_reduce = c1.slider("📉 Sobriété Km (Réduction Volontaire)", 0, 50, 0, format="-%d%%", help="Ex: Moins de voyages, optimisation des tournées.")
                sim_mob_train = c2.checkbox("🚆 Report Modal (Interdiction Avion)", help="Bascule les trajets avion vers le train.")
                sim_mob_carpool = c1.slider("🚙 Taux Covoiturage", 1.0, 4.0, 1.0, step=0.1, help="Nb pers. / voiture.")
                sim_mob_soft = c2.checkbox("🚲 Plan Vélo (Trajets courts)", help="Report de 15% des trajets voiture vers vélo.")

            # ONGLET 3 : BÂTIMENT
            with t_bat:
                c1, c2 = st.columns(2)
                sim_elec_green = c1.checkbox("⚡ Contrat Électricité Verte", help="Passe le facteur d'émission élec proche de 0.")
                sim_solar = c1.slider("☀️ Panneaux Solaires (Autoconsommation)", 0, 50, 0, format="%d%% besoin")
                sim_heat = c2.slider("🔥 Isolation & Sobriété (19°C)", 0, 50, 0, format="-%d%%", help="Agit sur le Chauffage/Radiateurs.")
                sim_led = c2.checkbox("💡 Relamping LED Total", help="-50% sur l'éclairage.")

            # ONGLET 4 : IT & RESSOURCES
            with t_res:
                c1, c2 = st.columns(2)
                sim_it_life = c1.slider("⏳ Durée de vie IT (+ années)", 0, 5, 0, help="Garder les PC plus longtemps.")
                sim_it_refurb = c1.slider("♻️ Part d'achat Reconditionné", 0, 100, 0, format="%d%%")
                sim_food_vege = c2.slider("🥗 Menus Végétariens", 0, 100, 0, format="%d%% repas")
                sim_waste = c2.slider("🗑️ Réduction Déchets", 0, 50, 0, format="-%d%%")

        # --- 3. MOTEUR DE CALCUL ---
        
        # A. FACTEUR DÉMOGRAPHIQUE
        coeff_pop = 1 + (sim_pop_growth / 100.0)
        
        # B. CALCUL MOBILITÉ
        # 1. Effet Pop
        mob_v1 = ref_mob * coeff_pop 
        # 2. Effet Distanciel (1j = 20% de moins)
        ratio_pres = (5 - sim_remote_days) / 5.0
        mob_v2 = mob_v1 * ratio_pres
        # 3. Effet Sobriété Km (Le levier que tu voulais garder)
        mob_v3 = mob_v2 * (1 - sim_mob_reduce/100.0)
        
        # 4. Report Train (sur part avion estimée)
        part_avion = mob_v3 * 0.30 
        gain_train = (part_avion * 0.90) if sim_mob_train else 0
        mob_v4 = mob_v3 - gain_train
        
        # 5. Covoit & Vélo
        mob_v5 = mob_v4 / sim_mob_carpool
        gain_velo = mob_v5 * 0.15 if sim_mob_soft else 0
        
        final_mob = mob_v5 - gain_velo
        gain_total_mob = (ref_mob * coeff_pop) - final_mob

        # C. CALCUL ÉNERGIE
        ener_elec_v1 = ref_ener_elec * coeff_pop
        ener_heat_v1 = ref_ener_heat * coeff_pop
        
        # Chauffage (Isolation) -> Agit sur Gaz, Fioul ET Radiateurs
        final_heat = ener_heat_v1 * (1 - sim_heat/100.0)
        
        # Élec
        elec_v2 = ener_elec_v1 * 0.90 if sim_led else ener_elec_v1
        elec_v3 = elec_v2 * (1 - sim_solar/100.0)
        final_elec = elec_v3 * 0.10 if sim_elec_green else elec_v3
        
        gain_total_ener = (ener_elec_v1 + ener_heat_v1) - (final_heat + final_elec)

        # D. CALCUL RESSOURCES
        it_v1 = ref_it * coeff_pop
        food_v1 = ref_food * coeff_pop
        waste_v1 = ref_waste * coeff_pop
        
        it_v2 = it_v1 / (1 + (sim_it_life / 4.0))
        ratio_recond = (1 - sim_it_refurb/100) * 1.0 + (sim_it_refurb/100) * 0.2
        final_it = it_v2 * ratio_recond
        
        final_food = food_v1 * (1 - sim_food_vege/100) + (food_v1 * sim_food_vege/100 * 0.15)
        final_waste = waste_v1 * (1 - sim_waste/100.0)
        
        gain_total_res = (it_v1 + food_v1 + waste_v1) - (final_it + final_food + final_waste)

        # E. SYNTHÈSE
        total_ref_projete = total_ref * coeff_pop
        total_final = final_mob + final_heat + final_elec + final_it + final_food + final_waste
        
        # --- 4. VISUALISATION ---
        st.divider()
        st.subheader("📉 Trajectoire & Résultats 2030")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Référence 2026", f"{total_ref/1000:.1f} T")
        
        delta_pop = total_ref_projete - total_ref
        k2.metric("Impact Démographique", f"{delta_pop/1000:+.1f} T", "Inertiel", delta_color="off")
        
        total_economy = total_ref_projete - total_final
        k3.metric("Gains Actions", f"-{total_economy/1000:.1f} T", delta="Économie", delta_color="inverse")
        
        pop_projete = (st.session_state.params['pop_etu'] + st.session_state.params['pop_alt'] + st.session_state.params['pop_prof']) * coeff_pop
        if pop_projete == 0: pop_projete = 1
        ratio_final = (total_final / 1000) / pop_projete
        cible = st.session_state.params['budget_co2']
        
        k4.metric("Atterrissage / Pers.", f"{ratio_final:.2f} T", f"Cible: {cible} ({'✅' if ratio_final <= cible else '⚠️'})", delta_color="inverse")
        
        # GRAPHIQUES
        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.markdown("**🌊 Cascade des Gains (Waterfall)**")
            wf_data = [
                {"Etape": "1. Base 2026", "Val": total_ref/1000, "Type": "Base", "Order": 1},
                {"Etape": "2. Effet Pop.", "Val": delta_pop/1000, "Type": "Hausse", "Order": 2},
                {"Etape": "3. Gain Mobilité", "Val": -gain_total_mob/1000, "Type": "Baisse", "Order": 3},
                {"Etape": "4. Gain Énergie", "Val": -gain_total_ener/1000, "Type": "Baisse", "Order": 4},
                {"Etape": "5. Gain Ressources", "Val": -gain_total_res/1000, "Type": "Baisse", "Order": 5},
                {"Etape": "6. Arrivée 2030", "Val": total_final/1000, "Type": "Final", "Order": 6}
            ]
            df_wf = pd.DataFrame(wf_data)
            
            df_wf["prev"] = df_wf["Val"].cumsum().shift(1).fillna(0)
            df_wf["start"] = df_wf["prev"]
            df_wf["end"] = df_wf["prev"] + df_wf["Val"]
            df_wf.loc[df_wf["Type"] == "Base", "start"] = 0
            df_wf.loc[df_wf["Type"] == "Base", "end"] = df_wf["Val"]
            df_wf.loc[df_wf["Type"] == "Final", "start"] = 0
            df_wf.loc[df_wf["Type"] == "Final", "end"] = df_wf["Val"]
            
            chart_wf = alt.Chart(df_wf).mark_bar().encode(
                x=alt.X("Etape", sort=alt.SortField("Order"), axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("start", title="Tonnes CO2e"),
                y2="end",
                color=alt.Color("Type", scale=alt.Scale(domain=["Base", "Hausse", "Baisse", "Final"], range=["#95a5a6", "#e74c3c", "#27ae60", "#2c3e50"])),
                tooltip=["Etape", alt.Tooltip("Val", format=".1f", title="Volume")]
            ).properties(height=350)
            st.altair_chart(chart_wf, use_container_width=True)

        with g2:
            st.markdown("**💰 Contribution des Gains**")
            gains_data = pd.DataFrame([
                {"Source": "Mobilité", "Gain": gain_total_mob},
                {"Source": "Énergie", "Gain": gain_total_ener},
                {"Source": "Ressources", "Gain": gain_total_res}
            ])
            gains_data = gains_data[gains_data["Gain"] > 0.001] # Filtre les zéros
            
            if not gains_data.empty:
                chart_donut = alt.Chart(gains_data).mark_arc(innerRadius=40).encode(
                    theta="Gain",
                    color=alt.Color("Source", scale=alt.Scale(scheme='set2')),
                    tooltip=["Source", alt.Tooltip("Gain", format=".1f")]
                )
                st.altair_chart(chart_donut, use_container_width=True)
            else:
                st.caption("Activez des leviers pour voir la répartition des gains.")
# ==============================================================================
# PAGE 5 : RAPPORT & EXPORT (OFFICIAL REPORTING)
# ==============================================================================
elif "5." in nav:
    st.title("📄 Édition du Rapport Officiel")
    
    # --- CSS SPÉCIAL IMPRESSION ---
    st.markdown("""
        <style>
            @media print {
                [data-testid="stSidebar"] {display: none;}
                .stButton {display: none;}
                .stDeployButton {display: none;}
                header {display: none;}
                #MainMenu {display: none;}
                .block-container {padding-top: 0 !important;}
            }
            .report-box {border: 2px solid #2c3e50; padding: 20px; border-radius: 10px; margin-bottom: 20px;}
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.db_entries:
        st.warning("⚠️ Aucune donnée à rapporter.")
    else:
        # PRÉPARATION DES DONNÉES
        df = pd.DataFrame(st.session_state.db_entries)
        
        # Nettoyage
        df["Impact_kgCO2"] = pd.to_numeric(df["Impact_kgCO2"], errors='coerce').fillna(0)
        df["Marge"] = pd.to_numeric(df["Marge"], errors='coerce').fillna(0)
        
        # Fonction Scope
        def detect_scope(row):
            detail = str(row.get("Détail", ""))
            if "Scope 1" in detail: return "Scope 1"
            if "Scope 2" in detail: return "Scope 2"
            if "Scope 3" in detail: return "Scope 3"
            cat = str(row.get("Catégorie", ""))
            item = str(row.get("Item", ""))
            if "Bâtiment" in cat or "Énergie" in cat:
                if "Gaz" in item or "Fioul" in item: return "Scope 1"
                if "Élec" in item or "Chauffage" in item: return "Scope 2"
            return "Scope 3"

        df["Scope"] = df.apply(detect_scope, axis=1)
        
        tot_co2 = df["Impact_kgCO2"].sum() / 1000
        tot_marge = df["Marge"].sum() / 1000
        pop = st.session_state.params['pop_etu'] + st.session_state.params['pop_alt'] + st.session_state.params['pop_prof']
        if pop == 0: pop = 1
        ratio = (tot_co2 * 1000) / pop
        
        # --- CONFIGURATION ---
        # --- CONFIGURATION DU RAPPORT (AVEC ASSISTANT IA) ---
        with st.expander("🛠️ Configuration & Assistant de Rédaction", expanded=True):
            c1, c2 = st.columns(2)
            auteur = c1.text_input("Auteur du rapport", "Département Supply Chain & RSE")
            version = c2.text_input("Version", f"V1.0 - {datetime.date.today()}")
            
            # --- LE CERVEAU DE L'ASSISTANT (Logique Expert) ---
            def generer_analyse_auto():
                analyse = []
                # 1. Analyse Globale
                analyse.append(f"Le bilan carbone global s'élève à {tot_co2:.1f} Tonnes CO2e.")
                
                # 2. Analyse de l'Objectif
                delta = ratio - st.session_state.params['budget_co2']
                if delta <= 0:
                    analyse.append(f"✅ EXCELLENT : Avec {ratio:.1f} T/pers, l'objectif ({st.session_state.params['budget_co2']} T) est atteint.")
                else:
                    analyse.append(f"⚠️ ATTENTION : Le ratio de {ratio:.1f} T/pers dépasse la cible de +{delta:.1f} T.")

                # 3. Identification du Hotspot (Le plus gros pollueur)
                top_item = df.groupby("Catégorie")["Impact_kgCO2"].sum().idxmax()
                top_val = df.groupby("Catégorie")["Impact_kgCO2"].sum().max() / 1000
                part = (top_val / tot_co2) * 100
                analyse.append(f"Le poste critique est '{top_item}' qui représente {part:.0f}% des émissions ({top_val:.1f} T).")

                # 4. Analyse Qualité Donnée
                if tot_marge / tot_co2 < 0.10:
                    analyse.append("La qualité des données est jugée fiable (incertitude < 10%).")
                else:
                    analyse.append("Des efforts de collecte sont nécessaires pour réduire l'incertitude actuelle.")
                
                # 5. Conclusion
                analyse.append("RECOMMANDATION : Prioriser les actions de réduction sur le premier poste d'émission identifié ci-dessus.")
                
                return " ".join(analyse)

            # Bouton Magique
            if st.button("✨ Générer l'analyse par l'IA (Auto-Writing)"):
                st.session_state['auto_comment'] = generer_analyse_auto()
            
            # Zone de texte (qui prend le texte généré ou reste vide)
            valeur_texte = st.session_state.get('auto_comment', "Cliquez sur le bouton magique ci-dessus pour générer l'analyse...")
            commentaires = st.text_area("💬 Analyse & Commentaires", value=valeur_texte, height=150)

        # --- DOCUMENT VISUEL ---
        st.markdown(f"""
        <div class="report-box">
            <h1 style="text-align: center; color: #2c3e50;">BILAN CARBONE & FLUX</h1>
            <h3 style="text-align: center; color: #7f8c8d;">{st.session_state.params['entity_name']}</h3>
            <hr>
            <p><b>Date :</b> {datetime.date.today()} | <b>Auteur :</b> {auteur} | <b>Ref :</b> {version}</p>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("1. Synthèse Executive")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empreinte Totale", f"{tot_co2:.2f} T CO2e", f"± {tot_marge:.2f} T")
        k2.metric("Intensité Carbone", f"{ratio:.0f} kg/pers", f"Cible: {st.session_state.params['budget_co2']*1000:.0f} kg")
        k3.metric("Coût Carbone", f"{tot_co2 * st.session_state.params['shadow_price']:,.0f} €", "Valorisation risque")

        st.subheader("2. Analyse & Conclusions")
        st.info(f"📝 **Note de l'expert :**\n\n{commentaires}")

        st.subheader("3. Détail des Émissions par Scope (ISO 14064)")
        if "Scope" in df.columns:
            df_scope = df.groupby("Scope")["Impact_kgCO2"].sum().reset_index()
            df_scope["Tonnes CO2e"] = df_scope["Impact_kgCO2"] / 1000
            df_scope["Part (%)"] = (df_scope["Impact_kgCO2"] / df["Impact_kgCO2"].sum()) * 100
            st.table(df_scope[["Scope", "Tonnes CO2e", "Part (%)"]].style.format({"Tonnes CO2e": "{:.2f}", "Part (%)": "{:.1f}%"}))

        st.subheader("4. Top 5 des Postes d'Émission (Pareto)")
        df_top = df.groupby(["Catégorie", "Item"])["Impact_kgCO2"].sum().reset_index().sort_values("Impact_kgCO2", ascending=False).head(5)
        df_top["Tonnes"] = df_top["Impact_kgCO2"] / 1000
        st.table(df_top[["Catégorie", "Item", "Tonnes"]].style.format({"Tonnes": "{:.2f}"}))

        st.markdown("<br><br><br>", unsafe_allow_html=True)
        c_sig1, c_sig2 = st.columns(2)
        c_sig1.markdown("**Visa Responsable RSE :**\n\n__________________")
        c_sig2.markdown("**Visa Direction :**\n\n__________________")

        st.divider()
        
        # --- BOUTONS D'ACTION (NOUVEAU : EXPORT EXCEL) ---
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.success("🖨️ **Pour imprimer :** Faites `Ctrl + P` et choisissez 'Enregistrer au format PDF'.")
        
        with col_btn2:
            # 1. Création du buffer mémoire
            buffer = io.BytesIO()
            
            # 2. Écriture du fichier Excel dans le buffer
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Onglet 1 : Données Brutes
                df.to_excel(writer, index=False, sheet_name='Données Brutes')
                
                # Onglet 2 : Synthèse par Scope (Petit bonus !)
                if "Scope" in df.columns:
                    df_scope.to_excel(writer, index=False, sheet_name='Synthèse Scope')
                
            # 3. Préparation du téléchargement
            st.download_button(
                label="📥 Télécharger le Rapport Excel (.xlsx)",
                data=buffer,
                file_name=f"Bilan_Carbone_{st.session_state.params['entity_name']}.xlsx",
                mime="application/vnd.ms-excel"
            )