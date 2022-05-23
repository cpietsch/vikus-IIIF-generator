from typing import List
import asyncio
from imp import reload
import json
import uuid
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pathlib import Path

import os
import math
import logging
import os
from functools import wraps
import shutil
import uuid

import websockets

# from cache import Cache
from playground import create_config_json, crawl, cache

LOGGER = logging.getLogger(__name__)

DATA_DIR = "../data"

# cache = Cache()

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

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: json, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: json):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()

InstanceManager = {}

@app.get("/")
def home():
    return {"Hello": "World"}
  

@app.get("/instances")
def list_instances():
    instances = []
    paths = sorted(filter(os.path.isdir, Path(DATA_DIR).iterdir()), key=os.path.getmtime, reverse=True)
    for dir in paths:
        instance = {
            "id": dir.name,
            "absolutePath": dir.resolve(),
            "label": dir.name,
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
async def crawlManifest(instance_id: str):
    config = read_instance(instance_id)
    # print(config)
    # if config["status"] != "created":
    #     return {"error": "Instance {} is alr7eady crawled".format(instance_id)}, 404
    
    # config["status"] = "crawling"
    # with open(os.path.join(config["path"], "instance.json"), "w") as f:
    #     f.write(json.dumps(config, indent=4))

    manifests = await crawl(config["iiif_url"], instance_id, config)

    InstanceManager[instance_id] = {
        "config": config,
        "manifests": manifests,
        "status": "crawled",
    }

    # config["status"] = "crawled"
    # with open(os.path.join(config["path"], "instance.json"), "w") as f:
    #     f.write(json.dumps(config, indent=4))

    # return InstanceManager[instance_id]

    config["status"] = "crawled"
    config["images"] = len(manifests)
    with open(os.path.join(config["path"], "instance.json"), "w") as f:
        f.write(json.dumps(config, indent=4))

    return config

@app.get("/instances/{instance_id}/crawlImages")
async def crawlImages(instance_id: str):
    config = read_instance(instance_id)

    manifests = InstanceManager[instance_id]["manifests"]

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
async def websocket_endpoint(websocket: WebSocket, instance_id: str):
    # https://github.com/tiangolo/fastapi/issues/3008
    # https://github.com/tiangolo/fastapi/issues/2496
    await manager.connect(websocket)

    last_id = 0
    sleep_ms = 10
    print("Connected", instance_id)

    cache.delete(instance_id)

    try:
        while True:
            # print(f"instance_id: {instance_id}")
            # await asyncio.sleep(0.3)
            await manager.broadcast({ "type": "ping", "data": 1 })
            # resp = cache.xread({instance_id: '$'}, None, sleep_ms)
            resp = cache.xread({instance_id: last_id}, count=100, block=sleep_ms)
            
            if resp:
                key, messages = resp[0]  # :(
                last_id, data = messages[0]

                ddata_dict = {k.decode("utf-8"): data[k].decode("utf-8") for k in data}
                print(ddata_dict)
                # print(resp)
                await manager.broadcast(ddata_dict)
            else:
                print("no data")
                await asyncio.sleep(0.3)
    except Exception as e:
        manager.disconnect(websocket)
        print("Disconnected", instance_id)
        

if __name__ == "__main__":
    uvicorn.run("apiFast:app", host="0.0.0.0", port=5000, reload=True)
  






# async def _alive_task(websocket: WebSocket, instance_id: str, manager: ConnectionManager):
#     try:
#         await websocket.receive_text()
#     except (WebSocketDisconnect, websockets.exceptions.ConnectionClosedError):
#         manager.disconnect(websocket)
#         pass
        
# async def _send_data(websocket: WebSocket, instance_id: str, manager: ConnectionManager):
#     last_id = 0
#     sleep_ms = 100
#     try:
#         while True:
#             await asyncio.sleep(0.3)
#             print("Sending data")
#             resp = cache.xread({instance_id: last_id}, count=1, block=sleep_ms)
#             if resp:
#                 print(resp)
#                 await manager.broadcast({ "type": "update", "data": 1 })
#     except (WebSocketDisconnect, websockets.exceptions.ConnectionClosedError):
#         manager.disconnect(websocket)
#         pass

# @app.websocket("/instances/{instance_id}/ws")
# async def websocket_endpoint(websocket: WebSocket, instance_id: str):
#     await manager.connect(websocket)

#     print("Connected", instance_id)

#     loop = asyncio.get_running_loop()
#     alive_task = loop.create_task(
#         _alive_task(websocket, instance_id, manager),
#         name=f"WS alive check: {websocket.client}",
#     )
#     send_task: asyncio.Task = loop.create_task(
#         _send_data(websocket, instance_id, manager),
#         name=f"WS data sending: {websocket.client}",
#     )
    
#     alive_task.add_done_callback(send_task.cancel)
#     send_task.add_done_callback(alive_task.cancel)
    
#     await asyncio.wait({alive_task, send_task})