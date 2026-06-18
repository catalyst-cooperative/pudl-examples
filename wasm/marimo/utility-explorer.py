import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    # Imports
    import pandas as pd
    import marimo as mo

    # import plotly.graph_objects as go
    # import plotly
    import altair as alt
    import json
    from urllib.request import urlopen

    # import plotly.express as px
    return alt, json, mo, pd, urlopen


@app.cell
def _(mo, selection):
    mo.output.append(mo.md("# Utility Explorer"))
    mo.output.append(
        mo.md(
            'Explore attributes of any utility that reports to <a href="https://docs.catalyst.coop/pudl/data_sources/eia861.html" target="_blank">EIA-861</a>. Select a state and specific utility to explore its attributes, generation over time and generators.'
        )
    )
    mo.output.append(mo.vstack([selection.state_selector, selection.util_selector]))
    return


@app.cell
def _():
    ###
    # Wherever displaying state selector: change to selection.state_selector
    # Wherever accessing selected state: change to selection.state
    return


@app.function
# Preview tables
def table_preview_href(name):
    return f"""<a href="https://data.catalyst.coop/preview/pudl/{name}" target="_blank">{name}</a>"""


@app.cell
def _(pd):
    # Retreive tables func
    def path(name):
        return f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"

    # Read tables func
    def pudl(name, columns=None):
        return pd.read_parquet(
            path(name),
            engine="fastparquet",
            **({"columns": columns} if columns else {}),
        )

    # Grab tables
    st_df = pudl("out_eia861__yearly_utility_service_territory")
    yu_df = pudl("out_eia__yearly_utilities")
    od_df = pudl("core_eia861__yearly_operational_data_misc")
    odr_df = pudl("core_eia861__yearly_operational_data_revenue")
    s_df = pudl("core_eia861__yearly_sales")
    gen_df = pudl("out_eia__yearly_generators")
    gen_fuel_df = pudl("out_eia923__generation_fuel_combined")
    mfrc_df = pudl("out_eia923__monthly_fuel_receipts_costs")
    r_df = pudl("core_eia861__yearly_reliability")
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
def _(mo, pd, st_df, yu_df):
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
                .sort_values(by="utility_name_eia")["utility_name_eia"]
            )

        # For utilities, add a function that filters based on the available states (see plant_explorer notebook)

    return (Options,)


@app.cell
def _(initialize_default_params, query_params):
    def reset_params(**kwargs):
        """Persist selection parameters into the URL.

        Should be called whenever the user makes a change to their selection.
        Automatically updates downstream selections to valid defaults."""
        for param, value in kwargs.items():
            query_params.set(param, value)
        initialize_default_params()

    return (reset_params,)


@app.cell
def _(Options, mo, query_params, reset_params):
    from pydantic import BaseModel, computed_field
    from functools import cached_property

    class Selection(BaseModel):
        """Store/represent the user's current plant selection.

        The direct values (state, county, plant, etc) are pulled from
        and persisted to the corresponding URL parameters.

        The selector views (state_selector, county_selector, etc) are
        computed based on the values and cached for display in the dashboard."""

        state: str
        util: str

        @computed_field
        @cached_property
        def state_selector(self) -> mo.Html:
            # return mo.hstack([
            #     mo.md(f"""<div data-tooltip="Some utilities operate in multiple states. Use the state selector to help narrow down your utility search, but know that utility information from multiple states will show where applicable.">{mo.icon("lucide:info")}</div>"""),
            return mo.ui.dropdown.from_series(
                Options.available_states(),
                label="Select a state:",
                value=self.state,
                searchable=True,
                allow_select_none=True,
                on_change=lambda value: reset_params(state=value),
            )
            # ], justify="start")

        @computed_field
        @cached_property
        def util_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown.from_series(
                Options.available_utils(self.state),
                label="Select a Utility",
                value=self.util,
                searchable=True,
                allow_select_none=False,
                on_change=lambda value: reset_params(util=value),
            )

    # default_util = in_state_utils_stats.iloc[0]
    # selected_util = mo.ui.dropdown(
    #     options={
    #         f"{name} (id={id})": id for id, name in in_state_utils_stats.to_records()
    #     },
    #     value=f"{default_util.utility_name_eia} (id={default_util.name})",
    #     label="Select a Utility:",
    #     searchable=True,
    # )

    selection = Selection(**query_params.to_dict())
    return (selection,)


