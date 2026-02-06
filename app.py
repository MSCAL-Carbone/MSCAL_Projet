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

# --- SÉCURITÉ : MOT DE PASSE ---
def check_password():
    """Retourne True si l'utilisateur a le bon mot de passe."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True  # Déjà connecté

    st.markdown("### 🔒 Accès Sécurisé MSCAL ERP")
    pwd = st.text_input("Veuillez entrer le mot de passe administrateur :", type="password")
    
    if st.button("Se connecter"):
        if pwd == "MSCAL2026":  # <--- Le MOT DE PASSE EST ICI 
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Mot de passe incorrect")
            
    return False

if not check_password():
    st.stop()  # ARRÊTE TOUT SI PAS CONNECTÉ



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
    # --- ZONE DE SAUVEGARDE/CHARGEMENT (NOUVEAU V2) ---
    st.sidebar.markdown("### 💾 Mémoire Session")
    col_save, col_load = st.sidebar.columns(2)
    
    # Bouton SAUVEGARDER
    with col_save:
        # On compacte tout (paramètres + données) dans un paquet
        session_data = {
            'params': st.session_state.params,
            'db': st.session_state.db_entries
        }
        session_json = json.dumps(session_data)
        st.download_button("Bkp ⬇️", session_json, f"mscal_backup_{datetime.date.today()}.json", "application/json", help="Sauvegarder mon travail sur mon ordi")

    # Bouton CHARGER
    with col_load:
        # Petit hack pour charger discrètement
        uploaded_json = st.file_uploader("Ouvrir ⬆️", type=["json"], label_visibility="collapsed")
        if uploaded_json is not None:
            try:
                data = json.load(uploaded_json)
                # On remet les données en place
                if 'params' in data: st.session_state.params = data['params']
                if 'db' in data: st.session_state.db_entries = data['db']
                st.success("Chargé !")
                st.rerun()
            except:
                st.error("Erreur fichier")
    
    st.sidebar.divider()
    # ----------------------------------------------------
    st.markdown("### 🧭 Menu de Navigation")
    
    nav = st.radio("Séquence de travail", [
        "0. 📘 GUIDE & DÉFINITIONS",
        "1. ⚙️ DÉFINIR & PARAMÉTRER", 
        "2. 📝 MESURER (Saisie Flux)", 
        "3. 📊 ANALYSER (Cockpit & KPIs)",
        "4. 🚀 AMÉLIORER (Simulateur)",
        "5. 📄 CONTRÔLER (Rapport Final)"
    ])
    
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
# PAGE 3 : ANALYSER (TABLEAU DE BORD DÉCISIONNEL)
# ==============================================================================
elif "3." in nav:
    import altair as alt # Nécessaire pour les graphes interactifs
    
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
        
        # --- MOTEUR DE CALCUL DES KPIs ---
        # A. Totaux
        total_co2_t = df["Impact_kgCO2"].sum() / 1000.0
        total_marge_t = df["Marge"].sum() / 1000.0
        
        # B. Population & Ratios
        pop_totale = st.session_state.params['pop_etu'] + st.session_state.params['pop_alt'] + st.session_state.params['pop_prof']
        if pop_totale == 0: pop_totale = 1 # Anti-division par zéro
        
        ratio_pers = total_co2_t / pop_totale
        budget_cible = float(st.session_state.params['budget_co2'])
        
        # C. Financier
        cout_carbone = total_co2_t * st.session_state.params['shadow_price']
        
        # D. Qualité de Donnée (DQI)
        # On calcule une note sur 10 basée sur l'incertitude moyenne pondérée par l'impact
        if total_co2_t > 0:
            dqi_score = 10 - (df["Marge"].sum() / df["Impact_kgCO2"].sum() * 20) # Formule arbitraire expert
        else:
            dqi_score = 0
        dqi_score = max(0, min(10, dqi_score)) # Borner entre 0 et 10

        # --- ZONE 1 : CONTROL TOWER (8 KPIs) ---
        st.markdown("### 🎛️ Control Tower")
        
        # LIGNE 1 : PERFORMANCE ABSOLUE
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(
            "Empreinte Totale (Net)", 
            f"{total_co2_t:.2f} T CO2e", 
            delta=f"± {total_marge_t:.2f} T (Incertitude)",
            delta_color="off"
        )
        
        # Jauge comparative (Target vs Réel)
        delta_obj = budget_cible - ratio_pers
        k2.metric(
            "Ratio / Personne", 
            f"{ratio_pers:.2f} T/pers", 
            f"{delta_obj:+.2f} T vs Objectif {budget_cible}T",
            delta_color="normal" # Vert si on est en dessous, Rouge si au dessus
        )
        
        k3.metric("Coût Fantôme (Risque)", f"{cout_carbone:,.0f} €", f"Prix: {st.session_state.params['shadow_price']}€/T")
        
        # Intensité temporelle
        intensite_jour = (total_co2_t * 1000) / st.session_state.params['jours_ouverture']
        k4.metric("Intensité Quotidienne", f"{intensite_jour:.0f} kgCO2e/j", "Jours ouvrés")

        # LIGNE 2 : PERFORMANCE SUPPLY CHAIN
        k5, k6, k7, k8 = st.columns(4)
        
        # Part du Scope 3 (Calcul approximatif basé sur les catégories)
        scope3_items = df[df['Catégorie'].isin(['Mobilité', 'Achats', 'Numérique', 'Logistique Humaine'])]['Impact_kgCO2'].sum() / 1000
        part_scope3 = (scope3_items / total_co2_t) * 100 if total_co2_t > 0 else 0
        
        k5.metric("Part du Scope 3", f"{part_scope3:.1f} %", "Dépendance Extérieure")
        
        # Data Quality Index
        dqi_color = "normal" if dqi_score > 7 else "inverse"
        k6.metric("Indice Qualité Donnée (DQI)", f"{dqi_score:.1f} / 10", "Fiabilité", delta_color=dqi_color)
        
        k7.metric("Nombre de Flux", len(df), "Lignes saisies")
        
        # Ratio Surfacique (si bâtiment saisi)
        bat_impact = df[df['Catégorie'] == 'Bâtiment']['Impact_kgCO2'].sum()
        k8.metric("Impact Bâtiment Seul", f"{bat_impact/1000:.1f} T", "Scope 1 & 2")

        st.divider()

        # --- ZONE 2 : VISUALISATION AVANCÉE (INTERACTIVE) ---
        st.markdown("### 🔭 Analyse Visuelle & Stratégique")
        
        t_rep, t_pareto, t_matrix, t_pop = st.tabs(["🍩 Répartition", "📉 Pareto (80/20)", "🎯 Matrice Priorité", "👥 Par Population"])
        
        # GRAPHE 1 : DONUT INTERACTIF
        with t_rep:
            c1, c2 = st.columns([2, 1])
            with c1:
                # Agrégation
                df_cat = df.groupby("Catégorie")["Impact_kgCO2"].sum().reset_index()
                
                # Chart Altair
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

        # GRAPHE 2 : PARETO (L'outil de l'ingénieur)
        with t_pareto:
            st.caption("Le diagramme de Pareto permet d'identifier les 'Vital Few' : les 20% d'actions qui génèrent 80% de l'impact.")
            
            # Préparation Pareto
            df_pareto = df.groupby("Item")["Impact_kgCO2"].sum().reset_index().sort_values("Impact_kgCO2", ascending=False)
            df_pareto["Cumul"] = df_pareto["Impact_kgCO2"].cumsum()
            df_pareto["Cumul_Pct"] = df_pareto["Cumul"] / df_pareto["Impact_kgCO2"].sum()
            
            # Base Chart
            base = alt.Chart(df_pareto.head(10)).encode(x=alt.X('Item', sort=None))

            # Barres
            bars = base.mark_bar().encode(
                y='Impact_kgCO2',
                tooltip=['Item', 'Impact_kgCO2']
            )

            # Ligne Cumul
            line = base.mark_line(color='red').encode(
                y='Cumul_Pct',
                tooltip=[alt.Tooltip('Cumul_Pct', format='.0%')]
            )

            st.altair_chart((bars + line).resolve_scale(y='independent'), use_container_width=True)

        # GRAPHE 3 : MATRICE DE PRIORITÉ (SCATTER PLOT)
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

        # GRAPHE 4 : ANALYSE POPULATION
        with t_pop:
            # On filtre uniquement ce qui concerne les humains
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

        # --- ZONE 3 : EXPORT & RAPPORT ---
        st.divider()
        st.subheader("📄 Export & Reporting")
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.info("💡 **Pour générer un PDF :** Utilisez la fonction 'Imprimer' de votre navigateur (Ctrl+P) et choisissez 'Enregistrer au format PDF'.")
            
        with col_ex2:
            # Export Excel pour l'Analyse
            buffer_analyse = io.BytesIO()
            with pd.ExcelWriter(buffer_analyse, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Données Calculées')
                
            st.download_button(
                label="📥 Télécharger Données (.xlsx)",
                data=buffer_analyse,
                file_name=f"Donnees_Analyse_{datetime.date.today()}.xlsx",
                mime="application/vnd.ms-excel"
            )
            
        # Tableau Récapitulatif Final pour le Rapport
        with st.expander("Voir le Tableau de Synthèse Complet", expanded=False):
            st.dataframe(df, use_container_width=True)
# ==============================================================================
# PAGE 4 : AMÉLIORER (SIMULATEUR AVANCÉ)
# ==============================================================================
elif "4." in nav:
    import altair as alt # Import local pour garantir le fonctionnement
    
    st.title("🚀 Simulateur de Transition & Plan d'Action")
    st.markdown("Pilotez la décarbonation via 10 leviers stratégiques. Visualisez l'atterrissage 2030.")

    if not st.session_state.db_entries:
        st.warning("⚠️ Aucune donnée de référence. Veuillez saisir des flux à l'étape 2.")
    else:
        # --- 1. CALCUL DE LA BASELINE (SITUATION INITIALE) ---
        df_base = pd.DataFrame(st.session_state.db_entries)
        df_base["Impact_kgCO2"] = pd.to_numeric(df_base["Impact_kgCO2"], errors='coerce').fillna(0)
        
        # Segmentation fine pour les calculs
        ref_mob = df_base[df_base['Catégorie'].str.contains("Mobilité|Logistique", na=False)]['Impact_kgCO2'].sum()
        ref_ener_elec = df_base[df_base['Item'].str.contains("Élec", case=False, na=False)]['Impact_kgCO2'].sum()
        ref_ener_heat = df_base[df_base['Item'].str.contains("Gaz|Chauffage", case=False, na=False)]['Impact_kgCO2'].sum()
        ref_it = df_base[df_base['Catégorie'].str.contains("Numérique", na=False)]['Impact_kgCO2'].sum()
        ref_food = df_base[df_base['Item'].str.contains("Repas|Café", case=False, na=False)]['Impact_kgCO2'].sum()
        ref_waste = df_base[df_base['Catégorie'].str.contains("Déchets|Achats", na=False)]['Impact_kgCO2'].sum()
        
        total_ref = df_base["Impact_kgCO2"].sum()
        
        # --- 2. TABLEAU DE BORD DES LEVIERS (10 ACTIONS) ---
        with st.container(border=True):
            st.subheader("🎛️ Cockpit des Leviers d'Action")
            
            t1, t2, t3 = st.tabs(["🚗 Mobilité", "⚡ Bâtiment & Énergie", "💻 IT & Ressources"])
            
            # LEVIERS MOBILITÉ
            with t1:
                c1, c2 = st.columns(2)
                sim_mob_reduce = c1.slider("📉 Sobriété (Moins de km)", 0, 50, 10, format="-%d%%", help="Télétravail, cours à distance, optimisation tournées.")
                sim_mob_train = c2.checkbox("🚆 Report Modal (Avion ➔ Train)", help="Bascule les trajets avion vers le train (-90% CO2).")
                sim_mob_carpool = c1.slider("🚙 Taux Covoiturage", 1.0, 3.0, 1.0, step=0.1, help="Passer de 1 pers/voiture à 2 pers/voiture divise l'impact par 2.")
                sim_mob_soft = c2.checkbox("🚲 Plan Vélo / Douce", help="Report de 10% des trajets courts voiture vers vélo.")

            # LEVIERS ÉNERGIE
            with t2:
                c1, c2 = st.columns(2)
                sim_elec_green = c1.checkbox("⚡ Contrat Électricité Verte", help="Fournisseur garanti origine renouvelable.")
                sim_solar = c1.slider("☀️ Panneaux Solaires (Autoconsommation)", 0, 50, 0, format="%d%% besoin", help="Produire sa propre électricité.")
                sim_heat = c2.slider("🔥 Isolation & Sobriété Chauffage", 0, 40, 5, format="-%d%%", help="Isolation, 19°C max (-7% par degré en moins).")
                sim_led = c2.checkbox("💡 Relamping LED (100%)", help="Réduit la part éclairage de 50%.")

            # LEVIERS IT & RESSOURCES
            with t3:
                c1, c2 = st.columns(2)
                sim_it_life = c1.slider("⏳ Allongement Vie IT (+ années)", 0, 4, 0, help="Garder les PC 6 ou 8 ans au lieu de 4.")
                sim_it_refurb = c1.slider("♻️ Part Achat Reconditionné", 0, 100, 0, format="%d%%", help="Le reconditionné émet 80% moins de CO2 à l'achat.")
                sim_food_vege = c2.slider("🥗 Menus Végétariens", 0, 100, 10, format="%d%% des repas", help="Impact divisé par 10 vs Bœuf.")
                sim_waste = c2.slider("🗑️ Réduction Déchets", 0, 50, 0, format="-%d%%", help="Vrac, zéro plastique, recyclage.")

        # --- 3. MOTEUR DE CALCUL (SCÉNARIOS) ---
        
        # MOBILITÉ
        # 1. On réduit le volume (Sobriété)
        mob_step1 = ref_mob * (1 - sim_mob_reduce/100)
        # 2. Report Modal (On cible une part arbitraire de 30% avion transformée en train)
        gain_train = (mob_step1 * 0.30) * 0.90 if sim_mob_train else 0
        mob_step2 = mob_step1 - gain_train
        # 3. Covoit (On divise l'impact routier restant par le taux d'occupation)
        mob_step3 = mob_step2 / sim_mob_carpool
        # 4. Vélo (Gain 5% global)
        gain_velo = mob_step3 * 0.05 if sim_mob_soft else 0
        
        final_mob = mob_step3 - gain_velo
        gain_total_mob = ref_mob - final_mob

        # ÉNERGIE
        # 1. Chauffage
        final_heat = ref_ener_heat * (1 - sim_heat/100)
        # 2. Élec (LED réduit conso, Solaire réduit grid, Vert réduit facteur)
        elec_step1 = ref_ener_elec * 0.90 if sim_led else ref_ener_elec # Gain LED
        elec_step2 = elec_step1 * (1 - sim_solar/100) # Gain Solaire (moins de kWh réseau)
        final_elec = elec_step2 * 0.10 if sim_elec_green else elec_step2 # Facteur devient quasi nul si vert
        
        gain_total_ener = (ref_ener_elec + ref_ener_heat) - (final_heat + final_elec)

        # IT & ACHATS
        # 1. IT Vie (Ratio: 4ans / (4+Extension))
        it_step1 = ref_it * (4 / (4 + sim_it_life))
        # 2. IT Reconditionné (La part reconditionnée a un impact réduit de 80%)
        # Formule : Part_Neuf * 1 + Part_Recond * 0.2
        ratio_mix_it = (1 - sim_it_refurb/100) * 1 + (sim_it_refurb/100) * 0.2
        final_it = it_step1 * ratio_mix_it
        
        # 3. Food
        # Part Bœuf remplacée par Végé (facteur ~0.15 du bœuf)
        final_food = ref_food * (1 - sim_food_vege/100) + (ref_food * sim_food_vege/100 * 0.15)
        
        # 4. Déchets
        final_waste = ref_waste * (1 - sim_waste/100)
        
        gain_total_ressources = (ref_it + ref_food + ref_waste) - (final_it + final_food + final_waste)

        # TOTAL
        total_sim = final_mob + final_heat + final_elec + final_it + final_food + final_waste
        total_gain = total_ref - total_sim

        # --- 4. VISUALISATION DES RÉSULTATS ---
        st.divider()
        st.markdown("### 🔮 Trajectoire Carbone 2030")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Référence 2026", f"{total_ref/1000:.1f} T")
        k2.metric("Gain Identifié", f"-{total_gain/1000:.1f} T", delta="Économie", delta_color="inverse")
        k3.metric("Atterrissage 2030", f"{total_sim/1000:.1f} T")
        
        # Target Check
        pop = st.session_state.params['pop_etu'] + st.session_state.params['pop_alt'] + st.session_state.params['pop_prof']
        if pop == 0: pop = 1
        ratio_sim = (total_sim / 1000) / pop
        target = float(st.session_state.params['budget_co2'])
        
        icon = "✅" if ratio_sim <= target else "🚧"
        k4.metric("Nouvelle Performance", f"{ratio_sim:.1f} T/pers", f"Cible: {target} {icon}")

        # WATERFALL CHART (Le juge de paix)
        df_waterfall = pd.DataFrame([
            {"Label": "1. Situation Actuelle", "Amount": total_ref/1000, "Type": "Départ"},
            {"Label": "2. Plan Mobilité", "Amount": -gain_total_mob/1000, "Type": "Gain"},
            {"Label": "3. Efficacité Énergétique", "Amount": -gain_total_ener/1000, "Type": "Gain"},
            {"Label": "4. Sobriété Numérique/Achats", "Amount": -gain_total_ressources/1000, "Type": "Gain"},
            {"Label": "5. Objectif 2030", "Amount": total_sim/1000, "Type": "Arrivée"}
        ])

        chart = alt.Chart(df_waterfall).mark_bar().encode(
            x=alt.X('Label', sort=None, title=None),
            y=alt.Y('Amount', title="Tonnes CO2e"),
            color=alt.Color('Type', scale=alt.Scale(domain=['Départ', 'Gain', 'Arrivée'], range=['#95a5a6', '#2ecc71', '#3498db'])),
            tooltip=['Label', 'Amount']
        ).properties(height=400)
        
        st.altair_chart(chart, use_container_width=True)

        # PLAN D'ACTION (Récapitulatif)
        with st.expander("📄 Exporter le Plan d'Action (Tableau)", expanded=True):
            action_plan = pd.DataFrame({
                "Domaine": ["Mobilité", "Mobilité", "Mobilité", "Énergie", "Énergie", "IT", "IT", "Achats"],
                "Levier": ["Réduction Km", "Covoiturage", "Report Train", "Élec Verte", "Isolation", "Durée de vie +", "Reconditionné", "Menu Végé"],
                "Configuration": [f"-{sim_mob_reduce}%", f"x{sim_mob_carpool}", f"{sim_mob_train}", f"{sim_elec_green}", f"-{sim_heat}%", f"+{sim_it_life} ans", f"{sim_it_refurb}%", f"{sim_food_vege}%"],
                "Statut": ["Activé" if x else "En attente" for x in [sim_mob_reduce, sim_mob_carpool>1, sim_mob_train, sim_elec_green, sim_heat, sim_it_life, sim_it_refurb, sim_food_vege]]
            })
            st.dataframe(action_plan, use_container_width=True)
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
        with st.expander("🛠️ Configuration du Rapport (Auteur & Commentaires)", expanded=True):
            c1, c2 = st.columns(2)
            auteur = c1.text_input("Auteur du rapport", "Département Supply Chain & RSE")
            version = c2.text_input("Version du document", f"V1.0 - {datetime.date.today()}")
            
            commentaires = st.text_area("💬 Analyse & Commentaires de l'Ingénieur", 
                                      "Le bilan montre une prédominance du Scope 3 liée à la mobilité. "
                                      "L'incertitude est maîtrisée. "
                                      "Des actions correctives sur l'IT sont recommandées.")

        st.divider()

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