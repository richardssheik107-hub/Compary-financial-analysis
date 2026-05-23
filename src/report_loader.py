from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from src.research_models import ResearchDocument, SourceNote

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
COMPANY_INFO_DIR = ROOT / "data" / "company_info"
INDUSTRY_INFO_DIR = ROOT / "data" / "industry_info"
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"\s+", "", normalized)


def _guess_source_type(path: Path, content: str) -> str:
    text = _normalize(path.name + "\n" + content[:1000])
    if any(key in text for key in ["研报", "券商", "评级", "盈利预测"]):
        return "研报观点"
    if any(key in text for key in ["年报", "年度报告", "季报", "季度报告"]):
        return "年报文本"
    return "本地资料"


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf_file(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    chunks: list[str] = []
    for page in reader.pages[:30]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.strip()
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _read_content(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _read_pdf_file(path)
    return _read_text_file(path)


def _matches_company(path: Path, content: str, company_name: str, stock_code: str) -> bool:
    haystack = _normalize(path.name + "\n" + content[:3000])
    names = [_normalize(company_name), _normalize(stock_code)]
    compact_company = _normalize(company_name).replace("a", "")
    if compact_company and compact_company not in names:
        names.append(compact_company)
    return any(item and item in haystack for item in names)


def _scan_dir_documents(
    base_dir: Path, company_name: str, stock_code: str, fallback_source_type: str
) -> tuple[list[ResearchDocument], dict]:
    if not base_dir.exists():
        return [], {"scanned": 0, "matched": 0, "pdf_scanned": 0, "pdf_empty": 0}
    results: list[ResearchDocument] = []
    stats = {"scanned": 0, "matched": 0, "pdf_scanned": 0, "pdf_empty": 0}
    for path in base_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.name.lower() == "readme.md":
            continue
        stats["scanned"] += 1
        if path.suffix.lower() == ".pdf":
            stats["pdf_scanned"] += 1
        content = _read_content(path).strip()
        if not content:
            if path.suffix.lower() == ".pdf":
                stats["pdf_empty"] += 1
            continue
        if not _matches_company(path, content, company_name, stock_code):
            continue
        stats["matched"] += 1
        source_type = _guess_source_type(path, content)
        if source_type == "本地资料":
            source_type = fallback_source_type
        results.append(
            ResearchDocument(
                title=path.stem,
                source_type=source_type,
                content=content[:8000],
                file_path=str(path),
            )
        )
    return results, stats


def load_company_documents(company_name: str, stock_code: str) -> list[ResearchDocument]:
    if not REPORT_DIR.exists():
        return []
    docs, _ = _scan_dir_documents(REPORT_DIR, company_name, stock_code, "本地资料")
    return docs


def load_research_documents(company_name: str, stock_code: str) -> tuple[list[ResearchDocument], dict]:
    report_docs, report_stats = _scan_dir_documents(REPORT_DIR, company_name, stock_code, "本地资料")
    company_docs, company_stats = _scan_dir_documents(COMPANY_INFO_DIR, company_name, stock_code, "公司资料")
    industry_docs, industry_stats = _scan_dir_documents(INDUSTRY_INFO_DIR, company_name, stock_code, "行业资料")
    all_docs = [*report_docs, *company_docs, *industry_docs]
    summary = {
        "reports": len(report_docs),
        "company_info": len(company_docs),
        "industry_info": len(industry_docs),
        "total": len(all_docs),
        "scanned_files": int(report_stats["scanned"] + company_stats["scanned"] + industry_stats["scanned"]),
        "matched_files": int(report_stats["matched"] + company_stats["matched"] + industry_stats["matched"]),
        "pdf_scanned": int(report_stats["pdf_scanned"] + company_stats["pdf_scanned"] + industry_stats["pdf_scanned"]),
        "pdf_empty": int(report_stats["pdf_empty"] + company_stats["pdf_empty"] + industry_stats["pdf_empty"]),
        "matched_titles": [doc.title for doc in all_docs[:8]],
    }
    return all_docs, summary


def _query_terms(query: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", query or "").lower()
    terms = re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", normalized)
    stopwords = {"公司", "分析", "研究", "情况", "怎么样", "哪个", "比较", "对比", "如何", "以及"}
    return [t for t in terms if t not in stopwords]


def retrieve_relevant_passages(
    documents: list[ResearchDocument], query: str, top_k: int = 8
) -> list[tuple[ResearchDocument, str]]:
    if not documents:
        return []
    terms = _query_terms(query)
    ranked: list[tuple[int, ResearchDocument, str]] = []
    for doc in documents:
        sentences = re.split(r"[。！？\n]+", doc.content)
        for sentence in sentences:
            text = sentence.strip()
            if len(text) < 10:
                continue
            score = 0
            if terms:
                lowered = text.lower()
                score += sum(1 for t in terms if t in lowered)
            if doc.source_type == "年报文本":
                score += 1
            if doc.source_type == "研报观点":
                score += 1
            if score > 0:
                ranked.append((score, doc, text))
    ranked.sort(key=lambda x: x[0], reverse=True)
    selected: list[tuple[ResearchDocument, str]] = []
    seen: set[tuple[str, str]] = set()
    for _, doc, text in ranked:
        key = (doc.title, text)
        if key in seen:
            continue
        seen.add(key)
        selected.append((doc, text))
        if len(selected) >= top_k:
            break
    return selected


def unsupported_source_note() -> SourceNote:
    return SourceNote(
        source_type="资料边界",
        title="本地资料加载说明",
        detail="当前版本支持 txt/md/pdf。若 PDF 为扫描版，可能提取不到文本。",
        file_path=str(REPORT_DIR),
    )
