#!/usr/bin/env python3
"""
Copyright (C) 2019 Hedius gitlab.com/hedius

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
__author__ = "Hedius"
__version__ = "1.1"
__license__ = "GPLv3"
__status__ = "Production"

import sys
import os
import configparser
import argparse
import time
from threading import Thread
import logging as log

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed

from GPortal import GPortal

def sendDiscordEmbed(webhook, title, description, color):
    """
    sends a discord notification
    :param webhook: url
    :param title: title of msg
    :param description: content of msg
    :param color: color of msg
    """
    discord = DiscordWebhook(url=webhook)
    embed = DiscordEmbed(title=title, description=description, color=color)
    discord.add_embed(embed)
    discord.execute()


def getServerStatus(server):
    """
    asks Battlelog for the status of the given server
    :param server: datadict of server
    :returns: True if online
              False if stuck/offline
    """
    url = "http://battlelog.battlefield.com/bf4/servers/show/pc/{}/".format(server["GUID"])
    r = requests.get(url)
    if "Sorry, that page doesn't exist" in r.text:
        log.warning("Battlelog> Server {} with GUID {} is offline! Checking again in 30s!"
                    .format(server["ID"], server["GUID"]))
        time.sleep(30)
        r = requests.get(url)
        if "Sorry, that page doesn't exist" in r.text:
            log.warning("Battlelog> Server {} with GUID {} is offline! Restart needed!"
                        .format(server["ID"], server["GUID"]))
            return False
    log.debug("Battlelog> Server {} is online".format(server["ID"]))
    return True


def monitorServer(gp, webhook, server):
    """
    checks the status of a server every 5 minutes and restarts the server if it
    is down
    :param gp: object of class GPortal
    :param webhook: url
    :param server: datadict of server
    """
    log.info("Started monitoring for server {}: {}"
             .format(server["ID"], server["GUID"]))
    while True:
        if getServerStatus(server) == False:
            # server down - send disc notification
            sendDiscordEmbed(webhook, "ALARM! HELP! Server {} down!".format(server["ID"]),
                             "Restarting server {}!".format(server["GUID"]), 16711680)
            if gp.restartServer(server["restartURL"]):
                sendDiscordEmbed(webhook, "Restart", "Successfully restarted server {}."
                                 .format(server["ID"]), 65280)
                time.sleep(900) # cooldown after restart
            else:
                sendDiscordEmbed(webhook, "Restart", "Restart of server {} failed! "
                                 "Trying again in 3 minutes!".format(server["ID"]), 16711680)
        time.sleep(300)


def startMonitoring(gp, webhook, bf4Servers):
    """
    starts a thread for each server to monitor
    :param gp: object of class GPortal
    :param webhook: url
    :param bf4Servers: list containing all datadicts of servers
    """
    threads = []
    for server in bf4Servers:
        newThread = Thread(target=monitorServer, args=(gp, webhook, server))
        newThread.daemon = True
        threads.append(newThread)
        newThread.start()
    for t in threads:
        t.join()


def configLogger(loglevel):
    """
    configures the logger
    :param loglevel: loglevel as string
    """
    loglevels = {
        'NOTSET': 0,
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50
    }
    if loglevel.upper() in loglevels:
        level = loglevels[loglevel.upper()]
    else:
        level = 10
    log.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    level=level)

# Config/Argv
def readConfig(configFile):
    """
    reads the config and connection data from the given config file
    :param configFile: path to config file
    :returns: connection socket for G-Portal (object)
              url of DiscordWebhook
              BF4 servers in a list
    """
    # read config
    if not os.path.isfile(configFile):
        print("Error while accessing config!", file=sys.stderr)
        exit(1)

    config = configparser.ConfigParser(interpolation=None)
    config.read(configFile)
    # g-portal
    try:
        section = config["GPortal"]
        gp = GPortal(section["user"], section["pw"])
    except (configparser.Error, KeyError):
        print("Error while reading G-Portal login data from config!",
              file=sys.stderr)
        exit(1)
    # discord
    try:
        section = config["DiscordWebhook"]
        webhook = section["webhook"]
    except (configparser.Error, KeyError):
        print("Error while reading DiscordWebhook from config!",
              file=sys.stderr)
        exit(1)
    # logging
    try:
        section = config["Logging"]
        configLogger(section["loglevel"])
    except (configparser.Error, KeyError):
        print("Error while reading Logging from config!", file=sys.stderr)
        exit(1)
    # BF4 servers
    bf4Servers = []
    i = 1
    try:
        while config.has_section("Server" + str(i)):
            section = config["Server" + str(i)]
            newdict = {
                'ID': i,
                'GUID': section["GUID"],
                'restartURL': section["restartURL"]
            }
            bf4Servers.append(newdict)
            i += 1
    except (configparser.Error, KeyError):
        print("Error while reading BF4 servers from config!", file=sys.stderr)
        exit(1)
    return gp, webhook, bf4Servers


def main():
    parser = argparse.ArgumentParser(description="Crash handler for G-Portal BF4 servers by E4GL")
    parser.add_argument("-c", "--config", help="path to config file", required=True,
                        dest="configFile")
    args = parser.parse_args()

    gp, webhook, bf4Servers = readConfig(args.configFile)

    startMonitoring(gp, webhook, bf4Servers)


if __name__ == "__main__":
    main()


