from __future__ import annotations

import html
import io
import json
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ebooklib import epub
from PIL import Image, ImageOps


class EpubGenerator:
    def __init__(self, timezone="Asia/Ho_Chi_Minh", image_timeout=15):
        self.timezone = ZoneInfo(timezone)
        self.image_timeout = image_timeout
        self.image_size = (480, 800)

    def generate(self, article_pool, output_path, sources, title="YOUR NEWS", edition_time="07:00", article_ids: set[str] | None = None):
        pool=Path(article_pool); output=Path(output_path); source_map={s["id"]:s for s in sources}; allowed_ids=article_ids; articles=[]
        for path in sorted(pool.glob("*/*.json")):
            if path.name.endswith(".meta.json"): continue
            article=json.loads(path.read_text(encoding="utf-8"))
            if allowed_ids is not None and article.get("id") not in allowed_ids: continue
            source=source_map.get(article.get("source_id"), {})
            if source.get("status", "active") != "active": continue
            articles.append(self._apply_policy(article, source.get("policy", {})))
        articles.sort(key=lambda a:a.get("published_at") or "", reverse=True)

        now=datetime.now(self.timezone); date_label=now.strftime("%-d %B %Y")
        book=epub.EpubBook(); book.set_identifier(f"tangthu-news-{now:%Y%m%d}"); book.set_title(f"{title} at {edition_time} — {date_label}"); book.set_language("vi"); book.add_author("Tàng Thư"); book.add_metadata("DC","publisher","Tàng Thư"); book.add_metadata("DC","description",f"{title} at {edition_time} — {date_label}")
        edition=epub.EpubHtml(title="Edition",file_name="edition.xhtml",lang="vi"); edition.content=self._edition_html(title,edition_time,date_label,len(articles)); book.add_item(edition)

        article_chapters=[]; image_root=output.parent / ".epub-images"
        if image_root.exists(): shutil.rmtree(image_root,ignore_errors=True)
        image_root.mkdir(parents=True,exist_ok=True)
        for index,article in enumerate(articles,start=1):
            chapter=epub.EpubHtml(title=article["title"] or f"Article {index}",file_name=f"article-{index}.xhtml",lang="vi")
            image_item=None
            if article.get("image"):
                image_item=self._download_image(article["image"], article.get("url") or article.get("canonical_url"), image_root, index)
                if image_item:
                    book.add_item(image_item)
            chapter.content=self._article_html(article,index,image_item)
            book.add_item(chapter); article_chapters.append(chapter)

        toc_page=epub.EpubHtml(title="Mục lục",file_name="toc.xhtml",lang="vi"); toc_page.content=self._toc_html(articles,source_map); book.add_item(toc_page)
        source_groups={}
        for chapter,article in zip(article_chapters,articles): source_groups.setdefault(article.get("source_id") or "Nguồn khác",[]).append(chapter)
        book.toc=tuple([epub.Link("toc.xhtml","Mục lục","toc-page")]+[epub.Section(source_map.get(source_id,{}).get("name") or source_id,tuple(chapters)) for source_id,chapters in source_groups.items()])
        book.add_item(epub.EpubNcx()); book.add_item(epub.EpubNav()); book.spine=["nav",edition,toc_page,*article_chapters]
        output.parent.mkdir(parents=True,exist_ok=True); epub.write_epub(str(output),book); shutil.rmtree(image_root,ignore_errors=True); return output

    @staticmethod
    def _apply_policy(article,source_policy):
        mode=source_policy.get("mode","excerpt"); result=dict(article); body=result.get("body") or ""
        if mode=="metadata_only": result["body"]=""
        elif mode=="excerpt": result["body"]=body[:800].strip()
        elif mode in {"full_article","licensed"}: result["body"]=body
        else: result["body"]=body[:800].strip()
        return result

    @staticmethod
    def _edition_html(title,edition_time,date_label,article_count):
        return f"""<html><head><title>{html.escape(title)}</title></head><body><h1>{html.escape(title)}</h1><p>{html.escape(edition_time)}</p><p>{html.escape(date_label)}</p><p>{article_count} articles</p></body></html>"""

    @staticmethod
    def _toc_html(articles,source_map):
        items=[]; current_source=None
        for index,article in enumerate(articles,start=1):
            source_id=article.get("source_id") or "Nguồn khác"; source=source_map.get(source_id,{}).get("name") or source_id; title=html.escape(article.get("title") or f"Article {index}")
            if source != current_source:
                if current_source is not None: items.append("</ul>")
                items.append(f"<li><strong>{html.escape(source)}</strong><ul>"); current_source=source
            items.append(f'<li><a href="article-{index}.xhtml">{title}</a></li>')
        if current_source is not None: items.append("</ul></li>")
        return """<html><head><title>Mục lục</title></head><body><h1>Mục lục</h1><ul>"""+"\n".join(items)+"""</ul></body></html>"""

    def _download_image(self,url,referer,image_root,index):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36","Referer":referer or "https://vnexpress.net/"})
            with urllib.request.urlopen(req,timeout=self.image_timeout) as response:
                raw=response.read()
            with Image.open(io.BytesIO(raw)) as src:
                image=ImageOps.exif_transpose(src).convert("RGB")
                max_w, max_h = self.image_size
                scale = min(max_w / image.width, max_h / image.height, 1.0)
                if scale < 1.0:
                    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
                canvas=Image.new("L",self.image_size,255)
                gray=image.convert("L")
                x=(self.image_size[0]-gray.width)//2; y=(self.image_size[1]-gray.height)//2
                canvas.paste(gray,(x,y))
                path=image_root/f"article-{index}.bmp"; canvas.save(path,format="BMP")
            return epub.EpubImage(uid=f"image-{index}",file_name=f"images/article-{index}.bmp",media_type="image/bmp",content=path.read_bytes())
        except Exception as exc:
            print(f"image download/convert failed {url}: {exc}")
            return None

    def _article_html(self,article,index,image_item=None):
        title=html.escape(article.get("title") or "Untitled",quote=False); author=html.escape(article.get("author") or "",quote=False); source=html.escape(article.get("source_id") or "",quote=False); published=html.escape(article.get("published_at") or "",quote=False); url=html.escape(article.get("canonical_url") or article.get("url") or "")
        body=article.get("body") or ""
        paragraphs="\n".join(f"<p>{html.escape(line.strip(),quote=False)}</p>" for line in body.splitlines() if line.strip())
        if not paragraphs and body: paragraphs=f"<p>{html.escape(body,quote=False)}</p>"
        meta=" · ".join(x for x in (source,published,author) if x)
        image_html=f'<p><img src="{html.escape(image_item.file_name)}" alt="" /></p>' if image_item else ""
        link=f'<p><a href="{url}">Original article</a></p>' if url else ""
        return f"""<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{meta}</p>{image_html}{paragraphs}{link}</body></html>"""
