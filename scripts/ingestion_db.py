import pandas as pd
import os
from sqlalchemy import create_engine
import time
import logging

# Logging setup
logging.basicConfig(
    filename='../logs/ingestion_db.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

# FUNCTION 1 — Database Engine 
def create_db_engine(db_path):
    try:
        engine = create_engine(f'sqlite:///{db_path}')
        logging.info(f"Database engine created at: {db_path}")
        return engine
    except Exception as e:
        logging.error(f"Failed to create engine: {e}")
        raise

# FUNCTION 2 — CSV File --> load to  Database 
def ingest_db(df, table_name, engine):
    try:
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        logging.info(f"Successfully inserted: {table_name} --> {df.shape[0]:,} rows")
    except Exception as e:
        logging.error(f"Failed to insert {table_name}: {e}")
        raise

# FUNCTION 3 — load all csv files
def load_raw_data(data_path, engine):
  
    logging.info("=" * 50)
    logging.info("Starting data ingestion process...")
    logging.info("=" * 50)

    start_time = time.time()
    files_loaded = 0

    for file in os.listdir(data_path):
        if file.endswith('.csv'):

            table_name = file.replace('.csv', '')

            logging.info(f"Reading file: {file}")
            df = pd.read_csv(data_path + file)

            logging.info(f"Inserting {file} into database...")
            ingest_db(df, table_name, engine)

            files_loaded += 1
            print(f"Loaded: {table_name} --> {df.shape[0]:,} rows")

    end_time = time.time()
    total_time = round((end_time - start_time) / 60, 2)

    logging.info("=" * 50)
    logging.info(f"Ingestion complete! Total files loaded: {files_loaded}")
    logging.info(f"Total time taken: {total_time} minutes")
    logging.info("=" * 50)

    print(f"\n Done! {files_loaded} files loaded in {total_time} minutes")
    print(" Check logs/ingestion_db.log for details")


if __name__ == '__main__':
    DATA_PATH = '../data/'
    DB_PATH = '../data/olist_ecommerce.db'

    engine = create_db_engine(DB_PATH)
    load_raw_data(DATA_PATH, engine)