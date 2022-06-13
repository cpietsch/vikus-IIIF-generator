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


class ImageCrawler:
    def __init__(self, *args, **kwargs):
        self.client = kwargs.get('client')
        self.limitRecursion = kwargs.get('limitRecursion', False)
        self.cache = kwargs.get('cache', None)
        self.semaphore = kwargs.get(
            'semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0))
        self.session = kwargs.get('session')
        self.logger = kwargs.get('logger', logging.getLogger('ImageCrawler'))
        self.workers = kwargs.get('workers', 1)
        self.callback = kwargs.get('callback', None)
        self.path = kwargs.get('path', "../data")
        self.queue = asyncio.Queue()
        self.logger.debug("init crawler")
        self.tasks = []
        self.done = []
        self.overwrite = kwargs.get('overwrite', False)
        self.instanceId = kwargs.get('instanceId', 'default')
        self.size = 0
        self.completed = 0

        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def addFromManifests(self, manifests):
        for manifest in manifests:
            self.addFromManifest(manifest)

    def addFromManifest(self, manifest):
        thumbnailUrl = manifest.getThumbnailUrl()
        id = manifest.getId()
        self.logger.debug("adding {}".format(thumbnailUrl))
        if thumbnailUrl is not None:
            self.size += 1
            self.queue.put_nowait((id, thumbnailUrl))

    def makeFilename(self, id):
        # id is an hash
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

        filePath = self.makeFilename(id)
        if os.path.exists(filePath) and not self.overwrite:
            return filePath

        async with session.get(url) as response:
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
                filepath = await self.download(url, id, session)
                if filepath is not None:
                    self.logger.debug("{} downloaded {}".format(name, url))
                    self.done.append((id, filepath))
                    if self.callback != None:
                        self.callback(id, filepath)
                else:
                    self.logger.debug(
                        "{} failed to download {}".format(name, url))

                self.completed += 1
                progress = self.completed / self.size
                # progress.update(task, advance=1)
                await self.cache.redis.xadd(self.instanceId, {
                    'progress': progress,
                    'size': self.size,
                    'task': 'crawlImages',
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

        for i in range(self.workers):
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

        await self.cache.redis.xadd(self.instanceId, {
            'progress': 1,
            'size': self.size,
            'task': 'crawlingImages',
            'queue': self.queue.qsize(),
            'completed': self.completed,
            'status': 'done'
        })
        self.logger.debug("load images done")

        return self.done
