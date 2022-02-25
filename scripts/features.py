import struct
from PIL import Image
import torch
import logging
import numpy as np
from transformers import CLIPProcessor, CLIPModel
from rich.progress import track


class FeatureExtractor:
    def __init__(self, model_name, device, **kwargs):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.processor = None
        self.logger = kwargs.get('logger', logging.getLogger('FeatureExtractor'))
        self.cache = kwargs.get('cache', None)
        self.progress = kwargs.get('progress', None)
        
    @torch.no_grad()
    def load_model(self):
        self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(self.model_name)

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
        inputs = self.processor(images=image, return_tensors="pt", padding=True)
        outputs = self.model.get_image_features(**inputs)
        detached = outputs.detach().numpy()
        return detached[0]

    @torch.no_grad()
    def get_features(self, id, image_path):
        if(self.cache):
            features = self.cache.getArray(id)
            if(features is not None):
                self.logger.debug("Found features in cache for {}".format(id))
                return features
        features = self.extract_features(image_path)
        if(self.cache):
            self.logger.debug("Caching features for {}".format(id))
            self.cache.saveArray(id, features)
        return features
    
    @torch.no_grad()
    def batch_extract_features(self, imageList):
        self.logger.debug("Extracting features of {}".format(len(imageList)))
        images = [self.prepareImage(image_path) for (id,image_path) in imageList]
        inputs = self.processor(images=images, return_tensors="pt", padding=True)
        outputs = self.model.get_image_features(**inputs)
        detached = outputs.detach().numpy()
        return detached
    
    @torch.no_grad()
    def concurrent_extract_features(self, imageList):
        self.logger.info("Extracting features of {}".format(len(imageList)))
        features = [] 
        for (id,path) in track(imageList, description="Extracting features", total=len(imageList) ):
            feature = self.get_features(id, path)
            features.append(feature)
        self.logger.info("Extracted features of {}".format(len(imageList)))
        #return features
        return np.array(features)


if __name__ == "__main__":
    extractor = FeatureExtractor("openai/clip-vit-base-patch32", "cpu")
    extractor.load_model()
    testImagePath = '../data/Myths_and_legends/images/thumbs/88440f2d48876bd4d2e93fb3b391a082.jpg'
    features = extractor.extract_features(testImagePath)
    print(features.shape)
    features2 = extractor.get_features('test',testImagePath)
    print(features2.shape)
    print(features == features2)