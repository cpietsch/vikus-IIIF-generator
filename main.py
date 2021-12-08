import os
from PIL import Image
import requests
from flask import Flask, request, jsonify
from transformers import CLIPProcessor, CLIPModel

app = Flask(__name__)

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

@app.route("/")
def hello_world():
    name = os.environ.get("NAME", "World")
    print("hello world")
    return "Hello {}!".format(name)

@app.route('/features')
def features():
    text = request.args.get('text')
    if text is None:
        return jsonify(code=403, message="bad request")
    inputs = processor(text=text, return_tensors="pt")
    outputs = model(**inputs)
    print(outputs)
    #classify = pipeline("sentiment-analysis", model=model_path, tokenizer=model_path)
    return jsonify([0,12,3])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))