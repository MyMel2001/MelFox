
#!/usr/bin/env python3
"""
MelFox v1 — Haiku Firefox configuration backend

Configures Firefox through its user profile.
Does not modify Haiku's package-managed Firefox installation.
"""

import configparser
import json
import os
import shutil
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


# --------------------------------------------------
# Configuration
# --------------------------------------------------

FIREFOX_CONFIG = (
    Path.home()
    / "config/settings/Mozilla/Firefox"
)

EXTENSIONS = {
    "uBlock0@raymondhill.net": (
        "uBlock Origin",
        "https://addons.mozilla.org/firefox/downloads/latest/"
        "ublock-origin/latest.xpi",
    ),
    "jid1-MnnxcxisBPnSXQ@jetpack": (
        "Privacy Badger",
        "https://addons.mozilla.org/firefox/downloads/latest/"
        "privacy-badger17/latest.xpi",
    ),
    "{446900e4-71c2-419f-a6a7-df9c091e268b}": (
        "Bitwarden",
        "https://addons.mozilla.org/firefox/downloads/latest/"
        "bitwarden-password-manager/latest.xpi",
    ),
    "sponsorBlocker@ajay.app": (
        "SponsorBlock",
        "https://addons.mozilla.org/firefox/downloads/latest/"
        "sponsorblock/latest.xpi",
    ),
    "addon@darkreader.org": (
        "Dark Reader",
        "https://addons.mozilla.org/firefox/downloads/latest/"
        "darkreader/latest.xpi",
    ),
    "deArrow@ajay.app": (
        "DeArrow",
        "https://addons.mozilla.org/firefox/downloads/latest/"
        "dearrow/latest.xpi",
    ),
}


# --------------------------------------------------
# Profile discovery
# --------------------------------------------------

def find_firefox_profile():
    ini_path = FIREFOX_CONFIG / "profiles.ini"

    if not ini_path.is_file():
        raise FileNotFoundError(
            f"Firefox profiles.ini not found: {ini_path}"
        )

    ini = configparser.ConfigParser()
    ini.read(ini_path)

    profiles = [
        section for section in ini.sections()
        if section.startswith("Profile")
    ]

    if not profiles:
        raise RuntimeError("No Firefox profiles found.")

    # Prefer the profile explicitly marked as default.
    selected = next(
        (
            section for section in profiles
            if ini.getboolean(
                section, "Default", fallback=False
            )
        ),
        None,
    )

    # Some Firefox installations identify the default
    # profile through an Install section instead.
    if selected is None:
        for section in ini.sections():
            if not section.startswith("Install"):
                continue

            default_path = ini.get(
                section, "Default", fallback=None
            )

            if default_path:
                candidate = Path(default_path)

                if not candidate.is_absolute():
                    candidate = FIREFOX_CONFIG / candidate

                if candidate.is_dir():
                    return candidate.resolve()

    # Fall back to the first profile if only one exists.
    if selected is None and len(profiles) == 1:
        selected = profiles[0]

    if selected is None:
        raise RuntimeError(
            "Could not identify the default Firefox profile."
        )

    relative = ini.get(
        selected, "Path", fallback=None
    )

    if not relative:
        raise RuntimeError(
            f"No Path value in [{selected}]."
        )

    profile_path = Path(relative)

    if not ini.getboolean(
        selected, "IsRelative", fallback=True
    ):
        candidates = [profile_path]
    else:
        # Haiku installations can use a Profiles directory
        # even when the Path value omits that component.
        candidates = [
            FIREFOX_CONFIG / profile_path,
            FIREFOX_CONFIG / "Profiles" / profile_path,
        ]

    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not locate the profile directory. "
        f"Checked: {candidates}"
    )


# --------------------------------------------------
# Backup utilities
# --------------------------------------------------

def backup_file(path):
    if not path.exists():
        return

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    backup = path.with_name(
        f"{path.name}.melfox-backup-{timestamp}"
    )

    shutil.copy2(path, backup)
    print(f"Backed up: {backup}")


