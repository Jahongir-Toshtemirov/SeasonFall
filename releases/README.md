# 📦 Releases

Ready-to-run SeasonFall packages — **no Python, no terminal needed**.

| OS | File | How to install / run |
|---|---|---|
| 🐧 **Linux** (Debian/Ubuntu) | `SeasonFall_<version>_amd64.deb` | `sudo apt install ./SeasonFall_*_amd64.deb` — then launch **SeasonFall** from your app grid (right-click → *Season Settings* to configure) |
| 🪟 **Windows** | `SeasonFall-Windows.exe` | double-click — portable single file, nothing to install |
| 🍎 **macOS** | `SeasonFall-macOS.zip` | unzip → drag **SeasonFall.app** into `Applications` → open once (right-click → *Open* the first time to pass Gatekeeper) |

## Which files are built where?

- **Linux `.deb`** — built locally with `packaging/build_deb.sh` (see below) and
  committed here.
- **Windows `.exe`** and **macOS `.app`** — cross-compiling Windows/macOS
  binaries from Linux is impossible (PyInstaller only builds for the OS it runs
  on). They are produced automatically by
  [`.github/workflows/release.yml`](../.github/workflows/release.yml):
  push a tag and they appear on the GitHub *Releases* page:

  ```bash
  git tag v1.1.0
  git push origin v1.1.0        # CI builds .exe + .app + .deb and attaches them
  ```

  (You can also trigger it manually: repo → *Actions* → *Release* → *Run workflow*.)

## Rebuilding the Linux .deb locally

```bash
pip install -r requirements.txt pyinstaller      # in your venv
pyinstaller --noconfirm --clean --onefile --name SeasonFall \
            --paths . packaging/entrypoint.py
./packaging/build_deb.sh dist/SeasonFall releases
```

Requires `dpkg-deb` (present on any Debian/Ubuntu system).
