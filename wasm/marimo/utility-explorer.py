import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.output.append(mo.md("# ⚡Utility Explorer⚡"))
    mo.output.append(
        mo.md(
            'Explore attributes of any utility that reports to <a href="https://docs.catalyst.coop/pudl/data_sources/eia861.html" target="_blank">EIA-861</a>. Select a state and specific utility to explore its attributes and its electricity sources, sales, and reliability over time.'
        )
    )
    return


@app.cell
def _():
    # Imports
    import json
    from urllib.request import urlopen

    # import plotly.graph_objects as go
    # import plotly
    import altair as alt
    import pandas as pd

    import marimo as mo

    # import plotly.express as px
    return alt, json, mo, pd, urlopen


@app.cell
def _(mo, selection):
    # ~~~~ FORMAT INITIAL STATE/UTIL SELECTION ~~~~
    mo.output.append(
        mo.vstack(
            [
                mo.hstack(
                    [
                        mo.md(
                            f"""<div data-tooltip="Some utilities operate in multiple states. The dashboard data displayed will cover all states a utility operates in.">{mo.icon("lucide:info")}</div>"""
                        ),
                        selection.state_selector,
                    ],
                    justify="start",
                ),
                selection.util_selector,
            ]
        )
    )
    return


@app.cell
def _(mo, selection):
    mo.md(f"""
    #**{selection.util_name}**
    """)
    return


@app.cell
def _(pd):
    # ~~~~ HELPFUL FUNCTIONS ~~~~

    # ---- Preview tables func ----
    def table_preview_href(name):
        return f"""<a href="https://data.catalyst.coop/preview/pudl/{name}" target="_blank">{name}</a>"""

    # ---- Retreive tables func ----
    def path(name):
        return f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"

    # ---- Read tables func ----
    def pudl(name, **kwargs):
        df = pd.read_parquet(
            path(name),
            **kwargs,
        )
        # fastparquet gets the dtypes right but pyarrow seems to miss them
        if "report_date" in df.columns and df.report_date.dtype != "datetime64[s]":
            df["report_date"] = pd.to_datetime(df["report_date"])
        return df

    # ---- Turn date to year ----
    def make_report_date_report_year(df):
        df["report_year"] = df["report_date"].dt.year
        return df

    return make_report_date_report_year, pudl, table_preview_href


@app.cell
def _(selection):
    # ~~~~ MORE HELPFUL FUNCTIONS ~~~~

    # ---- Get desired year/util ----
    def get_util_years(df):
        return df[
            (df["utility_id_eia"] == selection.util_id)
            & (
                df["report_date"].dt.year.isin(
                    range(selection.start_year, selection.end_year + 1)
                )
            )
        ]

    # --- Get specific utility information from the most recent year. --- #
    def show_static_value_from_recent_year(df, col):

        util_df = df.loc[(df["utility_id_eia"] == selection.util_id)].dropna(
            subset=[col]
        )
        recent_year = util_df.report_date.dt.year.max()
        out_df = util_df.loc[util_df["report_date"].dt.year == recent_year]

        if out_df.empty:
            value = "Nothing Reported"
        else:
            value_list = out_df[col].unique().tolist()
            value = ", ".join(str(x) for x in value_list)
        return value

    return get_util_years, show_static_value_from_recent_year


@app.cell
def _(mo, pudl):
    # ~~~~ LOAD INPUT TABLES ~~~~
    with mo.status.progress_bar(
        total=9,
        title="Loading data",
        subtitle="out_eia861__yearly_utility_service_territory",
        remove_on_exit=True,
    ) as do_fetch_data:
        st_df = pudl("out_eia861__yearly_utility_service_territory")
        do_fetch_data.update(subtitle="out_eia861__yearly_utility_service_territory")
        yu_df = pudl("out_eia__yearly_utilities")
        do_fetch_data.update(subtitle="out_eia__yearly_utilities")
        od_df = pudl("core_eia861__yearly_operational_data_misc")
        do_fetch_data.update(subtitle="core_eia861__yearly_operational_data_misc")
        odr_df = pudl("core_eia861__yearly_operational_data_revenue")
        do_fetch_data.update(subtitle="core_eia861__yearly_operational_data_revenue")
        s_df = pudl("core_eia861__yearly_sales")
        do_fetch_data.update(subtitle="core_eia861__yearly_sales")
        gen_df = pudl(
            "out_eia__yearly_generators",
            columns=[
                "report_date",
                "utility_id_eia",
                "operational_status",
                "balancing_authority_code_eia",
                "plant_id_eia",
                "capacity_mw",
                "fuel_type_code_pudl",
                "technology_description",
                "plant_name_eia",
                "city",
                "generator_id",
            ],
        )
        do_fetch_data.update(subtitle="out_eia__yearly_generators")
        gen_fuel_df = pudl("out_eia923__generation_fuel_combined")
        do_fetch_data.update(subtitle="out_eia923__generation_fuel_combined")
        mfrc_df = pudl("out_eia923__monthly_fuel_receipts_costs")
        do_fetch_data.update(subtitle="out_eia923__monthly_fuel_receipts_costs")
        r_df = pudl("core_eia861__yearly_reliability")
        do_fetch_data.update(subtitle="core_eia861__yearly_reliability")
        do_fetch_data.update(subtitle="Done!")
    return (
        gen_df,
        gen_fuel_df,
        mfrc_df,
        od_df,
        odr_df,
        r_df,
        s_df,
        st_df,
        yu_df,
    )


