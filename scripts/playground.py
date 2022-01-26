from distutils.archive_util import make_archive
from distutils.log import debug
from multiprocessing.dummy import Array
import os
from PIL import Image
import requests, json, os, time, logging, sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import redis
import asyncio
import aiohttp
import random
import time
import traceback

from rich import pretty
from rich.logging import RichHandler
from rich import print

from crawler import Crawler

pretty.install()

debug = True

cache = redis.Redis(host='redis', port=6379)

# clear redis cache
def clearCache():
    cache.flushdb()

logging.basicConfig(level=logging.WARNING, handlers=[RichHandler()])
logger = logging.getLogger('rich')

# url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"
# url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Broadsides"
url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Myths_and_legends"


async def main():
    #clearCache()
    # await manifestEntry.load()
    # await manifestEntry.loadChildren()
    # await manifestEntry.loadDeep()
    # console.log(manifestEntry.data)
    # print(manifestEntry.tree)

    logger.info("start")
    try:
        print("start")
        crawler = Crawler(url=url, cache=cache, logger=logger)
        manifest = await crawler.run()
    except Exception as e:
        logger.error(traceback.format_exc())

    manifests = manifest.getFlatList(manifest)
    thumbnails = [ manifest.getThumbnail() for manifest in manifests ]

    print(manifest.tree)
    print(thumbnails)
    print('Done')


if __name__ == "__main__":
    asyncio.run(main())

