"""
Analyst Service - Database Version
分析助手服務 - 資料庫版本

This service loads data from Django models instead of CSV files.
"""

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
    """Load data from database into pandas DataFrames / 從資料庫載入數據"""
    try:
        from accounting.models import Invoice, InvoiceLine, Payment, Contact, Expense
        
        # Load Invoices (Sales Data) / 載入發票（銷售數據）
        invoices = Invoice.objects.filter(invoice_type='SALES').values(
            'id', 'invoice_number', 'contact__company_name', 'contact__contact_name',
            'issue_date', 'due_date', 'status', 'subtotal', 'tax_amount', 
            'discount_amount', 'total', 'amount_paid', 'amount_due',
            'currency__code', 'contact__city', 'contact__country'
        )
        
        if invoices.exists():
            df_invoices = pd.DataFrame(list(invoices))
            df_invoices.columns = [
                'invoice_id', 'invoice_number', 'company_name', 'contact_name',
                'issue_date', 'due_date', 'status', 'subtotal', 'tax_amount',
                'discount_amount', 'total', 'amount_paid', 'amount_due', 'currency',
                'city', 'country'
            ]
            # Convert to datetime and extract time components
            df_invoices['issue_date'] = pd.to_datetime(df_invoices['issue_date'])
            df_invoices['year'] = df_invoices['issue_date'].dt.year
            df_invoices['month'] = df_invoices['issue_date'].dt.month
            df_invoices['month_name'] = df_invoices['issue_date'].dt.strftime('%B')
            df_invoices['quarter'] = df_invoices['issue_date'].dt.quarter
            
            # Convert Decimal to float for analysis
            numeric_cols = ['subtotal', 'tax_amount', 'discount_amount', 'total', 'amount_paid', 'amount_due']
            for col in numeric_cols:
                df_invoices[col] = df_invoices[col].astype(float)
        else:
            df_invoices = pd.DataFrame()
        
        # Load Invoice Lines (Product/Service Details) / 載入發票明細
        lines = InvoiceLine.objects.filter(invoice__invoice_type='SALES').values(
            'id', 'invoice__invoice_number', 'description', 'quantity', 
            'unit_price', 'tax_amount', 'discount_amount', 'line_total',
            'account__name', 'invoice__issue_date', 'invoice__contact__company_name'
        )
        
        if lines.exists():
            df_lines = pd.DataFrame(list(lines))
            df_lines.columns = [
                'line_id', 'invoice_number', 'product', 'quantity',
                'unit_price', 'tax_amount', 'discount_amount', 'line_total', 
                'category', 'date', 'customer'
            ]
            # Convert to proper types
            df_lines['date'] = pd.to_datetime(df_lines['date'])
            df_lines['year'] = df_lines['date'].dt.year
            df_lines['month'] = df_lines['date'].dt.month
            numeric_cols = ['quantity', 'unit_price', 'tax_amount', 'discount_amount', 'line_total']
            for col in numeric_cols:
                df_lines[col] = df_lines[col].astype(float)
        else:
            df_lines = pd.DataFrame()
        
        # Load Contacts (Customers) / 載入客戶資料
        contacts = Contact.objects.filter(contact_type__in=['CUSTOMER', 'BOTH']).values(
            'id', 'contact_type', 'company_name', 'contact_name', 'email',
            'city', 'state', 'country', 'payment_terms', 'credit_limit'
        )
        
        if contacts.exists():
            df_contacts = pd.DataFrame(list(contacts))
            df_contacts.columns = [
                'customer_id', 'contact_type', 'company_name', 'contact_name', 
                'email', 'city', 'state', 'country', 'payment_terms', 'credit_limit'
            ]
            df_contacts['credit_limit'] = df_contacts['credit_limit'].astype(float)
        else:
            df_contacts = pd.DataFrame()
        
        # Store in cache - use invoice lines as primary analysis data for more detail
        if not df_lines.empty:
            dataframe_cache["analysis_data"] = df_lines
            dataframe_cache["invoices"] = df_invoices
            dataframe_cache["customers"] = df_contacts
            
            return {
                "message": "Database data loaded successfully / 資料庫數據載入成功",
                "rows": {
                    "sales_data": len(df_lines),
                    "invoices": len(df_invoices),
                    "customers": len(df_contacts),
                },
                "columns": df_lines.columns.tolist()
            }
        elif not df_invoices.empty:
            # Fallback to invoices if no lines
            dataframe_cache["analysis_data"] = df_invoices
            dataframe_cache["customers"] = df_contacts
            
            return {
                "message": "Invoice data loaded (no line items) / 發票數據已載入（無明細）",
                "rows": {
                    "invoices": len(df_invoices),
                    "customers": len(df_contacts),
                },
                "columns": df_invoices.columns.tolist()
            }
        else:
            # No data in database, try CSV fallback
            try:
                dataframe_cache["analysis_data"] = pd.read_csv("ai_assistants/data/analysis_data.csv")
                return {
                    "message": "CSV fallback data loaded (no database data) / CSV 備用數據已載入",
                    "rows": {
                        "analysis_data": len(dataframe_cache["analysis_data"]),
                    },
                    "columns": dataframe_cache["analysis_data"].columns.tolist()
                }
            except Exception:
                dataframe_cache["analysis_data"] = pd.DataFrame()
                return {
                    "message": "No data available. Please generate sample data. / 沒有可用數據，請生成範例數據。",
                    "rows": {},
                    "empty": True
                }

    except Exception as e:
        raise RuntimeError(f"Failed to load datasets: {e}")


