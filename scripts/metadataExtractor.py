import asyncio
import logging
import os
import spacy
import spacy_ke
import pandas as pd
from rich.progress import track


class MetadataExtractor:
    def __init__(self, **kwargs):
        self.logger = kwargs.get(
            'logger', logging.getLogger('MetadataExtractor'))
        self.nlp = None
        self.cache = kwargs.get('cache', None)
        self.skipCache = kwargs.get('skipCache', False)

    def load(self, useGpu = False):
        if self.nlp is None:
            # spacy.load("en_core_web_md")
            if useGpu or ("USEGPU" in os.environ and os.environ['USEGPU'] is True):
                spacy.prefer_gpu()
            self.nlp = spacy.load("en_core_web_sm")
            self.nlp.add_pipe("yake")

    async def extract(self, manifests, extract_keywords=True, runOnAllFields=True, instanceId="default"):
        self.load()
        self.logger.debug("extracting")
        metadataList = []
        completed = 0
        total = len(manifests)

        for manifest in manifests:
            # for manifest in track(manifests, description="Extracting keywords and metadata"):
            metadata = manifest.getMetadata()
            keywords = "None"
            if extract_keywords:
                if runOnAllFields:
                    dynamicMetadata = [
                        value for key, value in metadata.items() if key.startswith("_")]
                    keywords = await self.getKeywords(",".join(dynamicMetadata))
                else:
                    keywords = await self.getKeywords(metadata['_label'])
            metadata['keywords'] = keywords
            metadataList.append(metadata)
            if self.cache is not None:
                progress = completed / total
                completed += 1
                await self.cache.postProgress(instanceId, {
                    'progress': progress,
                    'task': 'metadata',
                    'size': total,
                    'completed': completed
                })
        if self.cache is not None:
            progress = 1
            await self.cache.postProgress(instanceId, {
                'progress': progress,
                'task': 'metadata',
                'size': total,
                'completed': completed
            })
        return metadataList

    async def getKeywords(self, text, n=4):
        if self.cache is not None and not self.skipCache:
            cached = await self.cache.getKeywords(text)
            if cached is not None:
                return cached.decode("utf-8")

        doc = self.nlp(text)
        keywords = [keyword.text for keyword,
                    score in doc._.extract_keywords(n)]
        keywordsString = ",".join(keywords)
        if self.cache is not None:
            await self.cache.setKeywords(text, keywordsString)

        return keywordsString

    def saveToCsv(self, metadataList, file):
        self.logger.debug("saving to csv")
        dataframe = pd.DataFrame(metadataList)
        dataframe.to_csv(file, index=False)

    def makeDetailStructure(self, metadataList):
        self.logger.debug("making detail structure")
        ''' structure: 
             {
                "name": "Description",
                "source": "_description",
                "display": "column",
                "type": "text"
            },
        '''
        detailStructure = {}
        # print(metadataList)
        for metadata in metadataList:
            for key, value in metadata.items():
                # print("metadata is: ", key)
                if key not in detailStructure:
                    detailStructure[key] = {
                        "name": key,
                        "source": key,
                        "display": "wide",
                        "type": "text"
                    }
        # print(detailStructure)

        return detailStructure


async def main():
    from vikus import crawlCollection, cache

    url = "https://resource.swissartresearch.net/manifest/zbz-collection-100"
    manifests = await crawlCollection(url, "test")
    #manifests = manifests[:10]
    metadataExtractor = MetadataExtractor(cache=cache)
    metadata = await metadataExtractor.extract(manifests)
    #details = metadataExtractor.makeDetailStructure(metadata)
    # print(metadata)

    #metadataExtractor.saveToCsv(metadata, "metadata.csv")


if __name__ == "__main__":
    asyncio.run(main())
