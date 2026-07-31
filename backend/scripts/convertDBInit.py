#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from contextlib import closing
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(SCRIPT_DIR)

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


DEFAULT_PG_RAW_URL = os.environ.get(
    "PG_RAW_URL",
    "postgresql://admin:admin@127.0.0.1:5432/mtg_sandbox",
)

DEFAULT_SQLITE_PATH = os.environ.get(
    "MTGJSON_SQLITE_PATH",
    "/home/ijohnson/MtG-webapp/backend/data/AllPrintings.sqlite",
)

BATCH_SIZE = 1000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import MTGJSON SQLite into Postgres.")
    parser.add_argument("--pg-url", default=DEFAULT_PG_RAW_URL)
    parser.add_argument("--sqlite-path", default=DEFAULT_SQLITE_PATH)
    parser.add_argument(
        "--wipe-core",
        action="store_true",
        help="Delete and rebuild imported mtgCore tables before importing.",
    )
    parser.add_argument(
        "--wipe-analysis-imports",
        action="store_true",
        help="Delete imported analysis tables if you later choose to populate them here.",
    )
    return parser.parse_args()


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def to_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "t", "1", "yes"}:
            return True
        if lowered in {"false", "f", "0", "no"}:
            return False
    return None


def parse_jsonish(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def to_text_array(value: Any) -> list[str] | None:
    parsed = parse_jsonish(value)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or None
    return None


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    return " ".join(name.lower().split())


def connect_sqlite(sqlite_path: str) -> sqlite3.Connection:
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite file not found at: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def connect_pg(pg_url: str):
    return psycopg2.connect(pg_url)


def sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def fetch_rows(conn: sqlite3.Connection, sql: str, params: tuple = ()):
    cur = conn.execute(sql, params)
    while True:
        rows = cur.fetchmany(BATCH_SIZE)
        if not rows:
            break
        yield rows


def create_schemas(pg_conn) -> None:
    sql = """
    CREATE SCHEMA IF NOT EXISTS "mtgCore";
    CREATE SCHEMA IF NOT EXISTS "mtgDecks";
    CREATE SCHEMA IF NOT EXISTS "mtgGames";
    CREATE SCHEMA IF NOT EXISTS "mtgAnalysis";
    """
    with pg_conn.cursor() as cur:
        cur.execute(sql)
    pg_conn.commit()


def wipe_imported_core_tables(pg_conn) -> None:
    table_names = [
        "productContents",
        "products",
        "printingImages",
        "printings",
        "cardFaces",
        "cards",
        "sets",
    ]

    existing_tables = []
    with pg_conn.cursor() as cur:
        for table_name in table_names:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'mtgCore'
                      AND table_name = %s
                )
                """,
                (table_name,),
            )
            if cur.fetchone()[0]:
                existing_tables.append(f'"mtgCore"."{table_name}"')

        if existing_tables:
            sql = (
                "TRUNCATE TABLE "
                + ", ".join(existing_tables)
                + " RESTART IDENTITY CASCADE;"
            )
            cur.execute(sql)

    pg_conn.commit()

def wipe_analysis_import_tables(pg_conn) -> None:
    sql = """
    TRUNCATE TABLE
      "mtgAnalysis"."cardMatchupTags",
      "mtgAnalysis"."cardRoleTags"
    RESTART IDENTITY CASCADE;
    """
    with pg_conn.cursor() as cur:
        cur.execute(sql)
    pg_conn.commit()


def load_card_identifiers(sqlite_conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    if not table_exists(sqlite_conn, "cardIdentifiers"):
        return {}

    rows = sqlite_conn.execute("SELECT * FROM cardIdentifiers").fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_dict = dict(row)
        uuid = row_dict.get("uuid")
        if uuid:
            result[uuid] = row_dict
    return result


def load_set_lookup(sqlite_conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    if not table_exists(sqlite_conn, "sets"):
        return lookup

    rows = sqlite_conn.execute("SELECT * FROM sets").fetchall()
    for row in rows:
        row_dict = dict(row)
        code = row_dict.get("code")
        if code:
            lookup[code] = row_dict
    return lookup


def load_products(sqlite_conn: sqlite3.Connection) -> list[dict[str, Any]]:
    if not table_exists(sqlite_conn, "sealedProducts"):
        return []
    return [dict(row) for row in sqlite_conn.execute("SELECT * FROM sealedProducts").fetchall()]


def load_product_contents(sqlite_conn: sqlite3.Connection) -> list[dict[str, Any]]:
    if not table_exists(sqlite_conn, "sealedProductContents"):
        return []
    return [dict(row) for row in sqlite_conn.execute("SELECT * FROM sealedProductContents").fetchall()]


def import_sets(pg_conn, set_lookup: dict[str, dict[str, Any]]) -> dict[str, int]:
    if not set_lookup:
        return {}

    rows = []
    for code, raw in set_lookup.items():
        rows.append(
            (
                code,
                raw.get("name"),
                raw.get("releaseDate"),
                raw.get("block"),
                raw.get("type"),
                to_bool(raw.get("isOnlineOnly")) or False,
                to_int(raw.get("totalSetSize") or raw.get("baseSetSize")),
                to_int(raw.get("tokenCount")),
                Json(raw),
            )
        )

    sql = """
    INSERT INTO "mtgCore"."sets"
    ("code", "name", "releaseDate", "block", "setType", "isDigital", "totalCards", "tokenCount", "rawJson")
    VALUES %s
    """

    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            rows,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            page_size=BATCH_SIZE,
        )
    pg_conn.commit()

    code_to_id: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        cur.execute('SELECT id, code FROM "mtgCore"."sets"')
        for set_id, code in cur.fetchall():
            code_to_id[code] = set_id

    return code_to_id


def import_cards_and_faces(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    card_identifiers: dict[str, dict[str, Any]],
    set_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[str, int], dict[str, dict[str, Any]]]:
    card_rows = []
    face_rows = []
    uuid_to_card_payload: dict[str, dict[str, Any]] = {}

    sql = "SELECT * FROM cards"
    for batch in fetch_rows(sqlite_conn, sql):
        for row in batch:
            raw = dict(row)
            uuid = raw.get("uuid")
            name = raw.get("name")
            if not uuid or not name:
                continue

            identifiers = card_identifiers.get(uuid, {})
            set_code = raw.get("setCode")
            set_name = set_lookup.get(set_code, {}).get("name") if set_code else None

            card_payload = {
                "uuid": uuid,
                "oracleId": identifiers.get("scryfallOracleId"),
                "name": name,
                "normalizedName": normalize_name(name),
                "faceName": raw.get("faceName"),
                "manaCost": raw.get("manaCost"),
                "manaValue": to_decimal(raw.get("manaValue")),
                "colors": to_text_array(raw.get("colors")),
                "colorIdentity": to_text_array(raw.get("colorIdentity")),
                "typeLine": raw.get("type"),
                "oracleText": raw.get("text"),
                "power": raw.get("power"),
                "toughness": raw.get("toughness"),
                "loyalty": raw.get("loyalty"),
                "defense": raw.get("defense"),
                "layout": raw.get("layout"),
                "side": raw.get("side"),
                "isToken": to_bool(raw.get("isToken")) or False,
                "isReserved": to_bool(raw.get("isReserved")),
                "isReprint": to_bool(raw.get("isReprint")),
                "edhrecRank": to_int(raw.get("edhrecRank")),
                "defaultSetCode": set_code,
                "defaultSetName": set_name,
                "rarity": raw.get("rarity"),
                "availability": to_text_array(raw.get("availability")),
                "identifiers": identifiers,
                "legalities": parse_jsonish(raw.get("legalities"), default={}) or {},
                "rawJson": raw,
            }
            uuid_to_card_payload[uuid] = card_payload

            card_rows.append(
                (
                    card_payload["uuid"],
                    card_payload["oracleId"],
                    card_payload["name"],
                    card_payload["normalizedName"],
                    card_payload["faceName"],
                    card_payload["manaCost"],
                    card_payload["manaValue"],
                    card_payload["colors"],
                    card_payload["colorIdentity"],
                    card_payload["typeLine"],
                    card_payload["oracleText"],
                    card_payload["power"],
                    card_payload["toughness"],
                    card_payload["loyalty"],
                    card_payload["defense"],
                    card_payload["layout"],
                    card_payload["side"],
                    card_payload["isToken"],
                    card_payload["isReserved"],
                    card_payload["isReprint"],
                    card_payload["edhrecRank"],
                    card_payload["defaultSetCode"],
                    card_payload["defaultSetName"],
                    card_payload["rarity"],
                    card_payload["availability"],
                    Json(card_payload["identifiers"]),
                    Json(card_payload["legalities"]),
                    Json(card_payload["rawJson"]),
                )
            )

            other_face_ids = parse_jsonish(raw.get("otherFaceIds"), default=[]) or []
            face_order = 0
            if raw.get("faceName") or raw.get("side"):
                face_rows.append((uuid, face_order, raw))

    insert_cards_sql = """
    INSERT INTO "mtgCore"."cards"
    (
    "uuid","oracleId","name","normalizedName","faceName","manaCost","manaValue","colors",
    "colorIdentity","typeLine","oracleText","power","toughness","loyalty","defense",
    "layout","side","isToken","isReserved","isReprint","edhrecRank","defaultSetCode",
    "defaultSetName","rarity","availability","identifiers","legalities","rawJson"
    )
    VALUES %s
    """

    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            insert_cards_sql,
            card_rows,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            page_size=BATCH_SIZE,
        )
    pg_conn.commit()

    uuid_to_card_id: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        cur.execute('SELECT id, uuid FROM "mtgCore"."cards"')
        for card_id, uuid in cur.fetchall():
            uuid_to_card_id[uuid] = card_id

    # Faces
    face_insert_rows = []
    for card_uuid, face_order, raw in face_rows:
        card_id = uuid_to_card_id.get(card_uuid)
        if not card_id:
            continue
        identifiers = card_identifiers.get(card_uuid, {})
        face_insert_rows.append(
            (
                card_id,
                face_order,
                raw.get("faceName") or raw.get("name"),
                raw.get("manaCost"),
                raw.get("type"),
                raw.get("text"),
                raw.get("power"),
                raw.get("toughness"),
                raw.get("loyalty"),
                raw.get("defense"),
                to_text_array(raw.get("colors")),
                Json(identifiers),
                Json(raw),
            )
        )

    if face_insert_rows:
        insert_faces_sql = """
        INSERT INTO "mtgCore"."cardFaces"
        (
          "cardId","faceOrder","name","manaCost","typeLine","oracleText",
          "power","toughness","loyalty","defense","colors","identifiers","rawJson"
        )
        VALUES %s
        """
        with pg_conn.cursor() as cur:
            execute_values(
                cur,
                insert_faces_sql,
                face_insert_rows,
                template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                page_size=BATCH_SIZE,
            )
        pg_conn.commit()

    return uuid_to_card_id, uuid_to_card_payload


def import_printings(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    uuid_to_card_id: dict[str, int],
    card_identifiers: dict[str, dict[str, Any]],
    code_to_set_id: dict[str, int],
) -> dict[str, int]:
    rows = []

    for batch in fetch_rows(sqlite_conn, "SELECT * FROM cards"):
        for row in batch:
            raw = dict(row)
            uuid = raw.get("uuid")
            if not uuid:
                continue

            card_id = uuid_to_card_id.get(uuid)
            if not card_id:
                continue

            set_code = raw.get("setCode")
            set_id = code_to_set_id.get(set_code) if set_code else None
            identifiers = card_identifiers.get(uuid, {})

            rows.append(
                (
                    card_id,
                    set_id,
                    uuid,
                    raw.get("number"),
                    raw.get("rarity"),
                    raw.get("artist"),
                    raw.get("flavorText"),
                    raw.get("frameVersion"),
                    raw.get("borderColor"),
                    raw.get("language") or "English",
                    to_bool(raw.get("isPromo")) or False,
                    to_bool(raw.get("isFullArt")) or False,
                    to_text_array(raw.get("availability")),
                    Json(identifiers),
                    Json(raw),
                )
            )

    sql = """
    INSERT INTO "mtgCore"."printings"
    (
    "cardId","setId","uuid","collectorNumber","rarity","artist","flavorText",
    "frameVersion","borderColor","language","isPromo","isFullArt","availability",
    "identifiers","rawJson"
    )
    VALUES %s
    """

    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            rows,
            template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            page_size=BATCH_SIZE,
        )
    pg_conn.commit()

    uuid_to_printing_id: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        cur.execute('SELECT id, uuid FROM "mtgCore"."printings"')
        for printing_id, uuid in cur.fetchall():
            uuid_to_printing_id[uuid] = printing_id

    return uuid_to_printing_id


def import_products(
    pg_conn,
    products: list[dict[str, Any]],
    code_to_set_id: dict[str, int],
) -> dict[str, int]:
    if not products:
        return {}

    rows = []
    for raw in products:
        product_code = raw.get("uuid") or raw.get("productCode") or raw.get("code")
        if not product_code:
            continue
        set_code = raw.get("setCode")
        set_id = code_to_set_id.get(set_code) if set_code else None
        rows.append(
            (
                product_code,
                raw.get("name"),
                raw.get("productType") or raw.get("type"),
                set_id,
                raw.get("releaseDate"),
                Json(raw),
            )
        )

    sql = """
    INSERT INTO "mtgCore"."products"
    ("productCode","name","productType","setId","releaseDate","rawJson")
    VALUES %s
    """

    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            rows,
            template="(%s,%s,%s,%s,%s,%s)",
            page_size=BATCH_SIZE,
        )
    pg_conn.commit()

    product_code_to_id: dict[str, int] = {}
    with pg_conn.cursor() as cur:
        cur.execute('SELECT id, "productCode" FROM "mtgCore"."products"')
        for product_id, product_code in cur.fetchall():
            product_code_to_id[product_code] = product_id

    return product_code_to_id


def import_product_contents(
    pg_conn,
    product_contents: list[dict[str, Any]],
    product_code_to_id: dict[str, int],
    uuid_to_card_id: dict[str, int],
):
    if not product_contents:
        return

    rows = []
    for raw in product_contents:
        product_code = raw.get("sealedProductUuid") or raw.get("productCode") or raw.get("uuid")
        card_uuid = raw.get("cardUuid") or raw.get("uuid")
        
        if not product_code or not card_uuid:
            continue
            
        product_id = product_code_to_id.get(product_code)
        card_id = uuid_to_card_id.get(card_uuid)

        if not product_id or not card_id:
            continue

        rows.append(
            (
                product_id,
                card_id,
                to_int(raw.get("quantity")) or 1,
                to_bool(raw.get("isCommander")) or False,
                raw.get("boardSection") or "main",
            )
        )

    if not rows:
        return

    sql = """
    INSERT INTO "mtgCore"."productContents"
    ("productId","cardId","quantity","isCommander","boardSection")
    VALUES %s
    ON CONFLICT DO NOTHING
    """

    with pg_conn.cursor() as cur:
        execute_values(
            cur,
            sql,
            rows,
            template="(%s,%s,%s,%s,%s)",
            page_size=BATCH_SIZE,
        )
    pg_conn.commit()


def print_counts(pg_conn) -> None:
    checks = [
        ('sets', 'SELECT COUNT(*) FROM "mtgCore"."sets"'),
        ('cards', 'SELECT COUNT(*) FROM "mtgCore"."cards"'),
        ('cardFaces', 'SELECT COUNT(*) FROM "mtgCore"."cardFaces"'),
        ('printings', 'SELECT COUNT(*) FROM "mtgCore"."printings"'),
        ('products', 'SELECT COUNT(*) FROM "mtgCore"."products"'),
        ('productContents', 'SELECT COUNT(*) FROM "mtgCore"."productContents"'),
    ]
    with pg_conn.cursor() as cur:
        for label, sql in checks:
            cur.execute(sql)
            count = cur.fetchone()[0]
            print(f"{label}: {count}")


def main() -> None:
    args = parse_args()

    with closing(connect_sqlite(args.sqlite_path)) as sqlite_conn, closing(connect_pg(args.pg_url)) as pg_conn:
        print("Connected to SQLite and Postgres.")
        create_schemas(pg_conn)

        if args.wipe_core:
            print("Wiping imported mtgCore tables...")
            wipe_imported_core_tables(pg_conn)

        if args.wipe_analysis_imports:
            print("Wiping imported mtgAnalysis tables...")
            wipe_analysis_import_tables(pg_conn)

        print("Loading identifier and set lookup data from SQLite...")
        card_identifiers = load_card_identifiers(sqlite_conn)
        set_lookup = load_set_lookup(sqlite_conn)
        products = load_products(sqlite_conn)
        product_contents = load_product_contents(sqlite_conn)

        print(f"Loaded {len(card_identifiers)} cardIdentifiers rows.")
        print(f"Loaded {len(set_lookup)} sets rows.")
        print(f"Loaded {len(products)} product rows.")
        print(f"Loaded {len(product_contents)} product content rows.")

        print("Importing sets...")
        code_to_set_id = import_sets(pg_conn, set_lookup)
        print(f"Imported {len(code_to_set_id)} sets.")

        print("Importing cards and faces...")
        uuid_to_card_id, _ = import_cards_and_faces(
            sqlite_conn,
            pg_conn,
            card_identifiers,
            set_lookup,
        )
        print(f"Imported {len(uuid_to_card_id)} cards.")

        print("Importing printings...")
        uuid_to_printing_id = import_printings(
            sqlite_conn,
            pg_conn,
            uuid_to_card_id,
            card_identifiers,
            code_to_set_id,
        )
        print(f"Imported {len(uuid_to_printing_id)} printings.")

        print("Importing products...")
        product_code_to_id = import_products(pg_conn, products, code_to_set_id)
        print(f"Imported {len(product_code_to_id)} products.")

        print("Importing product contents...")
        import_product_contents(
            pg_conn,
            product_contents,
            product_code_to_id,
            uuid_to_card_id,
        )

        print("Final counts:")
        print_counts(pg_conn)

        print("Import complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
