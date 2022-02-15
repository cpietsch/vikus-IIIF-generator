import hashlib
import requests, json, os, time, logging, sys
import asyncio
import aiohttp
import random
import time
import logging

from manifest import Manifest
class ManifestCrawler:
    def __init__(self,*args,**kwargs):
        self.client = kwargs.get('client')
        self.limitRecursion = kwargs.get('limitRecursion', False)
        self.cache = kwargs.get('cache', None)
        self.semaphore = kwargs.get('semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0) )
        self.session = kwargs.get('session')
        self.logger = kwargs.get('logger', logging.getLogger('ManifestCrawler'))
        self.workers = kwargs.get('workers', 1)
        self.callback = kwargs.get('callback', None)

        self.logger.debug("init crawler")

    async def manifestWorker(self, name, queue):
        self.logger.debug("worker {} started".format(name))
        async with aiohttp.ClientSession() as session:
            while True:
                # Get a "work item" out of the queue.
                try:
                    prio, manifest = await queue.get()
                except asyncio.CancelledError:
                    self.logger.debug("worker {} cancelled".format(name))
                    return

                data = await self.cache.getJson(manifest.url, session)
                manifest.load(data)

                if self.callback != None and manifest.type == 'Manifest':
                    self.callback(manifest)

                if manifest.data.get('items', False):
                    for item in manifest.data.get('items'):
                        # print("{} added {}".format(name, item.get('id')))
                        child = Manifest(
                            url=item.get('id'),
                            depth=manifest.depth+1,
                            parent = manifest,
                        )
                        manifest.add(child)
                        
                        if self.limitRecursion and manifest.depth >= self.limitRecursion:
                            continue

                        if item.get('type') == 'Collection' or item.get('type') == 'Manifest':
                            queue.put_nowait((prio + 1 + random.uniform(0, 1), child))

                # Notify the queue that the "work item" has been processed.
                queue.task_done()
            
                self.logger.debug(f'{name}: {prio} {manifest.label} done with {len(manifest.children)} children, {queue.qsize()} items left')


    async def crawl(self, manifest):
        self.logger.debug("load manifests from {}".format(manifest.id))
        # Create a queue that we will use to store our "workload".
        queue = asyncio.PriorityQueue()

        

        tasks = []
        for i in range(self.workers):
            task = asyncio.create_task(self.manifestWorker(f'worker-{i}', queue))
            tasks.append(task)

        queue.put_nowait((0, manifest))

        await queue.join()
    
        # Cancel our worker tasks.
        for task in tasks:
            await asyncio.sleep(0)
            task.cancel()
            await task

        # Wait until all worker tasks are cancelled.
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(e)
        self.logger.debug("load manifests done")
  
        return manifest

class ImageCrawler:
    def __init__(self, *args, **kwargs):
        self.client = kwargs.get('client')
        self.limitRecursion = kwargs.get('limitRecursion', False)
        self.cache = kwargs.get('cache', None)
        self.semaphore = kwargs.get('semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0) )
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

        
    def addFromManifest(self, manifest):
        thumbnailUrl = manifest.getThumbnail()
        id = manifest.getId()
        self.logger.debug("adding {}".format(thumbnailUrl))
        if thumbnailUrl is not None:
            self.queue.put_nowait((id,thumbnailUrl))
    
    def makeFilename(self, id):
        filename = id + ".jpg"
        filepath = os.path.join(self.path, filename)
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
        self.logger.debug("imageworker {} started".format(name))
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
                    self.logger.debug("{} failed to download {}".format(name, url))
                self.queue.task_done()
                
                self.logger.debug(f'{name}: {url} done, {self.queue.qsize()} items left')

    async def runImageWorkers(self):
        self.logger.debug("runImageWorkers")
        # Create a queue that we will use to store our "workload".

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
        self.logger.debug("load images done")      
        
        return self.done
