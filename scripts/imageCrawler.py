import hashlib
import requests
import json
import os
import time
import logging
import sys
import asyncio
import aiohttp
import random
import time
import logging
from rich.progress import Progress
from helpers import calculateThumbnailSize


class ImageCrawler:
    def __init__(self, *args, **kwargs):
        self.client = kwargs.get('client')
        self.limitRecursion = kwargs.get('limitRecursion', False)
        self.cache = kwargs.get('cache', None)
        self.semaphore = kwargs.get(
            'semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0))
        self.session = kwargs.get('session')
        self.logger = kwargs.get('logger', logging.getLogger('ImageCrawler'))
        self.numWorkers = kwargs.get('numWorkers', 1)
        self.callback = kwargs.get('callback', None)
        self.path = kwargs.get('path', "../data")
        self.queue = asyncio.Queue()
        self.logger.debug("init crawler")
        self.tasks = []
        self.done = []
        self.instanceId = kwargs.get('instanceId', 'default')
        self.size = 0
        self.completed = 0
        self.skipCache = kwargs.get('skipCache', False)

        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def addFromManifests(self, manifests):
        #thumbnailSize = calculateThumbnailSize(len(manifests))
        #print("thumbnailSize {}".format(thumbnailSize))

        for manifest in manifests:
            self.addFromManifest(manifest)

    def addFromManifest(self, manifest, size=224):
        thumbnailUrl = manifest.getThumbnailUrl(size)
        id = manifest.getId()
        self.logger.debug("adding {}".format(thumbnailUrl))
        if thumbnailUrl is not None:
            self.size += 1
            self.queue.put_nowait((id, thumbnailUrl))

    def makeFilename(self, url):
        # id is an hash
        id = hashlib.md5(url.encode('utf-8')).hexdigest()
        filename = id + ".jpg"
        # create 2 subfolders
        # first subfolder is the first 2 chars of the hash
        # second subfolder is the last 2 chars of the hash
        subfolder1 = id[0:2]
        subfolder2 = id[-2:]
        path = os.path.join(self.path, subfolder1, subfolder2)
        # create path
        if not os.path.exists(path):
            os.makedirs(path)
        filepath = os.path.join(path, filename)
        return filepath

    async def download(self, url, id, session):
        self.logger.debug("download {}".format(url))

        filePath = self.makeFilename(url)
        if os.path.exists(filePath) and not self.skipCache:
            return filePath

        async with session.get(url, allow_redirects=True) as response:
            if response.status == 200:
                self.logger.debug("downloading {}".format(url))
                data = await response.read()
                with open(filePath, 'wb') as f:
                    f.write(data)
                return filePath
            else:
                return None

    async def imageWorker(self, name):
        self.logger.debug("[red]imageworker {} started".format(name))
        # with Progress() as progress:
        #     task = progress.add_task("imageworker {} downloading".format(name), total=int(self.queue.qsize/self.workers))
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    (id, url) = await self.queue.get()
                except asyncio.CancelledError:
                    self.logger.debug("imageworker {} cancelled".format(name))
                    return

                self.logger.debug("{} downloading {}".format(name, url))
                try:
                    downloadedFile = await self.download(url, id, session)
                except Exception as e:
                    self.logger.error("{} {}".format(name, e))
                    downloadedFile = None

                if downloadedFile is not None:
                    self.logger.debug("{} downloaded {}".format(name, url))
                    self.done.append((id, downloadedFile))
                    if self.callback != None:
                        self.callback(id, downloadedFile)
                else:
                    self.logger.error(
                        "{} failed to download {}".format(name, url))

                self.completed += 1
                progress = self.completed / self.size
                # progress.update(task, advance=1)
                if(self.completed % 10 == 0):
                    await self.cache.postProgress(self.instanceId, {
                        'progress': progress,
                        'size': self.size,
                        'task': 'images',
                        'queue': self.queue.qsize(),
                        'completed': self.completed
                    })
                # await self.cache.redis.publish(self.instanceId, json.dumps({'task': 'crawlingImages', 'queue': self.queue.qsize() }))

                self.logger.debug(
                    f'{name}: {url} done, {self.queue.qsize()} items left')

                self.queue.task_done()

    async def runImageWorkers(self):
        self.logger.debug("runImageWorkers")
        # Create a queue that we will use to store our "workload".
        self.done = []
        self.size = self.queue.qsize()
        self.completed = 0

        for i in range(self.numWorkers):
            task = asyncio.create_task(self.imageWorker(f'worker-{i}'))
            self.tasks.append(task)

        await self.queue.join()

        # Cancel our worker tasks.
        for task in self.tasks:
            await asyncio.sleep(0)
            task.cancel()
            await task

        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*self.tasks, return_exceptions=True)

        await self.cache.postProgress(self.instanceId, {
            'progress': 1,
            'size': self.size,
            'task': 'images',
            'queue': self.queue.qsize(),
            'completed': self.completed
        })
        self.logger.debug("load images done")

        return self.done
