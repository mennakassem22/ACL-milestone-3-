# ui/streamlit_app.py - CHIC BLUE & WHITE DESIGN

import streamlit as st
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from intent_classifier import classify_intent_rule_based
from entity_extractor import extract_entities
from retriever import run_template, choose_template_for_intent, expand_subgraph_for_flights
from grounding_builder import build_grounding_from_baseline, build_provenance_table, format_for_recommendation
from llm_prompt import build_prompt, build_system_message
from llm_caller import LLMCaller

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="SkyMind Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chic Blue & White Theme CSS
st.markdown("""
<style>
    /* Elegant gradient background */
    .stApp {
        background: linear-gradient(to bottom, #E3F2FD 0%, #BBDEFB 50%, #90CAF9 100%);
        background-attachment: fixed;
    }
    
    /* Main content container - crisp white */
    .main .block-container {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 2.5rem;
        box-shadow: 0 10px 40px rgba(25, 118, 210, 0.12);
        border: 1px solid rgba(144, 202, 249, 0.3);
    }
    
    /* Elegant header */
    .airline-header {
        text-align: center;
        padding: 2.5rem 2rem;
        background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
        border-radius: 12px;
        margin-bottom: 2.5rem;
        box-shadow: 0 8px 24px rgba(25, 118, 210, 0.25);
    }
    
    .airline-title {
        font-size: 3.2rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
        letter-spacing: 1px;
    }
    
    .airline-slogan {
        font-size: 1.2rem;
        color: #E3F2FD;
        margin-top: 0.5rem;
        font-weight: 400;
        letter-spacing: 0.5px;
    }
    
    /* Chic buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4);
        background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%);
    }
    
    /* Primary action button */
    button[kind="primary"] {
        background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%) !important;
        font-size: 1.05rem !important;
        padding: 0.9rem 2rem !important;
        box-shadow: 0 6px 16px rgba(13, 71, 161, 0.35) !important;
    }
    
    /* Section headers */
    h3 {
        color: #1565C0;
        font-weight: 600;
        border-left: 4px solid #2196F3;
        padding-left: 16px;
        margin-top: 2rem;
    }
    
    /* Info boxes - light blue */
    .stAlert {
        background: #E3F2FD;
        border-radius: 10px;
        border-left: 4px solid #2196F3;
        color: #0D47A1;
    }
    
    /* Success box - elegant */
    .success-box {
        background: linear-gradient(135deg, #F1F8FF 0%, #E3F2FD 100%);
        border-left: 4px solid #1976D2;
        padding: 2rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 16px rgba(25, 118, 210, 0.15);
        color: #0D47A1;
        line-height: 1.8;
    }
    
    /* Metric cards - clean white with blue accents */
    .stMetric {
        background: #FFFFFF;
        padding: 1.2rem;
        border-radius: 10px;
        border: 2px solid #BBDEFB;
        box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
    }
    
    .stMetric label {
        color: #1976D2 !important;
        font-weight: 600 !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #0D47A1 !important;
    }
    
    /* Sidebar - elegant blue gradient */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1565C0 0%, #1976D2 50%, #2196F3 100%);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {
        color: white !important;
        border-left: none !important;
    }
    
    /* Sidebar dividers */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2);
    }
    
    /* Text area - blue border */
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #2196F3;
        font-size: 1rem;
        background: #FFFFFF;
    }
    
    .stTextArea textarea:focus {
        border-color: #1565C0;
        box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
    }
    
    /* Expander - clean style */
    .streamlit-expanderHeader {
        background: #F5FAFF;
        border-radius: 8px;
        border-left: 3px solid #2196F3;
        color: #1565C0;
    }
    
    /* Radio buttons */
    section[data-testid="stSidebar"] .stRadio label {
        color: white !important;
    }
    
    /* Select box in sidebar */
    section[data-testid="stSidebar"] .stSelectbox label {
        color: white !important;
    }
    
    /* Code blocks */
    code {
        background-color: #0D47A1 !important;
        color: #E3F2FD !important;
        border-radius: 6px;
        padding: 2px 6px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #1565C0 0%, #1976D2 50%, #2196F3 100%);
        border-radius: 12px;
        margin-top: 3rem;
        color: white;
        box-shadow: 0 8px 24px rgba(25, 118, 210, 0.25);
    }
    
    /* Input boxes */
    .stTextInput input {
        border: 2px solid #BBDEFB;
        border-radius: 8px;
    }
    
    .stTextInput input:focus {
        border-color: #2196F3;
        box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #2196F3 !important;
    }
</style>
""", unsafe_allow_html=True)

