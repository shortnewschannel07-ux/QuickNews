#!/bin/bash
# 動画と表紙を公開リポジトリ（media/日付/）に置き、Metricool に渡す URL を表示する。
# 使い方: bash publish.sh リポジトリの場所 YYYY-MM-DD スラッグ 動画.mp4 表紙.jpg [台本.json]
# 台本も置いておくと、あとで直して書き出し直せる
set -e
R="$1"; DAY="$2"; SLUG="$3"; MP4="$4"; JPG="$5"; SCR="${6:-}"
mkdir -p "$R/media/$DAY"
cp "$MP4" "$R/media/$DAY/$SLUG.mp4"; cp "$JPG" "$R/media/$DAY/${SLUG}_cover.jpg"
# 場面の時刻表（qn_short.py が動画の隣に書き出す）も置く。投稿後の離脱分析で使う
T="${MP4%.mp4}.timeline.json"; [ -f "$T" ] && cp "$T" "$R/media/$DAY/$SLUG.timeline.json"
[ -n "$SCR" ] && [ -f "$SCR" ] && cp "$SCR" "$R/media/$DAY/$SLUG.script.json"
cd "$R"
git fetch -q origin main && git rebase -q origin/main || true
git add "media/$DAY" media/posted.json 2>/dev/null || git add "media/$DAY"
git -c user.name="shortnewschannel07-ux" -c user.email="shortnewschannel07-ux@users.noreply.github.com" commit -q -m "投稿用の動画と表紙 $DAY $SLUG"
git push -q origin main
B="https://raw.githubusercontent.com/shortnewschannel07-ux/QuickNews/main/media/$DAY"
echo "VIDEO_URL=$B/$SLUG.mp4"
echo "COVER_URL=$B/${SLUG}_cover.jpg"