@app.cell
def _():
    cat_colors = [
        "palevioletred",
        "purple",
        "mediumpurple",
        "lightskyblue",
        "lightseagreen",
        "turquoise",
        "aquamarine",
        "lightgreen",
        "gold",
        "goldenrod",
        "darkorange",
        "tomato",
        "firebrick",
        "mediumorchid",
        "mediumseagreen",
        "mediumslateblue",
        "mediumspringgreen",
        "mediumturquoise",
        "mediumvioletred",
        "midnightblue",
    ]
    return (cat_colors,)


@app.cell
def _(gen_df, mo, pd, st_df, yu_df):
    # ~~~~ DEFINE SELECTION OPTIONS ~~~~

    class Options:
        """Compute valid plant selection options based on partial selections.

        Caches the results so we're not constantly repeating dataframe queries.

        Used by marimo ui widgets in constructing dropdown options; used by
        selection initialization in validating/filling gaps in url params."""

        @classmethod
        @mo.cache
        def available_states(cls) -> pd.Series:
            return st_df.state.drop_duplicates().sort_values()

        @classmethod
        @mo.cache
        def available_utils(cls, state: str) -> pd.Series:
            return (
                (
                    yu_df[
                        yu_df["utility_id_eia"].isin(
                            st_df.loc[st_df.state == state, "utility_id_eia"]
                            .drop_duplicates()
                            .to_list()
                        )
                    ]
                    if state
                    else yu_df
                )[["utility_id_eia", "utility_name_eia"]]
                .drop_duplicates()
                .sort_values(by="utility_name_eia")
                .set_index("utility_id_eia")
            )

        @classmethod
        @mo.cache
        def available_years(cls, state: str, util_id: str) -> pd.Series:
            return (
                yu_df.loc[(yu_df.utility_id_eia == int(util_id))]
                .report_date.dt.year.drop_duplicates()
                .sort_values(ascending=False)
            )

        @classmethod
        @mo.cache
        def available_counties(cls, util_id: str) -> pd.Series:
            return st_df.loc[
                (st_df.utility_id_eia == int(util_id))
            ].county_id_fips.drop_duplicates()

        @classmethod
        @mo.cache
        def available_plant_status(cls) -> pd.Series:
            return gen_df.operational_status.drop_duplicates().dropna()

    return (Options,)


@app.cell
def _(initialize_default_params, query_params):
    # ~~~~ ENABLE PARAMETER RESET ~~~~

    def reset_params(**kwargs):
        """Persist selection parameters into the URL.

        Should be called whenever the user makes a change to their selection.
        Automatically updates downstream selections to valid defaults."""
        for param, value in kwargs.items():
            query_params.set(param, value)
        initialize_default_params()

    return (reset_params,)


@app.cell
def _(Options, mo, query_params, reset_params, yu_df):
    # ~~~~ CREATE SELECTION DROPDOWNS AND CACHED VALUES ~~~~

    from functools import cached_property

    from pydantic import BaseModel, computed_field

    class Selection(BaseModel):
        """Store/represent the user's current plant selection.

        The direct values (state, utility, year, etc) are pulled from
        and persisted to the corresponding URL parameters.

        The selector views (state_selector, util_selector, etc) are
        computed based on the values and cached for display in the dashboard."""

        state: str
        util_id: int
        start_year: int
        end_year: int
        plant_year: int
        plant_status: str

        @computed_field
        @cached_property
        def state_selector(self) -> mo.Html:
            return mo.ui.dropdown.from_series(
                Options.available_states(),
                label="Select a state:",
                value=self.state,
                searchable=True,
                allow_select_none=True,
                on_change=lambda value: reset_params(state=value),
            )

        @computed_field
        @cached_property
        def util_selector(self) -> mo.ui.dropdown:
            def get_util_name(util_id):
                util_record = Options.available_utils(self.state).loc[util_id]
                return f"{util_record.utility_name_eia} (id={util_record.name})"

            return mo.ui.dropdown(
                options={
                    f"{name} (id={id})": id
                    for id, name in Options.available_utils(self.state).to_records()
                },
                label="Select a Utility",
                value=get_util_name(self.util_id),
                searchable=True,
                allow_select_none=False,
                on_change=lambda value: reset_params(util_id=str(value)),
            )

        @computed_field
        @cached_property
        def start_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options=(
                    Options.available_years(self.state, self.util_id)
                    .sort_values(ascending=True)
                    .astype(str)
                ),
                label="Select a start year",
                value=self.start_year,
                searchable=True,
                on_change=lambda value: reset_params(start_year=value),
            )

        @computed_field
        @cached_property
        def end_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options=[
                    str(i)
                    for i in sorted(
                        Options.available_years(self.state, self.util_id), reverse=True
                    )
                    if i >= int(self.start_year)
                ],
                label="Select an end year",
                value=self.end_year,
                searchable=True,
                on_change=lambda value: reset_params(end_year=value),
            )

        @computed_field
        @cached_property
        def plant_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options=(
                    Options.available_years(self.state, self.util_id)
                    .sort_values(ascending=False)
                    .astype(str)
                ),
                label="Select a year",
                value=self.plant_year,
                searchable=True,
                on_change=lambda value: reset_params(plant_year=value),
            )

        @computed_field
        @cached_property
        def plant_status_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options=Options.available_plant_status(),
                label="Select plant status",
                value=self.plant_status,
                searchable=True,
                on_change=lambda value: reset_params(plant_status=value),
            )

        @computed_field
        @cached_property
        def util_name(self) -> str:
            return yu_df.loc[
                (yu_df["utility_id_eia"] == self.util_id)
                & (yu_df["report_date"].dt.year == self.plant_year)
            ].utility_name_eia.item()

    selection = Selection(**query_params.to_dict())
    return (selection,)


