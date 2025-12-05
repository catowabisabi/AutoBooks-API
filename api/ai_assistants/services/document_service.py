import os
import uuid
import json
from PIL import Image
from pdf2image import convert_from_bytes
import google.generativeai as genai
from django.conf import settings
from ai_assistants.agents.prompts import get_document_analysis_prompt
from ai_assistants.agents.document_classifier import classify_document_query

# Load Gemini config
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

# Allowed types
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'jfif'}
document_cache = {}


def is_allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_pdf_to_combined_image(pdf_file):
    images = convert_from_bytes(pdf_file.read(), size=(800, None))
    widths, heights = zip(*(i.size for i in images))

    total_height = sum(heights)
    max_width = max(widths)

    combined_image = Image.new("RGB", (max_width, total_height), color="white")
    y_offset = 0
    for img in images:
        combined_image.paste(img, (0, y_offset))
        y_offset += img.height

    return combined_image


def get_gemini_response(image, prompt: str):
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content([prompt, image])
    return response.text  # This returns the text content directly


# We can remove these utility functions since we're getting structured JSON from Gemini
# def extract_summary(text: str) -> str:
#     return text[:500].strip() if text else "No summary available."

# def extract_html(text: str) -> str:
#     if "<html>" in text:
#         return text[text.index("<html>"):]
#     return "No HTML structure found."


def process_document(file) -> dict:
    filename = file.name
    doc_id = str(uuid.uuid4())

    try:
        # Validate type
        if filename.lower().endswith(".pdf"):
            image = convert_pdf_to_combined_image(file)
        elif filename.lower().endswith(tuple(ALLOWED_EXTENSIONS - {"pdf"})):
            image = Image.open(file)
        else:
            raise ValueError("Unsupported file type")

        prompt = get_document_analysis_prompt()

        # Gemini Vision Call
        response_text = get_gemini_response(image, prompt)

        # Clean up the response text
        raw_text = response_text.strip()

        # Remove markdown json wrapper if present
        if raw_text.startswith("```json") and raw_text.endswith("```"):
            raw_text = raw_text[len("```json"):].strip()
            raw_text = raw_text.rstrip("```").strip()

        # Parse JSON response
        parsed_response = json.loads(raw_text)

        # Add document ID to the response
        parsed_response["document_id"] = doc_id

        print(f"Processed document {doc_id}: {parsed_response}")

        # Cache the document with the parsed response
        document_cache[doc_id] = parsed_response

        return parsed_response

    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response from Gemini: {str(e)}")
    except Exception as e:
        raise Exception(f"Document processing failed: {str(e)}")


def handle_document_query_logic(document_id: str, query: str) -> dict:
    doc = document_cache.get(document_id)
    if not doc:
        return {
            "type": "error",
            "message": f"Document with ID {document_id} not found."
        }

    query_type = classify_document_query(query)

    # Get content from the cached document
    content = doc.get("html_structure", "") or doc.get("summary", "")

    if query_type == "TRANSLATE":
        prompt = f"Translate the following document to the language requested in the query.\nQuery: {query}\nDocument:\n{content}"
    elif query_type == "SUMMARIZE_AGAIN":
        prompt = f"Rewrite or rephrase the summary of the following document:\n{content}"
    elif query_type == "EXTRACT_INFO":
        prompt = f"Extract specific information based on the user query.\nQuery: {query}\nDocument:\n{content}"
    elif query_type == "TABLE_TO_EXCEL":
        # Return tables directly from the parsed response
        tables = doc.get("tables", [])
        return {
            "type": "success",
            "document_id": document_id,
            "query_type": query_type,
            "response": {
                "tables": tables,
                "message": f"Found {len(tables)} tables in the document"
            }
        }
    else:  # QUERY_ANALYSIS
        prompt = f"Answer the user's question using this document.\nQuery: {query}\nDocument:\n{content}"

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        result = response.text

        return {
            "type": "success",
            "document_id": document_id,
            "query_type": query_type,
            "response": result
        }
    except Exception as e:
        return {
            "type": "error",
            "message": f"Gemini processing failed: {str(e)}",
            "query_type": query_type
        }
