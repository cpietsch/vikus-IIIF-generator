# https://hub.docker.com/_/python
FROM nginx:latest
RUN apt-get update
RUN apt-get install -y git
# RUN apt-get install -ynodejs
# # Install NPM
# RUN curl -fsSL https://deb.nodesource.com/setup_17.x | bash -
# RUN apt-get install -y nodejs
# RUN mkdir /web
# WORKDIR /web

RUN git clone https://github.com/cpietsch/vikus-viewer /usr/share/nginx/html/viewer; \
    cd /usr/share/nginx/html/viewer; \
    git switch docker;

RUN git clone https://github.com/cpietsch/vikus-docker-frontend /usr/share/nginx/html/frontend; \
    cd /usr/share/nginx/html/frontend; \
    git switch gh-pages;

# WORKDIR /usr/share/nginx/html/docker
# RUN npm install
# RUN npm run build
# WORKDIR /web