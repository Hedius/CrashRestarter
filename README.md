# E4GL Crash Restarter
The E4GL Crash Restarter docker image allows you to monitor G-Portal.com and/or Fragnet/XLGames BF4 servers and restarts them if needed.

## Features
- restart servers if needed (crashes)
- send notifications to a Discord server by using a webhook

## Installation
### Get the restart URL of your server
Copy the url of the restart button.

![Restart URL](https://i.imgur.com/3QMdCk4.png "Restart URL")

### Config
Copy the example config to crashrestarter.cfg and edit it.

**The crashrestarter.cfg has to be in the root folder of the report!**
```
[GPortal]
user=
pw=
# Do not change this if you use the supplied compose
selenium=http://selenium:4444

[Fragnet]
user=
pw=

# optional - leave it empty if you do not want to use discord notifications
[DiscordWebhook]
webhook=

[Logging]
# Debug, Info, Warning, Error, Critical
loglevel=Debug

# create a section for each server
[Server1]
GUID=
# For g-portal
restartURL=https://www.g-portal.com/eur/server/bf4/xxxx/restartService
# For Fragnet. https://gamepanel.fragnet.net/Service/Home/X
serviceID=X
# One of both is required.

# [Server2]
# GUID=
# restartURL=
```

### docker-compose
 1. clone the repository
 2. copy crashrestarter.cfg.example to crashrestarter.cfg and edit it
    1. leave the webhook setting empty if you do not want to use it
 3. make docker
 

## Updating
 ### docker-compose
 `make update-docker`
