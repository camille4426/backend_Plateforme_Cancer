import logging
import colorlog

def get_logger(name: str):
    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        "[\033[35mLog projet\033[0m] %(log_color)s[%(levelname)s]%(reset)s %(asctime)s: %(message)s",
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red'
        },
        style='%'
    )
    handler.setFormatter(formatter)

    logger = colorlog.getLogger(name) # Pour ajout de nos propres logs
    logger.addHandler(handler)
    #logger.setLevel(logging.INFO)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    return logger