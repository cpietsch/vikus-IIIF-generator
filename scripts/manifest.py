import json
import logging
import asyncio
import random
import time
import hashlib
import aiohttp

from cache import Cache


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
        # self.tree = kwargs.get(
        #     'tree', self.parent and self.parent.tree or None)
        self.type = None
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.shortId = self.id.split('/')[-1]
        self.hashId = self.hashId = hashlib.md5(
            self.id.encode('utf-8')).hexdigest()
        self.version = None
        #self.path = self.parent and self.id.replace(self.parent.id, '') or self.id

    def __str__(self):
        return """
        id: {}
        label: {}
        type: {}
        parent: {}
        version: {}
        """.format(self.id, self.label, self.type, self.parent, self.version)

    def getId(self):
        return self.hashId

    def getVersionFromData(self):
        if self.parent is None:
            if self.data.get("@context") == "http://iiif.io/api/presentation/2/context.json":
                self.version = 2
            else:
                self.version = 3
        else:
            self.version = self.parent.version

    def load(self, data=None):
        if data:
            # self.logger.debug("loading manifest from url {}".format(self.url))
            self.data = data
            self.getVersionFromData()

            if self.version == 2:
                self.id = self.data.get("@id")
                self.label = self.getLabel()
                self.type = self.data.get("@type")

            elif self.version == 3:
                self.id = self.data.get("id") or self.data.get("@id")
                self.label = self.getLabel()
                self.type = self.data.get('type') or self.data.get('@type')

            # if(self.tree is None):
            #     self.tree = Tree(
            #         f":open_file_folder: [link {self.id}]{self.id}")
            # else:
            #     emoji = self.type == 'Collection' and ':open_file_folder:' or ':framed_picture:'
            #     self.tree = self.tree.add(f"{emoji} [link {self.id}]{self.id}")

            return self

    def add(self, child):
        self.children.append(child)

    def getLabel(self):
        label = ""
        if isinstance(self.data.get("label"), dict):
            labels = list(self.data.get("label").values())[0]
            label = labels[0]
        elif isinstance(self.data.get("label"), list):
            label = self.data.get("label")[0]
        else:
            label = self.data.get("label") or self.data.get("@label")
        return label

    def getThumbnailUrl(self, size=128):
        try:
            if self.data.get('thumbnail'):
                if self.data.get('thumbnail')[0].get('id'):
                    return self.data.get('thumbnail')[0].get('id')
                elif self.data.get('thumbnail')[0].get('@id'):
                    return self.data.get('thumbnail')[0].get('@id')
                elif self.data.get('thumbnail')[0].get('id'):
                    return self.data.get('thumbnail')[0].get('id')
            else:
                return self.getLargeImageUrl(size)
        except Exception as e:
            self.logger.warning("no thumbnail found for {}".format(self))
            return None

    # def getImageUrl(self):
    #     try:
    #         if self.version == 2:
    #             return self.data.get('sequences')[0].get('canvases')[0].get('images')[0].get('resource').get('@id')
    #         elif self.version == 3:
    #             return self.data.get('items')[0].get('items')[0].get('body').get('id')
    #     except:
    #         self.logger.warning("no image found for {}".format(self))

    def getLargeImageUrl(self, max=4096):
        try:
            body = self.data.get('items')[0].get('items')[0].get('body')
            service = body.get('service')[0]
            if service.get("@type") == "ImageService2":
                width = service.get("width")
                height = service.get("height")

                if width > max or height > max:
                    if(width > height):
                        ratio = max / width
                    else:
                        ratio = max / height

                    return "{}/full/{},{}/0/default.jpg".format(
                        service.get("@id"),
                        int(width * ratio),
                        int(height * ratio)
                    )
                return "{}/full/full/0/default.jpg".format(
                    service.get("@id"),
                )

            if service.get("type") == "ImageService3":
                width = body.get("width")
                height = body.get("height")

                if width > max or height > max:
                    if(width > height):
                        ratio = max / width
                    else:
                        ratio = max / height

                    return "{}/full/{},{}/0/default.jpg".format(
                        service.get("id"),
                        int(width * ratio),
                        int(height * ratio)
                    )
                return "{}/full/full/0/default.jpg".format(
                    service.get("id"),
                )

        except:
            self.logger.warning("no image found for {}".format(self))

    def getThumbnailUrls(self):
        items = self.data.get('items')
        urls = []
        for item in items:
            try:
                url = item.get('thumbnail')[0].get("id")
                urls.append(url)
            except:
                self.logger.warning("no image url found for {}".format(item))
        return urls

    # def getImageUrls(self):
    #     items = self.data.get('items')
    #     urls = []
    #     for item in items:
    #         try:
    #             url = item.get('items')[0].get('items')[
    #                 0].get('body').get('id')
    #             urls.append(url)
    #         except:
    #             self.logger.warning("no image url found for {}".format(item))
    #     return urls

    def getFlatList(self, manifest=None, list=None):
        if list is None:
            list = []
        if manifest is None:
            manifest = self

        if manifest.version == 2:
            type = "sc:Canvas"
        else:
            type = "Canvas"

        if manifest.type == type:
            list.append(manifest)
        for child in manifest.children:
            self.getFlatList(child, list)
        return list

        # if manifest.type == type:
        #     list.append(manifest)

        # for item in manifest.children:
        #     self.getFlatList(item, type, list)

        # return list

    def getChildren(self):
        return self.children

    def valueToStr(self, value):
        if isinstance(value, list):
            return ",".join(value)
        elif isinstance(value, dict):
            return json.dumps(value)
        else:
            return str(value)

    def getMetadata(self, arr=None):
        """
        Returns a dictionary of metadata for this object.
        If arr is not None, the metadata is added to the dictionary.
        If arr is None, a new dictionary is created.
        """

        if arr is None:
            arr = {}

        if(self.type == 'Canvas'):
            arr['id'] = self.getId()
            arr['thumbnail'] = self.getThumbnailUrl()
            # arr['image'] = self.getImageUrl()
            # hack for welcome collection: use custom size to trick the cache
            arr['image'] = self.getLargeImageUrl(1025)
            arr['largeImage'] = self.getLargeImageUrl()

            if(self.parent is None):
                return arr

            return self.parent.getMetadata(arr)

        metadata = self.data.get('metadata')
        if(metadata is None):
            self.logger.warning("no metadata found for {}".format(self))
            return None

        arr['_label'] = self.valueToStr(self.label)
        arr['_iiif'] = self.id

        try:
            for item in metadata:
                if self.version == 2:
                    label = item.get('label')
                    if isinstance(item.get('value'), list):
                        value = item.get('value')[0]
                    else:
                        value = item.get('value')
                elif self.version == 3:
                    label = next(iter(item.get('label').values()))[0]
                    value = next(iter(item.get('value').values()))[0]

                arr["_" + label] = self.valueToStr(value)
        except:
            self.logger.warning("error in metadata {}".format(self))

        # print(list)
        return arr

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


