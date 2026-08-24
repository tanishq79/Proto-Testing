from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


SUCCESS = re.compile(r"^\[SUCCESS\] (?P<source>.+) -> (?P<url>/manus-storage/.+)$")


def asset_key(path: str) -> str:
    parts = Path(path).parts
    try:
        raw_index = parts.index("raw")
    except ValueError as error:
        raise ValueError(f"Cannot derive a raw-data-relative path from {path}") from error
    return Path(*parts[raw_index + 1 :]).as_posix()


def upload_urls(log_path: Path) -> dict[str, str]:
    urls: dict[str, str] = {}
    marker = "/industrial-hardware-gallery/"
    for line in log_path.read_text(encoding="utf-8").splitlines():
        match = SUCCESS.match(line.strip())
        if not match or marker not in match.group("source"):
            continue
        relative = match.group("source").split(marker, 1)[1]
        urls[Path(relative).as_posix()] = match.group("url")
    return urls


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the notebook manifest to a portable asset-key/URL manifest.")
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--upload-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    urls = upload_urls(args.upload_log)
    records: list[dict[str, str | None]] = []
    with args.source_manifest.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            relative = asset_key(row["image_path"])
            if relative not in urls:
                raise RuntimeError(f"No managed-storage URL was found for {relative}")
            record = {key: (value or None) for key, value in row.items() if key not in {"image_path", "metadata_path", "folder_name"}}
            record["asset_key"] = relative
            record["image_url"] = urls[relative]
            records.append(record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(records)} portable manifest rows to {args.output}")


if __name__ == "__main__":
    main()
