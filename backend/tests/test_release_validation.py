"""Local deployment regression checks; these do not replace PostgreSQL execution."""
import ast
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReleaseValidationTests(unittest.TestCase):
    def test_core_importer_discovers_token_rows_and_refreshes_by_uuid(self):
        from scripts import convertDBInit as importer

        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE cards (uuid TEXT)")
        connection.execute("CREATE TABLE tokens (uuid TEXT, name TEXT)")
        connection.execute("CREATE TABLE tokenIdentifiers (uuid TEXT, scryfallOracleId TEXT)")
        connection.execute("INSERT INTO tokens VALUES ('token-a', 'Goblin')")
        connection.execute("INSERT INTO tokenIdentifiers VALUES ('token-a', 'oracle-a')")

        self.assertEqual(importer.source_tables(connection), [("cards", False), ("tokens", True)])
        self.assertEqual(
            importer.load_identifiers(connection, "tokenIdentifiers")["token-a"]["scryfallOracleId"],
            "oracle-a",
        )
        source = (ROOT / "backend/scripts/convertDBInit.py").read_text()
        self.assertIn('ON CONFLICT ("uuid") DO UPDATE SET', source)
        connection.close()

    def test_initial_migration_defers_foreign_keys_until_tables_exist(self):
        tree = ast.parse((ROOT / "backend/migrations/versions/14dab1a395db_upgrades.py").read_text())
        upgrade = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade")
        tables = set(); foreign_keys = 0
        for statement in upgrade.body:
            if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
                continue
            call = statement.value
            if not isinstance(call.func, ast.Attribute):
                continue
            if call.func.attr == "create_table":
                schema = next(ast.literal_eval(k.value) for k in call.keywords if k.arg == "schema")
                tables.add((schema, ast.literal_eval(call.args[0])))
                self.assertFalse(any(isinstance(a, ast.Call) and isinstance(a.func, ast.Attribute)
                    and a.func.attr == "ForeignKeyConstraint" for a in call.args))
            elif call.func.attr == "create_foreign_key":
                schema = next(ast.literal_eval(k.value) for k in call.keywords if k.arg == "referent_schema")
                self.assertIn((schema, ast.literal_eval(call.args[2])), tables)
                foreign_keys += 1
        self.assertEqual(foreign_keys, 48)

    def test_docker_startup_refuses_unconfigured_or_container_local_auth(self):
        for url in ("", "http://127.0.0.1", "http://localhost:5000", "http://[::1]"):
            env = dict(os.environ, KACHHAPA_AUTH_URL=url, DATABASE_URL="sqlite://",
                       PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
            result = subprocess.run(["/bin/sh", str(ROOT / "backend/docker-entrypoint.sh"), "true"],
                env=env, text=True, capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("external Kachhapa service", result.stderr)
