import time

from playwright.sync_api import Page, expect

WIDGET_TYPES = [
    "dropdown",
]


def _find_interactible(page: Page, label: str, widget_type: str):
    """Grab the interactible element labeled by `label`.

    Look for a marimo widget that matches your label. Then find a sibling element
    that advertises it has data (for HTML inputs) or a popup (for div-based inputs).
    """
    container = page.locator(f"marimo-{widget_type}").filter(has_text=label).first
    interactible = (
        container.locator("[data-testid]")
        .or_(container.locator("[aria-haspopup]"))
        .first
    )
    expect(interactible).to_be_visible()
    return interactible


def _multiselect_option(page: Page, option_text: str) -> None:
    option = page.locator("[role='option']:visible", has_text=option_text).first
    expect(option).to_be_visible()
    option.click()


def _multiselect_option_by_text(page: Page, label: str, option_text: str) -> None:
    """Find the interactible labeled by `label` and click popup option text."""
    interactible = _find_interactible(page, label, "multiselect")
    interactible.click()
    _multiselect_option(page, option_text)


def _chart_png(page: Page) -> bytes:
    chart = page.locator("[role='graphics-document'], .vega-embed").first
    expect(chart).to_be_visible(timeout=5_000)
    # without this sleep, sometimes the chart isn't attached to the DOM when
    # we try to take a screenshot
    time.sleep(0.2)
    return chart.screenshot()


def test_plant_explorer_interactions(page: Page, server_base_url: str) -> None:
    page.goto(f"{server_base_url}/plant-explorer.html")

    # Takes quite a while to load data before we can see the explorer
    expect(page.get_by_text("Select a state:", exact=True)).to_be_visible(
        timeout=75_000
    )

    _find_interactible(page, "Select a state:", "dropdown").select_option("AL")
    _find_interactible(page, "Select a county:", "dropdown").select_option("Mobile")
    _find_interactible(page, "Select a plant:", "dropdown").select_option(
        "Barry (id=3)"
    )
    first_chart_png = _chart_png(page)
    assert first_chart_png, "Expected non-empty chart screenshot after first plant."

    # Add a second plant and verify the chart updates.
    _find_interactible(page, "Select a plant:", "dropdown").select_option(
        "Hog Bayou Energy Center (id=55241)"
    )
    for _ in range(30):
        if _chart_png(page) != first_chart_png:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("Chart did not update after selecting a second plant.")

    # Pare down the list of generators
    container = page.get_by_test_id("genselect-prime_mover_code")
    interactible = container.locator("[aria-haspopup]").first
    expect(interactible).to_be_visible()
    interactible.click()
    _multiselect_option(page, "CA")
    expect(page.get_by_text("1 of 2 generators selected")).to_be_visible(timeout=5_000)