@app.cell
def _(Options, mo):
    # ~~~~ INITIALIZE DEFAULT PARAMETERS ~~~~

    # this has to be in a cell other than the cell where `selection` is defined,
    # otherwise updates won't propagate correctly.
    query_params = mo.query_params()

    def initialize_default_params():
        if "state" not in query_params or query_params["state"] not in set(
            Options.available_states()
        ):
            query_params["state"] = "CO"

        if "util_id" not in query_params or int(query_params["util_id"]) not in set(
            Options.available_utils(query_params["state"]).index
        ):
            query_params["util_id"] = str(
                Options.available_utils(query_params["state"]).iloc[0].name
            )
        if "start_year" not in query_params or int(
            query_params["start_year"]
        ) not in set(
            Options.available_years(query_params["state"], query_params["util_id"])
        ):
            query_params["start_year"] = str(
                Options.available_years(
                    query_params["state"], query_params["util_id"]
                ).iloc[-1]
            )

        if "end_year" not in query_params or int(query_params["end_year"]) not in set(
            Options.available_years(query_params["state"], query_params["util_id"])
        ):
            query_params["end_year"] = str(
                Options.available_years(
                    query_params["state"], query_params["util_id"]
                ).iloc[0]
            )
        if "plant_year" not in query_params or int(
            query_params["plant_year"]
        ) not in set(
            Options.available_years(query_params["state"], query_params["util_id"])
        ):
            query_params["plant_year"] = str(
                Options.available_years(
                    query_params["state"], query_params["util_id"]
                ).iloc[0]
            )
        if "plant_status" not in query_params or query_params[
            "plant_status"
        ] not in set(Options.available_plant_status()):
            query_params["plant_status"] = "existing"

    initialize_default_params()
    return initialize_default_params, query_params


@app.cell
def _(
    gen_df,
    mo,
    num_plants_owned,
    od_df,
    pd,
    selection,
    show_static_value_from_recent_year,
    st_df,
    table_preview_href,
    total_cap,
    yu_df,
):
    # ~~~~ BUILD UTILITY STATS TABLE ~~~~

    # ---- Get stats from data ----
    address = show_static_value_from_recent_year(yu_df, "street_address")
    states = show_static_value_from_recent_year(st_df, "state")
    entity_type = show_static_value_from_recent_year(od_df, "entity_type")
    ba = show_static_value_from_recent_year(gen_df, "balancing_authority_code_eia")

    # ---- Build stats table ----
    stats_table = mo.ui.table(
        pd.DataFrame(
            [
                {
                    "Value": str(selection.util_id),
                    "Reference Table": "",
                },
                {
                    "Value": entity_type,
                    "Reference Table": mo.md(
                        table_preview_href("core_eia861__yearly_operational_data_misc")
                    ),
                },
                {
                    "Value": address,
                    "Reference Table": mo.md(
                        table_preview_href("out_eia__yearly_utilities")
                    ),
                },
                {
                    "Value": states,
                    "Reference Table": mo.md(
                        table_preview_href(
                            "out_eia861__yearly_utility_service_territory"
                        )
                    ),
                },
                {
                    "Value": ba,
                    "Reference Table": mo.md(
                        table_preview_href("out_eia__yearly_generators")
                    ),
                },
                {
                    "Value": num_plants_owned,
                    "Reference Table": mo.md(
                        table_preview_href("out_eia__yearly_generators")
                    ),
                },
                {
                    "Value": total_cap,
                    "Reference Table": mo.md(
                        table_preview_href("out_eia__yearly_generators")
                    ),
                },
            ],
            index=[
                "Utility ID EIA",
                "Business Type",
                "Address",
                "States",
                "Balancing Authority",
                "Total Plants Owned",
                "Total Owned Capacity (MW)",
            ],
        ),
        selection=None,
        show_data_types=False,
        wrapped_columns=["Value"],
    )
    return (stats_table,)


