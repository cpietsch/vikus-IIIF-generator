# vikus-docker
VIKUS Viewer Docker instance builder for IIIF Collections (Presentation 3.x API)
# Features
- crawl all manifests in a [IIIF Collection](https://iiif.io/api/presentation/3.0/) (v3) recursively
- Async Queueing for crawling manifests and images
- downloads an image of each canvas and save it to disk
- create spritesheets
- extract metadata from manifests and generate keywords
- extract embeddings with CLIP using [huggingface transformers](https://huggingface.co/docs/transformers/model_doc/clip)
- redis cache for manifests and feature vectors
- generate similarity layouts with [UMAP](https://umap-learn.readthedocs.io/en/latest/) and [Rasterfairy](https://github.com/Quasimondo/RasterFairy)
- REST Api
- Websocket realtime progress
- Download data ZIP archive for VIKUS Viewer

# RUN
docker compose up

## GPU Support (NVIDIA)
- this will increase the speed of CLIP features extraction
docker compose -f docker-compose.gpu.yml up

## rebuild the image
docker-compose down
docker-compose up --force-recreate --build -d

# Usage
- Open the VIKUS Docker frontend in a browser: http://localhost:8000/frontend/
- Paste an IIIF Collection (v3) URL and click "Create"
- Click "Generate", this will run all the steps.
-- Optional: Fiddle with the settings of each step and or run them individually
- Open a VIKUS Viewer preview
- Download the data ZIP and extract it into the /data folder of the VIKUS Viewer

# API
Open the VIKUS Docker API in a browser:
http://localhost:3000/docs


# Sub-projects
- https://github.com/cpietsch/vikus-docker-frontend/ (svelte)
- https://github.com/cpietsch/vikus-viewer (docker branch)


# Requirements
- Docker
- Docker Compose


# Notebooks
To start the notebook server on port 5000 instead of the server, connect to the vikusdocker and run
- `pip install jupyter-lab`
- `jupyter-lab --port 5000`


# Funding
The work on this project was made possible through funding of the [Swiss Art Research Infrastructure (SARI)](https://swissartresearch.net/).