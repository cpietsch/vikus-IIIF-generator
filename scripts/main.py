import os
from PIL import Image
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizer
import redis
import time
import logging

# logging.basicConfig(filename='file.log',level=logging.INFO)

app = Flask(__name__)
CORS(app)

# model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
# processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
client = redis.Redis(host='redis', port=6379)


def get_hit_count():
    retries = 5
    while True:
        try:
            return client.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)



@app.route("/")
def hello_world():
    name = os.environ.get("NAME", "World")
    count = get_hit_count()
    print("hello world")
    return 'Hello Worlds! I have been seen {} times.\n'.format(count)



@app.route("/cache") 
def cache():
    url = request.args.get('url')
    app.logger.info("get cache for {}".format(url))
    if url is None or url == "":
        return jsonify({"error": "url is required"})
    if client.exists(url):
        app.logger.info("cache hit")
        return client.get(url)
    else:
        # try to get a json from url
        try:
            response = requests.get(url)
            if response.status_code == 200:
                # if success, save it to redis
                app.logger.info("cache miss")
                client.set(url, response.text)
                return response.text
            else:
                return jsonify({"error": "url is not valid"})
        except Exception as e:
            return jsonify({"error": "url is not valid"})
        

# #@torch.no_grad()
# @app.route('/text')
# def text():
#     text = request.args.get('text')
#     print(text)
#     if text is None:
#         return jsonify(code=403, message="bad request")
#     inputs = processor(text=text, padding=True, return_tensors="pt")
#     outputs = model.get_text_features(**inputs)
#     #print(outputs)
#     detached = outputs.detach().numpy().tolist()
#     #print(detached)
#     return jsonify(detached)

# @app.route('/image')
# def images():
#     url = request.args.get('url')
#     print(url)
#     if url is None:
#         return jsonify(code=403, message="bad request")
#     image = Image.open(requests.get(url, stream=True).raw)
#     inputs = processor(images=image, return_tensors="pt")
#     outputs = model.get_image_features(**inputs)
#     print(outputs)
#     detached = outputs.detach().numpy().tolist()
#     print(detached)
#     return jsonify(detached)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
