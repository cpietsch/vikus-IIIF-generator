# VIKUS IIIF Generator
This GitHub Repo contains code to build a VIKUS IIIF generator instance, which can be used to view IIIF Collections (Presentation 3.x API) with [VIKUS Viewer](https://github.com/cpietsch/vikus-viewer). The code crawls all manifests in a IIIF Collection (v3) recursively, downloads images of each canvas, creates spritesheets, extracts metadata, and generates similarity layouts using UMAP and Rasterfairy. The code also includes a REST API and websocket for real-time progress updates, and allows for the download of a ZIP archive for the VIKUS Viewer. The code uses redis cache for manifests and feature vectors and also extract embeddings with CLIP using huggingface transformers.

<img width="1166" alt="vikusdocker" src="https://user-images.githubusercontent.com/129529/186490880-1dffef6b-ba03-479c-985d-d32941d440b7.png">


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

### CLI

To run the CLI, run:

```
docker exec -it vikus-docker-vikusdocker-1 python cli.py https://resource.swissartresearch.net/manifest/zbz-collection-100
```
You can also use the CLI with the following [options](https://github.com/cpietsch/vikus-docker/blob/main/scripts/files/defaults.json):

```
python cli.py https://resource.swissartresearch.net/manifest/zbz-collection-100 collection.worker=1 collection.depth=1
```

## Usage

To use the VIKUS IIIF generator, open the frontend in a browser at http://localhost:8000/frontend/. Paste an IIIF Collection (v3) URL and click "Create". Click "Generate" to run all the steps.

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
Open the VIKUS IIIF generator API in a browser:
http://localhost:3000/docs


## Sub-projects
- https://github.com/cpietsch/vikus-docker-frontend/ (svelte)
- https://github.com/cpietsch/vikus-viewer

## Requirements
- Docker
- Docker Compose

## Notebooks
To start the notebook server on port 5000 instead of the server, connect to the vikusdocker and run
- `pip install jupyter-lab`
- `jupyter-lab --port 5000`

## Funding
The work on this project was made possible through the [Swiss Art Research Infrastructure (SARI)](https://swissartresearch.net/) in the framework of the [Bilder der Schweiz Online](https://bso.swissartresearch.net) project funded by the [Stiftung Familie Fehlmann](https://stiftung-familie-fehlmann.ch/).
