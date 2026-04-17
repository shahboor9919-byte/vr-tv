import aiohttp
import re
from typing import List, Dict

async def parse_m3u_fast(url: str) -> List[Dict]:
    """
    تحليل M3U سريع جداً باستخدام regex.
    """
    channels = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return []
                content = await response.text()
                
                # Regex patterns for M3U parsing
                # This matches #EXTINF lines and the following URL
                pattern = re.compile(r'#EXTINF:.*?,(.*?)\n(http.*?)(?=\n#EXTINF|$)', re.DOTALL)
                matches = pattern.findall(content)
                
                for name, stream_url in matches:
                    channels.append({
                        "name": name.strip(),
                        "streams": [stream_url.strip()],
                        "logo": "", # Can be enhanced to extract tvg-logo
                        "source": url
                    })
    except Exception:
        pass
    return channels
