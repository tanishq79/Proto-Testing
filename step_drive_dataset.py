#!/usr/bin/env python3
"""Turn STEP/STP files in Google Drive into six-view image folders."""

from __future__ import annotations

import argparse
import io
import tempfile
from pathlib import Path, PurePosixPath

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import numpy as np
from googleapiclient.http import MediaFileUpload
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drive_flatten import FOLDER_MIME, children, create_folder, folder_id, get_service, names_in

VIEW_ANGLES = {
    "top": (90, -90), "bottom": (-90, -90), "front": (0, -90),
    "back": (0, 90), "left": (0, 180), "right": (0, 0),
}


def step_files(service, source_id: str):
    """Yield STEP/STP files below the source Drive folder."""
    folders = [source_id]
    while folders:
        for item in children(service, folders.pop()):
            if item["mimeType"] == FOLDER_MIME:
                folders.append(item["id"])
            elif item["name"].lower().endswith((".step", ".stp")):
                yield item


def model_mesh(step_path: Path) -> tuple[np.ndarray, np.ndarray]:
    model = cq.importers.importStep(str(step_path))
    vertices, triangles = model.val().tessellate(tolerance=0.05, angularTolerance=0.1)
    verts = np.array([(vertex.x, vertex.y, vertex.z) for vertex in vertices], dtype=np.float64)
    faces = np.array(triangles, dtype=np.int64)
    if not len(verts) or not len(faces):
        raise ValueError("The STEP file contains no renderable geometry.")
    centre = (verts.min(axis=0) + verts.max(axis=0)) / 2
    largest_side = (verts.max(axis=0) - verts.min(axis=0)).max()
    return (verts - centre) * (2 / largest_side if largest_side else 1), faces


def render_view(vertices: np.ndarray, triangles: np.ndarray, elevation: int, azimuth: int, output: Path) -> None:
    fig = plt.figure(figsize=(5.12, 5.12), dpi=100)
    axis = fig.add_subplot(111, projection="3d")
    mesh = vertices[triangles]
    normals = np.cross(mesh[:, 1] - mesh[:, 0], mesh[:, 2] - mesh[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(lengths == 0, 1, lengths)
    light = np.array([0.4, -0.5, 0.75])
    light = light / np.linalg.norm(light)
    brightness = 0.45 + 0.55 * np.abs(normals @ light)
    colour = np.array([0.55, 0.60, 0.68])
    face_colours = np.c_[colour * brightness[:, None], np.ones(len(brightness))]
    axis.add_collection3d(Poly3DCollection(mesh, facecolors=face_colours, edgecolor="none"))
    axis.set_xlim(-1.4, 1.4)
    axis.set_ylim(-1.4, 1.4)
    axis.set_zlim(-1.4, 1.4)
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=elevation, azim=azimuth)
    axis.set_proj_type("ortho")
    axis.set_axis_off()
    fig.patch.set_facecolor("white")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(output, facecolor="white")
    plt.close(fig)


def write_metadata(path: Path, model_name: str) -> None:
    name = model_name.replace('"', '""')
    path.write_text('"Symbol";"Value";"Unit";\n"DESIGN";"' + name + '";"";\n', encoding="utf-8-sig")


def upload_file(service, local_path: Path, destination_id: str) -> None:
    mime_type = "image/png" if local_path.suffix == ".png" else "text/plain"
    media = MediaFileUpload(str(local_path), mimetype=mime_type)
    service.files().create(
        body={"name": local_path.name, "parents": [destination_id]}, media_body=media, fields="id"
    ).execute()


def process_file(service, item: dict, destination_id: str, destination_names: set[str]) -> None:
    model_name = PurePosixPath(item["name"]).stem
    output_id, output_name = create_folder(service, destination_id, model_name, destination_names)
    print(f"Processing {item['name']} -> {output_name}/")
    with tempfile.TemporaryDirectory(prefix="step-render-") as temp_dir:
        temp = Path(temp_dir)
        step_path = temp / item["name"]
        step_path.write_bytes(service.files().get_media(fileId=item["id"]).execute())
        vertices, triangles = model_mesh(step_path)
        for view_name, (elevation, azimuth) in VIEW_ANGLES.items():
            image_path = temp / f"{view_name}.png"
            render_view(vertices, triangles, elevation, azimuth, image_path)
            upload_file(service, image_path, output_id)
        metadata_path = temp / "metadata.txt"
        write_metadata(metadata_path, model_name)
        upload_file(service, metadata_path, output_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Drive STEP/STP files into six-view image folders.")
    parser.add_argument("--source", required=True, help="Source Google Drive folder URL or ID")
    parser.add_argument("--destination", required=True, help="Destination Google Drive folder URL or ID")
    parser.add_argument("--credentials", default="credentials.json", help="OAuth client JSON")
    parser.add_argument("--token", default="token.json", help="Saved OAuth token")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = get_service(args.credentials, args.token)
    destination_id = folder_id(args.destination)
    destination_names = names_in(service, destination_id)
    success, failed = 0, 0
    for item in step_files(service, folder_id(args.source)):
        try:
            process_file(service, item, destination_id, destination_names)
            success += 1
        except Exception as error:
            failed += 1
            print(f"FAILED {item['name']}: {error}")
    print(f"Finished. Successful: {success}; failed: {failed}.")


if __name__ == "__main__":
    main()
