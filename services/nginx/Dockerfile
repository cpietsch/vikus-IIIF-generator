# https://hub.docker.com/_/python
FROM nginx:latest
RUN apt-get update
RUN apt-get install -y git

RUN git clone https://github.com/cpietsch/vikus-viewer /usr/share/nginx/html/viewer

RUN git clone https://github.com/cpietsch/vikus-docker-frontend -b gh-pages /usr/share/nginx/html/frontend
