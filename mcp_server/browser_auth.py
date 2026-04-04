"""Browser-based ESPN login — opens a browser, user logs in, cookies are captured."""

import asyncio
from dataclasses import dataclass
from typing import Callable

ESPN_LOGIN_URL = "https://www.espn.com/login"
ESPN_FANTASY_URL = "https://fantasy.espn.com"
TIMEOUT_SECONDS = 300  # 5 minutes


@dataclass
class EspnCredentials:
    espn_s2: str
    swid: str


async def login_with_browser(
    *,
    headless: bool = False,
    on_status: Callable[[str], None] | None = None,
) -> EspnCredentials:
    """Open a browser for ESPN login and capture espn_s2 + SWID cookies.

    Raises TimeoutError if the user doesn't complete login within 5 minutes.
    Raises RuntimeError if Playwright/Chromium is not installed.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run: uv run playwright install chromium"
        )

    def _status(msg: str) -> None:
        if on_status:
            on_status(msg)

    captured = asyncio.Event()
    creds: EspnCredentials | None = None

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=headless)
        except Exception:
            raise RuntimeError(
                "Chromium browser not found. Run: uv run playwright install chromium"
            )

        context = await browser.new_context(
            viewport={"width": 480, "height": 800},
        )
        page = await context.new_page()

        _status("Opening ESPN login page...")
        await page.goto(ESPN_LOGIN_URL, wait_until="domcontentloaded")
        _status("Waiting for you to log in...")

        async def _poll_cookies() -> None:
            """Poll browser cookies until espn_s2 and SWID appear."""
            nonlocal creds
            while not captured.is_set():
                await asyncio.sleep(2)
                cookies = await context.cookies()
                cookie_map = {c["name"]: c["value"] for c in cookies}
                espn_s2 = cookie_map.get("espn_s2")
                swid = cookie_map.get("SWID")
                if espn_s2 and swid:
                    _status("Cookies captured!")
                    creds = EspnCredentials(espn_s2=espn_s2, swid=swid)
                    captured.set()
                    return

        poll_task = asyncio.create_task(_poll_cookies())

        try:
            await asyncio.wait_for(captured.wait(), timeout=TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            poll_task.cancel()
            await browser.close()
            raise TimeoutError("Login timed out after 5 minutes.")

        poll_task.cancel()

        # Navigate to Fantasy to confirm cookies work
        _status("Verifying access to ESPN Fantasy...")
        try:
            await page.goto(ESPN_FANTASY_URL, wait_until="domcontentloaded", timeout=10000)
        except Exception:
            pass  # Best-effort verification

        await browser.close()

    assert creds is not None
    return creds
