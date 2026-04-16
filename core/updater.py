import urllib.request
import json
from pathlib import Path
from typing import Tuple, Optional

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

def get_current_version(base_dir: Path) -> str:
    version_file = base_dir / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"

def get_latest_version() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (tag_name, download_url) or (None, None) on error.
    """
    try:
        req = urllib.request.Request(GITHUB_API_URL)
        req.add_header('User-Agent', 'TartantisVTT-Updater')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            tag = data.get('tag_name', '').replace('v', '')
            url = data.get('html_url', f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest")
            return tag, url
    except Exception as e:
        print(f"Error checking for updates: {e}")
        return None, None

def check_for_updates(base_dir: Path) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Returns (update_available, latest_version, download_url)
    """
    current = get_current_version(base_dir)
    latest, url = get_latest_version()
    
    if latest and _is_newer(latest, current):
        return True, latest, url
    
    return False, current, url

if __name__ == "__main__":
    # Test
    base = Path(__file__).parent.parent
    available, ver, uurl = check_for_updates(base)
    print(f"Available: {available}, Version: {ver}, URL: {uurl}")
