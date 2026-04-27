# Cheap Ticket Finder

A background flight scanner that monitors Google Flights for cheap tickets from Istanbul to Asian destinations and fires a macOS notification the moment a deal appears.

## How it works

Every 20 minutes the scanner opens headless Chromium, checks Google Flights for each destination, and compares the cheapest found price against a configurable threshold (default **TL 29,000**). If a price is at or below the threshold, a native macOS notification is sent with the date and price.

It runs as a macOS **LaunchAgent**, so it starts automatically on login and restarts itself if it crashes.

## Destinations

| City     |
|----------|
| Seoul    |
| Tokyo    |
| Beijing  |
| Shanghai |

Origin is always **Istanbul**.

## Requirements

- macOS (uses `osascript` for notifications and `launchctl` for auto-start)
- Python 3.10+

## Setup

```bash
chmod +x setup.sh
./setup.sh
```

`setup.sh` will:
1. Create a Python virtual environment in `.venv/`
2. Install dependencies (`playwright`)
3. Download the Chromium browser
4. Register and start a LaunchAgent (`com.flightscanner`) that keeps the scanner alive 24/7

## Configuration

Edit the top of `flight_scanner.py`:

```python
MAX_PRICE           = 29_000   # alert threshold in Turkish Lira
CHECK_INTERVAL_MINS = 20       # how often to scan
```

To add or change destinations, edit the `DESTINATIONS` list.

## Logs

| File | Contents |
|------|----------|
| `flight_scanner.log` | Scan results, found prices, notifications sent |
| `launchd_stdout.log` | Standard output captured by launchd |
| `launchd_stderr.log` | Standard error captured by launchd |

## Managing the LaunchAgent

```bash
# Stop the scanner
launchctl unload ~/Library/LaunchAgents/com.flightscanner.plist

# Start the scanner
launchctl load ~/Library/LaunchAgents/com.flightscanner.plist
```

## Running manually

```bash
.venv/bin/python3 flight_scanner.py
```

## Dependencies

- [Playwright](https://playwright.dev/python/) — headless browser automation for scraping Google Flights
