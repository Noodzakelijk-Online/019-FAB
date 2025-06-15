from google.cloud import functions
from google.cloud import storage
import functions_framework
import os
import json

from src.workflow.controller import WorkflowController
from src.config_loader import ConfigLoader
from src.workflow.logger import AppLogger

# Initialize ConfigLoader and Logger globally for Cloud Functions
# This helps in reusing the initialized objects across invocations (warm starts)
config_loader = ConfigLoader(config_file="config/config.ini")
app_config = config_loader.get_all_config()

# Configure logger for Cloud Functions. Logs will go to Cloud Logging.
# No file handler needed for Cloud Functions.
logger = AppLogger(log_file=None).get_logger()

@functions_framework.cloud_event
def process_document_cloud_function(cloud_event):
    """Cloud Function to process documents triggered by GCS events.

    Args:
        cloud_event: The Cloud Event object containing event data.
                      Expected to be triggered by a Google Cloud Storage event.
    """
    data = cloud_event.data

    bucket_name = data["bucket"]
    file_name = data["name"]
    file_id = data["id"]
    event_type = cloud_event["type"]

    logger.info(f"Processing event_type: {event_type} for file: {file_name} in bucket: {bucket_name}")

    # Download the file from GCS to a temporary location
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    # Create a temporary directory for the file
    temp_dir = "/tmp/cloud_function_docs"
    os.makedirs(temp_dir, exist_ok=True)
    local_file_path = os.path.join(temp_dir, file_name)

    try:
        blob.download_to_filename(local_file_path)
        logger.info(f"File {file_name} downloaded to {local_file_path}")

        # Prepare a dummy document structure for the workflow controller
        # In a real scenario, you might pass more metadata from the GCS event
        document_data = {
            "id": file_id,
            "original_filename": file_name,
            "local_path": local_file_path,
            "source": "google_cloud_storage" # Indicate source
        }

        # Initialize and run a simplified workflow controller for this single document
        # Note: The full WorkflowController might be too heavy for a single Cloud Function invocation.
        # Consider refactoring if only specific processing steps are needed.
        # For this example, we'll assume a lightweight version or direct calls to processors.
        
        # Example: Directly calling a processor pipeline
        from src.document_processors.processor_pipeline import ProcessorPipeline
        processor_pipeline = ProcessorPipeline(app_config) # Use the globally loaded config
        processed_data = processor_pipeline.process_document(local_file_path)
        processed_data["document_id"] = file_id # Add document ID

        logger.info(f"Document {file_name} processed. Extracted data: {processed_data.get("extracted_data")}")

        # Further steps (categorization, data entry) would follow here,
        # potentially by calling other Cloud Functions or services.
        # For now, we'll just log the result.

        # Example: Categorization
        from src.categorizers.hybrid_categorizer import HybridCategorizer
        categorizer = HybridCategorizer(app_config)
        categorized_result = categorizer.categorize(processed_data)
        logger.info(f"Document {file_name} categorized as: {categorized_result.get("category")}")

        # Example: Data Entry (simplified, would need proper handler initialization)
        # from src.data_entry.mijngeldzaken_handler import MijngeldzakenHandler
        # mijngeldzaken_handler = MijngeldzakenHandler(app_config)
        # mijngeldzaken_handler.enter_data(processed_data) # This would need the categorized data

        return f"Successfully processed {file_name}"

    except Exception as e:
        logger.error(f"Error processing file {file_name}: {e}", exc_info=True)
        # In a real application, you might move the file to a dead-letter bucket
        # or trigger a manual review process here.
        raise # Re-raise the exception to indicate failure to Cloud Functions

@functions_framework.http
def trigger_workflow_http(request):
    """HTTP Cloud Function to trigger the full workflow.

    This function can be called via an HTTP request to start the entire
    automated bookkeeping workflow, similar to how `main.py` would run.
    """
    logger.info("HTTP trigger received. Starting full workflow.")
    
    # Initialize WorkflowController with the globally loaded config
    workflow_controller = WorkflowController(app_config)
    workflow_controller.run_workflow()

    return "Automated bookkeeping workflow triggered successfully!", 200


