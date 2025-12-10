import base64

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models.schemas import (
    HistoryResponse,
    ImageAnalysisResponse,
    ParseDemoRequest,
    ParseDemoResponse,
    ParsedContent,
    TextAnalysisRequest,
    TextAnalysisResponse,
)
from backend.services.history_service import history_service
from backend.services.openai_service import openai_service
from backend.services.parser_service import parser_service

app = FastAPI(
    title="Мониторинг конкурентов",
    description="Текст+изображения, парсинг URL, история",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.post("/analyze_text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    try:
        analysis = await openai_service.analyze_text(request.text)
        history_service.add_entry("text", request.text[:100], analysis.summary)
        return TextAnalysisResponse(success=True, analysis=analysis)
    except Exception as e:
        return TextAnalysisResponse(success=False, error=str(e))


@app.post("/analyze_image", response_model=ImageAnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    allowed = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Допустимо: {', '.join(allowed)}")
    try:
        raw = await file.read()
        image_b64 = base64.b64encode(raw).decode("utf-8")
        analysis = await openai_service.analyze_image(
            image_b64, mime_type=file.content_type
        )
        history_service.add_entry(
            "image", f"Изображение: {file.filename}", analysis.description[:120]
        )
        return ImageAnalysisResponse(success=True, analysis=analysis)
    except Exception as e:
        return ImageAnalysisResponse(success=False, error=str(e))


@app.post("/parse_demo", response_model=ParseDemoResponse)
async def parse_demo(request: ParseDemoRequest):
    title, h1, paragraph, screenshot_bytes, error = await parser_service.parse_url(
        str(request.url)
    )
    if error:
        return ParseDemoResponse(success=False, error=error)

    if screenshot_bytes:
        screenshot_b64 = parser_service.screenshot_to_base64(screenshot_bytes)
        analysis = await openai_service.analyze_website_screenshot(
            screenshot_b64, str(request.url), title or "", h1 or "", paragraph or ""
        )
    else:
        analysis = await openai_service.analyze_parsed_content(
            title or "", h1 or "", paragraph or ""
        )

    data = ParsedContent(
        url=str(request.url),
        title=title,
        h1=h1,
        first_paragraph=paragraph,
        analysis=analysis,
    )
    history_service.add_entry(
        "parse",
        f"URL: {request.url}",
        analysis.summary[:120] if analysis.summary else "",
    )
    return ParseDemoResponse(success=True, data=data)


@app.get("/history", response_model=HistoryResponse)
async def get_history():
    items = history_service.get_history()
    return HistoryResponse(items=items, total=len(items))


@app.delete("/history")
async def clear_history():
    history_service.clear_history()
    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "competitor-monitor"}


app.mount("/static", StaticFiles(directory="frontend"), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", host=settings.api_host, port=settings.api_port, reload=True
    )

