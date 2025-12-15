# ui/pages/2_📊_Model_Comparison.py

import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from model_comparison import ModelComparator
from intent_classifier import classify_intent_rule_based
from entity_extractor import extract_entities
from retriever import run_template, choose_template_for_intent
from grounding_builder import build_grounding_from_baseline
from llm_prompt import build_prompt, build_system_message

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Model Comparison - SkyMind",
    page_icon="📊",
    layout="wide"
)

# Apply same styling as main app
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(to bottom, #E3F2FD 0%, #BBDEFB 50%, #90CAF9 100%);
        background-attachment: fixed;
    }
    
    .main .block-container {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 2.5rem;
        box-shadow: 0 10px 40px rgba(25, 118, 210, 0.12);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-left: 4px solid #2196F3;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
    }
    
    .comparison-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%);
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 8px 24px rgba(25, 118, 210, 0.25);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
    }
    
    .test-case-box {
        background: #F5FAFF;
        border-left: 3px solid #2196F3;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="comparison-header">
    <h1>📊 LLM Model Comparison Lab</h1>
    <p style="margin: 0; font-size: 1.1rem;">
        Evaluate Multiple AI Models on Flight Data Analysis
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - Configuration
# ============================================================================

with st.sidebar:
    st.markdown("### ⚙️ Comparison Settings")
    
    st.markdown("#### 🤖 Select Models to Compare")
    
    model_selections = {}
    
    model_selections["ollama-llama"] = st.checkbox(
        " Llama 3.2 (Ollama - Local)",
        value=True,
        help="Fast, private, runs on your machine"
    )
    
    model_selections["hf-mistral"] = st.checkbox(
        "☁️ Mistral 7B (HuggingFace)",
        value=True,
        help="Cloud-based, requires HF token"
    )
    
    model_selections["hf-gemma"] = st.checkbox(
        "☁️ Gemma 2B (HuggingFace)",
        value=False,
        help="Lightweight cloud model"
    )
    
    st.divider()
    
    st.markdown("#### 🔑 API Keys")
    hf_token = st.text_input(
        "HuggingFace Token",
        type="password",
        help="Required for HuggingFace models"
    )
    
    st.divider()
    
    st.markdown("#### 🎯 Test Configuration")
    test_mode = st.radio(
        "Test Mode",
        ["Quick Test (3 queries)", "Standard (5 queries)", "Custom Queries"],
        help="Choose test complexity"
    )
    
    use_auto_eval = st.checkbox(
        "🤖 Enable Automated Evaluation",
        value=True,
        help="Automatically evaluate response quality with metrics"
    )
    
    max_tokens = st.slider("Max Response Tokens", 200, 1500, 800, 100)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
    
    st.divider()
    
    st.markdown("#### 💾 Export Options")
    export_format = st.selectbox(
        "Export Format",
        ["JSON", "CSV", "Markdown Report"]
    )

# ============================================================================
# MAIN INTERFACE
# ============================================================================

# Initialize session state
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None
if 'comparator' not in st.session_state:
    st.session_state.comparator = None

# Tab navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Run Comparison",
    "📈 Quantitative Analysis",
    "✍️ Qualitative Evaluation",
    "📄 Detailed Report"
])

# ============================================================================
# TAB 1: Run Comparison
# ============================================================================

