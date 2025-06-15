from src.workflow.controller import WorkflowController
from src.config_loader import ConfigLoader
from src.workflow.logger import AppLogger
import os

def main():
    # Load configuration
    config_loader = ConfigLoader(config_file="config/config.ini")
    config = config_loader.get_all_config()

    # Initialize logger
    log_file = config.get("app", {}).get("log_file", "logs/app.log")
    logger = AppLogger(log_file=log_file).get_logger()
    logger.info("Application started.")

    # Initialize and run the workflow controller
    workflow_controller = WorkflowController(config)
    workflow_controller.run_workflow()

    logger.info("Application finished.")

if __name__ == "__main__":
    main()


