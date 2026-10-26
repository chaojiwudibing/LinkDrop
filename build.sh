#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ is required"'
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
FFMPEG_BIN="${FFMPEG_BIN:-$(command -v ffmpeg || true)}"
for executable in "$NODE_BIN" "$FFMPEG_BIN"; do
  test -n "$executable" && test -x "$executable" || { echo 'Install Node and FFmpeg first.' >&2; exit 1; }
done
APP="$PWD/build/LinkDrop.app"
RES="$APP/Contents/Resources"
mkdir -p "$RES" "$APP/Contents/MacOS"
cp Info.plist "$APP/Contents/Info.plist"
cp src/linkdrop_backend.py "$RES/"
ln -sfn "$PWD/.venv" "$RES/python"
ln -sf "$NODE_BIN" "$RES/node"
ln -sf "$FFMPEG_BIN" "$RES/ffmpeg"
cat > "$RES/yt-dlp" <<'LAUNCHER'
#!/bin/sh
RESOURCE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec "$RESOURCE_DIR/python/bin/python" "$RESOURCE_DIR/linkdrop_backend.py" "$@"
LAUNCHER
chmod +x "$RES/yt-dlp"
swiftc src/main.swift -o "$APP/Contents/MacOS/LinkDrop" -framework Cocoa -framework Carbon
"$APP/Contents/MacOS/LinkDrop" --self-test
"$RES/yt-dlp" --self-test
codesign --force --sign - "$APP"
printf 'Built: %s\nKeep this checkout and its .venv in place. This is a local build, not a portable app.\n' "$APP"
