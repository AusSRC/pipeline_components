#!/usr/bin/env python3

import asyncio
import os
import unittest
from unittest import mock

from aussrc_pipeline_components.database import create_run


class TestCreateRun(unittest.TestCase):
    def setUp(self):
        self.db_env = f"{os.path.dirname(__file__)}/db.env"
        with open(self.db_env, "w") as f:
            f.write("DATABASE_HOST = localhost\n")
            f.write("DATABASE_NAME = name\n")
            f.write("DATABASE_USER = admin\n")
            f.write("DATABASE_PASSWORD = password\n")
            f.write("DATABASE_SCHEMA = survey\n")

    def tearDown(self):
        if os.path.isfile(self.db_env):
            os.remove(self.db_env)

    def test_create_run(self):
        """Run is inserted with the run name and default sanity thresholds
        in the schema from the database.env file. Returns the run id."""
        conn = mock.MagicMock()
        conn.fetchrow = mock.AsyncMock(return_value={"id": 7})
        conn.close = mock.AsyncMock()
        conn.transaction.return_value.__aenter__ = mock.AsyncMock()
        conn.transaction.return_value.__aexit__ = mock.AsyncMock(return_value=False)

        # database.env is loaded into the environment, restore it after the test
        with (
            mock.patch.dict(os.environ),
            mock.patch.object(
                create_run.asyncpg, "connect", mock.AsyncMock(return_value=conn)
            ) as connect,
        ):
            run_id = asyncio.run(create_run.main(["-r", "run_name", "-e", self.db_env]))

        self.assertEqual(run_id, 7)
        self.assertEqual(connect.call_args.kwargs["host"], "localhost")
        self.assertEqual(
            connect.call_args.kwargs["server_settings"], {"search_path": "survey"}
        )
        conn.fetchrow.assert_awaited_once_with(create_run.QUERY, "run_name", "{}")
        conn.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
