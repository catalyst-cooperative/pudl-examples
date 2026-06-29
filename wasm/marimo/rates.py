import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Rates Explorer
    Explore utility rates with data from <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html" target="_blank">FERC Form 1</a> or <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia861.html" target="_blank">EIA-861</a>. The publically available data can help us understand how rates have changed over time, the primary drivers of change and who bears the impact. The data available provides an incompelete picutre - rates are quite complex and the data is imperfect and incomplete. Nonetheless, we encourage you to explore and see what meaning you can make and utility rates. This dashbooard is attempting to daylight two important tables that can help make meaning about electricty rates:
    * <a href="https://data.catalyst.coop/preview/pudl/out_ferc1__yearly_rate_base" target="_blank">out_ferc1__yearly_rate_base</a>: Annual time series of granular accounting data consisting of what utilities can typically include in their rate bases. This table tells us about the costs that utilities incur.
    * <a href="https://data.catalyst.coop/preview/pudl/core_eia861__yearly_sales" target="_blank">core_eia861__yearly_sales</a>: Annual time series of electricity sales to ultimate customers by utility, balancing authority, state, and customer class. The EIA-861 sales data tells us about revenue collected from consumers, presumable to cover those costs from the FERC Form 1 rate base table.

    ## Brief overview of what goes into an electric utility bill?
    There is a fair amount of complexity in rate making and this dashboard only gives us a snapshot.  For more background materials, see the Additional Resources at the bottom of the page.

    * What are the costs that go into rate base?
      * __"Rate base"__ includes expenses, investmetns, a rate of return on captial investment, amoung other things.
        * __Fixed vs. Variable__: Some costs are variable based on the amount of electricity consumers use (ex: using natural gas when generating electricity at a natural gas generation facility) and some costs are *relatively* fixed (ex: investments in maintaining the physical structure at a natural gas plant or the maintenance costs for the distribution system in an area that isn't experiencing lots of growth). Many things in a "fixed" side of rates certainly change over time and require investments when use exa the existing infrastructure.
        * __Capital Bias__ is a well understood result of the predominate rate design in the U.S., which incentivizes utilities to invest more capital into their systems because they get a fixed rate of return for allowable capital investments.
      * __Fuel costs & Other Riders__ (not included in this dashboard): "Riders" or "pass-throughs" are a common method for charging customers for specific programs or costs as a line-item on your bill. These costs are not included in rate base, but do effect customer prices. Fuel costs are the most notable because they can be extremely variable and can be significant. Fuel costs and other riders are not explored in this dashbaord.
    * How do those costs get allocated to customers?
      * __Cost Allocation__: Allocating utility costs to customers happens in a rate design process. This typically happens in a rate case and involves cost of service studies. The high level goal is to allocate costs to customers incurring those costs with minimal cross-subsidy between custsomers.
      * __Demand vs volumetric charges__: Residential customers almost always have bills which is largely volumetric pricing - meaning you are charged based on how much you consume. Some rate structures are demand-based, meaning you are charged by the maximum amount of energy you have consumed.
      * The EIA-861 data in this dashboard tells us about what costs are collected from different kinds of customers, but it does not tell us about how rates are structured or calculated. For more information about rate schedules you can explore <a href='https://data.catalyst.coop/preview/pudl/out_ferc1__yearly_sales_by_rate_schedules_sched304' target='_blank'>out_ferc1__yearly_sales_by_rate_schedules_sched304</a>, but beware that table is not particularly well structured.

    ## Notable things not covered here
    * __Inflation__. All costs in this dashboard are nominal USD.
    * __Fuel Costs__. As noted above, this data does not include pass through costs like fuel which can be substaintial.
    * __FERC Form 1 Respondents Only__. Because we only have rate base data for those utilities which report to FERC Form 1 (see <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html#who-submits-this-data" target="_blank">reporting requirements</a>), this entire dashboard is restricted to only those utilities.
    """)
    return


@app.cell
def _():
    import marimo as mo

    with mo.status.progress_bar(
        total=1, title="Loading subroutines", remove_on_exit=True
    ) as do_imports:
        from textwrap import wrap

        import altair as alt
        import fastparquet as fp
        import pandas as pd
        import pyarrow as pa

        do_imports.update(subtitle="Done!")
    return alt, mo, pd, wrap


@app.cell
def _(pd):
    def path(name):
        # return f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"
        return f"/Users/christinagosnell/code/pudl_work/output/parquet/{name}.parquet"

    def pudl(name, columns=None):
        return pd.read_parquet(
            path(name),
            engine="fastparquet",
            **({"columns": columns} if columns else {}),
        )

    def table_preview_href(name):
        return f"""<a href="https://data.catalyst.coop/preview/pudl/{name}" target="_blank">{name}</a>"""

    return (pudl,)


@app.cell
def _(mo, pd, pudl):
    with mo.status.progress_bar(
        total=5,
        title="Loading data",
        subtitle="out_ferc1__yearly_rate_base",
        remove_on_exit=True,
    ) as do_fetch_data:
        # glue
        core_pudl__entity_utilities_pudl = pudl("core_pudl__entity_utilities_pudl")
        do_fetch_data.update(subtitle="core_pudl__entity_utilities_pudl")
        core_pudl__assn_ferc1_pudl_utilities = pudl(
            "core_pudl__assn_ferc1_pudl_utilities"
        )
        do_fetch_data.update(subtitle="core_pudl__assn_ferc1_pudl_utilities")
        core_pudl__assn_eia_pudl_utilities = pudl("core_pudl__assn_eia_pudl_utilities")
        do_fetch_data.update(subtitle="core_pudl__assn_eia_pudl_utilities")
        # data
        out_ferc1__yearly_rate_base = pudl("out_ferc1__yearly_rate_base")
        do_fetch_data.update(subtitle="out_ferc1__yearly_rate_base")
        core_eia861__yearly_sales = pudl("core_eia861__yearly_sales")
        do_fetch_data.update(subtitle="core_eia861__yearly_sales")

        out_eia861__yearly_utility_service_territory = pudl(
            "out_eia861__yearly_utility_service_territory"
        )
        do_fetch_data.update(subtitle="out_eia861__yearly_utility_service_territory")
        # done
        do_fetch_data.update(subtitle="Done!")
        # glue

    # glue
    # make a utility/state map
    eia861_utility_states = out_eia861__yearly_utility_service_territory.loc[
        :, ["report_date", "utility_id_eia", "state"]
    ].drop_duplicates()

    eia861_utility_states.state = eia861_utility_states.state.astype(pd.StringDtype())
    eia861_utility_states.loc[:, "state_n"] = eia861_utility_states.groupby(
        ["utility_id_eia", "report_date"]
    )[["state"]].transform("cumcount")

    eia861_utility_states = eia861_utility_states.set_index(
        ["utility_id_eia", "report_date", "state_n"]
    ).unstack(level="state_n")
    state_cols = [f"state_{c[1]}" for c in eia861_utility_states.columns]
    eia861_utility_states.columns = state_cols
    eia861_utility_states = eia861_utility_states.reset_index()

    out_pudl__entity_utilities_pudl = (
        core_pudl__entity_utilities_pudl.merge(
            core_pudl__assn_ferc1_pudl_utilities,
            on=["utility_id_pudl"],
            how="outer",
        )
        .merge(
            core_pudl__assn_eia_pudl_utilities,
            on=["utility_id_pudl"],
            how="outer",
        )
        .merge(eia861_utility_states, on=["utility_id_eia"], how="outer")
        .assign(report_year=lambda x: x.report_date.dt.year)
    )

    out_ferc1__yearly_rate_base = out_ferc1__yearly_rate_base.merge(
        out_pudl__entity_utilities_pudl.drop_duplicates(
            subset=["utility_id_pudl", "utility_id_ferc1"]
        )[
            ["utility_id_pudl", "utility_id_ferc1", "utility_name_pudl", "report_year"]
            + list(out_pudl__entity_utilities_pudl.filter(like="state_").columns)
        ],
        on=["utility_id_pudl", "utility_id_ferc1", "report_year"],
        how="left",
        validate="m:1",
    )

    core_eia861__yearly_sales = core_eia861__yearly_sales.merge(
        out_pudl__entity_utilities_pudl.drop_duplicates(
            subset=["utility_id_eia", "report_date"]
        )[
            ["utility_id_pudl", "utility_id_eia", "utility_name_pudl", "report_date"]
            + list(out_pudl__entity_utilities_pudl.filter(like="state_").columns)
        ],
        on=["utility_id_eia", "report_date"],
        how="left",
        validate="m:1",
    )
    return (
        core_eia861__yearly_sales,
        out_eia861__yearly_utility_service_territory,
        out_ferc1__yearly_rate_base,
        state_cols,
    )


@app.cell
def _(core_eia861__yearly_sales, out_ferc1__yearly_rate_base, pd, state_cols):
    out_ferc1__yearly_rate_base.utility_id_ferc1_xbrl = (
        out_ferc1__yearly_rate_base.groupby(["report_year", "utility_id_ferc1"])[
            ["utility_id_ferc1_xbrl"]
        ].transform("bfill")
    )
    out_ferc1__yearly_rate_base.utility_id_ferc1_dbf = (
        out_ferc1__yearly_rate_base.groupby(["report_year", "utility_id_ferc1"])[
            ["utility_id_ferc1_dbf"]
        ].transform("ffill")
    )
    out_ferc1__yearly_rate_base.plant_function = (
        out_ferc1__yearly_rate_base.plant_function.astype(pd.StringDtype()).fillna(
            "unclassified"
        )
    )

    # back and forward fill the state columns
    out_ferc1__yearly_rate_base.loc[:, state_cols] = (
        out_ferc1__yearly_rate_base.groupby(["utility_id_pudl"])[state_cols]
        .bfill()
        .ffill()
    )
    out_ferc1__yearly_rate_base.loc[:, "utility_name_pudl"] = (
        out_ferc1__yearly_rate_base.groupby(["utility_id_pudl"])[["utility_name_pudl"]]
        .bfill()
        .ffill()
    )

    core_eia861__yearly_sales.loc[:, "sales_revenue_by_mwh"] = (
        core_eia861__yearly_sales.sales_revenue / core_eia861__yearly_sales.sales_mwh
    )
    core_eia861__yearly_sales.loc[:, "revenue_per_customer"] = (
        core_eia861__yearly_sales.sales_revenue / core_eia861__yearly_sales.customers
    )
    core_eia861__yearly_sales.loc[:, "revenue_per_month_customer"] = (
        core_eia861__yearly_sales.revenue_per_customer / 12
    )
    core_eia861__yearly_sales.loc[:, "report_year"] = (
        core_eia861__yearly_sales.report_date.dt.year
    )
    return


@app.cell
def _(out_ferc1__yearly_rate_base, pd):
    plant_to_type_map = {
        "unclassified": "other",
        "nuclear_production": "energy_production",
        "energy_storage": "energy_production",
        "transmission": "transmission_and_distribution",
        "hydraulic_production": "energy_production",
        "other_production": "energy_production",
        "distribution": "transmission_and_distribution",
        "other_renewable_production": "energy_production",
        "solar_production": "energy_production",
        "experimental": "other",
        "wind_production": "energy_production",
        "regional_transmission_and_market_operation": "other",
        "intangible": "other",
        "general": "other",
        "steam_production": "energy_production",
        "purchased_sold": "energy_production",
    }
    out_ferc1__yearly_rate_base.loc[:, "plant_function_type"] = (
        out_ferc1__yearly_rate_base.plant_function.map(plant_to_type_map).astype(
            pd.StringDtype()
        )
    )
    return


@app.cell
def _(
    mo,
    out_eia861__yearly_utility_service_territory,
    out_ferc1__yearly_rate_base,
    pd,
):
    class OptionsFerc1:
        """Compute valid rate base options based on partial selections.

        Caches the results so we're not constantly repeating dataframe queries.

        Used by marimo ui widgets in constructing dropdown options; used by
        selection initialization in validating/filling gaps in url params."""

        @classmethod
        @mo.cache
        def available_states(cls) -> pd.Series:
            return pd.concat(
                [
                    pd.Series("ALL"),
                    out_eia861__yearly_utility_service_territory.state.drop_duplicates().sort_values(),
                ]
            )

        @classmethod
        @mo.cache
        def available_utilities(cls, states: set[str]) -> pd.Series:
            df = out_ferc1__yearly_rate_base
            if states != {"ALL"}:
                df = out_ferc1__yearly_rate_base.loc[
                    df.filter(like="state_").isin(states).any(axis="columns")
                ]
            utils = df.loc[:, "utility_name_pudl"].drop_duplicates().sort_values()
            return pd.concat([pd.Series(["ALL"]), utils])

        @classmethod
        @mo.cache
        def available_years(cls, utilities_1) -> pd.Series:
            # TODO: make available years based on the union of years for utils 1 and 2
            if utilities_1 == "ALL" or utilities_1 != "":
                df = out_ferc1__yearly_rate_base
            else:
                df = out_ferc1__yearly_rate_base.loc[
                    (
                        out_ferc1__yearly_rate_base.utility_name_pudl.isin(
                            list(utilities_1)
                        )
                    )
                ]
            return (
                df.report_year.drop_duplicates()
                .astype(pd.Int64Dtype())
                .sort_values(ascending=False)
            )

    return (OptionsFerc1,)


@app.cell
def _(OptionsFerc1, mo):
    # this has to be in a cell other than the cell where `selection` is defined,
    # otherwise updates won't propagate correctly.
    query_params = mo.query_params()

    def initialize_default_params():
        if "states_1" not in query_params:
            query_params["states_1"] = "ALL"
        if "utilities_1" not in query_params:
            query_params["utilities_1"] = "ALL"
        util_set = set(query_params["utilities_1"].split("|"))
        available_years = OptionsFerc1.available_years(util_set)
        if "start_year" not in query_params or (
            int(query_params["start_year"]) not in set(available_years)
        ):
            query_params["start_year"] = str(available_years.min())
        if "end_year" not in query_params or (
            int(query_params["end_year"]) not in set(available_years)
        ):
            query_params["end_year"] = str(available_years.max())
        if "states_2" not in query_params:
            query_params["states_2"] = ""
        if "utilities_2" not in query_params:
            query_params["utilities_2"] = ""

    initialize_default_params()
    return initialize_default_params, query_params


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
def _(OptionsFerc1, mo, query_params, reset_params):
    from functools import cached_property

    from pydantic import BaseModel, Field, computed_field, field_validator

    class Selection(BaseModel):
        """Store/represent the user's current utility selection.

        The direct values (utilities, years, etc) are pulled from
        and persisted to the corresponding URL parameters.

        The selector views (utilities_selector, years_selector, etc) are
        computed based on the values and cached for display in the dashboard."""

        start_year: str = "1994"
        end_year: str = "2024"

        states_1: set[str] = Field({"ALL"})
        utilities_1: set[str] = Field({"ALL"})

        states_2: set[str] = Field({None})
        utilities_2: set[str] = Field({None})

        @computed_field
        @cached_property
        def start_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={
                    str(i) for i in OptionsFerc1.available_years(self.utilities_1)
                },
                label="Utility attributes starting from:",
                value=str(self.start_year),
                on_change=lambda value: reset_params(start_year=str(value)),
            )

        @computed_field
        @cached_property
        def end_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={
                    str(i) for i in OptionsFerc1.available_years(self.utilities_1)
                },
                label="Utility attributes ending:",
                value=str(self.end_year),
                on_change=lambda value: reset_params(end_year=str(value)),
            )

        @computed_field
        @cached_property
        def states_1_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_states()),
                value=self.states_1,
                label="First Set States or select ALL: ",
                max_selections=10,
                on_change=lambda value: reset_params(
                    states_1="|".join(value), utilities_1=""
                ),
            )

        @computed_field
        @cached_property
        def utilities_1_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_utilities(self.states_1)),
                value=self.utilities_1,
                label="First Set Utilities or select ALL: ",
                max_selections=10,
                on_change=lambda value: reset_params(utilities_1="|".join(value)),
            )

        @computed_field
        @cached_property
        def states_2_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_states()),
                value=self.states_2,
                label="First Set States or select ALL: ",
                max_selections=10,
                # when this one changes, reset the states_1 param and clear the utils param
                on_change=lambda value: reset_params(
                    states_2="|".join(value), utilities_2=""
                ),
            )

        @computed_field
        @cached_property
        def utilities_2_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_utilities(self.states_2)),
                value=self.utilities_2,
                label="Second Set Utilities or Select All: ",
                max_selections=10,
                on_change=lambda value: reset_params(utilities_2="|".join(value)),
            )

        @computed_field
        @cached_property
        def mark_type_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={"Stacked Bar": "mark_bar", "Line": "mark_line"},
                label="Chart Display Type:",
                value="Stacked Bar",
            )

        @field_validator(
            "utilities_1", "utilities_2", "states_1", "states_2", mode="before"
        )
        @classmethod
        def deserialize(cls, value: str) -> set[str]:
            if value == "":
                out = set()
            else:
                out = set(value.split("|"))
            return out

    selection = Selection(**query_params.to_dict())
    return (selection,)


@app.cell
def _(mo, selection):
    mo.sidebar(
        [
            mo.md("##Make Selections:"),
            mo.md("###Choose Years:"),
            mo.hstack(
                [
                    mo.md(f"""<div data-tooltip="By default we extend the timeseries as far back as we have data available.
                To prune to a more recent year, select here.">{mo.icon("lucide:info")}</div>"""),
                    selection.start_year_selector,
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.hstack(
                [
                    mo.md(f"""<div data-tooltip="By default we include the most recent data available.
                To prune to a less recent year, select here.">{mo.icon("lucide:info")}</div>"""),
                    selection.end_year_selector,
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.md("""###Choose a Utility or Utilities to Compare:"""),
            mo.hstack(
                [
                    mo.md(
                        f"""<div data-tooltip="Choose a state or a set of states to explore. This will restrict the utiilty options. By default we show you all states. If you want to chose particular ones, select here.">{mo.icon("lucide:info")}</div>"""
                    ),
                    selection.states_1_selector,
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.hstack(
                [
                    mo.md(
                        f"""<div data-tooltip="Choose a first set of utilities to explore. By default we show you all utilities. If you want to chose particular ones, select here.">{mo.icon("lucide:info")}</div>"""
                    ),
                    selection.utilities_1_selector,
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.md("""###To Compare, choose Second Utility or Utilities:"""),
            mo.hstack(
                [
                    mo.md(
                        f"""<div data-tooltip="Choose a state or a set of states to explore. This will restrict the utiilty options. By default we show you all states. If you want to chose particular ones, select here.">{mo.icon("lucide:info")}</div>"""
                    ),
                    selection.states_2_selector,
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.hstack(
                [
                    mo.md(
                        f"""<div data-tooltip="Choose a second set of utilities to explore. By default we show you all utilities. If you want to chose particular ones, select here.">{mo.icon("lucide:info")}</div>"""
                    ),
                    selection.utilities_2_selector,
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.md("""###Choose between chart styles:"""),
            selection.mark_type_selector,
        ]
    )
    # TODO: add a warning if a user chooses utilities_2 but not utilities_1
    return


@app.cell
def _(core_eia861__yearly_sales, out_ferc1__yearly_rate_base, selection):
    graph_inputs = {"opt_1": {}, "opt_2": {}}

    for opt_n in graph_inputs.keys():
        utility_selection = selection.model_dump().get(
            f"utilities_{opt_n.removeprefix('opt_')}"
        )
        state_selection = selection.model_dump().get(
            f"states_{opt_n.removeprefix('opt_')}"
        )
        if utility_selection:
            # Set default mask and title
            utility_selection_title_part = "All Utilities"
            utils_subtitle = ""
            rate_mask = out_ferc1__yearly_rate_base.report_year.between(
                int(selection.start_year), int(selection.end_year)
            )

            # Only show utilities which also show up in FERC1
            sales_mask = core_eia861__yearly_sales.report_year.between(
                int(selection.start_year), int(selection.end_year)
            ) & (
                core_eia861__yearly_sales.utility_id_pudl.isin(
                    list(out_ferc1__yearly_rate_base.utility_id_pudl.unique())
                )
            )
            if state_selection != {"ALL"}:
                rate_mask = rate_mask & (
                    out_ferc1__yearly_rate_base.filter(like="state")
                    .isin(state_selection)
                    .any(axis=1)
                )
                sales_mask = sales_mask & (
                    core_eia861__yearly_sales.filter(like="state")
                    .isin(state_selection)
                    .any(axis=1)
                )
                utility_selection_title_part = f"{', '.join(state_selection)} Utilities"
            if utility_selection != {"ALL"}:
                rate_mask = rate_mask & (
                    out_ferc1__yearly_rate_base.utility_name_pudl.isin(
                        utility_selection
                    )
                )
                sales_mask = sales_mask & (
                    core_eia861__yearly_sales.utility_name_pudl.isin(utility_selection)
                )
                if (util_len := len(utility_selection)) > 1:
                    utility_selection_title_part = f"{util_len} Utilities"
                    utils_subtitle = " & ".join(utility_selection)
                else:
                    utility_selection_title_part = f"{list(utility_selection)[0]}"
            filtered_rate_base = out_ferc1__yearly_rate_base[rate_mask]
            filtered_sales = core_eia861__yearly_sales[sales_mask]
            graph_inputs[opt_n] = {
                "utility_selection_title_part": utility_selection_title_part,
                "utils_subtitle": utils_subtitle,
                "filtered_rate_base": filtered_rate_base,
                "filtered_sales": filtered_sales,
                "utility_selection": utility_selection,
            }
    return (graph_inputs,)


@app.cell
def _(alt, mo, pd, selection, wrap):
    # why colors..?? bc.... bc i can! bc CUTENESS
    cat_colors = [
        "palevioletred",
        "purple",
        "thistle",
        "mediumpurple",
        "lavender",
        "lightskyblue",
        "paleturquoise",
        "lightseagreen",
        "turquoise",
        "aquamarine",
        "lightgreen",
        "gold",
        "goldenrod",
        "darkorange",
        "tomato",
        "firebrick",
        "linen",
        "mediumorchid",
        "mediumpurple",
        "mediumseagreen",
        "mediumslateblue",
        "mediumspringgreen",
        "mediumturquoise",
        "mediumvioletred",
        "midnightblue",
        "mintcream",
        "mistyrose",
    ]

    def make_chart(
        df: pd.DataFrame,
        aggregate: str,
        utils_subtitle: str,
        color_stack: str,
        colors: list[str],
        col: str,
        title: str,
        utility_selection_title_part: str,
        y_axis_format: str,
        y_title: str,
        filter_on_color_stack: list[str] | None = None,
        xOffset: str | None = None,
    ):
        if filter_on_color_stack:
            df = df[df[color_stack].isin(filter_on_color_stack)]
        # groupby first bc its toooo big otherwise T_T
        gb = df.groupby(["report_year", color_stack], observed=True)[col]
        agged = getattr(gb, aggregate)().reset_index()
        chart_cls = alt.Chart(
            agged,
            title=alt.Title(
                wrap(
                    f"{aggregate.title()} of {title} for {utility_selection_title_part}"
                ),
                subtitle=wrap(utils_subtitle),
            ),
        )
        xOffset_if_bar_and_side_by_side = (
            {"xOffset": xOffset}
            if xOffset and selection.mark_type_selector.value == "mark_bar"
            else {}
        )
        return (
            getattr(chart_cls, selection.mark_type_selector.value)()
            .encode(
                alt.X("report_year", type="ordinal").title("Report date"),
                alt.Y(col).axis(format=y_axis_format).title(y_title),
                color=alt.Color(color_stack).scale(range=colors),
                **xOffset_if_bar_and_side_by_side,
            )
            .properties(width="container")
        )

    def make_comparison_charts(cols_to_chart, graph_inputs, df_name: str):
        for col_to_chart in cols_to_chart:
            stack_graphs = {}
            for option_n, graph_input in graph_inputs.items():
                if graph_input:
                    rate_base_chart = make_chart(
                        df=graph_input[df_name],
                        aggregate=col_to_chart["aggregate"],
                        utils_subtitle=graph_input["utils_subtitle"],
                        color_stack=col_to_chart["color_stack"],
                        col=col_to_chart["col"],
                        title=col_to_chart["title"],
                        utility_selection_title_part=graph_input[
                            "utility_selection_title_part"
                        ],
                        y_title=col_to_chart["y_title"],
                        y_axis_format=col_to_chart["y_axis_format"],
                        filter_on_color_stack=col_to_chart.get(
                            "filter_on_color_stack", None
                        ),
                        xOffset=col_to_chart.get("xOffset", None),
                        colors=col_to_chart.get("colors", cat_colors),
                    )
                    stack_graphs[option_n] = rate_base_chart
            mo.output.append(mo.md(col_to_chart.get("preamble", "")))
            if len(stack_graphs) == 1:
                mo.output.append(stack_graphs["opt_1"])
            else:
                mo.output.append(
                    alt.hconcat(stack_graphs["opt_1"], stack_graphs["opt_2"])
                )

    return (make_comparison_charts,)


@app.cell
def _(graph_inputs, make_comparison_charts, mo):
    mo.output.append(mo.md("""## Utility Rate Base"""))

    cols_to_chart_ferc1 = [
        {
            "preamble": (
                "What portion of a utilities overall expenses or capital has increased or decreased over time? Are the increases coming from the **generation of electricity** or the **transmission and distribution system**? Consider fixed vs. variable costs."
            ),
            "col": "ending_balance",
            "aggregate": "sum",
            "title": "Rate Base by Function Type",
            "y_title": "Nominal USD",
            "y_axis_format": "$",
            "color_stack": "plant_function_type",
        },
        {
            "preamble": (
                "Want to dig in further? This graph breaks down rate base by 'plant function', which is a FERC-defined label of what function an expense or capital cost plays in utility operations."
            ),
            "col": "ending_balance",
            "title": "Rate Base by Plant Function",
            "y_title": "Nominal USD",
            "y_axis_format": "$",
            "aggregate": "sum",
            "color_stack": "plant_function",
        },
        {
            "preamble": (
                "Details Abound! The smart folks at <a href='rmi.org' target='_blank'>RMI</a> labled rate base with even more detail. This is a more detailed break down of these rate base costs."
            ),
            "col": "ending_balance",
            "aggregate": "sum",
            "title": "Rate Base by Category",
            "y_title": "Nominal USD",
            "y_axis_format": "$",
            "color_stack": "rate_base_category",
        },
    ]

    make_comparison_charts(cols_to_chart_ferc1, graph_inputs, "filtered_rate_base")
    return


@app.cell
def _(graph_inputs, make_comparison_charts, mo):
    mo.output.append(
        mo.md("""## Utility Revenue from Customers
    Now let's look at how much utilities are collecting from customers using EIA 861 data.
    """)
    )
    customer_colors = ["palevioletred", "purple", "lightseagreen"]
    cols_to_chart_eia861 = [
        {
            "preamble": (
                "How has utilty sales changed over time? Is this different than the rate base changing over time?\n"
                "How much of the revenue that utilities collect come from each different "
                "types of customers?"
            ),
            "col": "sales_revenue",
            "title": "Sales Revenue by Customer Class",
            "y_title": "$",
            "aggregate": "sum",
            "colors": customer_colors,
            "color_stack": "customer_class",
            "y_axis_format": "$",
            "filter_on_color_stack": ["commercial", "industrial", "residential"],
        },
        {
            # I added a filter in here bc.. well I assume most people want to see residential
            # and with all customers the residential customers were drowned out
            "preamble": (
                "What about average monthly revenue per residential customers? This "
                "isn't exactly equivilant to monthly bills but it is a good proxy for "
                "an average monthly customer bill."
            ),
            "col": "revenue_per_month_customer",
            "title": "Monthly Residential Sales",
            "y_title": "Sales ($) per Customer per Month",
            "aggregate": "mean",
            "colors": [customer_colors[-1]],
            "color_stack": "customer_class",
            "y_axis_format": "$",
            "filter_on_color_stack": ["residential"],
            "xOffset": "customer_class",
        },
        {
            "preamble": (
                "How has electricity consumption changed over time within these different customer classes\n"
                "**Hint**: Generally speaking, electricity consumption over the last few decades has been incredibly flat."
            ),
            "col": "sales_mwh",
            "title": "MWh Sales by Customer Class",
            "y_title": "MWh",
            "aggregate": "sum",
            "colors": customer_colors,
            "color_stack": "customer_class",
            "y_axis_format": None,
            "filter_on_color_stack": ["commercial", "industrial", "residential"],
        },
        {
            "col": "sales_revenue_by_mwh",
            "title": "Revenue per MWh by Customer Class",
            "y_title": "$/MWh",
            "aggregate": "mean",
            "colors": customer_colors,
            "color_stack": "customer_class",
            "y_axis_format": "$",
            "filter_on_color_stack": ["commercial", "industrial", "residential"],
            "xOffset": "customer_class",
        },
    ]

    make_comparison_charts(cols_to_chart_eia861, graph_inputs, "filtered_sales")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Addition Resoures
    * <a href="https://affordability-toolkit.rmi.org/" target='_blank'>RMI's Electricity Affordability Toolkit</a>
    * <a href='https://utilitydisconnections.org/' target='_blank'>Utility Disconnection Dashboard</a>
    * <a href='https://www.raponline.org/wp-content/uploads/2023/09/appendix-a-smart-rate-design-2015-aug-31.pdf' target='_blank'>RAP's Smart Rate Design for a Smart Future</a>
    * <a href='https://www.raponline.org/wp-content/uploads/2023/10/rap-improving-utility-performance-incentives-in-the-united-states-2023-october.pdf' target='_blank'>RAP's Improving Utility Performance Incentives in the United States</a>
    """)
    return


if __name__ == "__main__":
    app.run()
