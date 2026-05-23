from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from src.research_models import ResearchDocument, SourceNote

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data" / "reports"
SUPPORTED_SUFFIXES = {".txt", ".md"}


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


def _matches_company(path: Path, content: str, company_name: str, stock_code: str) -> bool:
    haystack = _normalize(path.name + "\n" + content[:3000])
    names = [_normalize(company_name), _normalize(stock_code)]
    compact_company = _normalize(company_name).replace("a", "")
    if compact_company and compact_company not in names:
        names.append(compact_company)
    return any(item and item in haystack for item in names)


def load_company_documents(company_name: str, stock_code: str) -> list[ResearchDocument]:
    if not REPORT_DIR.exists():
        return []

    documents: list[ResearchDocument] = []
    for path in REPORT_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.name.lower() == "readme.md":
            continue
        content = _read_text_file(path).strip()
        if not content:
            continue
        if not _matches_company(path, content, company_name, stock_code):
            continue
        documents.append(
            ResearchDocument(
                title=path.stem,
                source_type=_guess_source_type(path, content),
                content=content[:8000],
                file_path=str(path),
            )
        )
    return documents


def _query_terms(query: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", query or "").lower()
    terms = re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", normalized)
    stopwords = {"公司", "分析", "研究", "情况", "怎么样", "哪个", "比较", "对比", "如何", "以及"}
    return [t for t in terms if t not in stopwords]


def retrieve_relevant_passages(documents: list[ResearchDocument], query: str, top_k: int = 8) -> list[tuple[ResearchDocument, str]]:
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
        detail="当前版本优先支持 txt/md；PDF 可在下一步接入解析。",
        file_path=str(REPORT_DIR),
    )
