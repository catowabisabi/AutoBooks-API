import json
import base64
import logging
import numpy as np
import pandas as pd
import plotly.express as px
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI
from collections import Counter
from django.conf import settings
from django.utils import timezone
from ai_assistants.agents.query_classifier_agent import classify_planner_query
from ai_assistants.agents.prompts import (
    get_data_manipulation_prompt,
    get_data_visualization_prompt,
    get_invalid_query_prompt
)

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)
dataframe_cache = {}


# =================================================================
# AI Task Creation Service
# =================================================================

def get_task_creation_prompt() -> str:
    """Prompt for AI to extract tasks from free-form input"""
    return """You are an expert task planner for an accounting and audit firm ERP system.
Your job is to analyze user input (which may be notes, emails, meeting minutes, or general text) 
and extract actionable tasks.

For each task identified, provide:
1. title: Clear, actionable task title (max 100 chars)
2. description: Detailed description with context
3. priority: One of LOW, MEDIUM, HIGH, CRITICAL
4. estimated_hours: Estimated hours to complete (float)
5. suggested_deadline_days: Days from now to complete (integer)
6. category: One of AUDIT, TAX, IPO, FINANCIAL_PR, COMPLIANCE, MEETING, REPORT, CLIENT, INTERNAL, OTHER
7. tags: List of relevant tags
8. reasoning: Brief explanation of why this task is important

Respond ONLY with a valid JSON object in this exact format:
{
  "tasks": [
    {
      "title": "...",
      "description": "...",
      "priority": "MEDIUM",
      "estimated_hours": 2.0,
      "suggested_deadline_days": 7,
      "category": "AUDIT",
      "tags": ["audit", "client"],
      "reasoning": "..."
    }
  ],
  "summary": "Brief summary of all extracted tasks"
}

If no actionable tasks can be identified, return:
{
  "tasks": [],
  "summary": "No actionable tasks found in the input."
}
"""


def ai_parse_tasks_from_text(input_text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Use LLM to parse free-form text into structured tasks.
    
    Args:
        input_text: Free-form text containing task descriptions
        context: Optional context like source_email_id, project info
        
    Returns:
        Dictionary with 'tasks' list and 'summary'
    """
    try:
        system_prompt = get_task_creation_prompt()
        
        user_message = f"""Please analyze the following input and extract actionable tasks:

---
{input_text}
---

Additional context: {json.dumps(context or {}, ensure_ascii=False)}

Extract all tasks and provide the JSON response."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info(f"[AI Task Parser] Extracted {len(result.get('tasks', []))} tasks")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[AI Task Parser] JSON decode error: {e}")
        return {"tasks": [], "summary": f"Error parsing response: {e}"}
    except Exception as e:
        logger.error(f"[AI Task Parser] Error: {e}")
        return {"tasks": [], "summary": f"Error: {e}"}


def calculate_ai_priority_score(task_data: Dict) -> float:
    """
    Calculate AI priority score (0-100) based on task attributes.
    """
    score = 50.0  # Base score
    
    # Priority weight
    priority_weights = {
        'CRITICAL': 40,
        'HIGH': 25,
        'MEDIUM': 10,
        'LOW': -10
    }
    score += priority_weights.get(task_data.get('priority', 'MEDIUM'), 0)
    
    # Deadline urgency
    deadline_days = task_data.get('suggested_deadline_days', 14)
    if deadline_days <= 1:
        score += 20
    elif deadline_days <= 3:
        score += 15
    elif deadline_days <= 7:
        score += 10
    elif deadline_days > 30:
        score -= 5
    
    # Category weight (accounting-specific priorities)
    category_weights = {
        'AUDIT': 10,
        'TAX': 10,
        'COMPLIANCE': 15,
        'IPO': 12,
        'CLIENT': 8,
        'FINANCIAL_PR': 5,
        'MEETING': 3,
        'REPORT': 5,
        'INTERNAL': 0,
        'OTHER': 0
    }
    score += category_weights.get(task_data.get('category', 'OTHER'), 0)
    
    return max(0, min(100, score))


# =================================================================
# AI Reprioritization Service
# =================================================================