@app.cell
def _(Options, mo):
    # this has to be in a cell other than the cell where `selection` is defined,
    # otherwise updates won't propagate correctly.
    query_params = mo.query_params()

    def initialize_default_params():
        if "state" not in query_params or query_params["state"] not in set(
            Options.available_states()
        ):
            query_params["state"] = "CO"

        if "util" not in query_params or query_params["util"] not in set(
            Options.available_utils(query_params["state"])
        ):
            query_params["util"] = Options.available_utils(query_params["state"]).iloc[
                0
            ]

    initialize_default_params()
    return initialize_default_params, query_params


@app.cell
def _(end_year, selected_util, start_year):
    # Get desired year/util func
    def get_util_years(df):
        return df[
            (df["utility_id_eia"] == selected_util.value)
            & (
                df["report_date"].dt.year.isin(
                    range(start_year.value, end_year.value + 1)
                )
            )
        ]

    return (get_util_years,)


@app.cell
def _():
    # # State selection
    # selected_state = mo.ui.dropdown.from_series(
    #     Options.available_states(),
    #     label="Select a state:",
    #     value="CO",
    #     searchable=True,
    #     allow_select_none=True,
    # )

    # selected_state_full = mo.hstack([
    #     mo.md(f"""<div data-tooltip="Some utilities operate in multiple states. Use the state selector to help narrow down your utility search, but know that utility information from multiple states will show where applicable.">{mo.icon("lucide:info")}</div>"""),
    #     selected_state
    # ], justify="start",)
    return


@app.cell
def _(selected_state_full):
    selected_state_full
    return


@app.cell
def _(mo, selection, st_df, yu_df):
    # Utility selection
    in_state_utils_stats = (
        (
            yu_df[
                yu_df["utility_id_eia"].isin(
                    st_df.loc[st_df.state == selection.state, "utility_id_eia"]
                    .drop_duplicates()
                    .to_list()
                )
            ]
            if selection.state
            else yu_df
        )[["utility_id_eia", "utility_name_eia"]]
        .drop_duplicates()
        .sort_values(by="utility_name_eia")
        .set_index("utility_id_eia")
    )
    default_util = in_state_utils_stats.iloc[0]
    selected_util = mo.ui.dropdown(
        options={
            f"{name} (id={id})": id for id, name in in_state_utils_stats.to_records()
        },
        value=f"{default_util.utility_name_eia} (id={default_util.name})",
        label="Select a Utility:",
        searchable=True,
    )
    return (selected_util,)


@app.cell
def _(selected_util, st_df):
    # County selection (for service ter)
    util_counties = st_df[st_df["utility_id_eia"] == selected_util.value]
    max_year = util_counties.report_date.dt.year.max()
    util_counties_year = util_counties[util_counties["report_date"].dt.year == max_year]
    return (util_counties_year,)


@app.cell
def _(selected_util):
    # Function to grab specific utility information from the most recent year.
    def show_static_value(df, col):
        out_df = (
            df[df["utility_id_eia"] == selected_util.value]
            .sort_values(["report_date"], ascending=False)
            .dropna(subset=[col])
        )
        recent_report_date = out_df.report_date.iloc[0]

        if out_df.empty:
            value = "Nothing Reported"
            year = "N/A"
        else:
            value_list = (
                out_df[out_df["report_date"] == recent_report_date][col]
                .unique()
                .tolist()
            )
            value = ", ".join(str(x) for x in value_list)
            year = recent_report_date.year
        return value, year

    return (show_static_value,)


@app.cell
def _(gen_df, od_df, show_static_value, st_df, yu_df):
    # Grab utility stats
    util_name, util_name_year = show_static_value(yu_df, "utility_name_eia")
    address, address_year = show_static_value(yu_df, "street_address")
    states, states_year = show_static_value(st_df, "state")
    entity_type, entity_year = show_static_value(od_df, "entity_type")
    ba, ba_year = show_static_value(gen_df, "balancing_authority_code_eia")

    # Grab capacity stats
    return address, ba, entity_type, states


