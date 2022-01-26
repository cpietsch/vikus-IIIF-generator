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

logging.basicConfig(level=logging.WARNING, handlers=[RichHandler()])
logger = logging.getLogger('rich')

# url = "https://iiif.wellcomecollection.org/presentation/v3/collections/genres"
# url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Broadsides"
url = "https://iiif.wellcomecollection.org/presentation/collections/genres/Myths_and_legends"

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
        self.type = None
        #self.path = self.parent and self.id.replace(self.parent.id, '') or self.id

    async def load(self):
        if self.url:
            logger.info("get manifest from url {}".format(self.url))
            self.data = await getJsonFromCache(self.url)
            if self.id != self.data.get('id'):
                logger.warning("url {} does not match id {}".format(self.url, self.data.get('id')))
            self.id = self.data.get('id')
            self.label = getLabel(self.data)
            self.type = self.data.get('type')

            if(self.tree is None):
                self.tree = Tree(f":open_file_folder: [link {self.id}]{self.id}")
            else:
                emoji = self.type == 'Collection' and ':open_file_folder:' or ':framed_picture:'
                self.tree = self.tree.add(f"{emoji} [link {self.id}]{self.id}")

            return self
    
    def add(self, child):
        self.children.append(child)

    
    def getThumbnail(self):
        thumbnails = self.data.get('thumbnail')
        if isinstance(thumbnails, list):
            return thumbnails[0].get('id')
        else:
            return None

    async def downloadThumbnail(self):
        if url:
            logger.info("download thumbnail {}".format(url))
            response = requests.get(url)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning("failed to download thumbnail {}".format(url))
                return None
        else:
            logger.warning("no thumbnail url")
            return None
    
    def getChildren(self):
        return self.children


    # async def loadChildren(self):
    #     if self.data.get('items', False) and not self.loaded:
    #         for item in self.data.get('items')[:self.maxload]:
    #             child = Manifest(url=item.get('id'), depth=self.depth+1, parent = self, tree=self.tree)
    #             await child.load()
    #             self.children.append(child)
    #     self.loaded = True

    # async def loadDeep(self):
    #     for item in self.children:
    #         await item.loadChildren()


async def worker(name, queue):
    while True:
        # Get a "work item" out of the queue.
        prio, manifest = await queue.get()

        await manifest.load()

        if manifest.data.get('items', False):
            for item in manifest.data.get('items'):
                # print("{} added {}".format(name, item.get('id')))
                child = Manifest(
                    url=item.get('id'),
                    depth=manifest.depth+1,
                    tree=manifest.tree,
                    parent = manifest
                )
                manifest.add(child)
                # print(item.get('type'))
                if item.get('type') == 'Collection' or item.get('type') == 'Manifest':
                    queue.put_nowait((prio + 1 + random.uniform(0, 1), child))

        # Notify the queue that the "work item" has been processed.
        queue.task_done()

        logger.info(f'prio: {prio} {manifest.label} done with {len(manifest.children)} children, {queue.qsize()} items left')

def getFlatList(manifest):
    list = []
    if manifest.type == 'Manifest':
        list.append(manifest)

    for item in manifest.children:
        if item.type == 'Manifest':
            list.extend(getFlatList(item))

    return list


async def loadManifests(url, workers=1):
    logger.info("load manifests from {}".format(url))
     # Create a queue that we will use to store our "workload".
    queue = asyncio.PriorityQueue()

    manifest = Manifest(url=url, debug=True)

    queue.put_nowait((0, manifest))

    tasks = []
    for i in range(workers):
        task = asyncio.create_task(worker(f'worker-{i}', queue))
        tasks.append(task)

    await queue.join()

    # Cancel our worker tasks.
    for task in tasks:
        task.cancel()
    # Wait until all worker tasks are cancelled.
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("load manifests done")
    return manifest

async def main():
   

    # await manifestEntry.load()
    # await manifestEntry.loadChildren()
    # await manifestEntry.loadDeep()
    # console.log(manifestEntry.data)
    # print(manifestEntry.tree)

    manifest = await loadManifests(url);

    manifests = getFlatList(manifest)
    thumbnails = [ manifest.getThumbnail() for manifest in manifests ]

    print(manifest.tree)
    print(thumbnails)
    print('Done')


asyncio.run(main())

