from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CompetitorAnalysis(BaseModel):
    strengths: List[str] = []
    weaknesses: List[str] = []
    unique_offers: List[str] = []
    recommendations: List[str] = []
    summary: str = ""
    # Опционально: заполняется только для парсинга сайтов и анализа изображений
    design_score: Optional[int] = None  # 0-10 оценка визуального стиля
    animation_potential: Optional[str] = None  # Потенциал анимаций/визуальных приёмов


class ImageAnalysis(BaseModel):
    description: str = ""
    marketing_insights: List[str] = []
    visual_style_score: int = 0
    visual_style_analysis: str = ""
    recommendations: List[str] = []


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10)


class TextAnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ParseDemoRequest(BaseModel):
    url: HttpUrl


class ParsedContent(BaseModel):
    url: str
    title: Optional[str] = None
    h1: Optional[str] = None
    first_paragraph: Optional[str] = None
    analysis: Optional[CompetitorAnalysis] = None


class ParseDemoResponse(BaseModel):
    success: bool
    data: Optional[ParsedContent] = None
    error: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[ImageAnalysis] = None
    error: Optional[str] = None


class HistoryItem(BaseModel):
    request_type: str
    request_summary: str
    response_summary: str


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int

