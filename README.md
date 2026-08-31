# Sync ModelScope ↔ HuggingFace

把模型 / 数据集在 **ModelScope（魔搭）** 和 **HuggingFace** 之间相互迁移的小工具。
你只需要 **fork 本仓库 → 填好密钥 → 手动点一下（或让 AI agent 帮你跑）**，就能把任意
`owner/name` 的仓库从一个平台搬到另一个平台。

- 单文件脚本 `sync.py`，本地可直接跑，也适配 **GitHub Actions 手动触发**。
- 手动触发时可选 **方向**、填 **项目名**，两边密钥走仓库 **Secrets**。
- 同步方式：先把源仓库下载到本地临时目录，再上传到目标平台。下载时会把 LFS 指针解析成
  真实文件，所以镜像存的是真实数据（不是指针）。
- `--repo-type` 不填时**自动判断**是 model 还是 dataset。
- 针对境外 GitHub runner 已开启 **并行分片下载**，跨洋拉 ModelScope 也能跑满。

## 给新用户：三步就能用

1. **Fork** 这个仓库到你的 GitHub 账号。
2. 在 **Settings → Secrets and variables → Actions → Secrets** 里填上两个密钥
   （见下方「需要设置的密钥」）。
3. 进入 **Actions → “Sync ModelScope ↔ HuggingFace” → Run workflow**，
   选方向、填 `owner/name`，点 **Run workflow**。

> 想用 AI agent 帮你搬？直接把本仓库交给 agent，告诉它：
> “把这个仓库跑一次，方向 ms2hf，项目名 `DeepSeek/DeepSeek-V3`”，
> 它会填表单触发 workflow（密钥已经在你的 Secrets 里，不用再给）。

## 方向说明

| direction | 含义 |
|-----------|------|
| `ms2hf`   | ModelScope → HuggingFace |
| `hf2ms`   | HuggingFace → ModelScope |

## 需要设置的密钥（Repository Secrets）

在仓库 **Settings → Secrets and variables → Actions → Secrets → New repository secret** 里添加。

| 变量名 | 必填 | 作用 | 获取地址 |
|--------|------|------|----------|
| `MODELSCOPE_TOKEN` | 是（任意方向） | ModelScope 访问令牌 | https://modelscope.cn → 我的 → 访问令牌 |
| `HF_TOKEN` | 是（任意方向） | HuggingFace 访问令牌 | https://huggingface.co → Settings → Access Tokens |
| `MS_ENDPOINT` | 否 | ModelScope 站点地址，默认 `https://modelscope.cn`（与 `modelscope.cn` 同一账号体系；国际站 `www.modelscope.ai` 是另一套、基本无人使用，**请勿填**） | — |

> 本地运行时也可直接以环境变量形式导出（见下），不必写成 GitHub Secret。

## 手动触发（GitHub Actions）

1. Fork 本仓库并填好上面三个 Secret（前两个必填）。
2. 进入仓库 **Actions → “Sync ModelScope ↔ HuggingFace” → Run workflow**。
3. 在表单里：
   - **direction**：选 `ms2hf` 或 `hf2ms`
   - **repo_id**：填源仓库 id，必须带命名空间，如 `owner/name`
   - **repo_type**：留空则自动判断（推荐）
   - 其余按需填（目标仓库名、是否私有、文件过滤等）
4. 点 **Run workflow**，等日志跑完即可。

大仓库建议把 workflow 里的 `timeout-minutes`（默认 360）调大。

## 本地使用

```bash
pip install -r requirements.txt

# ModelScope -> HuggingFace（不填 --repo-type 会自动判断类型）
MODELSCOPE_TOKEN=xxx HF_TOKEN=yyy \
python sync.py --direction ms2hf --repo-id owner/name

# HuggingFace -> ModelScope
MODELSCOPE_TOKEN=xxx HF_TOKEN=yyy \
python sync.py --direction hf2ms --repo-id owner/name
```

也可以用命令行参数覆盖环境变量：

```bash
python sync.py --direction ms2hf --repo-id owner/name \
  --ms-token xxx --hf-token yyy
```

## 常用参数

| 参数 | 说明 |
|------|------|
| `--repo-id` | 源仓库 id，必须带命名空间，如 `owner/name` |
| `--repo-type` | `model` / `dataset`，留空则自动判断 |
| `--target-repo-id` | 目标仓库 id，留空则复用源 id（跨账号同步时必填，且需填你自己的命名空间） |
| `--revision` | 分支 / 版本，留空用平台默认分支 |
| `--private` | 目标仓库创建为私有 |
| `--allow-patterns` | 只同步匹配的文件，逗号分隔，如 `*.safetensors,config.json` |
| `--ignore-patterns` | 排除的文件，逗号分隔 |
| `--workdir` | 本地暂存目录，默认 `.sync_work/<repo>` |
| `--endpoint` | ModelScope 地址，默认 `https://modelscope.cn` |

## 注意事项

- **跨账号同步**（例如把别人的 ModelScope 模型同步到你自己的 HF 账号）时，
  `--target-repo-id` 必须填**你自己的命名空间**下的名字，否则创建仓库会失败。
- 源仓库需对所用 token **可读**；目标仓库若不存在会自动创建，已存在则直接追加上传。
- 速度相关：本工具已对 ModelScope 下载开启 `MODELSCOPE_DOWNLOAD_PARALLEL_WORKERS=8`
  的并行分片下载，以解决境外 runner 单流 ~2MB/s 的问题。
