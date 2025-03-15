"""
Main script to run the workers compensation processing workflow.
"""
import os
import sys
import argparse
import logging
import shutil
from pathlib import Path
import time

import config
from extract import initialize_documentai
from process import process_order_folder, format_llm_request, save_results
from llm_client import call_llm_api

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_all_orders():
    """
    Process all order folders in the input directory.
    """
    start_time = time.time()
    logger.info(f"Starting batch processing using OpenAI")
    
    # Ensure input directory exists
    if not os.path.exists(config.INPUT_DIR):
        logger.error(f"Input directory not found: {config.INPUT_DIR}")
        return
    
    # Get list of order folders
    order_folders = [f for f in config.INPUT_DIR.glob("*") if f.is_dir()]
    
    if not order_folders:
        logger.warning(f"No order folders found in {config.INPUT_DIR}")
        return
    
    logger.info(f"Found {len(order_folders)} order folders to process")
    
    # Initialize Document AI once for all orders
    try:
        initialize_documentai()
    except Exception as e:
        logger.error(f"Failed to initialize Document AI: {str(e)}")
        return
    
    # Process each order folder
    for order_folder in order_folders:
        order_id = order_folder.name
        logger.info(f"Processing order folder: {order_id}")
        
        try:
            # Step 1: Process documents in the order folder
            order_data = process_order_folder(order_folder)
            
            if not order_data["documents"]:
                logger.warning(f"No valid documents found in order folder: {order_id}")
                continue
            
            # Step 2: Format the data for LLM request
            api_request = format_llm_request(order_data)
            
            # Step 3: Call the LLM API
            llm_response = call_llm_api(api_request)
            
            # Step 4: Save results
            save_results(order_id, order_data, api_request, llm_response)
            
            # Optional: Move processed order to an archive folder
            # archive_path = config.INPUT_DIR.parent / "archive" / order_id
            # shutil.move(str(order_folder), str(archive_path))
            
            logger.info(f"Completed processing order: {order_id}")
        except Exception as e:
            logger.error(f"Error processing order {order_id}: {str(e)}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Batch processing completed in {elapsed_time:.2f} seconds")

def process_single_order(order_id):
    """
    Process a single order folder.
    
    Args:
        order_id: ID of the order to process
    """
    logger.info(f"Processing single order: {order_id}")
    
    order_folder = config.INPUT_DIR / order_id
    
    if not order_folder.exists() or not order_folder.is_dir():
        logger.error(f"Order folder not found: {order_folder}")
        return
    
    try:
        # Step 1: Process documents in the order folder
        order_data = process_order_folder(order_folder)
        
        if not order_data["documents"]:
            logger.warning(f"No valid documents found in order folder: {order_id}")
            return
        
        # Step 2: Format the data for LLM request
        api_request = format_llm_request(order_data)
        
        # Step 3: Call the LLM API
        llm_response = call_llm_api(api_request)
        
        # Step 4: Save results
        save_results(order_id, order_data, api_request, llm_response)
        
        logger.info(f"Completed processing order: {order_id}")
    except Exception as e:
        logger.error(f"Error processing order {order_id}: {str(e)}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Workers Compensation Document Processing")
    parser.add_argument("--order", help="Process a single order by ID")
    
    args = parser.parse_args()
    
    # Check if Google credentials file exists
    if not os.path.exists(config.GOOGLE_CREDENTIALS_PATH):
        logger.error(f"Google credentials file not found: {config.GOOGLE_CREDENTIALS_PATH}")
        sys.exit(1)
    
    if args.order:
        process_single_order(args.order)
    else:
        process_all_orders()

if __name__ == "__main__":
    main()