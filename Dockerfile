# https://hub.docker.com/_/python
FROM python:3.8

ENV PYTHONUNBUFFERED True
ENV PORT 5000
ENV WORKER 4
ENV TIMEOUT 60

EXPOSE $PORT

# Copy local code to the container image.
COPY ./scripts /scripts
WORKDIR /scripts

# Install production dependencies.
RUN pip install -r requirements.txt
#RUN spacy download en_core_web_md
RUN spacy download en_core_web_sm

# Using Debian, as root
RUN curl -fsSL https://deb.nodesource.com/setup_17.x | bash -
RUN apt-get install -y nodejs

RUN git clone https://github.com/cpietsch/sharpsheet /modules/sharpsheet; cd /modules/sharpsheet; npm install;

RUN exec python downloadModel.py

#CMD exec uvicorn --port :$PORT --workers 1 --threads 8 --timeout 0 main:app
CMD exec gunicorn main:app -w $WORKER --timeout $TIMEOUT -k uvicorn.workers.UvicornWorker