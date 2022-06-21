import asyncio
import logging
from cache import Cache
from vikus import url, crawlCollection
import spacy
import spacy_ke
import pandas as pd


class KeywordExtractor:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.nlp = spacy.load("en_core_web_lg")

    def extract(self, manifests):
        self.logger("extracting")
        metadataList = []
        for manifest in manifests:
            metadata = manifest.getMetadata()
            metadata['keywords'] = self.getKeywords(metadata['label'])
            metadataList.append(metadata)
        return metadataList

    def getKeywords(self, text, n=4):
        doc = self.nlp(text)
        return [keyword for keyword, score in doc._.extract_keywords(n)]

    def saveToCsv(self, metadataList, file):
        self.logger("saving to csv")
        dataframe = pd.DataFrame(metadataList)
        dataframe.to_csv(file, index=False)


async def main():
    manifests = await crawlCollection(url, "test")
    metadataExtractor = KeywordExtractor()
    metadata = metadataExtractor.extract(manifests)
    print(metadata)

    #metadataExtractor.saveToCsv(metadata, "metadata.csv")


if __name__ == "__main__":
    asyncio.run(main())
