import json
import urllib.request
import urllib.error
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ReleaseInfo:
    version: str
    html_url: str
    download_url: Optional[str]
    release_notes: str
    

class UpdateChecker:
    REPO_OWNER = "E7G"
    REPO_NAME = "simpleRPA"
    API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    
    def __init__(self, current_version: str = "0.1.0"):
        self._current_version = current_version
    
    def _parse_version(self, version: str) -> Tuple[int, ...]:
        clean_version = version.lstrip('v').split('-')[0]
        parts = clean_version.split('.')
        return tuple(int(p) for p in parts if p.isdigit())
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        try:
            parsed_v1 = self._parse_version(v1)
            parsed_v2 = self._parse_version(v2)
            
            for i in range(max(len(parsed_v1), len(parsed_v2))):
                p1 = parsed_v1[i] if i < len(parsed_v1) else 0
                p2 = parsed_v2[i] if i < len(parsed_v2) else 0
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            return 0
        except Exception:
            return 0
    
    def check_for_update(self, timeout: int = 10) -> Optional[ReleaseInfo]:
        try:
            request = urllib.request.Request(
                self.API_URL,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': f'{self.REPO_NAME}-UpdateChecker'
                }
            )
            
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', '')
            
            if self._compare_versions(self._current_version, latest_version) < 0:
                download_url = None
                assets = data.get('assets', [])
                for asset in assets:
                    if asset.get('name', '').endswith('.zip'):
                        download_url = asset.get('browser_download_url')
                        break
                
                return ReleaseInfo(
                    version=latest_version,
                    html_url=data.get('html_url', ''),
                    download_url=download_url,
                    release_notes=data.get('body', '')
                )
            
            return None
            
        except urllib.error.URLError as e:
            print(f"网络错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"检查更新失败: {e}")
            return None
    
    @property
    def current_version(self) -> str:
        return self._current_version
    
    @staticmethod
    def get_release_page_url() -> str:
        return f"https://github.com/E7G/simpleRPA/releases"
