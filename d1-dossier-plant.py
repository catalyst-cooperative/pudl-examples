import marimo

__generated_with = "0.20.2"
app = marimo.App(width="medium")


@app.cell
def _():
    from datetime import date

    import pandas as pd
    import marimo as mo

    return mo, pd


@app.function
def pretty_plant_name(row):
    return f"{row.plant_name_eia} (id={row.plant_id_eia})"


@app.cell
def _(pd):
    out_eia__yearly_plants = pd.read_parquet("https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/out_eia__yearly_plants.parquet")
    return (out_eia__yearly_plants,)


@app.cell
def _(pd):
    out_eia__yearly_generators = pd.read_parquet("https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/out_eia__yearly_generators.parquet")
    out_eia923__monthly_generation_fuel_combined = pd.read_parquet("https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/out_eia923__monthly_generation_fuel_combined.parquet")
    out_eia923__monthly_generation = pd.read_parquet("https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/out_eia923__monthly_generation.parquet")
    return (
        out_eia923__monthly_generation,
        out_eia923__monthly_generation_fuel_combined,
        out_eia__yearly_generators,
    )


@app.cell
def _(mo, out_eia__yearly_plants):
    selected_state = mo.ui.dropdown.from_series(out_eia__yearly_plants.state.drop_duplicates().sort_values(), label="Select a state:", value="CO")
    return (selected_state,)


@app.cell
def _(mo, out_eia__yearly_plants, selected_state):
    in_state_counties = out_eia__yearly_plants.loc[
        out_eia__yearly_plants.state == selected_state.value,
        "county"
    ].drop_duplicates().sort_values()
    selected_county = mo.ui.dropdown.from_series(in_state_counties, label="Select a county:", value=in_state_counties.iloc[0])
    return (selected_county,)


@app.cell
def _(mo, out_eia__yearly_plants, selected_county, selected_state):
    in_county_plants = out_eia__yearly_plants.loc[
        (out_eia__yearly_plants.state == selected_state.value) &
        (out_eia__yearly_plants.county == selected_county.value),
        ["plant_id_eia","plant_name_eia"]
    ].drop_duplicates().sort_values(by="plant_id_eia").set_index("plant_id_eia")
    default_plant = in_county_plants.iloc[0]
    selected_plant = mo.ui.dropdown(
        options={
            f"{name} (id={id})": id
            for id, name in in_county_plants.to_records()
        },
        value=f"{default_plant.plant_name_eia} (id={default_plant.name})",
        label="Select a plant:"
    )
    return (selected_plant,)


@app.cell
def _(mo, selected_county, selected_plant, selected_state):
    mo.hstack([selected_state, selected_county, selected_plant])
    return


@app.cell
def _(mo, out_eia__yearly_plants, selected_plant):
    available_years = out_eia__yearly_plants.loc[
        (out_eia__yearly_plants.plant_id_eia==selected_plant.value)
    ].report_date.drop_duplicates().sort_values(ascending=False)
    selected_year = mo.ui.dropdown(
        options={
            str(i): i
            for i in available_years
        },
        label="Data as of:",
        value=str(available_years.iloc[0])
    )
    return (selected_year,)


