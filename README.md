# vikus-docker
This is a Docker instance builder for IIIF Collections (Presentation API 3.0), allowing you to crawl all manifests recursively, download images of each canvas, create spritesheets, extract metadata, generate keywords, and more.

This repository contains code to build a VIKUS Viewer Docker instance. This instance can be used to view IIIF Collections (Presentation 3.x API). The code will crawl all manifests in a IIIF Collection (v3) recursively, download an image of each canvas, and save it to disk. It will also create spritesheets and extract metadata from manifests. The code uses redis cache for manifests and feature vectors. The similarity layouts can be generated with UMAP and Rasterfairy. There is also a REST Api and websocket real time progress.
The resulting ZIP archive for VIKUS Viewer can be downloaded.

## Features

- Crawling of all manifests in a [IIIF Collection](https://iiif.io/api/presentation/3.0/) (v3) recursively
- Asynchronous queueing for crawling manifests and images
- Downloads an image of each canvas and save it to disk
- Create spritesheets
- Extract metadata from manifests and generate keywords using [spacy](https://spacy.io/models/xx)
- Extract embeddings with CLIP using [huggingface transformers](https://huggingface.co/docs/transformers/model_doc/clip)
- Redis cache for manifests and feature vectors
- Generate similarity layouts with [UMAP](https://umap-learn.readthedocs.io/en/latest/) and [Rasterfairy](https://github.com/Quasimondo/RasterFairy)
- REST Api
- Websocket real time progress
- Download data ZIP archive for VIKUS Viewer

## RUN

To start up the Docker instance, run:

```
docker compose up
```

If you have a GPU available, you can increase the speed of CLIP features extraction by running:

```
docker compose -f docker-compose.gpu.yml up
```

If you need to rebuild the image, run:

```
docker-compose down
docker-compose up --force-recreate --build -d
```

## Usage

To use the VIKUS Docker instance, open the frontend in a browser at http://localhost:8000/frontend/. Paste an IIIF Collection (v3) URL and click "Create". Click "Generate" to run all the steps.

If you want, you can fiddle with the settings of each step and/or run them individually. Once the process is finished, you can open a VIKUS Viewer preview, or download the data ZIP and extract it into the /data folder of the VIKUS Viewer.

## Tech
- Python3
- Redis
- Huggingface Transformers
- CLIP
- Spacy
- UMAP
- Rasterfairy
- FastAPI
- Svelte
- Docker

## API
Open the VIKUS Docker API in a browser:
http://localhost:3000/docs


## Sub-projects
- https://github.com/cpietsch/vikus-docker-frontend/ (svelte)
- https://github.com/cpietsch/vikus-viewer (docker branch)

## Requirements
- Docker
- Docker Compose

## Notebooks
To start the notebook server on port 5000 instead of the server, connect to the vikusdocker and run
- `pip install jupyter-lab`
- `jupyter-lab --port 5000`

## Funding
The work on this project was made possible through funding of the [Swiss Art Research Infrastructure (SARI)](https://swissartresearch.net/).