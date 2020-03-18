#!/bin/sh

echo "Installing Manalyze"
apt-get install libboost-regex-dev libboost-program-options-dev libboost-system-dev libboost-filesystem-dev libssl-dev build-essential cmake git -y
cmake bin/manalyze/.
make bin/manalyze -j5

cd .. # Back to bin folder

echo "Installing peframe"
cd peframe
sh install.sh

