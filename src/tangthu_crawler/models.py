from dataclasses import dataclass
from datetime import datetime
@dataclass(frozen=True)
class ArticleRef:
    source_id: str
    url: str
    discovered_at: datetime
