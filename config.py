"""
Configuration settings for the workers compensation processor.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from external file
env_path = r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Intake AI Agent\keys.env"
load_dotenv(env_path)

# Base paths
BASE_DIR = Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Intake AI Agent")
INPUT_DIR = BASE_DIR / "data" / "orders"
OUTPUT_DIR = BASE_DIR / "data" / "results"
OCR_DIR = BASE_DIR / "data" / "ocr"
MAPS_DIR = BASE_DIR / "data" / "maps"

# Ensure directories exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OCR_DIR, exist_ok=True)
os.makedirs(MAPS_DIR, exist_ok=True)

# Google Document AI Settings
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\OCR\bill-review-ocr-529ae52caf66.json")
GOOGLE_PROJECT_ID = "704440646290"
GOOGLE_LOCATION = "us"
GOOGLE_PROCESSOR_ID = "8ecc3543a9209b03"

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# OSM API key is optional and only needed for commercial geocoding services
OSM_API_KEY = os.getenv("OSM_API_KEY", "")  # Optional commercial geocoding API key

# Mapping Configuration
ENABLE_GEOCODING = True  # Flag to enable/disable geocoding functionality
GEOCODE_CACHE_EXPIRY = 30  # Cache geocoding results for 30 days
MAP_PROVIDER = "openstreetmap"  # Options: "openstreetmap", "google", "mapbox"

# LLM Settings
OPENAI_MODEL = "gpt-3.5-turbo"
MAX_TOKENS = 4000

# Document Processing
SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".eml", ".txt"]
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# System prompt for the LLM
SYSTEM_PROMPT = """
You are an intelligent workers compensation intake processor. Your task is to extract key information from unstructured documents which may include emails, PDFs, and other attachments.

Focus on identifying and extracting ONLY these critical pieces of information:
1. Patient/Claimant Name (note: sometimes referred to as "claimant" or just "patient")
2. Patient Address (full address if available)
3. Order Request (the specific service or treatment being requested)
4. Location Request (any special instructions around where to schedule the service, specific provider or location)
5. Referring Provider (the original provider who requested the service, ideally name and NPI)
6. The Adjustor's name and contact information (typically a part of the email signature)
7. Additional Considerations (any special instructions, medical history, or important details relevant to the order)

IMPORTANT INSTRUCTIONS:
- Different parts of the information may appear in different documents (email body, attachments, etc.)
- Text may contain OCR errors, especially in handwritten portions
- Look for variations in terminology (patient/claimant, request/order, etc.)
- If you find conflicting information, prioritize the most recent document or the most detailed source
- For each piece of information, note which document it came from (e.g., "found in email" or "from attachment 1")
- If information is unclear or potentially incorrect due to OCR issues, indicate your uncertainty
- Always extract the complete patient address when available, as this will be used for geocoding and mapping

Format your response as a JSON object like this:
{
  "patient_name": {"value": "John Smith", "source": "email body", "confidence": "high"},
  "patient_address": {"value": "123 Main St, Anytown, CA 94001", "source": "attachment 2", "confidence": "medium"},
  "order_request": {"value": "MRI of left shoulder", "source": "email body", "confidence": "high"},
  "location_request": {"value": "Preferred location: North County Imaging", "source": "email body", "confidence": "medium"},
  "referring_provider": {"value": "Dr. Jane Rodriguez (NPI: 1234567890)", "source": "attachment 1", "confidence": "high"},
  "adjustor_info": {"value": "Mark Johnson, Liberty Mutual, mark.johnson@example.com, 555-123-4567", "source": "email signature", "confidence": "high"},
  "additional_considerations": {"value": "Patient has history of rotator cuff injury", "source": "attachment 1", "confidence": "medium"}
}

If any information is completely missing, use null for the value and "not found" for the source.
"""