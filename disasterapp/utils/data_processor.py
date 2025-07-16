import json
from datetime import datetime
from .location_extractor import LocationExtractor

class DataProcessor:
    def __init__(self):
        self.location_extractor = LocationExtractor()
    
    def process_articles(self, articles):
        """Process raw news articles and extract relevant information"""
        processed_data = []
        
        for article in articles:
            try:
                # Extract basic information
                processed_article = {
                    "title": article.get("title"),
                    "description": article.get("description"),
                    "content": article.get("content"),
                    "url": article.get("url"),
                    "urlToImage": article.get("urlToImage"),
                    "publishedAt": article.get("publishedAt"),
                    "source": article.get("source", {}).get("name"),
                    "disaster_type": article.get("disaster_type")
                }
                
                # Extract locations from title and description
                text_to_analyze = f"{article.get('title', '')} {article.get('description', '')}"
                location_names = self.location_extractor.extract_locations(text_to_analyze)
                
                locations_with_coords = []
                for loc_name in location_names:
                    loc_data = self.location_extractor.get_coordinates(loc_name)
                    if loc_data:
                        locations_with_coords.append(loc_data)
                
                processed_article["locations"] = locations_with_coords
                
                # Only add articles that have at least one valid location
                if locations_with_coords:
                    processed_data.append(processed_article)
                
            except Exception as e:
                print(f"Error processing article: {str(e)}")
        
        return processed_data

if __name__ == "__main__":
    # Load the raw data for testing
    with open('data/raw_news_data.json', 'r') as f:
        raw_data = json.load(f)
    
    processor = DataProcessor()
    processed_data = processor.process_articles(raw_data)
    
    # Save processed data for testing
    with open('data/processed_news_data.json', 'w') as f:
        json.dump(processed_data, f)
    
    print(f"Processed {len(processed_data)} articles with valid locations out of {len(raw_data)} total articles")