import spacy
import geopy.geocoders
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

class LocationExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        geopy.geocoders.options.default_user_agent = "disaster_monitoring_app"
        self.geolocator = Nominatim(user_agent="disaster_monitoring_app")
        self.geocode = RateLimiter(self.geolocator.geocode, min_delay_seconds=1)
    
    def extract_locations(self, text):
        """Extract location entities from text using SpaCy NER"""
        if not text:
            return []
        
        doc = self.nlp(text)
        locations = []
        
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                locations.append(ent.text)
        
        return list(set(locations))  # Remove duplicates
    
    def get_coordinates(self, location_name):
        """Get latitude and longitude for a location name"""
        try:
            location = self.geocode(location_name)
            if location:
                return {
                    "name": location_name,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "address": location.address
                }
            return None
        except Exception as e:
            print(f"Error geocoding {location_name}: {str(e)}")
            return None