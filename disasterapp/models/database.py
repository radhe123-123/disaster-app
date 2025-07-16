import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime,timedelta 

load_dotenv()

class Database:
    def __init__(self):
        self.mongo_uri = os.getenv('MONGODB_URI')
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client.disaster_monitoring
        self.disaster_collection = self.db.disaster_events
        self.users_collection = self.db.users
        
    def store_disaster_data(self, processed_articles):
        """Store processed disaster articles in MongoDB"""
        count = 0
        for article in processed_articles:
            # Create a unique identifier to avoid duplicates
            article_url = article.get('url')
            
            # Check if article already exists
            existing = self.disaster_collection.find_one({'url': article_url})
            if not existing:
                # Add timestamp for when it was added to database
                article['added_to_db'] = datetime.now().isoformat()
                
                # Insert the document
                self.disaster_collection.insert_one(article)
                count += 1
        
        return count
    
    def get_disaster_events(self, filters=None):
        """Retrieve disaster events with optional filters"""
        query = {}
        
        if filters:
            if 'disaster_type' in filters and filters['disaster_type']:
                query['disaster_type'] = filters['disaster_type']
            
            if 'from_date' in filters and filters['from_date']:
                query['publishedAt'] = {'$gte': filters['from_date']}
            
            if 'to_date' in filters and filters['to_date']:
                if 'publishedAt' in query:
                    query['publishedAt']['$lte'] = filters['to_date']
                else:
                    query['publishedAt'] = {'$lte': filters['to_date']}
        
        return list(self.disaster_collection.find(query))
    
    def get_recent_disasters(self, days=7):
        """Get disasters from the past days"""
        from_date = (datetime.now() - timedelta(days=days)).isoformat()
        return self.get_disaster_events({'from_date': from_date})
    
    def register_user(self, username, email, password_hash, preferences=None):
        """Register a new user"""
        user = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'preferences': preferences if preferences else {},
            'created_at': datetime.now().isoformat()
        }
        result = self.users_collection.insert_one(user)
        return result.inserted_id
    
    def find_user(self, username):
        """Find user by username"""
        return self.users_collection.find_one({'username': username})