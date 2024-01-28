from data_processing import *
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import pandas as pd
from sqlalchemy import create_engine
import os

def create_report(df):
    print("Generating report...")

    # Your data processing functions
    multiples = get_multiples(df[['deal_type', 'deal_type_2', 'valuation_by_revenue']])
    revenue = get_revenue(df[['deal_type', 'deal_type_2', 'revenue']])
    deal_size = get_deal_size(df[['deal_type', 'deal_type_2', 'deal_size']])
    valuation = get_valuation(df[['deal_type', 'deal_type_2', 'post_valuation']])
    # Additional data processing functions...

    file_path = "report.pdf"
    pdf = SimpleDocTemplate(file_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Add a title
    elements.append(Paragraph("Startup Funding Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Add some introductory text
    intro_text = (
        "This report showcases the funding trajectory of various startups. "
        "Here are some insights and visualizations based on the data."
    )
    elements.append(Paragraph(intro_text, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Add your data processing results as paragraphs
    elements.append(Paragraph("Median Valuation by Revenue:", styles['Heading2']))
    elements.append(Paragraph(multiples[0].to_string(), styles['Normal']))
    elements.append(Paragraph(multiples[1].to_string(), styles['Normal']))

    elements.append(Paragraph("Median Revenue:", styles['Heading2']))
    elements.append(Paragraph(revenue[0].to_string(), styles['Normal']))
    elements.append(Paragraph(revenue[1].to_string(), styles['Normal']))

    # Additional data results...

    # Build the PDF
    pdf.build(elements)

    print("Report successfully generated")

# Your main function remains unchanged

def main():
    table_name = 'deals'
    source_file = 'test_1'
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("Database connection string not found in environment variables")

    try:
        engine = create_engine(db_url)
        query = f"SELECT * FROM {table_name} where source_file='{source_file}'"
        df = pd.read_sql_query(query, engine)

        create_report(df)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

