import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium 
from datetime import datetime, timedelta
import time
import hashlib
import json

from utils.news_api import NewsDataCollector
from utils.data_processor import DataProcessor
from models.database import Database

# Initialize session state for login functionality
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

def setup_app():
    st.set_page_config(
        page_title="Disaster Monitoring System",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.sidebar.title("Disaster Monitoring System")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Home", "Alerts", "Insights", "Precaution", "About", "Login"]
    )
    
    return page

def display_home_page(db):
    st.title("Geospatial Visualization for Disaster Monitoring")
    
    # Filters in a cleaner expander
    with st.expander("Filter Disaster Events", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        
        with col2:
            end_date = st.date_input("End Date", datetime.now())
        
        with col3:
            # Disaster type filter
            disaster_types = ["earthquake", "flood", "hurricane", "tsunami", "wildfire",
                            "tornado", "cyclone", "landslide", "volcano", "drought"]
            selected_type = st.selectbox("Disaster Type", ["All"] + disaster_types)
    
    # Convert to filters for database
    filters = {
        'from_date': start_date.isoformat(),
        'to_date': end_date.isoformat(),
    }
    
    if selected_type != "All":
        filters['disaster_type'] = selected_type
    
    # Get data from database
    disaster_events = db.get_disaster_events(filters)
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Events", len(disaster_events))
    
    if disaster_events:
        disaster_types_count = {}
        for event in disaster_events:
            disaster_type = event.get('disaster_type', 'unknown')
            disaster_types_count[disaster_type] = disaster_types_count.get(disaster_type, 0) + 1
        
        most_common_type = max(disaster_types_count.items(), key=lambda x: x[1])[0]
        col2.metric("Most Common Disaster", most_common_type.capitalize())
        
        # Get locations count
        location_count = sum(len(event.get('locations', [])) for event in disaster_events)
        col3.metric("Affected Locations", location_count)
        
        # Get most recent event
        most_recent = max(disaster_events, key=lambda x: x.get('publishedAt', ''))
        col4.metric("Most Recent", most_recent.get('disaster_type', '').capitalize())
    
    # Create and display map
    st.subheader("Disaster Events Map")
    
    # Create map
    m = folium.Map(location=[20, 0], zoom_start=2)
    
    # Add disaster events to map with ID for later reference
    for i, event in enumerate(disaster_events):
        for location in event.get('locations', []):
            popup_html = f"""
            <strong>{event['title']}</strong><br>
            Type: {event['disaster_type']}<br>
            Date: {event['publishedAt']}<br>
            <a href="{event['url']}" target="_blank">Read more</a>
            <button onclick="window.parent.postMessage({{'type': 'select_event', 'id': {i}}}, '*')">
                Show Details
            </button>
            """
            
            # Color based on disaster type
            colors = {
                'earthquake': 'red',
                'flood': 'blue',
                'hurricane': 'purple',
                'tsunami': 'darkblue',
                'wildfire': 'orange',
                'tornado': 'darkpurple',
                'cyclone': 'pink',
                'landslide': 'darkred',
                'volcano': 'darkred',
                'drought': 'beige'
            }
            
            color = colors.get(event['disaster_type'], 'gray')
            
            folium.Marker(
                [location['latitude'], location['longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{location['name']} - {event['disaster_type']}",
                icon=folium.Icon(color=color)
            ).add_to(m)
    
    # Display the map
    st_folium(m)
    
    # Create two columns for data display
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Display data table
        st.subheader("Disaster Events Data")
        
        # Convert to dataframe for display
        df_data = []
        for i, event in enumerate(disaster_events):
            locations_str = ", ".join([loc['name'] for loc in event.get('locations', [])])
            df_data.append({
                "ID": i,
                "Title": event['title'],
                "Disaster Type": event['disaster_type'],
                "Locations": locations_str,
                "Date": event['publishedAt'],
                "Source": event['source']
            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            
            # Make the table interactive to select events
            selected_rows = st.dataframe(df, use_container_width=True, height=400)
            selected_indices = selected_rows.index if selected_rows else []
            
            # Store selected event in session state
            if selected_indices and len(selected_indices) > 0:
                st.session_state.selected_event_id = selected_indices[0]
        else:
            st.write("No disaster events found for the selected criteria.")
    
    with col2:
        # Display selected event details
        st.subheader("Event Details")
        
        selected_id = st.session_state.get('selected_event_id', None)
        
        if selected_id is not None and selected_id < len(disaster_events):
            event = disaster_events[selected_id]
            
            # Display event details in a nicely formatted card
            st.markdown(f"### {event['title']}")
            st.markdown(f"**Type**: {event['disaster_type'].capitalize()}")
            st.markdown(f"**Date**: {event['publishedAt']}")
            st.markdown(f"**Source**: {event['source']}")
            
            if event.get('description'):
                st.markdown("**Description**:")
                st.markdown(f"{event['description']}")
            
            # Display locations
            st.markdown("**Affected Locations**:")
            for loc in event.get('locations', []):
                st.markdown(f"- {loc['name']}")
            
            # Display image if available
            if event.get('urlToImage'):
                st.image(event['urlToImage'], caption="Source: " + event['source'])
            
            # Link to source
            st.markdown(f"[Read full article]({event['url']})")
        else:
            st.info("Select an event from the table to view details")
    
    # Active disasters marquee
    st.sidebar.markdown("### Active Disasters (Last Week)")
    recent_disasters = db.get_recent_disasters()
    recent_titles = [f"{d['disaster_type'].upper()}: {d['title']}" for d in recent_disasters[:10]]
    
    if recent_titles:
        marquee_text = " | ".join(recent_titles)
        st.sidebar.markdown(
            f'<div class="marquee"><span>{marquee_text}</span></div>',
            unsafe_allow_html=True
        )
        
        # Add CSS for marquee
        st.markdown("""
        <style>
        .marquee {
          width: 100%;
          overflow: hidden;
          white-space: nowrap;
          border: 1px solid #ddd;
          padding: 10px;
          border-radius: 5px;
        }
        .marquee span {
          display: inline-block;
          padding-left: 100%;
          animation: marquee 30s linear infinite;
        }
        @keyframes marquee {
          0% { transform: translate(0, 0); }
          100% { transform: translate(-100%, 0); }
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Button to refresh data
    if st.sidebar.button("Refresh Data"):
        with st.spinner("Fetching new disaster data..."):
            collector = NewsDataCollector()
            processor = DataProcessor()
            
            # Fetch and process new data
            raw_articles = collector.fetch_disaster_news()
            processed_articles = processor.process_articles(raw_articles)
            
            # Store in database
            new_count = db.store_disaster_data(processed_articles)
            st.success(f"Added {new_count} new disaster events to the database!")
            st.experimental_rerun()

def display_alerts_page(db):
    st.title("Disaster Alerts")
    
    if not st.session_state.logged_in:
        st.warning("Please log in to set up disaster alerts.")
        st.write("Alerts allow you to receive notifications about specific types of disasters in your areas of interest.")
        return
    
    st.subheader(f"Alert Settings for {st.session_state.username}")
    
    # Get user data
    user = db.find_user(st.session_state.username)
    preferences = user.get('preferences', {})
    
    # Set up alert preferences
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Disaster Types")
        disaster_types = ["earthquake", "flood", "hurricane", "tsunami", "wildfire",
                        "tornado", "cyclone", "landslide", "volcano", "drought"]
        
        selected_disasters = {}
        for disaster in disaster_types:
            default = disaster in preferences.get('disaster_types', [])
            selected_disasters[disaster] = st.checkbox(disaster.capitalize(), value=default)
    
    with col2:
        st.subheader("Regions of Interest")
        regions = st.text_area("Enter regions (one per line)", 
                              value="\n".join(preferences.get('regions', [])))
        
        notification_method = st.selectbox(
            "Notification Method",
            ["Email", "SMS", "Push Notification"],
            index=0 if not preferences.get('notification_method') else 
                  ["Email", "SMS", "Push Notification"].index(preferences.get('notification_method'))
        )
    
    if st.button("Save Alert Preferences"):
        # Update user preferences
        new_preferences = {
            'disaster_types': [d for d in disaster_types if selected_disasters[d]],
            'regions': [r.strip() for r in regions.split("\n") if r.strip()],
            'notification_method': notification_method
        }
        
        # Save to database (simplified, would actually update user doc)
        st.success("Alert preferences saved successfully!")
        
        # In a real app, you would update the user document in the database
        # db.users_collection.update_one(
        #     {'username': st.session_state.username},
        #     {'$set': {'preferences': new_preferences}}
        # )
    
    # Display recent alerts that match user preferences
    st.subheader("Recent Alerts Matching Your Preferences")
    
    # This is a placeholder. In a real app, you would query the database
    # for disasters matching the user's preferences
    st.info("You will receive alerts based on your preferences.")

def display_insights_page(db):
    st.title("Disaster Insights")
    
    # Get all disaster data
    all_disasters = db.get_disaster_events()
    
    if not all_disasters:
        st.warning("No disaster data available for analysis.")
        return
    
    # Convert to DataFrame for analysis
    df_data = []
    for event in all_disasters:
        try:
            published_date = datetime.fromisoformat(event['publishedAt'].replace('Z', '+00:00'))
            locations = [loc['name'] for loc in event.get('locations', [])]
            countries = list(set([loc['name'].split(', ')[-1] if ', ' in loc['name'] else loc['name'] for loc in event.get('locations', [])]))
            
            df_data.append({
                "disaster_type": event['disaster_type'],
                "published_date": published_date,
                "month": published_date.month,
                "year": published_date.year,
                "source": event['source'],
                "title": event['title'],
                "locations": locations,
                "countries": countries,
                "location_count": len(locations)
            })
        except Exception as e:
            print(f"Error processing event for insights: {str(e)}")
    
    df = pd.DataFrame(df_data)
    
    # Set up tabs for different insights
    tab1, tab2, tab3 = st.tabs(["Disaster Distribution", "Temporal Analysis", "Geographic Analysis"])
    
    with tab1:
        st.subheader("Distribution of Disaster Types")
        
        # Create a horizontal bar chart using Plotly
        import plotly.express as px
        
        disaster_counts = df['disaster_type'].value_counts().reset_index()
        disaster_counts.columns = ['Disaster Type', 'Count']
        
        fig = px.bar(
            disaster_counts,
            x='Count',
            y='Disaster Type',
            orientation='h',
            color='Disaster Type',
            title='Distribution of Disaster Types',
            labels={'Count': 'Number of Events', 'Disaster Type': ''},
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Source distribution
        st.subheader("Top News Sources")
        source_counts = df['source'].value_counts().head(10).reset_index()
        source_counts.columns = ['Source', 'Count']
        
        fig = px.pie(
            source_counts,
            values='Count',
            names='Source',
            title='Top 10 News Sources',
            hole=0.4
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Temporal Analysis")
        
        # Monthly trend
        df['month_year'] = df['published_date'].dt.strftime('%Y-%m')
        monthly_counts = df.groupby(['month_year', 'disaster_type']).size().unstack().fillna(0)
        
        # Plot using Plotly
        fig = px.line(
            monthly_counts,
            x=monthly_counts.index,
            y=monthly_counts.columns,
            title='Monthly Disaster Trends',
            labels={'value': 'Number of Events', 'month_year': 'Month'},
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Day of week analysis
        df['day_of_week'] = df['published_date'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        day_counts = df['day_of_week'].value_counts().reindex(day_order).reset_index()
        day_counts.columns = ['Day of Week', 'Count']
        
        fig = px.bar(
            day_counts,
            x='Day of Week',
            y='Count',
            title='Disaster Reports by Day of Week',
            color='Count',
            labels={'Count': 'Number of Events', 'Day of Week': ''},
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Geographic Analysis")
        
        # Extract and count countries
        all_countries = []
        for countries_list in df['countries']:
            all_countries.extend(countries_list)
        
        country_counts = pd.Series(all_countries).value_counts().head(15).reset_index()
        country_counts.columns = ['Country', 'Count']
        
        fig = px.bar(
            country_counts,
            x='Country',
            y='Count',
            title='Top 15 Countries with Most Reported Disasters',
            color='Count',
            labels={'Count': 'Number of Events', 'Country': ''},
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Disaster types by top countries
        top_countries = country_counts['Country'].head(5).tolist()
        
        country_disaster_data = []
        for _, row in df.iterrows():
            for country in row['countries']:
                if country in top_countries:
                    country_disaster_data.append({
                        'Country': country,
                        'Disaster Type': row['disaster_type']
                    })
        
        country_disaster_df = pd.DataFrame(country_disaster_data)
        
        # Create grouped bar chart
        country_disaster_counts = country_disaster_df.groupby(['Country', 'Disaster Type']).size().reset_index()
        country_disaster_counts.columns = ['Country', 'Disaster Type', 'Count']
        
        fig = px.bar(
            country_disaster_counts,
            x='Country',
            y='Count',
            color='Disaster Type',
            title='Disaster Types by Top 5 Countries',
            barmode='group',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

def display_precaution_page():
    st.title("Disaster Precautions")
    
    disaster_type = st.selectbox(
        "Select Disaster Type",
        ["Earthquake", "Flood", "Hurricane", "Tsunami", "Wildfire",
         "Tornado", "Cyclone", "Landslide", "Volcano", "Drought"]
    )
    
    st.subheader(f"Safety Precautions for {disaster_type}")
    
    # Precaution information for each disaster type
    precautions = {
        "Earthquake": {
            "Before": [
                "Secure heavy furniture to walls",
                "Know where and how to shut off utilities",
                "Create an emergency plan and kit",
                "Identify safe spots in each room (under sturdy furniture, against interior walls)"
            ],
            "During": [
                "Drop, Cover, and Hold On",
                "If indoors, stay there until shaking stops",
                "If outdoors, move to a clear area away from buildings",
                "If driving, pull over safely away from buildings and overpasses"
            ],
            "After": [
                "Check for injuries and provide first aid",
                "Check for damage to utilities",
                "Monitor news for emergency information",
                "Be prepared for aftershocks"
            ]
        },
        # Add similar information for other disaster types
    }
    
    # Display precaution information
    if disaster_type in precautions:
        for phase, tips in precautions[disaster_type].items():
            st.write(f"**{phase}:**")
            for tip in tips:
                st.write(f"- {tip}")
    else:
        st.write("Precaution information for this disaster type is not available yet.")
    
    # Additional resources
    st.subheader("Additional Resources")
    st.write("Here are some helpful resources for disaster preparedness:")
    st.write("- [Ready.gov](https://www.ready.gov/) - Official disaster preparedness website")
    st.write("- [Red Cross Disaster Safety](https://www.redcross.org/get-help/how-to-prepare-for-emergencies.html) - Comprehensive guides")
    st.write("- [FEMA App](https://www.fema.gov/about/news-multimedia/mobile-app-text-messages) - Real-time alerts and safety tips")

def display_about_page():
    st.title("About the Project")
    
    st.write("""
    ## Geospatial Visualization for Disaster Monitoring
    
    This project aims to provide real-time monitoring and visualization of global disasters through news data. 
    By leveraging natural language processing and geospatial mapping, we extract and display information about 
    ongoing disasters worldwide, helping users stay informed about events that might affect them or require attention.
    
    ### Key Features
    
    - **Real-time Monitoring**: Automatically collects data from news sources about various types of disasters
    - **Interactive Map**: Visualizes disaster events geographically with detailed information
    - **Filtering Capabilities**: Filter disasters by type, date range, and location
    - **Alert System**: Get notified about disasters in regions of interest
    - **Insights and Analytics**: View trends and patterns in disaster occurrences
    - **Precaution Information**: Access safety guidelines for different disaster types
    
    ### Technologies Used
    
    - **Data Collection**: NewsAPI for gathering real-time disaster news
    - **Data Processing**: SpaCy for Named Entity Recognition, extracting locations from text
    - **Geocoding**: GeoPy for converting location names to coordinates
    - **Database**: MongoDB Atlas for storing processed disaster information
    - **Visualization**: Streamlit and Folium for interactive maps and dashboards
    
    ### Future Enhancements
    
    - Integration with official disaster alert systems (e.g., USGS, NOAA)
    - Predictive analytics for disaster risk assessment
    - Mobile application for on-the-go alerts
    - Community reporting features for local observations
    """)

def display_login_page(db):
    st.title("User Account")
    
    if st.session_state.logged_in:
        st.write(f"Logged in as: {st.session_state.username}")
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.success("Logged out successfully!")
            time.sleep(1)
            st.experimental_rerun()
        
        return
    
    # Login/Register tabs
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if not login_username or not login_password:
                st.error("Please enter both username and password")
                return
            
            # Check if user exists (in a real app, verify password hash)
            user = db.find_user(login_username)
            
            if user:
                # Simple password verification (would use proper hashing in real app)
                password_hash = hashlib.sha256(login_password.encode()).hexdigest()
                
                if user.get('password_hash') == password_hash:
                    st.session_state.logged_in = True
                    st.session_state.username = login_username
                    st.success("Login successful!")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("Invalid password")
            else:
                st.error("User not found")
    
    with tab2:
        st.subheader("Register")
        new_username = st.text_input("Username", key="new_username")
        new_email = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        
        if st.button("Register"):
            if not new_username or not new_email or not new_password:
                st.error("Please fill all fields")
                return
            
            if new_password != confirm_password:
                st.error("Passwords do not match")
                return
            
            # Check if username exists
            existing_user = db.find_user(new_username)
            if existing_user:
                st.error("Username already exists")
                return
            
            # Hash password
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            
            # Create user
            db.register_user(new_username, new_email, password_hash)
            st.success("Registration successful! You can now login.")

def main():
    # Create instances
    db = Database()
    
    # Set up app and get current page
    page = setup_app()
    
    # Display current page
    if page == "Home":
        display_home_page(db)
    elif page == "Alerts":
        display_alerts_page(db)
    elif page == "Insights":
        display_insights_page(db)
    elif page == "Precaution":
        display_precaution_page()
    elif page == "About":
        display_about_page()
    elif page == "Login":
        display_login_page(db)

if __name__ == "__main__":
    main()