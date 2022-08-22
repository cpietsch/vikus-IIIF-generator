from ast import And
import json
import os
import time
import logging
import asyncio
import randomname
import math

from zipfile import ZipFile
import zipfile

from PIL import Image
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
from sharpsheet import Sharpsheet
from featureExtractor import FeatureExtractor
from metadataExtractor import MetadataExtractor


pretty.install()

DATA_DIR = "../data"
DATA_IMAGES_DIR = "../data/images"
MANIFESTWORKERS = 4
IMAGEWORKERS = 4

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

metadataExtractor = MetadataExtractor(cache=cache)

url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Watercolors"


def create_info_md(config):
    path = config['path']
    infoPath = os.path.join(path, "info.md")
    with open(infoPath, "w") as f:
        f.write("# {}\n{}\n".format(config["label"], config["iiif_url"]))


def create_data_json(config):
    path = config['path']
    dataPath = os.path.join(path, "config.json")
    with open("files/config.json", "r") as f:
        data = json.load(f)

    data["project"]["name"] = config["label"]

    columns = 100
    if "numImages" in config:
        columns = math.isqrt(int(config["numImages"] * 3))
        data["loader"]["textures"]["medium"]["size"] = calculateThumbnailSize(
            int(config["numImages"]))
    data["projection"]["columns"] = columns

    if "metadataStructure" in config:
        data["detail"]["structure"] = config["metadataStructure"]

    with open(dataPath, "w") as f:
        f.write(json.dumps(data, indent=4))


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
        "collection": False,
    }

    saveConfig(config)

    return config


def saveConfig(config):
    config["updated"] = int(time.time())
    with open(os.path.join(config['path'], "instance.json"), "w") as f:
        f.write(json.dumps(config, indent=4))

    # this needs to be outside of this function
    create_info_md(config)
    create_data_json(config)


@duration
async def crawlCollection(url, instanceId, numWorkers=MANIFESTWORKERS, limitRecursion=False, skip_cache=False):
    manifest = Manifest(url=url)
    manifestCrawler = ManifestCrawler(
        cache=cache,
        limitRecursion=limitRecursion,
        numWorkers=MANIFESTWORKERS,
        instanceId=instanceId,
        skipCache=skip_cache
    )
    await manifestCrawler.crawl(manifest)
    manifests = manifest.getFlatList()

    return manifests


@duration
async def crawlImages(manifests, instanceId, numWorkers=IMAGEWORKERS, skip_cache=False):
    imageCrawler = ImageCrawler(
        numWorkers=numWorkers,
        path=DATA_IMAGES_DIR,
        instanceId=instanceId,
        cache=cache,
        skipCache=skip_cache
    )
    imageCrawler.addFromManifests(manifests)
    images = await imageCrawler.runImageWorkers()

    return images


@duration
async def makeMetadata(manifests, instanceId, path, extract_keywords=True, skip_cache=False):
    file = path + '/metadata.csv'
    metadataExtractor.skipCache = skip_cache
    metadata = await metadataExtractor.extract(
        manifests,
        extract_keywords=extract_keywords,
        instanceId=instanceId
    )
    metadataExtractor.saveToCsv(metadata, file)
    structure = metadataExtractor.makeDetailStructure(metadata)

    return {'file': file, 'structure': structure}


@duration
async def makeSpritesheets(files, instanceId, projectPath, spritesheetPath, spriteSize=226):
    spriter = Sharpsheet(logger=logger, instanceId=instanceId)
    thumbnailPath = createFolder("{}/images/thumbs".format(projectPath))

    for file in os.listdir(spritesheetPath):
        os.remove(os.path.join(spritesheetPath, file))
    for file in os.listdir(thumbnailPath):
        os.remove(os.path.join(thumbnailPath, file))

    for id, file in files:
        filePath = os.path.abspath(file)
        thumbnailFile = os.path.join(thumbnailPath, id + ".jpg")
        if not os.path.exists(thumbnailFile):
            resizeImage(filePath, thumbnailFile, spriteSize)

    await spriter.generateFromPath(thumbnailPath, outputPath=spritesheetPath, spriteSize=spriteSize)


@duration
async def makeFeatures(files, instanceId, batchSize, skip_cache=False):
    featureExtractor = FeatureExtractor(
        cache=cache, overwrite=False, instanceId=instanceId, skipCache=skip_cache)
    device = "cpu"
    if "USEGPU" in os.environ and os.environ['USEGPU'] is True:
        device = os.environ['USEGPU']
    featureExtractor.load_model(device)
    features = await featureExtractor.batch_extract_features_cached(files, batchSize)
    # print(features)
    return features


@duration
async def makeUmap(features, instanceId, path, ids, n_neighbors=15, min_dist=0.2, raster_fairy=False):
    from dimensionReduction import DimensionReduction
    umaper = DimensionReduction(n_neighbors=n_neighbors, min_dist=min_dist)
    embedding = umaper.fit_transform(features)
    print(raster_fairy)
    if raster_fairy and len(embedding) > 100:
        embedding = umaper.rasterfairy(embedding)
    umaper.saveToCsv(embedding, path, ids)
    return path


@duration
async def makeZip(path, instanceId, fileName="project.zip"):
    zipPath = os.path.join(path, fileName)
    with ZipFile(zipPath, 'w', zipfile.ZIP_DEFLATED) as zip:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename == fileName:
                    continue
                if "thumbs" in dirpath:
                    continue
                zip.write(os.path.join(dirpath, filename),
                          os.path.relpath(os.path.join(dirpath, filename),
                                          os.path.join(path, '..')))

    return zipPath


async def test(url, path, instanceId):
    manifests = await crawlCollection(url, instanceId)
    print(manifests)
    # images = await crawlImages(manifests, instanceId, path)
    # print(images)


if __name__ == "__main__":
    asyncio.run(test(url, DATA_DIR + "/test", "test"))
