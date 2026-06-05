# amaran-python-control

Python control for Amaran / Sidus lights through the local Amaran Desktop OpenAPI v2 WebSocket.

This repository was first built for automating an `amaran Ray 120c` calibration workflow. CCT, G/M, HSL/HSI, and RGB modes have been validated on a Ray120c with write responses and same-mode readback.

## Features

- CCT: `1800K..20000K`
- G/M: public offset API uses `-1.0..+1.0`
- HSL/HSI: `hue 0..360`, `sat 0..100`
- RGB: `r/g/b 0..255`
- Intensity: percent `0..100`, mapped to OpenAPI raw `0..1000`
- Python API and CLI
- No third-party WebSocket dependency; only `cryptography` is required for OpenAPI token generation

## Requirements

- Python 3.9+
- Amaran Desktop installed and running
- The light connected inside Amaran Desktop
- Python package: `cryptography`

Install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Manual Setup

This script does not directly control Bluetooth. It connects to the local WebSocket OpenAPI exposed by Amaran Desktop; Amaran Desktop handles communication with the light.

Before use:

1. Open Amaran Desktop.
2. Log in and connect the target light in Amaran Desktop.
3. Confirm the local WebSocket is reachable. The default URL is `ws://127.0.0.1:33782`.
4. If your Desktop uses another port, set `AMARAN_WS_URL`.
5. If your target light has another node id, set `AMARAN_NODE_ID` or pass `--node-id`.

Environment variables:

```bash
export AMARAN_WS_URL=ws://127.0.0.1:33782
export AMARAN_NODE_ID=40165-560387
export AMARAN_OPENAPI_SECRET=...
```

The script includes the public demo secret from the Sidus / Amaran OpenAPI documentation because it worked with the local Amaran Desktop v2 OpenAPI during validation. Override it with `AMARAN_OPENAPI_SECRET` if your Desktop version requires a different secret.

## G/M Mapping

The recommended public API is `gm_offset`, or CLI `--gm-offset`:

- `gm_offset = -1.0`: maximum magenta, OpenAPI raw `gm=0`
- `gm_offset = 0.0`: neutral, OpenAPI raw `gm=100`
- `gm_offset = +1.0`: maximum green, OpenAPI raw `gm=200`

Mapping:

```text
raw_gm = round(100 + gm_offset * 100)
```

Raw GM is also available:

- Python: `gm=0..200`
- CLI: `--gm 0..200`

CLI shortcuts:

- `--gm-side m`: maximum magenta
- `--gm-side neutral`: neutral
- `--gm-side g`: maximum green

## CLI

Read capabilities:

```bash
python amaran_control.py node-config
```

CCT + G/M:

```bash
python amaran_control.py set-cct 1800 --intensity-percent 1 --gm-offset -1
python amaran_control.py set-cct 1800 --intensity-percent 1 --gm-offset 0
python amaran_control.py set-cct 1800 --intensity-percent 1 --gm-offset 1
python amaran_control.py get-cct
```

HSL/HSI:

Amaran OpenAPI names this mode `HSI`. The script exposes both `hsi` and `hsl` aliases.

```bash
python amaran_control.py set-hsl 120 100 --intensity-percent 1
python amaran_control.py get-hsl

python amaran_control.py set-hsi 240 100 --intensity-percent 1
python amaran_control.py get-hsi
```

RGB:

```bash
python amaran_control.py set-rgb 255 0 0 --intensity-percent 1
python amaran_control.py get-rgb
```

## Python API

```python
import amaran_control

# CCT: 1800K, 1%, maximum magenta
amaran_control.set_cct(1800, intensity_percent=1, gm_offset=-1)

# CCT: 20000K, 1%, maximum green
amaran_control.set_cct(20000, intensity_percent=1, gm_offset=1)

# HSL/HSI: hue=120, sat=100, 1%
amaran_control.set_hsl(120, 100, intensity_percent=1)
print(amaran_control.get_hsl())

# RGB: red at 1%
amaran_control.set_rgb(255, 0, 0, intensity_percent=1)
print(amaran_control.get_rgb())
```

Custom connection:

```python
from amaran_control import OpenAPISettings, set_cct

settings = OpenAPISettings(
    url="ws://127.0.0.1:33782",
    node_id="40165-560387",
)

set_cct(5600, intensity_percent=1, gm_offset=0, settings=settings)
```

## Ray120c Validation

Acceptance criterion: each point must return `code=0` from `set_*`, then the same-mode `get_*` must read back the exact written values.

Validated on `amaran Ray 120c #1`:

- CCT + G/M: `1800K`, `2300K`, `5600K`, `10000K`, `20000K` combined with `gm_offset=-1/0/+1`, intensity `1%`
- HSL/HSI: `hue=0/120/240`, `sat=100`, intensity `1%`
- HSL/HSI boundary points: `hue=360,sat=100` and `hue=30,sat=50`, intensity `1%`
- RGB: red, green, blue, and mixed `128,64,32`, intensity `1%`
- RGB without an intensity field preserves the current intensity

Ray120c `get_node_config` reports `advanced_hsi_support=false`. Although `set_hsi` can include `cct/gm` fields, this Ray120c ignores them; use `set_cct` for CCT + G/M control.

## References

The Python implementation in this repository was written independently; code was not copied from the repositories below. During research and validation, these sources were useful:

- [theontho/amaran-cli](https://github.com/theontho/amaran-cli): referenced for its Amaran Desktop local WebSocket notes and its observation that the Desktop WebSocket API is close to the Sidus / Amaran OpenAPI. It helped confirm the protocol direction for actions such as `set_cct`, `set_hsi`, and `set_rgb`.
- [wesbos/amaran-BLE-control](https://github.com/wesbos/amaran-BLE-control): referenced and tested as a direct BLE control path to evaluate whether the Desktop app could be bypassed. In this Ray120c validation, direct BLE was not selected as the main path because it did not reliably cover extended CCT + G/M control.
- Sidus / Amaran OpenAPI documentation: used to confirm the OpenAPI v2 request shape, AES-256-GCM token format, CCT/HSI/RGB fields, and value ranges.

## Tests

```bash
python -m py_compile amaran_control.py test_amaran_control.py
python -m unittest -v
```

Offline tests do not connect to a real light. Real device validation requires Amaran Desktop and a connected device.
