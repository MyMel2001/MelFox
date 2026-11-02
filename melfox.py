
#!/usr/bin/env python3
"""
MelFox v1

Supported platforms:
    Windows
    macOS
    Linux
    Haiku (using "Haiku" script)
    Flatpak Firefox

Requirements:
    Python 3.8+
    Firefox
    Flatpak CLI (for Flatpak installations)

The script configures Firefox using Enterprise Policies.
It does not modify Firefox binaries or user data.

Run with administrator/root permissions when required.
"""

import os
import sys
import json
import shutil
import platform
import subprocess

from pathlib import Path


# ============================================================
# Configuration
# ============================================================

FLATPAK_APP_ID = "org.mozilla.firefox"
FLATPAK_EXTENSION_ID = "org.mozilla.firefox.systemconfig"

EXTENSIONS = {
    "uBlock0@raymondhill.net": {
        "name": "uBlock Origin",
        "url": "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi"
    },

    "jid1-MnnxcxisBPnSXQ@jetpack": {
        "name": "Privacy Badger",
        "url": "https://addons.mozilla.org/firefox/downloads/latest/privacy-badger17/latest.xpi"
    },

    "{446900e4-71c2-419f-a6a7-df9c091e268b}": {
        "name": "Bitwarden",
        "url": "https://addons.mozilla.org/firefox/downloads/latest/bitwarden-password-manager/latest.xpi"
    },

    "sponsorBlocker@ajay.app": {
        "name": "SponsorBlock",
        "url": "https://addons.mozilla.org/firefox/downloads/latest/sponsorblock/latest.xpi"
    },

    "addon@darkreader.org": {
        "name": "Dark Reader",
        "url": "https://addons.mozilla.org/firefox/downloads/latest/darkreader/latest.xpi"
    },

    "deArrow@ajay.app": {
        "name": "DeArrow",
        "url": "https://addons.mozilla.org/firefox/downloads/latest/dearrow/latest.xpi"
    }
}

SEARCH_ENGINES = [
    {
        "Name": "DuckDuckGo Lite",
        "Alias": "ddglite",
        "Method": "GET",
        "URLTemplate": "https://lite.duckduckgo.com/lite/?q={searchTerms}"
    },
    {
        "Name": "Startpage",
        "Alias": "startpage",
        "Method": "GET",
        "URLTemplate": "https://www.startpage.com/sp/search?query={searchTerms}"
    }
]


# ============================================================
# Utility functions
# ============================================================

