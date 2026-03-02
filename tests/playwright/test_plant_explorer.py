import time

from playwright.sync_api import Page, expect


def _find_interactible(page: Page, label: str):
    """Grab the interactible element labeled by `label`.

    Look for a marimo label that matches your label. Then find a sibling element
    that advertises it has a popup.
    """
    container = page.locator("div.mo-label").filter(has_text=label).first
    interactible = container.locator("div[aria-haspopup]").first
    expect(interactible).to_be_visible()
    return interactible


def _select_option_by_text(page: Page, label: str, option_text: str) -> None:
    """Find the interactible labeled by `label` and click popup option text."""
    interactible = _find_interactible(page, label)
    interactible.click()
    option = page.locator("[role='option']:visible", has_text=option_text).first
    expect(option).to_be_visible()
    option.click()


def _chart_png(page: Page) -> bytes:
    chart = page.locator("[role='graphics-document'], .vega-embed").first
    expect(chart).to_be_visible()
    return chart.screenshot()


def test_plant_explorer_interactions(page: Page, server_base_url: str) -> None:
    page.goto(f"{server_base_url}/plant-explorer.html")

    # Should take quite some time to load the Marimo runtime
    expect(
        page.get_by_role("heading", name="Plant net generation over time")
    ).to_be_visible(timeout=15_000)

    # Takes a few seconds to download the data and then have utility/plant options
    expect(page.get_by_text("Utility", exact=True)).to_be_visible(timeout=30_000)
    expect(page.get_by_text("Plant", exact=True)).to_be_visible(timeout=30_000)

    _select_option_by_text(page, "Utility", "Alabama Power Co")
    _select_option_by_text(page, "Plant", "Barry")
    first_chart_png = _chart_png(page)
    assert first_chart_png, "Expected non-empty chart screenshot after first plant."

    # Add a second plant and verify the chart updates.
    _select_option_by_text(page, "Plant", "Gadsden")
    for _ in range(30):
        if _chart_png(page) != first_chart_png:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("Chart did not update after selecting a second plant.")
