import asyncio
import logging
import spacy
import spacy_ke
import pandas as pd
from rich.progress import track


class MetadataExtractor:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get(
            'logger', logging.getLogger('MetadataExtractor'))
        self.nlp = None

    def load(self):
        if self.nlp is None:
            # spacy.load("en_core_web_md")
            self.nlp = spacy.load("en_core_web_sm")
            self.nlp.add_pipe("yake")

    def extract(self, manifests, extract_keywords=True, runOnAllFields=True):
        self.load()
        self.logger.debug("extracting")
        metadataList = []
        for manifest in track(manifests, description="Extracting keywords and metadata"):
            metadata = manifest.getMetadata()
            keywords = "None"
            if extract_keywords:
                if runOnAllFields:
                    dynamicMetadata = [
                        value for key, value in metadata.items() if key.startswith("_")]
                    keywords = self.getKeywords(",".join(dynamicMetadata))
                else:
                    keywords = self.getKeywords(metadata['_label'])
            metadata['keywords'] = keywords
            metadataList.append(metadata)
        return metadataList

    def getKeywords(self, text, n=4):
        doc = self.nlp(text)
        keywords = [keyword.text for keyword,
                    score in doc._.extract_keywords(n)]
        keywordsString = ",".join(keywords)
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
        for metadata in metadataList:
            for key, value in metadata.items():
                if key not in detailStructure:
                    detailStructure[key] = {
                        "name": key,
                        "source": key,
                        "display": "wide",
                        "type": "text"
                    }
        return detailStructure


async def main():
    from vikus import crawlCollection

    url = "https://resource.swissartresearch.net/manifest/zbz-collection"
    manifests = await crawlCollection(url, "test")
    #manifests = manifests[:10]
    metadataExtractor = MetadataExtractor()
    metadata = metadataExtractor.extract(manifests)
    details = metadataExtractor.makeDetailStructure(metadata)
    # print(metadata)

    #metadataExtractor.saveToCsv(metadata, "metadata.csv")


if __name__ == "__main__":
    asyncio.run(main())
