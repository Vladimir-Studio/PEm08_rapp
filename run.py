import uvicorn
from backend.config import settings


if __name__ == "__main__":
    print(f"🚀 http://{settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

