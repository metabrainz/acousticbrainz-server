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
                       cron \
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

RUN pip install uWSGI==2.0.17.1

# Consul template service is already set up, just need to copy the configuration
COPY ./docker/consul-template.conf /etc/consul-template.conf

# uwsgi service files
COPY ./docker/$deploy_env/uwsgi/uwsgi.service /etc/service/uwsgi/run
RUN chmod 755 /etc/service/uwsgi/run
COPY ./docker/$deploy_env/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini

RUN mkdir /cache_namespaces
RUN chown -R www-data:www-data /cache_namespaces

# Create a user named acousticbrainz for cron jobs
RUN useradd --create-home --shell /bin/bash acousticbrainz

# Add cron jobs
ADD docker/crontab /etc/cron.d/ab-crontab
RUN chmod 0644 /etc/cron.d/ab-crontab && crontab -u acousticbrainz /etc/cron.d/ab-crontab
RUN touch /var/log/stats_calc.log /var/log/stats_cache.log && chown acousticbrainz:acousticbrainz /var/log/stats_calc.log /var/log/stats_cache.log

# Make sure that the cron service doesn't start automagically
# http://smarden.org/runit/runsv.8.html
RUN touch /etc/service/cron/down

COPY . /code
RUN /code/node_modules/.bin/gulp
