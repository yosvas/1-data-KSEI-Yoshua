# Reproducible Build Notes

Use this process when the dashboard must look the same on another PC.

## Build One Artifact

Run `build_exe.bat` on the build PC. The script:

1. Installs the pinned package versions from `requirements.txt`.
2. Builds `dist\KSEI_Dashboard\KSEI_Dashboard.exe`.
3. Creates `KSEI_Dashboard.zip`.

Send `KSEI_Dashboard.zip` to the other PC. Do not send only
`KSEI_Dashboard.exe`; the EXE needs the bundled `_internal` folder.

## Why This Matters

The Streamlit UI can change when Streamlit, Plotly, Altair, or Pandas versions
change. `requirements.txt` pins the tested versions so the packaged app uses
the same runtime every time.

The launcher also sets the Streamlit theme explicitly, so the packaged EXE does
not depend on whether `.streamlit/config.toml` exists on the target PC.

## Target PC

On the target PC:

1. Unzip `KSEI_Dashboard.zip`.
2. Run `KSEI_Dashboard.exe` from the extracted `KSEI_Dashboard` folder.
3. Keep `ksei.db` next to the EXE if you want to preserve local uploaded data.

If the browser does not open automatically, open `http://localhost:8501`.