@app.cell
def _(
    mo,
    out_eia923__monthly_generation,
    out_eia923__monthly_generation_fuel_combined,
    out_eia__yearly_generators,
    out_eia__yearly_plants,
    pd,
    selected_plant,
    selected_year,
):
    this_plant = out_eia__yearly_plants.loc[
        (out_eia__yearly_plants.plant_id_eia==selected_plant.value) & 
        (out_eia__yearly_plants.report_date == selected_year.value)
    ].iloc[0]
    this_plant = this_plant.rename(pretty_plant_name(this_plant))

    this_plant__monthly_generation_fuel_combined = out_eia923__monthly_generation_fuel_combined.loc[
        out_eia923__monthly_generation_fuel_combined.plant_id_eia == selected_plant.value
    ]

    this_plant__monthly_generation = out_eia923__monthly_generation.loc[
        (out_eia923__monthly_generation.plant_id_eia == selected_plant.value)
    ]

    this_plant__generators = out_eia__yearly_generators.loc[
        (out_eia__yearly_generators.plant_id_eia==selected_plant.value) &
        (out_eia__yearly_generators.report_date==this_plant.report_date)
    ].drop(columns=[
        "plant_id_eia","report_date","plant_id_pudl","plant_name_eia","utility_id_eia","utility_id_pudl","utility_name_eia",
        "balancing_authority_code_eia","balancing_authority_name_eia",
        "state","street_address","timezone","zip_code","latitude","longitude","city","county",
        "data_maturity"
    ]).drop_duplicates()

    this_plant__summary = pd.Series({
        "fuel_types": ", ".join(this_plant__monthly_generation_fuel_combined.fuel_type_code_pudl.unique()),
        "generators": this_plant__generators.shape[0],
        "technologies": ", ".join(this_plant__generators.technology_description.dropna().drop_duplicates())
    }, name=this_plant.name)

    mo.vstack([
        mo.md(f"# {this_plant.name}"),
        selected_year,
        mo.md("----"),
        mo.hstack([
            mo.vstack([
                mo.md("## Grid"),
                mo.plain(this_plant[[
                    "plant_name_eia",
                    "plant_id_eia",
                    "balancing_authority_code_eia",
                    "sector_name_eia",
                    "utility_name_eia",
                    "utility_id_eia",
                    "utility_id_pudl",
                ]].dropna())
            ]),
            mo.vstack([
                mo.md("## Location"),
                mo.plain(this_plant[[
                    "street_address","city","state","zip_code","county","timezone",
                ]].dropna())
            ]),
            mo.vstack([
                mo.md("## Function"),
                mo.plain(this_plant__summary)
            ])  
        ], justify="space-around", widths=[1.2, 0.9, 1])
    ])
    return (
        this_plant,
        this_plant__generators,
        this_plant__monthly_generation,
        this_plant__monthly_generation_fuel_combined,
    )


@app.cell
def _():
    import matplotlib as mp
    import altair as alt

    return (alt,)


@app.cell
def _(alt, mo, this_plant, this_plant__monthly_generation_fuel_combined):
    plant_netgen_chart = alt.Chart(this_plant__monthly_generation_fuel_combined).mark_line().encode(
        alt.X("report_date").title("Report date"),
        alt.Y("net_generation_mwh", aggregate="sum").title("Net Generation (MWh)"),
    ).properties(title=f"Total: {this_plant.name}, {this_plant['city']}, {this_plant['state']}")
    mo.ui.altair_chart(plant_netgen_chart)
    return


@app.cell
def _(alt, mo, this_plant, this_plant__monthly_generation_fuel_combined):
    plant_netgen_bysource_chart = alt.Chart(this_plant__monthly_generation_fuel_combined).mark_line().encode(
        alt.X("report_date").title("Report date"),
        alt.Y("net_generation_mwh", aggregate="sum").title("Net Generation (MWh)"),
        color="fuel_type_code_pudl"
    ).properties(title=f"By fuel type: {this_plant.name}, {this_plant['city']}, {this_plant['state']}")
    mo.ui.altair_chart(plant_netgen_bysource_chart)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Generators
    """)
    return


@app.cell
def _(alt, this_plant__monthly_generation):
    bygen_chart = alt.Chart(this_plant__monthly_generation).mark_line().encode(
        alt.X("report_date"),
        alt.Y("net_generation_mwh"),
        color="generator_id"
    )
    bygen_chart
    return


@app.cell
def _(this_plant__generators):
    this_plant__generators.set_index("generator_id").T.dropna(thresh=1)
    return


@app.cell
def _(mo, this_plant__generators):
    selected_generator = mo.ui.dropdown.from_series(this_plant__generators.generator_id, label="Select generator:", value=this_plant__generators.generator_id.iloc[0])
    selected_generator
    return (selected_generator,)


@app.cell
def _(
    alt,
    out_eia923__monthly_generation,
    selected_generator,
    this_plant__monthly_generation,
):
    gen_chart = alt.Chart(this_plant__monthly_generation.loc[
        (out_eia923__monthly_generation.generator_id == selected_generator.value)
    ]).mark_line().encode(
        alt.X("report_date"),
        alt.Y("net_generation_mwh")
    )
    gen_chart
    return


if __name__ == "__main__":
    app.run()
