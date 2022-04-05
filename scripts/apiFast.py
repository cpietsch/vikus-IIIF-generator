from imp import reload
import uvicorn
from fastapi import FastAPI
import os
import math
import logging
import os
from functools import wraps
import shutil

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
                "absolutePath": os.path.join(DATA_DIR, dir),
                "label": dir,
            }
    return instances

@app.get("/instance/{instance_id}")
def read_instance(instance_id: str):
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    return {"id": instance_id, "absolutePath": path, "label": instance_id}

if __name__ == "__main__":
    uvicorn.run("apiFast:app", host="0.0.0.0", port=5000, reload=True)
