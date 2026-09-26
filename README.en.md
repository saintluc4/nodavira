# Nodavira

[Português](README.md) · **English**

**An open-source DNS benchmark for Windows and Linux, with English and Portuguese interfaces.**

[Download for Windows](https://github.com/saintluc4/nodavira/releases/download/v0.5.0/Nodavira.exe) · [Linux packages and releases](https://github.com/saintluc4/nodavira/releases) · [Report an issue](https://github.com/saintluc4/nodavira/issues)

I built Nodavira to compare DNS resolvers from the connection where they will actually be used. It measures latency, variation and failures using a known set of queries, with an open methodology and exportable results.

The app runs locally in its own desktop window. It sends queries directly to the selected resolvers and does not change system DNS settings. Source code, visual assets, tests and build scripts are included in this repository.

The project is in early development. Rankings describe the conditions observed during a test; they do not certify a provider or predict future performance. Nodavira does not measure download speed, gaming ping or full page load time.

## Download and run

| Platform | Download | Installation |
|---|---|---|
| Windows x64 | `Nodavira.exe` | Open the executable |
| Ubuntu 24.04+ / Linux Mint 22+ | `nodavira_0.5.0-1_all.deb` | `sudo apt install ./nodavira_0.5.0-1_all.deb` |
| Arch Linux | `nodavira-0.5.0-1-any.pkg.tar.zst` | `sudo pacman -U ./nodavira-0.5.0-1-any.pkg.tar.zst` |

Download the files from [GitHub Releases](https://github.com/saintluc4/nodavira/releases). Windows requires Microsoft Edge WebView2 Runtime and .NET Framework 4.6.2 or later. Python is bundled in the executable. Linux package managers install Python, GTK 3, PyGObject and WebKitGTK 4.1 as needed. The application itself runs as a regular user.

The AUR package has not been published. `yay -S nodavira` is not available; install the Arch package from the Release using `pacman -U`.

## Language

Choose **English** or **Português** from the language selector at the top of the window. The choice applies immediately and is saved across restarts:

- Windows: `%APPDATA%/nodavira/preferences.json`.
- Linux: `$XDG_CONFIG_HOME/nodavira/preferences.json`, or `~/.config/nodavira/preferences.json` when unset.

On first launch, a Portuguese system locale selects Portuguese; other locales select English. Language changes do not change the selected servers, domains, measurement parameters or scoring method. The default domain list includes Brazilian services; customize it or import a HAR to reflect your own browsing.

API validation messages and application-owned report messages follow the selected language. JSON keys, CSV columns, DNS status codes, domain names and user-provided server names remain stable. External library diagnostics and license texts remain in their original language. Existing report files are not rewritten when switching languages.

## Interface

![Nodavira benchmark interface](docs/images/interface.jpg)

*Screenshot of the earlier Portuguese interface. The current application also provides English through the language selector.*

## Features

- Classic DNS over UDP, with TCP fallback for truncated responses.
- DNS over HTTPS (DoH), with HTTP/2 and recorded HTTP/1.1 fallback.
- DNS over TLS (DoT), with certificate and hostname validation.
- IPv4 and IPv6 transports, with independent A/AAAA record selection.
- Median, P95, failures, dispersion and a score with timeout penalties.
- Custom servers, domains, passes, concurrency and timeout.
- Local TXT/HAR import and JSON/CSV export.
- A native desktop window: WebView2 on Windows, GTK/WebKitGTK on Linux.

HAR import reads request hostnames locally. Full URLs, cookies and request content are not submitted to the benchmark engine. DNS queries are sent to the selected providers; the application has no telemetry.

## How the benchmark works

Every resolver receives the same query set. Server and query order is shuffled in blocks using a random seed included in the JSON report. One resolver is measured at a time to reduce competition introduced by the test itself.

The first pass measures names not yet queried by this run. It is **not an empty-cache test**: providers may already have cached those names. Later passes measure repeats, without assuming cache retention. A selected local intermediary such as `127.0.0.53` includes that service and any cache it maintains; the app does not infer its upstream resolver.

The score gives equal weight to the two phases:

```text
score = 0.5 × mean first-pass cost + 0.5 × mean repeat-pass cost
```

Each failure costs at least the configured timeout. Median and P95 use valid responses; failures are reported separately. NXDOMAIN, SERVFAIL, refusals and blocking addresses do not gain an advantage by responding quickly. NODATA is a valid response without the requested record, not proof of connectivity.

Encrypted connections are reused per concurrency lane. Initial probes include connection setup and are excluded from the ranking. Reconnections during the measured phase still count. DoH uses the selected destination IP while retaining SNI and certificate verification.

Unreachable resolvers remain visible but are not ranked. Cancelled runs are partial and do not recommend a winner. Repeat at different times and avoid heavy network activity. Small differences and limited samples do not establish statistical significance; the app does not calculate it.

The **How we measure** screen contains the full English explanation. The technical [methodology document](METHODOLOGY.md) is currently in Portuguese.

## Reports

JSON includes the configuration, seed, destination IPs, samples, answers, TTL, failures and batch timings. CSV contains one row per query. The reported AD bit is recorded; the app does not independently validate DNSSEC.

Reports are saved next to the Windows executable in `reports/`, or under `$XDG_DATA_HOME/nodavira/reports` on Linux (default: `~/.local/share/nodavira/reports`). You can also export them from the interface. Reports contain queried domains and resolver addresses; review them before sharing.

## Run from source

Windows:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install --no-deps --target .deps -r requirements-lock.txt
.venv\Scripts\python app.py
```

Ubuntu/Mint:

```bash
sudo apt install python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 ca-certificates xdg-utils
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --no-deps -r requirements-linux-lock.txt
.venv/bin/python app.py
```

Arch:

```bash
sudo pacman -S --needed python python-dnspython python-httpx python-h2 python-pywebview python-gobject python-cairo gtk3 webkit2gtk-4.1 ca-certificates xdg-utils
python app.py
```

Use `--browser` to open the UI in a browser or `--no-browser` for a local server without a window. The server binds to loopback and requires a session token. See [Linux packaging](docs/LINUX.md) and [contributing](CONTRIBUTING.md) for build details in Portuguese.

## Tests and translations

```bash
python -m unittest discover -s tests -v
```

English translations are stored in `static/en.json`, keyed by the Portuguese source strings. `static/i18n.js` translates registered interface text and attributes. `nodavira/i18n.py` manages local preferences and translates application-owned messages without changing measurements. Tests check translation coverage, placeholders, preference persistence and authenticated language updates.

Linux CI builds and installs Ubuntu and Arch packages and opens a real GTK window under Xvfb. Mint desktop, Wayland and other architectures still require manual validation. See [test notes](TESTING.md) for the recorded scope.

## License

The application is distributed under the [MIT license](LICENSE). Dependencies retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md) and `licenses/`. Editable branding resources are available in `brand/`.
