from docx import Document
from data_processing import extract_company_names, get_company_info
import os
import pandas as pd
from sqlalchemy import create_engine

def generate_document(company_name, competitors_info, output_file):
    try:
        doc = Document()
        doc.add_heading(f"Competitor Analysis for {company_name}", 0)  # Include company name

        for competitor, info in competitors_info.items():
            with doc.create_section() as section:
                section.add_heading(competitor, level=1)

                for key, value in info.items():
                    section.add_heading(key, level=2)
                    section.add_paragraph(value)

        doc.save(output_file)
        print(f"Document saved as {output_file}")

    except Exception as e:
        print(f"An error occurred during document generation: {e}")


def main():
    global company_names
    table_name = 'deals'
    source_file = 'test_1'
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("Database connection string not found in environment variables")

    try:
        engine = create_engine(db_url)
        query = f"SELECT * FROM {table_name} where source_file='{source_file}'"
        df = pd.read_sql_query(query, engine)

        company_name = "Perceive Now"
        # competitor_names = extract_company_names(df)
        competitor_names = ['Clarivate (NYS: CLVT)', 'Gartner (NYS: IT)', 'PatSnap']
        output_file = 'Competitor_Analysis.docx'
        competitors_info = get_company_info(company_name, competitor_names)
        generate_document(company_name, competitors_info, output_file)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

