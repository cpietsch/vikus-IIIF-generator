from imp import reload
import json
import uuid
import uvicorn
from fastapi import FastAPI
import os
import math
import logging
import os
from functools import wraps
import shutil
import uuid
from playground import run_all

LOGGER = logging.getLogger(__name__)

DATA_DIR = "../data"

INSTANCES = {}

app = FastAPI()

@app.get("/")
def home():
    return {"Hello": "World"}

@app.get("/instances")
def list_instances():
    instances = {}
    for dir in os.listdir(DATA_DIR):
        if os.path.isdir(os.path.join(DATA_DIR, dir)):
            instances[dir] = {
                "id": dir,
                "absolutePath": os.path.abspath(os.path.expanduser(os.path.expandvars(os.path.join(DATA_DIR, dir)))),
                "label": dir,
            }
    return instances

@app.get("/instance/{instance_id}")
def read_instance(instance_id: str):
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    return {"id": instance_id, "absolutePath": path, "label": instance_id}

@app.delete("/instance/{instance_id}")
def delete_instance(instance_id: str):
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    shutil.rmtree(path)
    return {"id": instance_id, "absolutePath": path, "label": instance_id, "status": "deleted"}

@app.post("/instance/create")
async def create_instance(iiif_url: str):
    label = str(uuid.uuid4())
    path = os.path.join(DATA_DIR, label)
    os.mkdir(path)
    config = create_config_json(path, label, iiif_url)

    instance = await run_all(iiif_url, path, label)

    return {"id": label, "absolutePath": path, "label": label, "config": config, "instance": instance}


if __name__ == "__main__":
    uvicorn.run("apiFast:app", host="0.0.0.0", port=5000, reload=True)
  


def create_config_json(path: str, id: str, iiif_url: str):
    config = {
        "id": id,
        "label": id,
        "iiif_url": iiif_url,
    }
    with open(os.path.join(path, "info.json"), "w") as f:
        f.write(json.dumps(config, indent=4))
    return config
