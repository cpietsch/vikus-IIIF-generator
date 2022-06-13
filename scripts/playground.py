
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
import randomname

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
# from features import FeatureExtractor
# from dimensionReductor import DimensionReductor
from sharpsheet import Sharpsheet

import pandas as pd
from pandas.io.json import json_normalize
import uuid

pretty.install()

DATA_DIR = "../data"
DATA_IMAGES_DIR = "../data/images"
MANIFESTWORKERS = 2

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

cache = Cache()
# cache.clear()

#url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Broadsides"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Myths_and_legends"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Advertisements"
#url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Stickers"
url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Watercolors"
#url = "https://iiif.bodleian.ox.ac.uk/iiif/manifest/e32a277e-91e2-4a6d-8ba6-cc4bad230410.json"


@duration
async def run_all(url, path, id):

    manifest = Manifest(url=url)
    # dataPath = createFolder("../data/{}".format(manifest.shortId))
    dataPath = createFolder(path)
    thumbPath = createFolder("{}/images/thumbs".format(dataPath))
    print(thumbPath)

    manifestCrawler = ManifestCrawler(cache=cache, numWorkers=2)
    manifest = await manifestCrawler.crawl(manifest)
    manifests = manifest.getFlatList(manifest, type='Canvas')
    #manifests = manifests[:2]

    metadata = [m.getMetadata() for m in manifests]
    dataframe = pd.DataFrame(metadata)
    dataframe.to_csv(dataPath + '/metadata.csv', index=False)
    # print(dataframe)

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

    umaper = DimensionReductor(n_neighbors=15, min_dist=0.2)
    embedding = umaper.fit_transform(features)
    umaper.saveToCsv(embedding, dataPath, ids)

    umaper = DimensionReductor(n_neighbors=3, min_dist=0.2)
    embedding = umaper.fit_transform(features)
    umaper.saveToCsv(embedding, dataPath, ids, "umap3")

    # print(embedding)
    # print(manifest.tree)
    # print(thumbnails)
    print('Done')
    print('Open http://localhost:8000/viewer/?{}'.format(id))

    instance_url = 'http://localhost:8000/viewer/?{}'.format(id)

    return {
        'id': id,
        'url': instance_url,
        'path': path,
    }


def create_info_md(config):
    path = config['path']
    infoPath = os.path.join(path, "info.md")
    with open(infoPath, "w") as f:
        f.write("# {}\n{}\n".format(config["label"], config["iiif_url"]))


def create_config_json(iiif_url: str, label: str):
    # uid = str(uuid.uuid4())
    uid = randomname.get_name()
    if label is None:
        label = uid
    path = os.path.join(DATA_DIR, uid)
    os.mkdir(path)

    spritesheetPath = createFolder("{}/images/sprites".format(path))
    timestamp = int(time.time())

    config = {
        "id": uid,
        "label": label,
        "iiif_url": iiif_url,
        "path": path,
        "spritesheetPath": spritesheetPath,
        "created": timestamp,
        "updated": timestamp,
        "status": "created"
    }

    with open(os.path.join(path, "instance.json"), "w") as f:
        f.write(json.dumps(config, indent=4))

    return config


@duration
async def crawlCollection(url, instanceId, numWorkers=MANIFESTWORKERS, limitRecursion=False):
    manifest = Manifest(url=url)
    manifestCrawler = ManifestCrawler(
        cache=cache,
        limitRecursion=limitRecursion,
        numWorkers=MANIFESTWORKERS,
        instanceId=instanceId
    )
    await manifestCrawler.crawl(manifest)
    manifests = manifest.getFlatList(type='Canvas')

    return manifests


@duration
async def crawlImages(manifests, instanceId):
    imageCrawler = ImageCrawler(
        workers=5,
        path=DATA_IMAGES_DIR,
        instanceId=instanceId,
        cache=cache
    )
    imageCrawler.addFromManifests(manifests)
    images = await imageCrawler.runImageWorkers()

    return images


@duration
async def makeMetadata(manifests, instanceId, path):
    file = path + '/metadata.csv'
    metadata = [m.getMetadata() for m in manifests]
    dataframe = pd.DataFrame(metadata)
    dataframe.to_csv(file, index=False)

    return {'file': file, 'dataframe': dataframe}


@duration
async def makeSpritesheets(files, instanceId, projectPath, spritesheetPath):
    spriter = Sharpsheet(logger=logger, instanceId=instanceId)
    thumbnailPath = createFolder("{}/images/thumbs".format(projectPath))
    # make for each file a symlink into the thumbnailPath folder
    for file in files:
        symlinkFile = os.path.join(thumbnailPath, os.path.basename(file))
        if not os.path.exists(symlinkFile):
            os.symlink(file, symlinkFile)

    await spriter.generateFromPath(thumbnailPath, outputPath=spritesheetPath)


@duration
async def makeFeatures(files, instanceId):
    print("Extracting features import")
    from featureExtractor import FeatureExtractor
    print("Extracting features")

    featureExtractor = FeatureExtractor(
        "openai/clip-vit-base-patch32", "cpu", cache=cache, overwrite=False, instanceId=instanceId)
    featureExtractor.load_model()
    features = await featureExtractor.concurrent_extract_features(files)
    # print(features)
    return features


@duration
async def makeUmap(features, instanceId, path, ids, n_neighbors=15, min_dist=0.2):
    from dimensionReduction import DimensionReduction
    umaper = DimensionReduction(n_neighbors=n_neighbors, min_dist=min_dist)
    embedding = umaper.fit_transform(features)
    umaper.saveToCsv(embedding, path, ids)
    return path


async def test(url, path, instanceId):
    manifests = await crawlCollection(url, instanceId)
    print(manifests)
    # images = await crawlImages(manifests, instanceId, path)
    # print(images)


def saveConfig(config):
    with open(os.path.join(config['path'], "instance.json"), "w") as f:
        f.write(json.dumps(config, indent=4))


if __name__ == "__main__":
    asyncio.run(test(
        url, "../data/{}".format(hashlib.md5(url.encode('utf-8')).hexdigest()), "test"))
