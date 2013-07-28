import logging

logger = logging.getLogger('')
logging.getLogger('yapsy').setLevel(logging.INFO)  # this one is way too verbose in debug
logging.getLogger('Rocket.Errors').setLevel(logging.INFO)  # this one is way too verbose in debug
logger.setLevel(logging.INFO)