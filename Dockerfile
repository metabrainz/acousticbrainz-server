FROM metabrainz/python:2.7 AS acousticbrainz-base

ARG deploy_env

# Dockerize
ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

# Install dependencies
# Node
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - && apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       ca-certificates \
                       git \
                       ipython \
                       libavcodec-dev \
                       libavformat-dev \
                       libavutil-dev \
                       libavresample-dev \
                       libffi-dev \
                       libfftw3-dev \
                       libpq-dev \
                       libsamplerate0-dev \
                       libqt4-dev \
                       libssl-dev \
                       libtag1-dev \
                       libxml2-dev \
                       libxslt1-dev \
                       libyaml-dev \
                       nodejs \
                       pkg-config \
                       pxz \
                       python-dev \
                       python-numpy-dev \
                       python-numpy \
                       swig2.0 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /code
RUN mkdir /code/hl_extractor
RUN mkdir /data
WORKDIR /code

# Gaia
# See https://github.com/MTG/gaia
RUN git clone https://github.com/MTG/gaia /tmp/gaia \
    && cd /tmp/gaia \
    && ./waf configure --with-python-bindings \
    && ./waf \
    && ./waf install \
    && cd / && rm -r /tmp/gaia

# Essentia
# See http://essentia.upf.edu/documentation/installing.html
RUN git clone https://github.com/MTG/essentia /tmp/essentia \
    && cd /tmp/essentia \
    && ./waf configure --mode=release --with-gaia --with-example=streaming_extractor_music_svm \
    && ./waf \
    && ./waf install \
    && ldconfig \
    && cp /tmp/essentia/build/src/examples/essentia_streaming_extractor_music_svm /usr/local/bin \
    && cd / && rm -r /tmp/essentia

# SVM models
RUN mkdir /tmp/models \
    && cd /tmp/models \
    && curl -L --silent -o models.tar.gz https://essentia.upf.edu/documentation/svm_models/essentia-extractor-svm_models-v2.1_beta1.tar.gz \
    && tar -xvzf models.tar.gz \
    && mv /tmp/models/v2.1_beta1/svm_models /data/ \
    && cd / && rm -r /tmp/models

# Python dependencies
RUN mkdir /code/docs/
COPY docs/requirements.txt /code/docs/requirements.txt
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY package.json /code
RUN npm install


FROM acousticbrainz-base AS acousticbrainz-dev

ARG deploy_env

COPY requirements_development.txt /code/requirements_development.txt
RUN pip install --no-cache-dir -r requirements_development.txt

COPY . /code


FROM acousticbrainz-base AS acousticbrainz-prod

ARG deploy_env

RUN pip install --no-cache-dir uWSGI==2.0.17.1

RUN mkdir /cache_namespaces
RUN chown -R www-data:www-data /cache_namespaces

# Consul template service is already set up, just need to copy the configuration
COPY ./docker/consul-template.conf /etc/consul-template.conf

# runit service files
# All services are created with a `down` file, preventing them from starting
# rc.local removes the down file for the specific service we want to run in a container
# http://smarden.org/runit/runsv.8.html

# uwsgi service files
COPY ./docker/uwsgi/uwsgi.service /etc/service/uwsgi/run
COPY ./docker/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
RUN touch /etc/service/uwsgi/down

# hl_extractor service files
COPY ./docker/hl_extractor/hl_extractor.service /etc/service/hl_extractor/run
RUN touch /etc/service/hl_extractor/down

# dataset evaluator service files
COPY ./docker/dataset_eval/dataset_eval.service /etc/service/dataset_eval/run
RUN touch /etc/service/dataset_eval/down

# Add cron jobs
ADD docker/crontab /etc/cron.d/acousticbrainz
RUN chmod 0644 /etc/cron.d/acousticbrainz
RUN touch /etc/service/cron/down

COPY ./docker/$deploy_env/rc.local /etc/rc.local

COPY . /code
RUN /code/node_modules/.bin/gulp
