from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel
import hashlib

class Source(BaseModel):
    name: str
    url: str

class StartupContent(BaseModel):
    entity_name: str
    description: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    funding_total: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

class StartupRecord(BaseModel):
    schema_version: str = "1.0"
    record_type: Literal["STARTUP"] = "STARTUP"
    record_id: str = ""
    source: Source
    content: StartupContent
    collected_at: datetime = None
    canonical_entity: Optional[str] = None

    def model_post_init(self, __context):
        if not self.collected_at:
            self.collected_at = datetime.utcnow()
        if not self.record_id:
            key = f"{self.source.url}:{self.content.entity_name}"
            self.record_id = hashlib.sha256(key.encode()).hexdigest()[:16]

class ProductContent(BaseModel):
    product_name: str
    startup_name: Optional[str] = None
    description: Optional[str] = None
    pricing_model: Optional[Literal["FREE", "FREEMIUM", "PAID", "ENTERPRISE"]] = None
    website: Optional[str] = None

class ProductRecord(BaseModel):
    schema_version: str = "1.0"
    record_type: Literal["PRODUCT"] = "PRODUCT"
    record_id: str = ""
    source: Source
    content: ProductContent
    collected_at: datetime = None
    canonical_entity: Optional[str] = None

    def model_post_init(self, __context):
        if not self.collected_at:
            self.collected_at = datetime.utcnow()
        if not self.record_id:
            key = f"{self.source.url}:{self.content.product_name}"
            self.record_id = hashlib.sha256(key.encode()).hexdigest()[:16]

class PaperContent(BaseModel):
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    paper_url: str
    github_url: Optional[str] = None
    github_stars: Optional[int] = None
    published_date: Optional[datetime] = None

class PaperRecord(BaseModel):
    schema_version: str = "1.0"
    record_type: Literal["RESEARCH_PAPER"] = "RESEARCH_PAPER"
    record_id: str = ""
    source: Source
    content: PaperContent
    collected_at: datetime = None

    def model_post_init(self, __context):
        if not self.collected_at:
            self.collected_at = datetime.utcnow()
        if not self.record_id:
            self.record_id = hashlib.sha256(self.content.paper_url.encode()).hexdigest()[:16]

class NewsContent(BaseModel):
    title: str
    summary: Optional[str] = None
    full_text: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    article_url: str

class NewsRecord(BaseModel):
    schema_version: str = "1.0"
    record_type: Literal["NEWS"] = "NEWS"
    record_id: str = ""
    source: Source
    content: NewsContent
    collected_at: datetime = None
    within_24h: bool = False

    def model_post_init(self, __context):
        if not self.collected_at:
            self.collected_at = datetime.utcnow()
        if not self.record_id:
            self.record_id = hashlib.sha256(self.content.article_url.encode()).hexdigest()[:16]

class JobContent(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    job_url: str

class JobRecord(BaseModel):
    schema_version: str = "1.0"
    record_type: Literal["JOB"] = "JOB"
    record_id: str = ""
    source: Source
    content: JobContent
    collected_at: datetime = None
    within_24h: bool = False

    def model_post_init(self, __context):
        if not self.collected_at:
            self.collected_at = datetime.utcnow()
        if not self.record_id:
            self.record_id = hashlib.sha256(self.content.job_url.encode()).hexdigest()[:16]

class EntityMapping(BaseModel):
    raw_name: str
    canonical_name: str
    entity_type: str
    source_url: str
    confidence: float
    resolved_at: datetime = None

    def model_post_init(self, __context):
        if not self.resolved_at:
            self.resolved_at = datetime.utcnow()