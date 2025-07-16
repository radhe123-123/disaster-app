import os
import json
from datetime import datetime, timedelta
from newsapi import NewsApiClient
from dotenv import load_dotenv

load_dotenv()

class NewsDataCollector:
    def __init__(self):
        self.api_key = os.getenv('NEWS_API_KEY')
        self.newsapi = NewsApiClient(api_key=self.api_key)
        self.disaster_keywords = [
            'earthquake', 'flood', 'hurricane', 'tsunami', 'wildfire',
            'tornado', 'cyclone', 'landslide', 'volcano', 'drought'
        ]
    
    def fetch_disaster_news(self, days_back=7):
        """Fetch news articles related to disasters from the past days_back days"""
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')
        all_articles = []
        
        for keyword in self.disaster_keywords:
            print(f"Fetching news for keyword: {keyword}")
            try:
                response = self.newsapi.get_everything(
                    q=keyword,
                    from_param=from_date,
                    to=to_date,
                    language='en',
                    sort_by='publishedAt',
                    page_size=100
                )
                
                if response['status'] == 'ok':
                    # Add disaster type to each article
                    for article in response['articles']:
                        article['disaster_type'] = keyword
                    all_articles.extend(response['articles'])
                    print(f"Found {len(response['articles'])} articles for {keyword}")
                else:
                    print(f"Error fetching articles for {keyword}: {response['status']}")
                    
            except Exception as e:
                print(f"Error fetching articles for {keyword}: {str(e)}")
        
        print(f"Total articles collected: {len(all_articles)}")
        return all_articles

if __name__ == "__main__":
    collector = NewsDataCollector()
    articles = collector.fetch_disaster_news()
    
    # Save raw data to file for testing
    with open('data/raw_news_data.json', 'w') as f:
        json.dump(articles, f)