@app.cell
def _(
    address,
    ba,
    entity_type,
    mo,
    num_plants_owned,
    pd,
    selected_util,
    st_fig,
    states,
    total_cap,
):
    stats_table = mo.ui.table(
        pd.DataFrame(
            [
                {
                    "Value": str(selected_util.value),
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
                    "Value": round(total_cap),
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
        )
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
                            mo.ui.plotly(st_fig.update_layout(width=500, height=300)),
                        ]
                    ),
                ],
                justify="space-between",
            ),
        ]
    )
    return (util_stats,)


@app.cell
def _(util_stats):
    util_stats
    return


@app.cell
def _(gen_df, selected_util):
    util_gen = gen_df[gen_df["utility_id_eia"] == selected_util.value].sort_values(
        "report_date", ascending=False
    )

    recent_report_date = util_gen["report_date"].iloc[0]

    util_gen_existing = util_gen[
        (util_gen["report_date"] == recent_report_date)
        & (util_gen["operational_status"] == "existing")
    ]

    # For util stats table
    num_plants_owned = len(util_gen_existing.plant_id_eia.unique())
    total_cap = util_gen_existing.capacity_mw.sum()

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
                    "city": lambda x: ", ".join(v for v in x.unique() if v is not None),
                }
            )
            .reset_index()
        )

        util_plant_df["report_year"] = util_plant_df["report_date"].dt.year.astype(
            "str"
        )
        util_plant_df = util_plant_df.drop(columns=["report_date"])
        return util_plant_df

    return agg_plant_values, num_plants_owned, total_cap, util_gen


@app.cell
def _(gen_fuel_df, mo, selected_util):
    # Drop down for selecting which year of plants to show

    util_gen_fuel = gen_fuel_df[gen_fuel_df["utility_id_eia"] == selected_util.value]

    available_years = sorted(
        util_gen_fuel["report_date"].dt.year.unique(), reverse=True
    )

    selected_plant_year = mo.ui.dropdown(
        options=[int(y) for y in available_years],
        value=int(available_years[0]),
        label="Select year:",
    )
    return available_years, selected_plant_year, util_gen_fuel


@app.cell
def _(available_years, mo):
    available_years_ascending = available_years[::-1]

    start_year = mo.ui.dropdown(
        options=[int(y) for y in available_years_ascending],
        value=int(available_years_ascending[0]),
        label="Start year:",
    )

    end_year = mo.ui.dropdown(
        options=[int(y) for y in available_years_ascending],
        value=int(available_years_ascending[-1]),
        label="End year:",
    )
    return end_year, start_year


@app.cell
def _(mo):
    # Create drop down for selecting which plant table to show
    selected_status = mo.ui.dropdown(
        options=["existing", "proposed", "retired"],
        value="existing",
        label="Select generator status:",
    )
    return (selected_status,)


@app.cell
def _(agg_plant_values, mo, selected_plant_year, selected_status, util_gen):
    # Display selected plant table
    selected_year_util_gen = util_gen[
        util_gen["report_date"].dt.year == selected_plant_year.value
    ]

    status_df = agg_plant_values(selected_year_util_gen, selected_status.value)

    owned_gen = mo.vstack(
        [
            mo.md("## Owned Capacity"),
            mo.vstack(
                [
                    mo.hstack(
                        [
                            selected_plant_year,
                            selected_status,
                        ],
                        justify="start",
                    ),
                    mo.Html(
                        f'<div style="max-width: 1000px">{mo.ui.table(status_df).text if not status_df.empty else ""}</div>'
                    ),
                    mo.md(f"via {table_preview_href('out_eia__yearly_generators')}"),
                ]
            ),
        ]
    )
    owned_gen
    return


