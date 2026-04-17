import os
from dotenv import load_dotenv

load_dotenv()

def get_all_provider_urls() -> list[str]:
    urls = []
    i = 1
    while True:
        url = os.getenv(f"PROVIDER_{i}_URL")
        if not url:
            break
        urls.append(url)
        i += 1
    return urls
