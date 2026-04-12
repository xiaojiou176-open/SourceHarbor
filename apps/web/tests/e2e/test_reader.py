from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def test_reader_fail_close_links(page: Page) -> None:
    page.goto("/reader", wait_until="domcontentloaded")

    specimen_link = page.get_by_role("link", name="Open specimen detail").first
    expect(specimen_link).to_be_visible()
    specimen_link.click()
    expect(page).to_have_url(re.compile(r"/reader/demo$"))

    page.goto("/reader", wait_until="domcontentloaded")
    ops_link = page.get_by_role("link", name="Open ops desk")
    expect(ops_link).to_be_visible()
    ops_link.click()
    expect(page).to_have_url(re.compile(r"/ops(?:\?.*)?$"))

    page.goto("/reader", wait_until="domcontentloaded")
    source_intake_link = page.get_by_role("link", name="Source intake")
    expect(source_intake_link).to_be_visible()
    source_intake_link.click()
    expect(page).to_have_url(re.compile(r"/subscriptions(?:\?.*)?$"))
