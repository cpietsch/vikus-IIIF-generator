import asyncio
from ctypes import resize
import struct
from PIL import Image
import torch
import logging
import numpy as np
from transformers import CLIPProcessor, CLIPModel, CLIPFeatureExtractor
#from transformers import AutoFeatureExtractor
from rich.progress import track
import os

class FeatureExtractor:
    def __init__(self, **kwargs):
        self.model = None
        self.processor = None
        self.logger = kwargs.get(
            'logger', logging.getLogger('FeatureExtractor'))
        self.cache = kwargs.get('cache', None)
        self.progress = kwargs.get('progress', None)
        self.overwrite = kwargs.get('overwrite', False)
        self.instanceId = kwargs.get('instanceId', None)

    @torch.no_grad()
    def load_model(self, device="cpu", local=True):
        self.model_name = local and "models/clip/" or "openai/clip-vit-base-patch32"
        self.device = device
        if(self.model is None):
            self.model = CLIPModel.from_pretrained(
                self.model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)

    def save_model(self, model_path="models/clip/"):
        if not os.path.exists(model_path):
            os.makedirs(model_path)
        self.model.save_pretrained(model_path)
        self.processor.save_pretrained(model_path)

    def prepareImage(self, image_path, resize=False):
        image = Image.open(image_path)
        image = image.convert('RGB')
        if(resize):
            image = image.resize((224, 224))
        return image

    @torch.no_grad()
    def extract_features(self, image_path):
        self.logger.debug("Extracting features from {}".format(image_path))
        image = self.prepareImage(image_path)
        # print(image)
        # print(image.size)
        inputs = self.processor(
            images=image, return_tensors="pt", padding=True, resize=True)
        outputs = self.model.get_image_features(**inputs)
        detached = outputs.detach().numpy()
        return detached[0]

    @torch.no_grad()
    async def get_features(self, id, image_path):
        if(self.cache and not self.overwrite):
            features = await self.cache.getFeatures(id)
            if(features is not None):
                self.logger.debug("Found features in cache for {}".format(id))
                return features
        features = self.extract_features(image_path)
        if(self.cache):
            self.logger.debug("Caching features for {}".format(id))
            await self.cache.saveFeatures(id, features)
        return features

    @torch.no_grad()
    async def batch_extract_features_cached(self, imageList, batchSize=64):
        featuresList = []
        idList = []
        queueList = []
        for (id, path) in imageList:
            features = await self.cache.getFeatures(id)
            if(features is not None):
                self.logger.debug("Found features in cache for {}".format(id))
                featuresList.append(features)
                idList.append(id)
            else:
                queueList.append((id, path))
        print("{}/{} images found in cache".format(len(featuresList), len(imageList)))
        if(len(queueList) > 0):
            self.logger.debug(
                "Extracting features for {}".format(len(queueList)))
            (ids, features) = await self.batch_extract_features(queueList, batchSize)
            featuresList.extend(features)
            idList.extend(ids)
            for (id, feature) in zip(ids, features):
                self.logger.debug("Caching features for {}".format(id))
                await self.cache.saveFeatures(id, feature)
        return (idList, featuresList)

    @torch.no_grad()
    async def batch_extract_features(self, imageList, batchSize=64):
        self.logger.debug("Extracting features of {}".format(len(imageList)))
        features = []
        ids = []

        batchedImageList = [imageList[i:i + batchSize]
                            for i in range(0, len(imageList), batchSize)]
        for batch in track(batchedImageList, total=len(batchedImageList), description="Extracting features in batches"):
            images = [self.prepareImage(image_path)
                      for (id, image_path) in batch]
            inputs = self.processor(
                images=images, return_tensors="pt", padding=True)
            outputs = self.model.get_image_features(**inputs)
            detached = outputs.detach().numpy()
            features.extend(detached)
            ids.extend([id for (id, image_path) in batch])

        return (ids, features)

    @torch.no_grad()
    async def concurrent_extract_features(self, imageList):
        self.logger.info("Extracting features of {}".format(len(imageList)))
        features = []
        ids = []
        for (id, path) in track(imageList, description="Extracting features", total=len(imageList)):
            feature = await self.get_features(id, path)
            print(id, feature.shape)
            features.append(feature)
            ids.append(id)
        self.logger.info("Extracted features of {}".format(len(imageList)))
        return (ids, features)
        # return np.array(featureList)


async def main():
    extractor = FeatureExtractor(overwrite=True)
    extractor.load_model()
    testImagePath = 'files/test.png'
    features = extractor.extract_features(testImagePath)
    print(features.shape)
    features2 = await extractor.get_features('test', testImagePath)
    print(features2.shape)
    print(features == features2)

if __name__ == "__main__":
    asyncio.run(main())
