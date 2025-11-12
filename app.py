import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pandas as pd
import time
import os
import googlemaps

st.set_page_config(page_title="Store & Restaurant Locator", layout="wide")

st.title("Store & Restaurant Locator")
st.markdown("Find stores and restaurants near any zip code")

def get_coordinates_from_zipcode(zipcode):
    """Geocode a zip code to latitude and longitude"""
    try:
        geolocator = Nominatim(user_agent="store_restaurant_locator")
        time.sleep(1)
        location = geolocator.geocode(f"{zipcode}, USA")
        if location:
            return location.latitude, location.longitude, location.address
        else:
            return None, None, None
    except Exception as e:
        st.error(f"Error geocoding zip code: {e}")
        return None, None, None

def get_real_businesses(center_lat, center_lon, radiusmiles=10, api_key=None):
    """Fetch real business data from Google Places API"""
    if not api_key:
        return None
    
    try:
        gmaps = googlemaps.Client(key=api_key)
        radius_meters = radius_miles * 1609.34
        
        all_businesses = []
        
        for place_type in ['store', 'restaurant']:
            results = gmaps.places_nearby(
                location=(center_lat, center_lon),
                radius=radius_meters,
                type=place_type
            )
            
            for place in results.get('results', []):
                place_id = place.get('place_id')
                details = gmaps.place(place_id=place_id, fields=[
                    'name', 'formatted_address', 'geometry', 'rating', 
                    'opening_hours', 'formatted_phone_number', 'types'
                ])
                
                detail_info = details.get('result', {})
                place_lat = detail_info.get('geometry', {}).get('location', {}).get('lat')
                place_lon = detail_info.get('geometry', {}).get('location', {}).get('lng')
                
                if place_lat and place_lon:
                    distance = geodesic((center_lat, center_lon), (place_lat, place_lon)).miles
                    
                    business_type = "Restaurant" if 'restaurant' in detail_info.get('types', []) else "Store"
                    
                    categories = detail_info.get('types', [])
                    category = categories[0].replace('_', ' ').title() if categories else "General"
                    
                    opening_hours = detail_info.get('opening_hours', {})
                    hours_text = "Open now" if opening_hours.get('open_now') else "Closed"
                    if 'weekday_text' in opening_hours:
                        hours_text = "; ".join(opening_hours['weekday_text'][:2])
                    
                    all_businesses.append({
                        "Name": detail_info.get('name', 'Unknown'),
                        "Type": business_type,
                        "Category": category,
                        "Address": detail_info.get('formatted_address', 'N/A'),
                        "Latitude": place_lat,
                        "Longitude": place_lon,
                        "Distance (miles)": round(distance, 2),
                        "Rating": detail_info.get('rating', 'N/A'),
                        "Phone": detail_info.get('formatted_phone_number', 'N/A'),
                        "Hours": hours_text
                    })
        
        return pd.DataFrame(all_businesses) if all_businesses else pd.DataFrame()
    
    except Exception as e:
        st.error(f"Error fetching business data: {e}")
        return None

@st.cache_data
def get_sample_businesses(center_lat, center_lon, radius_km=10):
    """Generate sample stores and restaurants around a given location"""
    businesses = [
        {"name": "Target", "type": "Store", "category": "Department Store", "lat_offset": 0.02, "lon_offset": 0.01, "street": "Main St"},
        {"name": "Walmart Supercenter", "type": "Store", "category": "Supermarket", "lat_offset": -0.01, "lon_offset": 0.03, "street": "Commerce Blvd"},
        {"name": "Whole Foods Market", "type": "Store", "category": "Grocery", "lat_offset": 0.03, "lon_offset": -0.02, "street": "Oak Avenue"},
        {"name": "Best Buy", "type": "Store", "category": "Electronics", "lat_offset": -0.02, "lon_offset": -0.01, "street": "Technology Way"},
        {"name": "CVS Pharmacy", "type": "Store", "category": "Pharmacy", "lat_offset": 0.01, "lon_offset": 0.02, "street": "Park Street"},
        {"name": "The Olive Garden", "type": "Restaurant", "category": "Italian", "lat_offset": 0.015, "lon_offset": 0.015, "street": "Restaurant Row"},
        {"name": "Chipotle Mexican Grill", "type": "Restaurant", "category": "Mexican", "lat_offset": -0.015, "lon_offset": 0.02, "street": "Market Street"},
        {"name": "Starbucks", "type": "Restaurant", "category": "Coffee Shop", "lat_offset": 0.025, "lon_offset": -0.015, "street": "Center Avenue"},
        {"name": "McDonald's", "type": "Restaurant", "category": "Fast Food", "lat_offset": -0.025, "lon_offset": -0.025, "street": "Highway 101"},
        {"name": "Panera Bread", "type": "Restaurant", "category": "Bakery Cafe", "lat_offset": 0.005, "lon_offset": -0.03, "street": "Plaza Drive"},
        {"name": "Red Lobster", "type": "Restaurant", "category": "Seafood", "lat_offset": -0.03, "lon_offset": 0.01, "street": "Waterfront Way"},
        {"name": "Buffalo Wild Wings", "type": "Restaurant", "category": "American", "lat_offset": 0.02, "lon_offset": 0.025, "street": "Stadium Boulevard"},
    ]
    
    business_list = []
    for business in businesses:
        lat = center_lat + business["lat_offset"]
        lon = center_lon + business["lon_offset"]
        
        address = f"123 {business['street']}, Nearby City"
        distance = geodesic((center_lat, center_lon), (lat, lon)).miles
        
        business_list.append({
            "Name": business["name"],
            "Type": business["type"],
            "Category": business["category"],
            "Address": address,
            "Latitude": lat,
            "Longitude": lon,
            "Distance (miles)": round(distance, 2)
        })
    
    return pd.DataFrame(business_list)

