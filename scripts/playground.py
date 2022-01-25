from distutils.archive_util import make_archive
from distutils.log import debug
import os
from PIL import Image
import requests, json, os, time, logging, sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import redis
from iiif_downloader import Manifest as IIIFManifest
import asyncio
import aiohttp
import random
import time


from rich import pretty
pretty.install()
from rich.logging import RichHandler
from rich.console import Console
from rich.tree import Tree
from rich import print

debug = True

cache = redis.Redis(host='redis', port=6379)
semaphore = asyncio.Semaphore(debug and 10 or -1) 

# clear redis cache
def clearCache():
    cache.flushdb()

#clearCache()

logging.basicConfig(level=logging.DEBUG, handlers=[RichHandler()])
logger = logging.getLogger('rich')

url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"

async def getJson(url):
    retries = 5
    async with aiohttp.ClientSession() as session:
        for i in range(retries):
            try:
                async with session.get(url) as response:
                    return await response.text()
            except Exception as e:
                logger.error(e)
                logger.error("retry {} {url}".format(i))
                await asyncio.sleep(1)
        return None


async def getJsonFromCache(url):
    logger.info("get cache for {}".format(url))
    if cache.exists(url):
        logger.info("cache hit")
        cached = cache.get(url)
        return json.loads(cached)
    else:
        logger.info("cache miss")
        data = await getJson(url)
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

async def worker(name, queue):
    while True:
        # Get a "work item" out of the queue.
        await asyncio.sleep(1)
        priority, manifest = await queue.get()
        logger.info("{} got {}".format(name, manifest.id))

        # Sleep for the "sleep_for" seconds.
        await manifest.load()
        
        if manifest.data.get('items', False):
            for item in manifest.data.get('items'):
                print("{} added {}".format(name, item.get('id')))
                child = Manifest(url=item.get('id'), depth=manifest.depth+1)
                queue.put(asyncio.ensure_future((priority+1, child)))
                # manifest.children.append(child)

        queue.task_done()
        print(f'{name} {priority} {manifest.id}')


class Manifest:
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get('url', '')
        self.data = {}
        self.children = []
        self.maxload = debug and 10 or -1
        self.depth = kwargs.get('depth', 0)
        self.loaded = False
        self.url = kwargs.get('url', '')
        self.parent = kwargs.get('parent', None)
        self.label = None
        self.tree =  kwargs.get('tree', None)

    async def load(self):
        if self.url:
            logger.info("get manifest from url {}".format(self.url))
            self.data = await getJsonFromCache(self.url)
            if self.id != self.data.get('id'):
                logger.warning("url {} does not match id {}".format(self.url, self.data.get('id')))
            self.id = self.data.get('id')
            self.label = getLabel(self.data)
            if(self.tree is None):
                self.tree = Tree(f":open_file_folder: [link {self.id}]{self.label}")
            else:
                self.tree = self.tree.add(f":open_file_folder: [link {self.id}]{self.label}")

    async def loadChildren(self):
        if self.data.get('items', False) and not self.loaded:
            for item in self.data.get('items')[:self.maxload]:
                child = Manifest(url=item.get('id'), depth=self.depth+1, parent = self, tree=self.tree)
                await child.load()
                self.children.append(child)
        self.loaded = True

    async def loadDeep(self):
        for item in self.children:
            await item.loadChildren()





# 'label': {'en': ['Works by Genre']}
def getLabel(data):
    labels = list(data.get("label").values())[0]
    label = labels[0]
    return label

async def main():
    # Create a queue that we will use to store our "workload".
    # queue = asyncio.PriorityQueue()

    # Generate random timings and put them into the queue.

    manifestEntry = Manifest(url=url, debug=True)
    await manifestEntry.load()
    await manifestEntry.loadChildren()
    await manifestEntry.loadDeep()
    # console.log(manifestEntry.data)
    print(manifestEntry.tree)

    # await manifestEntry.loadChildren()

    # await crawl(manifestEntry)
    print('Done')


asyncio.run(main())

async def crawl(manifest):
    print("crawl {}".format(manifest.id))
    await manifest.load()
    
    logger.info(manifest.data, log_locals=True)
    # await manifest.loadChildren()

    # if manifest.data.get('items', False):
    #         for item in manifest.data.get('items'):
    #             print("added {}".format(item.get('id')))
    #             child = Manifest(url=item.get('id'), depth=manifest.depth+1)
    #             manifest.children.append(child)
    #             if(manifest.depth < 2):
    #                 await crawl(child)
    #             # await asyncio.ensure_future(crawl(child))

    return manifest


# m = Manifest(url=url)
# m.loatItems()
# #m.loadDeep()

# IIIFManifest(url='https://iiif.harvardartmuseums.org/manifests/object/299843').save_images()