# https://hub.docker.com/_/python
FROM python:3.8

ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
COPY ./scripts /scripts
WORKDIR /scripts

#RUN apk add --no-cache gcc musl-dev linux-headers

# install rust
# RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
# ENV PATH="/root/.cargo/bin:${PATH}"

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt
RUN spacy download en_core_web_lg

ENV PORT 5000
EXPOSE $PORT

# Using Debian, as root
RUN curl -fsSL https://deb.nodesource.com/setup_17.x | bash -
RUN apt-get install -y nodejs

RUN git clone https://github.com/cpietsch/sharpsheet /modules/sharpsheet; cd /modules/sharpsheet; npm install;

#CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
CMD exec python main.py

