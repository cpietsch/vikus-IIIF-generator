import asyncio
import logging
import spacy
import spacy_ke
import pandas as pd


class MetadataExtractor:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        self.nlp = spacy.load("en_core_web_lg")
        self.nlp.add_pipe("yake")

    def extract(self, manifests):
        self.logger.debug("extracting")
        metadataList = []
        for manifest in manifests:
            metadata = manifest.getMetadata()
            metadata['keywords'] = self.getKeywords(metadata['label'])
            metadataList.append(metadata)
        return metadataList

    def getKeywords(self, text, n=4):
        doc = self.nlp(text)
        keywords = [keyword.text for keyword, score in doc._.extract_keywords(n)]
        keywordsString = ",".join(keywords)
        return keywordsString

    def saveToCsv(self, metadataList, file):
        self.logger.debug("saving to csv")
        dataframe = pd.DataFrame(metadataList)
        dataframe.to_csv(file, index=False)


async def main():
    from vikus import url, crawlCollection

    manifests = await crawlCollection(url, "test")
    metadataExtractor = MetadataExtractor()
    metadata = metadataExtractor.extract(manifests)
    print(metadata)

    #metadataExtractor.saveToCsv(metadata, "metadata.csv")


if __name__ == "__main__":
    asyncio.run(main())
