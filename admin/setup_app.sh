#!/bin/bash

# Setting up the application
if [ $# -eq 1 ]
  then
    cd $1
else
    echo "Application directory is not specified. Using current directory!"
fi

echo "source venv-acousticbrainz/bin/activate" > ~/.bashrc
virtualenv ../venv-acousticbrainz
source ../venv-acousticbrainz/bin/activate

pip install -U pip
pip install -r requirements.txt

python manage.py init_db
python manage.py init_test_db

npm install
./node_modules/.bin/gulp
