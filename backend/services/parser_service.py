import asyncio
import base64
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from backend.config import logger, settings


class ParserService:
    async def parse_url(
        self, url: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        """
        Открывает страницу в Chrome (Playwright, sync внутри отдельного треда),
        ждёт загрузку, делает скриншот и возвращает распарсенный контент.
        """
        return await asyncio.to_thread(self._parse_sync, url)

    def _parse_sync(
        self, url: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes], Optional[str]]:
        try:
            if not url.startswith("http"):
                url = "https://" + url

            timeout_ms = max(settings.parser_timeout or 0, 20) * 1000

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
                context = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent=settings.parser_user_agent,
                )
                page = context.new_page()

                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
                page.wait_for_selector("body", timeout=timeout_ms)

                page_title = page.title() or None
                h1_text = page.eval_on_selector("h1", "el => el?.innerText?.trim() || null")
                first_paragraph = page.eval_on_selector("p", "el => el?.innerText?.trim() || null")

                page_source = page.content()
                screenshot_bytes = page.screenshot(full_page=True)

                browser.close()

            soup = BeautifulSoup(page_source, "lxml")
            title = page_title or (soup.title.string.strip() if soup.title and soup.title.string else None)
            h1 = h1_text or (soup.find("h1").get_text(strip=True) if soup.find("h1") else None)
            paragraph = first_paragraph or (soup.find("p").get_text(strip=True) if soup.find("p") else None)

            return title, h1, paragraph, screenshot_bytes, None

        except PlaywrightTimeout as e:
            logger.error(f"Playwright timeout: {e}")
            return None, None, None, None, f"Timeout loading page: {e}"
        except Exception as e:
            logger.error(f"parse_url error: {e}")
            return None, None, None, None, str(e)

    def screenshot_to_base64(self, screenshot_bytes: Optional[bytes]) -> Optional[str]:
        if not screenshot_bytes:
            return None
        return base64.b64encode(screenshot_bytes).decode("utf-8")


parser_service = ParserService()

