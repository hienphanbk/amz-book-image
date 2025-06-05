import logging

def configure_logging(app_name='app', log_level=logging.INFO, log_file=None):
    """
    Simple logging configuration for the app.
    Args:
        app_name (str): Logger name.
        log_level (int): Logging level.
        log_file (str, optional): If set, logs will also be written to this file.
    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)

    # Remove all handlers associated with the logger object
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Optional file handler
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

