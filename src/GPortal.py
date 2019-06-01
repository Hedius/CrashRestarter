#!/usr/bin/env python3
__author__ = "Hedius"
__version__ = "1.1"
__license__ = "GPLv3"
__status__ = "Production"

import sys
import requests
import logging as log

class GPortal:
    """connector for G-Portal.com"""
    def __init__(self, user, pw):
        """
        init GPortal
        :param user: G-Portal.com username/email
        :param pw: G-Portal.com password
        """
        self.user = user
        self.pw = pw


    def restartServer(self, restartURL):
        """
        restarts a G-Portal Battlefield 4 server
        :param restartURL: restartURL of server
        :returns: True on success
                  False on failure
        """
        # login
        data = {'_method': 'POST', 'login': self.user, 'password': self.pw}
        s = requests.session()
        s.post("https://id2.g-portal.com/login", data=data)
        r = s.get("https://id2.g-portal.com/goto/www.g-portal.com")
        if "My Servers" not in r.text:
            err = "GPortal> Login failed!"
            log.critical(err)
            print(err, file=sys.stderr)
            exit(2)
        log.debug("GPortal> Login successful!")

        # restart server
        r = s.get(restartURL)
        if r.status_code is 200:
            if r.json()["message"] == "Your gameserver is restarting":
                log.info("GPortal> Successfully restarted server!")
                return True
        log.error("GPortal> Restart failed!")
        return False
