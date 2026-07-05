import streamlit as st
import requests
import time
import pandas as pd
import plotly.graph_objects as go

# Sivun asetukset
st.set_page_config(
    page_title="CODENAME: Strain Isolation",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tyylit
custom_css = """
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Courier New', Courier, monospace !important;
    }
    .sidebar-title {
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #111111;
        margin-bottom: 5px;
    }
    .status-text {
        font-size: 0.85rem;
        color: #444444;
        margin-bottom: 5px;
    }
    .sidebar-section {
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #111111;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    [data-testid="stSidebar"] hr {
        border: 1px solid #FF3333 !important;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .main-title {
        font-weight: bold !important;
        letter-spacing: 2px !important;
        font-size: 2.5rem !important;
        margin-bottom: 25px !important;
        color: #111111 !important;
    }
    .main-title span {
        color: #FF3333 !important;
        display: inline !important;
    }
    .stButton>button {
        background-color: transparent !important;
        color: #FF3333 !important;
        border: 1px solid #FF3333 !important;
        border-radius: 4px !important;
        font-weight: bold !important;
        letter-spacing: 1px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        margin-top: 10px;
    }
    .stButton>button:hover {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
        border-color: #FF0000 !important;
    }
    [data-testid="stNotification"] p {
        color: #222222 !important;
    }
</style>
"""
# Syötetään CSS tyylit Streamlitiin
st.markdown(custom_css, unsafe_allow_html=True)

# Alustetaan tilamuuttujat (Session State) dynaamista seurantaa varten
if "search_status" not in st.session_state:
    st.session_state.search_status = "INACTIVE"
if "repo_count" not in st.session_state:
    st.session_state.repo_count = "0"
if "primary_lang" not in st.session_state:
    st.session_state.primary_lang = "None"
if "warning_message" not in st.session_state:
    st.session_state.warning_message = "⚠️ SYSTEM NOTICE: Awaiting target user ID input."
if "languages_data" not in st.session_state:
    st.session_state.languages_data = None

# Placeholder latauspalkille
progress_placeholder = st.empty()

# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-title">Control Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-text">Access level: Unrestricted</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-text">System status: Ready</div>', unsafe_allow_html=True)

    st.divider()

    # Näytteenotto
    st.markdown('<div class="sidebar-section">Sample Acquisition</div>', unsafe_allow_html=True)

    # Tekstikenttä syötteelle
    username_input = st.text_input("Target User ID", placeholder="Enter GitHub username...")

    # Scan button
    scan_button = st.button("START SCAN")

# Main content
st.markdown(
    '<div class="main-title">🧬 <span>C</span>ODENAME: <span>S</span>TRAIN <span>I</span>SOLATION</div>', 
    unsafe_allow_html=True
)

# Placeholder mittareille
metrics_placeholder = st.empty()

def render_metrics(repos, lang, status):
    with metrics_placeholder.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Repositories Scanned", value=repos)
        with col2:
            st.metric(label="Dominant Strain", value=lang)
        with col3:
            st.metric(label="Analysis Status", value=status)

progress_placeholder = st.empty()
warning_placeholder = st.empty()

st.markdown("---")

# Skannauslogiikka (haetaan GitHub API-rajapinnasta)
if scan_button:
    if not username_input.strip():
        st.session_state.search_status = "INACTIVE"
        st.session_state.repo_count = "0"
        st.session_state.primary_lang = "None"
        st.session_state.languages_data = None
        st.session_state.warning_message = "⚠️ SYSTEM NOTICE: Target user ID is required to initiate scan."
    else:

        # Nollataan mahdolliset aikaisemmat varoitukset
        st.session_state.warning_message = ""
        st.session_state.languages_data = None
        warning_placeholder.empty()

        # Asetetaan tila Pending muotoon
        render_metrics(repos="0", lang="", status="PENDING")

        # Määritellään GitHub token
        headers = {}
        if "GITHUB_TOKEN" in st.secrets:
            headers["Authorization"] = f"token {st.secrets['GITHUB_TOKEN']}"
        
        # Api-kutsu: Haetaan käyttäjätunnuksen julkiset repot
        url = f"https://api.github.com/users/{username_input.strip()}/repos?per_page=100"

        try:
            response = requests.get(url, headers=headers)

            # Tarkistetaan löytyykö käyttäjätunnusta
            if response.status_code == 404:
                st.session_state.search_status = "INACTIVE"
                st.session_state.repo_count = "0"
                st.session_state.primary_lang = "None"
                st.session_state.warning_message = f"⚠️ SYSTEM NOTICE: User '{username_input}' not found in GitHub registry."

            # Jos haku onnistuu
            elif response.status_code == 200:
                repos = response.json()
                target_repos_count = len(repos)

                # Jos käyttäjällä ei ole julkisia repoja
                if target_repos_count == 0:
                    st.session_state.search_status = "COMPLETE"
                    st.session_state.repo_count = "0"
                    st.session_state.primary_lang = "None"
                    st.session_state.warning_message = f"⚠️ SYSTEM NOTICE: Target user has 0 public repositories."

                # Jos repoja löytyy
                else:
                    progress_bar = progress_placeholder.progress(0.0)
                    global_lang_bytes = {} # Sanakirja, johon summataan kaikkien repojen kielitavut

                    # Käydään jokainen repo läpi
                    for idx, repo in enumerate(repos):
                        repo_name = repo["name"]

                        # Haetaan kunkin repon tarkat kielitilastot (tavut)
                        lang_url = f"https://api.github.com/repos/{username_input.strip()}/{repo_name}/languages"

                        try:
                            lang_res = requests.get(lang_url, headers=headers)
                            if lang_res.status_code == 200:
                                repo_languages = lang_res.json() # Palauttaa esim. {"HTML": 500, "CSS": 200}

                                # Summataan löydetyt tavut globaaliin sanakirjaan kielen mukaan
                                for lang, bytes_count in repo_languages.items():
                                    global_lang_bytes[lang] = global_lang_bytes.get(lang, 0) + bytes_count
                        except:
                            pass # Jos yksi repo epäonnistuu, ei kaadeta koko ohjelmaa vaan jatketaan

                        # Päivitetään latauspalkin edistyminen ja skannattujen repojen määrä
                        progress_percentage = (idx + 1) / target_repos_count
                        progress_bar.progress(progress_percentage)
                        render_metrics(repos=str(idx + 1), lang="", status="PENDING")
                        time.sleep(0.02) # Pieni viive tasaisen animaation takaamiseksi

                    # Matemaattinen käsittely datalle, käsitellään se Pandasilla
                    if global_lang_bytes:
                        df = pd.DataFrame(list(global_lang_bytes.items()), columns=["Language", "Bytes"])

                        # Suodatetaan pois "Procfile"-taustakohina, jotta se ei vääristä tuloksia
                        df = df[df["Language"] != "Procfile"]

                        # Järjestetään kielet suurimmasta tavumäärästä pienimpään
                        df = df.sort_values(by="Bytes", ascending=False).reset_index(drop=True)

                        if not df.empty:

                            # Lasketaan kokonaistavut ohjelmointikielistä
                            total_bytes = df["Bytes"].sum()

                            # Lasketaan kunkin kielen aito prosenttiosuus kaikista tavuista yhteensä
                            df["Percentage"] = (df["Bytes"] / total_bytes) * 100
                        
                            # Määritetään eniten käytetty kieli
                            dominant = df.iloc[0]['Language']
                            st.session_state.languages_data = df.to_dict(orient="records")
                        else:
                            dominant = "UNKNOWN"
                            st.session_state.languages_data = None

                    else:
                        dominant = "UNKNOWN"
                        st.session_state.languages_data = None

                    # Pidetään latauspalkki 100 % jälkeen näkyvissä 1s
                    time.sleep(1)

                    # Tallennetaan tiedot istunnon tilaan (Session State)
                    st.session_state.search_status = "COMPLETE"
                    st.session_state.repo_count = str(target_repos_count)
                    st.session_state.primary_lang = dominant

                    # Tyhjennetään latauspalkki pois näkyvistä
                    progress_placeholder.empty()

            else:
                st.session_state.search_status = "INACTIVE"
                st.session_state.warning_message = f"SYSTEM NOTICE: GitHub API failure ({response.status_code})."
        except Exception as e:
            st.session_state.search_status = "INACTIVE"
            st.session_state.warning_message = "SYSTEM NOTICE: Security protocol block or connection timeout."

# Piirretään mittarit lopulliseen tilaan haun päätyttyä
render_metrics(
    repos=st.session_state.repo_count, 
    lang=st.session_state.primary_lang, 
    status=st.session_state.search_status
)

# Plotly vaakapylväs diagrammi
if st.session_state.search_status == "COMPLETE" and st.session_state.languages_data:
    st.markdown("### 🔬 Genetic Strain Distribution")

    # Muunnetaan istunnon tiedot DataFrameksi graafin piirtämistä varten
    df_chart = pd.DataFrame(st.session_state.languages_data)

    # Käännetään datan järjestys ympäri, jotta suurin kieli asettuu vaakagraafissa ylimmäksi
    df_chart = df_chart.iloc[::-1]

    # Luodaan tekstilaput (esim. " 27.1 %") pyöristettynä yhdellä desimaalilla
    text_labels = [f" {pct:.1f} %" for pct in df_chart["Percentage"]]

    # Etsitään suurin prosentti dynaamista X-akselin laajennusta varten
    max_pct = df_chart["Percentage"].max()

    # Luodaan vaakapylväsdiagrammi (Horizontal Bar Chart)
    fig = go.Figure(go.Bar(
        x=df_chart["Percentage"],
        y=df_chart["Language"],
        orientation='h',
        text=text_labels,
        textposition='outside', # Pakotetaan prosenttiteksti palkin ulkopuolelle
        hovertemplate="<b>%{y}</b>: %{x}%<extra></extra>", # Hover-laatikko ilman välimerkkejä
        marker=dict(
            color='#FF3333',
            line=dict(color='#CC0000', width=1)
        ),
        textfont=dict(
            family="Courier New, monospace",
            size=14,
            color="#111111"
        )
    ))

    # Säädetään kaavion asettelu ja dynaamiset marginaalit responsiivisuuden takaamiseksi
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',

        # Marginaali r=180 antaa riittävästi tilaa pisimmänkin palkin prosenteille
        margin=dict(l=120, r=180, t=20, b=20),

        # Tyylitellään hiirellä esiin tuleva hover-laatikko
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#FF3333",
            font_size=14,
            font_family="Courier New, monospace",
            font_color="#111111"
        ),
        xaxis=dict(
            showgrid=False, 
            zeroline=False,
            showticklabels=False, # Piilotetaan X-akselin numerot, prosentit näkyvät jo palkeissa

            # Laajennetaan X-akseli 15 % yli suurimman arvon, jotta teksti ei leikkaudu
            range=[0, max_pct * 1.15]
        ),
        yaxis=dict(
            tickfont=dict(family="Courier New, monospace", size=14, color="#111111")
        ),

        # Lasketaan korkeus automaattisesti kielten määrän mukaan, ei kiinteitä arvoja
        height=100 + (len(df_chart) * 40)
    )

    # Piirretään valmis Plotly-diagrammi ja otetaan käyttöön Streamlitin automaattinen leveys
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# Jos järjestelmässä on aktiivinen huomautus tai virheviesti
if st.session_state.warning_message:
    warning_placeholder.warning(st.session_state.warning_message)