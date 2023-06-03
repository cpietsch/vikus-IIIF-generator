# https://hub.docker.com/_/python
FROM nginx:latest
RUN apt-get update
RUN apt-get install -y git

RUN git clone https://github.com/cpietsch/vikus-viewer /usr/share/nginx/html/viewer; \
    cd /usr/share/nginx/html/viewer;

RUN git clone https://github.com/cpietsch/vikus-docker-frontend /usr/share/nginx/html/frontend; \
    cd /usr/share/nginx/html/frontend; \
    git switch gh-pages;