@app.cell
def _(Options, alt, json, pd, selection, urlopen):
    # ~~~~ GENERATE MAP FOR SERVICE TERRITORY ~~~~

    with urlopen(
        "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    ) as _r:
        _geojson = json.load(_r)

    with urlopen(
        "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
    ) as _r:
        _states_geojson = json.load(_r)

    # --- build the same plot dataframe ---
    fips_set = set(Options.available_counties(util_id=selection.util_id).str.zfill(5))
    _all_fips = [f["id"] for f in _geojson["features"]]
    _plot_df = pd.DataFrame(
        {
            "fips": _all_fips,
            "in_df": [1 if f in fips_set else 0 for f in _all_fips],
        }
    )

    # --- county choropleth ---
    counties = alt.topo_feature(
        "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json", "counties"
    )
    states_map = alt.topo_feature(
        "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json", "states"
    )

    county_layer = (
        alt.Chart(counties)
        .mark_geoshape(stroke="black", strokeWidth=0.3)
        .transform_lookup(
            lookup="id",
            from_=alt.LookupData(data=_plot_df, key="fips", fields=["in_df"]),
            default="0",
        )
        .encode(
            color=alt.condition(
                alt.datum.in_df == 1,
                alt.value("#1a237e"),
                alt.value("#e8eaf6"),
            ),
            tooltip="id:N",
        )
    )

    state_layer = alt.Chart(states_map).mark_geoshape(
        fill=None, stroke="black", strokeWidth=1.5
    )

    st_chart = (
        alt.layer(county_layer, state_layer)
        .project("albersUsa")
        .properties(width="container", height=560)
        .configure_view(stroke=None)
    )
    return fips_set, st_chart


@app.cell
def _(fips_set, mo, selection, st_chart, stats_table, table_preview_href):
    # ~~~~ COMBINE AND DISPLAY UTIL STATS WITH SERVICE TERRITORY MAP ~~~~
    # TO-DO: Make it slide horizontally

    if not fips_set:
        service_ter_chart = f"*No service territory reported for {selection.util_name}*"
    else:
        service_ter_chart = mo.ui.altair_chart(
            st_chart.properties(width="container", height=300)
        )

    if not fips_set:
        service_ter_chart = mo.md(
            f"*No service territory data for {selection.util_name}.*"
        )

    util_stats = mo.vstack(
        [
            mo.md("## Basic Information"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("### Utility Stats"),
                            mo.Html(
                                f'<div style="width: 600px">{stats_table.text}</div>'
                            ),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("### Service Territory"),
                            service_ter_chart,
                            mo.md(
                                f"via {table_preview_href('out_eia861__yearly_utility_service_territory')}"
                            ),
                        ]
                    ),
                ],
                justify="space-between",
            ),
        ]
    )
    util_stats
    return


@app.cell
def _(pd):
    def agg_plant_values(df, op_status):

        df = df[df["operational_status"] == op_status]

        plant_cols = [
            "generator_id",  # aggregate into list
            "plant_name_eia",  # choose first
            "technology_description",  # aggregate into list
            "fuel_type_code_pudl",  # list
            "capacity_mw",  # sum
            "city",  # list
        ]

        util_plant_df = (
            df.groupby(["report_date", "plant_id_eia"])[plant_cols]
            .agg(
                {
                    "generator_id": lambda x: ", ".join(
                        v for v in x.unique() if v is not None
                    ),
                    "plant_name_eia": "first",
                    "technology_description": lambda x: ", ".join(
                        v for v in x.unique() if v is not None
                    ),
                    "fuel_type_code_pudl": lambda x: ", ".join(
                        v for v in x.unique() if v is not None
                    ),
                    "capacity_mw": lambda x: f"{x.sum():.2f}",
                    "city": lambda x: ", ".join(
                        v for v in x.unique() if v is not pd.NA
                    ),
                }
            )
            .reset_index()
        )

        util_plant_df["report_year"] = util_plant_df["report_date"].dt.year.astype(
            "str"
        )
        util_plant_df = util_plant_df.drop(columns=["report_date"])
        return util_plant_df

    return (agg_plant_values,)


@app.cell
def _(gen_df, pd, selection):
    # ~~~~ PREP CONTENT FOR UTIL STATS TABLE ~~~~

    util_gen = gen_df[gen_df["utility_id_eia"] == selection.util_id].sort_values(
        "report_date", ascending=False
    )

    util_gen_existing = pd.DataFrame()

    if not util_gen.empty:
        recent_report_date = util_gen["report_date"].dt.year.iloc[0]
        util_gen_existing = util_gen[
            (util_gen["report_date"].dt.year == recent_report_date)
            & (util_gen["operational_status"] == "existing")
        ]

    # For util stats table
    if not util_gen_existing.empty:
        num_plants_owned = len(util_gen_existing.plant_id_eia.unique())
        total_cap = round(util_gen_existing.capacity_mw.sum())
    else:
        num_plants_owned = "No owned generation reported"
        total_cap = "No capacity to report"
    return num_plants_owned, total_cap, util_gen


