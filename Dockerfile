# https://hub.docker.com/_/python
FROM python:3.10-slim

ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
ENV PORT 5000

WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE $PORT

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
