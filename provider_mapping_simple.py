"""
Simplified module for mapping patient addresses to nearby providers based purely on distance.
"""
import logging
import sqlite3
import math
from pathlib import Path
import json
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database file path
PROVIDER_DB_PATH = r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\reference_tables\orders2.db"

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using the Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in miles
    """
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # Earth's radius in miles
    radius = 3956
    
    # Distance in miles
    distance = radius * c
    
    return distance

def find_nearest_providers(latitude, longitude, limit=3):
    """
    Find the nearest providers from the database based purely on distance.
    
    Args:
        latitude: Patient location latitude
        longitude: Patient location longitude
        limit: Maximum number of providers to return (default 3)
        
    Returns:
        List of nearby providers with distance information
    """
    if not latitude or not longitude:
        logger.warning("No coordinates provided for provider search")
        return []
    
    try:
        # Connect to the providers database
        conn = sqlite3.connect(PROVIDER_DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        # Log database connection attempt
        logger.info(f"Connecting to provider database: {PROVIDER_DB_PATH}")
        
        # First check if there are any providers in the database
        cursor.execute("SELECT COUNT(*) FROM providers")
        count = cursor.fetchone()[0]
        logger.info(f"Total providers in database: {count}")
        
        # Get all providers with coordinates (don't filter by type or distance)
        query = "SELECT * FROM providers WHERE lat IS NOT NULL AND lon IS NOT NULL AND lat != '' AND lon != ''"
        cursor.execute(query)
        
        providers = cursor.fetchall()
        logger.info(f"Found {len(providers)} providers with valid coordinates")
        
        # Also check if there's a structural issue
        if len(providers) == 0:
            # Check column names
            cursor.execute("PRAGMA table_info(providers)")
            columns = cursor.fetchall()
            logger.info(f"Provider table columns: {[col['name'] for col in columns]}")
            
            # Try a simple query
            cursor.execute("SELECT * FROM providers LIMIT 5")
            sample = cursor.fetchall()
            logger.info(f"Sample provider data available: {len(sample) > 0}")
        
        conn.close()
        
        # Calculate distance for each provider
        all_providers = []
        for provider in providers:
            # Skip providers with invalid coordinates
            try:
                prov_lat = float(provider['lat'])
                prov_lon = float(provider['lon'])
            except (ValueError, TypeError):
                continue
                
            # Calculate distance
            distance = calculate_distance(latitude, longitude, prov_lat, prov_lon)
            
            # Always add to list with distance
            provider_info = {
                'PrimaryKey': provider['PrimaryKey'],
                'DBA Name Billing Name': provider['DBA Name Billing Name'],
                'TIN': provider['TIN'],
                'State': provider['State'],
                'Status': provider['Status'],
                'Provider Type': provider['Provider Type'],
                'Provider Network': provider['Provider Network'],
                'City': provider['City'],
                'distance_miles': round(distance, 2)
            }
            all_providers.append(provider_info)
        
        # Sort by distance - pure distance-based, no filters
        all_providers.sort(key=lambda x: x['distance_miles'])
        
        # Return the closest N providers regardless of distance
        nearest_providers = all_providers[:limit]
        
        logger.info(f"Returning the {len(nearest_providers)} closest providers")
        return nearest_providers
        
    except Exception as e:
        logger.error(f"Error finding providers: {str(e)}")
        return []

def add_provider_mapping_to_results(results):
    """
    Add provider mapping data to order processing results.
    
    Args:
        results: Order processing results dictionary
        
    Returns:
        Updated results dictionary with provider mapping data
    """
    try:
        # Check if we have mapping data
        if "mapping_data" not in results or results["mapping_data"].get("status") == "geocoding_failed":
            logger.warning("No geocoding data available for provider mapping")
            results["provider_mapping"] = {"status": "geocoding_failed"}
            return results
        
        # Get geocode data
        geocode_data = results["mapping_data"].get("geocode_data")
        if not geocode_data:
            logger.warning("No geocode data in mapping_data")
            results["provider_mapping"] = {"status": "no_geocode_data"}
            return results
        
        # Get coordinates
        latitude = geocode_data.get("latitude")
        longitude = geocode_data.get("longitude")
        
        # Find nearest providers
        providers = find_nearest_providers(latitude, longitude)
        
        # Prepare provider mapping
        provider_mapping = {
            "status": "success" if providers else "no_providers_found",
            "patient_location": {
                "latitude": latitude,
                "longitude": longitude,
                "address": geocode_data.get("display_name")
            },
            "providers": providers
        }
        
        # Add to results
        results["provider_mapping"] = provider_mapping
        
        return results
        
    except Exception as e:
        logger.error(f"Error adding provider mapping to results: {str(e)}")
        results["provider_mapping"] = {"status": "error", "message": str(e)}
        return results


def test_database_connection():
    """Test the database connection and structure."""
    try:
        # Connect to the providers database
        conn = sqlite3.connect(PROVIDER_DB_PATH)
        cursor = conn.cursor()
        
        # Check if the providers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='providers'")
        if not cursor.fetchone():
            print("ERROR: 'providers' table does not exist in the database!")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(providers)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        required_columns = ['PrimaryKey', 'DBA Name Billing Name', 'TIN', 'State', 
                           'Status', 'Provider Type', 'Provider Network', 'City', 'lat', 'lon']
        
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            print(f"ERROR: Missing required columns: {missing_columns}")
            return False
            
        # Check for providers with coordinates
        cursor.execute("SELECT COUNT(*) FROM providers WHERE lat IS NOT NULL AND lon IS NOT NULL AND lat != '' AND lon != ''")
        coord_count = cursor.fetchone()[0]
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM providers")
        total_count = cursor.fetchone()[0]
        
        print(f"Database connection successful:")
        print(f"- Total providers: {total_count}")
        print(f"- Providers with coordinates: {coord_count}")
        
        # Sample data
        cursor.execute("SELECT * FROM providers WHERE lat IS NOT NULL AND lon IS NOT NULL AND lat != '' AND lon != '' LIMIT 3")
        sample = cursor.fetchall()
        
        if sample:
            print("\nSample provider data:")
            for provider in sample:
                print(f"- {provider[columns['DBA Name Billing Name'].index]}, {provider[columns['City'].index]}, {provider[columns['State'].index]}")
                print(f"  Coordinates: {provider[columns['lat'].index]}, {provider[columns['lon'].index]}")
        else:
            print("\nWARNING: No providers with valid coordinates found!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR connecting to database: {str(e)}")
        return False

if __name__ == "__main__":
    # Test database connection
    test_database_connection()