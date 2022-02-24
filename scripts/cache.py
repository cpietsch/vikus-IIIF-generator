import logging
import redis
import asyncio
import requests, json, os, time, logging, sys
import numpy as np
import struct

class Cache:
    def __init__(self, *args, **kwargs):
        self.redis = kwargs.get('redis', redis.Redis(host='redis', port=6379))
        self.logger = kwargs.get('logger', logging.getLogger('cache'))
    
    def get(self, id):
        return self.redis.get(id)

    def set(self, id, data):
        self.redis.set(id, data)

    def clear(self):
        self.redis.flushdb()
    
    def saveArray(self,id, a):
        encoded = a.tobytes()
        # Store encoded data in Redis
        self.redis.set(id,encoded)
        return

    def getArray(self,id):
        """Retrieve Numpy array from Redis key 'n'"""
        encoded = self.redis.get(id)
        if encoded is None:
            return None
        a = np.frombuffer(encoded)
        return a

    async def getJsonFromUrl(self,url, session = None, retries = 5):
        for i in range(retries):
            try:
                if session is None:
                    return requests.get(url).text
                
                async with session.get(url) as response:
                    return await response.text()
            except Exception as e:
                self.logger.error(e)
                self.logger.error("retry {i} {url}" .format(i=i, url=url))
                await asyncio.sleep(1)
        return None


    async def getJson(self, url, session = None, retries = 5):
        self.logger.debug("get cache for {}".format(url))
        if self.redis.exists(url):
            self.logger.debug("cache hit")
            cached = self.redis.get(url)
            return json.loads(cached)
        else:
            self.logger.debug("cache miss")
            data = await self.getJsonFromUrl(url, session, retries)
            if data is not None:
                self.logger.debug("cache set")
                self.redis.set(url, data)
                return json.loads(data)
            else:
                return None