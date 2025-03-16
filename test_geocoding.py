"""
Simple test script for the geocoding and mapping functionality.
"""
import os
import json
from pathlib import Path
from geocoding_client import geocode_address
from mapping import generate_static_map, process_address_for_mapping
import config

def test_geocoding():
    # Test addresses
    addresses = [
        "1600 Pennsylvania Ave NW, Washington, DC 20500",  # White House
        "350 Fifth Avenue, New York, NY 10118",           # Empire State Building
        "1 Infinite Loop, Cupertino, CA 95014"            # Apple HQ
    ]
    
    print("===== Testing Geocoding Functionality =====")
    
    for address in addresses:
        print(f"\nGeocoding address: {address}")
        
        # Test geocoding
        geocode_result = geocode_address(address)
        
        if geocode_result:
            print(f"✅ Successfully geocoded: {address}")
            print(f"  Coordinates: {geocode_result['latitude']}, {geocode_result['longitude']}")
            print(f"  Display name: {geocode_result['display_name']}")
            
            # Test map generation
            map_path = generate_static_map(
                latitude=geocode_result["latitude"],
                longitude=geocode_result["longitude"]
            )
            
            if map_path:
                print(f"✅ Generated map saved to: {map_path}")
            else:
                print("❌ Failed to generate map")
        else:
            print(f"❌ Failed to geocode address: {address}")
    
    print("\n===== Testing Complete =====")

def test_with_custom_address():
    """Test with a user-provided address."""
    address = input("\nEnter an address to geocode: ")
    
    if not address:
        print("No address provided.")
        return
    
    print(f"\nProcessing address: {address}")
    
    # Process address for mapping
    mapping_data = process_address_for_mapping(address)
    
    if mapping_data and mapping_data.get("geocode_data"):
        geocode_data = mapping_data["geocode_data"]
        print(f"✅ Successfully geocoded address:")
        print(f"  Coordinates: {geocode_data['latitude']}, {geocode_data['longitude']}")
        print(f"  Display name: {geocode_data['display_name']}")
        
        if mapping_data.get("map_path"):
            print(f"✅ Generated map saved to: {mapping_data['map_path']}")
        else:
            print("❌ Failed to generate map")
    else:
        print(f"❌ Failed to process address: {address}")

if __name__ == "__main__":
    # Make sure directories exist
    os.makedirs(config.MAPS_DIR, exist_ok=True)
    
    # Run tests
    test_geocoding()
    
    # Optionally test with custom address
    test_with_custom_address()