@app.cell
def _(agg_plant_values, mo, selection, util_gen):
    # Display selected plant table
    selected_year_util_gen = util_gen[
        util_gen["report_date"].dt.year == selection.plant_year
    ]

    status_df = agg_plant_values(selected_year_util_gen, selection.plant_status)

    owned_gen_selection = mo.vstack(
        [
            mo.md("## Owned Capacity"),
            mo.hstack(
                [selection.plant_year_selector, selection.plant_status_selector],
                justify="start",
            ),
        ]
    )

    owned_gen_selection
    return (status_df,)


@app.cell
def _(mo, selection, status_df, table_preview_href):
    (
        mo.stop(
            status_df.empty,
            mo.md(
                f"*{selection.util_name} has no {selection.plant_status} owned capacity.*"
            ),
        ),
    )
    mo.vstack(
        [
            mo.Html(
                f'<div style="max-width: 1000px">{mo.ui.table(status_df, show_data_types=False, selection=None).text if not status_df.empty else ""}</div>'
            ),
            mo.md(f"via {table_preview_href('out_eia__yearly_generators')}"),
        ]
    )
    return


@app.cell
def _(alt, cat_colors, gen_fuel_df, selection):
    # ~~~~ GENERATE FUEL CHART ~~~~

    util_gen_fuel = gen_fuel_df[gen_fuel_df["utility_id_eia"] == selection.util_id]

    fuel_year_df = util_gen_fuel[
        util_gen_fuel["report_date"].dt.year.isin(
            range(selection.start_year, selection.end_year + 1)
        )
    ]

    fuel_long = (
        fuel_year_df.groupby(["report_date", "fuel_type_code_pudl"])[
            "net_generation_mwh"
        ]
        .sum()
        .reset_index()
    )

    def pick_fuel_ticks():
        years = selection.end_year - selection.start_year
        if years <= 2:
            return "month"
        if years <= 5:
            # quarters
            return {"interval": "month", "step": 3}
        # otherwise
        return "year"

    fuel_chart = (
        alt.Chart(fuel_long)
        .mark_area()
        .encode(
            x=alt.X(
                "report_date:T",
                axis=alt.Axis(format="%Y-%m", tickCount=pick_fuel_ticks()),
                title="Date",
            ),
            y=alt.Y(
                "net_generation_mwh:Q",
                stack="zero",
                title="Net Generation (MWh)",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "fuel_type_code_pudl:N",
                scale=alt.Scale(range=cat_colors),
                legend=alt.Legend(title="Fuel Type"),
            ),
            tooltip=[
                alt.Tooltip("report_date:T", title="Date", format="%Y-%m"),
                alt.Tooltip("fuel_type_code_pudl:N", title="Fuel Type"),
                alt.Tooltip(
                    "net_generation_mwh:Q", title="Net Generation (MWh)", format=",.0f"
                ),
            ],
        )
        .properties(
            width="container",
            height=400,
        )
    )
    return fuel_chart, fuel_long


@app.cell
def _(alt, cat_colors, od_df, selection):
    util_od_df = od_df[od_df["utility_id_eia"] == selection.util_id]

    # Define value cols
    value_cols = [
        "net_generation_mwh",
        "wholesale_power_purchases_mwh",
        "net_power_exchanged_mwh",
        "net_wheeled_power_mwh",
        "transmission_by_other_losses_mwh",
    ]

    # Get year of interest
    source_year_df = util_od_df[
        util_od_df["report_date"].dt.year.isin(
            range(selection.start_year, selection.end_year + 1)
        )
    ]
    # source_year_df["report_date"] = source_year_df.report_date.dt.year

    # Melt to long format for Altair
    od_long = source_year_df[["report_date"] + value_cols].melt(
        id_vars="report_date",
        value_vars=value_cols,
        var_name="source",
        value_name="mwh",
    )

    # Remove all-zero columns
    nonzero_sources = [
        col for col in value_cols if not (source_year_df[col] == 0).all()
    ]
    od_long = od_long[od_long["source"].isin(nonzero_sources)]

    # Split into positive and negative
    od_pos = od_long[od_long["mwh"] > 0]
    od_neg = od_long[od_long["mwh"] < 0]

    base = alt.Chart().encode(
        x=alt.X("year(report_date):O", title="Year"),
        color=alt.Color(
            "source:N",
            scale=alt.Scale(range=cat_colors),
            legend=alt.Legend(orient="right", columns=1, labelLimit=300, offset=10),
        ),
        tooltip=[
            alt.Tooltip("report_date:T", title="Year", format="%Y"),
            alt.Tooltip("mwh:Q", title="Net Generation (Mwh)", format=","),
            alt.Tooltip("source:N", title="Source"),
        ],
    )
    pos_chart = (
        base.mark_bar(width={"band": 0.8})
        .encode(
            y=alt.Y("sum(mwh):Q", stack="zero", title="Net Generation (MWh)"),
        )
        .properties(data=od_pos, width="container")
    )
    neg_chart = (
        base.mark_bar(width={"band": 0.8})
        .encode(
            y=alt.Y("sum(mwh):Q", stack="zero"),
        )
        .properties(data=od_neg, width="container")
    )

    source_chart = alt.layer(pos_chart, neg_chart)
    return source_chart, util_od_df


