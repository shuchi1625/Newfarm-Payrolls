import pandas as pd
from fredapi import Fred
import psycopg2
from io import StringIO

# --- Step 1: Extract ---
print("--- Starting ETL Pipeline ---")
print("Step 1: Extracting data from FRED...")
fred = Fred(api_key='3a0b97eb64a0392bcb8230eea70b3811')
series_id = 'PAYEMS'
df = fred.get_series(series_id)
jobs_df = pd.DataFrame(df, columns=['value']).reset_index().rename(columns={'index': 'date'})

# --- Step 2: Transform ---
print("Step 2: Transforming data (calculating MoM change)...")
jobs_df['change_pct'] = (jobs_df['value'].pct_change() * 100).round(2)
jobs_df['change_abs'] = jobs_df['value'].diff()
jobs_df.dropna(inplace=True)
jobs_df = jobs_df.rename(columns={
    'value': 'total_nonfarm',
    'change_abs': 'mom_change_abs',
    'change_pct': 'mom_change_pct'
})

# --- Step 3: Load ---
print("Step 3: Loading transformed data into PostgreSQL...")
# Database details
DB_NAME = 'ETL'
DB_USER = 'postgres'
DB_PASSWORD = '@rSHUCHI16'
DB_HOST = 'localhost'
DB_PORT = '5432'

# Initialize connection and cursor to None
conn = None
cursor = None

try:
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nonfarm_payrolls (
            date DATE PRIMARY KEY,
            total_nonfarm DECIMAL,
            mom_change_abs DECIMAL,
            mom_change_pct DECIMAL
        );
    """)
    conn.commit()

    buffer = StringIO()
    jobs_df.to_csv(buffer, index=False, header=False, sep='\t')
    buffer.seek(0)
    cursor.copy_from(buffer, 'nonfarm_payrolls', columns=('date', 'total_nonfarm', 'mom_change_abs', 'mom_change_pct'), sep='\t')
    conn.commit()

    print("Data successfully loaded!")
except psycopg2.OperationalError as e:
    print(f"PostgreSQL connection error: {e}")
    # Specifically catch the connection error to provide a clearer message
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
        print("Database connection closed.")

print("--- ETL Pipeline complete! ---")