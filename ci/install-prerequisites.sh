#!/usr/bin/env bash

# Make sure we have all submodules
git submodule update --init --recursive

# Install Python requirements
pip install -r requirements.txt
python -m spacy download en > spacy.log
python -m nltk.downloader wordnet propbank
rm -rf ~/nltk_data/corpora/propbank
git clone https://github.com/propbank/propbank-frames ~/nltk_data/corpora/propbank

# Install DyNet
if [ -d dynet ]; then
  cd dynet
  git pull https://github.com/clab/dynet
else
  git clone https://github.com/clab/dynet
  cd dynet
fi
if [ -d eigen ]; then
  cd eigen
  hg pull --update
  cd ..
else
  hg clone https://bitbucket.org/eigen/eigen
fi
mkdir -p build
[ -d build/eigen ] || ln -sf eigen build/
cd build
export CXX="g++-4.8" CC="gcc-4.8"
cmake .. -DEIGEN3_INCLUDE_DIR=eigen -DPYTHON=`which python`
make
cd python
python setup.py install

# Install UCCA
cd ucca
python setup.py install