@app.cell
def _():
    return


@app.cell
def _(fuel_chart, fuel_long, mo, selection, source_chart, table_preview_href):
    # ~~~~ YEAR RANGE SELECTION AND DISPLAY FOR ELECTRICITY SOURCE

    if fuel_long.empty:
        fuel_chart_mo = mo.md(f"*{selection.util_name} has no owned generation*")
    else:
        fuel_chart_mo = mo.ui.altair_chart(
            fuel_chart.properties(width="container", height=250)
        )

    electricity_source = mo.vstack(
        [
            mo.md("## Electricity Source"),
            mo.hstack(
                [selection.start_year_selector, selection.end_year_selector],
                justify="start",
            ),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("### Owned Generation by Fuel Type"),
                            fuel_chart_mo,
                            mo.md(
                                f"via {table_preview_href('out_eia923__generation_fuel_combined')}"
                            ),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("### Owned vs. Purchased Generation"),
                            mo.ui.altair_chart(
                                source_chart.properties(width="container", height=250)
                            ),
                            mo.md(
                                f"via {table_preview_href('core_eia861__yearly_operational_data_misc')}"
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )
    electricity_source
    return


@app.cell
def _(mfrc_df, selection):
    util_mfrc_df = mfrc_df[
        (mfrc_df["utility_id_eia"] == selection.util_id)
        & (
            mfrc_df["report_date"].dt.year.isin(
                range(selection.start_year, selection.end_year + 1)
            )
        )
    ]
    return (util_mfrc_df,)


@app.cell
def _(util_mfrc_df):
    fuel_cost_df = util_mfrc_df.groupby(["report_date", "fuel_type_code_pudl"])[
        [
            "fuel_cost_per_mmbtu",
            "fuel_received_mmbtu",
        ]
    ].sum()

    fuel_cost_df["fuel_cost_received"] = (
        fuel_cost_df["fuel_cost_per_mmbtu"] * fuel_cost_df["fuel_received_mmbtu"]
    )
    return


@app.cell
def _(alt, cat_colors, mo, selection, util_mfrc_df):
    # annual aggregate with volume-weighted price
    annual = (
        util_mfrc_df.assign(
            fuel_cost=util_mfrc_df.fuel_cost_per_mmbtu
            * util_mfrc_df.fuel_received_mmbtu
        )
        .groupby(
            [util_mfrc_df.report_date.dt.year.rename("year"), "fuel_type_code_pudl"]
        )
        .agg(mmbtu=("fuel_received_mmbtu", "sum"), fuel_cost=("fuel_cost", "sum"))
        .assign(price=lambda d: d.fuel_cost / d.mmbtu)
        .reset_index()
    )
    annual = annual.loc[annual["mmbtu"] > 0]

    base1 = alt.Chart(annual).encode(
        x=alt.X("mmbtu:Q", title="Fuel received (MMBtu)"),
        y=alt.Y("price:Q", title="Delivered cost ($/MMBtu)"),
        color=alt.Color(
            "fuel_type_code_pudl:N",
            legend=alt.Legend(title="Fuel type"),
            scale=alt.Scale(range=cat_colors),
        ),
        detail="fuel_type_code_pudl:N",
        order="year:O",
        tooltip=[
            alt.Tooltip("fuel_type_code_pudl:N", title="Fuel"),
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("mmbtu:Q", title="MMBtu received", format=",.0f"),
            alt.Tooltip("price:Q", title="$/MMBtu", format="$.2f"),
            alt.Tooltip("fuel_cost:Q", title="Total spend", format="$,.0f"),
        ],
    )

    lines = base1.mark_line(point=True, interpolate="catmull-rom", strokeWidth=2)

    labels = base1.mark_text(dy=-10, fontSize=11).encode(text="year:O")

    endpoints = (
        base1.transform_window(
            rank="rank()",
            sort=[alt.SortField("year", order="descending")],
            groupby=["fuel_type_code_pudl"],
        )
        .transform_filter("datum.rank == 1")
        .mark_text(dx=12, align="left", fontWeight="bold", fontSize=12)
        .encode(text="fuel_type_code_pudl:N")
    )

    if util_mfrc_df.empty:
        fuel_cost_chart = mo.md(f"*{selection.util_name} does not have purchased fuel*")
    else:
        fuel_cost_chart = (lines + labels + endpoints).properties(
            width="container", height=380
        )
    return (fuel_cost_chart,)


@app.cell
def _(fuel_cost_chart, mo, table_preview_href):
    fuel_cost = mo.vstack(
        [
            mo.md("### Fuel Cost vs. Fuel Received"),
            fuel_cost_chart,
            mo.md(
                f"via {table_preview_href('out_eia923__monthly_fuel_receipts_costs')}"
            ),
        ]
    )
    fuel_cost
    return


@app.cell
def _(make_report_date_report_year, s_df, selection):
    # ~~~~ PIVOT TABLE FOR SALES and REV CHART ~~~~

    s_df_util = s_df[
        (s_df["utility_id_eia"] == selection.util_id)
        & (
            s_df["report_date"].dt.year.isin(
                range(selection.start_year, selection.end_year + 1)
            )
        )
    ]
    pivot = (
        s_df_util.pivot_table(
            index="report_date",
            columns="customer_class",
            values=["sales_mwh", "sales_revenue"],
            aggfunc="sum",
        )
        .sort_index()
        .reset_index()
    )

    sales_long = make_report_date_report_year(
        pivot.set_index("report_date")
        .stack(level="customer_class")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return (sales_long,)


@app.cell
def _(alt, cat_colors, mo, sales_long):
    combined_sales_chart = mo.ui.altair_chart(
        alt.Chart(
            # rename columns so that we can use a repeat chart
            # and still have nice axis titles
            sales_long.rename(
                columns={
                    "sales_mwh": "Sales (MWh)",
                    "sales_revenue": "Revenue ($)",
                }
            )
        )
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y(
                alt.repeat("column"),
                type="quantitative",
                stack="zero",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "customer_class:N",
                scale=alt.Scale(range=cat_colors),
                legend=alt.Legend(title="Customer Class", orient="bottom"),
            ),
            order=alt.Order("customer_class:N"),
            tooltip=[
                alt.Tooltip("report_year:T", title="Year", format="%Y"),
                alt.Tooltip("customer_class:N", title="Customer Class"),
                alt.Tooltip(alt.repeat("column"), type="quantitative", format=",.0f"),
            ],
        )
        .repeat(
            column=["Sales (MWh)", "Revenue ($)"],
        )
        # sad note: can't use width="container" here because
        # marimo-altair-vega doesn't pass container widths properly
        # to combo charts
        .properties(title="Retail Sales and Revenue by Customer Class")
    )
    return (combined_sales_chart,)


@app.cell
def _(alt, cat_colors, get_util_years, make_report_date_report_year, odr_df):
    # REVENUE CHART

    odr_year_util_df = make_report_date_report_year(get_util_years(odr_df))

    revenue_class_chart = (
        alt.Chart(odr_year_util_df)
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y(
                "revenue:Q",
                stack="zero",
                title="Revenue ($)",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "revenue_class:N",
                scale=alt.Scale(range=cat_colors),
                legend=alt.Legend(title="Revenue Class", orient="bottom"),
            ),
            order=alt.Order("revenue_class:N"),
            tooltip=[
                alt.Tooltip("report_year:T", title="Year", format="%Y"),
                alt.Tooltip("revenue_class:N", title="Revenue Class"),
                alt.Tooltip("sales_revenue:Q", title="Revenue ($)", format=",.0f"),
            ],
        )
        .properties(
            title="Total Revenue ($) by Revenue Class",
        )
    )
    return (revenue_class_chart,)


@app.cell
def _(get_util_years, make_report_date_report_year, r_df):
    # RELIABILITY

    r_util_year_df = get_util_years(r_df)
    r_util_year_df = r_util_year_df[r_util_year_df["standard"] == "ieee_standard"]

    caidi_cols = [c for c in r_util_year_df.columns if c.startswith("caidi")] + [
        "report_year"
    ]
    caidi_df = make_report_date_report_year(r_util_year_df)[caidi_cols]
    saidi_cols = [c for c in r_util_year_df.columns if c.startswith("saidi")] + [
        "report_year"
    ]
    saidi_df = make_report_date_report_year(r_util_year_df)[saidi_cols]
    saifi_cols = [c for c in r_util_year_df.columns if c.startswith("saifi")] + [
        "report_year"
    ]
    saifi_df = make_report_date_report_year(r_util_year_df)[saifi_cols]
    return caidi_df, saidi_df, saifi_df


@app.cell
def _(alt, cat_colors, saidi_df):
    # SAIDI CHART

    saidi_long = saidi_df.copy().melt(
        id_vars="report_year",
        value_vars=[c for c in saidi_df.columns if c.startswith("saidi")],
        var_name="metric",
        value_name="value",
    )

    saidi = (
        alt.Chart(saidi_long)
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y("value:Q", title="Minutes Without Power"),
            xOffset=alt.XOffset("metric:N"),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(range=cat_colors),
                legend=alt.Legend(
                    orient="bottom", columns=1, labelLimit=300, offset=10
                ),
            ),
            tooltip=[
                alt.Tooltip("report_year:O", title="Year"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="System Average Interruption Duration Index (SAIDI)",
                subtitle="Total length of time (minutes) an average customer is without power per year",
            ),
            width="container",
        )
    )
    return (saidi,)