@app.cell
def _(alt, end_year, start_year, util_gen_fuel):
    fuel_year_df = util_gen_fuel[
        util_gen_fuel["report_date"].dt.year.isin(
            range(start_year.value, end_year.value + 1)
        )
    ]

    fuel_long = (
        fuel_year_df.groupby(["report_date", "fuel_type_code_pudl"])[
            "net_generation_mwh"
        ]
        .sum()
        .reset_index()
    )

    fuel_chart = (
        alt.Chart(fuel_long)
        .mark_area()
        .encode(
            x=alt.X(
                "report_date:T",
                axis=alt.Axis(format="%b", tickCount="month"),
                title="Month",
            ),
            y=alt.Y(
                "net_generation_mwh:Q",
                stack="zero",
                title="Net Generation (MWh)",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "fuel_type_code_pudl:N",
                scale=alt.Scale(scheme="tableau10"),
                legend=alt.Legend(title="Fuel Type"),
            ),
            tooltip=[
                alt.Tooltip("report_date:T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip("fuel_type_code_pudl:N", title="Fuel Type"),
                alt.Tooltip(
                    "net_generation_mwh:Q", title="Net Generation (MWh)", format=",.0f"
                ),
            ],
        )
        .properties(
            width=700,
            height=400,
        )
    )
    return (fuel_chart,)


@app.cell
def _(go, json, pd, px, urlopen, util_counties_year):
    # Generate map for service territory
    with urlopen(
        "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    ) as _r:
        _geojson = json.load(_r)

    with urlopen(
        "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
    ) as _r:
        _states_geojson = json.load(_r)

    _fips_col = "county_fips"
    _fips_set = set(util_counties_year["county_id_fips"].str.zfill(5))
    _all_fips = [f["id"] for f in _geojson["features"]]

    _plot_df = pd.DataFrame(
        {
            "fips": _all_fips,
            "in_df": [1 if f in _fips_set else 0 for f in _all_fips],
        }
    )

    st_fig = px.choropleth(
        _plot_df,
        geojson=_geojson,
        locations="fips",
        color="in_df",
        scope="usa",
        color_continuous_scale=[(0, "#e8eaf6"), (1, "#1a237e")],
        range_color=[0, 1],
        hover_data={"fips": True, "in_df": False},
    )

    # Add state outlines as a Scattergeo trace
    for _feature in _states_geojson["features"]:
        _coords = _feature["geometry"]["coordinates"]
        _polys = (
            _coords if _feature["geometry"]["type"] == "MultiPolygon" else [_coords]
        )
        for _poly in _polys:
            _lons, _lats = zip(*_poly[0])
            st_fig.add_trace(
                go.Scattergeo(
                    lon=list(_lons) + [None],
                    lat=list(_lats) + [None],
                    mode="lines",
                    line=dict(color="black", width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    st_fig.update_traces(marker_line_color="black", marker_line_width=0.3)
    st_fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_showscale=False,
        geo=dict(
            scope="usa",
            showlakes=False,
            showsubunits=True,  # ← draws state boundaries
            subunitcolor="white",
            subunitwidth=1.5,
        ),
    )
    None
    return (st_fig,)


@app.cell
def _(od_df, selected_util):
    util_od_df = od_df[od_df["utility_id_eia"] == selected_util.value]
    return (util_od_df,)


@app.cell
def _(alt, end_year, start_year, util_od_df):
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
            range(start_year.value, end_year.value + 1)
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
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(orient="right", columns=1, labelLimit=300, offset=10),
        ),
    )
    pos_chart = (
        base.mark_bar(width={"band": 0.8})
        .encode(
            y=alt.Y("sum(mwh):Q", stack="zero", title="MWh"),
        )
        .properties(data=od_pos)
    )
    neg_chart = (
        base.mark_bar(width={"band": 0.8})
        .encode(
            y=alt.Y("sum(mwh):Q", stack="zero"),
        )
        .properties(data=od_neg)
    )

    source_chart = alt.layer(pos_chart, neg_chart)
    return (source_chart,)


@app.cell
def _(end_year, fuel_chart, mo, source_chart, start_year):
    electricity_source = mo.vstack(
        [
            mo.md("## Electricity Source"),
            mo.hstack([start_year, end_year], justify="start"),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md("### Owned Generation by Fuel Type"),
                            mo.ui.altair_chart(
                                fuel_chart.properties(width=350, height=250)
                            ),
                            mo.md(
                                f"via {table_preview_href('out_eia923__generation_fuel_combined')}"
                            ),
                        ]
                    ),
                    mo.vstack(
                        [
                            mo.md("### Owned vs. Purchased Generation"),
                            mo.ui.altair_chart(
                                source_chart.properties(width=350, height=250)
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
def _(end_year, gen_fuel_df, mfrc_df, selected_util, start_year):
    util_mfrc_df = mfrc_df[
        (mfrc_df["utility_id_eia"] == selected_util.value)
        & (
            mfrc_df["report_date"].dt.year.isin(
                range(start_year.value, end_year.value + 1)
            )
        )
    ]

    util_year_gen_fuel_df = gen_fuel_df[
        (gen_fuel_df["utility_id_eia"] == selected_util.value)
        & (
            gen_fuel_df["report_date"].dt.year.isin(
                range(start_year.value, end_year.value + 1)
            )
        )
    ]

    fuel_plus_gen_df = util_year_gen_fuel_df.groupby(
        ["report_date", "fuel_type_code_pudl"]
    )[["net_generation_mwh", "fuel_consumed_mmbtu"]].sum()
    return fuel_plus_gen_df, util_mfrc_df


@app.cell
def _(util_mfrc_df):
    util_mfrc_df.sort_values("report_date")
    util_mfrc_df["fuel_consumed_units"] = (
        util_mfrc_df.fuel_consumed_mmbtu / util_mfrc_df.fuel_mmbtu_per_unit
    )
    return


@app.cell
def _(util_mfrc_df):
    fuel_cost_df = util_mfrc_df.groupby(["report_date", "fuel_type_code_pudl"])[
        [
            "fuel_received_units",
            "fuel_mmbtu_per_unit",
            "fuel_cost_per_mmbtu",
            "fuel_consumed_mmbtu",
        ]
    ].sum()

    fuel_cost_df["fuel_received_mmbtu"] = (
        fuel_cost_df.fuel_received_units * fuel_cost_df.fuel_mmbtu_per_unit
    )
    fuel_cost_df["fuel_consumed_cost"] = (
        fuel_cost_df.fuel_cost_per_mmbtu * fuel_cost_df.fuel_consumed_mmbtu
    )
    fuel_cost_df["fuel_received_cost"] = (
        fuel_cost_df.fuel_cost_per_mmbtu * fuel_cost_df.fuel_received_mmbtu
    )
    return (fuel_cost_df,)


@app.cell
def _(fuel_cost_df, fuel_plus_gen_df, pd):
    # For some reason, fuel_consumed_mmbtu is really off when you aggregate up...
    fuel_cost_net_gen = pd.merge(
        fuel_plus_gen_df,
        fuel_cost_df,
        on=["report_date", "fuel_type_code_pudl"],
        suffixes=["_gen_df", "_cost_df"],
    ).reset_index()

    fuel_cost_net_gen = fuel_cost_net_gen[fuel_cost_net_gen["fuel_received_units"] > 0]
    fuel_cost_net_gen["fuel_consumed_cost_per_net_gen"] = (
        fuel_cost_net_gen.fuel_consumed_cost / fuel_cost_net_gen.net_generation_mwh
    )
    return (fuel_cost_net_gen,)


@app.cell
def _(alt, fuel_cost_net_gen):
    fuel_cost_mmbtu_chart = (
        alt.Chart(fuel_cost_net_gen)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("report_date:T", title="Report Date"),
            y=alt.Y("fuel_cost_per_mmbtu:Q", title="Fuel Cost ($/MMBtu)"),
            color=alt.Color("fuel_type_code_pudl:N", title="Fuel Type"),
            tooltip=[
                alt.Tooltip("report_date:T", title="Date"),
                alt.Tooltip("fuel_type_code_pudl:N", title="Fuel Type"),
                alt.Tooltip("fuel_cost_per_mmbtu:Q", title="$/MMBtu", format="$.3f"),
            ],
        )
        .properties(
            title="Fuel Cost per MMBtu Over Time",
        )
    )
    return (fuel_cost_mmbtu_chart,)


@app.cell
def _(alt, fuel_cost_net_gen):
    fuel_consumed_mmbtu_chart = (
        alt.Chart(fuel_cost_net_gen)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("report_date:T", title="Report Date"),
            y=alt.Y("fuel_consumed_mmbtu_gen_df:Q", title="Fuel Consumed (MMBtu)"),
            color=alt.Color("fuel_type_code_pudl:N", title="Fuel Type"),
            tooltip=[
                alt.Tooltip("report_date:T", title="Date"),
                alt.Tooltip("fuel_type_code_pudl:N", title="Fuel Type"),
                alt.Tooltip("sum(fuel_consumed_mmbtu):Q", title="MMBtu", format=",.0f"),
            ],
        )
        .properties(
            title="Fuel Consumed (MMBtu) Over Time",
        )
    )
    return (fuel_consumed_mmbtu_chart,)


@app.cell
def _(alt, fuel_cost_net_gen):
    fuel_cost_mer_mwh_chart = (
        alt.Chart(fuel_cost_net_gen)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("report_date:T", title="Report Date"),
            y=alt.Y(
                "fuel_consumed_cost_per_net_gen:Q",
                title="Fuel Cost ($) / Net Generation (MWh)",
            ),
            color=alt.Color("fuel_type_code_pudl:N", title="Fuel Type"),
            tooltip=[
                alt.Tooltip("report_date:T", title="Date"),
                alt.Tooltip("fuel_type_code_pudl:N", title="Fuel Type"),
                alt.Tooltip(
                    "fuel_consumed_cost_per_net_gen:Q",
                    title="Total Cost ($)",
                    format=",.0f",
                ),
            ],
        )
        .properties(
            title="Fuel Cost per MWh Over Time",
        )
    )
    return


@app.cell
def _(alt, fuel_consumed_mmbtu_chart, fuel_cost_mmbtu_chart):
    combined_fuel_chart = alt.hconcat(
        fuel_cost_mmbtu_chart.encode(
            color=alt.Color(
                "fuel_type_code_pudl:N",
                title="Fuel Type",
                legend=alt.Legend(orient="right", legendX=0, legendY=-30),
            ),
        ),
        fuel_consumed_mmbtu_chart.encode(
            color=alt.Color("fuel_type_code_pudl:N", legend=None)
        ),
        # fuel_cost_mer_mwh_chart.encode(color=alt.Color("fuel_type_code_pudl:N", legend=None)),
    ).resolve_scale(color="shared")
    return (combined_fuel_chart,)


@app.cell
def _(combined_fuel_chart, mo):
    fuel_cost = mo.vstack(
        [
            mo.md("### Fuel Stats"),
            mo.ui.altair_chart(combined_fuel_chart),
            mo.md(
                f"via {table_preview_href('out_eia923__monthly_fuel_receipts_costs')} and {table_preview_href('out_eia923__generation_fuel_combined')}"
            ),
        ]
    )

    fuel_cost
    return


@app.cell
def _(end_year, s_df, selected_util, start_year):
    # PIVOT TABLE FOR SALES and REV CHART

    s_df_util = s_df[
        (s_df["utility_id_eia"] == selected_util.value)
        & (
            s_df["report_date"].dt.year.isin(
                range(start_year.value, end_year.value + 1)
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
    customer_classes = [c for c in pivot.columns if c != "report_date"]

    sales_long = make_report_date_report_year(
        pivot.set_index("report_date")
        .stack(level="customer_class")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    return (sales_long,)


@app.cell
def _(alt, sales_long):
    # SALES MWH CHART

    sales_mwh_chart = (
        alt.Chart(sales_long)
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y(
                "sales_mwh:Q",
                stack="zero",
                title="Sales (MWh)",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "customer_class:N",
                scale=alt.Scale(scheme="tableau10"),
                legend=alt.Legend(title="Customer Class", orient="right"),
            ),
            order=alt.Order("customer_class:N"),
            tooltip=[
                alt.Tooltip("report_year:T", title="Year", format="%Y"),
                alt.Tooltip("customer_class:N", title="Customer Class"),
                alt.Tooltip("sales_mwh:Q", title="Sales (MWh)", format=",.0f"),
            ],
        )
        .properties(title="Retail Sales (MWh) by Customer Class", width=300)
    )
    return (sales_mwh_chart,)


@app.cell
def _(alt, sales_long):
    # REVENUE CHART

    sales_revenue_chart = (
        alt.Chart(sales_long)
        .mark_bar()
        .encode(
            x=alt.X("report_year:O", title="Year"),
            y=alt.Y(
                "sales_revenue:Q",
                stack="zero",
                title="Revenue ($)",
                axis=alt.Axis(format=",.0f"),
            ),
            color=alt.Color(
                "customer_class:N",
                scale=alt.Scale(scheme="tableau10"),
                legend=alt.Legend(title="Customer Class", orient="right"),
            ),
            order=alt.Order("customer_class:N"),
            tooltip=[
                alt.Tooltip("report_year:T", title="Year", format="%Y"),
                alt.Tooltip("customer_class:N", title="Customer Class"),
                alt.Tooltip("sales_revenue:Q", title="Revenue ($)", format=",.0f"),
            ],
        )
        .properties(title="Retail Revenue ($) by Customer Class", width=300)
    )
    return (sales_revenue_chart,)


@app.cell
def _(alt, sales_mwh_chart, sales_revenue_chart):
    combined_sales_chart = alt.hconcat(
        sales_mwh_chart.encode(
            color=alt.Color(
                "customer_class:N",
                title="Customer Class",
                legend=alt.Legend(orient="right", legendX=0, legendY=-30),
            ),
        ),
        sales_revenue_chart.encode(color=alt.Color("customer_class:N", legend=None)),
    ).resolve_scale(color="shared")
    return (combined_sales_chart,)


@app.cell
def _(alt, get_util_years, odr_df):
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
                scale=alt.Scale(scheme="tableau10"),
                legend=alt.Legend(title="Revenue Class", orient="right"),
            ),
            order=alt.Order("revenue_class:N"),
            tooltip=[
                alt.Tooltip("report_year:T", title="Year", format="%Y"),
                alt.Tooltip("revenue_class:N", title="Revenue Class"),
                alt.Tooltip("sales_revenue:Q", title="Revenue ($)", format=",.0f"),
            ],
        )
        .properties(
            title="Total Revenue ($) by Type",
            width=300,
        )
    )
    return (revenue_class_chart,)


@app.function
def make_report_date_report_year(df):
    df["report_year"] = df["report_date"].dt.year
    return df


@app.cell
def _(get_util_years, r_df):
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
def _(alt, saidi_df):
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
            width=500,
        )
    )
    return (saidi,)