with tab1:
    st.markdown("### 🎯 Test Cases")
    
    if test_mode == "Custom Queries":
        st.info("💡 Enter your own test queries below")
        
        num_queries = st.number_input("Number of test queries", 1, 10, 3)
        custom_queries = []
        
        for i in range(num_queries):
            query = st.text_area(
                f"Query {i+1}",
                placeholder="e.g., Which flights have the longest delays?",
                key=f"custom_query_{i}"
            )
            if query:
                custom_queries.append({
                    "id": i+1,
                    "query": query,
                    "intent": classify_intent_rule_based(query),
                    "difficulty": "custom"
                })
        
        test_cases = custom_queries if custom_queries else ModelComparator.TEST_CASES[:3]
    else:
        num_tests = 3 if "Quick" in test_mode else 5
        test_cases = ModelComparator.TEST_CASES[:num_tests]
        
        st.markdown("**Test queries to be evaluated:**")
        for i, tc in enumerate(test_cases, 1):
            st.markdown(f"""
            <div class="test-case-box">
                <strong>{i}. {tc['query']}</strong><br>
                <small>Intent: {tc['intent']} | Difficulty: {tc['difficulty']}</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Model selection summary
    selected_models = [k for k, v in model_selections.items() if v]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Test Cases", len(test_cases))
    with col2:
        st.metric("🤖 Models", len(selected_models))
    with col3:
        st.metric("🔢 Total Tests", len(test_cases) * len(selected_models))
    
    st.markdown("---")
    
    # Run button
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        run_button = st.button("🚀 Run Comparison", type="primary", use_container_width=True)
    
    if run_button:
        if not selected_models:
            st.error("⚠️ Please select at least one model")
        elif any(model_selections[m] for m in ["hf-mistral", "hf-gemma"]) and not hf_token:
            st.error("⚠️ HuggingFace token required for cloud models")
        else:
            with st.spinner("🔄 Running comparison... This may take a few minutes..."):
                try:
                    # Prepare grounding data for each test case
                    grounding_data = {}
                    
                    for tc in test_cases:
                        intent = tc["intent"]
                        entities = extract_entities(tc["query"])
                        
                        # Get data from Neo4j
                        template_name = choose_template_for_intent(intent)
                        params = {"limit": 10}
                        
                        if "origin" in entities:
                            params["origin"] = entities["origin"]
                        if "destination" in entities:
                            params["destination"] = entities["destination"]
                        if "flight_number" in entities:
                            params["flight_no"] = entities["flight_number"]
                        
                        try:
                            results = run_template(template_name, params)
                            grounding = build_grounding_from_baseline(results)
                            grounding_data[tc["id"]] = grounding
                        except Exception as e:
                            st.warning(f"Could not fetch data for test {tc['id']}: {str(e)}")
                            grounding_data[tc["id"]] = "No grounding data available"
                    
                    # Initialize comparator
                    api_keys = {}
                    if hf_token:
                        api_keys["hf-mistral"] = hf_token
                        api_keys["hf-gemma"] = hf_token
                    
                    comparator = ModelComparator(api_keys=api_keys)
                    
                    # Run comparison
                    results_df = comparator.run_comparison(
                        test_cases=test_cases,
                        models=selected_models,
                        grounding_data=grounding_data,
                        max_tokens=max_tokens,
                        temperature=temperature,
                       
                    )
                    
                    # Store in session state
                    st.session_state.comparison_results = results_df
                    st.session_state.comparator = comparator
                    
                    st.success("✅ Comparison completed!")
                    st.balloons()
                    
                    # Show quick summary
                    st.markdown("### 📊 Quick Results")
                    metrics = comparator.calculate_quantitative_metrics()
                    st.dataframe(metrics, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Error during comparison: {str(e)}")
                    with st.expander("🐛 Debug Info"):
                        import traceback
                        st.code(traceback.format_exc())

# ============================================================================
# TAB 2: Quantitative Analysis
# ============================================================================

with tab2:
    if st.session_state.comparison_results is None:
        st.info("👈 Run a comparison first to see quantitative analysis")
    else:
        st.markdown("### 📈 Quantitative Metrics Analysis")
        
        comparator = st.session_state.comparator
        df = st.session_state.comparison_results
        metrics = comparator.calculate_quantitative_metrics()
        
        # Overall metrics table
        st.markdown("#### 📊 Overall Performance")
        st.dataframe(metrics, use_container_width=True)
        
        # Key findings
        st.markdown("#### 🏆 Key Findings")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fastest = metrics['avg_response_time'].idxmin()
            st.markdown(f"""
            <div class="metric-card">
                <h4>⚡ Fastest Model</h4>
                <h2>{fastest}</h2>
                <p>{metrics.loc[fastest, 'avg_response_time']:.2f}s average</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            most_reliable = metrics['success_rate'].idxmax()
            st.markdown(f"""
            <div class="metric-card">
                <h4>✅ Most Reliable</h4>
                <h2>{most_reliable}</h2>
                <p>{metrics.loc[most_reliable, 'success_rate']:.1f}% success</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            cheapest = metrics['total_cost'].idxmin()
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 Most Cost-Effective</h4>
                <h2>{cheapest}</h2>
                <p>${metrics.loc[cheapest, 'total_cost']:.4f} total</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Visualizations
        st.markdown("#### 📉 Performance Visualizations")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            # Response time comparison
            fig1 = px.bar(
                metrics.reset_index(),
                x='model',
                y='avg_response_time',
                title="Average Response Time by Model",
                labels={'avg_response_time': 'Response Time (s)', 'model': 'Model'},
                color='avg_response_time',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with viz_col2:
            # Success rate comparison
            fig2 = px.bar(
                metrics.reset_index(),
                x='model',
                y='success_rate',
                title="Success Rate by Model",
                labels={'success_rate': 'Success Rate (%)', 'model': 'Model'},
                color='success_rate',
                color_continuous_scale='Greens'
            )
            fig2.update_yaxes(range=[0, 100])  
            st.plotly_chart(fig2, use_container_width=True)
        
        # Automated quality metrics (if available)
        if 'auto_quality_score' in df.columns:
            st.markdown("#### 🤖 Automated Quality Metrics")
            
            quality_metrics = df[df['success']].groupby('model')[[
                'auto_quality_score', 'specificity_score', 'coherence_score', 
                'completeness_score', 'readability_score'
            ]].mean().round(2)
            
            st.dataframe(quality_metrics, use_container_width=True)
            
            # Radar chart for quality dimensions
            st.markdown("##### 📊 Quality Dimensions Comparison")
            
            fig_radar = go.Figure()
            
            for model in quality_metrics.index:
                scores = quality_metrics.loc[model, [
                    'specificity_score', 'coherence_score', 
                    'completeness_score', 'readability_score'
                ]]
                fig_radar.add_trace(go.Scatterpolar(
                    r=scores.values,
                    theta=['Specificity', 'Coherence', 'Completeness', 'Readability'],
                    fill='toself',
                    name=model
                ))
            
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                title="Quality Metrics Radar Chart"
            )
            
            st.plotly_chart(fig_radar, use_container_width=True)
            
            # Hallucination risk
            if 'hallucination_risk' in df.columns:
                st.markdown("##### ⚠️ Hallucination Risk Analysis")
                
                risk_df = df[df['success']].groupby(['model', 'hallucination_risk']).size().reset_index(name='count')
                
                fig_risk = px.bar(
                    risk_df,
                    x='model',
                    y='count',
                    color='hallucination_risk',
                    title="Hallucination Risk Distribution",
                    color_discrete_map={'low': 'green', 'medium': 'orange', 'high': 'red'},
                    barmode='stack'
                )
                st.plotly_chart(fig_risk, use_container_width=True)
        
        # Performance by difficulty
        st.markdown("#### 🎯 Performance by Test Difficulty")
        
        difficulty_df = df[df['success']].groupby(['model', 'difficulty'])['response_time'].agg(['mean', 'count']).reset_index()
        
        fig3 = px.bar(
            difficulty_df,
            x='difficulty',
            y='mean',
            color='model',
            barmode='group',
            title="Response Time by Difficulty Level",
            labels={'mean': 'Avg Response Time (s)', 'difficulty': 'Difficulty'}
        )
        st.plotly_chart(fig3, use_container_width=True)
        
        # Token usage
        st.markdown("#### 🔢 Token Usage Analysis")
        
        token_fig = px.pie(
            metrics.reset_index(),
            values='total_tokens',
            names='model',
            title="Total Token Distribution"
        )
        st.plotly_chart(token_fig, use_container_width=True)

# ============================================================================
# TAB 3: Qualitative Evaluation
# ============================================================================

with tab3:
    if st.session_state.comparison_results is None:
        st.info("👈 Run a comparison first to perform qualitative evaluation")
    else:
        st.markdown("### ✍️ Manual Qualitative Evaluation")
        st.markdown("""
        Rate each model's response on the following criteria (1-5 scale):
        - **Relevance**: How relevant is the answer to the question?
        - **Accuracy**: Is the information factually correct?
        - **Completeness**: Does it fully answer the question?
        - **Naturalness**: How natural and well-written is the response?
        """)
        
        df = st.session_state.comparison_results
        
        # Initialize qualitative scores in session state
        if 'qualitative_scores' not in st.session_state:
            st.session_state.qualitative_scores = {}
        
        # Group by test case
        for test_id in df['test_id'].unique():
            test_results = df[df['test_id'] == test_id]
            test_query = test_results.iloc[0]['query']
            
            st.markdown(f"#### Test {test_id}: {test_query}")
            
            for _, row in test_results[test_results['success']].iterrows():
                with st.expander(f"📝 {row['model']} - Response"):
                    st.markdown(f"**Response Time:** {row['response_time']:.2f}s")
                    st.markdown("**Response:**")
                    st.info(row['response'])
                    
                    st.markdown("---")
                    st.markdown("**Rate this response:**")
                    
                    key_prefix = f"{test_id}_{row['model_id']}"
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        relevance = st.slider(
                            "Relevance",
                            1, 5, 3,
                            key=f"{key_prefix}_relevance"
                        )
                        accuracy = st.slider(
                            "Accuracy",
                            1, 5, 3,
                            key=f"{key_prefix}_accuracy"
                        )
                    
                    with col2:
                        completeness = st.slider(
                            "Completeness",
                            1, 5, 3,
                            key=f"{key_prefix}_completeness"
                        )
                        naturalness = st.slider(
                            "Naturalness",
                            1, 5, 3,
                            key=f"{key_prefix}_naturalness"
                        )
                    
                    comments = st.text_area(
                        "Comments",
                        key=f"{key_prefix}_comments",
                        placeholder="Optional notes about this response..."
                    )
                    
                    # Store scores
                    st.session_state.qualitative_scores[key_prefix] = {
                        'test_id': test_id,
                        'model': row['model'],
                        'relevance': relevance,
                        'accuracy': accuracy,
                        'completeness': completeness,
                        'naturalness': naturalness,
                        'overall': (relevance + accuracy + completeness + naturalness) / 4,
                        'comments': comments
                    }
            
            st.markdown("---")
        
        # Summary of qualitative scores
        if st.session_state.qualitative_scores:
            st.markdown("### 📊 Qualitative Summary")
            
            qual_df = pd.DataFrame(list(st.session_state.qualitative_scores.values()))
            avg_scores = qual_df.groupby('model')[['relevance', 'accuracy', 'completeness', 'naturalness', 'overall']].mean()
            
            st.dataframe(avg_scores.round(2), use_container_width=True)
            
            # Radar chart
            fig = go.Figure()
            
            for model in avg_scores.index:
                scores = avg_scores.loc[model, ['relevance', 'accuracy', 'completeness', 'naturalness']]
                fig.add_trace(go.Scatterpolar(
                    r=scores.values,
                    theta=['Relevance', 'Accuracy', 'Completeness', 'Naturalness'],
                    fill='toself',
                    name=model
                ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                showlegend=True,
                title="Qualitative Scores Comparison"
            )
            
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 4: Detailed Report
# ============================================================================

with tab4:
    if st.session_state.comparison_results is None:
        st.info("👈 Run a comparison first to generate a detailed report")
    else:
        st.markdown("### 📄 Comprehensive Comparison Report")
        
        comparator = st.session_state.comparator
        
        # Generate report
        report = comparator.generate_comparison_report()
        
        # Display report
        st.markdown(report)
        
        st.markdown("---")
        
        # Export options
        st.markdown("### 💾 Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Download JSON", use_container_width=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"comparison_{timestamp}.json"
                comparator.save_results(filename)
                st.success(f"Saved to {filename}")
        
        with col2:
            if st.button("📥 Download CSV", use_container_width=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"comparison_{timestamp}.csv"
                st.session_state.comparison_results.to_csv(filename, index=False)
                st.success(f"Saved to {filename}")
        
        with col3:
            if st.button("📥 Download Report (MD)", use_container_width=True):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{timestamp}.md"
                with open(filename, 'w') as f:
                    f.write(report)
                st.success(f"Saved to {filename}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #1976D2 0%, #2196F3 100%); border-radius: 12px; color: white;">
    <h3 style="margin: 0;">📊 Model Comparison Lab</h3>
    <p style="margin: 0.5rem 0;">Systematic LLM Evaluation for Flight Intelligence</p>
    <small>Part of SkyMind Intelligence | CSEN903 Milestone 3</small>
</div>
""", unsafe_allow_html=True)