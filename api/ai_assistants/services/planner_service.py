import json
import base64
import numpy as np
import pandas as pd
import plotly.express as px
from openai import OpenAI
from collections import Counter
from django.conf import settings
from ai_assistants.agents.query_classifier_agent import classify_planner_query
from ai_assistants.agents.prompts import (
    get_data_manipulation_prompt,
    get_data_visualization_prompt,
    get_invalid_query_prompt
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
dataframe_cache = {}


def load_all_datasets():
    try:
        dataframe_cache["planner_data"] = pd.read_csv("ai_assistants/data/planner_data.csv")

        return {
            "message": "Planner dataset loaded successfully",
            "rows": {
                "planner_data": len(dataframe_cache["planner_data"]),
            }
        }

    except Exception as e:
        raise RuntimeError(f"Failed to load datasets: {e}")


def handle_query_logic(query: str) -> dict:
    df = dataframe_cache.get("planner_data")
    if df is None:
        return {"type": "error", "message": "No planner data found. Please call /start first."}

    try:
        query_type = classify_planner_query(query, df.columns.tolist())
    except Exception as e:
        return {"type": "error", "message": f"Error classifying query: {e}"}

    if query_type == "DATA_ANALYSIS":
        response_obj = generate_response(query, df, query_type)
        try:
            result = eval(response_obj["code"], {"df": df, "pd": pd})
            # Handle non-JSON-compliant float values
            result_copy = result.copy()
            # Replace infinite values with None
            result_copy = result_copy.replace([float('inf'), float('-inf')], None)
            # Replace NaN values with None
            result_copy = result_copy.replace({pd.NA: None, np.nan: None})
            return {"type": "table", "data": result_copy.to_dict(orient="records")}
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
        message = response_obj.get("code", "I can't answer that query with the available data.")
        return {"type": "invalid", "message": message}


def generate_response(query, data: pd.DataFrame, query_type: str):
    if query_type == "DATA_ANALYSIS":
        prompt = get_data_manipulation_prompt()
    elif query_type == "GRAPH":
        prompt = get_data_visualization_prompt()
    else:
        prompt = get_invalid_query_prompt()

    columns = ", ".join(data.columns)
    prompt += f"\nDataset Columns: {columns}\nQuery: \"{query}\"\nProvide only the correct response in JSON format."

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
            values = chart_data.get("values", [])

            # If values are provided, use them instead of counting labels
            if values:
                # Handle non-JSON-compliant float values in values array
                processed_values = []
                for v in values:
                    # Replace infinite and NaN values with None
                    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                        v = None
                    processed_values.append(v)

                # Create data with labels and processed values, skipping None values
                data = [{"label": label, "value": value}
                        for label, value in zip(labels, processed_values)
                        if value is not None]
            else:
                # Use label counts as before
                label_counts = Counter(labels)
                data = [{"label": label, "value": count} for label, count in label_counts.items()]

            return {"type": "pie", "title": title, "data": data, "labelKey": "label", "valueKey": "value"}

        elif chart_type in ["bar", "scatter", "line"]:
            x_values = chart_data.get("x", [])
            y_raw = chart_data.get("y", [])
            y_values = decode_y(y_raw)

            # Handle non-JSON-compliant float values in x and y arrays
            processed_x = []
            processed_y = []
            for x, y in zip(x_values, y_values):
                # Replace infinite and NaN values with None
                if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
                    x = None
                if isinstance(y, float) and (np.isnan(y) or np.isinf(y)):
                    y = None
                processed_x.append(x)
                processed_y.append(y)

            data = [{"x": x, "y": y} for x, y in zip(processed_x, processed_y) if x is not None and y is not None]
            return {"type": chart_type, "title": title, "data": data, "xKey": "x", "yKey": "y"}

        else:
            return {"type": "unsupported", "message": f"Chart type '{chart_type}' is not supported.",
                    "original": fig_dict}

    except Exception as e:
        return {"type": "error", "message": f"Error converting chart: {e}"}
