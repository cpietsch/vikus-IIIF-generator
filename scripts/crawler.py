import requests, json, os, time, logging, sys
import redis
import asyncio
import aiohttp
import random
import time
import logging

from rich.tree import Tree


class Crawler:
    def __init__(self,*args,**kwargs):
        self.url = kwargs.get('url', None)
        self.client = kwargs.get('client')
        self.limitRecursion = kwargs.get('limitRecursion', False)
        self.cache = kwargs.get('cache', redis.Redis(host='redis', port=6379))
        self.semaphore = kwargs.get('semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0) )
        self.session = kwargs.get('session')
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.workers = kwargs.get('worker', 1)

        self.logger.info("init crawler")
        self.logger.info("url: {}".format(self.url))

    async def run(self):
        if self.url:
            #asyncio.run(self.runWorkers())
            return await self.runWorkers()
    

    async def getJson(self,url):
        retries = 5
        async with aiohttp.ClientSession() as session:
            for i in range(retries):
                try:
                    async with session.get(url) as response:
                        return await response.text()
                except Exception as e:
                    self.logger.error(e)
                    self.logger.error("retry {} {url}".format(i))
                    await asyncio.sleep(1)
            return None


    async def getJsonFromCache(self, url):
        self.logger.info("get cache for {}".format(url))
        if self.cache.exists(url):
            self.logger.info("cache hit")
            cached = self.cache.get(url)
            return json.loads(cached)
        else:
            self.logger.info("cache miss")
            data = await self.getJson(url)
            if data is not None:
                self.logger.info("cache set")
                self.cache.set(url, data)
                return json.loads(data)
            else:
                return None
    
    async def worker(self, name, queue):
        while True:
            # Get a "work item" out of the queue.
            prio, manifest = await queue.get()

            data = await self.getJsonFromCache(manifest.url)
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


    async def runWorkers(self):
        self.logger.info("load manifests from {}".format(self.url))
        # Create a queue that we will use to store our "workload".
        queue = asyncio.PriorityQueue()

        manifest = Manifest(url=self.url)

        queue.put_nowait((0, manifest))

        tasks = []
        for i in range(self.workers):
            task = asyncio.create_task(self.worker(f'worker-{i}', queue))
            tasks.append(task)

        await queue.join()

        # Cancel our worker tasks.
        for task in tasks:
            task.cancel()
        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("load manifests done")
        return manifest


class Manifest:
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get('url', '')
        self.data = {}
        self.children = []
        self.depth = kwargs.get('depth', 0)
        self.loaded = False
        self.url = kwargs.get('url', '')
        self.parent = kwargs.get('parent', None)
        self.label = None
        self.tree =  kwargs.get('tree', None)
        self.type = None
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.crawler = kwargs.get('crawler', None)
        #self.path = self.parent and self.id.replace(self.parent.id, '') or self.id

    def load(self, data=None):
        if data:
            self.logger.info("get manifest from url {}".format(self.url))
            self.data = data
            if self.id != self.data.get('id'):
                self.logger.warning("url {} does not match id {}".format(self.url, self.data.get('id')))
            self.id = self.data.get('id')
            self.label = self.getLabel(self.data)
            self.type = self.data.get('type')

            if(self.tree is None):
                self.tree = Tree(f":open_file_folder: [link {self.id}]{self.id}")
            else:
                emoji = self.type == 'Collection' and ':open_file_folder:' or ':framed_picture:'
                self.tree = self.tree.add(f"{emoji} [link {self.id}]{self.id}")

            return self
    
    def add(self, child):
        self.children.append(child)

    def getLabel(self, data):
        labels = list(data.get("label").values())[0]
        label = labels[0]
        return label

    
    def getThumbnail(self):
        thumbnails = self.data.get('thumbnail')
        if isinstance(thumbnails, list):
            return thumbnails[0].get('id')
        else:
            return None

    def getFlatList(self, manifest):
        list = []
        if manifest.type == 'Manifest':
            list.append(manifest)

        for item in manifest.children:
            if item.type == 'Manifest':
                list.extend(self.getFlatList(item))

        return list

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




# async def main():
   
#     # await manifestEntry.load()
#     # await manifestEntry.loadChildren()
#     # await manifestEntry.loadDeep()
#     # console.log(manifestEntry.data)
#     # print(manifestEntry.tree)

#     manifest = await loadManifests(url);

#     manifests = getFlatList(manifest)
#     thumbnails = [ manifest.getThumbnail() for manifest in manifests ]

#     print(manifest.tree)
#     print(thumbnails)
#     print('Done')


# if __name__ == "__main__":
#     asyncio.run(main())

