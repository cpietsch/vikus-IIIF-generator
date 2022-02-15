from transformers import ViTFeatureExtractor, ViTModel, ViTForImageClassification
from PIL import Image

testImagePath = '../data/Myths_and_legends/images/thumbs/88440f2d48876bd4d2e93fb3b391a082.jpg'

# modelPath = "google/vit-base-patch16-224-in21k"
modelPath = "openai/clip-vit-base-patch32"

feature_extractor = ViTFeatureExtractor.from_pretrained(modelPath)
model = ViTModel.from_pretrained(modelPath)

def extractFeatureFromImage(imagePath):
    image = Image.open(imagePath)
    encoding = feature_extractor(images=image, return_tensors="pt")
    # print(encoding)
    # print(encoding['pixel_values'].shape)
    pixel_values = encoding['pixel_values']
    outputs = model(pixel_values,output_hidden_states=True)
    # print(outputs)
    last_hidden_states = outputs.last_hidden_state
    print(last_hidden_states.shape)
    return last_hidden_states
    
    

features = extractFeatureFromImage(testImagePath)
print(features)