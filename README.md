# E4GL Crash Restarter
The E4GL Crash Restarter docker image allows you to monitor G-Portal.com BF4 servers and restarts them if needed.

## Features
- restart servers if needed (crashes)
- send notifications to a Discord server by using a webhook

## Installation
### docker-compose
 1. clone the repository
 2. copy crashrestarter.cfg.example to crashrestarter.cfg and edit it
 3. sudo docker-compose up -d

## Updating
### docker-compose
 1. sudo docker-compose down --rmi all
 2. git pull
 3. sudo docker-compose up -d
