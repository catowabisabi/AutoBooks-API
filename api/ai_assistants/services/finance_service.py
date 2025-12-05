import os
import json
from PIL import Image
from pdf2image import convert_from_bytes
from google.generativeai import GenerativeModel
from django.conf import settings
import google.generativeai as genai

# Load Gemini config
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS


class ReceiptAnalyzerService:
    def analyze_receipt(self, file, categories):
        filename = file.name.lower()
        category_list = [cat.strip() for cat in categories] if categories else []

        prompt = self.build_prompt(category_list)

        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.jfif')):
            image = Image.open(file)
        elif filename.endswith('.pdf'):
            image = self.convert_pdf_to_image(file)
        else:
            raise ValueError("Unsupported file format")

        response_text = self.get_gemini_response(image, prompt)
        cleaned_json = self.clean_response(response_text)

        try:
            parsed_data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}")

        return parsed_data

    def build_prompt(self, categories):
        return f"""
            You are analyzing an expense receipt image and need to extract the following structured information as JSON. Choose the best match for 'expenseCategory' from: {categories}.
            
            Expense receipt may be in any language or script.
            - If the values for item name, merchant name etc are not in Roman script then translate the item name, merchant name etc. to English and append to the value with a hyphen in between.
            - expenseDate should be in the format YYYY-MM-DD.
            - Determine the country name from city, phone number, or pin/zip code. Return two digit ISO code for the country.
            - If you cannot determine the receiptCurrency from the receipt then return the three character currency code of the country as the receiptCurrency, like USD, INR, etc.
            - Make sure to map the currency symbol to the currency code.
            - If there is a currency symbol in the amount field then take the value after the currency symbol. For example, for 23 $ 6.49 take 6.49
            - for the hotel expense, city name should be the city where the hotel is located and country should be the country for the hotel.  Hotel name would be the merchant name.
            - Treat voucher image as an expense receipt image. Voucher date would be same as expenseDate.
            
            Return a JSON in this exact format (values should be extracted or null if not available):

            {{
              "merchantName": "Name of the merchant or vendor from the receipt, translated to English if not in Roman script.",
              "invoiceNo": "Invoice number mentioned on the receipt, if available.",
              "expenseDate": "Date of the expense in YYYY-MM-DD format. This is usually the date on the receipt.",
              "currency": "Three-letter currency code like USD, INR, EUR. If a symbol is present, map it accordingly.",
              "claimedAmount": "Total amount claimed from the receipt. Extract the numeric value, ignoring currency symbols.",
              "city": "City name where the expense occurred. Extract from the receipt header, address, or footer.",
              "country": "Full country name (e.g., USA, India) derived from address, phone code, or ZIP code.",
              "description": "A brief, human-readable description of the expense, describing the receipt (e.g., 'Expense for Hotel Stay and Meal on 20th July 2025.').",
              "status": "Set this to 'Pending' by default. Used by the reviewer to update the claim status.",
              "receiptFile": "Set this to null. This will be replaced by the uploaded file on backend."
            }}

            If a field is not present on the receipt, return null for that field.
            Do not include explanations or notes—return only the JSON.
            """

    def get_gemini_response(self, image, prompt):
        model = GenerativeModel('gemini-1.5-pro')
        response = model.generate_content([prompt, image])
        return response.text

    def clean_response(self, response_text: str) -> str:
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("Could not extract JSON from Gemini response.")
        return response_text[start:end + 1]

    def convert_pdf_to_image(self, pdf_file):
        images = convert_from_bytes(pdf_file.read(), size=(1024, None))
        return images[0]
