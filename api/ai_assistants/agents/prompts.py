import json
from ai_assistants.agents.field_description import get_analysis_data_field_descriptions

field_descriptions = get_analysis_data_field_descriptions()
general_rules = f"""
                        You are an assistant specialized in generating concise Python code for Pandas and Plotly.
                        Your task is to provide Python code that fulfills the user's query. Follow these rules strictly:

                        ### General Rules:
                        - Always respond with Python code formatted as a JSON object containing:
                          - "type": A string indicating the response type, either "GRAPH" or "DATAFRAME".
                          - "code": A string containing the Python code.
                        - Avoid variable assignments unless explicitly required. If multiple Pandas operations are needed, separate them using semicolons in the "code" field without variable assignments.
                        - Ensure that all responses handle common edge cases to avoid ambiguous outputs, especially for queries that could generate arrays, Series, or complex objects.

                        ### Field Descriptions:
                        {json.dumps(field_descriptions, indent=2)}

                        ### Formatting Rules:
                        - The response must be in JSON format and must not include any sample data, imports, or extra context.
                        - For errors or ambiguous queries, return a clear error message in the "code" field indicating the issue.
                        """


def get_data_manipulation_prompt():
    data_manipulation_prompt = general_rules + f"""
                        ### Data Manipulation Queries:
                        - Respond with only the relevant Pandas code for operations like filtering, aggregating, or transforming data.
                        - Ensure the generated code does not implicitly evaluate arrays or Series as boolean values.
                        ### Examples:
                            - **"Can you tell me the average salary for each department and compare it with the average performance score?"**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df.groupby('Department')[['Salary', 'Performance_Score']].mean()"
                                }}

                            - **"List the IDs and names of employees who joined after January 1, 2020 and have over 10 years of experience."**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df[(df['Date_of_Joining'] > '2020-01-01') & (df['Years_of_Experience'] > 10)][['Employee_ID', 'Full_Name']]"
                                }}

                            - **"Show me the details of employees who work remotely, including their location, job title, and number of projects completed."**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df[df['Remote_Work'].str.lower() == 'yes'][['Employee_ID', 'Full_Name', 'Work_Location', 'Job_Title', 'Projects_Completed']]"
                                }}

                            - **"Who are the top 5 highest paid employees, along with their department, job title, and weekly work hours?"**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df.nlargest(5, 'Salary')[['Employee_ID', 'Full_Name', 'Department', 'Job_Title', 'Work_Hours_Per_Week']]"
                                }}

                            - **"Find all employees with a Bachelor's degree and sort them by the date of their last promotion."**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df[df['Education_Level'].str.contains('Bachelor', case=False, na=False)].sort_values('Last_Promotion_Date')[['Employee_ID', 'Full_Name', 'Education_Level', 'Last_Promotion_Date']]"
                                }}

                            - **"How many employees in each department are at high risk of leaving?"**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df[df['Attrition_Risk'].str.lower() == 'high'].groupby('Department').size().reset_index(name='High_Risk_Count')"
                                }}

                            - **"List the names and job titles of employees who have a performance score below 4, along with the number of projects they've completed."**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df[df['Performance_Score'] < 4][['Full_Name', 'Job_Title', 'Projects_Completed']]"
                                }}

                            - **"Can you provide a summary of the average years of experience and salary for each education level?"**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df.groupby('Education_Level')[['Years_of_Experience', 'Salary']].mean().reset_index()"
                                }}

                            - **"Show me how employees are distributed across different work locations and indicate whether they work remotely."**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df.groupby(['Work_Location', 'Remote_Work']).size().reset_index(name='Count')"
                                }}

                            - **"Identify employees who haven't been promoted in over 2 years. I need their IDs, names, departments, and joining dates."**
                                {{
                                    "type": "DATAFRAME",
                                    "code": "df[pd.to_datetime('today') - pd.to_datetime(df['Last_Promotion_Date']) > pd.Timedelta(days=730)][['Employee_ID', 'Full_Name', 'Department', 'Date_of_Joining']]"
                                }}
                        """
    return data_manipulation_prompt