def handle_query_logic(query: str) -> dict:
    """Handle user query and generate response / 處理用戶查詢並生成回應"""
    df = dataframe_cache.get("analysis_data")
    if df is None or df.empty:
        return {
            "type": "error", 
            "message": "No analysis data found. Please call /start first or generate sample data. / 找不到分析數據，請先呼叫 /start 或生成範例數據。"
        }
    
    try:
        query_type = classify_analysis_query(query, df.columns.tolist())
    except Exception as e:
        return {"type": "error", "message": f"Error classifying query: {e}"}

    if query_type == "DATA_ANALYSIS":
        response_obj = generate_response(query, df, query_type)
        try:
            result = eval(response_obj["code"], {"df": df, "pd": pd})
            
            # Handle different result types
            if isinstance(result, pd.DataFrame):
                data = result.to_dict(orient="records")
            elif isinstance(result, pd.Series):
                data = result.reset_index().to_dict(orient="records")
            elif np.isscalar(result) or isinstance(result, (int, float, str)):
                data = [{"Result": result}]
            else:
                data = [{"Result": str(result)}]
                
            return {"type": "table", "data": data}
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
        message = response_obj.get("code", "I can't answer that query with the available data. / 無法用現有數據回答該問題。")
        return {"type": "invalid", "message": message}


def generate_response(query, data: pd.DataFrame, query_type: str):
    """Generate AI response based on query type / 根據查詢類型生成 AI 回應"""
    if query_type == "DATA_ANALYSIS":
        prompt = get_data_manipulation_prompt()
    elif query_type == "GRAPH":
        prompt = get_data_visualization_prompt()
    else:
        prompt = get_invalid_query_prompt()

    columns = ", ".join(data.columns)
    sample_data = data.head(5).to_string()
    data_info = f"""
Dataset Columns: {columns}
Sample Data:
{sample_data}
Data Types: {data.dtypes.to_string()}
Total Rows: {len(data)}
"""
    prompt += f"\n{data_info}\nQuery: \"{query}\"\nProvide only the correct response in JSON format."
    
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
    """Convert Plotly figure to Recharts-compatible format / 將 Plotly 圖表轉換為 Recharts 格式"""
    try:
        chart_data = fig_dict.get("data", [])[0]
        chart_type = chart_data.get("type")
        title = fig_dict.get("layout", {}).get("title", {}).get("text", "Analysis Result / 分析結果")

        def decode_y(y_obj):
            if isinstance(y_obj, dict) and "bdata" in y_obj and "dtype" in y_obj:
                dtype = y_obj["dtype"]
                bdata = base64.b64decode(y_obj["bdata"])
                return np.frombuffer(bdata, dtype=dtype).tolist()
            return y_obj

        if chart_type == "pie":
            labels = chart_data.get("labels", [])
            values = chart_data.get("values", [])
            if values:
                data = [{"label": label, "value": value} for label, value in zip(labels, values)]
            else:
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
            return {
                "type": "unsupported", 
                "message": f"Chart type '{chart_type}' is not supported. / 不支援的圖表類型。",
                "original": fig_dict
            }

    except Exception as e:
        return {"type": "error", "message": f"Error converting chart: {e}"}
