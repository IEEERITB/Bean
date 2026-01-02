import os
import json
import io
import google.generativeai as genai
from dotenv import load_dotenv
from docxtpl import DocxTemplate
from models import EventReport

# Load environment variables
load_dotenv()

# Configure Gemini API
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)

def get_model():
    """Returns the configured Gemini model."""
    return genai.GenerativeModel('gemini-2.5-flash')

def analyze_text(raw_input: str, current_state: dict) -> dict:
    """
    Analyzes the text to extract event details and update the current state.
    """
    try:
        model = get_model()
        
        # strict schema definition for the model to follow
        schema_instruction = """
        You are a strict data extraction engine. Your goal is to extract event details from the user's text 
        and map them to the following JSON schema.
        
        Target Schema:
        {{
            "event_title": "String or 'UNKNOWN'",
            "date": "String or 'UNKNOWN'",
            "speaker_name": "String or 'UNKNOWN'",
            "attendance_count": "Integer or 'UNKNOWN'",
            "duration_hours": "Float or 'UNKNOWN'",
            "executive_summary": "String (3 sentences) or 'UNKNOWN'",
            "key_takeaways": ["String", "String", "String"] (or empty list if unknown),
            "missing_info": ["field_name_1", "field_name_2"] (list of fields set to 'UNKNOWN')
        }}
        
        Rules:
        1. If a value is not explicitly mentioned or clearly inferred, value MUST be "UNKNOWN".
        2. Do NOT hallucinate or invent data.
        3. If 'attendance_count' or 'duration_hours' are 'UNKNOWN', keep them as string "UNKNOWN". If found, valid numbers.
        4. Update the 'missing_info' list to include ALL fields that are currently "UNKNOWN". 
           The required fields to track in missing_info are: event_title, date, attendance_count, duration_hours, executive_summary, key_takeaways.
           speaker_name is optional, but if missing and relevant, you can track it, otherwise ignore. 
           Actually, strictly follow this: If any of [event_title, date, attendance_count, duration_hours, executive_summary, key_takeaways] is 'UNKNOWN' or empty, add it to missing_info.
        5. Merge new information with the Previous State provided below. If the user provides a correction, overwrite the old value.
        
        Previous State:
        {current_state}
        
        User Input:
        "{raw_input}"
        
        Output only valid JSON.
        """
        
        formatted_prompt = schema_instruction.format(
            current_state=json.dumps(current_state, default=str),
            raw_input=raw_input
        )

        response = model.generate_content(formatted_prompt, generation_config={"response_mime_type": "application/json"})
        
        try:
            extracted_data = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if model returns markdown block
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            extracted_data = json.loads(cleaned_text)
            
        return extracted_data

    except Exception as e:
        print(f"Error in analyze_text: {e}")
        # Return current state if failure, to avoid data loss
        return current_state

def generate_clarification_question(missing_fields: list[str]) -> str:
    """
    Generates a natural language question to ask the user for missing information.
    """
    if not missing_fields:
        return "All information looks complete! You can now download the report."

    try:
        model = get_model()
        prompt = f"""
        You are a helpful assistant. The user is trying to generate a report but is missing some information.
        Missing Fields: {missing_fields}
        
        Generate a polite, single-sentence question asking the user to provide the missing details. 
        Prioritize the most important missing fields (like Title or Date) if there are many.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Could you please provide details for: {', '.join(missing_fields)}?"

def generate_docx(data: dict, template_path: str = "templates/ieee_report_template.docx") -> io.BytesIO:
    """
    Renders the data into a DOCX template and returns the file as a BytesIO object.
    """
    doc = DocxTemplate(template_path)
    
    # Ensure context keys match template tags.
    # We might need to handle 'key_takeaways' specifically if the template expects a loop or formatted string.
    # Assuming template does something like:
    # {% for point in key_takeaways %}
    # - {{ point }}
    # {% endfor %}
    
    doc.render(data)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream