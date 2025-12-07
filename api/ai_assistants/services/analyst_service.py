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
from uuid import UUID
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


def convert_uuid_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert UUID columns to strings to avoid aggregation errors / 將 UUID 欄位轉換為字串以避免聚合錯誤"""
    for col in df.columns:
        try:
            # Check if column contains UUID objects
            if df[col].dtype == 'object' and len(df[col]) > 0:
                first_non_null = df[col].dropna().head(1)
                if len(first_non_null) > 0 and isinstance(first_non_null.iloc[0], UUID):
                    df[col] = df[col].astype(str)
            # Also handle columns that might have UUID as string representation
            elif col.endswith('_id') or col == 'id':
                # Force ID columns to be strings
                df[col] = df[col].astype(str)
        except Exception:
            # If conversion fails, try to convert to string anyway for ID-like columns
            if col.endswith('_id') or col == 'id':
                try:
                    df[col] = df[col].astype(str)
                except Exception:
                    pass
    return df


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
            # Convert UUID columns to strings
            convert_uuid_columns(df_lines)
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
            # Convert UUID columns to strings
            convert_uuid_columns(df_contacts)
            df_contacts['credit_limit'] = df_contacts['credit_limit'].astype(float)
        else:
            df_contacts = pd.DataFrame()
        
        # Convert UUIDs in invoices as well
        if not df_invoices.empty:
            convert_uuid_columns(df_invoices)
        
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
    
    # Auto-load data if not available / 如果數據不可用則自動載入
    if df is None or df.empty:
        try:
            load_result = load_all_datasets()
            if load_result.get("empty"):
                return {
                    "type": "error", 
                    "message": "No analysis data found. Please call /start first or generate sample data. / 找不到分析數據，請先呼叫 /start 或生成範例數據。"
                }
            df = dataframe_cache.get("analysis_data")
            if df is None or df.empty:
                return {
                    "type": "error", 
                    "message": "Failed to auto-load data. Please try refreshing the page. / 自動載入數據失敗，請嘗試刷新頁面。"
                }
        except Exception as load_error:
            return {
                "type": "error", 
                "message": f"No analysis data found and auto-load failed: {load_error} / 找不到分析數據且自動載入失敗"
            }
    
    try:
        query_type = classify_analysis_query(query, df.columns.tolist())
    except Exception as e:
        # If classification fails, treat as general chat
        query_type = "CHAT"

    # Check if user explicitly asks for a chart
    chart_keywords = ['chart', 'graph', 'plot', 'pie', 'bar', 'line', 'scatter', '圖表', '圖', '餅圖', '柱狀圖', '折線圖', 'visualization', 'visualize']
    query_lower = query.lower()
    wants_chart = any(kw in query_lower for kw in chart_keywords)
    
    # If user wants a chart but query_type is not GRAPH, force it
    if wants_chart and query_type not in ["GRAPH"]:
        query_type = "GRAPH"

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
            result = convert_plotly_to_recharts_format(fig_dict)
            
            # Add a message explaining the chart
            if result.get("type") not in ["error", "unsupported"]:
                result["message"] = f"Here's the analysis for \"{query}\":\n\n**{result.get('title', 'Analysis Result')}**"
            
            return result
        except Exception as e:
            # If graph generation fails, try to provide a helpful error with data summary
            return {
                "type": "error", 
                "message": f"Error generating chart: {e}\n\n**Available columns:** {', '.join(df.columns.tolist())}\n\nTry specifying the exact column names in your query."
            }

    elif query_type == "CHAT":
        # General conversation - multimodal support
        response_obj = generate_chat_response(query, df)
        return response_obj

    else:
        # INVALID or unknown - try chat response
        response_obj = generate_chat_response(query, df)
        return response_obj


def generate_chat_response(query: str, data: pd.DataFrame) -> dict:
    """Generate a general chat response - multimodal AI conversation / 生成一般對話回應 - 多模態 AI 對話"""
    try:
        columns = ", ".join(data.columns) if not data.empty else "No data"
        row_count = len(data) if not data.empty else 0
        
        # Get sample data for context
        sample_data = ""
        if not data.empty:
            sample_data = f"\n\n範例數據 (前5行):\n{data.head(5).to_string()}"
        
        system_prompt = f"""你是一個友善的 AI 數據分析助手。你可以:
1. 回答關於數據分析的問題
2. 解釋圖表和統計概念
3. 提供數據洞察建議
4. 進行一般性對話

當前數據集:
- 欄位: {columns}
- 行數: {row_count}
{sample_data}

請用中文或英文回答（根據用戶的語言）。
如果用戶問的是關於數據的問題，盡量提供有用的分析建議。
如果用戶要求圖表但你無法生成，請建議他們使用更具體的查詢。
如果是一般對話，請友善回應。
支持 Markdown 格式，包括：
- **粗體** 和 *斜體*
- 列表和編號
- `代碼` 和代碼塊
- 表格等"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return {"type": "text", "message": content}
        
    except Exception as e:
        return {"type": "error", "message": f"Chat error: {e}"}


def generate_response(query, data: pd.DataFrame, query_type: str):
    """Generate AI response based on query type / 根據查詢類型生成 AI 回應"""
    if query_type == "DATA_ANALYSIS":
        prompt = get_data_manipulation_prompt()
    elif query_type == "GRAPH":
        prompt = get_data_visualization_prompt()
    elif query_type == "CHAT":
        # General chat/conversation - multimodal support
        return generate_chat_response(query, data)
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
        response_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # If JSON parsing fails, return as chat response
            return {"type": "CHAT", "code": response_text}
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
