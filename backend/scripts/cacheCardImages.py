#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

DEFAULT_DSN = os.environ.get(
    "PG_RAW_URL",
    "postgresql://admin:admin@localhost:5432/mtg_sandbox",
)

VALID_SIZES = {"small", "normal", "large"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cache MTG card images locally using Scryfall API and record results in Postgres."
    )
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--size", required=True, choices=sorted(VALID_SIZES))
    parser.add_argument(
        "--output-dir",
        default="/home/ijohnson/MtG-webapp/card-images",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--failure-log",
        default="cacheCardImages_failures.log",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=250,
        help="Print a progress update every N printings processed.",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def extract_identifier(identifiers: Any, key: str) -> str | None:
    if identifiers is None:
        return None
    if isinstance(identifiers, str):
        try:
            identifiers = json.loads(identifiers)
        except json.JSONDecodeError:
            return None
    if isinstance(identifiers, dict):
        value = identifiers.get(key)
        return value if isinstance(value, str) and value else None
    return None


def fetch_printings(conn, limit: int | None):
    sql = """
        SELECT
            id,
            uuid,
            identifiers
        FROM "mtgCore"."printings"
        WHERE identifiers IS NOT NULL
        ORDER BY id
    """
    if limit is not None:
        sql += " LIMIT %s"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if limit is not None:
            cur.execute(sql, (limit,))
        else:
            cur.execute(sql)
        return cur.fetchall()


def fetch_scryfall_card(session: requests.Session, scryfall_id: str) -> dict[str, Any]:
    url = f"https://api.scryfall.com/cards/{scryfall_id}"
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def resolve_image_targets(card_json: dict[str, Any], size: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []

    image_uris = card_json.get("image_uris") or {}
    if image_uris.get(size):
        targets.append(
            {
                "faceName": "front",
                "sourceUrl": image_uris[size],
            }
        )

    card_faces = card_json.get("card_faces") or []
    if card_faces:
        for index, face in enumerate(card_faces):
            face_image_uris = face.get("image_uris") or {}
            face_url = face_image_uris.get(size)
            if face_url:
                face_name = face.get("name") or f"face{index + 1}"
                safe_face_name = (
                    face_name.lower()
                    .replace(" ", "_")
                    .replace("/", "_")
                    .replace("\\", "_")
                )
                targets.append(
                    {
                        "faceName": safe_face_name,
                        "sourceUrl": face_url,
                    }
                )

    return targets


def local_image_path(base_dir: Path, size: str, face_name: str, scryfall_id: str) -> Path:
    return base_dir / size / face_name / scryfall_id[0] / scryfall_id[1] / f"{scryfall_id}.jpg"


def public_image_url(size: str, face_name: str, scryfall_id: str) -> str:
    return f"/card-images/{size}/{face_name}/{scryfall_id[0]}/{scryfall_id[1]}/{scryfall_id}.jpg"


def download_file(
    session: requests.Session,
    url: str,
    dest: Path,
    overwrite: bool,
    dry_run: bool,
) -> tuple[bool, int, str | None]:
    if dest.exists() and not overwrite:
        return False, dest.stat().st_size, None

    ensure_dir(dest)

    if dry_run:
        return True, 0, None

    with session.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type")
        tmp_path = dest.with_suffix(dest.suffix + ".part")
        with open(tmp_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    handle.write(chunk)
        tmp_path.replace(dest)

    return True, dest.stat().st_size, content_type


def append_failure_log(
    log_path: Path,
    *,
    printing_id: Any,
    printing_uuid: Any,
    face_name: str,
    scryfall_id: str | None,
    url: str | None,
    dest: Path | None,
    error_type: str,
    error_message: str,
) -> None:
    ensure_dir(log_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "printingId": printing_id,
                    "printingUuid": printing_uuid,
                    "faceName": face_name,
                    "scryfallId": scryfall_id,
                    "url": url,
                    "dest": str(dest) if dest else None,
                    "errorType": error_type,
                    "errorMessage": error_message,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def upsert_printing_image(
    conn,
    *,
    printing_id: int,
    face_name: str,
    image_size: str,
    local_path: str | None,
    public_url: str | None,
    source_url: str | None,
    status: str,
    content_type: str | None,
    file_bytes: int | None,
    last_error: str | None,
) -> None:
    sql = """
        INSERT INTO "mtgCore"."printingImages"
        (
            "printingId",
            "faceName",
            "imageSize",
            "localPath",
            "publicUrl",
            "sourceUrl",
            "status",
            "contentType",
            "fileBytes",
            "lastError",
            "lastAttemptedAt",
            "downloadedAt"
        )
        VALUES
        (
            %(printingId)s,
            %(faceName)s,
            %(imageSize)s,
            %(localPath)s,
            %(publicUrl)s,
            %(sourceUrl)s,
            %(status)s,
            %(contentType)s,
            %(fileBytes)s,
            %(lastError)s,
            NOW(),
            CASE WHEN %(status)s = 'cached' THEN NOW() ELSE NULL END
        )
        ON CONFLICT ("printingId", "faceName", "imageSize")
        DO UPDATE SET
            "localPath" = EXCLUDED."localPath",
            "publicUrl" = EXCLUDED."publicUrl",
            "sourceUrl" = EXCLUDED."sourceUrl",
            "status" = EXCLUDED."status",
            "contentType" = EXCLUDED."contentType",
            "fileBytes" = EXCLUDED."fileBytes",
            "lastError" = EXCLUDED."lastError",
            "lastAttemptedAt" = NOW(),
            "downloadedAt" = CASE
                WHEN EXCLUDED."status" = 'cached' THEN NOW()
                ELSE "mtgCore"."printingImages"."downloadedAt"
            END
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "printingId": printing_id,
                "faceName": face_name,
                "imageSize": image_size,
                "localPath": local_path,
                "publicUrl": public_url,
                "sourceUrl": source_url,
                "status": status,
                "contentType": content_type,
                "fileBytes": file_bytes,
                "lastError": last_error,
            },
        )
    conn.commit()


def format_elapsed(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_progress(
    *,
    processed_printings: int,
    total_printings: int,
    printings_with_scryfall: int,
    lookups_succeeded: int,
    image_targets_found: int,
    downloaded_count: int,
    skipped_count: int,
    failed_count: int,
    total_bytes: int,
    started_at: float,
) -> None:
    gb = total_bytes / (1024 ** 3)
    elapsed = format_elapsed(time.time() - started_at)
    print(
        f"[{processed_printings}/{total_printings}] "
        f"withId={printings_with_scryfall} "
        f"lookupOk={lookups_succeeded} "
        f"targets={image_targets_found} "
        f"downloaded={downloaded_count} "
        f"skipped={skipped_count} "
        f"failed={failed_count} "
        f"stored≈{gb:.2f}GB "
        f"elapsed={elapsed}"
    )


def main() -> int:
    args = parse_args()

    base_dir = Path(args.output_dir)
    failure_log_path = Path(args.failure_log)

    api_session = requests.Session()
    api_session.headers.update(
        {
            "User-Agent": "MTG-Sandbox/0.1 (local cache builder; contact: local-admin)",
            "Accept": "application/json",
        }
    )

    image_session = requests.Session()
    image_session.headers.update(
        {
            "User-Agent": "MTG-Sandbox/0.1 (local cache builder; contact: local-admin)",
            "Accept": "image/jpeg,*/*;q=0.8",
        }
    )

    try:
        conn = psycopg2.connect(args.dsn)
    except Exception as exc:
        print(f"Failed to connect to Postgres: {exc}", file=sys.stderr)
        return 1

    try:
        rows = fetch_printings(conn, args.limit)
    except Exception:
        conn.close()
        raise

    total_printings = len(rows)
    print(f"Loaded {total_printings} printings to scan for size '{args.size}'.")

    processed_printings = 0
    printings_with_scryfall = 0
    lookups_succeeded = 0
    image_targets_found = 0
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    total_bytes = 0
    started_at = time.time()

    try:
        for row in rows:
            processed_printings += 1

            printing_id = row["id"]
            printing_uuid = row["uuid"]
            identifiers = row["identifiers"]

            scryfall_id = extract_identifier(identifiers, "scryfallId")
            if not scryfall_id:
                failed_count += 1
                append_failure_log(
                    failure_log_path,
                    printing_id=printing_id,
                    printing_uuid=printing_uuid,
                    face_name="unknown",
                    scryfall_id=None,
                    url=None,
                    dest=None,
                    error_type="MissingIdentifier",
                    error_message="No scryfallId found in identifiers",
                )
                if processed_printings % args.progress_every == 0:
                    print_progress(
                        processed_printings=processed_printings,
                        total_printings=total_printings,
                        printings_with_scryfall=printings_with_scryfall,
                        lookups_succeeded=lookups_succeeded,
                        image_targets_found=image_targets_found,
                        downloaded_count=downloaded_count,
                        skipped_count=skipped_count,
                        failed_count=failed_count,
                        total_bytes=total_bytes,
                        started_at=started_at,
                    )
                continue

            printings_with_scryfall += 1

            try:
                card_json = fetch_scryfall_card(api_session, scryfall_id)
                lookups_succeeded += 1
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                message = str(exc)

                # Safe values for face_name, source_url, dest before targets loop
                safe_face_name = "front"
                safe_source_url = f"https://api.scryfall.com/cards/{scryfall_id}"
                safe_dest = None

                if status_code == 404:
                    append_failure_log(
                        failure_log_path,
                        printing_id=printing_id,
                        printing_uuid=printing_uuid,
                        face_name="front",
                        scryfall_id=scryfall_id,
                        url=f"https://api.scryfall.com/cards/{scryfall_id}",
                        dest=None,
                        error_type="ImageMissing",
                        error_message=message,
                    )
                    upsert_printing_image(
                        conn,
                        printing_id=printing_id,
                        face_name="front",
                        image_size=args.size,
                        local_path=None,
                        public_url=None,
                        source_url=f"https://api.scryfall.com/cards/{scryfall_id}",
                        status="missing",
                        content_type=None,
                        file_bytes=None,
                        last_error=message,
                    )
                else:
                    failed_count += 1
                    append_failure_log(
                        failure_log_path,
                        printing_id=printing_id,
                        printing_uuid=printing_uuid,
                        face_name="front",
                        scryfall_id=scryfall_id,
                        url=f"https://api.scryfall.com/cards/{scryfall_id}",
                        dest=None,
                        error_type="ImageDownloadError",
                        error_message=message,
                    )
                    upsert_printing_image(
                        conn,
                        printing_id=printing_id,
                        face_name="front",
                        image_size=args.size,
                        local_path=None,
                        public_url=None,
                        source_url=f"https://api.scryfall.com/cards/{scryfall_id}",
                        status="failed",
                        content_type=None,
                        file_bytes=None,
                        last_error=message,
                    )
                if processed_printings % args.progress_every == 0:
                    print_progress(
                        processed_printings=processed_printings,
                        total_printings=total_printings,
                        printings_with_scryfall=printings_with_scryfall,
                        lookups_succeeded=lookups_succeeded,
                        image_targets_found=image_targets_found,
                        downloaded_count=downloaded_count,
                        skipped_count=skipped_count,
                        failed_count=failed_count,
                        total_bytes=total_bytes,
                        started_at=started_at,
                    )
                continue

            targets = resolve_image_targets(card_json, args.size)
            if not targets:
                failed_count += 1
                message = f"No image target returned by Scryfall for size '{args.size}'"
                append_failure_log(
                    failure_log_path,
                    printing_id=printing_id,
                    printing_uuid=printing_uuid,
                    face_name="front",
                    scryfall_id=scryfall_id,
                    url=f"https://api.scryfall.com/cards/{scryfall_id}",
                    dest=None,
                    error_type="NoImageTarget",
                    error_message=message,
                )
                upsert_printing_image(
                    conn,
                    printing_id=printing_id,
                    face_name="front",
                    image_size=args.size,
                    local_path=None,
                    public_url=None,
                    source_url=None,
                    status="missing",
                    content_type=None,
                    file_bytes=None,
                    last_error=message,
                )
                if processed_printings % args.progress_every == 0:
                    print_progress(
                        processed_printings=processed_printings,
                        total_printings=total_printings,
                        printings_with_scryfall=printings_with_scryfall,
                        lookups_succeeded=lookups_succeeded,
                        image_targets_found=image_targets_found,
                        downloaded_count=downloaded_count,
                        skipped_count=skipped_count,
                        failed_count=failed_count,
                        total_bytes=total_bytes,
                        started_at=started_at,
                    )
                continue

            image_targets_found += len(targets)

            for target in targets:
                face_name = target["faceName"]
                source_url = target["sourceUrl"]
                dest = local_image_path(base_dir, args.size, face_name, scryfall_id)
                public_url = public_image_url(args.size, face_name, scryfall_id)

                try:
                    changed, file_size, content_type = download_file(
                        session=image_session,
                        url=source_url,
                        dest=dest,
                        overwrite=args.overwrite,
                        dry_run=args.dry_run,
                    )

                    if changed:
                        downloaded_count += 1
                    else:
                        skipped_count += 1

                    if file_size:
                        total_bytes += file_size

                    upsert_printing_image(
                        conn,
                        printing_id=printing_id,
                        face_name=face_name,
                        image_size=args.size,
                        local_path=str(dest),
                        public_url=public_url,
                        source_url=source_url,
                        status="cached",
                        content_type=content_type,
                        file_bytes=file_size,
                        last_error=None,
                    )

                except requests.RequestException as exc:
                    failed_count += 1
                    message = str(exc)
                    append_failure_log(
                        failure_log_path,
                        printing_id=printing_id,
                        printing_uuid=printing_uuid,
                        face_name=face_name,
                        scryfall_id=scryfall_id,
                        url=source_url,
                        dest=dest,
                        error_type="ImageDownloadError",
                        error_message=message,
                    )
                    upsert_printing_image(
                        conn,
                        printing_id=printing_id,
                        face_name=face_name,
                        image_size=args.size,
                        local_path=None,
                        public_url=None,
                        source_url=source_url,
                        status="failed",
                        content_type=None,
                        file_bytes=None,
                        last_error=message,
                    )

                except OSError as exc:
                    failed_count += 1
                    message = str(exc)
                    append_failure_log(
                        failure_log_path,
                        printing_id=printing_id,
                        printing_uuid=printing_uuid,
                        face_name=face_name,
                        scryfall_id=scryfall_id,
                        url=source_url,
                        dest=dest,
                        error_type="FilesystemError",
                        error_message=message,
                    )
                    upsert_printing_image(
                        conn,
                        printing_id=printing_id,
                        face_name=face_name,
                        image_size=args.size,
                        local_path=None,
                        public_url=None,
                        source_url=source_url,
                        status="failed",
                        content_type=None,
                        file_bytes=None,
                        last_error=message,
                    )

                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

            if processed_printings % args.progress_every == 0:
                print_progress(
                    processed_printings=processed_printings,
                    total_printings=total_printings,
                    printings_with_scryfall=printings_with_scryfall,
                    lookups_succeeded=lookups_succeeded,
                    image_targets_found=image_targets_found,
                    downloaded_count=downloaded_count,
                    skipped_count=skipped_count,
                    failed_count=failed_count,
                    total_bytes=total_bytes,
                    started_at=started_at,
                )

    finally:
        api_session.close()
        image_session.close()
        conn.close()

    print_progress(
        processed_printings=processed_printings,
        total_printings=total_printings,
        printings_with_scryfall=printings_with_scryfall,
        lookups_succeeded=lookups_succeeded,
        image_targets_found=image_targets_found,
        downloaded_count=downloaded_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        total_bytes=total_bytes,
        started_at=started_at,
    )

    gb = total_bytes / (1024 ** 3)
    print("Done.")
    print(f"Printings scanned:     {processed_printings}")
    print(f"With Scryfall ID:      {printings_with_scryfall}")
    print(f"Lookup success:        {lookups_succeeded}")
    print(f"Image targets found:   {image_targets_found}")
    print(f"Downloaded:            {downloaded_count}")
    print(f"Skipped:               {skipped_count}")
    print(f"Failed:                {failed_count}")
    print(f"Stored size:           ~{gb:.2f} GB")
    print(f"Failure log:           {failure_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())