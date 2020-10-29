#!/usr/bin/env python3

__author__ = "Hedius"
__version__ = "1.2.2"
__license__ = "GPLv3"

#  Copyright (C) 2020. Hedius gitlab.com/hedius
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

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


def send_discord_embed(webhook, title, description, color):
    """Send a discord notification
    :param webhook: url
    :param title: title of msg
    :param description: content of msg
    :param color: color of msg
    """
    discord = DiscordWebhook(url=webhook)
    embed = DiscordEmbed(title=title, description=description, color=color)
    discord.add_embed(embed)
    discord.execute()


def get_server_status(server):
    """Ask Battlelog for the status of the given server
    :param server: datadict of server
    :returns: True if online
              False if stuck/offline
    """
    url = ("http://battlelog.battlefield.com/bf4/servers/show/pc/{}/"
           .format(server["GUID"]))
    r = requests.get(url)
    if "Sorry, that page doesn't exist" in r.text:
        log.warning("Battlelog> Server {} with GUID {} is offline! "
                    "Checking again in 30s!"
                    .format(server["ID"], server["GUID"]))

        r = requests.get(url)
        if "Sorry, that page doesn't exist" in r.text:
            log.warning("Battlelog> Server {} with GUID {} is offline! "
                        "Restart needed!"
                        .format(server["ID"], server["GUID"]))
            return False
    log.debug("Battlelog> Server {} is online".format(server["ID"]))
    return True


def monitor_server(gp, webhook, server):
    """Check the status of a server every 5 minutes and restarts the server if it
    is down
    :param gp: object of class GPortal
    :param webhook: url
    :param server: datadict of server
    """
    log.info("Started monitoring for server {}: {}"
             .format(server["ID"], server["GUID"]))
    while True:
        if get_server_status(server) is False:
            # server down - send disc notification
            if webhook and webhook != "":
                send_discord_embed(webhook, "ALARM! HELP! Server {} down!"
                                   .format(server["ID"]), "Restarting server {}!"
                                   .format(server["GUID"]), 16711680)
            restart = gp.restart_server(server["restartURL"])
            if not webhook or webhook == "":
                time.sleep(600)
                continue
            if restart:
                send_discord_embed(webhook, "Restart",
                                   "Successfully restarted server {}."
                                   .format(server["ID"]), 65280)
                time.sleep(600)  # cooldown after restart
            else:
                send_discord_embed(webhook, "Restart", "Restart of server {} "
                                                       "failed! Trying again in 10 minutes!"
                                   .format(server["ID"]), 16711680)
                time.sleep(600)
        time.sleep(240)


def start_monitoring(gp, webhook, bf4_servers):
    """Start a thread for each server to monitor
    :param gp: object of class GPortal
    :param webhook: url
    :param bf4_servers: list containing all datadicts of servers
    """
    threads = []
    for server in bf4_servers:
        new_thread = Thread(target=monitor_server, args=(gp, webhook, server))
        new_thread.daemon = True
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()


def config_logging(log_level):
    """Configure the logger
    :param log_level: loglevel as string
    """
    log_levels = {
        'NOTSET': 0,
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50
    }
    if log_level.upper() in log_levels:
        level = log_levels[log_level.upper()]
    else:
        level = 10
    log.basicConfig(format="%(asctime)s | %(levelname)s | "
                           "%(funcName)s | %(message)s",
                    level=level)


# Config/Argv
def read_config(config_file):
    """Read the config and connection data from the given config file
    :param config_file: path to config file
    :returns: connection socket for G-Portal (object)
              url of DiscordWebhook
              BF4 servers in a list
    """
    # read config
    if not os.path.isfile(config_file):
        print("Error while accessing config!", file=sys.stderr)
        exit(1)

    config = configparser.ConfigParser(interpolation=None)
    config.read(config_file)
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
        config_logging(section["loglevel"])
    except (configparser.Error, KeyError):
        print("Error while reading Logging from config!", file=sys.stderr)
        exit(1)
    # BF4 servers
    bf4_servers = []
    i = 1
    try:
        while config.has_section("Server" + str(i)):
            section = config["Server" + str(i)]
            newdict = {
                'ID': i,
                'GUID': section["GUID"],
                'restartURL': section["restartURL"]
            }
            bf4_servers.append(newdict)
            i += 1
    except (configparser.Error, KeyError):
        print("Error while reading BF4 servers from config!", file=sys.stderr)
        exit(1)
    return gp, webhook, bf4_servers


def main():
    parser = argparse.ArgumentParser(description="Crash handler for G-Portal "
                                     "BF4 servers by E4GL")
    parser.add_argument("-c", "--config", help="path to config file",
                        required=True, dest="configFile")
    args = parser.parse_args()

    gp, webhook, bf4_servers = read_config(args.configFile)

    start_monitoring(gp, webhook, bf4_servers)


if __name__ == "__main__":
    main()
