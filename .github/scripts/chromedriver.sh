#!/bin/bash

# the script is inspired by this gist https://gist.github.com/ziadoz/3e8ab7e944d02fe872c3454d17af31a5

set -ex -o pipefail

echo "Install chromedriver"

CHROME_DRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE)

wget -N https://chromedriver.storage.googleapis.com/"$CHROME_DRIVER_VERSION"/chromedriver_linux64.zip -P ~/

unzip ~/chromedriver_linux64.zip -d ~/

rm ~/chromedriver_linux64.zip

sudo mv -f ~/chromedriver /usr/local/bin/chromedriver

sudo chown root:root /usr/local/bin/chromedriver

sudo chmod 0755 /usr/local/bin/chromedriver
