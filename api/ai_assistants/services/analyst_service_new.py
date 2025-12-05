import json
import base64
import numpy as np
import pandas as pd
import plotly.express as px
from openai import OpenAI
from collections import Counter
from django.conf import settings
from ai_assistants.agents.query_classifier_agent import classify_analysis_query
from ai_assistants.agents.prompts import (
    get_data_manipulation_prompt,
    get_data_visualization_prompt,
    get_invalid_query_prompt
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
dataframe_cache = {}


def load_all_datasets():
    """Load data from database into pandas DataFrames"""
    try:
        from accounting.models import Invoice, InvoiceLine, Payment, Contact, Expense
        
        # Load Invoices (Sales Data)
        invoices = Invoice.objects.filter(invoice_type='SALES').values(
            'id', 'invoice_number', 'contact__company_name', 'contact__contact_name',
            'issue_date', 'due_date', 'status', 'subtotal', 'tax_amount', 
            'discount_amount', 'total', 'amount_paid', 'amount_due',
            'currency__code'
        )
        
        if invoices.exists():
            df_invoices = pd.DataFrame(list(invoices))
            df_invoices.columns = [
                'invoice_id', 'invoice_number', 'company_name', 'contact_name',
                'issue_date', 'due_date', 'status', 'subtotal', 'tax_amount',
                'discount_amount', 'total', 'amount_paid', 'amount_due', 'currency'
            ]
            df_invoices['issue_date'] = pd.to_datetime(df_invoices['issue_date'])
            df_invoices['year'] = df_invoices['issue_date'].dt.year
            df_invoices['month'] = df_invoices['issue_date'].dt.month
            df_invoices['month_name'] = df_invoices['issue_date'].dt.strftime('%B')
        else:
            df_invoices = pd.DataFrame()
        
        # Load Contacts (Customers)
        contacts = Contact.objects.filter(contact_type__in=['CUSTOMER', 'BOTH']).values(
            'id', 'contact_type', 'company_name', 'contact_name', 'email',
            'city', 'state', 'country', 'payment_terms', 'credit_limit'
        )
        
        if contacts.exists():
            df_contacts = pd.DataFrame(list(contacts))
        else:
            df_contacts = pd.DataFrame()
        
        # Store in cache
        if not df_invoices.empty:
            dataframe_cache["analysis_data"] = df_invoices
            dataframe_cache["customers"] = df_contacts
            
            return {
                "message": "Database data loaded successfully",
                "rows": {
                    "invoices": len(df_invoices),
                    "customers": len(df_contacts),
                }
            }
        else:
            # Fallback to CSV
            try:
                dataframe_cache["analysis_data"] = pd.read_csv("ai_assistants/data/analysis_data.csv")
                return {
                    "message": "CSV fallback data loaded",
                    "rows": {
                        "analysis_data": len(dataframe_cache["analysis_data"]),
                    }
                }
            except:
                dataframe_cache["analysis_data"] = pd.DataFrame()
                return {
                    "message": "No data available",
                    "rows": {},
                    "empty": True
                }

    except Exception as e:
        raise RuntimeError(f"Failed to load datasets: {e}")


def handle_query_logic(query: str) -> dict:
    df = dataframe_cache.get("analysis_data")
    if df is None or df.empty:
        return {"type": "error", "message": "No analysis data found."}
    try:
        query_type = classify_analysis_query(query, df.columns.tolist())
    except Exception as e:
        return {"type": "error", "message": f"Error classifying query: {e}"}

    if query_type == "DATA_ANALYSIS":
        response_obj = generate_response(query, df, query_type)
        try:
            result = eval(response_obj["code"], {"df": df, "pd": pd})
            return {"type": "table", "data": result.to_dict(orient="records")}
        except Exception as e:
            return {"type": "error", "message": f"Error executing query: {e}"}

    elif query_type == "GRAPH":
        response_obj = generate_response(query, df, query_type)
        try:
            namespace = {"df": df, "pd": pd, "px": px}
            exec(response_obj["code"], namespace)
            fig = namespace.get("fig")
            if fig is None:
                raise ValueError("Graph variable 'fig' not found.")
            fig_dict = json.loads(fig.to_json())
            return convert_plotly_to_recharts_format(fig_dict)
        except Exception as e:
            return {"type": "error", "message": f"Error executing graph query: {e}"}

    else:
        response_obj = generate_response(query, df, "INVALID")
        message = response_obj.get("code", "I cannot answer that query.")
        return {"type": "invalid", "message": message}


def generate_response(query, data: pd.DataFrame, query_type: str):
    if query_type == "DATA_ANALYSIS":
        prompt = get_data_manipulation_prompt()
    elif query_type == "GRAPH":
        prompt = get_data_visualization_prompt()
    else:
        prompt = get_invalid_query_prompt()

    columns = ", ".join(data.columns)
    sample_data = data.head(5).to_string()
    prompt += f"\nDataset Columns: {columns}\nSample Data:\n{sample_data}\nQuery: \"{query}\"\nProvide only the correct response in JSON format."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500,
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"type": "INVALID", "code": f"Error: {e}"}


def convert_plotly_to_recharts_format(fig_dict: dict) -> dict:
    try:
        chart_data = fig_dict.get("data", [])[0]
        chart_type = chart_data.get("type")
        title = fig_dict.get("layout", {}).get("title", {}).get("text", "Untitled Chart")

        def decode_y(y_obj):
            if isinstance(y_obj, dict) and "bdata" in y_obj and "dtype" in y_obj:
                dtype = y_obj["dtype"]
                bdata = base64.b64decode(y_obj["bdata"])
                return np.frombuffer(bdata, dtype=dtype).tolist()
            return y_obj

        if chart_type == "pie":
            labels = chart_data.get("labels", [])
            label_counts = Counter(labels)
            data = [{"label": label, "value": count} for label, count in label_counts.items()]
            return {"type": "pie", "title": title, "data": data, "labelKey": "label", "valueKey": "value"}

        elif chart_type in ["bar", "scatter", "line"]:
            x_values = chart_data.get("x", [])
            y_raw = chart_data.get("y", [])
            y_values = decode_y(y_raw)
            data = [{"x": x, "y": y} for x, y in zip(x_values, y_values) if x is not None and y is not None]
            return {"type": chart_type, "title": title, "data": data, "xKey": "x", "yKey": "y"}

        else:
            return {"type": "unsupported", "message": f"Chart type '{chart_type}' is not supported.",
                    "original": fig_dict}

    except Exception as e:
        return {"type": "error", "message": f"Error converting chart: {e}"}
