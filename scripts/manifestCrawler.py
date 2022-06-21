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

from manifest import Manifest


class ManifestCrawler:
    def __init__(self, *args, **kwargs):
        self.client = kwargs.get('client')
        self.instanceId = kwargs.get('instanceId', 'default')
        self.limitRecursion = kwargs.get('limitRecursion', 0)
        self.cache = kwargs.get('cache', None)
        # self.semaphore = kwargs.get(
        #     'semaphore', asyncio.Semaphore(self.limitRecursion and 10 or 0))
        self.session = kwargs.get('session')
        self.logger = kwargs.get(
            'logger', logging.getLogger('ManifestCrawler'))
        self.numWorkers = kwargs.get('numWorkers', 1)
        self.callback = kwargs.get('callback', None)
        self.size = 0
        self.completed = 0

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

                try:
                    data = await self.cache.getJson(manifest.url, session)
                    manifest.load(data)
                except:
                    self.logger.error(
                        "error loading manifest {}".format(manifest.url))
                    continue

                # if self.callback != None and manifest.type == 'Manifest':
                #     self.callback(manifest)

                if manifest.data.get('items', False):
                    for item in manifest.data.get('items'):
                        # print("{} added {}".format(name, item.get('id')))
                        child = Manifest(
                            url=item.get('id'),
                            depth=manifest.depth+1,
                            parent=manifest,
                        )
                        child.load(item)
                        manifest.add(child)

                        if self.limitRecursion != 0 and manifest.depth >= self.limitRecursion:
                            continue

                        if child.type == 'Collection' or child.type == 'Manifest':
                            # print("{} added {}".format(
                            #     self.completed, queue.qsize()))
                            self.size += 1
                            queue.put_nowait(
                                (prio + 1 + random.uniform(0, 1), child))

                self.completed += 1

                progress = self.completed / self.size

                await self.cache.redis.xadd(self.instanceId, {
                    'progress': progress,
                    'task': 'crawlCollection',
                    'queue': queue.qsize(),
                    'size': self.size,
                    'type': manifest.type,
                    'completed': self.completed
                })
                # await self.cache.redis.publish(self.instanceId, json.dumps({'task': 'crawlingManifest', 'queue': queue.qsize(), 'completed': self.completed, 'type': manifest.type}))

                self.logger.debug(
                    f'{name}: {prio} {manifest.label} done with {len(manifest.children)} children, {queue.qsize()} items left')

                # Notify the queue that the "work item" has been processed.
                queue.task_done()

    async def crawl(self, manifest):
        self.logger.debug("load manifests from {}".format(manifest.id))
        await self.cache.redis.delete(self.instanceId)
        # Create a queue that we will use to store our "workload".
        queue = asyncio.PriorityQueue()
        self.size = 1
        self.completed = 0

        tasks = []
        for i in range(self.numWorkers):
            task = asyncio.create_task(
                self.manifestWorker(f'worker-{i}', queue))
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

        await self.cache.redis.xadd(self.instanceId, {
            'progress': 1,
            'task': 'crawlingManifest',
            'queue': queue.qsize(),
            'size': self.size,
            'completed': self.completed,
            'type': 'done'
        })

        return manifest
