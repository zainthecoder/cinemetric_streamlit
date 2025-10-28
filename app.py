"""
Main Streamlit application for CineMetric
"""
import streamlit as st
import json
from database import (
    init_db, get_db, get_all_personas, get_persona_by_id,
    create_conversation, create_evaluation_result, import_personas_from_json
)
from groq_integration import evaluate_conversation

# Page configuration
st.set_page_config(
    page_title="CineMetric",
    page_icon="💬",
    layout="wide"
)

# Initialize database
@st.cache_resource
def initialize_database():
    """Initialize database and import personas if needed"""
    init_db()
    db = get_db()
    
    # Check if personas exist
    personas = get_all_personas(db)
    if len(personas) == 0:
        st.info("📥 Importing default personas...")
        # Load personas from JSON file
        try:
            with open("personas.json", "r") as f:
                personas_data = json.load(f)
            import_personas_from_json(db, personas_data["personas"])
        except FileNotFoundError:
            st.warning("⚠️ personas.json file not found. Please create it manually.")
    
    db.close()
    return True

# Initialize
initialize_database()

# App title
st.title("💬 CineMetric")
st.markdown("Select multiple personas, enter a conversation, and define a metric to evaluate the interaction.")

# Create two columns for layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🎭 Select Personas")
    
    # Get personas from database
    db = get_db()
    personas = get_all_personas(db)
    
    if len(personas) == 0:
        st.error("❌ No personas found in database. Please import personas first.")
    else:
        # Create persona selection checkboxes
        selected_persona_ids = []
        for persona in personas:
            if st.checkbox(
                f"{persona.name}",
                key=f"persona_{persona.id}",
                help=persona.description
            ):
                selected_persona_ids.append(persona.id)
        
        # Show selected personas details
        if selected_persona_ids:
            st.markdown("**Selected Characters:**")
            for pid in selected_persona_ids:
                persona = get_persona_by_id(db, pid)
                with st.expander(f"📖 {persona.name}"):
                    st.write(persona.description)

with col2:
    st.subheader("📊 Evaluation Metrics")
    
    # Suggested metrics
    suggested_metrics = ["Empathy", "Clarity", "Helpfulness", "Professionalism", "Authenticity", "Coherence"]
    
    # Metric input
    selected_metrics = st.multiselect(
        "Choose metrics to evaluate:",
        options=suggested_metrics,
        default=["Empathy"],
        help="Select one or more metrics for evaluation"
    )
    
    # Custom metric input
    custom_metric = st.text_input("Or add a custom metric:", placeholder="e.g., Technical Accuracy")
    if custom_metric and custom_metric not in selected_metrics:
        selected_metrics.append(custom_metric)

# Conversation input
st.subheader("💭 Conversation Input")

conversation_format = st.radio(
    "Conversation Format:",
    ["Plain Text", "Multi-Turn Structured"],
    horizontal=True
)

if conversation_format == "Plain Text":
    conversation_text = st.text_area(
        "Enter the conversation to evaluate:",
        placeholder="Type or paste the conversation here...",
        height=200
    )
    is_multi_turn = False
    turns = None
else:
    st.info("📝 Enter each turn of the conversation separately")
    num_turns = st.number_input("Number of turns:", min_value=1, max_value=20, value=2)
    
    turns = []
    for i in range(num_turns):
        col_speaker, col_message = st.columns([1, 3])
        with col_speaker:
            speaker = st.text_input(f"Speaker {i+1}:", value=f"Person {i+1}", key=f"speaker_{i}")
        with col_message:
            message = st.text_area(f"Message {i+1}:", key=f"message_{i}", height=80)
        
        if speaker and message:
            turns.append({"speaker": speaker, "message": message})
    
    # Format conversation text
    conversation_text = "\n".join([f"{turn['speaker']}: {turn['message']}" for turn in turns])
    is_multi_turn = True

# Evaluation options
evaluate_per_turn = st.checkbox(
    "Evaluate each turn separately (multi-turn only)",
    disabled=(conversation_format != "Multi-Turn Structured"),
    help="Provide detailed evaluation for each conversation turn"
)

store_conversation = st.checkbox("Save conversation to database", value=True)

# Evaluate button
if st.button("🚀 Evaluate Conversation", type="primary", disabled=not (selected_persona_ids and selected_metrics and conversation_text)):
    if not selected_persona_ids:
        st.error("❌ Please select at least one persona")
    elif not selected_metrics:
        st.error("❌ Please select at least one metric")
    elif not conversation_text:
        st.error("❌ Please enter a conversation")
    else:
        # Store conversation if requested
        saved_conversation = None
        if store_conversation:
            saved_conversation = create_conversation(
                db,
                content=conversation_text,
                is_multi_turn=is_multi_turn,
                turns=turns if is_multi_turn else None
            )
        
        # Evaluate with each persona
        for persona_id in selected_persona_ids:
            persona = get_persona_by_id(db, persona_id)
            
            st.markdown(f"---")
            st.subheader(f"🎭 {persona.name}")
            
            persona_context = f"{persona.name}: {persona.description}"
            
            # Evaluate each metric
            for metric in selected_metrics:
                with st.spinner(f"Evaluating {metric.lower()}..."):
                    try:
                        result = evaluate_conversation(
                            prompt_template=persona.prompt_template,
                            metric=metric,
                            conversation=conversation_text,
                            persona_context=persona_context
                        )
                        
                        # Display results
                        st.markdown(f"**📈 {metric}**")
                        
                        # Score visualization
                        score = result["score"]
                        st.progress(score / 10)
                        st.metric(label="Score", value=f"{score}/10")
                        
                        # Explanation
                        st.markdown("**💭 Evaluation:**")
                        st.info(result["explanation"])
                        
                        # Save to database if conversation was stored
                        if saved_conversation:
                            create_evaluation_result(
                                db,
                                conversation_id=saved_conversation.id,
                                persona_id=persona.id,
                                metric=metric,
                                score=score,
                                explanation=result["explanation"]
                            )
                        
                    except Exception as e:
                        st.error(f"❌ Evaluation failed: {str(e)}")

# Close database connection
db.close()

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This tool uses AI personas of famous movie characters to evaluate conversations based on specific metrics.
    
    **Features:**
    - Multiple persona selection
    - Custom evaluation metrics
    - Plain text or structured conversations
    - Turn-by-turn analysis
    - Results storage
    
    **Powered by:**
    - Groq API (Llama 3.1)
    - PostgreSQL Database
    - Streamlit
    """)
    
    st.markdown("---")
    st.markdown("**Available Personas:**")
    db = get_db()
    personas = get_all_personas(db)
    for p in personas:
        st.markdown(f"• {p.name}")
    db.close()