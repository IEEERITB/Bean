import streamlit as st
import time
import os
from models import EventReport
from logic import analyze_text, generate_clarification_question, generate_docx

# --- Page Config ---
st.set_page_config(page_title="Bean - IEEE Auto-Doc Agent", layout="wide")

# --- Session State Initialization ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    # Add initial greeting
    st.session_state.chat_history.append({"role": "assistant", "content": "Hello! I'm Bean. Paste your event notes or chat logs, and I'll help you create an IEEE report."})

if "report_data" not in st.session_state:
    # Initialize with UNKNOWN values based on our model
    st.session_state.report_data = {
        "event_title": "UNKNOWN",
        "date": "UNKNOWN",
        "speaker_name": "UNKNOWN",
        "attendance_count": "UNKNOWN",
        "duration_hours": "UNKNOWN",
        "executive_summary": "UNKNOWN",
        "key_takeaways": [],
        "missing_info": ["event_title", "date", "attendance_count", "duration_hours", "executive_summary", "key_takeaways"]
    }

if "processing_status" not in st.session_state:
    st.session_state.processing_status = "idle"

# --- Layout ---
left_col, right_col = st.columns([0.4, 0.6])

# --- Column 1: Chat Agent ---
with left_col:
    st.header("💬 Chat Agent")
    
    # Display chat history
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Type your message..."):
        # User message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Logic Processing
        with st.spinner("Analyzing text..."):
            # 1. Analyze text
            new_data = analyze_text(prompt, st.session_state.report_data)
            st.session_state.report_data = new_data
            
            # 2. Check for missing info
            missing_info = new_data.get("missing_info", [])
            
            # 3. Generate response
            response_text = generate_clarification_question(missing_info)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(response_text)
        
        st.rerun()

# --- Column 2: Live Preview ---
with right_col:
    st.header("📄 Live Report Preview")
    
    data = st.session_state.report_data
    missing_info = data.get("missing_info", [])
    
    # Completeness Progress
    # Required fields tracked in missing_info vs total required fields
    # Hardcoded required fields for calculation
    required_fields = ["event_title", "date", "attendance_count", "duration_hours", "executive_summary", "key_takeaways"]
    # Logic: if field NOT in missing_info, it's complete.
    completed_count = sum(1 for field in required_fields if field not in missing_info)
    total_fields = len(required_fields)
    progress = completed_count / total_fields if total_fields > 0 else 0
    
    st.progress(progress, text=f"Completeness: {int(progress*100)}%")

    # --- Metric Cards ---
    m1, m2, m3 = st.columns(3)
    
    def render_field_status(value, field_name):
        is_missing = field_name in missing_info
        icon = "🔴" if is_missing else "✅"
        display_val = "MISSING" if is_missing else value
        return f"{icon} {display_val}"

    with m1:
        st.metric("Event Title", render_field_status(data.get("event_title"), "event_title"))
    with m2:
        st.metric("Date", render_field_status(data.get("date"), "date"))
    with m3:
        st.metric("Attendance", render_field_status(data.get("attendance_count"), "attendance_count"))

    st.divider()
    
    st.subheader("Details")
    st.markdown(f"**Speaker:** {render_field_status(data.get('speaker_name'), 'speaker_name')}")
    st.markdown(f"**Duration:** {render_field_status(data.get('duration_hours'), 'duration_hours')} hours")
    
    st.subheader("Executive Summary")
    summary = data.get("executive_summary")
    if "executive_summary" in missing_info:
        st.warning("Executive Summary missing")
    else:
        st.info(summary)

    st.subheader("Key Takeaways")
    takeaways = data.get("key_takeaways")
    if "key_takeaways" in missing_info or not takeaways:
        st.warning("No key takeaways identified")
    else:
        for t in takeaways:
            st.markdown(f"- {t}")

    # --- Download Section ---
    st.divider()
    
    # Check if ready to download
    # We consider it ready if critical fields are NOT in missing_info.
    # If strictly following 'missing_info' list from logic:
    is_ready = len(missing_info) == 0
    
    if is_ready:
        st.success("Report Ready for Generation!")
        
        # Generate docx in memory
        # We assume template exists at templates/ieee_report_template.docx
        try:
            docx_file = generate_docx(data)
            
            st.download_button(
                label="Download Report (.docx)",
                data=docx_file,
                file_name=f"IEEE_Report_{data.get('event_title', 'draft').replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error generating document: {e}")
            st.info("Please ensure 'templates/ieee_report_template.docx' exists.")
            
    else:
        st.button("Download Report (.docx)", disabled=True, help="Fill all missing fields to enable download")

