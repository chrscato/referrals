"""
Client for geocoding addresses using OpenStreetMap Nominatim API.
"""
import logging
import requests
import time
import json
import os
import re
from pathlib import Path
from referrals import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cache directory for geocoding results
GEOCODE_CACHE_DIR = Path(config.BASE_DIR) / "data" / "geocode_cache"
os.makedirs(GEOCODE_CACHE_DIR, exist_ok=True)

def preprocess_address(address):
    """
    Preprocess address to improve geocoding success rate.
    
    Args:
        address: The address to preprocess
        
    Returns:
        Preprocessed address
    """
    if not address:
        return address
        
    # Dictionary of common state abbreviation corrections
    state_corrections = {
        "Flaz": "FL",
        "Fla": "FL",
        "Flor": "FL",
        "Flo": "FL",
        "Flaordia": "FL",
        "Fla.": "FL",
        "Cali": "CA",
        "Cal": "CA",
        "Calif": "CA",
        "Calif.": "CA",
        "Calf": "CA",
        "Illi": "IL",
        "Il": "IL",
        "Ill": "IL",
        "Ill.": "IL",
        # Add more as needed
    }
    
    # Try to fix state abbreviations
    parts = address.split(',')
    if len(parts) >= 2:
        # Check the part that might contain the state
        for i in range(1, min(len(parts), 3)):
            state_part = parts[i].strip().split()
            if state_part:
                for j, word in enumerate(state_part):
                    if word in state_corrections:
                        state_part[j] = state_corrections[word]
                        parts[i] = ' '.join(state_part)
    
    processed_address = ','.join(parts)
    
    # Replace special characters that might cause issues
    processed_address = processed_address.replace("'", "")
    
    # Remove apartment/suite numbers
    processed_address = processed_address.replace("Suite", "").replace("Apt", "").replace("Unit", "")
    processed_address = processed_address.replace("suite", "").replace("apt", "").replace("unit", "")
    processed_address = processed_address.replace("#", "")
    
    # Remove common address suffixes that might cause issues
    for suffix in [" Suite", " Ste", " Apartment", " Apt", " Unit", " #"]:
        if suffix in processed_address:
            # Find the suffix and remove everything after it until the next comma
            pos = processed_address.find(suffix)
            end_pos = processed_address.find(",", pos)
            if end_pos > pos:
                processed_address = processed_address[:pos] + processed_address[end_pos:]
            else:
                processed_address = processed_address[:pos]
    
    return processed_address.strip()

def geocode_zipcode(zipcode):
    """
    Special handling for US zip codes using a more reliable geocoding service.
    
    Args:
        zipcode: US zip code (5 digits)
        
    Returns:
        Dictionary with latitude, longitude, and address details or None if geocoding fails
    """
    # Validate zip code format
    if not re.match(r'^\d{5}$', zipcode):
        logger.warning(f"Invalid zip code format: {zipcode}")
        return None
        
    # Generate a cache key from the zip code
    cache_key = f"zip_{zipcode}"
    cache_file = GEOCODE_CACHE_DIR / f"{cache_key}.json"
    
    # Check if we have a cached result
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Using cached zip code result for: {zipcode}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading zip code cache: {str(e)}")
    
    try:
        # Use a more reliable US-specific geocoding service
        url = f"https://api.zippopotam.us/us/{zipcode}"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('places'):
            logger.warning(f"No location found for zip code: {zipcode}")
            return None
            
        # Get the first place (usually the main city for the zip code)
        place = data['places'][0]
        
        # Now use Nominatim to get precise coordinates
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{place['place name']}, {place['state']}, {zipcode}, USA",
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        headers = {
            "User-Agent": "WorkersCompProcessor/1.0",
            "Accept": "application/json"
        }
        
        time.sleep(1)  # Respect rate limits
        response = requests.get(nominatim_url, params=params, headers=headers)
        response.raise_for_status()
        
        results = response.json()
        if not results:
            logger.warning(f"No coordinates found for zip code: {zipcode}")
            return None
            
        result = results[0]
        
        geocoded_data = {
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
            "display_name": result["display_name"],
            "address_components": {
                "city": place['place name'],
                "state": place['state'],
                "postcode": zipcode,
                "country": "USA"
            },
            "original_address": zipcode
        }
        
        # Cache the result
        with open(cache_file, 'w') as f:
            json.dump(geocoded_data, f, indent=2)
            
        logger.info(f"Successfully geocoded zip code: {zipcode}")
        return geocoded_data
        
    except Exception as e:
        logger.error(f"Error geocoding zip code: {str(e)}")
        return None

