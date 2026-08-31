#!/usr/bin/env python3
"""Sync a repository between ModelScope and Hugging Face.

Directions:
  ms2hf  ModelScope  -> HuggingFace
  hf2ms  HuggingFace -> ModelScope

Authentication (env vars, or CLI flags that override them):
  MODELSCOPE_TOKEN   ModelScope SDK token
                     https://modelscope.cn  -> 我的 -> 访问令牌
  HF_TOKEN           Hugging Face token
                     https://huggingface.co/settings/tokens
  MS_ENDPOINT        optional, default https://modelscope.cn
                     (use https://www.modelscope.ai for the international site)

The repo type (model / dataset) is auto-detected when --repo-type is omitted.
The transfer is done by downloading the source repo into a local staging
directory, then uploading that directory to the target platform. LFS pointers
are resolved to real files during download, so the mirror stores actual blobs.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _parse_patterns(text: str | None):
    if not text:
        return None
    items = [p.strip() for p in text.split(",") if p.strip()]
    return items or None


def _ensure_dir(path: str | None, repo_id: str) -> Path:
    d = Path(path) if path else Path(".sync_work") / repo_id.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- #
# Repo-type auto-detection
# --------------------------------------------------------------------------- #
def detect_ms(repo_id, token, endpoint):
    from modelscope_hub import HubApi, RepoType

    api = HubApi(token=token, endpoint=endpoint or None)
    for rt in (RepoType.MODEL, RepoType.DATASET):
        if api.repo_exists(repo_id, rt):
            return "model" if rt is RepoType.MODEL else "dataset"
    sys.exit(f"ERROR: '{repo_id}' not found as model or dataset on ModelScope")


def detect_hf(repo_id, token):
    from huggingface_hub import HfApi, ModelInfo, DatasetInfo

    info = HfApi(token=token).repo_info(repo_id, repo_type=None, token=token)
    if isinstance(info, DatasetInfo):
        return "dataset"
    if isinstance(info, ModelInfo):
        return "model"
    return getattr(info, "repo_type", "model") or "model"


# --------------------------------------------------------------------------- #
# ModelScope (via modelscope_hub)
# --------------------------------------------------------------------------- #
def _ms_repo_type(repo_type: str):
    from modelscope_hub import RepoType

    return RepoType.MODEL if repo_type == "model" else RepoType.DATASET


def download_modelscope(repo_id, repo_type, revision, workdir, token, endpoint, allow, ignore):
    from modelscope_hub import HubApi

    api = HubApi(token=token, endpoint=endpoint or None)
    print(f"[ms] downloading {repo_id} ({repo_type}) -> {workdir}")
    kw = dict(
        repo_id=repo_id,
        repo_type=_ms_repo_type(repo_type),
        local_dir=workdir,
        allow_patterns=allow,
        ignore_patterns=ignore,
    )
    if revision:
        kw["revision"] = revision
    path = api.download_repo(**kw)
    print(f"[ms] download complete: {path}")
    return path


def upload_modelscope(repo_id, repo_type, workdir, token, revision, private, allow, ignore):
    from modelscope_hub import HubApi, Visibility

    api = HubApi(token=token)
    rt = _ms_repo_type(repo_type)
    if not api.repo_exists(repo_id, rt):
        print(f"[ms] creating repo {repo_id} ({repo_type})")
        api.create_repo(
            repo_id,
            rt,
            visibility=Visibility.PRIVATE if private else Visibility.PUBLIC,
        )
    else:
        print(f"[ms] repo {repo_id} exists, uploading into it")
    kw = dict(
        repo_id=repo_id,
        repo_type=rt,
        folder_path=workdir,
        allow_patterns=allow,
        ignore_patterns=ignore,
    )
    if revision:
        kw["revision"] = revision
    api.upload_folder(**kw)
    print(f"[ms] upload complete: {repo_id}")


# --------------------------------------------------------------------------- #
# Hugging Face (via huggingface_hub)
# --------------------------------------------------------------------------- #
def download_hf(repo_id, repo_type, revision, workdir, token, allow, ignore):
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    print(f"[hf] downloading {repo_id} ({repo_type}) -> {workdir}")
    kw = dict(
        repo_id=repo_id,
        repo_type=repo_type,
        local_dir=str(workdir),
        allow_patterns=allow,
        ignore_patterns=ignore,
    )
    if revision:
        kw["revision"] = revision
    path = api.snapshot_download(**kw)
    print(f"[hf] download complete: {path}")
    return path


def upload_hf(repo_id, repo_type, workdir, token, revision, private, allow, ignore):
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    if not api.repo_exists(repo_id=repo_id, repo_type=repo_type):
        print(f"[hf] creating repo {repo_id} ({repo_type}) private={private}")
        api.create_repo(repo_id=repo_id, repo_type=repo_type, private=private, exist_ok=True)
    else:
        print(f"[hf] repo {repo_id} exists, uploading into it")
    kw = dict(
        repo_id=repo_id,
        repo_type=repo_type,
        folder_path=str(workdir),
        allow_patterns=allow,
        ignore_patterns=ignore,
    )
    if revision:
        kw["revision"] = revision
    api.upload_folder(**kw)
    print(f"[hf] upload complete: {repo_id}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(
        description="Sync a repository between ModelScope and Hugging Face"
    )
    p.add_argument("--direction", required=True, choices=["ms2hf", "hf2ms"])
    p.add_argument("--repo-id", required=True, help="source repo id, e.g. owner/name")
    p.add_argument(
        "--repo-type",
        default="",
        choices=["", "model", "dataset"],
        help="repo type (model/dataset); empty = auto-detect",
    )
    p.add_argument("--revision", default="", help="branch/revision; empty = platform default")
    p.add_argument("--target-repo-id", default="", help="target repo id; empty = same as source")
    p.add_argument("--workdir", default="", help="local staging dir; empty = .sync_work/<repo>")
    p.add_argument("--private", action="store_true", help="create target repo as private")
    p.add_argument("--allow-patterns", default="", help="comma-separated globs to include (empty = all)")
    p.add_argument("--ignore-patterns", default="", help="comma-separated globs to exclude")
    p.add_argument("--ms-token", default=os.environ.get("MODELSCOPE_TOKEN", ""))
    p.add_argument("--hf-token", default=os.environ.get("HF_TOKEN", ""))
    p.add_argument(
        "--endpoint",
        default=os.environ.get("MS_ENDPOINT", ""),
        help="ModelScope endpoint (default https://modelscope.cn; "
             "do NOT use www.modelscope.ai - separate/unused account system)",
    )
    args = p.parse_args()

    src, dst = (
        ("ModelScope", "HuggingFace") if args.direction == "ms2hf" else ("HuggingFace", "ModelScope")
    )
    target_id = args.target_repo_id or args.repo_id
    revision = args.revision or None
    allow = _parse_patterns(args.allow_patterns)
    ignore = _parse_patterns(args.ignore_patterns)
    workdir = _ensure_dir(args.workdir or None, args.repo_id)

    ms_token = args.ms_token
    hf_token = args.hf_token

    print(f"==> direction: {args.direction} ({src} -> {dst})")
    print(f"==> source:    {args.repo_id}")
    print(f"==> target:    {target_id}")
    print(f"==> staging:   {workdir}")

    t0 = time.time()
    if args.direction == "ms2hf":
        if not ms_token:
            sys.exit("ERROR: MODELSCOPE_TOKEN (--ms-token) is required for ms2hf")
        if not hf_token:
            sys.exit("ERROR: HF_TOKEN (--hf-token) is required for ms2hf")
        repo_type = args.repo_type or detect_ms(args.repo_id, ms_token, args.endpoint)
        print(f"==> repo type: {repo_type} (auto-detected)" if not args.repo_type
              else f"==> repo type: {repo_type}")
        download_modelscope(
            args.repo_id, repo_type, revision, workdir, ms_token, args.endpoint, allow, ignore
        )
        upload_hf(target_id, repo_type, workdir, hf_token, revision, args.private, allow, ignore)
    else:  # hf2ms
        if not hf_token:
            sys.exit("ERROR: HF_TOKEN (--hf-token) is required for hf2ms")
        if not ms_token:
            sys.exit("ERROR: MODELSCOPE_TOKEN (--ms-token) is required for hf2ms")
        repo_type = args.repo_type or detect_hf(args.repo_id, hf_token)
        print(f"==> repo type: {repo_type} (auto-detected)" if not args.repo_type
              else f"==> repo type: {repo_type}")
        download_hf(args.repo_id, repo_type, revision, workdir, hf_token, allow, ignore)
        upload_modelscope(
            target_id, repo_type, workdir, ms_token, revision, args.private, allow, ignore
        )

    print(f"\nDONE: {src} '{args.repo_id}' -> {dst} '{target_id}' in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
