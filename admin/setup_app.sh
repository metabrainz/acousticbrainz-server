#!/bin/bash

# Setting up the application
if [ $# -eq 1 ]
  then
    cd $1
else
    echo "Application directory is not specified. Using current directory!"
fi

echo "source venv-acousticbrainz/bin/activate" >> ~/.bashrc
virtualenv ../venv-acousticbrainz
source ../venv-acousticbrainz/bin/activate
# We install gaia in the system, but it should also be available in the venv
# Generally putting this dir in a venv could be dangerous but in our case
# there is nothing else here.
echo "/usr/local/lib/python2.7/dist-packages/" > ../venv-acousticbrainz/lib/python2.7/site-packages/gaia.pth

pip install -U pip
pip install -r requirements.txt

python manage.py init_db
python manage.py init_test_db

npm install
./node_modules/.bin/gulp
