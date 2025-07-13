#!/bin/bash

# Script to install Node.js on a Linux system

echo "Starting Node.js installation..."

# Update the package index
echo "Updating package index..."
apt update -y

echo "Installing upgrade..."
apt upgrade -y

# install node
echo "Installing Node JS..."
apt install nodejs -y
 
# install npm
# echo "Installing NPM..."
# apt install npm -y