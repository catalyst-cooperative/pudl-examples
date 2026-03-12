import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    with mo.status.progress_bar(
        total=1, title="Loading subroutines", remove_on_exit=True
    ) as do_imports:
        import itertools
        import functools

        import fastparquet as fp
        import pandas as pd
        import pyarrow as pa
        import altair as alt

        do_imports.update(subtitle="Done!")
    return alt, functools, itertools, mo, pd


@app.function
def path(name):
    return (
        f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"
    )


@app.cell
def _(pd):
    def pudl(name, columns=None):
        return pd.read_parquet(
            path(name),
            engine="fastparquet",
            **({"columns": columns} if columns else {}),
        )

    return (pudl,)


@app.function
def pretty_plant_name(row):
    return f"{row.plant_name_eia} (EIA id={row.plant_id_eia})"


@app.function
def pretty_value_counts(series):
    return ", ".join(f"{k} ({v})" for k, v in series.value_counts().to_dict().items())


@app.cell
def _(mo, pudl):
    with mo.status.progress_bar(
        total=4,
        title="Loading data",
        subtitle="out_eia__yearly_plants",
        remove_on_exit=True,
    ) as do_fetch_data:
        out_eia__yearly_plants = pudl("out_eia__yearly_plants")
        do_fetch_data.update(subtitle="out_eia__yearly_generators")
        out_eia__yearly_generators = pudl("out_eia__yearly_generators")
        do_fetch_data.update(subtitle="out_eia923__monthly_generation_fuel_combined")
        # reduce columns read on this chonker
        out_eia923__monthly_generation_fuel_combined = pudl(
            "out_eia923__monthly_generation_fuel_combined",
            columns=[
                "plant_id_eia",
                "report_date",
                "prime_mover_code",
                "energy_source_code",
                "fuel_type_code_pudl",
                "net_generation_mwh",
            ],
        )
        do_fetch_data.update(subtitle=".")
        out_eia923__monthly_generation = pudl("out_eia923__monthly_generation")
        do_fetch_data.update(subtitle="Done!")
    return (
        out_eia923__monthly_generation,
        out_eia923__monthly_generation_fuel_combined,
        out_eia__yearly_generators,
        out_eia__yearly_plants,
    )


@app.cell
def _(mo, out_eia__yearly_plants):
    selected_state = mo.ui.dropdown.from_series(
        out_eia__yearly_plants.state.drop_duplicates().sort_values(),
        label="Select a state:",
        value="CO",
    )
    return (selected_state,)


@app.cell
def _(mo, out_eia__yearly_plants, selected_state):
    in_state_counties = (
        out_eia__yearly_plants.loc[
            out_eia__yearly_plants.state == selected_state.value, "county"
        ]
        .drop_duplicates()
        .sort_values()
    )
    selected_county = mo.ui.dropdown.from_series(
        in_state_counties, label="Select a county:", value=in_state_counties.iloc[0]
    )
    return (selected_county,)


@app.cell
def _(mo, out_eia__yearly_plants, selected_county, selected_state):
    in_county_plants = (
        out_eia__yearly_plants.loc[
            (out_eia__yearly_plants.state == selected_state.value)
            & (out_eia__yearly_plants.county == selected_county.value),
            ["plant_id_eia", "plant_name_eia"],
        ]
        .drop_duplicates()
        .sort_values(by="plant_id_eia")
        .set_index("plant_id_eia")
    )
    default_plant = in_county_plants.iloc[0]
    selected_plant = mo.ui.dropdown(
        options={f"{name} (id={id})": id for id, name in in_county_plants.to_records()},
        value=f"{default_plant.plant_name_eia} (id={default_plant.name})",
        label="Select a plant:",
    )
    return (selected_plant,)


@app.cell
def _(mo, selected_county, selected_plant, selected_state):
    mo.hstack([selected_state, selected_county, selected_plant])
    return


