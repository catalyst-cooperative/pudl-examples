import marimo

__generated_with = "unknown"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Plant net generation over time
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import altair as alt
    import pandas as pd

    return alt, pd


@app.cell
def _(pd):
    base_path = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly"
    generation = pd.read_parquet(
        f"{base_path}/out_eia923__monthly_generation.parquet",
        columns=[
            "plant_id_eia",
            "plant_name_eia",
            "utility_name_eia",
            "report_date",
            "net_generation_mwh",
        ],
    )

    return (generation,)


@app.cell
def _(generation, mo):
    utility_names = generation.utility_name_eia.unique()
    utility_selector = mo.ui.dropdown(options=utility_names, label="Utility")
    return (utility_selector,)


@app.cell
def _(generation, utility_selector):
    plant_names = (
        generation.loc[generation.utility_name_eia == utility_selector.value]
        .groupby("plant_id_eia")
        .plant_name_eia.first()
        .reset_index()
        .set_index("plant_name_eia")
    )
    return (plant_names,)


@app.cell
def _(mo, plant_names, utility_selector):
    plant_selector = mo.ui.multiselect(
        options=plant_names.to_dict()["plant_id_eia"], label="Plant"
    )
    mo.vstack([utility_selector, plant_selector])
    return (plant_selector,)


@app.cell
def _(alt, generation, mo, plant_selector):
    selected = generation.loc[
        generation.plant_id_eia.isin(plant_selector.value),
        ["report_date", "plant_name_eia", "net_generation_mwh"],
    ]
    chart_data = selected.groupby(["report_date", "plant_name_eia"], as_index=False)[
        "net_generation_mwh"
    ].sum()
    if hasattr(chart_data, "to_native"):
        chart_data = chart_data.to_native()

    if chart_data.empty:
        chart = mo.md("Select one or more plants to display net generation.")
    else:
        base = alt.Chart(chart_data).encode(
            x=alt.X("report_date:T", title="Report Date"),
            y=alt.Y(
                "net_generation_mwh:Q",
                title="Net Generation (MWh)",
                scale=alt.Scale(zero=True),
            ),
            color=alt.Color("plant_name_eia:N", title="Plant"),
        )

        line = base.mark_line()
        hover_targets = base.mark_circle(size=140, opacity=0.01).encode(
            tooltip=[
                alt.Tooltip("report_date:T", title="Report Date"),
                alt.Tooltip("plant_name_eia:N", title="Plant"),
                alt.Tooltip(
                    "net_generation_mwh:Q", title="Net Generation (MWh)", format=",.0f"
                ),
            ]
        )

        chart = (
            alt.layer(line, hover_targets)
            .encode(color=alt.Color("plant_name_eia:N", title="Plant"))
            .properties(height=420)
            .interactive()
        )

    chart
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
