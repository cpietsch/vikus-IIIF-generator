from enum import IntEnum
from typing import List, Union
import asyncio
from imp import reload
import json
import uuid
from warnings import catch_warnings
from zipfile import ZipFile
import zipfile
from torch import absolute
from traitlets import Integer
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pathlib import Path
from aioredis import Redis
from fastapi.params import Depends



import os
import math
import logging
import os
from functools import wraps
import shutil
import uuid

# from cache import Cache
from vikus import create_config_json, crawlCollection, create_data_json, crawlImages, makeMetadata, makeSpritesheets, saveConfig, create_info_md, makeFeatures, makeUmap, cache
from connectionManager import ConnectionManager

LOGGER = logging.getLogger(__name__)

DATA_DIR = "../data"

# cache = Cache()

app = FastAPI(
    # title="Vikus Docker",
    # description="https://github.com/cpietsch/vikus-docker",
    # version="0.0.1",
    # license_info="MIT",
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
        "depth": 0
    },
    "images": {
        "worker": 4,
        "depth": 0
    },
    "features": {
        "batch_size": 64,
    },
    "metadata": {},
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
    config = create_config_json(url, label)

    print(config)
    return config

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


@app.post("/instances/steps/collection")
async def crawl_collection(
        instance_id: str = Query(title="Instance ID", description="Instance ID"),
        worker: int = Query(DEFAULTS["collection"]["worker"] ,title="Workers", description="Number of workers"),
        depth: int  = Query(DEFAULTS["collection"]["depth"],title="Depth", description="Recursive crawl depth", min=0, max=100),
    ):
    """
    Crawl a IIIF collection using parallel workers and a maximal depth.
    """ 
    config = read_instance(instance_id)
    if config is None:
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404


    manifests = await crawlCollection(
        config["iiif_url"],
        instance_id,
        worker,
        depth
    )

    config["status"] = "crawledCollection"
    config["manifests"] = len(manifests)
    saveConfig(config)

    if instance_id not in InstanceManager:
        InstanceManager[instance_id] = {"config": config}

    InstanceManager[instance_id].update({
        "status": "crawledCollection",
        "manifests": manifests
    })

    return config


@app.post("/instances/steps/images") 
async def crawl_images(
        instance_id: str = Query(title="Instance ID", description="Instance ID"),
        worker: int = Query(DEFAULTS["collection"]["worker"],title="Workers", description="Number of workers")
    ):
    """
    Download all thubmnail images from a IIIF collection.
    """
    if instance_id not in InstanceManager or "manifests" not in InstanceManager[instance_id]:
        await crawl_collection(instance_id)

    config = InstanceManager[instance_id]["config"]

    manifests = InstanceManager[instance_id]["manifests"]
    images = await crawlImages(manifests, instance_id, worker)

    config["status"] = "crawledImages"
    config["images"] = len(images)
    saveConfig(config)

    InstanceManager[instance_id].update({
        "status": "crawledImages",
        "images": images
    })

    return config


@app.post("/instances/steps/metadata")
async def make_metadata(
        instance_id: str = Query(title="Instance ID", description="Instance ID"),
        # extract_keywords: bool = Query(default=True,title="Extract keywords", description="Extract keywords"),
    ):
    """
    Create a metadata file for all images in a IIIF collection.
    Use Spacy to extract keywords.
    """
    # print(extract_keywords)
    if instance_id not in InstanceManager or "manifests" not in InstanceManager[instance_id]:
        await crawl_collection(instance_id)

    config = InstanceManager[instance_id]["config"]
    manifests = InstanceManager[instance_id]["manifests"]
    path = config["path"]
    metadata = await makeMetadata(manifests, instance_id, path)
    saveConfig(config, metadata["metadata"])

    config["status"] = "metadata"
    config["metadataFile"] = metadata["file"]

    return config


@app.post("/instances/steps/spritesheets")
async def make_spritesheets(
        instance_id: str = Query(title="Instance ID", description="Instance ID")
    ):
    """
    Create a spritesheet for all images in a IIIF collection given the downloaded thumbnails.
    """
    if instance_id not in InstanceManager or "images" not in InstanceManager[instance_id]:
        await crawl_images(instance_id)

    config = InstanceManager[instance_id]["config"]
    images = InstanceManager[instance_id]["images"]
    files = [os.path.abspath(path) for (id, path) in images]
    spritesheetPath = config["spritesheetPath"]
    projectPath = config["path"]
    await makeSpritesheets(files, instance_id, projectPath, spritesheetPath)

    config["status"] = "spritesheets"

    return config


@app.post("/instances/steps/features")
async def make_features(
        instance_id: str = Query(title="Instance ID", description="Instance ID"),
        batch_size: int = Query(DEFAULTS["features"]["batch_size"],title="Batch Size", description="Batch size for the feature extraction"),
    ):
    """
    Create a CLIP features fo all images in a IIIF collection given the downloaded thumbnails.
    """
    if instance_id not in InstanceManager or "images" not in InstanceManager[instance_id]:
        await crawl_images(instance_id)

    config = InstanceManager[instance_id]["config"]
    images = InstanceManager[instance_id]["images"]

    features = await makeFeatures(images, instance_id, batch_size)

    InstanceManager[instance_id].update({
        "status": "features",
        "features": features
    })
    config["status"] = "features"

    return config


