# Google Drive ZIP folder copier

This script copies the direct contents of a Google Drive source folder into a destination folder:

- A ZIP named `pump.zip` becomes a destination folder named `pump`, containing the ZIP's files and internal folders.
- A normal source Drive folder is copied as the same folder, including all its subfolders and files.
- Loose files directly in the source folder are put in one `Loose files` folder, so the destination contains folders rather than a long flat list of files.

Duplicate names are kept by adding ` (2)`, ` (3)`, and so on.

## One-time Google setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create/select a project and enable **Google Drive API**.
2. Create an **OAuth client ID** of type **Desktop app**, then download its JSON file.
3. Put that JSON beside this script and name it `credentials.json` (or use `--credentials path`).

## Run

```powershell
py -m pip install -r requirements.txt
py drive_flatten.py --source "https://drive.google.com/drive/folders/SOURCE_ID" --destination "https://drive.google.com/drive/folders/DESTINATION_ID"
```

The first run opens a browser so you can sign in to the Google account that can access both folders. It creates `token.json`; keep it private and do not commit it.

## Notes

- Source ZIP files themselves are not uploaded—only the folder made from their contents is.
- Google Docs/Sheets/Slides are not supported by this first version because they require exporting to a selected file format first.
- ZIP contents are kept in memory while each archive is processed. Very large ZIPs may need a streaming/local-temp-file variant.

## STEP/STP image dataset pipeline

To convert STEP/STP files in a Drive folder into dataset folders, install the dependencies and run:

~~~powershell
py -m pip install -r requirements.txt
py step_drive_dataset.py --source "SOURCE_FOLDER_LINK" --destination "EMPTY_DESTINATION_FOLDER_LINK"
~~~

For `example.step`, the destination receives `example/` containing six PNGs:
`top`, `bottom`, `front`, `back`, `left`, `right`, plus `metadata.txt`.

`metadata.txt` contains:

~~~text
"Symbol";"Value";"Unit";
"DESIGN";"example";"";
~~~
