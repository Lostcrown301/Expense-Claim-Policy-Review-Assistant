from pydantic import BaseModel
from typing import List, Optional
from functools import lru_cache
from pathlib import Path
import re

class PolicySection(BaseModel):
    id: str
    title: str
    text: str

@lru_cache(maxsize=1)
def load_policy(path: Optional[str] = None) -> List[PolicySection]:
    if path is None:
        path = str(Path(__file__).parent.parent / "data" / "policy.md")
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    parts = re.split(r'^##\s+', content, flags=re.MULTILINE)
    
    sections = []
    for part in parts[1:]:
        lines = part.strip().split('\n', 1)
        heading = lines[0].strip()
        text = lines[1].strip() if len(lines) > 1 else ""
        
        heading_parts = heading.split(maxsplit=1)
        sec_id = heading_parts[0]
        title = heading_parts[1] if len(heading_parts) > 1 else ""
        
        sections.append(PolicySection(id=sec_id, title=title, text=text))
        
    return sections

def get_section(section_id: str, path: Optional[str] = None) -> Optional[PolicySection]:
    sections = load_policy(path)
    for sec in sections:
        if sec.id == section_id:
            return sec
    return None

def _normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().lower()

def quote_exists_in_section(section_id: str, quote: str, path: Optional[str] = None) -> bool:
    sec = get_section(section_id, path)
    if not sec:
        return False
    
    norm_quote = _normalize_whitespace(quote)
    norm_text = _normalize_whitespace(sec.text)
    
    return norm_quote in norm_text
