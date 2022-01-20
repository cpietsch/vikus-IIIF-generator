import os
from PIL import Image
import requests, json, os, time, logging, sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import redis

cache = redis.Redis(host='redis', port=6379)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('loader')



url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"


def getJson(url):
    retries = 5
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            else:
                return None
        except Exception as e:
            if retries == 0:
                return None
            retries -= 1
            time.sleep(0.5)

def getJsonFromCache(url):
    logger.info("get cache for {}".format(url))
    if cache.exists(url):
        logger.info("cache hit")
        cached = cache.get(url)
        return json.loads(cached)
    else:
        logger.info("cache miss")
        data = getJson(url)
        if data is not None:
            logger.info("cache set")
            cache.set(url, data)
            return json.loads(data)
        else:
            return None


def getLabel(data):
    labels = list(data.get("label").values())[0]
    label = labels[0]
    return label

default_verbose = True

class Manifest:
    def __init__(self, *args, **kwargs):
        self.id = ''
        self.json = {}
        self.items = []
        self.maxload = kwargs.get('maxload', 20)

        if kwargs.get('url', False):
            logger.info("get manifest from url {}".format(kwargs.get('url')))
            self.json = getJsonFromCache(kwargs.get('url'))
            self.id = self.json.get('id')
    def loatItems(self):
        if self.json.get('items', False):
            for item in self.json.get('items')[:self.maxload]:
                self.items.append(Manifest(url=item.get('id')))


def load(url):
    data = getJsonFromCache(url)
    print(data.get("type"))
    id = data.get("id")
    type = data.get("type")
    label = getLabel(data)
    print(label)
    if type == "Collection":
        for item in data.get("items"):
            print(getLabel(item))
            print(item.get("id"))
            print(item.get("type"))
            print(item.get("items"))
            print("\n")

#load(url)

m = Manifest(url=url)
m.loatItems()