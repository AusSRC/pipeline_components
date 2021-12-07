#!/usr/bin/env python3

import os
import sys
import io
import configparser
import unittest
from source_finding import database_credentials


SOFIA_PARAMS = "sofia.par"
SOFIAX_CONFIG = "config.ini"


class SourceFindingTests(unittest.TestCase):
    """Tests of CASDA download components.

    """
    def setUp(self):
        """Set credentials as environment variables for
        local and remote testing.

        """
        creds = "credentials.ini"
        if os.path.isfile(creds):
            config = configparser.ConfigParser()
            config.read(creds)
            login = config["login"]
            os.environ["CASDA_USERNAME"] = login['username']
            os.environ["CASDA_PASSWORD"] = login['password']

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.add_section('SoFiAX')
        config.set('SoFiAX', 'db_hostname', 'db_hostname')
        config.set('SoFiAX', 'db_name', 'db_name')
        config.set('SoFiAX', 'db_username', 'db_username')
        config.set('SoFiAX', 'db_password', 'db_password')
        with open(SOFIAX_CONFIG, 'w') as f:
            config.write(f)

    def tearDown(self):
        if os.path.isfile(SOFIA_PARAMS):
            os.remove(SOFIA_PARAMS)
        if os.path.isfile(SOFIAX_CONFIG):
            os.remove(SOFIAX_CONFIG)

    def test_sofiax_config_write(self):
        """Assert that database credentials are updated with the
        database_credentials.py file.

        """
        host = "hostname"
        name = "user"
        user = "admin"
        pwd = "admin"

        database_credentials.main([
            "--config", SOFIAX_CONFIG,
            "--host", host,
            "--name", name,
            "--username", user,
            "--password", pwd
        ])

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(SOFIAX_CONFIG)

        self.assertEqual(host, config.get('SoFiAX', 'db_hostname'))
        self.assertEqual(name, config.get('SoFiAX', 'db_name'))
        self.assertEqual(user, config.get('SoFiAX', 'db_username'))
        self.assertEqual(pwd, config.get('SoFiAX', 'db_password'))


if __name__ == "__main__":
    unittest.main()
