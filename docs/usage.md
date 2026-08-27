# CLI Reference

## Synopsis

```
pxygen -i INPUT -o OUTPUT [options]
```

## Modes

### Directory Mode

Walks a footage folder tree, collects folders at the specified depth, imports them into DaVinci Resolve, and queues render jobs.

```sh
pxygen -i /Volumes/SSD/Footage -o /Volumes/SSD/Proxy -n 1 -d 2
```

### JSON Mode

Re-generates missing or incomplete proxies using file paths from an [fcmp](https://github.com/geekshootjack/fcmp) JSON report (`unique_in_a` / `unique_in_b`, plus `frame_mismatches` in proxy-frames mode).

Depth values are relative to the footage root recorded in the report (the `group_a`/`group_b` directories fcmp was run against). Files sitting directly at that root are too shallow to group — pxygen lists them in a warning and skips them.

```sh
pxygen -i fcmp_report.json -o /Volumes/SSD/Proxy -g a -n 1 -d 2
```

---

## Options

### Required

| Flag | Description |
|------|-------------|
| `-i, --input PATH` | Footage root folder or fcmp JSON report |
| `-o, --output PATH` | Proxy output root folder |

### Depth Control

Depth values now support a more intuitive relative interpretation:

- `0` means the input folder itself
- `1` means the first level below the input folder
- `2` means the second level below the input folder

| Flag | Default (macOS / other) | Description |
|------|-------------------------|-------------|
| `-n, --in-depth N` | 1 | Depth of the shooting-day folders |
| `-d, --out-depth N` | 2 | Depth of the camera-reel folders (≥ in-depth) |

**Example** — if your input folder is `/Volumes/SSD/Footage`:

| Depth | Meaning |
|-------|---------|
| `0` | `/Volumes/SSD/Footage` |
| `1` | `Day1` |
| `2` | `A001` |

So `-n 1 -d 2` means: group by Day, include camera reels as subfolders.

### Folder Selection *(mutually exclusive)*

| Flag | Description |
|------|-------------|
| `-s, --select` | Print a numbered list of folders and read a selection from stdin |
| `--filter NAME...` | Folder names to include, space-separated (e.g. `Day1 Day2`) |

**Interactive selection example:**

```
Folders (3):
  1  Shooting_Day_1
  2  Shooting_Day_2
  3  Shooting_Day_3

Numbers like '1 3 8', range like 2-4, 'all', or 'q' to quit
> 1 3
```

Entering `q` at any prompt exits gently. At the final render confirmation,
already-queued jobs stay in the saved Resolve project.

### JSON Mode Options

| Flag | Default | Description |
|------|---------|-------------|
| `-g, --group {a,b}` | `a` | fcmp side to render: a = `unique_in_a`, b = `unique_in_b` |

### Render Options

| Flag | Default | Description |
|------|---------|-------------|
| `-k, --codec CODEC` | `auto` | Override render preset (see below) |

**Codec values:**

| Value | Preset used |
|-------|-------------|
| `auto` | H.265 for ≤ 4 audio channels; ProRes Proxy for > 4 |
| `h265` / `hevc` / `265` | `fhd-h265-5mbps.xml` |
| `prores` | `fhd-prores-proxy.xml` |

The `auto` default exists because Adobe Premiere cannot hardware-decode 4:2:0 8-bit H.265 files with more than 4 audio tracks (Sony XAVC-I). ProRes avoids this issue.

---

## Examples

```sh
# Single depth level (shooting-day folders only)
pxygen -i /Volumes/SSD/Footage -o /Volumes/SSD/Proxy -n 1 -d 1

# Two depth levels (shooting day + camera reel)
pxygen -i /Volumes/SSD/Footage -o /Volumes/SSD/Proxy -n 1 -d 2

# Force ProRes for all clips
pxygen -i /Volumes/SSD/Footage -o /Volumes/SSD/Proxy -n 1 -d 2 -k prores

# Specific days only
pxygen -i /Volumes/SSD/Footage -o /Volumes/SSD/Proxy -n 1 -d 2 \
  --filter Shooting_Day_3 Shooting_Day_4

# JSON mode, side B, interactive selection
pxygen -i fcmp_report.json -o /Volumes/SSD/Proxy -g b -n 1 -d 2 --select
```

---

## DaVinci Resolve Presets

pxygen requires three presets to be imported into Resolve before use.
Preset files are included in the `presets/` directory:

| Preset name | File | Used for |
|-------------|------|----------|
| `fhd-h265-5mbps` | `presets/fhd-h265-5mbps.xml` | Standard proxy render |
| `fhd-prores-proxy` | `presets/fhd-prores-proxy.xml` | Multi-audio proxy render |
| `burn-in-vertical` | `presets/burn-in-vertical.xml` | Clip name + timecode overlay, centered — fits landscape and portrait |

To import: **DaVinci Resolve → Deliver → Render Settings → ⋯ → Import Preset**.

---

## Recovery from Crashes

The project is saved automatically before rendering starts. If Resolve crashes mid-render:

1. Reopen DaVinci Resolve.
2. Open the `proxy_YYYYMMDD_HHMMSS` project that was created.
3. Go to **Deliver** and restart the render queue.
