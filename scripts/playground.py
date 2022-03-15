
# from PIL import Image
import requests
import json
import os
import time
import logging
import sys
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
from rich.progress import Progress

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
from dimensionReductor import DimensionReductor
from sharpsheet import Sharpsheet

import pandas as pd
from pandas.io.json import json_normalize

pretty.install()

debug = False
loggingLevel = logging.DEBUG if debug else logging.INFO

logging.basicConfig(
    level=loggingLevel,
    # format="%(message)s",
    datefmt="%X",
    handlers=[RichHandler(
        show_time=True, rich_tracebacks=True, tracebacks_show_locals=True)]
)
logger = logging.getLogger('rich')

#url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Broadsides"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Myths_and_legends"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Advertisements"
url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Stickers"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Watercolors"

@duration
async def test():

    cache = Cache()
    # cache.clear()

    manifest = Manifest(url=url)
    dataPath = createFolder("../data/{}".format(manifest.shortId))
    thumbPath = createFolder("{}/images/thumbs".format(dataPath))
    print(thumbPath)

    manifestCrawler = ManifestCrawler(cache=cache, workers=2)
    manifest = await manifestCrawler.crawl(manifest)
    manifests = manifest.getFlatList(manifest, type='Canvas')
    #manifests = manifests[:2]

    metadata = [m.getMetadata() for m in manifests]
    dataframe = pd.DataFrame(metadata)
    dataframe.to_csv(dataPath + '/metadata.csv', index=False)
    print(dataframe)

    imageCrawler = ImageCrawler(workers=8, path=thumbPath)
    imageCrawler.addFromManifests(manifests)
    images = await imageCrawler.runImageWorkers()

    spriter = Sharpsheet(logger=logger)
    await spriter.generate(thumbPath)

    featureExtractor = FeatureExtractor(
        "openai/clip-vit-base-patch32", "cpu", cache=cache, overwrite=False)
    featureExtractor.load_model()
    (ids, features) = featureExtractor.concurrent_extract_features(images)

    # print(ids, features)
    # print(features[0])

    umaper = DimensionReductor(n_neighbors=15, min_dist=0.5, cache=cache)
    embedding = umaper.fit_transform(features)
    umaper.saveToCsv(embedding, dataPath, ids)

    # print(embedding)
    # print(manifest.tree)
    # print(thumbnails)
    print('Done')

if __name__ == "__main__":
    asyncio.run(test())
