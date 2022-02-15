import logging
import asyncio
import random
import time
import hashlib

from rich.tree import Tree

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
        self.tree =  kwargs.get('tree', self.parent and self.parent.tree or None)
        self.type = None
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.shortId = self.id.split('/')[-1]
        self.hashId = self.hashId = hashlib.md5(self.id.encode('utf-8')).hexdigest()
        #self.path = self.parent and self.id.replace(self.parent.id, '') or self.id
        
    def getId(self):
        return self.hashId

    def load(self, data=None):
        if data:
            self.logger.debug("get manifest from url {}".format(self.url))
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