@app.cell
def _(alt, caidi_df, cat_colors):
    # CAIDI CHART

    caidi_long = caidi_df.melt(
        id_vars="report_year",
        value_vars=[c for c in caidi_df.columns if c.startswith("caidi")],
        var_name="metric",
        value_name="value",
    )

    caidi = (
        alt.Chart(caidi_long)
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y("value:Q", title="Number of Interruptions"),
            xOffset=alt.XOffset("metric:N"),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(range=cat_colors),
                legend=alt.Legend(
                    orient="bottom", columns=1, labelLimit=300, offset=10
                ),
            ),
            tooltip=[
                alt.Tooltip("report_year:O", title="Year"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="Customer Average Interruption Duration Index (CAIDI)",
                subtitle="Length of time (minutes) that an average customer is without power during an event",
            ),
            width="container",
        )
    )
    return (caidi,)


@app.cell
def _(alt, cat_colors, saifi_df):
    # SAIFI CHART

    saifi_long = saifi_df.melt(
        id_vars="report_year",
        value_vars=[c for c in saifi_df.columns if c.startswith("saifi")],
        var_name="metric",
        value_name="value",
    )

    saifi = (
        alt.Chart(saifi_long)
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y("value:Q", title="Number of Interruptions per Customer"),
            xOffset=alt.XOffset("metric:N"),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(range=cat_colors),
                legend=alt.Legend(
                    orient="bottom", columns=1, labelLimit=300, offset=10
                ),
            ),
            tooltip=[
                alt.Tooltip("report_year:O", title="Year"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.2f"),
            ],
        )
        .properties(
            title=alt.TitleParams(
                text="System Average Interruption Frequency Index (SAIFI)",
                subtitle="How often the average customer experiences interruptions per year",
            ),
            width="container",
        )
    )
    return (saifi,)


