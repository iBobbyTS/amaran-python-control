# amaran-python-control

用 Python 通过 Amaran Desktop 本地 OpenAPI v2 控制 Amaran / Sidus 灯具。

这个仓库最初为 `amaran Ray 120c` 自动化标定而写，已在 Ray120c 上验证 CCT、G/M、HSL/HSI、RGB 模式的写入和读回。

[English README](README.en.md)

## 功能

- CCT：`1800K..20000K`
- G/M：公开接口使用 `-1.0..+1.0`
- HSL/HSI：`hue 0..360`、`sat 0..100`
- RGB：`r/g/b 0..255`
- 强度：支持百分比 `0..100`，内部映射到 OpenAPI raw `0..1000`
- Python API 和 CLI 都可用
- 不依赖第三方 WebSocket 库，只依赖 `cryptography` 生成 OpenAPI token

## 依赖

- Python 3.9+
- Amaran Desktop 已安装并正在运行
- 灯具已经在 Amaran Desktop 里连接成功
- Python 包：`cryptography`

安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 需要手动操作的部分

这个脚本不直接操作蓝牙。它连接 Amaran Desktop 在本机开放的 WebSocket OpenAPI，由 Amaran Desktop 负责和灯具通信。

使用前需要手动完成：

1. 打开 Amaran Desktop。
2. 在 Amaran Desktop 中登录并连接目标灯具。
3. 确认本机 WebSocket 可访问。默认 URL 是 `ws://127.0.0.1:33782`。
4. 如果你的 Amaran Desktop 使用了其他端口，设置 `AMARAN_WS_URL`。
5. 如果你的目标灯具 node id 不同，设置 `AMARAN_NODE_ID` 或在 CLI 里传 `--node-id`。

环境变量：

```bash
export AMARAN_WS_URL=ws://127.0.0.1:33782
export AMARAN_NODE_ID=40165-560387
export AMARAN_OPENAPI_SECRET=...
```

脚本默认包含 Sidus / Amaran OpenAPI 示例文档里的公开 demo secret；它在本地 Amaran Desktop v2 OpenAPI 验证可用。如果你的 Desktop 版本要求自己的 secret，请用 `AMARAN_OPENAPI_SECRET` 覆盖。

## G/M 映射

对外推荐使用 `gm_offset` 或 CLI 的 `--gm-offset`：

- `gm_offset = -1.0`：最偏品红，OpenAPI raw `gm=0`
- `gm_offset = 0.0`：中性，OpenAPI raw `gm=100`
- `gm_offset = +1.0`：最偏绿，OpenAPI raw `gm=200`

映射公式：

```text
raw_gm = round(100 + gm_offset * 100)
```

也可以直接使用 raw GM：

- Python: `gm=0..200`
- CLI: `--gm 0..200`

快捷 CLI：

- `--gm-side m`：最偏品红
- `--gm-side neutral`：中性
- `--gm-side g`：最偏绿

## CLI 用法

读取能力：

```bash
python amaran_control.py node-config
```

CCT + G/M：

```bash
python amaran_control.py set-cct 1800 --intensity-percent 1 --gm-offset -1
python amaran_control.py set-cct 1800 --intensity-percent 1 --gm-offset 0
python amaran_control.py set-cct 1800 --intensity-percent 1 --gm-offset 1
python amaran_control.py get-cct
```

HSL/HSI：

Amaran OpenAPI 把这个模式命名为 `HSI`。脚本同时提供 `hsi` 和 `hsl` 两套别名。

```bash
python amaran_control.py set-hsl 120 100 --intensity-percent 1
python amaran_control.py get-hsl

python amaran_control.py set-hsi 240 100 --intensity-percent 1
python amaran_control.py get-hsi
```

RGB：

```bash
python amaran_control.py set-rgb 255 0 0 --intensity-percent 1
python amaran_control.py get-rgb
```

## Python 用法

```python
import amaran_control

# CCT: 1800K, 1%, 最偏品红
amaran_control.set_cct(1800, intensity_percent=1, gm_offset=-1)

# CCT: 20000K, 1%, 最偏绿
amaran_control.set_cct(20000, intensity_percent=1, gm_offset=1)

# HSL/HSI: hue=120, sat=100, 1%
amaran_control.set_hsl(120, 100, intensity_percent=1)
print(amaran_control.get_hsl())

# RGB: red at 1%
amaran_control.set_rgb(255, 0, 0, intensity_percent=1)
print(amaran_control.get_rgb())
```

自定义连接：

```python
from amaran_control import OpenAPISettings, set_cct

settings = OpenAPISettings(
    url="ws://127.0.0.1:33782",
    node_id="40165-560387",
)

set_cct(5600, intensity_percent=1, gm_offset=0, settings=settings)
```

## Ray120c 验证记录

验收标准：每个测试点都要求 `set_*` 返回 `code=0`，随后同模式 `get_*` 精确读回写入值。

已在 `amaran Ray 120c #1` 上验证：

- CCT + G/M：`1800K`、`2300K`、`5600K`、`10000K`、`20000K` 分别组合 `gm_offset=-1/0/+1`，强度 `1%`
- HSL/HSI：`hue=0/120/240`、`sat=100`、强度 `1%`
- HSL/HSI 边界：`hue=360,sat=100` 和 `hue=30,sat=50`，强度 `1%`
- RGB：红、绿、蓝和混合色 `128,64,32`，强度 `1%`
- RGB 省略 intensity 时会保持当前 intensity

Ray120c 的 `get_node_config` 显示 `advanced_hsi_support=false`。因此虽然 `set_hsi` 请求可以附带 `cct/gm` 字段，但 Ray120c 会忽略这些字段；CCT + G/M 请使用 `set_cct`。

## 测试

```bash
python -m py_compile amaran_control.py test_amaran_control.py
python -m unittest -v
```

离线测试不会连接真实灯具；真实灯具验证需要 Amaran Desktop 和已连接的设备。
