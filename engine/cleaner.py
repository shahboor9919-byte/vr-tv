import re
from typing import List, Dict

def smart_category(name: str) -> str:
    name_lower = name.lower()
    
    # رياضة
    if any(x in name_lower for x in ["bein", "sport", "espn", "sky sport", "football", "basketball", "tennis"]):
        return "Sports"
    # أفلام
    if any(x in name_lower for x in ["movie", "cinema", "film", "hbo", "netflix", "prime"]):
        return "Movies"
    # أطفال
    if any(x in name_lower for x in ["kids", "cartoon", "disney", "nickelodeon", "baby"]):
        return "Kids"
    # أخبار
    if any(x in name_lower for x in ["news", "cnn", "bbc", "fox news", "sky news", "aljazeera"]):
        return "News"
    # عربية
    if any(x in name_lower for x in ["arab", "ksa", "egy", "dubai", "mbc", "rotana", "dubai", "abu dhabi"]):
        return "Arabic"
    return "General"

def clean_channels(raw_channels: List[Dict]) -> List[Dict]:
    """
    تنظيف القنوات: إزالة البيانات الفارغة، إعادة التصنيف، تعيين معرف فريد.
    """
    cleaned = []
    for idx, ch in enumerate(raw_channels):
        name = ch.get("name", "").strip()
        if not name:
            continue
        
        # إزالة الأحرف غير المرغوب فيها من الاسم
        name = re.sub(r'[^\w\s\u0600-\u06FF\-]', '', name)
        
        cleaned.append({
            "id": idx + 1,
            "name": name,
            "category": smart_category(name),
            "logo": ch.get("logo", ""),
            "streams": ch.get("streams", []),
            "source": ch.get("source", ""),
            "alive": False,      # يتم تحديثها عند الطلب
            "best_stream": None,
            "backup_streams": [],
            "score": 0
        })
    return cleaned
