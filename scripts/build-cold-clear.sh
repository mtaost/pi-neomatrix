#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="$project_dir/third_party/cold-clear"

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo is required. Install it first, for example: sudo apt install -y cargo rustc" >&2
  exit 1
fi

if [ ! -f "$source_dir/Cargo.toml" ]; then
  echo "Cold Clear source is missing. Run: git submodule update --init --recursive" >&2
  exit 1
fi

cd "$source_dir"
cargo build --release -p c-api
