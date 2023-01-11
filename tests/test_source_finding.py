#!/usr/bin/env python3

import os
import configparser
import unittest
from source_finding import update_sofiax_config


class TestUpdateSoFiAXConfig(unittest.TestCase):
    def setUp(self):
        """Verify SoFiAX config file exists. Set run_name parameter to default."""
        self.sofiax_config = f"{os.path.dirname(__file__)}/sofiax.ini"
        if os.path.isfile(self.sofiax_config):
            config = configparser.RawConfigParser()
            config.optionxform = str
            config.read(self.sofiax_config)
            config.set("SoFiAX", "run_name", "default")
            with open(self.sofiax_config, "w") as f:
                config.write(f)
        else:
            with open(self.sofiax_config, "w") as f:
                f.write("[SoFiAX]\n")
                f.write("db_hostname = \n")
                f.write("db_name = \n")
                f.write("db_username = \n")
                f.write("db_password = \n")
                f.write("sofia_execute = 0\n")
                f.write("sofia_path = /usr/local/bin/sofia\n")
                f.write("sofia_processes = 24\n")
                f.write("run_name = default\n")
                f.write("spatial_extent = 10,10\n")
                f.write("spectral_extent = 10,10\n")
                f.write("flux = 15\n")
                f.write("uncertainty_sigma = 5\n")
                f.write(
                    "output = /mnt/shared/home/ashen/pipeline_components/tests/sofiax.ini\n"
                )

        self.db_env = f"{os.path.dirname(__file__)}/db.env"
        if not os.path.isfile(self.db_env):
            with open(self.db_env, "w") as f:
                f.write("DATABASE_HOST = localhost\n")
                f.write("DATABASE_NAME = name\n")
                f.write("DATABASE_USER = admin\n")
                f.write("DATABASE_PASSWORD = password\n")

    def tearDown(self):
        if os.path.isfile(self.sofiax_config):
            os.remove(self.sofiax_config)
        if os.path.isfile(self.db_env):
            os.remove(self.db_env)

    def test_update_run_name(self):
        """Update the run name from the default value. No database credentials set
        1. Verify that the value initially is "default"
        2. Update to "run_name"
        3. Verify new value is "run_name"

        """
        run_name = "run_name"

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(self.sofiax_config)
        self.assertEqual(config.get("SoFiAX", "run_name"), "default")

        update_sofiax_config.main(
            [
                "--config",
                self.sofiax_config,
                "--output",
                self.sofiax_config,
                "--run_name",
                run_name,
            ]
        )

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(self.sofiax_config)
        self.assertEqual(config.get("SoFiAX", "run_name"), "run_name")

    def test_update_database_credentials(self):
        """Set the database credentials with the database.env file"""
        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(self.sofiax_config)
        self.assertEqual(config.get("SoFiAX", "db_hostname"), "")

        update_sofiax_config.main(
            [
                "--config",
                self.sofiax_config,
                "--output",
                self.sofiax_config,
                "--database",
                self.db_env,
            ]
        )

        config = configparser.RawConfigParser()
        config.optionxform = str
        config.read(self.sofiax_config)
        self.assertEqual(config.get("SoFiAX", "db_hostname"), "localhost")


if __name__ == "__main__":
    unittest.main()