def get_reprioritize_prompt() -> str:
    """Prompt for AI to reprioritize tasks"""
    return """You are an expert task prioritization assistant for an accounting firm.
Your job is to analyze a list of tasks and provide optimal priority scores and reasoning.

Consider these factors when prioritizing:
1. Due dates and urgency (overdue tasks get highest priority)
2. Task priority level (CRITICAL > HIGH > MEDIUM > LOW)
3. Business impact (client-facing > internal)
4. Dependencies (tasks blocking others should be higher)
5. Workload balance (avoid overloading)

Respond ONLY with a valid JSON object:
{
  "reprioritized_tasks": [
    {
      "task_id": "uuid-here",
      "new_score": 85.0,
      "reasoning": "High priority client task due tomorrow"
    }
  ],
  "summary": "Overall reprioritization summary",
  "recommendations": ["List of scheduling recommendations"]
}
"""


def ai_reprioritize_tasks(tasks: List[Dict], options: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Use LLM to intelligently reprioritize tasks.
    
    Args:
        tasks: List of task dictionaries with current status
        options: Optional settings like consider_deadlines, consider_dependencies
        
    Returns:
        Dictionary with reprioritized scores and reasoning
    """
    if not tasks:
        return {
            "reprioritized_tasks": [],
            "summary": "No tasks to reprioritize",
            "recommendations": []
        }
    
    try:
        system_prompt = get_reprioritize_prompt()
        
        # Prepare task summary for LLM
        today = datetime.now().date()
        task_summaries = []
        for task in tasks:
            due_date = task.get('due_date')
            days_until_due = None
            is_overdue = False
            if due_date:
                if isinstance(due_date, str):
                    due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                days_until_due = (due_date - today).days
                is_overdue = days_until_due < 0
            
            task_summaries.append({
                "task_id": str(task.get('id', '')),
                "title": task.get('title', ''),
                "priority": task.get('priority', 'MEDIUM'),
                "status": task.get('status', 'TODO'),
                "due_date": str(due_date) if due_date else None,
                "days_until_due": days_until_due,
                "is_overdue": is_overdue,
                "current_score": task.get('ai_priority_score', 50),
                "tags": task.get('tags', []),
            })
        
        user_message = f"""Please reprioritize the following tasks:

Tasks:
{json.dumps(task_summaries, indent=2, ensure_ascii=False)}

Options:
- Consider deadlines: {options.get('consider_deadlines', True) if options else True}
- Consider dependencies: {options.get('consider_dependencies', True) if options else True}

Today's date: {today}

Provide new priority scores (0-100) and reasoning for each task."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info(f"[AI Reprioritize] Processed {len(result.get('reprioritized_tasks', []))} tasks")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"[AI Reprioritize] JSON decode error: {e}")
        return {"reprioritized_tasks": [], "summary": f"Error: {e}", "recommendations": []}
    except Exception as e:
        logger.error(f"[AI Reprioritize] Error: {e}")
        return {"reprioritized_tasks": [], "summary": f"Error: {e}", "recommendations": []}


# =================================================================
# AI Schedule Suggestion Service
# =================================================================

def ai_suggest_schedule(tasks: List[Dict], available_hours_per_day: float = 8.0) -> Dict[str, Any]:
    """
    Use LLM to suggest an optimal schedule for tasks.
    
    Args:
        tasks: List of task dictionaries
        available_hours_per_day: Working hours per day
        
    Returns:
        Suggested schedule with task assignments per day
    """
    try:
        system_prompt = """You are a scheduling assistant for an accounting firm.
Create an optimal daily schedule for the given tasks, considering:
1. Due dates (don't schedule past due date)
2. Priority (higher priority tasks earlier)
3. Estimated hours (don't exceed daily capacity)
4. Buffer time for unexpected work

Respond with JSON:
{
  "schedule": [
    {
      "date": "2025-12-08",
      "tasks": [
        {"task_id": "...", "suggested_hours": 2.0, "time_slot": "morning"}
      ],
      "total_hours": 6.0
    }
  ],
  "unscheduled": ["task_ids that couldn't fit"],
  "warnings": ["Any scheduling conflicts or concerns"]
}
"""
        
        today = datetime.now().date()
        task_data = []
        for task in tasks:
            due = task.get('due_date')
            task_data.append({
                "task_id": str(task.get('id', '')),
                "title": task.get('title', ''),
                "estimated_hours": task.get('estimated_hours', 2.0),
                "priority": task.get('priority', 'MEDIUM'),
                "due_date": str(due) if due else None,
                "ai_score": task.get('ai_priority_score', 50),
            })
        
        user_message = f"""Schedule these tasks starting from {today}:

Tasks: {json.dumps(task_data, indent=2)}

Available hours per day: {available_hours_per_day}
Planning horizon: 14 days

Create an optimal schedule."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"[AI Schedule] Error: {e}")
        return {"schedule": [], "unscheduled": [], "warnings": [str(e)]}


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


# =================================================================
# Secure Code Execution
# =================================================================

# Whitelist of allowed operations for secure execution
ALLOWED_PANDAS_METHODS = {
    'groupby', 'filter', 'sort_values', 'head', 'tail', 'nlargest', 'nsmallest',
    'mean', 'sum', 'count', 'max', 'min', 'std', 'var', 'median',
    'reset_index', 'set_index', 'rename', 'drop', 'dropna', 'fillna',
    'value_counts', 'unique', 'nunique', 'describe',
    'merge', 'join', 'concat', 'pivot', 'pivot_table', 'melt',
    'to_dict', 'copy', 'size', 'agg', 'apply',
}

ALLOWED_BUILTINS = {
    'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple',
    'min', 'max', 'sum', 'abs', 'round', 'sorted', 'zip', 'enumerate',
}


def validate_code(code: str) -> bool:
    """
    Basic validation to check for dangerous patterns.
    Returns True if code appears safe, False otherwise.
    """
    dangerous_patterns = [
        'import ', 'from ', '__', 'exec', 'eval', 'compile',
        'open(', 'file(', 'input(', 'raw_input(',
        'os.', 'sys.', 'subprocess', 'shutil',
        'globals(', 'locals(', 'vars(',
        'getattr', 'setattr', 'delattr',
        'breakpoint', 'exit', 'quit',
    ]
    
    code_lower = code.lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in code_lower:
            logger.warning(f"[Secure Exec] Blocked dangerous pattern: {pattern}")
            return False
    
    return True


def safe_eval(code: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Safely evaluate pandas code with restricted namespace.
    """
    if not validate_code(code):
        raise ValueError("Code contains potentially dangerous operations")
    
    # Create restricted namespace
    safe_namespace = {
        'df': df,
        'pd': pd,
        'np': np,
        # Allow only safe builtins
        '__builtins__': {name: getattr(__builtins__, name) if hasattr(__builtins__, name) else __builtins__[name]
                        for name in ALLOWED_BUILTINS if hasattr(__builtins__, name) or (isinstance(__builtins__, dict) and name in __builtins__)},
    }
    
    try:
        result = eval(code, {"__builtins__": {}}, safe_namespace)
        return result
    except Exception as e:
        logger.error(f"[Safe Eval] Error: {e}")
        raise


def safe_exec_graph(code: str, df: pd.DataFrame) -> Any:
    """
    Safely execute plotly graph code with restricted namespace.
    """
    if not validate_code(code):
        raise ValueError("Code contains potentially dangerous operations")
    
    # Create restricted namespace
    safe_namespace = {
        'df': df,
        'pd': pd,
        'px': px,
        'np': np,
    }
    
    try:
        exec(code, {"__builtins__": {}}, safe_namespace)
        fig = safe_namespace.get("fig")
        if fig is None:
            raise ValueError("Graph variable 'fig' not found in code output")
        return fig
    except Exception as e:
        logger.error(f"[Safe Exec Graph] Error: {e}")
        raise


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
            # Use safe_eval instead of direct eval
            result = safe_eval(response_obj["code"], df)
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
            # Use safe_exec_graph instead of direct exec
            fig = safe_exec_graph(response_obj["code"], df)
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
