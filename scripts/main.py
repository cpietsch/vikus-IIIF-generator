from enum import IntEnum
from typing import List, Union
import asyncio
from imp import reload
import json
import uuid
from warnings import catch_warnings

from torch import absolute
from traitlets import Integer
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.params import Depends

import os
import math
import logging
import os
from functools import wraps
import shutil
import uuid
from helpers import calculateThumbnailSize

from vikus import create_config_json, crawlCollection, crawlImages, makeMetadata, makeSpritesheets, saveConfig, makeZip, makeFeatures, makeUmap, cache
from connectionManager import ConnectionManager

LOGGER = logging.getLogger(__name__)

DATA_DIR = "../data"

app = FastAPI(
    title="Vikus Docker",
    description="Vikus Docker",
    version="0.1.0",
    docs_url="/docs",
)
manager = ConnectionManager()

origins = [
    # "http://localhost",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

InstanceManager = {}

DEFAULTS = {
    "collection": {
        "worker": 4,
        "depth": 0,
        "skip_cache": False,
    },
    "images": {
        "worker": 4,
        "depth": 0,
        "skip_cache": False,
    },
    "features": {
        "batch_size": 16,
        "skip_cache": False,
    },
    "metadata": {
        "skip_cache": False,
    },
    "spritesheets": {},
    "umap": {
        "n_neighbors": 15,
        "min_distance": 0.3,
        "raster_fairy": False
    }
}


@app.get("/")
def home():
    return {"IIIF": "meet VIKUS Viewer"}


@app.get("/instances")
def list_instances():
    instances = []
    paths = sorted(filter(os.path.isdir, Path(DATA_DIR).iterdir()),
                   key=os.path.getmtime, reverse=True)
    for dir in paths:
        if dir.name in ['images', 'viewer']:
            continue
        instance = {
            "id": dir.name,
            "absolutePath": dir.resolve(),
            "label": dir.name,
            "modified": os.path.getmtime(dir),
        }
        instances.append(instance)
    return instances


@app.post("/instances")
async def create_instance(url: str, label: str = None):
    """
    Create a new instance using the given url.
    """
    config = create_config_json(url, label)
    return config


@app.get("/instances/{instance_id}")
def read_instance(instance_id: str):
    """
    Read the config.json of the given instance.
    """
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    configFile = os.path.join(path, "instance.json")
    if not os.path.isfile(configFile):
        return {"error": "Instance {} doesn't have a config file".format(instance_id)}, 404
    with open(configFile, "r") as f:
        config = json.load(f)
    return config


@app.post("/instances/steps/collection")
async def crawl_collection(
    instance_id: str = Query(title="Instance ID", description="Instance ID"),
    worker: int = Query(DEFAULTS["collection"]["worker"],
                        title="Workers", description="Number of workers"),
    depth: int = Query(DEFAULTS["collection"]["depth"], title="Depth",
                       description="Recursive crawl depth", min=0, max=100),
    skip_cache: bool = Query(
        DEFAULTS["collection"]["skip_cache"], title="Skip cache", description="Skip cache"),
):
    """
    Crawl a IIIF collection using parallel workers and a maximal depth.
    """
    config = read_instance(instance_id)
    if "error" in config:
        return config

    manifests = await crawlCollection(
        config["iiif_url"],
        instance_id,
        worker,
        depth,
        skip_cache
    )

    config["collection"] = True
    saveConfig(config)

    if instance_id not in InstanceManager:
        InstanceManager[instance_id] = {"config": config}

    InstanceManager[instance_id].update({
        "manifests": manifests
    })

    return config


@app.post("/instances/steps/images")
async def crawl_images(
    instance_id: str = Query(title="Instance ID", description="Instance ID"),
    worker: int = Query(DEFAULTS["images"]["worker"],
                        title="Workers", description="Number of workers"),
    skip_cache: bool = Query(
        DEFAULTS["images"]["skip_cache"], title="Skip cache", description="Skip cache")
):
    """
    Download all thubmnail images from a IIIF collection.
    """
    if instance_id not in InstanceManager or "manifests" not in InstanceManager[instance_id]:
        await crawl_collection(instance_id, worker=DEFAULTS["collection"]["worker"], depth=DEFAULTS["collection"]["depth"], skip_cache=DEFAULTS["collection"]["skip_cache"])

    config = InstanceManager[instance_id]["config"]

    manifests = InstanceManager[instance_id]["manifests"]
    images = await crawlImages(manifests, instance_id, worker, skip_cache)

    config["images"] = True
    config["numImages"] = len(images)
    saveConfig(config)

    InstanceManager[instance_id].update({
        "images": images
    })

    return config


@app.post("/instances/steps/metadata")
async def make_metadata(
    instance_id: str = Query(title="Instance ID", description="Instance ID"),
    skip_cache: bool = Query(
        default=DEFAULTS["metadata"]["skip_cache"],
        title="Skip cache",
        description="Skip read cache and save value to cache"
    )
):
    """
    Create a metadata file for all images in a IIIF collection.
    Use Spacy to extract keywords.
    """
    # print(extract_keywords)
    if instance_id not in InstanceManager or "manifests" not in InstanceManager[instance_id]:
        await crawl_collection(instance_id, worker=DEFAULTS["collection"]["worker"], depth=DEFAULTS["collection"]["depth"], skip_cache=DEFAULTS["collection"]["skip_cache"])

    config = InstanceManager[instance_id]["config"]
    manifests = InstanceManager[instance_id]["manifests"]

    metadata = await makeMetadata(manifests, instance_id, config["path"], skip_cache=skip_cache)

    config["metadata"] = True
    config["metadataFile"] = metadata["file"]
    config["metadataStructure"] = metadata["structure"]

    saveConfig(config)

    return config


@app.post("/instances/steps/spritesheets")
async def make_spritesheets(
    instance_id: str = Query(title="Instance ID", description="Instance ID")
):
    """
    Create a spritesheet for all images in a IIIF collection given the downloaded thumbnails.
    """
    if instance_id not in InstanceManager or "images" not in InstanceManager[instance_id]:
        await crawl_images(instance_id, worker=DEFAULTS["images"]["worker"], skip_cache=DEFAULTS["images"]["skip_cache"])

    config = InstanceManager[instance_id]["config"]
    images = InstanceManager[instance_id]["images"]
    spriteSize = calculateThumbnailSize(len(images))
    # files = [os.path.abspath(path) for (id, path) in images]

    await makeSpritesheets(images, instance_id, config["path"], config["spritesheetPath"], spriteSize)

    config["spritesheets"] = True
    saveConfig(config)

    return config


@app.post("/instances/steps/features")
async def make_features(
    instance_id: str = Query(
        title="Instance ID",
        description="Instance ID"
    ),
    batch_size: int = Query(
        default=DEFAULTS["features"]["batch_size"],
        title="Batch Size",
        description="Batch size for the feature extraction"
    ),
    skip_cache: bool = Query(
        default=DEFAULTS["features"]["skip_cache"],
        title="Skip cache",
        description="Skip read cache and save value to cache"
    )
):
    """
    Create a CLIP features fo all images in a IIIF collection given the downloaded thumbnails.
    """
    if instance_id not in InstanceManager or "images" not in InstanceManager[instance_id]:
        await crawl_images(instance_id, worker=DEFAULTS["images"]["worker"], skip_cache=DEFAULTS["images"]["skip_cache"])

    config = InstanceManager[instance_id]["config"]
    images = InstanceManager[instance_id]["images"]

    features = await makeFeatures(images, instance_id, batch_size, skip_cache)

    InstanceManager[instance_id].update({
        "features": features
    })
    config["features"] = True
    saveConfig(config)

    return config


@app.post("/instances/steps/similarity")
async def make_umap(
    instance_id: str = Query(title="Instance ID", description="Instance ID"),
    n_neighbors: int = Query(
        DEFAULTS["umap"]["n_neighbors"], title="Neighbors", description="Number of neighbors"),
    min_distance: float = Query(
        DEFAULTS["umap"]["min_distance"], title="Min Distance", description="Minimum distance"),
    raster_fairy: bool = Query(
        DEFAULTS["umap"]["raster_fairy"], title="Raster Fairy", description="Use raster fairy"),
):
    """
    Create a UMAP embedding based on the CLIP features.
    """
    if instance_id not in InstanceManager or "features" not in InstanceManager[instance_id]:
        await make_features(instance_id, batch_size=DEFAULTS["features"]["batch_size"], skip_cache=DEFAULTS["features"]["skip_cache"])

    config = InstanceManager[instance_id]["config"]
    (ids, features) = InstanceManager[instance_id]["features"]

    await makeUmap(features, instance_id, config["path"], ids, n_neighbors, min_distance, raster_fairy)

    config["similarity"] = True
    saveConfig(config)

    return config


@app.post("/instances/steps/zip")
async def make_zip(instance_id: str):
    """
    Create a zip file for the data folder of VIKUS Viewer
    """
    config = read_instance(instance_id)

    # todo: if zip file already exists, do not create a new one
    if instance_id not in InstanceManager:
        await run(instance_id)

    config = InstanceManager[instance_id]["config"]

    zipFile = await makeZip(config["path"], instance_id)

    config["zip"] = True
    config["zipFile"] = zipFile
    saveConfig(config)

    return config


@app.post("/instances/generate")
async def run(instance_id: str = Query(title="Instance ID", description="Instance ID")):
    """
    Run all steps of the pipeline for a given instance.
    """
    await crawl_collection(instance_id, worker=DEFAULTS["collection"]["worker"], depth=DEFAULTS["collection"]["depth"], skip_cache=DEFAULTS["collection"]["skip_cache"])
    await crawl_images(instance_id, worker=DEFAULTS["images"]["worker"], skip_cache=DEFAULTS["images"]["skip_cache"])
    await make_spritesheets(instance_id)
    await make_features(instance_id, batch_size=DEFAULTS["features"]["batch_size"], skip_cache=DEFAULTS["features"]["skip_cache"])
    await make_umap(instance_id, n_neighbors=DEFAULTS["umap"]["n_neighbors"], min_distance=DEFAULTS["umap"]["min_distance"], raster_fairy=DEFAULTS["umap"]["raster_fairy"])
    await make_metadata(instance_id, skip_cache=DEFAULTS["metadata"]["skip_cache"])
    await make_zip(instance_id)

    config = InstanceManager[instance_id]["config"]

    return config


@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str = Query(title="Instance ID", description="Instance ID")):
    """
    Delete an instance.
    """
    if instance_id in InstanceManager:
        del InstanceManager[instance_id]
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    else:
        shutil.rmtree(path)
    return {"id": instance_id, "absolutePath": path, "label": instance_id, "status": "deleted"}


