#!/usr/bin/env bash
# Sets up the flight scanner: installs dependencies, registers macOS LaunchAgent

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PLIST="$HOME/Library/LaunchAgents/com.flightscanner.plist"

echo "=== Ucus Tarayici Kurulum ==="

# Create / update venv
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

# Install Playwright browsers (Chromium only)
"$VENV/bin/playwright" install chromium

echo "Bagimliliklar kuruldu."

# Write LaunchAgent plist (keeps scanner alive 24/7, auto-restarts on crash)
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.flightscanner</string>

    <key>ProgramArguments</key>
    <array>
        <string>$VENV/bin/python3</string>
        <string>$SCRIPT_DIR/flight_scanner.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/launchd_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/launchd_stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

echo "LaunchAgent yazildi: $PLIST"

# Load / reload the agent
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo ""
echo "Tarayici baslatildi ve her yeniden baslatmada otomatik calisacak."
echo "Log dosyasi: $SCRIPT_DIR/flight_scanner.log"
echo ""
echo "Durdurmak icin:"
echo "  launchctl unload ~/Library/LaunchAgents/com.flightscanner.plist"
echo ""
echo "Yeniden baslatmak icin:"
echo "  launchctl load ~/Library/LaunchAgents/com.flightscanner.plist"
