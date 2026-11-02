# MelFox

**Version:** `v1`\
**Description:** A cross-platform Firefox configuration and debloating
script.

MelFox applies Firefox Enterprise Policies to configure a quieter,
privacy-focused browser. It is designed for Windows, macOS, Linux,
Haiku, and Firefox installed through Flatpak.

> **Status:** v1 is an initial, best-effort release. Firefox policy
> support varies by Firefox version, package format, and operating
> system. Always verify the result in `about:policies`.

## Features

MelFox's configuration aims to:

-   Set the homepage to `about:blank`.
-   Open blank pages for new tabs.
-   Add DuckDuckGo Lite and Startpage as search engines.
-   Set DuckDuckGo Lite as the private-window search engine.
-   Set Startpage as the regular search engine on Windows.
-   Leave the regular default search engine unchanged on other
    platforms.
-   Force-install the following Firefox extensions:
    -   [uBlock
        Origin](https://addons.mozilla.org/firefox/addon/ublock-origin/)
    -   [Privacy
        Badger](https://addons.mozilla.org/firefox/addon/privacy-badger17/)
    -   [Bitwarden](https://addons.mozilla.org/firefox/addon/bitwarden-password-manager/)
    -   [SponsorBlock](https://addons.mozilla.org/firefox/addon/sponsorblock/)
    -   [Dark
        Reader](https://addons.mozilla.org/firefox/addon/darkreader/)
    -   [DeArrow](https://addons.mozilla.org/firefox/addon/dearrow/)
-   Disable Pocket and several sponsored, recommendation, and AI-related
    features through Firefox policies where supported.

MelFox does not disable Firefox updates, certificate validation, Safe
Browsing, or other core browser security features.

## Requirements

-   Python 3.8 or newer.
-   Mozilla Firefox.
-   Administrator/root permissions when writing to a system-wide Firefox
    installation or system-wide Flatpak installation.
-   The `flatpak` command for Flatpak detection.

MelFox uses Python's standard library; no third-party Python packages
are required.

## Installation and usage

1.  Save the script as `melfox.py`.
2.  Close Firefox before applying the configuration.
3.  Run the script using the command appropriate for your platform.

### Windows

``` powershell
py melfox.py
```

If Firefox is installed in a protected directory, open PowerShell with
administrator privileges.

### macOS

``` bash
python3 melfox.py
```

If Firefox is installed in `/Applications`, you may need to run the
command with appropriate administrator permissions.

### Linux

``` bash
python3 melfox.py
```

For a system-wide Firefox installation, you may need:

``` bash
sudo python3 melfox.py
```

The script currently looks for Firefox in common installation locations
and writes the policy file to the installation's `distribution`
directory.

### Haiku

``` bash
python3 melfox.py
```

Haiku support is best-effort. The script checks common Firefox
locations, but Firefox packaging and Enterprise Policy support can
differ between Haiku builds. If automatic detection fails, see [Manual
installation path](#manual-installation-path).

### Flatpak

For a system-wide Flatpak installation, run:

``` bash
sudo python3 melfox.py
```

For a per-user Flatpak installation, run it as the user who installed
Firefox:

``` bash
python3 melfox.py
```

MelFox detects the Flatpak installation using the Flatpak CLI and
targets the `org.mozilla.firefox.systemconfig` extension directory for
the detected architecture and branch.

The expected policy-file layout is:

``` text
<Flatpak installation>/extension/
└── org.mozilla.firefox.systemconfig/
    └── <architecture>/
        └── <branch>/
            └── policies/
                └── policies.json
```

Typical system-wide and per-user extension roots are:

``` text
/var/lib/flatpak/extension/
```

``` text
~/.local/share/flatpak/extension/
```

The Firefox Flatpak package must expose the
`org.mozilla.firefox.systemconfig` extension point. MelFox creates the
host-side policy directory and file; it does not install or modify the
Firefox Flatpak itself.

If multiple Flatpak installations contain Firefox, check which
installation `flatpak info` resolves before running MelFox. The script's
automatic detection may not select the installation you intended.

To skip Flatpak detection and use a native Firefox installation on
Linux:

``` bash
FIREFOX_FLATPAK=0 python3 melfox.py
```

## Manual installation path

If MelFox cannot detect Firefox, set `FIREFOX_DIR` to the Firefox
installation directory.

Linux example:

``` bash
FIREFOX_DIR="/opt/firefox" python3 melfox.py
```

Windows PowerShell example:

``` powershell
$env:FIREFOX_DIR = "C:\Program Files\Mozilla Firefox"
py melfox.py
```

macOS example:

``` bash
FIREFOX_DIR="/Applications/Firefox.app" python3 melfox.py
```

`FIREFOX_DIR` is intended for native installations. Flatpak uses its own
detection path.

## Verify the configuration

After the script completes:

1.  Start or restart Firefox.
2.  Open `about:policies`.
3.  Select the **Active** tab and check which policies were applied.
4.  Select the **Errors** tab and review any rejected or unsupported
    policies.
5.  Open `about:addons` and confirm that the six extensions have been
    installed.
6.  Check **Settings → Search** to verify the available search engines
    and defaults.

Policy support is version-dependent. In particular, search-engine policy
support and newer AI-related controls may require a recent Firefox
release. If a policy appears under Errors, consult Mozilla's current
policy reference rather than assuming that the setting took effect.

## Important behavior and limitations

### Force-installed extensions

The six extensions are configured with Firefox's `force_installed` mode.
Firefox manages these extensions, and users generally cannot disable or
remove them through the normal Add-ons interface while the policy
remains active.

Extension installation requires Firefox to be able to reach the relevant
Mozilla Add-ons download endpoints. The script writes policy
configuration; Firefox performs the extension downloads.

### Search engines

The script registers DuckDuckGo Lite and Startpage by name. The private
default is configured using Firefox's `SearchEngines.DefaultPrivate`
policy. On Windows, the regular default is set to Startpage.

On macOS, Linux, and Haiku, MelFox does not set the regular default
search engine.

### Blank new tabs

Firefox's `NewTabPage` policy set to `false` makes new tabs open a blank
page rather than Firefox Home. The homepage policy separately sets
`about:blank`.

### AI and recommendations

Firefox's enterprise policy set changes over time. MelFox includes
policy entries intended to disable AI-related functionality, Pocket,
sponsored content, and recommendations. Not every policy key is
recognized by every Firefox version. Check `about:policies` for errors
and verify the behavior in the installed browser.

### Platform support

-   **Windows and macOS:** Uses the conventional Firefox application
    policy directory.
-   **Linux:** Uses the detected Firefox installation's `distribution`
    directory.
-   **Flatpak:** Uses the Flatpak `org.mozilla.firefox.systemconfig`
    extension directory.
-   **Haiku:** Best-effort detection and policy placement; compatibility
    depends on the Firefox port.

Other packaging formats, including Snap, may require a
packaging-specific policy location and are not explicitly supported by
this v1 script.

## Backups and reverting

If a `policies.json` file already exists, MelFox creates a backup named:

``` text
policies.json.backup
```

To revert the policy file, close Firefox and restore that backup to its
original location. If no backup existed before MelFox ran, remove the
generated `policies.json` file to remove the policies.

For Flatpak, restore or remove the file in the
`org.mozilla.firefox.systemconfig` extension directory.

Do not delete the entire Firefox profile to undo MelFox. The script is
intended to configure policies, not erase bookmarks, history, passwords,
or other profile data.

## Project structure

A minimal v1 layout:

``` text
MelFox/
├── README.md
└── melfox.py
```

## References

-   [Firefox Enterprise Policy
    documentation](https://firefox-admin-docs.mozilla.org/reference/policies/)
-   [Mozilla: Configuring Firefox
    policies](https://firefox-admin-docs.mozilla.org/guides/policies-configuration/)
-   [Mozilla: SearchEngines
    policy](https://firefox-admin-docs.mozilla.org/reference/policies/searchengines/)
-   [Mozilla: NewTabPage
    policy](https://firefox-admin-docs.mozilla.org/reference/policies/newtabpage/)
-   [Mozilla: ExtensionSettings
    policy](https://firefox-admin-docs.mozilla.org/reference/policies/extensions/)
-   [Flatpak extension
    documentation](https://docs.flatpak.org/en/latest/extension.html)

## License

No license is specified for MelFox v1. Add a `LICENSE` file before
redistributing the project if you want to grant others explicit reuse,
modification, or distribution rights.