@app.get("/defaults")
def get_defaults():
    """
    Get the default values for the pipeline.
    """
    return DEFAULTS


@app.post("/defaults")
def set_defaults(defaults: dict):
    """
    Set the default values for the pipeline.
    """
    global DEFAULTS
    # check if all keys are in defaults
    for key in defaults:
        if key not in DEFAULTS:
            return {"error": "Key {} is not in defaults".format(key)}, 400
        if type(defaults[key]) != type(DEFAULTS[key]):
            return {"error": "Type of key {} is not the same as in defaults".format(key)}, 400
        for subkey in defaults[key]:
            if subkey not in DEFAULTS[key]:
                return {"error": "Subkey {} is not in defaults".format(subkey)}, 400
            if type(defaults[key][subkey]) != type(DEFAULTS[key][subkey]):
                return {"error": "Type of subkey {} is not the same as in defaults".format(subkey)}, 400
    DEFAULTS = defaults

    return DEFAULTS


@app.websocket("/instances/{instance_id}/ws")
async def websocket_endpoint(websocket: WebSocket, instance_id: str):
    # https://github.com/tiangolo/fastapi/issues/3008
    # https://github.com/tiangolo/fastapi/issues/2496
    await manager.connect(websocket)

    last_id = 0
    print("Connected", instance_id)
    await cache.redis.delete(instance_id)

    try:
        while True:
            resp = await cache.redis.xread({instance_id: last_id}, count=100)

            if resp:
                key, messages = resp[0]
                for (id, message) in messages:
                    last_id = id
                    data = {key.decode(): val.decode()
                            for key, val in message.items()}
                    await manager.broadcast(data)
            else:
                await asyncio.sleep(0.1)
                await manager.broadcast({"type": "ping", "data": 1, "instance": instance_id})
    except Exception as e:
        manager.disconnect(websocket)
        print("Disconnected", instance_id)


if __name__ == "__main__":
    uvicorn.run("main:app",
                host="0.0.0.0",
                port=5000,
                reload=True,
                # log_level="debug"
                )
    # asyncio.run(app())
