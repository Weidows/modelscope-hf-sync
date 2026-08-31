# Sync ModelScope <-> HuggingFace

把模型 / 数据集在 **ModelScope（魔搭）** 和 **HuggingFace** 之间相互同步的小工具。

- 单文件脚本 `sync.py`，本地直接跑，也适配 **GitHub Actions 手动触发**。
- 手动触发时可选 **方向** 并 **填写项目名**，两边密钥走仓库 **Secrets**。
- 同步方式：先把源仓库下载到本地临时目录，再上传到目标平台。下载时会把 LFS 指针解析成真实文件，所以镜像存的是真实数据。

## 方向说明

| direction | 含义 |
|-----------|------|
| `ms2hf`   | ModelScope → HuggingFace |
| `hf2ms`   | HuggingFace → ModelScope |

## 本地使用

```bash
pip install -r requirements.txt

# ModelScope -> HuggingFace
MODELSCOPE_TOKEN=xxx HF_TOKEN=yyy \
python sync.py --direction ms2hf --repo-id owner/name --repo-type model

# HuggingFace -> ModelScope
MODELSCOPE_TOKEN=xxx HF_TOKEN=yyy \
python sync.py --direction hf2ms --repo-id owner/name --repo-type dataset
```

或者用命令行参数覆盖环境变量：

```bash
python sync.py --direction ms2hf --repo-id owner/name \
  --ms-token xxx --hf-token yyy
```

常用参数：

| 参数 | 说明 |
|------|------|
| `--repo-id` | 源仓库 id，必须带命名空间，如 `owner/name` |
| `--repo-type` | `model`（默认）或 `dataset` |
| `--target-repo-id` | 目标仓库 id，留空则复用源 id（跨账号同步时必填，且需填你自己的命名空间） |
| `--revision` | 分支 / 版本，留空用平台默认分支 |
| `--private` | 目标仓库创建为私有 |
| `--allow-patterns` | 只同步匹配的文件，逗号分隔，如 `*.safetensors,config.json` |
| `--ignore-patterns` | 排除的文件，逗号分隔 |
| `--workdir` | 本地暂存目录，默认 `.sync_work/<repo>` |
| `--endpoint` | ModelScope 地址，默认 `https://modelscope.cn`（国际站用 `https://www.modelscope.ai`） |

## GitHub Actions 使用

1. 把本仓库推到 GitHub（公开或私有均可）。
2. 在仓库 **Settings → Secrets and variables → Actions → New repository secret** 里添加：
   - `MODELSCOPE_TOKEN`：ModelScope 访问令牌（我的 → 访问令牌）
   - `HF_TOKEN`：HuggingFace token（Settings → Access Tokens）
   - `MS_ENDPOINT`（可选）：默认 `https://modelscope.cn`，国际站填 `https://www.modelscope.ai`
3. 进入仓库 **Actions → “Sync ModelScope <-> HuggingFace” → Run workflow**，
   在表单里选择 **方向**、填写 **项目名**（`owner/name`），按需填其他选项，点 **Run workflow**。

大仓库建议适当调大 `timeout-minutes`（默认 360 分钟）。

## 说明 / 注意

- 跨账号同步（例如把别人的 ModelScope 模型同步到你自己的 HF 账号）时，
  `--target-repo-id` 必须填**你自己的命名空间**下的名字，否则创建仓库会失败。
- 源仓库需对所用 token 可读；目标仓库若不存在会自动创建，已存在则直接追加上传。