@app.cell
def _(
    caidi,
    combined_sales_chart,
    mo,
    revenue_class_chart,
    saidi,
    saifi,
    table_preview_href,
):
    customer_facing = mo.vstack(
        [
            mo.md("## Customer-Facing"),
            mo.vstack(
                [
                    mo.md("### Sales"),
                    mo.ui.tabs(
                        {
                            "By Customer Class": combined_sales_chart,
                            "By Revenue Class": revenue_class_chart,
                        }
                    ),
                    mo.md(f"via {table_preview_href('core_eia861__yearly_sales')}"),
                ]
            ),
            mo.vstack(
                [
                    mo.md("### Reliability"),
                    mo.ui.tabs({"SAIDI": saidi, "SAIFI": saifi, "CAIDI": caidi}),
                    mo.md(
                        f"via {table_preview_href('core_eia861__yearly_reliability')}"
                    ),
                ]
            ),
        ],
        # make a larger gap between subsections than within each subsection
        gap=1,
    )

    customer_facing
    return


@app.cell
def _(alt, cat_colors, util_od_df):
    peak_long = util_od_df[
        ["report_date", "summer_peak_demand_mw", "winter_peak_demand_mw"]
    ].melt(
        id_vars="report_date",
        var_name="season",
        value_name="mw",
    )

    summer_v_winter_demand_chart = (
        alt.Chart(peak_long)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X(
                "report_date:T",
                axis=alt.Axis(format="%Y", tickCount="year"),
                title="Year",
            ),
            y=alt.Y("mw:Q", title="MW"),
            color=alt.Color(
                "season:N",
                scale=alt.Scale(
                    domain=["summer_peak_demand_mw", "winter_peak_demand_mw"],
                    range=cat_colors,
                ),
                legend=alt.Legend(orient="right"),
            ),
            tooltip=["report_date:T", "season:N", "mw:Q"],
        )
        .properties(
            title="Summer vs. Winter Peak Demand",
            width="container",
            height=400,
        )
    )
    return (summer_v_winter_demand_chart,)


@app.cell
def _(mo, summer_v_winter_demand_chart, table_preview_href):
    demand = mo.vstack(
        [
            mo.md("### Peak Demand"),
            summer_v_winter_demand_chart,
            mo.md(
                f"via {table_preview_href('core_eia861__yearly_operational_data_misc')}"
            ),
        ]
    )

    demand
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    If you see anything odd in the data, find a bug or just have a question, feel free to reach out to us by emailing us at hello@catalyst.coop or write up a <a href="https://github.com/catalyst-cooperative/pudl/issues/new?template=bug_report.md" target="_blank">github issue</a>. Heck, if you just found this helpful, let us know! As an open-source project we love to hear about your energy data needs.
    """)
    return


if __name__ == "__main__":
    app.run()
