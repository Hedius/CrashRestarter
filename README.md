# E4GL Crash Restarter
The E4GL Crash Restarter docker image allows you to monitor G-Portal.com BF4 servers and restarts them if needed.

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

# optional - leave it empty if you do not want to use discord notifications
[DiscordWebhook]
webhook=

[Logging]
# Debug, Info, Warning, Error, Critical
loglevel=Debug

# create a section for each server
[Server1]
GUID=
restartURL=

# [Server2]
# GUID=
# restartURL=
```

### docker-compose
 1. clone the repository
 2. copy crashrestarter.cfg.example to crashrestarter.cfg and edit it
    1. leave the webhook setting empty if you do not want to use it
 3. make docker
 
 ### Directly on machine
 2. Install the requirements with `make install`
 3. copy crashrestarter.cfg.example to crashrestarter.cfg and edit it
    1. leave the webhook setting empty if you do not want to use it
 4. Start the script: `make start`

## Updating
 ### docker-compose
 `make update-docker`

 ### Directly on machine
 1. End the script
 2. Update and start it again with `make start`