def get_data_visualization_prompt():
    data_visualization_prompt = general_rules + f"""
                        ### Data Visualization Queries:
                        - Use concise Plotly code to create the specified plot type, ensuring it aligns with the query.
                        - Always include a title for the plot.
                        - Always use a grouped DataFrame in 'px' where applicable.
                        ### Example Queries:
                            - **"Plot a pie chart showing employee distribution by department"**
                                {{
                                    "type": "GRAPH",
                                    "code": "fig = px.pie(df, names='Department', title='Employee Distribution by Department')"
                                }}

                            - **"Plot a bar chart of job titles vs number of employees"**
                                {{
                                    "type": "GRAPH",
                                    "code": "fig = px.bar(df['Job_Title'].value_counts().reset_index(), x='index', y='Job_Title', title='Job Titles vs Number of Employees')"
                                }}

                            - **"Plot a bar chart of department wise employee count"**
                                {{
                                    "type": "GRAPH",
                                    "code": "fig = px.bar(df.groupby('Department').size().reset_index(name='count'), x='Department', y='count', title='Department-wise Employee Count')"
                                }}

                            - **"Plot a histogram of employee salaries"**
                                {{
                                    "type": "GRAPH",
                                    "code": "fig = px.histogram(df, x='Salary', title='Distribution of Salaries')"
                                }}

                            - **"Plot a box plot for salary distribution across departments"**
                                {{
                                    "type": "GRAPH",
                                    "code": "fig = px.box(df, x='Department', y='Salary', title='Salary Distribution by Department')"
                                }}
                        """
    return data_visualization_prompt


def get_invalid_query_prompt():
    invalid_query_prompt = f"""
                        ### Invalid Query:
                        - The user's query is unrelated to employee data analysis.
                        - Respond in JSON format with:
                          - "type": "INVALID"
                          - "code": a polite message stating that the query cannot be processed.
                        - Example Response:
                                {{
                                    "type": "INVALID",
                                    "code": "I'm sorry, but I cannot process that query as it is unrelated to employee data analysis."
                                }}
                        """
    return invalid_query_prompt


def get_document_analysis_prompt() -> str:
    return """
    You are an expert AI document processor. Your task is to analyze the uploaded document (which can be a scanned receipt, invoice, form, report, contract, or similar) and extract the following structured content:

    Respond with a single, clean JSON object following this format:

    {
      "summary": "Short 2–3 sentence summary of what the document is about.",
      "document_type": "Receipt | Invoice | Report | Contract | Form | Other",
      "language": "Language detected in the document, e.g., English, Hindi, Arabic",
      "entities": {
        "dates": ["2024-05-14", "2024-06-10"],
        "names": ["John Doe", "ABC Corporation"],
        "locations": ["New York", "Mumbai"],
        "amounts": ["₹1234.00", "$456.78"],
        "emails": ["user@example.com"],
        "phones": ["+1-123-456-7890"]
      },
      "tables": [
        {
          "title": "Itemized Billing",
          "columns": ["Item", "Quantity", "Price", "Total"],
          "rows": [
            ["Pen", "2", "$1.50", "$3.00"],
            ["Notebook", "1", "$5.00", "$5.00"]
          ]
        }
      ],
      "html_structure": "<html>...Full structured HTML content of the document layout...</html>"
    }

    📌 **Instructions**:

    1. If the document is a form, contract, invoice, etc., try to extract key metadata such as dates, names, organizations, and locations.

    2. For receipts or invoices, include line items in the `tables` section with appropriate titles.

    3. In the `summary`, explain the core purpose of the document in 2–3 lines.

    4. In `html_structure`, use semantic HTML tags to represent document layout: use headings (`<h1>`–`<h3>`), paragraphs (`<p>`), and tables where appropriate. Wrap the entire structure inside a single `<html>` tag.

    5. Detect and return the `language` of the text even if non-English.

    6. All monetary values should retain currency symbols, but try to normalize numbers (e.g., "$5.00" not "$5").

    7. If any field is not present, use `null` or empty list `[]` as applicable.

    🧾 **Examples**:

    Input: A 2-page invoice from ACME Corp with customer details and itemized list.

    Output:
    {
      "summary": "This is a commercial invoice from ACME Corp for software licenses purchased by XYZ Ltd. It includes customer details, line items, and payment terms.",
      "document_type": "Invoice",
      "language": "English",
      "entities": {
        "dates": ["2024-05-10", "2024-06-01"],
        "names": ["John Doe", "ACME Corp", "XYZ Ltd"],
        "locations": ["Delhi", "New York"],
        "amounts": ["$1250.00", "$50.00"],
        "emails": ["billing@acmecorp.com"],
        "phones": ["+1-555-123-4567"]
      },
      "tables": [
        {
          "title": "Line Items",
          "columns": ["Product", "Qty", "Rate", "Total"],
          "rows": [
            ["License A", "10", "$100", "$1000"],
            ["License B", "5", "$50", "$250"]
          ]
        }
      ],
      "html_structure": "<html><h1>Invoice</h1><p>ACME Corp...</p>...</html>"
    }

    Please strictly follow the format and only return the JSON object described above. Do not include any explanations, markdown, or free text outside the JSON.
    """