# Elegant Header
st.markdown("""
<div class="airline-header">
    <h1 class="airline-title">✈️ SkyMind Intelligence</h1>
    <p class="airline-slogan">Your Journey, Our Insight</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - MODEL SELECTION
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # Model Selection
    st.markdown("#### 🤖 Select AI Model")
    
    model_options = {
        "🏠 Ollama (Local)": "ollama-llama",
        "☁️ HuggingFace (Cloud)": "hf-mistral"
    }
    
    selected_model = st.selectbox(
        "Choose your AI engine:",
        list(model_options.keys()),
        help="Ollama runs locally (fast, private), HuggingFace runs in cloud (requires token)"
    )
    
    model_choice = model_options[selected_model]
    
    # API key input based on selection
    api_key = None
    if model_choice == "ollama-llama":
        # Check if Ollama is running
        try:
            import requests
            requests.get("http://localhost:11434", timeout=1)
            st.success("✅ Ollama is running")
        except:
            st.error("❌ Ollama not detected")
            st.info("💡 Start Ollama: `ollama serve`")
    else:  # HuggingFace
        api_key = st.text_input(
            "🔑 HuggingFace Token",
            type="password",
            help="Get your token from huggingface.co/settings/tokens"
        )
        if api_key:
            st.success("✅ Token provided")
        else:
            st.warning("⚠️ Token required for HuggingFace")
    
    st.divider()
    
    # Search Method
    st.markdown("#### 🔍 Search Method")
    retrieval_options = {
        "🎯 Smart Search": "Baseline + Embeddings",
        "⚡ Quick Search": "Baseline Only",
        "🧠 AI Search": "Embeddings Only"
    }
    
    selected_search = st.radio(
        "Choose search type:",
        list(retrieval_options.keys()),
        help="Smart Search gives best results"
    )
    
    retrieval_method = retrieval_options[selected_search]
    use_embeddings = retrieval_method in ["Baseline + Embeddings", "Embeddings Only"]
    use_baseline = retrieval_method in ["Baseline Only", "Baseline + Embeddings"]
    
    st.divider()
    
    # Advanced Settings
    with st.expander("⚙️ Advanced"):
        max_tokens = st.slider("Response Length", 200, 1500, 800, 100)
        temperature = st.slider("Creativity", 0.0, 1.0, 0.2, 0.1)
        show_details = st.checkbox("Show Technical Details", value=False)
    
    st.divider()
    
    # About
    st.markdown("#### ℹ️ About")
    st.markdown("""
    <div style='background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;'>
    <small style='color: white;'>
    SkyMind combines Neo4j graphs with AI models for intelligent flight analysis.
    <br><br>
    <strong>Technology Stack:</strong><br>
    • Neo4j Knowledge Graph<br>
    • LLM Integration<br>
    • Semantic Search<br>
    • Real-time Analytics
    </small>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN INTERFACE
# ============================================================================

if 'query_history' not in st.session_state:
    st.session_state.query_history = []

# Quick Action Buttons
st.markdown("### 💡 Quick Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔴 High Delays", use_container_width=True):
        st.session_state.query = "Show flights with highest delays"
with col2:
    if st.button("📊 Route Stats", use_container_width=True):
        st.session_state.query = "What routes perform worst?"
with col3:
    if st.button("⭐ Top Rated", use_container_width=True):
        st.session_state.query = "Show best rated flights"
with col4:
    if st.button("💬 Reviews", use_container_width=True):
        st.session_state.query = "Show feedback for flight 1004"

st.markdown("<br>", unsafe_allow_html=True)

# Query Input
query = st.text_area(
    "✍️ Ask about flights, routes, delays, or passenger feedback:",
    value=st.session_state.get('query', ''),
    height=110,
    placeholder="Example: 'Which flights from ORX to LAX have the best on-time record?'"
)

# Action Buttons
col1, col2, col3 = st.columns([2, 1, 4])
with col1:
    analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
with col2:
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

if clear_btn:
    st.session_state.query = ''
    st.rerun()

# ============================================================================
# MAIN PROCESSING
# ============================================================================

if analyze_btn and query:
    if model_choice == "hf-mistral" and not api_key:
        st.error("⚠️ Please provide your HuggingFace token in the sidebar")
    else:
        with st.spinner("✈️ Processing your query..."):
            try:
                # STEP 1: Intent & Entities
                st.markdown("---")
                st.markdown("### 🎯 Query Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    intent = classify_intent_rule_based(query)
                    intent_names = {
                        "flight_search": "🔍 Flight Search",
                        "delay_query": "⏰ Delay Analysis",
                        "complaints_search": "💬 Feedback",
                        "recommendation": "⭐ Recommendation",
                        "route_stats": "📊 Route Statistics"
                    }
                    st.info(f"**Type:** {intent_names.get(intent, intent)}")
                
                with col2:
                    entities = extract_entities(query)
                    entity_text = ", ".join([f"{k}: {v}" for k, v in entities.items()])
                    st.info(f"**Details:** {entity_text or 'General'}")
                
                # STEP 2: Retrieval
                st.markdown("### 📊 Data Retrieval")
                
                baseline_results = []
                embedding_results = []
                
                if use_baseline:
                    with st.spinner("Searching database..."):
                        template_name = choose_template_for_intent(intent)
                        params = {"limit": 10}
                        
                        if "origin" in entities:
                            params["origin"] = entities["origin"]
                        if "destination" in entities:
                            params["destination"] = entities["destination"]
                        if "flight_number" in entities:
                            params["flight_no"] = entities["flight_number"]
                        
                        if show_details:
                            with st.expander("🔧 Query Details"):
                                from cypher_templates import TEMPLATES
                                st.code(TEMPLATES[template_name]["cypher"], language="cypher")
                        
                        baseline_results = run_template(template_name, params)
                        
                        if baseline_results:
                            flight_nums = [r.get('flight_number') or r.get('flight') for r in baseline_results[:5]]
                            flight_nums = [f for f in flight_nums if f]
                            if flight_nums:
                                expanded = expand_subgraph_for_flights(flight_nums)
                                if expanded:
                                    baseline_results = expanded
                        
                        st.success(f"✅ Found {len(baseline_results)} flights")
                
                if use_embeddings:
                    with st.spinner("AI semantic search..."):
                        try:
                            from embeddings import EmbeddingSearch
                            searcher = EmbeddingSearch("all-MiniLM-L6-v2")
                            
                            if not searcher.load_embeddings():
                                st.info("Building AI index (first time)...")
                                searcher.create_flight_embeddings(limit=200)
                                searcher.save_embeddings()
                            
                            similar = searcher.search_similar(query, top_k=5)
                            embedding_results = [item[0] for item in similar]
                            
                            st.success(f"✅ AI found {len(embedding_results)} related flights")
                        except Exception as e:
                            st.warning(f"⚠️ AI search failed: {str(e)[:40]}...")
                
                combined_results = baseline_results if use_baseline else embedding_results
                
                if not combined_results:
                    st.warning("🔍 No results. Try: 'Show flight 1004' or 'flights from ORX to LAX'")
                    st.stop()
                
                # Show raw retrieved context
                with st.expander("📊 View Retrieved Knowledge Graph Data", expanded=False):
                    st.markdown("**Raw data retrieved from Neo4j before LLM processing:**")
                    st.json(combined_results[:5])  # Show first 5 records
                    if len(combined_results) > 5:
                        st.caption(f"Showing 5 of {len(combined_results)} total records")
                
                # STEP 3: LLM Analysis
                st.markdown("### 🤖 AI Analysis")
                
                if intent == "recommendation":
                    grounding = format_for_recommendation(combined_results, "avg_delay")
                else:
                    grounding = build_grounding_from_baseline(combined_results)
                
                provenance = build_provenance_table(combined_results)
                task_type = "recommendation" if intent == "recommendation" else "qa"
                prompt = build_prompt(query, grounding, provenance, task_type)
                system_msg = build_system_message(task_type)
                
                with st.spinner(f"{'Ollama' if model_choice == 'ollama-llama' else 'HuggingFace'} processing..."):
                    caller = LLMCaller(model_choice, api_key)
                    result = caller.call(prompt, system_msg, max_tokens=max_tokens, temperature=temperature)
                
                st.markdown("---")
                
                if "error" in result:
                    st.error(f"❌ Error: {result['error']}")
                    if "Ollama" in result['error']:
                        st.info("💡 Start Ollama: `ollama serve` in terminal")
                    elif "410" in str(result.get('error', '')):
                        st.info("💡 HuggingFace model unavailable. Try Ollama instead!")
                else:
                    st.markdown("### ✨ Intelligence Report")
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.markdown(result['response'])
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("⚡ Time", f"{result['time']:.1f}s")
                    with col2:
                        st.metric("📊 Records", len(combined_results))
                    with col3:
                        st.metric("🤖 Model", "Ollama" if model_choice == "ollama-llama" else "HuggingFace")
                    with col4:
                        st.metric("🔍 Method", selected_search.split()[0])
                    
                    st.session_state.query_history.append({
                        'query': query,
                        'results': len(combined_results),
                        'time': result['time']
                    })
            
            except Exception as e:
                st.error("❌ An error occurred")
                if show_details:
                    with st.expander("🐛 Debug"):
                        import traceback
                        st.code(traceback.format_exc())

# Query History
if st.session_state.query_history:
    st.markdown("---")
    with st.expander("📜 Recent Queries"):
        for idx, item in enumerate(reversed(st.session_state.query_history[-5:]), 1):
            st.markdown(f"**{idx}.** {item['query'][:70]}...")
            st.caption(f"⏱️ {item['time']:.1f}s | 📊 {item['results']} results")

# Footer
st.markdown("""
<div class="footer">
    <h3 style="color: white; margin: 0;">✈️ SkyMind Intelligence</h3>
    <p style="margin: 0.5rem 0; color: #E3F2FD;"><em>Transforming Flight Data into Insights</em></p>
    <small style="color: #BBDEFB;">
        Neo4j • AI Models • Semantic Search<br>
        CSEN903 Milestone 3 | GUC
    </small>
</div>
""", unsafe_allow_html=True)