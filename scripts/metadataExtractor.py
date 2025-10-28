import asyncio
import logging
import os
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import pandas as pd
from rich.progress import track


class MetadataExtractor:
    def __init__(self, **kwargs):
        self.logger = kwargs.get(
            'logger', logging.getLogger('MetadataExtractor'))
        self.kw_model = None
        self.cache = kwargs.get('cache', None)
        self.skipCache = kwargs.get('skipCache', False)

    def load(self, useGpu = False):
        if self.kw_model is None:
            self.logger.info("Loading KeyBERT model...")
            # Use a small, efficient sentence transformer model (~80MB)
            sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.kw_model = KeyBERT(model=sentence_model)
            self.logger.info("KeyBERT model loaded successfully")

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
            
            progress = completed / total
            completed += 1
            if self.cache is not None and completed % 100 == 0:  
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

        # Use KeyBERT to extract keywords
        # keyphrase_ngram_range: (1, 2) means extract single words and 2-word phrases
        # stop_words: 'english' filters common English words
        # top_n: number of keywords to extract
        keywords_with_scores = self.kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            top_n=n,
            use_maxsum=True,  # Diversify keywords
            nr_candidates=20  # Consider top 20 candidates
        )
        
        # Extract just the keyword text (not the scores)
        keywords = [keyword for keyword, score in keywords_with_scores]
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
