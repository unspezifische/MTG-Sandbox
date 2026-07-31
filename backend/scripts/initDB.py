import os
import subprocess
import time


postgresUrl = os.environ.get(
    "PG_RAW_URL",
    "postgresql://admin:admin@localhost:5432/mtg_sandbox",
)

createSchemasSql = """
CREATE SCHEMA IF NOT EXISTS "mtgCore";
CREATE SCHEMA IF NOT EXISTS "mtgDecks";
CREATE SCHEMA IF NOT EXISTS "mtgGames";
CREATE SCHEMA IF NOT EXISTS "mtgAnalysis";
"""


def waitForDb(maxAttempts: int = 60, delaySeconds: int = 2) -> None:
    for attempt in range(maxAttempts):
        try:
            subprocess.run(
                ["psql", postgresUrl, "-c", "SELECT 1;"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Database is ready.")
            return
        except subprocess.CalledProcessError:
            if attempt < maxAttempts - 1:
                time.sleep(delaySeconds)
            else:
                raise RuntimeError("Database did not become ready in time.")


def createSchemas() -> None:
    subprocess.run(
        ["psql", postgresUrl, "-v", "ON_ERROR_STOP=1", "-c", createSchemasSql],
        check=True,
    )
    print("Schemas created or already present.")


if __name__ == "__main__":
    waitForDb()
    createSchemas()
    print("Database bootstrap complete.")