def run_command(command):
    """Run a command and return its output, or None."""

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout.strip()

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def write_json(path, data):
    """Write JSON atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
        file.write("\n")

    temporary.replace(path)


def load_policies(path):
    """Load existing policies and preserve them."""

    if not path.exists():
        return {"policies": {}}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data.get("policies"), dict):
            raise ValueError("Invalid Firefox policy structure")

        backup = path.with_suffix(".json.backup")

        if not backup.exists():
            shutil.copy2(path, backup)

        return data

    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(
            f"Cannot safely load existing policies: {error}"
        )


# ============================================================
# Flatpak detection
# ============================================================

def find_flatpak_firefox():
    """
    Detect Flatpak Firefox.

    Uses Mozilla's systemconfig extension point:
    <installation>/extension/org.mozilla.firefox.systemconfig/
    <architecture>/<branch>/policies/policies.json
    """

    if os.environ.get("FIREFOX_FLATPAK", "auto").lower() == "0":
        return None

    location = run_command([
        "flatpak",
        "info",
        "--show-location",
        FLATPAK_APP_ID
    ])

    if not location:
        return None

    app_path = Path(location).resolve()
    parts = app_path.parts

    try:
        index = next(
            i for i in range(len(parts) - 3)
            if parts[i] == "app"
            and parts[i + 1] == FLATPAK_APP_ID
        )

    except StopIteration:
        print("ERROR: Could not determine Flatpak installation layout.")
        return None

    architecture = parts[index + 2]
    branch = parts[index + 3]

    # Determine the Flatpak installation root.
    installation_root = Path(*parts[:index])

    policy_directory = (
        installation_root
        / "extension"
        / FLATPAK_EXTENSION_ID
        / architecture
        / branch
        / "policies"
    )

    print("Detected Flatpak Firefox.")
    print(f"Architecture: {architecture}")
    print(f"Branch: {branch}")
    print(f"Installation root: {installation_root}")

    return policy_directory / "policies.json"


# ============================================================
# Native Firefox detection
# ============================================================

def find_native_firefox():
    """Find a conventional Firefox installation."""

    override = os.environ.get("FIREFOX_DIR")

    if override:
        path = Path(override).expanduser().resolve()

        if path.is_file():
            path = path.parent

        return path

    system = platform.system()

    if system == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
                / "Mozilla Firefox",

            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
                / "Mozilla Firefox",

            Path(os.environ.get("LOCALAPPDATA", ""))
                / "Mozilla Firefox"
        ]

        for path in candidates:
            if (path / "firefox.exe").exists():
                return path

    elif system == "Darwin":
        candidates = [
            Path("/Applications/Firefox.app"),
            Path.home() / "Applications/Firefox.app"
        ]

        for path in candidates:
            if (path / "Contents/MacOS/firefox").exists():
                return path

    else:
        executable = shutil.which("firefox")

        if executable:
            path = Path(executable).resolve()

            if path.is_file():
                return path.parent

        candidates = [
            Path("/usr/lib/firefox"),
            Path("/usr/lib64/firefox"),
            Path("/opt/firefox"),
            Path("/boot/system/apps/Firefox")
        ]

        for path in candidates:
            if path.exists():
                return path

    return None


def get_native_policy_file(install):
    """Get the native Firefox policy file location."""

    system = platform.system()

    if system == "Darwin":
        return (
            install
            / "Contents"
            / "Resources"
            / "distribution"
            / "policies.json"
        )

    if system == "Windows":
        return install / "distribution" / "policies.json"

    return install / "distribution" / "policies.json"


# ============================================================
# Firefox policy configuration
# ============================================================

def configure_policies(policy_file):
    """Create or update Firefox Enterprise Policies."""

    print(f"\nPolicy file: {policy_file}")

    try:
        policies = load_policies(policy_file)

    except RuntimeError as error:
        print(f"ERROR: {error}")
        return False

    config = policies["policies"]

    # --------------------------------------------------------
    # Homepage and New Tab
    # --------------------------------------------------------

    config["Homepage"] = {
        "URL": "about:blank",
        "StartPage": "homepage"
    }

    config["NewTabPage"] = False

    # --------------------------------------------------------
    # Extensions
    # --------------------------------------------------------

    extension_settings = config.setdefault(
        "ExtensionSettings", {}
    )

    for extension_id, extension in EXTENSIONS.items():
        extension_settings[extension_id] = {
            "installation_mode": "force_installed",
            "install_url": extension["url"]
        }

    # --------------------------------------------------------
    # Search engines
    # --------------------------------------------------------

    search = config.setdefault("SearchEngines", {})

    existing = search.get("Add", [])

    if not isinstance(existing, list):
        existing = []

    # Preserve unrelated custom search engines.
    existing = [
        engine for engine in existing
        if engine.get("Name") not in {
            "DuckDuckGo Lite",
            "Startpage"
        }
    ]

    search["Add"] = existing + SEARCH_ENGINES

    # Private windows on every platform.
    search["DefaultPrivate"] = "DuckDuckGo Lite"

    # Regular Windows browsing.
    if platform.system() == "Windows":
        search["Default"] = "Startpage"

    # --------------------------------------------------------
    # Disable AI features
    # --------------------------------------------------------

    config["AIControls"] = {
        "Default": {
            "Value": "blocked",
            "Locked": True
        }
    }

    config["GenerativeAI"] = {
        "Enabled": False
    }

    # --------------------------------------------------------
    # Disable Pocket
    # --------------------------------------------------------

    config["DisablePocket"] = True

    # --------------------------------------------------------
    # Remove Firefox Home clutter
    # --------------------------------------------------------

    config["FirefoxHome"] = {
        "Search": False,
        "TopSites": False,
        "SponsoredTopSites": False,
        "Highlights": False,
        "Stories": False,
        "SponsoredStories": False,
        "Snippets": False
    }

    # --------------------------------------------------------
    # Disable Firefox Suggest
    # --------------------------------------------------------

    config["FirefoxSuggest"] = {
        "WebSuggestions": False,
        "OnlineEnabled": False,
        "SponsoredSuggestions": False,
        "ImproveSuggest": False
    }

    # --------------------------------------------------------
    # Disable unnecessary recommendations
    # --------------------------------------------------------

    config["UserMessaging"] = {
        "ExtensionRecommendations": False,
        "FeatureRecommendations": False,
        "UrlbarInterventions": False,
        "SkipOnboarding": True,
        "MoreFromMozilla": False
    }

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:
        write_json(policy_file, policies)

    except OSError as error:
        print(f"ERROR: Could not save policies: {error}")
        return False

    print("Firefox policies successfully written.")

    return True


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 52)
    print("             FIREFOX DEBLOAT v2.1")
    print("=" * 52)

    print(f"Operating system: {platform.system()}")
    print(f"Architecture: {platform.machine()}")

    # Prefer Flatpak if installed.
    policy_file = find_flatpak_firefox()

    if policy_file is not None:
        installation_type = "Flatpak"

    else:
        install = find_native_firefox()

        if install is None:
            print("\nERROR: Firefox installation not found.")
            print("Set FIREFOX_DIR or check your installation.")
            sys.exit(1)

        policy_file = get_native_policy_file(install)
        installation_type = "Native"

        print(f"Firefox installation: {install}")

    print(f"Installation type: {installation_type}")

    # Apply configuration.
    if not configure_policies(policy_file):
        sys.exit(1)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nConfigured extensions:")

    for extension in EXTENSIONS.values():
        print(f"  [+] {extension['name']}")

    print("\nBrowser configuration:")
    print("  [+] about:blank homepage")
    print("  [+] Blank New Tab")
    print("  [+] DuckDuckGo Lite private search")

    if platform.system() == "Windows":
        print("  [+] Startpage regular search")

    print("  [+] AI features blocked")
    print("  [+] Pocket disabled")
    print("  [+] Sponsored content disabled")

    print("\nConfiguration complete!")
    print("Restart Firefox to apply changes.")
    print("Verify at about:policies")


if __name__ == "__main__":
    main()