async def main():
    cache = Cache()

    # url = "https://iiif.dl.itc.u-tokyo.ac.jp/iiif/2/collection/c-1"
    # url = "https://iiif.wellcomecollection.org/presentation/b2488473x"
    # url = "https://iiif.wellcomecollection.org/presentation/b16894376" # behind auth, non public

    #url = "https://iiif.bodleian.ox.ac.uk/iiif/manifest/e32a277e-91e2-4a6d-8ba6-cc4bad230410.json"
    # data = await cache.getJson(url)

    url = "https://iiif.harvardartmuseums.org/manifests/object/344226"
    url = "https://resource.swissartresearch.net/manifest/zbz-990109044120205508"
    url = "https://resource.swissartresearch.net/manifest/zbz-990054267420205508"
    async with aiohttp.ClientSession() as session:
        data = await cache.getJson(url, session, skipCache=True)

    # print(data)

    manifest = Manifest(url=url)
    manifest.load(data)
    print(manifest.getMetadata())
    # print(manifest)
    # for item in manifest.data.get('items', []):
    #     child = Manifest(
    #         url=item.get('id'),
    #         depth=1,
    #         parent=manifest,
    #     )
    #     child.load(item)
    #     # print(child.getThumbnailUrl())
    #     print(child.getMetadata())
    # print(manifest.getMetadata())
    # print(manifest.getThumbnailUrl())
    # print(manifest.getImageUrl())

if __name__ == "__main__":
    asyncio.run(main())