@app.post("/instances/steps/similarity")
async def make_umap(
        instance_id: str = Query(title="Instance ID", description="Instance ID"),
        n_neighbors: int = Query(DEFAULTS["umap"]["n_neighbors"],title="Neighbors", description="Number of neighbors"),
        min_distance: float = Query(DEFAULTS["umap"]["min_distance"],title="Min Distance", description="Minimum distance"),
        raster_fairy: bool = Query(DEFAULTS["umap"]["raster_fairy"],title="Raster Fairy", description="Use raster fairy"),
    ):
    """
    Create a UMAP embedding based on the CLIP features.
    """
    if instance_id not in InstanceManager or "features" not in InstanceManager[instance_id]:
        await make_features(instance_id)

    config = InstanceManager[instance_id]["config"]
    images = InstanceManager[instance_id]["images"]
    (ids, features) = InstanceManager[instance_id]["features"]

    path = config["path"]

    await makeUmap(features, instance_id, path, ids, n_neighbors, min_distance, raster_fairy)

    config["status"] = "umap"

    return config

@app.post("/instances/steps/zip")
async def make_zip(instance_id: str):
    """
    Create a zip file for the data folder of VIKUS Viewer
    """
    if instance_id not in InstanceManager:
        await run(instance_id)

    config = InstanceManager[instance_id]["config"]
    path = config["path"]
    zipPath = os.path.join(path, "project.zip")
    with ZipFile(zipPath, 'w', zipfile.ZIP_DEFLATED) as zip:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename == "project.zip":
                    continue
                if "thumbs" in dirpath:
                    continue
                zip.write(os.path.join(dirpath, filename),
                          os.path.relpath(os.path.join(dirpath, filename),
                                          os.path.join(path, '..')))

    config["status"] = "zip"
    config["zipFile"] = instance_id + "/project.zip"

    return config


@app.post("/instances/generate")
async def run(instance_id: str = Query(title="Instance ID", description="Instance ID")):
    # run all steps
    print("Running instance {}".format(instance_id))
    await crawl_collection(instance_id, worker=DEFAULTS["collection"]["worker"], depth=DEFAULTS["collection"]["depth"])
    await crawl_images(instance_id, worker=DEFAULTS["images"]["worker"])
    await make_metadata(instance_id)
    await make_spritesheets(instance_id)
    await make_features(instance_id, batch_size=DEFAULTS["features"]["batch_size"])
    await make_umap(instance_id, n_neighbors=DEFAULTS["umap"]["n_neighbors"], min_distance=DEFAULTS["umap"]["min_distance"], raster_fairy=DEFAULTS["umap"]["raster_fairy"])
    await make_zip(instance_id)
    
    config = InstanceManager[instance_id]["config"]
    config["status"] = "umap"

    return config



@app.delete("/instances/{instance_id}")
def delete_instance(instance_id: str = Query(title="Instance ID", description="Instance ID")):
    path = os.path.join(DATA_DIR, instance_id)
    if not os.path.isdir(path):
        return {"error": "Instance {} doesn't exist".format(instance_id)}, 404
    shutil.rmtree(path)
    return {"id": instance_id, "absolutePath": path, "label": instance_id, "status": "deleted"}

# @app.post("/instances/defaults")
# async def defaults():


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
                    data = { key.decode(): val.decode() for key, val in message.items() }
                    await manager.broadcast(data)
            else:
                await asyncio.sleep(0.1)
                await manager.broadcast({"type": "ping", "data": 1})
    except Exception as e:
        manager.disconnect(websocket)
        print("Disconnected", instance_id)


# @app.get("/instances/{instance_id}/eventStream")
# async def stream(req: Request, instance_id: str = "default"):
#     return EventSourceResponse(subscribe(req, instance_id))


# async def subscribe(req: Request, instance_id: str = "default"):
#     try:
#         async with cache.psub as p:
#             print("start subscribe")
#             try:
#                 await p.subscribe(instance_id)
#             except Exception as e:
#                 print("subscribe error", e)

#             print("subscribed")
#             yield {"event": "open", "data": "subscribed to {}".format(instance_id)}
#             while True:
#                 disconnected = await req.is_disconnected()
#                 if disconnected:
#                     print(f"Disconnecting client {req.client}")
#                     break
#                 message = await p.get_message(ignore_subscribe_messages=True)
#                 # print("message")
#                 if message is not None:
#                     # print(message)
#                     yield {"event": "message", "data": message["data"].decode("utf-8")}
#                 await asyncio.sleep(0.01)
#     # except asyncio.CancelledError as e:
#     except Exception as e:
#         print(f"Error {e}")

#     finally:
#         print(f"Closing client {req.client}")

#     await p.unsubscribe(instance_id)
#     yield {"event": "close", "data": "unsubscribed from {}".format(instance_id)}


if __name__ == "__main__":
    uvicorn.run("main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        # log_level="debug"
    )
    # asyncio.run(app())
