
from PIL import Image
import requests, json, os, time, logging, sys
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import asyncio
import aiohttp
import random
import traceback
import hashlib

from rich import pretty
from rich.logging import RichHandler
# from rich.console import Console
# from rich.theme import Theme
from rich import print
# console = Console(theme=Theme({"logging.level": "green"}))

from crawler import ManifestCrawler, Cache, ImageCrawler

from helpers import *

pretty.install()

debug = True
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

    dataPath = createFolder("../data/images")
    print(dataPath)

    cache = Cache(
        #logger=logger
    )
    cache.clear()
    
    imageCrawler = ImageCrawler(workers=1, path=dataPath)
    manifestCrawler = ManifestCrawler(
        url=url, 
        cache=cache,
        #logger=logger,
        workers=2,
        callback=imageCrawler.addFromManifest
    )
    # manifest = await manifestCrawler.runManifestWorkers()
    manifests, images = await asyncio.gather(
        manifestCrawler.runManifestWorkers(),
        imageCrawler.run()
    )
    print(images)
    # manifestsFlat = manifest.getFlatList(manifest)
    # thumbnails = [ manifest.getThumbnail() for manifest in manifestsFlat ]

    # downloader = ImageDownloader()

    # for thumbnail in thumbnails:
    #     await downloader.download(thumbnail, dataPath)

    # print(manifest.tree)
    # print(thumbnails)
    print('Done')


if __name__ == "__main__":
    asyncio.run(main())

