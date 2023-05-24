__author__ = "Hedius"
__license__ = "GPLv3"

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

from threading import Lock
from typing import Optional

from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By


class GPortal:
    """
    connector for G-Portal.com, requires selenium
    The restarting process is a mutex.
    """

    def __init__(self, user, pw, remote_selenium):
        """
        Connector for g-portal.
        use
        :param user: G-Portal.com username/email
        :param pw: G-Portal.com password (2FA HAS TO BE DISABLED!)
        :param remote_selenium: http://IP:PORT of the remote selenium server (CHROME ONLY!)
        """
        self._user = user
        self._pw = pw
        self._remote_selenium = remote_selenium

        self._lock = Lock()

        self._driver: Optional[webdriver.Remote] = None

    def _init_driver(self) -> webdriver.Remote:
        """
        Open a connection to a remote chrome selenium instance.
        Sets the driver to self._driver
        :return: driver
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(
            '/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36')
        driver = webdriver.Remote(
            command_executor=f'{self._remote_selenium}/wd/hub',
            options=chrome_options
        )
        driver.implicitly_wait(10)
        self._driver = driver  # Redundant
        return driver

    def close_driver(self):
        if not self._driver:
            return
        self._driver.quit()
        self._driver = None

    def _check_login(self):
        """
        Opens the my server page of g-portal and performs a login if needed.
        """
        self._driver.get('https://www.g-portal.com/eur/gamecloud')
        if 'auth.g-portal.com' not in self._driver.current_url:
            # Seems like we are authenticated
            return

        # Perform login
        logger.info('Authenticating')
        # Navigate Authentication
        self._driver.find_element(By.ID, 'username').send_keys(self._user)
        self._driver.find_element(By.ID, 'password').send_keys(self._pw)
        self._driver.find_element(By.ID, 'kc-login').click()

        # Click cookie button if needed
        try:
            self._driver.find_element(
                By.CSS_SELECTOR,
                'div.cf1lHZ:nth-child(1) > button:nth-child(1)'
            ).click()
            logger.info('Clicked the cookie button')
        except Exception:
            pass

    def restart_server(self, restart_url):
        """
        Restart a G-Portal Battlefield 4 server
        :param restart_url: restart URL of server
        """
        # Mutex to prevent several threads from doing the same stuff at the same time.
        # selenium would support multiple sessions but we only use one
        with self._lock:
            if not self._driver:
                self._init_driver()
            self._check_login()
            self._driver.get(restart_url)

            if not self._driver.current_url.endswith('restartService'):
                # we are on a different page!
                raise RuntimeError('LOGIN FAILED!!! = RESTART FAILED!')


if __name__ == '__main__':
    gp = GPortal(user='A', pw='x', remote_selenium='http://127.0.0.1:4444')
    gp.restart_server('https://www.g-portal.com/eur/server/bf4/4973584/restartService')
    print(gp)