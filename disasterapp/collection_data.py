"""
Script to collect and process disaster news data, to be run on a schedule.
Can be set up as a cron job or scheduled task.
"""

import os
import sys
import json
from datetime import datetime

# Add project directory to path if running as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.news_api import NewsDataCollector
from utils.data_processor import DataProcessor
from models.database import Database

def collect_and_process_data():
    print(f"Starting data collection at {datetime.now().isoformat()}")
    
    # Initialize components
    collector = NewsDataCollector()
    processor = DataProcessor()
    db = Database()
    
    # Collect data
    print("Collecting news data...")
    raw_articles = collector.fetch_disaster_news(days_back=2)  # Get last 2 days of news
    
    # Process data
    print("Processing articles...")
    processed_articles = processor.process_articles(raw_articles)
    
    # Store in database
    print("Storing in database...")
    new_count = db.store_disaster_data(processed_articles)
    
    print(f"Completed data collection. Added {new_count} new disaster events to the database.")
    print(f"Finished at {datetime.now().isoformat()}")
    
    return new_count

if __name__ == "__main__":
    collect_and_process_data()