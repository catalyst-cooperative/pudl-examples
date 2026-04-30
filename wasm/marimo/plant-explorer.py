import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _(mo, selection):
    mo.output.append(mo.md("# Plant Explorer"))
    mo.output.append(
        mo.md(
            'Explore attributes of any plant that reports to <a href="https://docs.catalyst.coop/pudl/data_sources/eia860.html" target="_blank">EIA-860</a> or <a href="https://docs.catalyst.coop/pudl/data_sources/eia923.html" target="_blank">EIA-923</a>. Select a state, county and specific plant to explore its attributes, generation over time and generators.'
        )
    )
    mo.output.append(
        mo.hstack(
            [
                selection.state_selector,
                selection.county_selector,
                selection.plant_selector,
            ]
        )
    )
    return


@app.cell(hide_code=True)
def _(mo, selection, this_plant):
    mo.md(f"""
    # {"{} (EIA id={})".format(this_plant.name, this_plant.plant_id_eia) if selection.plant is not None else ""}
    """)
    return


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
    return row.plant_name_eia


@app.function
def pretty_value_counts(series):
    return ", ".join(f"{k} ({v})" for k, v in series.value_counts().to_dict().items())


@app.function
def table_preview_href(name):
    return f"""<a href="https://data.catalyst.coop/preview/pudl/{name}" target="_blank">{name}</a>"""


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
def _(mo, out_eia__yearly_plants, pd):
    class Options:
        @classmethod
        @mo.cache
        def available_states(cls) -> pd.Series:
            return out_eia__yearly_plants.state.drop_duplicates().sort_values()

        @classmethod
        @mo.cache
        def available_counties(cls, state: str) -> pd.Series:
            return (
                out_eia__yearly_plants.loc[
                    out_eia__yearly_plants.state == state, "county"
                ]
                .drop_duplicates()
                .sort_values()
            )

        @classmethod
        @mo.cache
        def available_plants(cls, state, county) -> pd.DataFrame:
            return (
                out_eia__yearly_plants.loc[
                    (out_eia__yearly_plants.state == state)
                    & (out_eia__yearly_plants.county == county),
                    ["plant_id_eia", "plant_name_eia"],
                ]
                .drop_duplicates()
                .sort_values(by="plant_id_eia")
                .set_index("plant_id_eia")
            )

        @classmethod
        @mo.cache
        def available_years(cls, plant) -> pd.Series:
            return (
                out_eia__yearly_plants.loc[
                    (out_eia__yearly_plants.plant_id_eia == plant)
                ]
                .report_date.dt.year.drop_duplicates()
                .sort_values(ascending=False)
            )

    return (Options,)


@app.cell
def _(Options, mo):
    # this has to be in a cell other than the cell where `selection` is defined
    query_params = mo.query_params()

    def initialize_default_params():
        if "state" not in query_params or query_params["state"] not in set(
            Options.available_states()
        ):
            query_params["state"] = "CO"
            mo.output.append("Fixed state")
        if "county" not in query_params or query_params["county"] not in set(
            Options.available_counties(query_params["state"])
        ):
            query_params["county"] = Options.available_counties(
                query_params["state"]
            ).iloc[0]
            mo.output.append("Fixed county")
        if "plant" not in query_params or query_params["plant"] not in set(
            Options.available_plants(
                query_params["state"], query_params["county"]
            ).index
        ):
            query_params["plant"] = int(
                Options.available_plants(query_params["state"], query_params["county"])
                .iloc[0]
                .name
            )
            mo.output.append("Fixed plant")
        if "year" not in query_params or query_params["year"] not in set(
            Options.available_years(query_params["plant"])
        ):
            query_params["year"] = int(
                Options.available_years(query_params["plant"]).max()
            )
            mo.output.append("Fixed year")
        if "timeseries_start" not in query_params or query_params[
            "timeseries_start"
        ] not in set(Options.available_years(query_params["plant"])):
            query_params["timeseries_start"] = int(
                Options.available_years(query_params["plant"]).min()
            )
            mo.output.append("Fixed timeseries_start")

    initialize_default_params()

    return initialize_default_params, query_params


@app.cell
def _(initialize_default_params, query_params):
    def reset_params(**kwargs):
        for param, value in kwargs.items():
            query_params.set(param, value)
        initialize_default_params()

    return (reset_params,)


