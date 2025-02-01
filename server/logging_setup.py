import google.cloud.logging
import logging

def _optimizations():
    logging.logThreads = False
    logging.logProcesses = False
    logging.logMultiprocessing = False
    logging.logAsyncioTasks = False
    
def setup_logging():
    try:
        client = google.cloud.logging.Client()
        client.setup_logging(log_level=logging.INFO)
        _optimizations()
        # Function names are hardcoded in the log data 
        # for speed up (avoiding sys._getframe() calls)
        logging._srcfile = None 
    except Exception as e:
        logging.basicConfig(
            level=logging.INFO, 
            format="%(asctime)s - %(funcName)s - %(levelname)s - %(message)s")
        _optimizations()
        logging.error("Error setting up Google Cloud logging: %s", e)
        raise e