@app.cell
def _(mo, out_eia__yearly_plants, selected_plant):
    available_years = (
        out_eia__yearly_plants.loc[
            (out_eia__yearly_plants.plant_id_eia == selected_plant.value)
        ]
        .report_date.dt.year.drop_duplicates()
        .sort_values(ascending=False)
    )
    selected_year = mo.ui.dropdown(
        options={str(i): i for i in available_years},
        label="Plant facts from year:",
        value=str(available_years.iloc[0]),
    )
    return available_years, selected_year


@app.cell
def _(available_years, mo, selected_year):
    selected_timeseries_start = mo.ui.dropdown(
        options={str(i): i for i in available_years if i <= selected_year.value},
        label="Timeseries going back to:",
        value=str(available_years.min()),
    )
    return (selected_timeseries_start,)


@app.cell
def _(
    mo,
    out_eia923__monthly_generation,
    out_eia923__monthly_generation_fuel_combined,
    out_eia__yearly_generators,
    out_eia__yearly_plants,
    pd,
    selected_plant,
    selected_timeseries_start,
    selected_year,
):
    this_plant = out_eia__yearly_plants.loc[
        (out_eia__yearly_plants.plant_id_eia == selected_plant.value)
        & (out_eia__yearly_plants.report_date.dt.year == selected_year.value)
    ].iloc[0]
    this_plant = this_plant.rename(pretty_plant_name(this_plant))

    this_plant__monthly_generation_fuel_combined = (
        out_eia923__monthly_generation_fuel_combined.loc[
            (
                out_eia923__monthly_generation_fuel_combined.plant_id_eia
                == selected_plant.value
            )
            & (
                out_eia923__monthly_generation_fuel_combined.report_date.dt.year
                <= selected_year.value
            )
            & (
                out_eia923__monthly_generation_fuel_combined.report_date.dt.year
                >= selected_timeseries_start.value
            )
        ]
    )

    this_plant__monthly_generation = out_eia923__monthly_generation.loc[
        (out_eia923__monthly_generation.plant_id_eia == selected_plant.value)
        & (out_eia923__monthly_generation.report_date.dt.year <= selected_year.value)
        & (
            out_eia923__monthly_generation.report_date.dt.year
            >= selected_timeseries_start.value
        )
    ]

    this_plant__generators = (
        out_eia__yearly_generators.loc[
            (out_eia__yearly_generators.plant_id_eia == selected_plant.value)
            & (out_eia__yearly_generators.report_date == this_plant.report_date)
        ]
        .drop(
            columns=[
                "plant_id_eia",
                "report_date",
                "plant_id_pudl",
                "plant_name_eia",
                "utility_id_eia",
                "utility_id_pudl",
                "utility_name_eia",
                "balancing_authority_code_eia",
                "balancing_authority_name_eia",
                "state",
                "street_address",
                "timezone",
                "zip_code",
                "latitude",
                "longitude",
                "city",
                "county",
                "data_maturity",
            ]
        )
        .drop_duplicates()
    )

    this_plant__summary = pd.Series(
        {
            "fuel_types": ", ".join(
                this_plant__monthly_generation_fuel_combined.fuel_type_code_pudl.unique()
            ),
            "capacity_mw": round(
                this_plant__generators[
                    this_plant__generators.operational_status == "existing"
                ].capacity_mw.sum()
            ),
            "generators": this_plant__generators.shape[0],
            "status": pretty_value_counts(this_plant__generators.operational_status),
            "technologies": pretty_value_counts(
                this_plant__generators.technology_description.dropna()
            ),
        },
        name=this_plant.name,
    )

    mo.vstack(
        [
            mo.md(f"# {this_plant.name}"),
            selected_year,
            selected_timeseries_start,
            mo.md("----"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("## Grid"),
                            mo.plain(
                                this_plant[
                                    [
                                        "plant_name_eia",
                                        "plant_id_eia",
                                        "balancing_authority_code_eia",
                                        "sector_name_eia",
                                        "utility_name_eia",
                                        "utility_id_eia",
                                        "utility_id_pudl",
                                    ]
                                ].dropna()
                            ),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("## Location"),
                            mo.plain(
                                this_plant[
                                    [
                                        "street_address",
                                        "city",
                                        "state",
                                        "zip_code",
                                        "county",
                                        "timezone",
                                        "latitude",
                                        "longitude",
                                    ]
                                ].dropna()
                            ),
                        ]
                    ),
                    mo.vstack([mo.md("## Function"), mo.plain(this_plant__summary)]),
                ],
                justify="space-around",
                widths=[1.2, 0.9, 1],
            ),
        ]
    )
    return (
        this_plant,
        this_plant__generators,
        this_plant__monthly_generation,
        this_plant__monthly_generation_fuel_combined,
    )


