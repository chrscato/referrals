"""
Configuration settings for the workers compensation processor with enhanced HCFA-like functionality.
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

# System prompt for the LLM with enhanced HCFA-like line item extraction
SYSTEM_PROMPT = """
You are an intelligent workers compensation intake processor. Your task is to extract key information from unstructured documents.

IMPORTANT: Always use the EXACT format specified below. Do not add additional fields or change the structure.

Return your response in this JSON structure:
{
  "patient_info": {
    "patient_name": {"value": "John Smith", "source": "email body", "confidence": "high"},
    "patient_address": {"value": "123 Main St, Anytown, CA 94001", "source": "attachment 2", "confidence": "medium"},
    "claim_number": {"value": "WC-12345-67", "source": "email body", "confidence": "high"},
    "adjustor_info": {"value": "Mark Johnson, Liberty Mutual, mark.johnson@example.com, 555-123-4567", "source": "email signature", "confidence": "high"},
    "employer_name": {"value": "ABC Company", "source": "attachment 1", "confidence": "high"},
    "employer_phone": {"value": "555-123-4567", "source": "attachment 1", "confidence": "medium"},
    "employer_address": {"value": "456 Business Ave, Anytown, CA 94001", "source": "attachment 1", "confidence": "medium"},
    "employer_email": {"value": "hr@abccompany.com", "source": "attachment 1", "confidence": "medium"}
  },
  "procedures": [
    {
      "service_description": {"value": "MRI of left shoulder", "source": "email body", "confidence": "high"},
      "cpt_code": {"value": "73221", "source": "attachment 1", "confidence": "high"},
      "icd10_code": {"value": "M75.102", "source": "attachment 1", "confidence": "high"},
      "location_request": {"value": "Preferred location: North County Imaging", "source": "email body", "confidence": "medium"},
      "referring_provider": {"value": "Dr. Jane Rodriguez (NPI: 1234567890)", "source": "attachment 1", "confidence": "high"},
      "additional_considerations": {"value": "Patient has history of rotator cuff injury", "source": "attachment 1", "confidence": "medium"}
    }
  ]
}

If a patient has multiple procedures, include each procedure as a separate object in the procedures array.
If any information is completely missing, use null for the value and "not found" for the source.
Do not include any additional fields or change the structure.
"""