from datetime import datetime
import os
from zoneinfo import ZoneInfo
from .article_pool import ArticlePool
from .config import ROOT,load_settings
from .crawler import article_id,crawl
from .discovery import SourceDiscovery
from .epub import EpubGenerator
from .extractor import ArticleExtractor
from .registry import SourceRegistry
from .validator import validate_epub
from .drive_upload import upload_epub

def _is_today_or_undated(published_at,timezone_name):
    if not published_at: return True
    try: published=datetime.fromisoformat(published_at.replace("Z","+00:00"))
    except ValueError: return True
    tz=ZoneInfo(timezone_name); today=datetime.now(tz).date()
    if published.tzinfo is None: return published.date()==today
    return published.astimezone(tz).date()==today

def run():
    settings=load_settings(); timezone_name=settings.get("timezone","Asia/Ho_Chi_Minh")
    registry=SourceRegistry(); active_sources=[s for s in registry.list_sources() if s.get("status")=="active"]
    output_dir=ROOT/settings.get("storage",{}).get("article_pool","data/article_pool")
    pool=ArticlePool(output_dir); extractor=ArticleExtractor(); edition_article_ids=set()
    for source in active_sources:
        try: refs=SourceDiscovery(source,settings).discover(); print(f"{source['id']}: discovered {len(refs)} article URLs")
        except Exception as exc: print(f"{source['id']}: discovery failed: {exc}"); continue
        try: crawl(refs,source,settings,output_dir)
        except Exception as exc: print(f"{source['id']}: crawl failed: {exc}"); continue
        kept=dropped_old=0
        for ref in refs:
            item_id=article_id(ref.url); html_path=pool.html_path(ref.source_id,item_id)
            if not html_path.exists(): print(f"{source['id']}: crawl missing {ref.url}"); continue
            try:
                article=extractor.extract(html_path,ref.url,source)
                article["id"]=item_id; article["source_id"]=ref.source_id; pool.write_article(article)
                if _is_today_or_undated(article.get("published_at"),timezone_name): edition_article_ids.add(item_id); kept+=1
                else: dropped_old+=1
            except Exception as exc: print(f"{source['id']}: extraction failed {ref.url}: {exc}")
        print(f"{source['id']}: edition kept={kept}, dropped_old={dropped_old}")
    epub_path=ROOT/settings.get("storage",{}).get("editions","data/editions")/"0neNews.epub"
    EpubGenerator(timezone=timezone_name).generate(article_pool=output_dir,output_path=epub_path,sources=active_sources,title=settings.get("edition",{}).get("title","YOUR NEWS"),edition_time=settings.get("edition",{}).get("time","07:00"),article_ids=edition_article_ids)
    validate_epub(epub_path); print(f"EPUB validated: {epub_path}")
    if os.getenv("TANGTHU_UPLOAD_ENABLED","false").strip().lower()=="true":
        result=upload_epub(epub_path,filename=settings.get("drive_upload",{}).get("filename","0neNews.epub")); print(f"Drive upload complete: {result.get('filename','0neNews.epub')} (file_id={result.get('file_id','unknown')}, operation={result.get('operation','unknown')})")
    else: print("Drive upload skipped: TANGTHU_UPLOAD_ENABLED is not true.")

if __name__=="__main__": run()
