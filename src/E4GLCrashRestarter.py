#!/usr/bin/env python3

__author__ = 'Hedius'
__version__ = '2.0.0'
__license__ = 'GPLv3'

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

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed
from icmplib import ping
from loguru import logger

from GPortal import GPortal


def send_discord_embed(webhook, title, description, color):
    """
    Send a discord notification
    :param webhook: url
    :param title: title of msg
    :param description: content of msg
    :param color: color of msg
    """
    logger.info(f'{title}: {description}')
    if not webhook or len(webhook) == 0:
        return
    discord = DiscordWebhook(url=webhook)
    embed = DiscordEmbed(title=title, description=description, color=color)
    discord.add_embed(embed)
    discord.execute()


def check_battlelog(server):
    """
    Return False if the server is offline else true
    :param server: server dict
    :returns: boolean
    """
    url = f'http://battlelog.battlefield.com/bf4/servers/show/pc/{server["GUID"]}/?json=1'
    r = requests.get(url)
    data = r.json()
    if (r.status_code > 400
            and data['type'] == 'error'
            and 'SERVER_INFO_NOT_FOUND' in data['message']):
        return False
    extract_server_info(server, data)
    return True


def ping_server(address):
    """
    Pings the server IP -> only restart if pingable
    :param address: IP / or DNS
    :return: True if pingable else False
    """
    r = ping(address, count=5, interval=1)
    return r.is_alive


def extract_server_info(server, data):
    """
    Extracts and saves the server name in the server Dict.
    Also saved the server IP in the dict
    :param server: server config dict
    :param data: battlelog profile JSON
    :returns: server name
    """
    try:
        name = data['message']['SERVER_INFO']['name']
        server['IP'] = data['message']['SERVER_INFO']['ip']
        if name not in (server['NAME'], server['GUID']):
            server['NAME'] = name
    except (KeyError, TypeError):
        pass
    return server['NAME']


def get_server_status(server):
    """
    Ask Battlelog for the status of the given server
    :param server: datadict of server
    :returns: True if online
              False if stuck/offline
    """
    # Main Function
    if check_battlelog(server) is False:
        logger.warning('Server {} with name/GUID {} is offline! '
                       'Checking again in 120s!'
                       .format(server['ID'], server['NAME']))
        time.sleep(120)
        if check_battlelog(server) is False:
            logger.warning('Server {} with name/GUID {} is offline! '
                           'Restart needed!'
                           .format(server['ID'], server['NAME']))
            return False
    logger.debug('Server {} with name/guid {} is online'
                 .format(server['ID'], server['NAME']))
    return True


def monitor_server(gp, webhook, server):
    """
    Check the status of a server every 5 minutes and restarts the server if
    it is down.
    :param gp: object of class GPortal
    :param webhook: url
    :param server: datadict of server
    """
    logger.info('Started monitoring for server {}: {}'
                .format(server['ID'], server['GUID']))
    # ToDO the colour codes are hardcoded numbers atm. not clean
    # Too lazy to migrate to f-strings here.
    while True:
        server['IP'] = '10.190.1.1'
        if get_server_status(server) is False:
            # server down - send disc notification
            send_discord_embed(webhook, 'ALARM! Server is down!',
                               '**{}**'.format(server['NAME']), 16711680)

            # Ping the server -> Only restart if we can ping it
            if 'IP' in server and not ping_server(server['IP']):
                # Cannot ping server - skip for now
                send_discord_embed(webhook, 'Server Ping Failed',
                                   'Cannot ping offline server\n**{}**\n! Trying again '
                                   'in 5 minutes!'
                                   .format(server['NAME']), 16711680)
                time.sleep(300)
                continue

            # Trigger a restart
            try:
                gp.restart_server(server['restartURL'])
                send_discord_embed(webhook, 'Restarted server',
                                   'Successfully restarted server\n**{}**.'
                                   .format(server['NAME']), 65280)
                time.sleep(180)
            except Exception as e:
                logger.exception(e)
                send_discord_embed(webhook, 'Restart failed',
                                   'Restart of server\n**{}**\nfailed! Trying again '
                                   'in 10 minutes! Error: {}'
                                   .format(server['NAME'], e), 16711680)
                time.sleep(420)  # cooldown after restart
            finally:
                gp.close_driver()
        time.sleep(180)


def start_monitoring(gp, webhook, bf4_servers):
    """
    Start a thread for each server to monitor
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


# Config/Argv
def read_config(config_file):
    """
    Read the config and connection data from the given config file
    :param config_file: path to config file
    :returns: connection socket for G-Portal (object)
              url of DiscordWebhook
              BF4 servers in a list
    """
    # read config
    if not os.path.isfile(config_file):
        print('Error while accessing config!', file=sys.stderr)
        exit(1)

    config = configparser.ConfigParser(interpolation=None)
    config.read(config_file)
    # g-portal
    section = config['GPortal']
    gp = GPortal(section['user'], section['pw'], section['selenium'])

    # discord
    section = config['DiscordWebhook']
    webhook = section['webhook']

    # BF4 servers
    bf4_servers = []
    i = 1
    try:
        while config.has_section('Server' + str(i)):
            section = config['Server' + str(i)]

            if 'restart' not in section['restartURL']:
                print('Invalid RestartURL for server {}!'.format(i))
                exit(1)

            new_dict = {
                'NAME': section['GUID'],
                'ID': i,
                'GUID': section['GUID'],
                'restartURL': section['restartURL']
            }
            bf4_servers.append(new_dict)
            i += 1
    except (configparser.Error, KeyError):
        print('Error while reading BF4 servers from config!', file=sys.stderr)
        exit(1)
    return gp, webhook, bf4_servers


def main():
    parser = argparse.ArgumentParser(description='Crash handler for G-Portal '
                                     'BF4 servers by E4GL')
    parser.add_argument('-c', '--config', help='path to config file',
                        required=True, dest='configFile')
    args = parser.parse_args()

    gp, webhook, bf4_servers = read_config(args.configFile)

    start_monitoring(gp, webhook, bf4_servers)


if __name__ == '__main__':
    main()
