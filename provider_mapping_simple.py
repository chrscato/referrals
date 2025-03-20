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

def clean_tin(tin):
    """Clean a TIN by removing all non-digit characters and ensuring 9 digits."""
    if not tin:
        return None
    # Remove all non-digit characters
    cleaned = ''.join(filter(str.isdigit, str(tin)))
    # Ensure exactly 9 digits
    return cleaned if len(cleaned) == 9 else None

def get_provider_rate(cursor, tin, proc_code):
    """Get the rate for a specific provider TIN and procedure code.
    
    Args:
        cursor: Database cursor
        tin: Provider TIN (will be cleaned)
        proc_code: Procedure code (will be trimmed)
        
    Returns:
        Rate if found, None otherwise
    """
    try:
        clean_tin_val = clean_tin(tin)
        if not clean_tin_val:
            return None
            
        # Trim the procedure code and convert to uppercase
        proc_code = str(proc_code).strip().upper()
        
        # Query the ppo table for the rate
        cursor.execute("""
            SELECT rate 
            FROM ppo 
            WHERE TRIM(TIN) = ? 
            AND TRIM(UPPER(proc_cd)) = ?
        """, (clean_tin_val, proc_code))
        
        result = cursor.fetchone()
        return float(result[0]) if result else None
        
    except Exception as e:
        logger.error(f"Error getting provider rate: {str(e)}")
        return None

def find_nearest_providers(latitude, longitude, proc_code=None, limit=3):
    """
    Find the nearest providers from the database based purely on distance.
    
    Args:
        latitude: Patient location latitude
        longitude: Patient location longitude
        proc_code: Optional procedure code to look up rates
        limit: Maximum number of providers to return (default 3)
        
    Returns:
        List of nearby providers with distance and rate information
    """
    if not latitude or not longitude:
        logger.warning("No coordinates provided for provider search")
        return []
    
    try:
        # Connect to the providers database
        conn = sqlite3.connect(PROVIDER_DB_PATH)
        cursor = conn.cursor()
        
        # Log database connection attempt
        logger.info(f"Connecting to provider database: {PROVIDER_DB_PATH}")
        
        # First check if there are any providers in the database
        cursor.execute("SELECT COUNT(*) FROM providers")
        count = cursor.fetchone()[0]
        logger.info(f"Total providers in database: {count}")
        
        # Get all providers with coordinates and required fields
        query = """
            SELECT 
                PrimaryKey,
                [DBA Name Billing Name],
                TIN,
                State,
                Status,
                [Provider Type],
                [Provider Network],
                City,
                lat,
                lon,
                Email,
                [Fax Number],
                Phone,
                Website
            FROM providers 
            WHERE lat IS NOT NULL 
            AND lon IS NOT NULL 
            AND lat != '' 
            AND lon != ''
            AND [DBA Name Billing Name] IS NOT NULL
            AND [DBA Name Billing Name] != ''
        """
        cursor.execute(query)
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Fetch all providers
        providers = cursor.fetchall()
        logger.info(f"Found {len(providers)} providers with valid coordinates")
        
        # Calculate distance for each provider and get rates if proc_code provided
        all_providers = []
        for provider in providers:
            # Create a dictionary with column names as keys
            provider_dict = dict(zip(column_names, provider))
            
            # Skip providers with invalid coordinates
            try:
                prov_lat = float(provider_dict['lat'])
                prov_lon = float(provider_dict['lon'])
            except (ValueError, TypeError):
                continue
                
            # Calculate distance
            distance = calculate_distance(latitude, longitude, prov_lat, prov_lon)
            
            # Add distance to provider info
            provider_dict['distance_miles'] = round(distance, 2)
            provider_dict['lat'] = prov_lat
            provider_dict['lon'] = prov_lon
            
            # Clean the TIN
            provider_dict['clean_tin'] = clean_tin(provider_dict['TIN'])
            
            # Get rate if procedure code provided
            if proc_code and provider_dict['clean_tin']:
                rate = get_provider_rate(cursor, provider_dict['clean_tin'], proc_code)
                provider_dict['rate'] = rate
            
            all_providers.append(provider_dict)
        
        conn.close()
        
        # Sort by distance - pure distance-based, no filters
        all_providers.sort(key=lambda x: x['distance_miles'])
        
        # Return the closest N providers regardless of distance
        nearest_providers = all_providers[:limit]
        
        logger.info(f"Returning the {len(nearest_providers)} closest providers")
        return nearest_providers
        
    except Exception as e:
        logger.error(f"Error finding providers: {str(e)}")
        import traceback
        traceback.print_exc()
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
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        required_columns = ['PrimaryKey', 'DBA Name Billing Name', 'TIN', 'State', 
                           'Status', 'Provider Type', 'Provider Network', 'City', 'lat', 'lon']
        
        missing_columns = [col for col in required_columns if col not in column_names]
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
        cursor.execute("""
            SELECT [DBA Name Billing Name], City, State, lat, lon 
            FROM providers 
            WHERE lat IS NOT NULL AND lon IS NOT NULL 
            AND lat != '' AND lon != '' 
            AND [DBA Name Billing Name] IS NOT NULL
            AND [DBA Name Billing Name] != ''
            LIMIT 3
        """)
        sample = cursor.fetchall()
        
        if sample:
            print("\nSample provider data:")
            for provider in sample:
                print(f"- {provider[0]}, {provider[1]}, {provider[2]}")
                print(f"  Coordinates: {provider[3]}, {provider[4]}")
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