@app.cell
def _(alt, mo, this_plant, this_plant__monthly_generation_fuel_combined):
    if this_plant__monthly_generation_fuel_combined.shape[0] == 0:
        mo.output.append(
            mo.callout("No generation data available for this plant.", kind="warn")
        )
    else:
        plant_netgen_chart = (
            alt.Chart(this_plant__monthly_generation_fuel_combined)
            .mark_line()
            .encode(
                alt.X("report_date").title("Report date"),
                alt.Y("net_generation_mwh", aggregate="sum").title(
                    "Net Generation (MWh)"
                ),
            )
            .properties(
                title=f"Total: {this_plant.name}, {this_plant['city'] or this_plant['county']}, {this_plant['state']}"
            )
        )
        mo.output.append(mo.ui.altair_chart(plant_netgen_chart))

        plant_netgen_bysource_chart = (
            alt.Chart(this_plant__monthly_generation_fuel_combined)
            .mark_line()
            .encode(
                alt.X("report_date").title("Report date"),
                alt.Y("net_generation_mwh", aggregate="sum").title(
                    "Net Generation (MWh)"
                ),
                color="fuel_type_code_pudl",
            )
            .properties(
                title=f"By fuel type: {this_plant.name}, {this_plant['city'] or this_plant['county']}, {this_plant['state']}"
            )
        )
        mo.output.append(mo.ui.altair_chart(plant_netgen_bysource_chart))
    return


@app.cell
def _(
    alt,
    mo,
    selected_plant,
    this_plant,
    this_plant__generators,
    this_plant__monthly_generation,
):
    if selected_plant.value is not None:
        mo.output.append(mo.md("# Generators"))
    if this_plant__monthly_generation.shape[0] == 0:
        mo.output.append(
            mo.md(
                "No generation data available at the generator level for this plant."
            ).style({"background": "#fee"})
        )
    else:
        n_monthly_gens = len(this_plant__monthly_generation.generator_id.unique())
        if n_monthly_gens < this_plant__generators.shape[0]:
            mo.output.append(
                mo.md(
                    f"Generation data available for {n_monthly_gens} of {this_plant__generators.shape[0]} generators for this plant."
                ).style({"background": "#eee"})
            )
        bygen_chart = (
            alt.Chart(this_plant__monthly_generation)
            .mark_line()
            .encode(
                alt.X("report_date").title("Report date"),
                alt.Y("net_generation_mwh").title("Net Generation (MWh)"),
                color="generator_id",
            )
            .properties(
                title=f"By generator: {this_plant.name}, {this_plant['city'] or this_plant['county']}, {this_plant['state']}"
            )
        )
        mo.output.append(mo.ui.altair_chart(bygen_chart))
    return


