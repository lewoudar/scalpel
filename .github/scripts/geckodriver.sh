#!/bin/bash

# the script is inspired by this article https://dev.to/erikwhiting88/install-browsers-and-webdrivers-in-travisci-n76

set -ex -o pipefail

echo "Install geckodriver"

wget -N https://github.com/mozilla/geckodriver/releases/download/v0.27.0/geckodriver-v0.27.0-linux64.tar.gz -P ~/

tar -xzf ~/geckodriver-v0.27.0-linux64.tar.gz -C ~/

rm ~/geckodriver-v0.27.0-linux64.tar.gz

sudo mv -f ~/geckodriver /usr/local/bin/geckodriver

sudo chmod 0755 /usr/local/bin/geckodriver
