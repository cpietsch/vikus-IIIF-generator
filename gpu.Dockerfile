FROM nvcr.io/nvidia/pytorch:22.07-py3

ENV PYTHONUNBUFFERED True
ENV PORT 5000
ENV WORKER 4
ENV TIMEOUT 60
ENV USEGPU True

EXPOSE $PORT

# Copy local code to the container image.
COPY ./scripts /scripts
WORKDIR /scripts

# Install production dependencies.
RUN pip install -r requirements-gpu.txt
#RUN spacy download en_core_web_md
RUN spacy download en_core_web_sm
RUN exec python downloadModel.py

# Using Debian, as root
RUN curl -fsSL https://deb.nodesource.com/setup_17.x | bash -
RUN apt-get install -y nodejs

RUN git clone https://github.com/cpietsch/sharpsheet /modules/sharpsheet; cd /modules/sharpsheet; npm install;

CMD exec gunicorn main:app -w $WORKER --timeout $TIMEOUT -k uvicorn.workers.UvicornWorker