__author__ = "Hedius"
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
import requests
import logging as log


class GPortal:
    """connector for G-Portal.com"""

    def __init__(self, user, pw):
        """init GPortal
        :param user: G-Portal.com username/email
        :param pw: G-Portal.com password
        """
        self.user = user
        self.pw = pw

    def restart_server(self, restart_url):
        """restart a G-Portal Battlefield 4 server
        :param restart_url: restartURL of server
        :return: True on success
                  False on failure
        """
        # login
        data = {'login': self.user, 'password': self.pw}
        s = requests.session()
        # s.post("https://id2.g-portal.com/login", data=data)
        s.headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:82.0) Gecko/20100101 Firefox/82.0"
        r = s.get("https://www.g-portal.com/en/")
        r = s.get("https://www.g-portal.com/eur/auth/login?redirectAfterLogin=%2F")
        r = s.post(
            "https://id2.g-portal.com/login?redirect=https%3A%2F%2Fwww.g-portal.com%2F%3AregionPrefix%2Fauth%2Flogin%3FredirectAfterLogin%3D%252F%26defaultRegion%3DEU",
            data=data)
        if self.user not in r.text:
            err = "GPortal> Login failed!"
            log.critical(err)
            print(err, file=sys.stderr)
            return False
        log.debug("GPortal> Login successful!")

        # restart server
        r = s.get(restart_url)
        if r.status_code == 200:
            if r.json()["message"] == "Your gameserver is restarting":
                log.info("GPortal> Successfully restarted server!")
                return True
        log.error("GPortal> Restart failed! Code: {} Error: {}"
                  .format(r.status_code, r.text))
        return False
