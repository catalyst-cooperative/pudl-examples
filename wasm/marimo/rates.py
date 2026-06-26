import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    # TODO:.... so much still T_T make this premable more ambly... add references. add a warning so everything pauses if you don't select any utilities_1.
    #
    mo.output.append(mo.md("# Rates Explorer"))
    mo.output.append(
        mo.md(
            'Explore utility rates with data from <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html" target="_blank">FERC Form 1</a> or <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia861.html" target="_blank">EIA-861</a>.'
        )
    )
    mo.output.append(
        mo.md(
            """
    ## What goes into setting your utility bill?
    Well, a lot! For most utility customers, you get chaged
    * Things that are included in "Rate Base"
    * A rate of return on capital investments
    * Riders or pass throughs. Mostl of the variable fuel costs ends up in <a href="https://affordability-toolkit.rmi.org/policies/fuel-cost-sharing" target='__blank'>fuel cost adjustors</a>

    ### Oookay what the heck is in Rate Base?
    * Capital Expenses: Things a utility invests in the system.
    *


    ### Questions this data can begin to answer
    * What portion of a utilities overall expenses or capital has increased or decreased over time? Are the increases coming from the generation of electricity or the transmission and distribution system?
    *
    """
        )
    )
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
def _(mo):
    mo.vstack(
        [
            mo.md("----"),
            mo.md(
                "Here is what we know about utility costs. Not all utilities report to both FERC and EIA 861."
            ),
        ]
    )
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

            # Set default mask
            sales_mask = core_eia861__yearly_sales.report_year.between(
                int(selection.start_year), int(selection.end_year)
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

    def make_rate_base_chart(
        filtered_rate_base: pd.DataFrame,
        utils_subtitle: str,
        color_stack: str,
        col: str,
        title: str,
        utility_selection_title_part: str,
        y_title: str,
    ):
        # groupby first bc its toooo big otherwise T_T
        rb_gb = (
            filtered_rate_base.groupby(["report_year", color_stack], observed=False)[
                col
            ]
            .sum(min_count=1)
            .reset_index()
        )
        rate_base_chart_cls = alt.Chart(
            rb_gb,
            title=alt.Title(
                wrap(
                    f"Annual Sum of Rate Base by {title} for {utility_selection_title_part}"
                ),
                subtitle=wrap(utils_subtitle),
            ),
        )
        return (
            getattr(rate_base_chart_cls, selection.mark_type_selector.value)()
            .encode(
                alt.X("report_year", type="ordinal").title("Report date"),
                alt.Y(col).axis(format="$").title(y_title),
                color=alt.Color(color_stack).scale(range=cat_colors),
            )
            .properties(
                width="container",
                # height=200
            )
        )

    def make_chart(
        df: pd.DataFrame,
        aggregate: str,
        utils_subtitle: str,
        color_stack: str,
        col: str,
        title: str,
        utility_selection_title_part: str,
        y_axis_format: str,
        y_title: str,
        filter_on_color_stack: str | None = None,
    ):
        if filter_on_color_stack:
            df = df[df[color_stack] == filter_on_color_stack]
        # groupby first bc its toooo big otherwise T_T
        gb = df.groupby(["report_year", color_stack], observed=False)[col]
        agged = getattr(gb, aggregate)().reset_index()
        chart_cls = alt.Chart(
            agged,
            title=alt.Title(
                wrap(
                    f"Annual {aggregate.title()} of {title} for {utility_selection_title_part}"
                ),
                subtitle=wrap(utils_subtitle),
            ),
        )
        return (
            getattr(chart_cls, selection.mark_type_selector.value)()
            .encode(
                alt.X("report_year", type="ordinal").title("Report date"),
                alt.Y(col).axis(format=y_axis_format).title(y_title),
                color=alt.Color(color_stack).scale(range=cat_colors),
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
def _(graph_inputs, make_comparison_charts):
    cols_to_chart_ferc1 = [
        {
            "preamble": ("Blah blah blah stuff about rate base"),
            "col": "ending_balance",
            "aggregate": "sum",
            "title": "Rate Base by Function Type",
            "y_title": "Nominal USD",
            "y_axis_format": "$",
            "color_stack": "plant_function_type",
        },
        {
            "preamble": (
                "Okay okay even more stuff about different bits of rate base."
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
                "Details Abound! The smart folks at <a href='rmi.org'  target='_blank'>RMI</a> labled rate base with even more detail."
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
def _(core_eia861__yearly_sales):
    core_eia861__yearly_sales
    return


@app.cell
def _(graph_inputs, make_comparison_charts):
    cols_to_chart_eia861 = [
        {
            "preamble": (
                "How much of the revenue that utilities collect come from each different "
                "types of customers?"
            ),
            "col": "sales_revenue",
            "title": "Sales Revenue by Customer Class",
            "y_title": "$",
            "aggregate": "sum",
            "color_stack": "customer_class",
            "y_axis_format": "$",
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
            "title": "Revenue per Residential Customer by per Month",
            "y_title": "Sales ($) per Customer per Month",
            "aggregate": "mean",
            "color_stack": "customer_class",
            "y_axis_format": "$",
            "filter_on_color_stack": "residential",
        },
        {
            "col": "sales_mwh",
            "title": "MWh Sales by Customer Class",
            "y_title": "MWh",
            "aggregate": "sum",
            "color_stack": "customer_class",
            "y_axis_format": None,
        },
        {
            "col": "sales_revenue_by_mwh",
            "title": "Revenue per MWh by Customer Class",
            "y_title": "$/MWh",
            "aggregate": "mean",
            "color_stack": "customer_class",
            "y_axis_format": "$",
        },
    ]

    make_comparison_charts(cols_to_chart_eia861, graph_inputs, "filtered_sales")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
