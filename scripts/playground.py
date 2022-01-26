import os
from PIL import Image
import requests, json, os, time, logging, sys
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import redis
import asyncio
import aiohttp
import random
import time
import traceback
import hashlib

from rich import pretty
from rich.logging import RichHandler
from rich import print

from crawler import Crawler

pretty.install()

debug = True

cache = redis.Redis(host='redis', port=6379)

# clear redis cache
# cache.flushdb()

logging.basicConfig(level=logging.WARN, handlers=[RichHandler()])
logger = logging.getLogger('rich')

# url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"
# url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Broadsides"
url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Myths_and_legends"

def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
        # return absolute path
        return os.path.abspath(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)


class ImageDownloader:
    async def download(self, url, path):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    logger.info("downloading {}".format(url))
                    data = await response.read()
                    filename = hashlib.md5(data).hexdigest() + ".jpg"
                    filepath = os.path.join(path, filename)
                    with open(filepath, 'wb') as f:
                        f.write(data)
                    return filepath
                else:
                    return None

async def main():

    dataPath = createFolder("../data/images")
    print(dataPath)

    crawler = Crawler(url=url, cache=cache, logger=logger, workers=1)
    manifest = await crawler.getManifest()

    manifestsFlat = manifest.getFlatList(manifest)
    thumbnails = [ manifest.getThumbnail() for manifest in manifestsFlat ]

    downloader = ImageDownloader()

    for thumbnail in thumbnails:
        await downloader.download(thumbnail, dataPath)

    print(manifest.tree)
    print(thumbnails)
    print('Done')


if __name__ == "__main__":
    asyncio.run(main())