# --------------------------------------------------
# Firefox preferences
# --------------------------------------------------

PREFERENCES = {
    # Homepage and new tab
    "browser.startup.homepage": "about:blank",
    "browser.startup.page": 1,
    "browser.newtabpage.enabled": False,

    # Firefox Home
    "browser.newtabpage.activity-stream.showSearch": False,
    "browser.newtabpage.activity-stream.feeds.topsites": False,
    "browser.newtabpage.activity-stream.feeds.section.highlights": False,
    "browser.newtabpage.activity-stream.feeds.section.topstories": False,
    "browser.newtabpage.activity-stream.showSponsored": False,
    "browser.newtabpage.activity-stream.showSponsoredTopSites": False,

    # Pocket
    "extensions.pocket.enabled": False,

    # Recommendations and suggestions
    "browser.urlbar.suggest.topsites": False,
    "browser.urlbar.suggest.trending": False,
    "browser.urlbar.suggest.quicksuggest.sponsored": False,
    "browser.urlbar.suggest.quicksuggest.nonsponsored": False,
    "browser.urlbar.suggest.addons": False,
    "browser.urlbar.suggest.pocket": False,

    # Telemetry and studies
    "datareporting.healthreport.uploadEnabled": False,
    "datareporting.policy.dataSubmissionEnabled": False,
    "app.shield.optoutstudies.enabled": False,

    # Disable built-in AI chatbot integrations
    "browser.ml.chat.enabled": False,
    "browser.ml.chat.sidebar": False,
    "browser.ml.enable": False,
}


def configure_preferences(profile):
    user_js = profile / "user.js"

    backup_file(user_js)

    marker_start = "// BEGIN MELFOX MANAGED SETTINGS"
    marker_end = "// END MELFOX MANAGED SETTINGS"

    existing = ""

    if user_js.exists():
        existing = user_js.read_text(
            encoding="utf-8"
        )

    # Remove the previous MelFox-managed section.
    if marker_start in existing and marker_end in existing:
        before = existing.split(marker_start, 1)[0]
        after = existing.split(marker_end, 1)[1]
        existing = before + after

    lines = [
        marker_start,
        "// Generated by MelFox v1",
        "",
    ]

    for name, value in PREFERENCES.items():
        lines.append(
            f"user_pref({json.dumps(name)}, "
            f"{json.dumps(value)});"
        )

    lines.extend([
        "",
        marker_end,
        "",
    ])

    with user_js.open("w", encoding="utf-8") as file:
        file.write(existing.rstrip() + "\n\n")
        file.write("\n".join(lines))

    print("Configured Firefox preferences.")


# --------------------------------------------------
# Extension installation
# --------------------------------------------------

def install_extensions(profile):
    extension_dir = profile / "extensions"
    extension_dir.mkdir(parents=True, exist_ok=True)

    for extension_id, (name, url) in EXTENSIONS.items():
        destination = extension_dir / f"{extension_id}.xpi"

        if destination.exists():
            print(f"Already present: {name}")
            continue

        print(f"Downloading: {name}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MelFox/1.0 Firefox Configuration"
            },
        )

        try:
            with urllib.request.urlopen(
                request, timeout=60
            ) as response:
                data = response.read()

            if not data.startswith(b"PK"):
                raise RuntimeError(
                    "Downloaded file does not appear to be an XPI."
                )

            temporary = destination.with_suffix(".xpi.tmp")
            temporary.write_bytes(data)
            temporary.replace(destination)

            print(f"Installed: {name}")

        except Exception as error:
            print(f"Failed to install {name}: {error}")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    if sys.platform != "haiku":
        print("This backend is intended for Haiku.")
        sys.exit(1)

    print("MelFox v1 — Haiku")
    print("-----------------")

    profile = find_firefox_profile()

    print(f"Firefox profile: {profile}")

    configure_preferences(profile)
    install_extensions(profile)

    print()
    print("MelFox configuration completed.")
    print("Restart Firefox to apply the changes.")


if __name__ == "__main__":
    main()
