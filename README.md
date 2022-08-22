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


# Notebooks
To start the notebook server on port 5000 instead of the server, connect to the vikusdocker and run
- `pip install jupyter-lab`
- `jupyter-lab --port 5000`