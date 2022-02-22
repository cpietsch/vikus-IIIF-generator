
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
import pandas as pd

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
# from umaper import Umaper


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
    
    imageCrawler = ImageCrawler(workers=2, path=thumbPath)
    for manifest in manifest.getFlatList(manifest):
        imageCrawler.addFromManifest(manifest)

    images = await imageCrawler.runImageWorkers()
    print(images)

    featureExtractor = FeatureExtractor("openai/clip-vit-base-patch32", "cpu")
    featureExtractor.load_model()

    # features = []
    # for image in images:
    #     feature = featureExtractor.extract_features(image)
    #     # features = np.append(features, feature)
    #     features.append(feature)
    #     # print(features)

    imagePaths = [path for (id, path) in images]
    features = featureExtractor.batch_extract_features(imagePaths)

    # features = np.array(features)
    # print(features)

    umaper = Umaper(n_neighbors=3, min_dist=0.1)
    embedding = umaper.fit_transform(features)
    
    # print(embedding)

    dataframe = pd.DataFrame(data=embedding, columns=['x', 'y'])
    dataframe['id'] = [id for (id, path) in images]
    dataframe.set_index('id')

    dataframe.to_csv("{}/embedding.csv".format(dataPath), index=False)

    # print(manifest.tree)
    # print(thumbnails)
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
        #callback=imageCrawler.addFromManifest
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
    # for manifest in list:
    #     print(manifest)
        
    
    # thumbs = []
    # for manifest in manifest.getFlatList(manifest):
    #     t = manifest.getThumbnailUrls()
    #     print(manifest)
    #     thumbs.append(t)

    # print(len(thumbs))


    print('Done')

if __name__ == "__main__":
    asyncio.run(collect())