def geocode_address(address, api_key=None):
    """
    Convert an address to geographic coordinates using OpenStreetMap Nominatim API.
    
    Args:
        address: The address to geocode
        api_key: Optional API key for commercial geocoding services (not required for standard Nominatim)
        
    Returns:
        Dictionary with latitude, longitude, and address details or None if geocoding fails
    """
    if not address:
        logger.warning("No address provided for geocoding")
        return None
        
    # Check if the input is just a zip code
    if re.match(r'^\d{5}$', address.strip()):
        return geocode_zipcode(address.strip())
        
    original_address = address
        
    # Generate a cache key from the address
    import hashlib
    cache_key = hashlib.md5(address.encode()).hexdigest()
    cache_file = GEOCODE_CACHE_DIR / f"{cache_key}.json"
    
    # Check if we have a cached result
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Using cached geocoding result for: {address}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading geocode cache: {str(e)}")
    
    # Use Nominatim API (OSM)
    nominatim_url = "https://nominatim.openstreetmap.org/search"
    
    headers = {
        "User-Agent": "WorkersCompProcessor/1.0",  # Required by Nominatim
        "Accept": "application/json"
    }
    
    # Try with original address first
    def try_geocode(query_address):
        params = {
            "q": query_address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        # Add API key if provided
        if api_key:
            params["key"] = api_key
        
        # Respect Nominatim's usage policy (max 1 request per second)
        time.sleep(1)
        
        response = requests.get(nominatim_url, params=params, headers=headers)
        response.raise_for_status()
        
        results = response.json()
        
        if not results:
            return None
            
        # Get the first (best) result
        result = results[0]
        
        return {
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
            "display_name": result["display_name"],
            "address_components": result.get("address", {}),
            "importance": result.get("importance", 0),
            "original_address": original_address
        }
    
    try:
        logger.info(f"Geocoding address: {address}")
        
        # First try with the original address
        geocoded_data = try_geocode(address)
        
        # If that fails, try with preprocessed address
        if not geocoded_data:
            processed_address = preprocess_address(address)
            logger.info(f"First attempt failed. Trying with preprocessed address: {processed_address}")
            
            if processed_address != address:
                geocoded_data = try_geocode(processed_address)
        
        # If that still fails, try with just city, state, zip
        if not geocoded_data:
            # Extract city, state, zip from address
            parts = address.split(',')
            if len(parts) >= 2:
                # Assume format like "Street, City, State ZIP"
                city_state_zip = ','.join(parts[1:]).strip()
                logger.info(f"Second attempt failed. Trying with just city/state/zip: {city_state_zip}")
                geocoded_data = try_geocode(city_state_zip)
        
        if geocoded_data:
            # Cache the result
            with open(cache_file, 'w') as f:
                json.dump(geocoded_data, f, indent=2)
                
            logger.info(f"Successfully geocoded address: {address}")
            return geocoded_data
        else:
            logger.warning(f"All geocoding attempts failed for address: {address}")
            return None
            
    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}")
        return None

def reverse_geocode(lat, lon, api_key=None):
    """
    Convert geographic coordinates to an address using OpenStreetMap Nominatim API.
    
    Args:
        lat: Latitude
        lon: Longitude
        api_key: Optional OSM API key for increased rate limits
        
    Returns:
        Dictionary with address details or None if reverse geocoding fails
    """
    # Generate a cache key from the coordinates
    cache_key = f"{lat}_{lon}".replace(".", "_")
    cache_file = GEOCODE_CACHE_DIR / f"reverse_{cache_key}.json"
    
    # Check if we have a cached result
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Using cached reverse geocoding result for: {lat}, {lon}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading reverse geocode cache: {str(e)}")
    
    # Use Nominatim API (OSM)
    nominatim_url = "https://nominatim.openstreetmap.org/reverse"
    
    headers = {
        "User-Agent": "WorkersCompProcessor/1.0",  # Required by Nominatim
        "Accept": "application/json"
    }
    
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1
    }
    
    # Add API key if provided
    if api_key:
        params["key"] = api_key
    
    try:
        logger.info(f"Reverse geocoding coordinates: {lat}, {lon}")
        
        # Respect Nominatim's usage policy
        time.sleep(1)
        
        response = requests.get(nominatim_url, params=params, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        if "error" in result:
            logger.warning(f"Error in reverse geocoding response: {result['error']}")
            return None
            
        geocoded_data = {
            "display_name": result["display_name"],
            "address_components": result.get("address", {}),
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
        }
        
        # Cache the result
        with open(cache_file, 'w') as f:
            json.dump(geocoded_data, f, indent=2)
            
        logger.info(f"Successfully reverse geocoded coordinates: {lat}, {lon}")
        return geocoded_data
        
    except Exception as e:
        logger.error(f"Error reverse geocoding coordinates: {str(e)}")
        return None