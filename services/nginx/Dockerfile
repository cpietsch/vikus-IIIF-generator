# https://hub.docker.com/_/python
FROM nginx:latest

RUN mkdir /web
WORKDIR /web

RUN git clone https://github.com/cpietsch/vikus-viewer /usr/share/nginx/html/viewer; \
    git switch docker;
RUN git clone https://github.com/cpietsch/vikus-docker-frontend /usr/share/nginx/html/docker; \
    cd /usr/share/nginx/html/docker; \
    npm install; npm run build;