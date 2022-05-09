#!/usr/bin/env python3

import os
import configparser
import unittest
from source_finding import update_sofiax_config


class TestUpdateSoFiAXConfig(unittest.TestCase):
    def setUp(self):
        """Verify SoFiAX config file exists. Set run_name parameter to default.

        """
        self.sofiax_config = f"{os.path.dirname(__file__)}/sofiax.ini"
        if os.path.isfile(self.sofiax_config):
            config = configparser.RawConfigParser()
            config.optionxform = str
            config.read(self.sofiax_config)
            config.set('SoFiAX', "run_name", "default")
            with open(self.sofiax_config, 'w') as f:
                config.write(f)
        else:
            raise Exception("Template SoFiAX configuration file could not be found")

    def test_update_run_name(self):
        """Update the run name from the default value.
        1. Verify that the value initially is "default"
        2. Update to "run_name"
        3. Verify new value is "run_name"

        """
        run_name = "run_name"

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(self.sofiax_config)
        self.assertEqual(config.get('SoFiAX', 'run_name'), 'default')

        update_sofiax_config.main([
            "--config", self.sofiax_config,
            "--run_name", run_name,
        ])

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(self.sofiax_config)
        self.assertEqual(config.get('SoFiAX', 'run_name'), 'run_name')


if __name__ == "__main__":
    unittest.main()