@app.cell
def _(Options, mo, query_params, reset_params):
    from pydantic import BaseModel, Field, computed_field
    from functools import cached_property

    class Selection(BaseModel):
        state: str = Field("CO")
        county: str
        plant: int
        year: int
        timeseries_start: int

        @computed_field
        @cached_property
        def state_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown.from_series(
                Options.available_states(),
                label="Select a state:",
                value=self.state,
                on_change=lambda value: reset_params(state=value),
            )

        @computed_field
        @cached_property
        def county_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown.from_series(
                Options.available_counties(self.state),
                label="Select a county:",
                value=self.county,
                on_change=lambda value: reset_params(county=value),
            )

        @computed_field
        @cached_property
        def plant_selector(self) -> mo.ui.dropdown:
            def as_default_plant_value(plant_id):
                plant_record = Options.available_plants(self.state, self.county).loc[
                    plant_id
                ]
                return f"{plant_record.plant_name_eia} (id={plant_record.name})"

            return mo.ui.dropdown(
                options={
                    f"{name} (id={id})": id
                    for id, name in Options.available_plants(
                        self.state, self.county
                    ).to_records()
                },
                value=as_default_plant_value(self.plant),
                label="Select a plant:",
                on_change=lambda value: reset_params(plant=int(value)),
            )

        @computed_field
        @cached_property
        def year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={str(i): i for i in Options.available_years(self.plant)},
                label="Plant attributes from year:",
                value=str(self.year),
                on_change=lambda value: reset_params(year=int(value)),
            )

        @computed_field
        @cached_property
        def timeseries_start_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={
                    str(i): i
                    for i in Options.available_years(self.plant)
                    if i <= self.year
                },
                label="Generation timeseries going back to:",
                value=str(self.timeseries_start),
                on_change=lambda value: reset_params(timeseries_start=int(value)),
            )

    selection = Selection(**query_params.to_dict())
    return (selection,)


@app.cell
def _(
    mo,
    out_eia923__monthly_generation,
    out_eia923__monthly_generation_fuel_combined,
    out_eia__yearly_generators,
    out_eia__yearly_plants,
    pd,
    selection,
):
    this_plant = out_eia__yearly_plants.loc[
        (out_eia__yearly_plants.plant_id_eia == selection.plant)
        & (out_eia__yearly_plants.report_date.dt.year == selection.year)
    ].iloc[0]
    this_plant = this_plant.rename(pretty_plant_name(this_plant))

    this_plant__monthly_generation_fuel_combined = (
        out_eia923__monthly_generation_fuel_combined.loc[
            (
                out_eia923__monthly_generation_fuel_combined.plant_id_eia
                == selection.plant
            )
            & (
                out_eia923__monthly_generation_fuel_combined.report_date.dt.year
                <= selection.year
            )
            & (
                out_eia923__monthly_generation_fuel_combined.report_date.dt.year
                >= selection.timeseries_start
            )
        ]
    )

    this_plant__monthly_generation = out_eia923__monthly_generation.loc[
        (out_eia923__monthly_generation.plant_id_eia == selection.plant)
        & (out_eia923__monthly_generation.report_date.dt.year <= selection.year)
        & (
            out_eia923__monthly_generation.report_date.dt.year
            >= selection.timeseries_start
        )
    ]

    this_plant__generators = (
        out_eia__yearly_generators.loc[
            (out_eia__yearly_generators.plant_id_eia == selection.plant)
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
            mo.hstack(
                [
                    mo.md(f"""<div data-tooltip="By default we show you plant attributes from the most recent year of data available.
                If you want to see plant attributes from a previous year, select here.">{mo.icon("lucide:info")}</div>"""),
                    selection.year_selector,
                ],
                justify="start",
            ),
            mo.hstack(
                [
                    mo.md(f"""<div data-tooltip="By default we extend the timeseries plots below as far back as we have data available.
                To prune to a more recent year, select here.">{mo.icon("lucide:info")}</div>"""),
                    selection.timeseries_start_selector,
                ],
                justify="start",
            ),
            mo.md("----"),
            mo.md(
                "Here is what we know about how this plant is situated within the grid, its physical location in space, and what operational generation capabilities it has."
            ),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("## Grid Attributes"),
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
                                ]
                                .dropna()
                                .rename("")
                            ),
                            mo.md(
                                f"via {table_preview_href('out_eia__yearly_plants')}"
                            ),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("## Location Attributes"),
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
                                ]
                                .dropna()
                                .rename("")
                            ),
                            mo.md(
                                f"via {table_preview_href('out_eia__yearly_plants')}"
                            ),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("## Operational Attributes"),
                            mo.plain(this_plant__summary.rename("")),
                            mo.md(
                                f"via {table_preview_href('out_eia__yearly_generators')};<br/>"
                                f"via {table_preview_href('out_eia923__monthly_generation_fuel_combined')}"
                                ""
                            ),
                        ]
                    ),
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
    mo.output.append(mo.md("## Plant-level generation"))
    mo.stop(
        this_plant__monthly_generation_fuel_combined.shape[0] == 0,
        mo.md("No plant-level generation data available for this plant.").style(
            {"background": "#fee"}
        ),
    )
    mo.output.append(
        mo.md("Here is a timeseries view of the electricity produced at this plant.")
    )

    plant_netgen_chart = (
        alt.Chart(
            this_plant__monthly_generation_fuel_combined,
            title=alt.Title(
                f"Net Generation: {this_plant.name}, {this_plant['city'] or this_plant['county']}, {this_plant['state']}",
                subtitle="Total",
            ),
        )
        .mark_line()
        .encode(
            alt.X("report_date").title("Report date"),
            alt.Y("net_generation_mwh", aggregate="sum").title("Net Generation (MWh)"),
        )
    )
    mo.output.append(mo.ui.altair_chart(plant_netgen_chart))
    mo.output.append(
        mo.md(
            f"via {table_preview_href('out_eia923__monthly_generation_fuel_combined')}"
        ).style({"margin-bottom": "2rem"})
    )

    plant_netgen_bysource_chart = (
        alt.Chart(
            this_plant__monthly_generation_fuel_combined,
            title=alt.Title(
                f"Net Generation: {this_plant.name}, {this_plant['city'] or this_plant['county']}, {this_plant['state']}",
                subtitle="By fuel type",
            ),
        )
        .mark_line()
        .encode(
            alt.X("report_date").title("Report date"),
            alt.Y("net_generation_mwh", aggregate="sum").title("Net Generation (MWh)"),
            color="fuel_type_code_pudl",
        )
    )
    mo.output.append(mo.ui.altair_chart(plant_netgen_bysource_chart))
    mo.output.append(
        mo.md(
            f"via {table_preview_href('out_eia923__monthly_generation_fuel_combined')}"
        )
    )
    return


