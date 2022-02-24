
# from PIL import Image
import requests, json, os, time, logging, sys
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import asyncio
import aiohttp
import random
import traceback
import hashlib

import numpy as np

from rich import pretty
from rich.logging import RichHandler
# from rich.console import Console
# from rich.theme import Theme
from rich import print
# console = Console(theme=Theme({"logging.level": "green"}))

from manifestCrawler import ManifestCrawler
from imageCrawler import ImageCrawler
from cache import Cache
from helpers import *
from manifest import Manifest
from features import FeatureExtractor
from umaper import Umaper


pretty.install()

debug = False
loggingLevel = logging.DEBUG if debug else logging.INFO

logging.basicConfig(
    level=loggingLevel,
    # format="%(message)s",
    datefmt="%X",
    handlers=[RichHandler(show_time=True, rich_tracebacks=True, tracebacks_show_locals=True)]
)
logger = logging.getLogger('rich')

#url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Broadsides"
url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Myths_and_legends"


@duration
async def main():

    cache = Cache()
    #cache.clear()
    
    manifest = Manifest(url=url)
    dataPath = createFolder("../data/{}".format(manifest.shortId))
    thumbPath = createFolder("{}/images/thumbs".format(dataPath))
    
    print(thumbPath)
    
    manifestCrawler = ManifestCrawler(
        cache=cache,
        workers=2,
        #callback=imageCrawler.addFromManifest
    )
    manifest = await manifestCrawler.crawl(manifest)
    
    imageCrawler = ImageCrawler(workers=8, path=thumbPath)
    canvasList = manifest.getFlatList(manifest, type='Canvas')
    canvasList = canvasList[:1000]
    
    for canvas in canvasList:
        imageCrawler.addFromManifest(canvas)

    images = await imageCrawler.runImageWorkers()
    print(images)


    featureExtractor = FeatureExtractor("openai/clip-vit-base-patch32", "cpu", cache=cache)
    featureExtractor.load_model()

    features = featureExtractor.concurrent_extract_features(images)

    # print(features)
    
    ids = [id for (id, path) in images]
    umaper = Umaper(n_neighbors=3, min_dist=0.1, cache=cache)
    embedding = umaper.fit_transform(features)
    umaper.saveToCsv(embedding, dataPath, ids)
    
    # print(embedding)
    # print(manifest.tree)
    # print(thumbnails)
    print('Done')

def makeDataCsv(images, dataPath):
    #print(manifest.tree)
    #print(thumbnails)
    print('Done')

@duration
async def collect():

    cache = Cache()
    #cache.clear()
    
    manifest = Manifest(url=url)
    dataPath = createFolder("../data/{}".format(manifest.shortId))
    thumbPath = createFolder("{}/images/thumbs".format(dataPath))
    
    # print(thumbPath)
    
    manifestCrawler = ManifestCrawler(
        cache=cache,
        workers=2,
    )
    manifest = await manifestCrawler.crawl(manifest)

    list = manifest.getFlatList(manifest, type='Canvas')

    print(len(list))
    # print(list[0])
    # print(list[0].data)
    # print(list[0].getLargeImageUrl())

    imagesFromList = []
    for canvas in list:
        # print(canvas.getLargeImageUrl())
        imagesFromList.append((canvas.getThumbnailUrl(), canvas.getImageUrl(), canvas.getLargeImageUrl()))

    print(imagesFromList[0])


    print('Done')

if __name__ == "__main__":
    asyncio.run(main())

