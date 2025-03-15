"""
Process order folders and prepare data for LLM.
"""
import os
import json
import shutil
from pathlib import Path
import logging
from extract import extract_text, initialize_documentai
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_order_folder(order_folder):
    """
    Process all documents in an order folder.
    
    Args:
        order_folder: Path to the order folder
        
    Returns:
        Dictionary with order data
    """
    order_path = Path(order_folder)
    order_id = order_path.name
    
    logger.info(f"Processing order: {order_id}")
    
    order_data = {
        "order_id": order_id,
        "documents": []
    }
    
    # Process all files in the order folder
    file_count = 0
    
    # First, initialize Google Document AI
    try:
        initialize_documentai()
    except Exception as e:
        logger.error(f"Failed to initialize Document AI: {str(e)}")
        return order_data
    
    # Process all files in the order folder
    for file_path in order_path.glob("*"):
        if not file_path.is_file():
            continue
            
        # Skip files that are too large
        if file_path.stat().st_size > config.MAX_FILE_SIZE:
            logger.warning(f"Skipping file {file_path}, exceeds max size: {file_path.stat().st_size} bytes")
            continue
            
        # Skip unsupported file types
        if file_path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
            logger.warning(f"Skipping unsupported file type: {file_path}")
            continue
        
        file_count += 1
        logger.info(f"Processing file {file_count}: {file_path.name}")
        
        # Extract text from the document using appropriate method
        extracted_text = extract_text(file_path)
        
        # Save OCR text to the OCR directory
        ocr_file_path = config.OCR_DIR / f"{order_id}_{file_path.stem}.txt"
        with open(ocr_file_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        document_data = {
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content": extracted_text,
            "ocr_path": str(ocr_file_path)
        }
        
        order_data["documents"].append(document_data)
    
    logger.info(f"Completed processing {file_count} files for order {order_id}")
    return order_data

def format_llm_request(order_data):
    """
    Format the order data for the OpenAI API request.
    
    Args:
        order_data: Processed order data
        
    Returns:
        Formatted API request
    """
    # Create a partitioned content structure
    email_content = ""
    attachment_contents = []
    
    # Identify potential email documents (by name or extension)
    for doc in order_data["documents"]:
        if doc["file_type"] == ".eml" or "email" in doc["file_name"].lower():
            email_content = doc["content"]
            break
    
    # If no email found, check for text files that might be emails
    if not email_content:
        for doc in order_data["documents"]:
            if doc["file_type"] == ".txt" and ("email" in doc["file_name"].lower() or 
                                             "from:" in doc["content"].lower() or 
                                             "subject:" in doc["content"].lower()):
                email_content = doc["content"]
                break
    
    # Group the rest as attachments
    for i, doc in enumerate(order_data["documents"]):
        if doc["content"] != email_content:  # Skip the email we already identified
            attachment_contents.append({
                "index": i+1,
                "name": doc["file_name"],
                "type": doc["file_type"],
                "content": doc["content"]
            })
    
    # Build the structure to send to the LLM
    structured_content = f"ORDER ID: {order_data['order_id']}\n\n"
    
    # Add email content if found
    if email_content:
        structured_content += "===== EMAIL CONTENT =====\n\n"
        structured_content += email_content + "\n\n"
    
    # Add attachments
    for i, attachment in enumerate(attachment_contents):
        structured_content += f"===== ATTACHMENT {i+1}: {attachment['name']} =====\n"
        structured_content += f"File type: {attachment['type']}\n\n"
        structured_content += attachment['content'] + "\n\n"
    
    # Create the API request for OpenAI
    api_request = {
        "model": config.OPENAI_MODEL,
        "max_tokens": config.MAX_TOKENS,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": config.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Please analyze these workers compensation documents and extract the key information as specified in your instructions:\n\n{structured_content}"
            }
        ]
    }
    
    return api_request

def save_results(order_id, processed_data, api_request, llm_response):
    """
    Save processing results to output directory.
    
    Args:
        order_id: ID of the processed order
        processed_data: Processed order data
        api_request: LLM API request
        llm_response: LLM API response
    """
    # Create a clean version of processed_data with shorter content for readability
    clean_data = {
        "order_id": processed_data["order_id"],
        "documents": []
    }
    
    for doc in processed_data["documents"]:
        clean_doc = {
            "file_name": doc["file_name"],
            "file_type": doc["file_type"],
            "ocr_path": doc.get("ocr_path", "")
        }
        clean_data["documents"].append(clean_doc)
    
    # Extract JSON content from LLM response
    content = llm_response.get("content", "{}")
    try:
        # Try to parse JSON from the content - it might be wrapped in markdown code blocks
        if "```json" in content:
            # Extract JSON from markdown code block
            json_str = content.split("```json")[1].split("```")[0].strip()
            extracted_data = json.loads(json_str)
        elif "```" in content:
            # Extract from generic code block
            json_str = content.split("```")[1].split("```")[0].strip()
            extracted_data = json.loads(json_str)
        else:
            # Try to parse the whole content as JSON
            extracted_data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse JSON from LLM response for order {order_id}")
        extracted_data = {"error": "Could not parse JSON from response", "raw_content": content}
    
    # Prepare results
    results = {
        "order_id": order_id,
        "processed_data": clean_data,
        "extracted_data": extracted_data,
        "raw_llm_response": llm_response
    }
    
    output_path = config.OUTPUT_DIR / f"{order_id}_results.json"
    
    # Ensure output directory exists
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {output_path}")