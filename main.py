from dotenv import load_dotenv
import os
import tkinter as tk
import logging
from connectors.binance_futures import BinancefutureClient


log_filename = 'logfile.txt'
log_encoding = 'utf-8'
log_level = logging.DEBUG
log_format = '%(asctime)s [%(levelname)s] %(message)s'

logging.basicConfig(filename=log_filename, level=log_level, format=log_format)

# create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

logger.info("init main.py")

if __name__ == '__main__':

    # Get the Keys
    load_dotenv()
    logger.info("Loading Keys")
    public_key = os.environ.get("binance_test_public_key")
    secret_key = os.environ.get("binance_test_secret_key")

    if not public_key:
        logger.error("Public Key is missing.")
        logger.error("Quitting")
        quit()
    if not secret_key:
        logger.error("Secret key is missing.")
        logger.error("Quitting")
        quit()

    binance = BinancefutureClient(public_key, secret_key, True)



    # logger.debug('Starting TK')
    # root = tk.Tk()
    # root.configure(bg='gray12')
    # calibri_font = ("Calibri", 11, "normal")
    #
    # root.mainloop()
    # logger.debug('Exit TK')




