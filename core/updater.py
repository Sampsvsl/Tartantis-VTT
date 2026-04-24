import urllib.request
import json
import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict

try:
    from packaging.version import Version
    def _is_newer(latest: str, current: str) -> bool:
        return Version(latest) > Version(current)
except ImportError:
    def _is_newer(latest: str, current: str) -> bool:
        def parse(v):
            return tuple(int(x) for x in v.strip().split('.') if x.isdigit())
        return parse(latest) > parse(current)

REPO_OWNER = "Sampsvsl"
REPO_NAME = "Tartantis-VTT"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


def _platform_key(platform_hint: Optional[str] = None) -> str:
    p = (platform_hint or sys.platform).lower()
    if p.startswith('win'):
        return 'windows'
    if p == 'darwin' or p.startswith('mac'):
        return 'macos'
    return 'linux'


def _pick_asset_url(assets: List[Dict[str, str]], platform_hint: Optional[str] = None) -> Optional[str]:
    key = _platform_key(platform_hint)
    targets = {
        'windows': ['instalador_tartantisvtt.exe', 'tartantisvtt.exe'],
        'linux': ['tartantisvtt-x86_64.appimage'],
        'macos': ['tartantisvtt-macos.zip'],
    }
    names = targets.get(key, [])
    for wanted in names:
        for asset in assets:
            aname = (asset.get('name') or '').strip().lower()
            if aname == wanted:
                return asset.get('browser_download_url')
    return None

def get_current_version(base_dir: Path) -> str:
    version_file = base_dir / 'VERSION'
    if version_file.exists():
        return version_file.read_text(encoding='utf-8').strip()
    return "0.0.0"

def get_latest_version(platform_hint: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (tag_name, download_url) or (None, None) on error.
    download_url is platform-specific when a matching asset exists, otherwise release page URL.
    """
    try:
        req = urllib.request.Request(GITHUB_API_URL)
        req.add_header('User-Agent', 'TartantisVTT-Updater')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            raw_tag = data.get('tag_name', '').strip()
            tag = raw_tag[1:] if raw_tag.lower().startswith('v') else raw_tag
            page_url = data.get('html_url', f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest")
            assets = data.get('assets', []) or []
            url = _pick_asset_url(assets, platform_hint) or page_url
            return tag, url
    except Exception as e:
        print(f"Error checking for updates: {e}")
        return None, None

def check_for_updates(base_dir: Path, platform_hint: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Returns (update_available, latest_version, download_url)
    """
    current = get_current_version(base_dir)
    latest, url = get_latest_version(platform_hint)
    
    if latest and _is_newer(latest, current):
        return True, latest, url
    
    return False, current, url

if __name__ == "__main__":
    # Test
    base = Path(__file__).parent.parent
    available, ver, uurl = check_for_updates(base)
    print(f"Available: {available}, Version: {ver}, URL: {uurl}")
