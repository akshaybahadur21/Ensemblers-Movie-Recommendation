from urllib import request
from flask import g, current_app
from flask_pymongo import PyMongo
from fluent import sender

def get_fluent_logger(name: str):
    fluent_logger = getattr(g, '_fluent_logger', None)
    if fluent_logger is None:
        fluent_logger = g._fluent_logger = sender.FluentSender(name, host='localhost', port=30971)
    return fluent_logger


def get_db():
    """
    Returns the global db instance. A PyMongo instance is created if not present in g.
    """
    db = getattr(g, '_database', None)
    if db is None:
        uri: str = current_app.config.get('DATABASE_URI')

        db = g._database = PyMongo(current_app, uri=uri)
    return db


def get_api_key():
    """
    Returns the global api key string.
    """
    api_key = getattr(g, '_api_key', None)
    if api_key is None:
        api_key = g._api_key = current_app.config.get('API_KEY')
    return api_key


def get_special_list():
    special_list = getattr(g, '_special_list', None)
    if special_list is None:
        special_list = g.special_list = current_app.config.get('SPECIAL_LIST')
    return special_list