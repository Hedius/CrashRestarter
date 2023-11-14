#!/usr/bin/env python3

__author__ = 'Hedius'
__version__ = '2.1.0'
__license__ = 'GPLv3'

#  Copyright (C) 2023. Hedius gitlab.com/hedius
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

import argparse
import configparser
import os
import sys
import time
from threading import Thread

import requests
from discord_webhook import DiscordEmbed, DiscordWebhook
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
    # Dirty Hack for support for battlelog proxies
    proxy = os.getenv('BATTLELOG_PROXY')
    proxies = None
    if proxy:
        proxies = {
            'http': proxy,
            'https': proxy,
        }
    url = f'http://battlelog.battlefield.com/bf4/servers/show/pc/{server["GUID"]}/?json=1'
    r = requests.get(url, proxies=proxies)
    try:
        data = r.json()
    except requests.exceptions.JSONDecodeError:
        # Assume that the connection failed / battlelog is broken partly...
        # And return online....
        # False might be a little dangerous here
        return True
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
    r = ping(address, count=5, interval=1, privileged=False, payload_size=32)
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


def monitor_server(gp: GPortal, webhook, server):
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
    notification_sent = False
    while True:
        try:
            if get_server_status(server) is False:
                # server down - send disc notification
                # Ping the server -> Only restart if we can ping it
                if 'IP' in server and not ping_server(server['IP']):
                    # Cannot ping server - skip for now
                    if not notification_sent:
                        send_discord_embed(webhook, 'Server Ping Failed',
                                           'Cannot ping offline server **{}**! Trying again '
                                           'in 5 minutes!'
                                           .format(server['NAME']), 16711680)
                    time.sleep(300)
                    notification_sent = True
                    continue
                else:
                    send_discord_embed(webhook, 'ALARM! Server is down!',
                                       '**{}**'.format(server['NAME']), 16711680)
                notification_sent = False

                # Trigger a restart
                try:
                    if server['restartURL'] not in ('', None):
                        gp.restart_server(server['restartURL'])
                    else:
                        gp.restart_fragnet_server(server['serviceID'])
                    send_discord_embed(webhook, 'Restarted server',
                                       'Successfully restarted server **{}**.'
                                       .format(server['NAME']), 65280)
                    time.sleep(180)
                except Exception as e:
                    logger.exception(e)
                    send_discord_embed(webhook, 'Restart failed',
                                       'Restart of server **{}** failed! Trying again '
                                       'in 10 minutes! Error: {}'
                                       .format(server['NAME'], e), 16711680)
                    time.sleep(420)  # cooldown after restart

            gp.close_driver()
        except Exception as e:
            logger.exception(e)
        finally:
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
        # Sleep a little to not send all requests at the same time
        time.sleep(5)
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
    gp = GPortal(section['selenium'], section['user'], section['pw'],
                 config['Fragnet']['user'], config['Fragnet']['pw'])

    # discord
    section = config['DiscordWebhook']
    webhook = section['webhook']

    # BF4 servers
    bf4_servers = []
    i = 1
    try:
        while config.has_section('Server' + str(i)):
            section = config['Server' + str(i)]

            if ('restart' not in section['restartURL']
                    and section['restartURL'] not in (None, '')):
                print('Invalid RestartURL for server {}!'.format(i))
                exit(1)

            new_dict = {
                'NAME': section['GUID'],
                'ID': i,
                'GUID': section['GUID'],
                'restartURL': section.get('restartURL'),
                'serviceID': section.get('serviceID')
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
