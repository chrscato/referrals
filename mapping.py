"""
Functions for creating maps based on geocoded addresses.
Updated to work with enhanced HCFA-like data format.
"""
import logging
import requests
import os
from pathlib import Path
import time
import io
from PIL import Image
import config
from geocoding_client import geocode_address

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_static_map(latitude, longitude, zoom=14, width=600, height=400, api_key=None, order_id=None):
    """
    Generate a static map using OpenStreetMap and save it locally.
    
    Args:
        latitude: Latitude for map center
        longitude: Longitude for map center
        zoom: Zoom level (1-19)
        width: Map width in pixels
        height: Map height in pixels
        api_key: Optional OSM API key
        order_id: Optional order ID to associate with the map
        
    Returns:
        Path to the saved map image
    """
    # Ensure maps directory exists
    os.makedirs(config.MAPS_DIR, exist_ok=True)
    
    # Generate map filename
    filename = f"map_{latitude}_{longitude}_{zoom}".replace(".", "_")
    if order_id:
        filename = f"{order_id}_map"
    
    map_path = config.MAPS_DIR / f"{filename}.png"
    
    # Check if map already exists
    if map_path.exists():
        logger.info(f"Using existing map at {map_path}")
        return map_path
    
    # OpenStreetMap Static Map API (via third-party service since OSM doesn't provide an official static map API)
    # We're using staticmap.openstreetmap.de as an example
    static_map_url = "https://staticmap.openstreetmap.de/staticmap.php"
    
    params = {
        "center": f"{latitude},{longitude}",
        "zoom": zoom,
        "size": f"{width}x{height}",
        "markers": f"{latitude},{longitude},red",
        "attribution": "true"
    }
    
    # If API key provided and using a different service that accepts it
    if api_key and config.MAP_PROVIDER != "openstreetmap":
        params["key"] = api_key
    
    try:
        logger.info(f"Generating static map for coordinates: {latitude}, {longitude}")
        
        # Respect service usage policy
        time.sleep(1)
        
        response = requests.get(static_map_url, params=params)
        response.raise_for_status()
        
        # Save the map image
        with open(map_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Successfully saved map to {map_path}")
        return map_path
        
    except Exception as e:
        logger.error(f"Error generating static map: {str(e)}")
        return None

def process_address_for_mapping(address, order_id=None, api_key=None):
    """
    Process a patient address for mapping.
    
    Args:
        address: The patient address to map
        order_id: Order ID for the patient
        api_key: Optional OSM API key
        
    Returns:
        Dictionary with geocoding data and map path
    """
    if not config.ENABLE_GEOCODING:
        logger.info("Geocoding is disabled in configuration")
        return None
    
    if not address:
        logger.warning("No address provided for mapping")
        return None
    
    try:
        # Step 1: Geocode the address
        api_key = api_key or config.OSM_API_KEY
        geocode_data = geocode_address(address, api_key)
        
        if not geocode_data:
            logger.warning(f"Could not geocode address: {address}")
            return None
            
        # Step 2: Generate a static map
        map_path = generate_static_map(
            latitude=geocode_data["latitude"],
            longitude=geocode_data["longitude"],
            api_key=api_key,
            order_id=order_id
        )
        
        # Step 3: Return mapping data
        mapping_data = {
            "geocode_data": geocode_data,
            "map_path": str(map_path) if map_path else None
        }
        
        return mapping_data
        
    except Exception as e:
        logger.error(f"Error processing address for mapping: {str(e)}")
        return None

def add_mapping_to_results(results, api_key=None):
    """
    Add mapping data to order processing results.
    
    Args:
        results: Order processing results dictionary
        api_key: Optional OSM API key
        
    Returns:
        Updated results dictionary with mapping data
    """
    if not config.ENABLE_GEOCODING:
        logger.info("Geocoding is disabled in configuration")
        return results
    
    try:
        # Extract patient address from results
        order_id = results.get("order_id")
        
        extracted_data = results.get("extracted_data", {})
        # Use the normalized structure
        patient_info = extracted_data.get("patient_info", {})
        patient_address_data = patient_info.get("patient_address", {})
        patient_address = patient_address_data.get("value") if isinstance(patient_address_data, dict) else None
        
        if not patient_address:
            logger.warning(f"No patient address found in results for order {order_id}")
            results["mapping_data"] = {"status": "no_address_found"}
            return results
            
        # Process the address for mapping
        mapping_data = process_address_for_mapping(
            address=patient_address,
            order_id=order_id,
            api_key=api_key or config.OSM_API_KEY
        )
        
        if mapping_data:
            results["mapping_data"] = mapping_data
            logger.info(f"Added mapping data to results for order {order_id}")
        else:
            results["mapping_data"] = {"status": "geocoding_failed"}
            
        return results
        
    except Exception as e:
        logger.error(f"Error adding mapping to results: {str(e)}")
        results["mapping_data"] = {"status": "error", "message": str(e)}
        return results