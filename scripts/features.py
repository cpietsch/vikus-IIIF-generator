from PIL import Image
import torch

from transformers import CLIPProcessor, CLIPModel

testImagePath = '../data/Myths_and_legends/images/thumbs/88440f2d48876bd4d2e93fb3b391a082.jpg'

class FeatureExtractor:
    def __init__(self, model_name, device):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.processor = None
        
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
        print("Extracting features from {}".format(image_path))
        image = self.prepareImage(image_path)
        inputs = self.processor(images=image, return_tensors="pt", padding=True)
        outputs = self.model.get_image_features(**inputs)
        detached = outputs.detach().numpy()
        return detached[0]
    
    @torch.no_grad()
    def batch_extract_features(self, image_paths):
        print("Extracting features of {}".format(image_paths))
        images = [self.prepareImage(image_path) for image_path in image_paths]
        inputs = self.processor(images=images, return_tensors="pt", padding=True)
        outputs = self.model.get_image_features(**inputs)
        detached = outputs.detach().numpy()
        return detached


if __name__ == "__main__":
    extractor = FeatureExtractor("openai/clip-vit-base-patch32", "cpu")
    extractor.load_model()
    features = extractor.extract_features(testImagePath)
    print(features)