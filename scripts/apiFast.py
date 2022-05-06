from imp import reload
import json
import uuid
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

import os
import math
import logging
import os
from functools import wraps
import shutil
import uuid
from playground import run_all, create_config_json, crawl

LOGGER = logging.getLogger(__name__)

DATA_DIR = "../data"

app = FastAPI()

origins = [
    #"http://localhost",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"Hello": "World"}
  

@app.get("/instances")
def list_instances():
    instances = []
    for dir in os.listdir(DATA_DIR):
        if os.path.isdir(os.path.join(DATA_DIR, dir)):
            instance = {
                "id": dir,
                "absolutePath": os.path.abspath(os.path.expanduser(os.path.expandvars(os.path.join(DATA_DIR, dir)))),
                "label": dir,
            }
            instances.append(instance)
    return instances

@app.get("/instances/{instance_id}")
def read_instance(instance_id: str):
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    configFile = os.path.join(path, "instance.json")
    if not os.path.isfile(configFile):
        return {"error": "Instance {} doesn't have a config file".format(instance_id)}, 404
    with open(configFile, "r") as f:
        config = json.load(f)
    return config

@app.get("/instances/{instance_id}/crawl")
async def startcrawl(instance_id: str):
    config = read_instance(instance_id)
    if config["status"] != "created":
        return {"error": "Instance {} is already crawled".format(instance_id)}, 404
    
    config["status"] = "crawling"
    with open(os.path.join(config["path"], "instance.json"), "w") as f:
        f.write(json.dumps(config, indent=4))

    manifests = await crawl(config["iiif_url"])
    config["status"] = "crawled"
    config["images"] = len(manifests)
    with open(os.path.join(config["path"], "instance.json"), "w") as f:
        f.write(json.dumps(config, indent=4))

    return config

@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str):
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    shutil.rmtree(path)
    return {"id": instance_id, "absolutePath": path, "label": instance_id, "status": "deleted"}

@app.post("/instances")
async def create_instance(iiif_url: str, label: str = None):
    
    config = create_config_json(iiif_url, label)

    print(config)
    # try:
    #     instance = await run_all(iiif_url, path, label)
    # except Exception as e:
    #     return {"error": str(e)}, 500

    return config

@app.websocket("/instances/{instance_id}/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_text(await websocket.receive_text())

if __name__ == "__main__":
    uvicorn.run("apiFast:app", host="0.0.0.0", port=5000, reload=True)
  