from vikus import crawlCollection
import json
import os
import time
import logging
import asyncio
import randomname
import math

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

import pandas as pd
from pandas.io.json import json_normalize

pretty.install()


cache = Cache()

url = "https://www.e-codices.unifr.ch/metadata/iiif/collection.json"
url = "https://resource.swissartresearch.net/manifest/zbz-collection"

logging.basicConfig(
    level=logging.DEBUG,
    # format="%(message)s",
    datefmt="%X",
    handlers=[RichHandler(
        show_time=True, rich_tracebacks=True, tracebacks_show_locals=True)]
)
logger = logging.getLogger('rich')


async def main():
    manifests = await crawlCollection(url, "test", numWorkers=10)
    manifests = manifests[:100]

    print("{} manifests".format(len(manifests)))
    for manifest in manifests:
        print(manifest.id, manifest.getThumbnailUrl())
    # metadataExtractor = MetadataExtractor()
    # metadata = metadataExtractor.extract(manifests)
    # details = metadataExtractor.makeDetailStructure(metadata)
    # print(metadata)

    #metadataExtractor.saveToCsv(metadata, "metadata.csv")


if __name__ == "__main__":
    asyncio.run(main())
