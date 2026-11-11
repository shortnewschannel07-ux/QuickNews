#!/bin/bash
# Quick News 動画エンジンの準備：読み上げ（VOICEVOX:冥鳴ひまり）と書体（Zen Kaku Gothic New）。
# 使い方: bash setup.sh [保存先]   既定は /home/claude/qn
# 地図・図の部品（d3・地図データ・字形）は kit/lib に入っているので取得不要。Chromium と Playwright は環境に入っている前提。
set -e
D="${1:-/home/claude/qn}"
mkdir -p "$D/vc/models" "$D/vc/dict" "$D/vc/ort" "$D/fonts"
pip install --break-system-packages -q pyopenjtalk-plus \
  "https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.2/voicevox_core-0.16.2-cp310-abi3-manylinux_2_34_x86_64.whl"
[ -f "$D/vc/models/1.vvm" ] || curl -sSL -o "$D/vc/models/1.vvm" \
  https://github.com/VOICEVOX/voicevox_vvm/releases/download/0.16.1/1.vvm
ls "$D"/vc/ort/*/lib/libvoicevox_onnxruntime.so >/dev/null 2>&1 || curl -sSL \
  https://github.com/VOICEVOX/onnxruntime-builder/releases/download/voicevox_onnxruntime-1.17.3/voicevox_onnxruntime-linux-x64-1.17.3.tgz | tar xz -C "$D/vc/ort"
ls -d "$D"/vc/dict/open_jtalk_dic_utf_8-* >/dev/null 2>&1 || curl -sSL \
  https://github.com/r9y9/open_jtalk/releases/download/v1.11.1/open_jtalk_dic_utf_8-1.11.tar.gz | tar xz -C "$D/vc/dict"
if [ ! -f "$D/fonts/package/700.css" ]; then
  (cd "$D/fonts" && npm pack -q @fontsource/zen-kaku-gothic-new >/dev/null 2>&1 && tar xzf fontsource-zen-kaku-gothic-new-*.tgz)
fi
echo "ready. 実行時に付ける: VOICEVOX_DIR=$D/vc QN_FONT_DIR=$D/fonts/package"