def create_map(center_lat, center_lon, businesses_df):
    """Create an interactive folium map with business markers"""
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles="OpenStreetMap"
    )
    
    folium.Marker(
        [center_lat, center_lon],
        popup="Search Location",
        tooltip="Your searched zip code",
        icon=folium.Icon(color="red", icon="home", prefix="fa")
    ).add_to(m)
    
    for idx, row in businesses_df.iterrows():
        icon_color = "blue" if row["Type"] == "Store" else "green"
        icon_symbol = "shopping-cart" if row["Type"] == "Store" else "utensils"
        
        popup_html = f"""
        <div style="width: 250px;">
            <h4>{row['Name']}</h4>
            <p><strong>Type:</strong> {row['Type']}<br>
            <strong>Category:</strong> {row['Category']}<br>
            <strong>Distance:</strong> {row['Distance (miles)']} miles<br>
            <strong>Address:</strong> {row['Address']}<br>
        """
        
        if 'Rating' in row and row['Rating'] != 'N/A':
            popup_html += f"<strong>Rating:</strong> { * int(float(row['Rating']))} ({row['Rating']})<br>"
        
        if 'Phone' in row and row['Phone'] != 'N/A':
            popup_html += f"<strong>Phone:</strong> {row['Phone']}<br>"
        
        if 'Hours' in row and row['Hours'] != 'N/A':
            popup_html += f"<strong>Hours:</strong> {row['Hours'][:50]}<br>"
        
        popup_html += "</p></div>"
        
        folium.Marker(
            [row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row["Name"],
            icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
        ).add_to(m)
    
    return m

google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")

if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'search_location' not in st.session_state:
    st.session_state.search_location = None

col1, col2 = st.columns([1, 2])

with col1:
    zipcode = st.text_input("Enter Zip Code", placeholder="e.g., 10001, 90210, 60601")
    
    use_real_data = st.checkbox(
        "Use Real Business Data (Google Places)",
        value=bool(google_api_key),
        disabled=not bool(google_api_key),
        help="Requires Google Places API key to be set"
    )
    
    st.markdown("### Filters")
    
    business_type_filter = st.multiselect(
        "Business Type",
        options=["Store", "Restaurant"],
        default=["Store", "Restaurant"],
        help="Select the types of businesses to display"
    )
    
    category_filter = st.multiselect(
        "Category",
        options=["All Categories", "Department Store", "Supermarket", "Grocery", "Electronics", 
                 "Pharmacy", "Italian", "Mexican", "Coffee Shop", "Fast Food", "Bakery Cafe", 
                 "Seafood", "American"],
        default=["All Categories"],
        help="Select specific business categories"
    )
    
    radius_miles = st.slider(
        "Search Radius (miles)",
        min_value=1,
        max_value=25,
        value=10,
        step=1,
        help="Adjust the search distance from the zip code"
    )
    
    search_button = st.button("Search", type="primary", use_container_width=True)

if search_button and zipcode:
    if len(zipcode) != 5 or not zipcode.isdigit():
        st.error("Please enter a valid 5-digit zip code")
    else:
        with st.spinner("Geocoding zip code..."):
            lat, lon, address = get_coordinates_from_zipcode(zipcode)
        
        if lat and lon:
            with st.spinner("Finding nearby stores and restaurants..."):
                if use_real_data and google_api_key:
                    all_businesses_df = get_real_businesses(lat, lon, radius_miles, google_api_key)
                    if all_businesses_df is None or all_businesses_df.empty:
                        st.warning("Could not fetch real business data. Using sample data instead.")
                        all_businesses_df = get_sample_businesses(lat, lon)
                else:
                    all_businesses_df = get_sample_businesses(lat, lon)
            
            st.session_state.search_results = all_businesses_df
            st.session_state.search_location = {
                'lat': lat,
                'lon': lon,
                'address': address,
                'zipcode': zipcode
            }

if st.session_state.search_results is not None and st.session_state.search_location is not None:
    st.success(f"Location found: {st.session_state.search_location['address']}")
    
    businesses_df = st.session_state.search_results.copy()
    lat = st.session_state.search_location['lat']
    lon = st.session_state.search_location['lon']
    zipcode = st.session_state.search_location['zipcode']
    
    if business_type_filter:
        businesses_df = businesses_df[businesses_df["Type"].isin(business_type_filter)]
    
    if category_filter and "All Categories" not in category_filter:
        businesses_df = businesses_df[businesses_df["Category"].isin(category_filter)]
    
    businesses_df = businesses_df[businesses_df["Distance (miles)"] <= radius_miles]
    
    if len(businesses_df) > 0:
        col_header1, col_header2 = st.columns([3, 1])
        with col_header1:
            st.subheader(f"Found {len(businesses_df)} businesses within {radius_miles} miles of {zipcode}")
        with col_header2:
            csv_data = businesses_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=" Export to CSV",
                data=csv_data,
                file_name=f"businesses_{zipcode}_{radius_miles}mi.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        tab1, tab2 = st.tabs(["Map View", " List View"])
        
        with tab1:
            map_obj = create_map(lat, lon, businesses_df)
            st_folium(map_obj, width=None, height=600)
            
            st.info(" Tip: Click on markers to see business details. Red marker shows your search location, blue for stores, green for restaurants.")
        
        with tab2:
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("### Stores")
                stores = businesses_df[businesses_df["Type"] == "Store"].sort_values("Distance (miles)")
                for idx, store in stores.iterrows():
                    title = f"{store['Name']} - {store['Distance (miles)']} mi"
                    if 'Rating' in store and store['Rating'] != 'N/A':
                        title += f" {store['Rating']}"
                    with st.expander(title):
                        st.write(f"**Category:** {store['Category']}")
                        st.write(f"**Address:** {store['Address']}")
                        if 'Phone' in store and store['Phone'] != 'N/A':
                            st.write(f"**Phone:** {store['Phone']}")
                        if 'Hours' in store and store['Hours'] != 'N/A':
                            st.write(f"**Hours:** {store['Hours']}")
                        st.write(f"**Coordinates:** {store['Latitude']:.4f}, {store['Longitude']:.4f}")
            
            with col_b:
                st.markdown("### ️ Restaurants")
                restaurants = businesses_df[businesses_df["Type"] == "Restaurant"].sort_values("Distance (miles)")
                for idx, restaurant in restaurants.iterrows():
                    title = f"{restaurant['Name']} - {restaurant['Distance (miles)']} mi"
                    if 'Rating' in restaurant and restaurant['Rating'] != 'N/A':
                        title += f" {restaurant['Rating']}"
                    with st.expander(title):
                        st.write(f"**Category:** {restaurant['Category']}")
                        st.write(f"**Address:** {restaurant['Address']}")
                        if 'Phone' in restaurant and restaurant['Phone'] != 'N/A':
                            st.write(f"**Phone:** {restaurant['Phone']}")
                        if 'Hours' in restaurant and restaurant['Hours'] != 'N/A':
                            st.write(f"**Hours:** {restaurant['Hours']}")
                        st.write(f"**Coordinates:** {restaurant['Latitude']:.4f}, {restaurant['Longitude']:.4f}")
            
            st.markdown("---")
            st.markdown("### All Businesses Table")
            st.dataframe(
                businesses_df.sort_values("Distance (miles)"),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning(f"No businesses found matching your filters within {radius_miles} miles of {zipcode}. Try adjusting your filters or search radius.")

elif not zipcode and search_button:
    st.warning("Please enter a zip code to search")

with col2:
    if not google_api_key:
        st.warning(" Google Places API key not set. Using sample data. To use real business data, add your GOOGLE_PLACES_API_KEY to the environment secrets.")
    
    st.info("""
    ### How to use:
    1. Enter a valid 5-digit US zip code
    2. Optionally enable real business data (requires API key)
    3. Use filters to narrow down by type and category
    4. Adjust the search radius with the slider
    5. Click Search to see results
    6. View businesses on the map or in list view
    7. Export results to CSV for further analysis
    
    ### Features:
    -  Interactive map with business markers
    - Filter by business type and category
    - Adjustable search radius (1-25 miles)
    - Real business ratings and hours (with API key)
    - Contact information display
    - CSV export functionality
    """)
