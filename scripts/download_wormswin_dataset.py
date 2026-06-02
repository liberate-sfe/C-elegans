from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen, urlretrieve


ZENODO_RECORD_URL = "https://zenodo.org/api/records/7456803"
DATASET_FILES = {
    "md": "md_dataset.zip",
    "csb1": "csb-1_dataset.zip",
    "synthetic": "synthetic_images_dataset.zip",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download WormSwin dataset archives from Zenodo."
    )
    parser.add_argument(
        "--dataset",
        choices=[*DATASET_FILES.keys(), "all"],
        default="md",
        help="Dataset archive to download. The MD split is the smallest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/wormswin"),
        help="Local cache directory for downloaded zip files.",
    )
    parser.add_argument("--force", action="store_true", help="Re-download existing files.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = json.load(urlopen(ZENODO_RECORD_URL))
    zenodo_files = {item["key"]: item for item in metadata["files"]}

    selected_keys = DATASET_FILES.keys() if args.dataset == "all" else [args.dataset]
    for dataset_key in selected_keys:
        file_name = DATASET_FILES[dataset_key]
        if file_name not in zenodo_files:
            raise SystemExit(f"{file_name} was not found in the Zenodo record.")

        item = zenodo_files[file_name]
        expected_size = int(item["size"])
        output_path = args.output_dir / file_name
        if (
            output_path.exists()
            and output_path.stat().st_size == expected_size
            and not args.force
        ):
            print(f"Already downloaded: {output_path}")
            continue

        print(f"Downloading {file_name} ({expected_size / 1024 / 1024:.1f} MB)")
        urlretrieve(item["links"]["self"], output_path)
        actual_size = output_path.stat().st_size
        if actual_size != expected_size:
            raise SystemExit(
                f"Downloaded size mismatch for {output_path}: "
                f"expected {expected_size}, got {actual_size}"
            )
        print(f"Saved: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
