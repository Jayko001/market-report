import psycopg2
import pandas as pd
from psycopg2.extensions import AsIs
import os

# Function to replace NaT/NaN with None
def replace_nan_nat_with_none(value):
    if pd.isnull(value) or value is None:
        return 'NaT'
    return value

def main():

     # Load the Excel file into a DataFrame
    excel_file_path = 'tests/test_data_2.xlsx'  # Replace with the path to your Excel file
    df = pd.read_excel(excel_file_path)

    df = df.applymap(lambda x: None if pd.isna(x) else x)
    df = df.applymap(replace_nan_nat_with_none)

    # Add an additional column for the Excel file identifier
    excel_file_identifier = 'test_1'  # Replace with your identifier (e.g., filename)
    df['source_file'] = excel_file_identifier

     # Clean up column names: replace spaces and periods with underscores
    df.columns = [col.replace(' ', '_',).replace('.', '_').replace('%','percent').replace('(','').replace(')','').replace(',','')
    .replace('-','_').replace('/','_by_').replace('#','number').replace('&','and') for col in df.columns]

    # Connection string
    conn_str = os.getenv('DATABASE_URL')
    if not conn_str:
        raise ValueError("Database connection string not found in environment variables")

    try:
        # Create a new database session
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()

        # Check if the table already exists
        table_name = 'deals'
        cur.execute("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = %s);", (table_name,))
        result = cur.fetchone()
        table_exists = result[0] if result else False

        if not table_exists:
            # Construct the column definitions for the CREATE TABLE statement
            column_definitions = ", ".join([f"{col} TEXT" for col in df.columns])
            create_table_statement = f"CREATE TABLE {table_name} ({column_definitions})"
            cur.execute(create_table_statement)
            conn.commit()
            print(f"Table {table_name} created")

        # Inserting data into the table
        column_names = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_statement = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        for _, row in df.iterrows():
            cur.execute(insert_statement, tuple(row))
 
        conn.commit()
        print("Data successfully inserted into the database")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close communication with the database
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    main()