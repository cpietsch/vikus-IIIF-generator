import requests, json, os, time, logging, sys
import asyncio
import aiohttp
import random
import time
import logging

from manifest import Manifest
class Crawler:
    def __init__(self,*args,**kwargs):
        self.url = kwargs.get('url', None)
        self.client = kwargs.get('client')
        self.limitRecursion = kwargs.get('limitRecursion', False)
        self.cache = kwargs.get('cache', None)
        self.semaphore = kwargs.get('semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0) )
        self.session = kwargs.get('session')
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.workers = kwargs.get('worker', 1)

        self.logger.info("init crawler")
        self.logger.info("url: {}".format(self.url))

    async def getManifest(self):
        if self.url:
            #asyncio.run(self.runWorkers())
            return await self.runManifestWorkers()
    

    async def getJson(self,url, session, retries = 5):
        for i in range(retries):
            try:
                async with session.get(url) as response:
                    return await response.text()
            except Exception as e:
                self.logger.error(e)
                self.logger.error("retry {i} {url}" .format(i=i, url=url))
                await asyncio.sleep(1)
        return None


    async def getJsonFromCache(self, url, session):
        self.logger.info("get cache for {}".format(url))
        if self.cache.exists(url):
            self.logger.info("cache hit")
            cached = self.cache.get(url)
            return json.loads(cached)
        else:
            self.logger.info("cache miss")
            data = await self.getJson(url, session)
            if data is not None:
                self.logger.info("cache set")
                self.cache.set(url, data)
                return json.loads(data)
            else:
                return None
    
    async def manifestWorker(self, name, queue):
        self.logger.info("worker {} started".format(name))
        async with aiohttp.ClientSession() as session:
            while True:
                # Get a "work item" out of the queue.
                prio, manifest = await queue.get()
                data = await self.getJsonFromCache(manifest.url, session)
                manifest.load(data)

                if manifest.data.get('items', False):
                    for item in manifest.data.get('items'):
                        # print("{} added {}".format(name, item.get('id')))
                        child = Manifest(
                            url=item.get('id'),
                            depth=manifest.depth+1,
                            tree=manifest.tree,
                            parent = manifest,
                            crawler = self,
                        )
                        manifest.add(child)
                        # print(item.get('type'))
                        if item.get('type') == 'Collection' or item.get('type') == 'Manifest':
                            queue.put_nowait((prio + 1 + random.uniform(0, 1), child))

                # Notify the queue that the "work item" has been processed.
                queue.task_done()

                self.logger.info(f'prio: {prio} {manifest.label} done with {len(manifest.children)} children, {queue.qsize()} items left')


    async def runManifestWorkers(self):
        self.logger.info("load manifests from {}".format(self.url))
        # Create a queue that we will use to store our "workload".
        queue = asyncio.PriorityQueue()

        manifest = Manifest(url=self.url)

        queue.put_nowait((0, manifest))

        # loop = asyncio.get_event_loop()
        tasks = []
        for i in range(self.workers):
            task = asyncio.create_task(self.manifestWorker(f'worker-{i}', queue))
            tasks.append(task)

        await queue.join()

        # Cancel our worker tasks.
        for task in tasks:
            task.cancel()
        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("load manifests done")
        return manifest


