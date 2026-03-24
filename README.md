# MacStats (Python, macOS menu bar)

A tiny, configurable **menu bar** app for macOS written in Python. Choose which stats to show with simple checkboxes in the app menu. No windows. No fluff.

**Modules available**

- CPU usage
- Memory usage
- Network rate (upload / download)
- Disk free space
- Battery percent (+ charging indicator)
- GPU (experimental; requires parsing `powermetrics`, typically needs `sudo` on Apple Silicon)

## Quick start

Requires [conda](https://docs.conda.io/en/latest/) (Anaconda or Miniconda) to be installed.

```bash
./start.sh
```

That's it. `start.sh` will:
1. Create (or update) the `macstats` conda environment from `environment.yml`
2. Activate the environment
3. Launch the app

### Manual setup (optional)

If you prefer to manage the environment yourself:

```bash
# Create the conda environment
conda env create -f environment.yml

# Activate it
conda activate macstats

# Run
python main.py
```

Grant **Accessibility** permission for the terminal you run from if macOS prompts you (rumps embeds a status item; usually no special permission is needed for reading stats, but prompts can vary).

Config is stored at `~/.macstats/config.json` after you hit **Save settings** in the app menu.

## Packaging into a .app

Run the build script to produce a fully self-contained `MacStats.app` — **no Python required on the target machine**:

```bash
./build.sh
```

The app is output to `dist/MacStats.app`. You can:
- Double-click it to run
- Drag it to `/Applications`
- Zip and distribute it to users — everything is bundled inside

> Powered by [PyInstaller](https://pyinstaller.org). The app icon and all dependencies are embedded in the bundle.

> Note: First launch of unsigned apps may require right‑click → Open.

## How it works

- **rumps** creates a single menu bar item whose title is a compact string of your selected modules.
- **psutil** reads CPU, memory, disk, battery, and network counters.
- Network **rate** is computed by sampling byte counters and converting to bytes per second.
- **GPU** is a placeholder; enabling it tries to parse `powermetrics --samplers gpu_power -n 1` output. For accurate data, you’ll likely need to run a privileged helper and cache samples at a lower frequency.

## Roadmap ideas

- Per‑core CPU and memory pressure indicator
- Per‑process top talkers for network (sampling `nettop`)
- A compact icon set with symbols instead of text
- Optional multi‑item mode (separate status items per module via PyObjC)
- Export snapshot to clipboard
- Configurable update interval

## Releases and Versioning

1.  **Bump version**: Update the [`VERSION`](file:///Users/fotiem.constant/Documents/gitrepo/personal/opensource/macstats-menu-app/macstats/VERSION) file (e.g., `1.1.0`).
2.  **Tag it**:
    ```bash
    git add VERSION
    git commit -m "Bump version to 1.1.0"
    git tag v1.1.0
    git push origin main --tags
    ```
3.  **Auto-build**: The [GitHub Action](file:///Users/fotiem.constant/Documents/gitrepo/personal/opensource/macstats-menu-app/macstats/.github/workflows/release.yml) will automatically build the self-contained `.app`, zip it, and create a [GitHub Release](https://github.com/codewithbro95/macstats/releases).

Existing users can use the **Check for Update** menu item to see if there's a new version available.

## License

MIT