@app.cell
def _(mo, this_plant__generators):
    filter_columns = [
        "generator_id",
        "unit_id_pudl",
        "technology_description",
        "energy_source_code_1",
        "prime_mover_code",
        "operational_status",
        "fuel_type_code_pudl",
        "associated_combined_heat_power",
        "operational_status_code",
    ]
    filter_counts = this_plant__generators[filter_columns].nunique()
    filter_counts = filter_counts.loc[filter_counts > 0]
    filters = {}
    only_option = set()
    filter_options = {}
    filter_defaults = {}
    for k, v in filter_counts.to_dict().items():
        available = this_plant__generators[k].value_counts(dropna=False)
        available = available.loc[available > 0].index
        if available.shape[0] == 1:
            only_option.add(k)
        filter_options[k] = {str(x): x for x in available}
        filter_defaults[k] = [str(available[0])] if k in only_option else None

    if filter_options:
        import math

        option_lengths = {k: [len(vk) for vk in v] for k, v in filter_options.items()}
        max_column = max(
            (len(k) + max(option_lengths[k])) for k, v in filter_options.items()
        )
        max_label = max(len(k) for k in filter_options)
        max_input = max(max(v) for v in option_lengths.values())
        columns = math.ceil(80 / max_column)

        for k in filter_options:
            filters[k] = mo.Html(
                f"""<div data-testid="genselect-{k}" style="display: flex; gap: 0.5rem; {"color: #bbbbbb" if k in only_option else ""}">
         <label style="flex: {max_label / max_input} 1 0%; text-align: end;">{k}</label>
         <div style="flex: 1 1 0%;">{{multiselect}}</div>
     </div>"""
            ).batch(
                multiselect=mo.ui.multiselect(
                    options=filter_options[k],
                    value=filter_defaults[k],
                    # label=k,
                )
            )
    filters = mo.ui.dictionary(filters)
    return columns, filters, math


@app.cell
def _(
    columns,
    filters,
    functools,
    itertools,
    math,
    mo,
    this_plant__generators,
):
    if len(filters) == 0:
        mo.output.append(
            mo.md("No other information about generators for this plant.").style(
                {"background": "#fee"}
            )
        )
    else:
        mo.output.append(
            mo.hstack(
                [
                    mo.vstack([f[1] for f in row if f])
                    for row in itertools.batched(
                        filters.items(), math.ceil(len(filters) / columns)
                    )
                ],
                widths="equal",
            )
        )
        selected__generators = this_plant__generators[
            functools.reduce(
                lambda accum, update: accum & update,
                [
                    this_plant__generators[k].isin(v.value["multiselect"])
                    for k, v in filters.items()
                    if v.value["multiselect"]
                ],
            )
        ]
        mo.output.append(
            mo.hstack(
                [
                    mo.md(
                        (
                            "All"
                            if selected__generators.shape[0]
                            == this_plant__generators.shape[0]
                            else f"{selected__generators.shape[0]} of"
                        )
                        + f" {this_plant__generators.shape[0]} generators selected"
                    ),
                ],
                justify="start",
            ).style(background="#eee")
        )
    return (selected__generators,)


@app.cell
def _(this_plant__generators):
    ops_columns = [
        "generator_id",
        "technology_description",
        "operational_status",
        "generator_operating_date",
        "original_planned_generator_operating_date",
        "generator_retirement_date",
        "planned_generator_retirement_date",
        "current_planned_generator_operating_date",
        "capacity_factor",
        "capacity_mw",
        "summer_capacity_estimate",
        "summer_capacity_mw",
        "summer_estimated_capability_mw",
        "winter_capacity_estimate",
        "winter_capacity_mw",
        "winter_estimated_capability_mw",
    ]
    nrg_columns = [
        "generator_id",
        "fuel_type_code_pudl",
        "prime_mover_code",
    ] + [f"energy_source_code_{i}" for i in range(1, 7)]
    remaining_columns = ["generator_id"] + sorted(
        set(this_plant__generators.columns) - set(ops_columns + nrg_columns)
    )
    return nrg_columns, ops_columns, remaining_columns


@app.cell
def _(
    filters,
    mo,
    nrg_columns,
    ops_columns,
    remaining_columns,
    selected__generators,
):
    if filters.value:
        mo.ui.table.default_page_size = 50
        mo.output.append(
            mo.ui.table(
                selected__generators[
                    ops_columns + nrg_columns[1:] + remaining_columns[1:]
                ]
                .set_index("generator_id")
                .T.dropna(thresh=1),
                selection=None,
            )
        )
    return


if __name__ == "__main__":
    app.run()
