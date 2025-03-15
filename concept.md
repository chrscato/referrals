# Workers Compensation Intake Processor

A streamlined processing system for extracting key information from unstructured workers compensation referrals and intake documents.

## Overview

This project automates the extraction of critical information from workers compensation referrals that arrive via email with various attachments. It uses Google Document AI for OCR processing and OpenAI's GPT models to extract structured data from unstructured content.

### Key Features

- Processes emails and attachments in various formats (PDF, images, Word documents, etc.)
- Handles handwritten, fuzzy, and unstructured content
- Extracts key patient/claimant information, addresses, and order requests
- Provides confidence scores for extracted information
- Skips already processed orders to avoid duplicate work
- Organizes results into JSON format for easy integration with other systems

## Project Structure

```
workers_comp_test/
├── config.py                # Configuration settings
├── extract.py               # Document text extraction via Google Document AI
├── process.py               # Processes orders and formats for LLM
├── llm_client.py            # OpenAI API client
├── main.py                  # Main entry point
├── requirements.txt         # Project dependencies
├── .env                     # Environment variables
├── data/
│   ├── orders/              # Input folders with documents
│   ├── ocr/                 # Extracted text from documents
│   └── results/             # Processed results
```

## Getting Started

### Prerequisites

- Python 3.7+
- Google Document AI account with a processor set up for OCR
- OpenAI API key

### Installation

1. Clone the repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Set up environment variables in `.env`:
```
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### Usage

#### Preparing Data

1. Create a folder for each order in `data/orders/`
2. Place all documents related to the order in its folder
3. Include emails (.eml or .txt) and all relevant attachments

#### Running the Processor

Process all new orders:
```
python main.py
```

Process a specific order:
```
python main.py --order order123
```

Force reprocessing of orders that have already been processed:
```
python main.py --force
```

#### Results

Results are saved as JSON files in `data/results/` with the following structure:
```json
{
  "order_id": "order123",
  "processed_data": {
    "documents": [...]
  },
  "extracted_data": {
    "patient_name": {"value": "John Smith", "source": "email body", "confidence": "high"},
    "patient_address": {"value": "123 Main St, Anytown, CA 94001", "source": "attachment 2", "confidence": "medium"},
    "order_request": {"value": "MRI of left shoulder", "source": "email body", "confidence": "high"},
    "additional_considerations": {"value": "Patient has history of rotator cuff injury", "source": "attachment 1", "confidence": "medium"}
  }
}
```

## How It Works

1. **Document Processing**:
   - Each document is processed using Google Document AI for OCR
   - Text is extracted from PDFs, images, and other file types
   - OCR text is saved for reference and debugging

2. **Information Extraction**:
   - The system formats the extracted text with clear separation between email and attachments
   - OpenAI's GPT model analyzes the text to extract key information
   - The model notes which document each piece of information came from
   - Confidence levels are provided for each extraction

3. **Result Management**:
   - Results are saved as structured JSON
   - The system tracks processed orders to avoid duplication
   - Original OCR text is preserved for verification

## Customization

### Modifying Extraction Fields

Edit the system prompt in `config.py` to change what information is extracted:

```python
SYSTEM_PROMPT = """
You are an intelligent workers compensation intake processor...
[...]
"""
```

### Adding Pre-processing Steps

For challenging documents, consider adding pre-processing steps in `extract.py`:
- Image deskewing
- Contrast enhancement
- Noise reduction

## License

[Your License Here]

## Acknowledgments

- Google Document AI for OCR processing
- OpenAI for GPT models