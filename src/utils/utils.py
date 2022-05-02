from jproperties import Properties
import logging

logging.basicConfig(
    format='%(asctime)s %(module)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def get_properties(path):
    logging.info("Loading the properties")
    properties = Properties()
    with open(path, 'rb') as config_file:
        properties.load(config_file)
    return properties


def eval_bool(s):
    return s.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']


def print_banner():
    logging.info("""
    
    
███████╗███╗   ██╗███████╗███████╗███╗   ███╗██████╗ ██╗     ███████╗██████╗ ███████╗
██╔════╝████╗  ██║██╔════╝██╔════╝████╗ ████║██╔══██╗██║     ██╔════╝██╔══██╗██╔════╝
█████╗  ██╔██╗ ██║███████╗█████╗  ██╔████╔██║██████╔╝██║     █████╗  ██████╔╝███████╗
██╔══╝  ██║╚██╗██║╚════██║██╔══╝  ██║╚██╔╝██║██╔══██╗██║     ██╔══╝  ██╔══██╗╚════██║
███████╗██║ ╚████║███████║███████╗██║ ╚═╝ ██║██████╔╝███████╗███████╗██║  ██║███████║
╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝     ╚═╝╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚══════╝
                                                                                     

    
    """)
