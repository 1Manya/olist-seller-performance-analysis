import pandas as pd
import sqlite3
from sqlalchemy import create_engine
import logging
import time

# logging setup
logging.basicConfig(
    filename='../logs/get_vendor_summary.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)
# final summary table 
def create_vendor_summary(conn):
   
    logging.info("Starting create_vendor_summary...")

    try:
        logging.info("Running main SQL query...")

        df = pd.read_sql("""
            SELECT 
                s.seller_id,
                s.seller_city,
                s.seller_state,
                COUNT(DISTINCT i.order_id)              AS total_orders,
                ROUND(SUM(i.price), 2)                  AS total_revenue,
                ROUND(SUM(i.freight_value), 2)          AS total_freight_cost,
                ROUND(AVG(i.price), 2)                  AS avg_order_value,
                ROUND(AVG(r.review_score), 2)           AS avg_rating,
                COUNT(r.review_id)                      AS total_reviews,
                COUNT(CASE 
                    WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date 
                    THEN 1 END)                         AS late_deliveries,
                ROUND(
                    COUNT(CASE 
                        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date 
                        THEN 1 END) * 100.0 / COUNT(DISTINCT o.order_id)
                , 2)                                    AS late_delivery_pct
            FROM olist_sellers_dataset s
            JOIN olist_order_items_dataset i
                ON s.seller_id = i.seller_id
            JOIN olist_orders_dataset o
                ON i.order_id = o.order_id
            JOIN olist_order_reviews_dataset r
                ON o.order_id = r.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY 
                s.seller_id,
                s.seller_city,
                s.seller_state
        """, conn)

        logging.info(f"SQL query successful! Rows fetched: {len(df):,}")

        # Category summary
        logging.info("Fetching category summary...")
        category_summary = pd.read_sql("""
            SELECT seller_id, top_category
            FROM (
                SELECT 
                    i.seller_id,
                    t.product_category_name_english AS top_category,
                    COUNT(*) AS category_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY i.seller_id 
                        ORDER BY COUNT(*) DESC
                    ) AS rank
                FROM olist_order_items_dataset i
                JOIN olist_products_dataset p
                    ON i.product_id = p.product_id
                JOIN product_category_name_translation t
                    ON p.product_category_name = t.product_category_name
                GROUP BY 
                    i.seller_id,
                    t.product_category_name_english
            )
            WHERE rank = 1
        """, conn)

        # Merge category
        df = pd.merge(df, category_summary, on='seller_id', how='left')
        logging.info("Category merged successfully!")

        return df

    except Exception as e:
        logging.error(f"Error in create_vendor_summary: {e}")
        raise
# data cleaning 
def clean_data(df):

    logging.info("Starting clean_data...")

    try:
        logging.info("Fixing duplicate sellers...")
        df = df.groupby(
            ['seller_id', 'seller_city', 'seller_state'],
            as_index=False
        ).agg({
            'total_orders'      : 'sum',
            'total_revenue'     : 'sum',
            'total_freight_cost': 'sum',
            'avg_order_value'   : 'mean',
            'avg_rating'        : 'mean',
            'total_reviews'     : 'sum',
            'late_deliveries'   : 'sum',
            'late_delivery_pct' : 'mean',
            'top_category'      : 'first'
        })
        logging.info(f"Duplicates fixed! Unique sellers: {len(df):,}")

        # Missing values
        logging.info("Filling missing values...")
        df['avg_rating'] = df['avg_rating'].fillna(0)
        df['top_category'] = df['top_category'].fillna('Unknown')

        # Whitespace removal
        logging.info("Stripping whitespace from text columns...")
        df['seller_city'] = df['seller_city'].str.strip()
        df['seller_state'] = df['seller_state'].str.strip()

        # New feature columns
        logging.info("Adding new feature columns...")

        df['gross_profit'] = round(
            df['total_revenue'] - df['total_freight_cost'], 2
        )

        df['profit_margin'] = round(
            (df['gross_profit'] / df['total_revenue']) * 100, 2
        )

        df['revenue_per_order'] = round(
            df['total_revenue'] / df['total_orders'], 2
        )

        def performance_label(row):
            if row['total_revenue'] >= 10000 and row['avg_rating'] >= 4.0:
                return 'Top Performer'
            elif row['total_revenue'] >= 5000 and row['avg_rating'] >= 3.5:
                return 'Mid Performer'
            else:
                return 'Low Performer'

        df['performance_label'] = df.apply(performance_label, axis=1)

        df['delivery_status'] = df['late_delivery_pct'].apply(
            lambda x: 'Good' if x <= 10 else ('Average' if x <= 25 else 'Poor')
        )

        logging.info("All feature columns added successfully!")
        logging.info(f"Final shape: {df.shape}")

        return df

    except Exception as e:
        logging.error(f"Error in clean_data: {e}")
        raise

def main():
    logging.info("get_vendor_summary.py STARTED")

    start_time = time.time()

    # Database connection
    logging.info("Connecting to database...")
    conn = sqlite3.connect('../data/olist_ecommerce.db')
    engine = create_engine('sqlite:///../data/olist_ecommerce.db')
    logging.info("Database connected!")

    # Step 1 — Summary banao
    df = create_vendor_summary(conn)
    print(f" Vendor summary created! Shape: {df.shape}")

    # Step 2 — Clean karo
    df = clean_data(df)
    print(f" Data cleaned! Shape: {df.shape}")

    # Step 3 — Database mein save karo
    logging.info("Saving final table to database...")
    df.to_sql('seller_summary', con=engine,
              if_exists='replace', index=False)
    logging.info("seller_summary saved to database!")
    print(f" seller_summary saved to database!")

    # Summary print karo
    print(f"\nPerformance Distribution:")
    print(df['performance_label'].value_counts())
    print(f"\nDelivery Status:")
    print(df['delivery_status'].value_counts())

    end_time = time.time()
    total_time = round((end_time - start_time) / 60, 2)

    logging.info(f"Total time taken: {total_time} minutes")
    logging.info("=" * 50)
    logging.info("get_vendor_summary.py COMPLETED")
    logging.info("=" * 50)

    print(f"\n Script complete! Time: {total_time} minutes")

# ===========================
if __name__ == '__main__':
    main()
    