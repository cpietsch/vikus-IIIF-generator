# vikus-docker
VIKUS Viewer Docker instance builder for IIIF Collections


# RUN
docker compose up

## rebuild the image
docker-compose down
docker-compose up -d

# Usage
Open the VIKUS Docker frontend in a browser:
http://localhost:8000/frontend


# Related projects
- https://github.com/cpietsch/vikus-docker-frontend/
- https://github.com/cpietsch/vikus-viewer (docker branch)


# Features
- crawl all manifests in a [IIIF Collection](https://iiif.io/api/presentation/3.0/) (v3) recursively
- download an image of each canvas and save it to disk
- create spritesheets
- extract metadata from manifests and generate keywords
- extract feature vector with CLIP using [huggingface transformers](https://huggingface.co/docs/transformers/model_doc/clip)
- redis cache for manifests and feature vectors
- generate similarity layouts with [UMAP](https://umap-learn.readthedocs.io/en/latest/) and [Rasterfairy](https://github.com/Quasimondo/RasterFairy)
- http API
- Websocket realtime progress logs


# Notebooks
To start the notebook server on port 5000 instead of the server, connect to the vikusdocker and run
- `pip install jupyter-lab`
- `jupyter-lab --port 5000`