@app.cell
def _(alt, caidi_df):
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
            width=500,
        )
    )
    return (caidi,)


@app.cell
def _(alt, saifi_df):
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
            width=500,
        )
    )
    return (saifi,)


@app.cell
def _(caidi, combined_sales_chart, mo, revenue_class_chart, saidi, saifi):
    customer_facing = mo.vstack(
        [
            mo.md("## Customer-Facing"),
            mo.md("### Sales"),
            mo.Html(f"""
        <div style="overflow-x: auto; width: 100%; display: block;">
            <div style="min-width: max-content;">
                {mo.hstack([combined_sales_chart, revenue_class_chart]).text}
            </div>
        </div>
        """),
            mo.md(f"via {table_preview_href('core_eia861__yearly_sales')}"),
            mo.Html("<div style='margin-top: 2rem;'></div>"),
            mo.md("### Reliability"),
            mo.Html(f"""
        <div style="overflow-x: auto; width: 100%; display: block;">
            <div style="min-width: max-content;">
                {mo.hstack([saidi, saifi, caidi]).text}
            </div>
        </div>
        """),
            mo.md(f"via {table_preview_href('core_eia861__yearly_reliability')}"),
        ]
    )

    customer_facing
    return


@app.cell
def _():
    ## Utility Programs drop down menu
    return


@app.cell
def _(alt, util_od_df):
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
                    range=["#e05c2a", "#4a90d9"],
                ),
                legend=alt.Legend(orient="right"),
            ),
            tooltip=["report_date:T", "season:N", "mw:Q"],
        )
        .properties(
            title="Summer vs. Winter Peak Demand",
            width=700,
            height=400,
        )
    )
    return (summer_v_winter_demand_chart,)


@app.cell
def _(mo, summer_v_winter_demand_chart):
    demand = mo.vstack([mo.md("## Demand"), summer_v_winter_demand_chart])

    demand
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
