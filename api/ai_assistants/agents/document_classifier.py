from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def classify_document_query(query: str) -> str:
    prompt = f"""
You are an AI assistant that classifies user queries related to a document into one of the following categories:

1. TRANSLATE – For queries like "Translate to French" or "Make this Hindi".
2. SUMMARIZE_AGAIN – For queries like "Summarize again", "Shorten this", or "Give a new summary".
3. EXTRACT_INFO – For queries like "Give me phone number", "Find email", or "Get merchant details".
4. TABLE_TO_EXCEL – For queries like "Export the table", "Give table in Excel", etc.
5. QUERY_ANALYSIS – For anything else like "What is this about?", "How much was paid?", etc.

Classify this query: "{query}"

Respond with just one of the labels: TRANSLATE, SUMMARIZE_AGAIN, EXTRACT_INFO, TABLE_TO_EXCEL, QUERY_ANALYSIS
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        label = response.choices[0].message.content.strip().upper()
        valid = {"TRANSLATE", "SUMMARIZE_AGAIN", "EXTRACT_INFO", "TABLE_TO_EXCEL", "QUERY_ANALYSIS"}
        return label if label in valid else "QUERY_ANALYSIS"
    except Exception:
        return "QUERY_ANALYSIS"
