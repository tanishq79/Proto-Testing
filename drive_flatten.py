#!/usr/bin/env python3
"""Copy a Google Drive folder, extracting every ZIP into its own folder."""

from __future__ import annotations

import argparse
import io
import mimetypes
import re
import sys
import zipfile
from pathlib import PurePosixPath

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_MIME = "application/vnd.google-apps.folder"


def folder_id(value: str) -> str:
    """Accept either a Drive folder ID or a normal Drive URL."""
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", value)
    return match.group(1) if match else value.strip()


def get_service(credentials_file: str, token_file: str):
    credentials = None
    try:
        credentials = Credentials.from_authorized_user_file(token_file, SCOPES)
    except FileNotFoundError:
        pass
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        credentials = flow.run_local_server(port=0)
    with open(token_file, "w", encoding="utf-8") as token:
        token.write(credentials.to_json())
    return build("drive", "v3", credentials=credentials)


def children(service, parent_id: str) -> list[dict]:
    """Return all direct children of a Drive folder."""
    result: list[dict] = []
    token = None
    while True:
        response = service.files().list(
            q=f"'{parent_id}' in parents and trashed = false",
            fields="nextPageToken, files(id,name,mimeType)",
            pageToken=token,
            pageSize=1000,
        ).execute()
        result.extend(response.get("files", []))
        token = response.get("nextPageToken")
        if not token:
            return result


def safe_name(name: str, used: set[str]) -> str:
    """Avoid collisions among children of one destination folder."""
    cleaned = PurePosixPath(name.replace("\\", "/")).name or "unnamed-file"
    candidate = cleaned
    stem, suffix = PurePosixPath(cleaned).stem, PurePosixPath(cleaned).suffix
    number = 2
    while candidate.casefold() in used:
        candidate = f"{stem} ({number}){suffix}"
        number += 1
    used.add(candidate.casefold())
    return candidate


def names_in(service, parent_id: str) -> set[str]:
    return {item["name"].casefold() for item in children(service, parent_id)}


def create_folder(service, parent_id: str, name: str, used_names: set[str]) -> tuple[str, str]:
    name = safe_name(name, used_names)
    response = service.files().create(
        body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}, fields="id"
    ).execute()
    return response["id"], name


def upload_bytes(service, parent_id: str, name: str, content: bytes, used_names: set[str]) -> str:
    name = safe_name(name, used_names)
    mime_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
    service.files().create(
        body={"name": name, "parents": [parent_id]}, media_body=media, fields="id"
    ).execute()
    return name


def copy_drive_folder(service, source_id: str, destination_id: str) -> int:
    """Copy a Drive folder recursively, retaining its folder layout."""
    count = 0
    used_names = names_in(service, destination_id)
    for item in children(service, source_id):
        if item["mimeType"] == FOLDER_MIME:
            child_id, child_name = create_folder(service, destination_id, item["name"], used_names)
            print(f"  Folder: {child_name}")
            count += copy_drive_folder(service, item["id"], child_id)
        else:
            raw = service.files().get_media(fileId=item["id"]).execute()
            uploaded = upload_bytes(service, destination_id, item["name"], raw, used_names)
            print(f"  Uploaded: {uploaded}")
            count += 1
    return count


def zip_part_path(filename: str) -> list[str] | None:
    """Return a safe relative path for an archive member, or skip unsafe entries."""
    parts = [part for part in PurePosixPath(filename.replace("\\", "/")).parts if part not in ("", ".")]
    if not parts or ".." in parts or parts[0] == "/":
        return None
    return parts


def extract_zip(service, content: bytes, destination_id: str) -> int:
    """Extract a ZIP while preserving its inner folders."""
    uploaded = 0
    folder_cache: dict[tuple[str, ...], tuple[str, set[str]]] = {(): (destination_id, names_in(service, destination_id))}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for member in archive.infolist():
            path = zip_part_path(member.filename)
            if not path:
                continue
            folder_parts = path if member.is_dir() else path[:-1]
            for size in range(1, len(folder_parts) + 1):
                key = tuple(folder_parts[:size])
                if key not in folder_cache:
                    parent_id, parent_names = folder_cache[key[:-1]]
                    new_id, _ = create_folder(service, parent_id, key[-1], parent_names)
                    folder_cache[key] = (new_id, set())
            if not member.is_dir():
                parent_id, parent_names = folder_cache[tuple(folder_parts)]
                upload_bytes(service, parent_id, path[-1], archive.read(member), parent_names)
                uploaded += 1
    return uploaded


def is_zip(item: dict) -> bool:
    return item["name"].lower().endswith(".zip") or item["mimeType"] in {
        "application/zip", "application/x-zip-compressed"
    }


def run(args: argparse.Namespace) -> None:
    service = get_service(args.credentials, args.token)
    source, destination = folder_id(args.source), folder_id(args.destination)
    destination_names = names_in(service, destination)
    loose_files_id = None
    loose_names: set[str] | None = None
    uploaded = 0

    for item in children(service, source):
        if item["mimeType"] == FOLDER_MIME:
            new_id, new_name = create_folder(service, destination, item["name"], destination_names)
            print(f"Copying folder: {new_name}")
            uploaded += copy_drive_folder(service, item["id"], new_id)
        elif is_zip(item):
            zip_folder_name = PurePosixPath(item["name"]).stem or item["name"]
            new_id, new_name = create_folder(service, destination, zip_folder_name, destination_names)
            print(f"Extracting ZIP into folder: {new_name}")
            raw = service.files().get_media(fileId=item["id"]).execute()
            try:
                uploaded += extract_zip(service, raw, new_id)
            except zipfile.BadZipFile:
                print(f"  Warning: {item['name']} is not a valid ZIP; skipped.", file=sys.stderr)
        else:
            if loose_files_id is None:
                loose_files_id, _ = create_folder(service, destination, "Loose files", destination_names)
                loose_names = names_in(service, loose_files_id)
            name = upload_bytes(
                service, loose_files_id, item["name"],
                service.files().get_media(fileId=item["id"]).execute(), loose_names,
            )
            print(f"Copied loose file: {name}")
            uploaded += 1
    print(f"Done. Copied {uploaded} file(s).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy Drive folders and extract ZIPs into named folders.")
    parser.add_argument("--source", required=True, help="Source Google Drive folder URL or ID")
    parser.add_argument("--destination", required=True, help="Destination Google Drive folder URL or ID")
    parser.add_argument("--credentials", default="credentials.json", help="OAuth client JSON (default: credentials.json)")
    parser.add_argument("--token", default="token.json", help="Saved login token (default: token.json)")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
