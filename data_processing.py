import os
import pandas as pd
from sqlalchemy import create_engine
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

def get_multiples(df):
    # Convert 'valuation_by_revenue' to numeric values, replacing 'NaT' with NaN
    df['valuation_by_revenue'] = pd.to_numeric(df['valuation_by_revenue'], errors='coerce')

    # Group by 'deal_type_1' and 'deal_type_2' and calculate the median of 'valuation_by_revenue'
    medians_1 = df.groupby('deal_type')['valuation_by_revenue'].median()
    medians_2 = df.groupby('deal_type_2')['valuation_by_revenue'].median()

    # Return both sets of medians as a tuple
    return medians_1, medians_2

def get_revenue(df):
    # Convert 'valuation_by_revenue' to numeric values, replacing 'NaT' with NaN
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce')

    # Group by 'deal_type_1' and 'deal_type_2' and calculate the median of 'revenue'
    medians_1 = df.groupby('deal_type')['revenue'].median()
    medians_2 = df.groupby('deal_type_2')['revenue'].median()

    # Return both sets of medians as a tuple
    return medians_1, medians_2

def get_deal_size(df):
    # Convert 'valuation_by_revenue' to numeric values, replacing 'NaT' with NaN
    df['deal_size'] = pd.to_numeric(df['deal_size'], errors='coerce')

    # Group by 'deal_type_1' and 'deal_type_2' and calculate the median of 'valuation_by_revenue'
    medians_1 = df.groupby('deal_type')['deal_size'].median()
    medians_2 = df.groupby('deal_type_2')['deal_size'].median()

    # Return both sets of medians as a tuple
    return medians_1, medians_2

def get_valuation(df):
    # Convert 'valuation_by_revenue' to numeric values, replacing 'NaT' with NaN
    df['post_valuation'] = pd.to_numeric(df['post_valuation'], errors='coerce')

    # Group by 'deal_type_1' and 'deal_type_2' and calculate the median of 'valuation_by_revenue'
    medians_1 = df.groupby('deal_type')['post_valuation'].median()
    medians_2 = df.groupby('deal_type_2')['post_valuation'].median()

    # Return both sets of medians as a tuple
    return medians_1, medians_2

def get_runway(df):
    exclude_deal_types = [
        'Acquisition Financing', 'Add-on', 'Bonds', 
        'Corporate Divestiture', 'NaT', 
        'Recapitalization', 'Series D1'
    ]

    # Convert 'Deal Date' to datetime format if not already
    df['deal_date'] = pd.to_datetime(df['deal_date'])

    # Filter out the rows with excluded deal types
    df = df[~df['deal_type_2'].isin(exclude_deal_types)]

    # Sort by 'Company ID' and 'Deal No.'
    df = df.sort_values(by=['company_id', 'deal_no_'])

    # Calculate the time difference between consecutive deals for each company
    df['Next Deal Date'] = df.groupby('company_id')['deal_date'].shift(-1)
    df['Time to Next Deal'] = (df['Next Deal Date'] - df['deal_date']).dt.days

    # Group by 'Deal Type 2' and calculate the median time difference
    median_runway = df.groupby('deal_type_2')['Time to Next Deal'].median() / 365

    return median_runway

import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Geocoding function
def geocode_city(city_name):
    try:
        geolocator = Nominatim(user_agent="vrs-comps")
        location = geolocator.geocode(city_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except GeocoderTimedOut:
        return None, None

def map_cities(cities):
    world_map = folium.Map(location=[20, 0], zoom_start=2)  # Center of the map

    # Add a marker for each city
    for city in cities:
        latitude, longitude = geocode_city(city)
        if latitude is not None and longitude is not None:
            folium.Marker([latitude, longitude], popup=city).add_to(world_map)

    world_map.save('map.html')

def main():
    table_name = 'deals'
    source_file = 'test_1'
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("Database connection string not found in environment variables")

    try:
        engine = create_engine(db_url)
        query = f"SELECT * FROM {table_name} where source_file='{source_file}'"
        df = pd.read_sql_query(query, engine)

        # multiples = get_multiples(df[['deal_type', 'deal_type_2', 'valuation_by_revenue']])
        # revenue = get_revenue(df[['deal_type', 'deal_type_2', 'revenue']])
        # deal_size = get_deal_size(df[['deal_type', 'deal_type_2', 'deal_size']])
        # valuation = get_valuation(df[['deal_type', 'deal_type_2', 'post_valuation']])
        # runway = get_runway(df[['company_id', 'deal_no_', 'deal_type_2', 'deal_date']])
        # world_map = map_cities(df['company_city'].unique().tolist())
        print("map saved")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