@app.cell
def _(
    alt,
    mo,
    selection,
    this_plant,
    this_plant__generators,
    this_plant__monthly_generation,
):
    mo.stop(not selection.plant)
    mo.stop(
        this_plant__monthly_generation.shape[0] == 0,
        mo.md("No generator-level generation data available for this plant.").style(
            {"background": "#fee"}
        ),
    )
    mo.output.append(mo.md("## Generator-level generation"))
    mo.output.append(
        mo.md(
            "Here is a timeseries view of the most granular data we have available on the electricity produced by each generator at this plant. Be aware, the plot below may not account for all of the electricity reported above, because different types and sizes of generators have different reporting requirements."
        ).style({"margin-bottom": "2rem"})
    )

    n_monthly_gens = len(this_plant__monthly_generation.generator_id.unique())
    if n_monthly_gens < this_plant__generators.shape[0]:
        mo.output.append(
            mo.md(
                f"Generation data available for {n_monthly_gens} of {this_plant__generators.shape[0]} generators for this plant."
            ).style({"background": "#eee"})
        )
    bygen_chart = (
        alt.Chart(
            this_plant__monthly_generation,
            title=alt.Title(
                f"Net generation: {this_plant.name}, {this_plant['city'] or this_plant['county']}, {this_plant['state']}",
                subtitle="By generator",
            ),
        )
        .mark_line()
        .encode(
            alt.X("report_date").title("Report date"),
            alt.Y("net_generation_mwh").title("Net Generation (MWh)"),
            color="generator_id",
        )
    )
    mo.output.append(mo.ui.altair_chart(bygen_chart))
    mo.output.append(
        mo.md(f"via {table_preview_href('out_eia923__monthly_generation')}")
    )
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
    mo.stop(
        len(filters) == 0,
        mo.md("No other information about generators for this plant.").style(
            {"background": "#fee"}
        ),
    )
    mo.output.append(mo.md("## Generator Attributes"))
    mo.output.append(
        mo.md(
            f"Here is what we know about each generator at this plant.{' You can review attributes of all generators at once, or use the filters to focus on generators that meet particular criteria.' if this_plant__generators.shape[0] > 1 else ''}"
        )
    )

    if this_plant__generators.shape[0] > 1:
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

    filter_selections = [
        this_plant__generators[k].isin(v.value["multiselect"])
        for k, v in filters.items()
        if v.value["multiselect"]
    ]
    selected__generators = (
        this_plant__generators[
            functools.reduce(
                lambda accum, update: accum & update,
                filter_selections,
            )
        ]
        if filter_selections
        else this_plant__generators
    )
    if this_plant__generators.shape[0] > 1:
        mo.output.append(
            mo.md(
                (
                    "All"
                    if selected__generators.shape[0] == this_plant__generators.shape[0]
                    else f"{selected__generators.shape[0]} of"
                )
                + f" {this_plant__generators.shape[0]} generators selected"
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
    mo.stop(not filters.value)
    mo.ui.table.default_page_size = 50
    mo.output.append(
        mo.ui.table(
            selected__generators[ops_columns + nrg_columns[1:] + remaining_columns[1:]]
            .set_index("generator_id")
            .T.dropna(thresh=1),
            selection=None,
        )
    )
    mo.output.append(mo.md(f"via {table_preview_href('out_eia__yearly_generators')}"))
    return


if __name__ == "__main__":
    app.run()
