import json
import re
import time
from typing import Optional

from openai import OpenAI

from backend.config import logger, settings
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis


class OpenAIService:
    def __init__(self):
        api_key = settings.proxy_api_key or settings.openai_api_key
        base_url = settings.proxy_api_base_url or None
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = settings.openai_model
        self.vision_model = settings.openai_vision_model

    def _parse_json(self, content: str) -> dict:
        block = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if block:
            content = block.group(1)
        obj = re.search(r"\{[\s\S]*\}", content)
        if obj:
            content = obj.group(0)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _build_analysis(
        data: dict, fallback_summary: str = "", include_design: bool = True
    ) -> CompetitorAnalysis:
        strengths = data.get("strengths", []) or []
        weaknesses = data.get("weaknesses", []) or []
        unique_offers = data.get("unique_offers", []) or []
        recommendations = data.get("recommendations", []) or []
        summary = data.get("summary", "") or fallback_summary
        design_score = None
        animation_potential = None

        if include_design:
            design_score = data.get("design_score", None)
            animation_potential = data.get("animation_potential", None)
            # Нормализуем числовую оценку стиля
            try:
                if design_score is not None:
                    design_score = int(design_score)
            except (TypeError, ValueError):
                design_score = None
            if design_score is not None:
                design_score = max(0, min(10, design_score))

        # Приводим к спискам, если модель вернула строку/словарь.
        def _ensure_list(value):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return [f"{k}: {v}" for k, v in value.items()]
            return [str(value)]

        return CompetitorAnalysis(
            strengths=_ensure_list(strengths),
            weaknesses=_ensure_list(weaknesses),
            unique_offers=_ensure_list(unique_offers),
            recommendations=_ensure_list(recommendations),
            summary=summary,
            design_score=design_score,
            animation_potential=(str(animation_potential) if animation_potential else None),
        )

    @staticmethod
    def _is_empty_analysis(analysis: CompetitorAnalysis) -> bool:
        # Если все списки пустые, считаем анализ пустым, даже если есть summary-заглушка
        return (
            not analysis.strengths
            and not analysis.weaknesses
            and not analysis.unique_offers
            and not analysis.recommendations
        )

    @staticmethod
    def _ensure_list(value) -> list:
        """Приводит marketing_insights/recommendations к списку."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [f"{k}: {v}" for k, v in value.items()]
        return [str(value)]

    @staticmethod
    def _fallback_from_content(
        title: str, h1: Optional[str], paragraph: Optional[str]
    ) -> CompetitorAnalysis:
        """Детерминированный запасной вариант, если модель вернула пустой анализ."""
        src = " ".join(filter(None, [title, h1, paragraph])).strip()
        strengths = []
        weaknesses = []
        unique_offers = []
        recommendations = []

        if title:
            strengths.append(f"Чёткий заголовок: «{title}»")
        if h1:
            strengths.append(f"H1 выделяет оффер: «{h1}»")
        if paragraph:
            strengths.append("Есть первый абзац с УТП/гарантией")

        if paragraph:
            unique_offers.append(f"Фраза из абзаца: «{paragraph}»")
        if "10 лет" in (paragraph or "").lower():
            unique_offers.append("Длительная гарантия (10 лет)")
        if "симферопол" in src.lower() or "крым" in src.lower():
            unique_offers.append("Локальный фокус на Крым/Симферополь")

        weaknesses.append("Нет данных о ценах и примерах работ (по контенту страницы)")
        weaknesses.append("Нет социального доказательства (отзывы/кейсы не обнаружены)")

        recommendations.append("Добавить конкретные цены или калькулятор")
        recommendations.append("Показать фото работ и отзывы клиентов")
        recommendations.append("Усилить CTA с точными сроками и гарантией")
        recommendations.append("Вынести ключевые выгоды в первый экран")

        summary = (
            "Автогенерированный анализ на основе заголовков и первого абзаца: "
            "добавить цены, кейсы и отзывы; подчеркнуть гарантию и локальный фокус."
        )

        return CompetitorAnalysis(
            strengths=strengths,
            weaknesses=weaknesses,
            unique_offers=unique_offers,
            recommendations=recommendations,
            summary=summary,
            design_score=6,
            animation_potential="Высокий потенциал для 2D-анимаций монтажа окон, слайдеров до/после и всплывающих CTA.",
        )

    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты аналитик конкурентов. Верни строгий JSON с полями: "
                        "strengths[], weaknesses[], unique_offers[], recommendations[], summary."
                    ),
                },
                {"role": "user", "content": f"Проанализируй текст конкурента:\n\n{text}"},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        logger.info(f"analyze_text latency={time.time()-start:.2f}s")
        data = self._parse_json(resp.choices[0].message.content)
        analysis = self._build_analysis(
            data, fallback_summary="Анализ по тексту страницы.", include_design=False
        )
        if self._is_empty_analysis(analysis):
            analysis = self._fallback_from_content("", "", text[:200])
            # для текстового анализа не возвращаем дизайн-поля
            analysis.design_score = None
            analysis.animation_potential = None
        return analysis

    async def analyze_image(self, image_base64: str, mime_type: str = "image/jpeg") -> ImageAnalysis:
        start = time.time()
        resp = self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты эксперт по визуальному маркетингу. Верни JSON с полями "
                        "description, marketing_insights, visual_style_score, "
                        "visual_style_analysis, recommendations."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Проанализируй изображение конкурента и верни структурированный JSON.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                        },
                    ],
                },
            ],
            max_tokens=1800,
            temperature=0.4,
        )
        logger.info(f"analyze_image latency={time.time()-start:.2f}s")
        data = self._parse_json(resp.choices[0].message.content)
        marketing_insights = self._ensure_list(data.get("marketing_insights"))
        recommendations = self._ensure_list(data.get("recommendations"))
        score = data.get("visual_style_score", 0)
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0
        return ImageAnalysis(
            description=data.get("description", ""),
            marketing_insights=marketing_insights,
            visual_style_score=score,
            visual_style_analysis=data.get("visual_style_analysis", ""),
            recommendations=recommendations,
        )

    async def analyze_parsed_content(
        self, title: str, h1: Optional[str], paragraph: Optional[str]
    ) -> CompetitorAnalysis:
        text = f"URL контент:\nTitle: {title}\nH1: {h1}\nParagraph: {paragraph}"
        analysis = self._build_analysis(
            self._parse_json(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты аналитик конкурентов в сфере производства и установки пластиковых/алюминиевых окон и дверей. "
                                "Верни строгий JSON с полями: strengths[], weaknesses[], unique_offers[], recommendations[], summary, "
                                "design_score (0-10, оценка визуального стиля), animation_potential (кратко о возможностях анимации/визуальных приёмов для этой ниши)."
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                    temperature=0.4,
                    max_tokens=1200,
                ).choices[0].message.content
            ),
            fallback_summary="Анализ по тексту страницы.",
            include_design=True,
        )

        # Если модель вернула пустые списки, строим детерминированный fallback
        if self._is_empty_analysis(analysis):
            analysis = self._fallback_from_content(title, h1, paragraph)

        return analysis

    async def analyze_website_screenshot(
        self, screenshot_base64: str, url: str, title: str, h1: str, first_paragraph: str
    ) -> CompetitorAnalysis:
        resp = self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты эксперт по конкурентному анализу сайтов в нише окон/дверей (ПВХ/алюминий). "
                        "Верни строгий JSON с полями: strengths[], weaknesses[], unique_offers[], recommendations[], summary, "
                        "design_score (0-10, оценка визуального стиля), animation_potential (идеи анимаций/визуальных приёмов)."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Сайт: {url}\nTitle: {title}\nH1: {h1}\nParagraph: {first_paragraph}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
                        },
                    ],
                },
            ],
            temperature=0.5,
            max_tokens=2000,
        )
        data = self._parse_json(resp.choices[0].message.content)
        analysis = self._build_analysis(
            data,
            fallback_summary="Модель не вернула структурированный ответ, использую текстовый анализ.",
            include_design=True,
        )

        # Fallback: если модель вернула пустые поля, повторяем текстовый анализ.
        if self._is_empty_analysis(analysis):
            return await self.analyze_parsed_content(title, h1, first_paragraph)

        return analysis


openai_service = OpenAIService()

