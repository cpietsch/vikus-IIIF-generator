# https://hub.docker.com/_/python
FROM nginx:latest
RUN apt-get update
RUN apt-get install -y git nodejs
# Install NPM
RUN curl -L https://npmjs.org/install.sh | sh 
RUN mkdir /web
WORKDIR /web

RUN git clone https://github.com/cpietsch/vikus-viewer /usr/share/nginx/html/viewer; \
    cd /usr/share/nginx/html/viewer; \
    git switch docker;

RUN git clone https://github.com/cpietsch/vikus-docker-frontend /usr/share/nginx/html/docker;
WORKDIR /usr/share/nginx/html/docker
RUN npm install
RUN npm build
WORKDIR /web