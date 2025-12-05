from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def classify_analysis_query(query: str, data_columns: list[str]) -> str:
    print(f"Query: {query}")
    print(f"Data Columns: {data_columns}")

    prompt = f"""
You are a query classifier for an employee data analysis system. The dataset contains the following columns: {', '.join(data_columns)}.
Your task is to classify the user's query into one of these categories:

1. DATA_ANALYSIS – For queries that require data filtering, sorting, aggregation, or any analysis using the available columns.
   - Examples:
     • "Show me employees in the Sales department."
     • "List employees with more than 5 years of experience."
     • "What is the average salary by department?"

2. GRAPH – For queries that request a chart, visualization, or graph using Plotly, based on the provided data columns.
   - Examples:
     • "Plot a bar chart of Salary by Department."
     • "Create a scatter plot of Performance_Score versus Years_of_Experience."
     • "Show me a pie chart of Remote_Work distribution."

3. INVALID – For queries that are unrelated to the available data or cannot be answered with the provided columns.
   - Examples:
     • "What is the weather forecast for tomorrow?"
     • "Show me customer reviews."
     • "How many apples are in a basket?"

Now, classify the following query into one of these categories:
"{query}"

Return your classification as a single word: DATA_ANALYSIS, GRAPH, or INVALID.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        classification = response.choices[0].message.content.strip().upper()
        valid_classifications = {"DATA_ANALYSIS", "GRAPH", "INVALID"}
        return classification if classification in valid_classifications else "INVALID"

    except Exception as e:
        print(f"[Query Classifier] Error: {e}")
        return "INVALID"


def classify_planner_query(query: str, data_columns: list[str]) -> str:
    print(f"Query: {query}")
    print(f"Data Columns: {data_columns}")

    prompt = f"""
You are a query classifier for a task and event planning system. The dataset contains the following columns: {', '.join(data_columns)}.
Your task is to classify the user's query into one of these categories:

1. DATA_ANALYSIS – For queries that require data filtering, sorting, aggregation, or any analysis using the available columns.
   - Examples:
     • "List all high priority events."
     • "Show all completed tasks assigned to John."
     • "How many meetings are scheduled for next week?"

2. GRAPH – For queries that request a chart, visualization, or graph using Plotly, based on the provided data columns.
   - Examples:
     • "Plot a pie chart of events by status."
     • "Show a bar chart of events per participant."
     • "Visualize priority distribution."

3. INVALID – For queries that are unrelated to the available data or cannot be answered with the provided columns.
   - Examples:
     • "What is the best productivity app?"
     • "Play a motivational video."
     • "Send an email reminder."

Now, classify the following query into one of these categories:
"{query}"

Return your classification as a single word: DATA_ANALYSIS, GRAPH, or INVALID.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        classification = response.choices[0].message.content.strip().upper()
        valid_classifications = {"DATA_ANALYSIS", "GRAPH", "INVALID"}
        return classification if classification in valid_classifications else "INVALID"

    except Exception as e:
        print(f"[Planner Query Classifier] Error: {e}")
        return "INVALID"
