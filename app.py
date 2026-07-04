import streamlit as st
import requests
import time

# Sivun asetukset
st.set_page_config(
    page_title="Genetic Code Analysis",
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
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #111111;
        margin-bottom: 5px;
    }
    .sidebar-status {
        font-family: monospace;
        font-size: 0.85rem;
        color: #444444;
        margin-bottom: 5px;
    }
    .sidebar-section {
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #111111;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    [data-testid="stSidebar"] hr {
        border: 1px solid #0077FF !important;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .main-title {
        font-family: 'Courier New', Courier, monospace !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        font-size: 2.5rem !important;
        margin-bottom: 25px !important;
        color: #111111 !important;
    }
    .main-title span {
        color: #0077FF !important;
        display: inline !important;
    }
    .stButton>button {
        background-color: transparent !important;
        color: #0077FF !important;
        border: 1px solid #0077FF !important;
        border-radius: 4px !important;
        font-family: monospace !important;
        font-weight: bold !important;
        letter-spacing: 1px !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        margin-top: 10px;
    }
    .stButton>button:hover {
        background-color: #0077FF !important;
        color: #FFFFFF !important;
        border-color: #0077FF !important;
    }
    [data-testid="stNotification"] p {
        color: #222222 !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Alustetaan tilamuuttujat (Session State) dynaamista seurantaa varten
if "search_status" not in st.session_state:
    st.session_state.search_status = "INACTIVE"
if "repo_count" not in st.session_state:
    st.session_state.repo_count = "0"
if "primary_lang" not in st.session_state:
    st.session_state.primary_lang = "None"
if "warning_message" not in st.session_state:
    st.session_state.warning_message = "SYSTEM NOTICE: Awaiting target user ID input."

progress_placeholder = st.empty()

#Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-title">Control Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-text">Access level: Unrestricted</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-text">System status: Ready</div>', unsafe_allow_html=True)

    st.divider()

    # Näytteenotto
    st.markdown('<div class="sidebar-section">Sample Acquisition</div>', unsafe_allow_html=True)
    username_input = st.text_input("Target User ID", placeholder="Enter GitHub username...")

    # Scan button
    scan_button = st.button("START SCAN")

# Main content
st.markdown(
    '<div class="main-title"><span>G</span>enetic <span>C</span>ode <span>A</span>nalysis</div>', 
    unsafe_allow_html=True
)

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

if scan_button:
    if not username_input.strip():
        st.session_state.search_status = "INACTIVE"
        st.session_state.repo_count = "0"
        st.session_state.primary_lang = "None"
        st.session_state.warning_message = "SYSTEM NOTICE: Target user ID is required to initiate scan."
    else:
        st.session_state.warning_message = ""
        warning_placeholder.empty()

        render_metrics(repos="0", lang="", status="PENDING")

        headers = {}
        if "GITHUB_TOKEN" in st.secrets:
            headers["Authorization"] = f"token {st.secrets['GITHUB_TOKEN']}"
            
        url = f"https://api.github.com/users/{username_input.strip()}/repos?per_page=100"

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 404:
                st.session_state.search_status = "INACTIVE"
                st.session_state.repo_count = "0"
                st.session_state.primary_lang = "None"
                st.session_state.warning_message = f"SYSTEM NOTICE: User '{username_input}' not found in GitHub registry."
            elif response.status_code == 200:
                repos = response.json()
                target_repos_count = len(repos)

                if target_repos_count == 0:
                    st.session_state.search_status = "COMPLETE"
                    st.session_state.repo_count = "0"
                    st.session_state.primary_lang = "None"
                    st.session_state.warning_message = f"SYSTEM NOTICE: Target user has 0 public repositories."
                else:
                    progress_bar = progress_placeholder.progress(0.0)

                    steps = 25
                    for i in range(1, steps + 1):
                        progress_percentage = i / steps
                        progress_bar.progress(progress_percentage)

                        current_count = int(progress_percentage * target_repos_count)
                        render_metrics(repos=str(current_count), lang="", status="PENDING")

                        time.sleep(0.05)

                    time.sleep(1)

                    st.session_state.search_status = "COMPLETE"
                    st.session_state.repo_count = str(target_repos_count)
                    st.session_state.primary_lang = "TBD"

                    progress_placeholder.empty()

            else:
                st.session_state.search_status = "INACTIVE"
                st.session_state.warning_message = f"SYSTEM NOTICE: GitHub API failure ({response.status_code})."
        except Exception as e:
            st.session_state.search_status = "INACTIVE"
            st.session_state.warning_message = "SYSTEM NOTICE: Security protocol block or connection timeout."

render_metrics(
    repos=st.session_state.repo_count, 
    lang=st.session_state.primary_lang, 
    status=st.session_state.search_status
)

if st.session_state.warning_message:
    warning_placeholder.warning(st.session_state.warning_message)