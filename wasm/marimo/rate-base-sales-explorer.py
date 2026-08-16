import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def header(mo):
    mo.md(r"""
    # ⚡💸Utility Rate Base & Sales Explorer 💸⚡

    This dashboard highlights two tables that can help us better understand utility rates:
    * 🧮 __<a href="https://data.catalyst.coop/preview/pudl/out_ferc1__yearly_rate_base" target="_blank">out_ferc1__yearly_rate_base</a>__: This table tells us about the investments that utilities make to serve electricity customers and typically include in their rate bases. This table was made with domain expertise and financial support from <a href="https://utilitytransitionhub.rmi.org/finances/" target="_blank">RMI</a>.
    * 🧾 __<a href="https://data.catalyst.coop/preview/pudl/core_eia861__yearly_sales" target="_blank">core_eia861__yearly_sales</a>__: This table tells us about revenue collected from each type of customer, presumably to cover those costs from the FERC Form 1 rate base table as well as other costs. This table gives us a good proxy for utility bills in aggregate, but doesn’t tell us about how rates are structured.

    These tables provide clues about how rates have changed over time, the primary drivers of that change and who bears the impact of that change. It’s important to note that, while informative, the data provide an incomplete and imperfect picture. The rate making process is complex and this dashboard only gives us a snapshot. Nonetheless, we think this information is useful and we encourage you to explore. For more background materials, see the Additional Resources at the bottom of the page.
    """)


@app.cell
def imports():
    import marimo as mo

    with mo.status.progress_bar(
        total=1, title="Loading subroutines", remove_on_exit=True
    ) as do_imports:
        from textwrap import wrap

        import altair as alt
        import pandas as pd
        import pyarrow as pa

        do_imports.update(subtitle="Done!")
    return alt, mo, pd, wrap


@app.cell
def helpers(pd):
    def path(name):
        return f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"

    def pudl(name, **kwargs):
        df = pd.read_parquet(
            path(name),
            **kwargs,
        )
        # fastparquet gets the dtypes right but pyarrow seems to miss them
        if "report_date" in df.columns and df.report_date.dtype != "datetime64[s]":
            df["report_date"] = pd.to_datetime(df["report_date"])
        return df

    def table_preview_href(name):
        return f"""<a href="https://data.catalyst.coop/preview/pudl/{name}" target="_blank">{name}</a>"""

    return (pudl,)


@app.cell
def import_dfs_and_glue(mo, pd, pudl):
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
        out_ferc1__yearly_rate_base1 = pudl("out_ferc1__yearly_rate_base")
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

    out_ferc1__yearly_rate_base = out_ferc1__yearly_rate_base1.merge(
        out_pudl__entity_utilities_pudl.drop_duplicates(
            subset=["utility_id_pudl", "utility_id_ferc1", "report_year"]
        )[
            ["utility_id_pudl", "utility_id_ferc1", "utility_name_pudl", "report_year"]
            + state_cols
        ],
        on=["utility_id_pudl", "utility_id_ferc1", "report_year"],
        how="left",
        validate="m:1",
    ).sort_values(by=["report_year"])

    core_eia861__yearly_sales = core_eia861__yearly_sales.merge(
        out_pudl__entity_utilities_pudl.drop_duplicates(
            subset=["utility_id_eia", "report_date"]
        )[
            ["utility_id_pudl", "utility_id_eia", "utility_name_pudl", "report_date"]
            + state_cols
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
def add_columns(
    core_eia861__yearly_sales,
    out_ferc1__yearly_rate_base,
    pd,
    state_cols,
):
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
    for fill_meth in ["bfill", "ffill"]:
        out_ferc1__yearly_rate_base.loc[:, state_cols] = (
            out_ferc1__yearly_rate_base.groupby(["utility_id_pudl"])[
                state_cols
            ].transform(fill_meth)
        )
        out_ferc1__yearly_rate_base.loc[:, "utility_name_pudl"] = (
            out_ferc1__yearly_rate_base.groupby(["utility_id_pudl"])[
                ["utility_name_pudl"]
            ].transform(fill_meth)
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


@app.cell
def options_ferc1(
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
                    pd.Series(["", "ALL"]),
                    out_eia861__yearly_utility_service_territory.state.drop_duplicates().sort_values(),
                ]
            )

        @classmethod
        @mo.cache
        def available_utilities(cls, states: str) -> pd.Series:
            df = out_ferc1__yearly_rate_base
            if states != "ALL":
                df = out_ferc1__yearly_rate_base.loc[
                    (df.filter(like="state_") == states).any(axis="columns")
                ]
            utils = df.loc[:, "utility_name_pudl"].drop_duplicates().sort_values()
            return pd.concat([pd.Series(["ALL"]), utils])

        @classmethod
        @mo.cache
        def available_years(cls, utilities_1) -> pd.Series:
            if utilities_1 == "ALL" or utilities_1 != "":
                df = out_ferc1__yearly_rate_base
            else:
                df = out_ferc1__yearly_rate_base.loc[
                    out_ferc1__yearly_rate_base.utility_name_pudl.isin(
                        list(utilities_1)
                    )
                ]
            return (
                df.report_year.drop_duplicates()
                .astype(pd.Int64Dtype())
                .sort_values(ascending=False)
            )

    return (OptionsFerc1,)


@app.cell
def build_query_params(OptionsFerc1, mo):
    # this has to be in a cell other than the cell where `selection` is defined,
    # otherwise updates won't propagate correctly.
    query_params = mo.query_params()

    def initialize_default_params():
        if "state_1" not in query_params:
            query_params["state_1"] = "ALL"
        if "utilities_1" not in query_params:
            query_params["utilities_1"] = "ALL"
        # Remove ALL if there are more than ALL in the utils
        util_set = set(query_params["utilities_1"].split("|"))
        if (len(util_set) > 1) and ("ALL" in util_set):
            util_set = {util for util in util_set if util != "ALL"}
            query_params["utilities_1"] = "|".join(util_set)
        available_years = OptionsFerc1.available_years(util_set)
        if "year_range" not in query_params:
            query_params["year_range"] = (
                f"{min(available_years)}|{max(available_years)}"
            )
        if "state_2" not in query_params:
            query_params["state_2"] = ""
        if "utilities_2" not in query_params:
            query_params["utilities_2"] = ""
        # Remove ALL if there are more than ALL in the utils
        util_set = set(query_params["utilities_2"].split("|"))
        if (len(util_set) > 1) and ("ALL" in util_set):
            util_set = {util for util in util_set if util != "ALL"}
            query_params["utilities_2"] = "|".join(util_set)

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
def selection(OptionsFerc1, mo, query_params, reset_params):
    from functools import cached_property

    from pydantic import BaseModel, Field, computed_field, field_validator

    class Selection(BaseModel):
        """Store/represent the user's current utility selection.

        The direct values (utilities, years, etc) are pulled from
        and persisted to the corresponding URL parameters.

        The selector views (utilities_selector, years_selector, etc) are
        computed based on the values and cached for display in the dashboard."""

        state_1: str = Field("ALL")
        utilities_1: set[str] = Field({"ALL"})

        state_2: str | None = Field(None)
        utilities_2: set[str] = Field({None})

        year_range: list[str]

        @computed_field
        @cached_property
        def year_range_silder(self) -> mo.ui.range_slider:
            available_years = OptionsFerc1.available_years(self.utilities_1)
            range_slider = mo.ui.range_slider(
                steps=range(min(available_years), max(available_years) + 1),
                value=[int(self.year_range[0]), int(self.year_range[1])],
                full_width=True,
                # this label by default is on top of not to the left of the selector..
                # which is a little annoying/inconsistent but alas
                label="Years:",
                on_change=lambda value: reset_params(
                    year_range="|".join([str(y) for y in value])
                ),
            )
            return range_slider

        @computed_field
        @cached_property
        def state_1_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options=list(OptionsFerc1.available_states()),
                value=self.state_1,
                label="State:",
                on_change=lambda value: reset_params(state_1=value, utilities_1="ALL"),
            )

        @computed_field
        @cached_property
        def utilities_1_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_utilities(self.state_1)),
                value=self.utilities_1,
                label="Utility:",
                max_selections=10,
                on_change=lambda value: reset_params(utilities_1="|".join(value)),
            )

        @computed_field
        @cached_property
        def state_2_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options=list(OptionsFerc1.available_states()),
                value=self.state_2,
                label="State:",
                # when this one changes, reset the state_1 param and clear the utils param
                on_change=lambda value: reset_params(state_2=value, utilities_2="ALL"),
            )

        @computed_field
        @cached_property
        def utilities_2_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_utilities(self.state_2)),
                value=self.utilities_2,
                label="Utility:",
                max_selections=10,
                on_change=lambda value: reset_params(utilities_2="|".join(value)),
            )

        @field_validator("utilities_1", "utilities_2", mode="before")
        @classmethod
        def deserialize_set(cls, value: str) -> set[str]:
            if value == "":
                out = set()
            else:
                out = set(value.split("|"))
            return out

        @field_validator("year_range", mode="before")
        @classmethod
        def deserialize_list(cls, value: str) -> set[str]:
            if value == "":
                out = []
            else:
                out = value.split("|")
            return out

    selection = Selection(**query_params.to_dict())
    return BaseModel, selection


@app.cell
def chart_type_select(mo):
    mark_type_selector = mo.ui.dropdown(
        options={"Stacked Bar": "mark_bar", "Line": "mark_line"},
        label="Chart Display Type:",
        value="Stacked Bar",
    )
    return (mark_type_selector,)


@app.cell
def sidebar(mark_type_selector, mo, selection):
    mo.sidebar(
        [
            mo.md("## Make Selections:"),
            mo.md("### Choose Utilities:"),
            mo.vstack(
                [  # the hstack's leave spaces after them, unless you wrap them in a vstack stack stack stack
                    mo.hstack(
                        [
                            mo.md(
                                f"""<div data-tooltip="View an entire state's data or subset to utilities within that state. All states are displayed by default.">{mo.icon("lucide:info")}</div>"""
                            ),
                            selection.state_1_selector,
                        ],
                        justify="start",
                        align="start",
                        gap=0,
                    ),
                    mo.hstack(
                        [
                            mo.md(
                                f"""<div data-tooltip="Choose a utility to explore. Selecting more than one utility will sum the outputs.">{mo.icon("lucide:info")}</div>"""
                            ),
                            selection.utilities_1_selector,
                        ],
                        justify="start",
                        align="start",
                        gap=0,
                    ),
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.md("""###To compare, choose additional utilities:"""),
            mo.vstack(
                [
                    mo.hstack(
                        [
                            mo.md(
                                f"""<div data-tooltip="View an entire state's data or subset to utilities within that state. All states are displayed by default.">{mo.icon("lucide:info")}</div>"""
                            ),
                            selection.state_2_selector,
                        ],
                        justify="start",
                        align="start",
                        gap=0,
                    ),
                    mo.hstack(
                        [
                            mo.md(
                                f"""<div data-tooltip="Choose a utility to explore. Selecting more than one utility will sum the outputs.">{mo.icon("lucide:info")}</div>"""
                            ),
                            selection.utilities_2_selector,
                        ],
                        justify="start",
                        align="start",
                        gap=0,
                    ),
                ],
                justify="start",
                align="start",
                gap=0,
            ),
            mo.md("### Other Options:"),
            mo.vstack(
                [
                    selection.year_range_silder,
                    mark_type_selector,
                ],
                justify="start",
                align="start",
                # weirdly 0 gap seems a lil too smol
                gap=2,
            ),
        ]
    )


@app.cell
def no_utilities_1_stop(mo, selection):
    mo.stop(
        not selection.model_dump().get("utilities_1"),
        mo.md(
            "## 🛑 **Choose a utilities the sidebar.** ⬅️\nWe really want to show you some pretty graphs, but you have to select utilities to show. If you happen to choose utilities in the 'To compare' section, you still need to choose utilities above that."
        ),
    )


@app.cell
def filter_dfs(
    BaseModel,
    core_eia861__yearly_sales,
    out_ferc1__yearly_rate_base,
    selection,
):
    from typing import TypeVar

    PandasDataFrame = TypeVar("PandasDataFrame")

    class GraphInput(BaseModel):
        filtered_rate_base: PandasDataFrame
        filtered_sales: PandasDataFrame
        utility_selection_title_part: str
        utils_subtitle: str
        utility_selection: set

    class GraphInputs(BaseModel):
        opt_1: GraphInput | dict
        opt_2: GraphInput | dict

    graph_inputs = {"opt_1": {}, "opt_2": {}}

    for opt_n in graph_inputs:
        utility_selection = selection.model_dump().get(
            f"utilities_{opt_n.removeprefix('opt_')}"
        )
        state_selection = selection.model_dump().get(
            f"state_{opt_n.removeprefix('opt_')}"
        )
        if utility_selection:
            # Set default mask and title
            utility_selection_title_part = "All Utilities"
            utils_subtitle = ""

            year_range = selection.year_range
            rate_mask = out_ferc1__yearly_rate_base.report_year.between(
                int(year_range[0]), int(year_range[1])
            )

            # Only show utilities which also show up in FERC1
            sales_mask = core_eia861__yearly_sales.report_year.between(
                int(year_range[0]), int(year_range[1])
            ) & (
                core_eia861__yearly_sales.utility_id_pudl.isin(
                    list(out_ferc1__yearly_rate_base.utility_id_pudl.unique())
                )
            )
            if state_selection != "ALL":
                rate_mask = rate_mask & (
                    (
                        out_ferc1__yearly_rate_base.filter(like="state")
                        == state_selection
                    ).any(axis=1)
                )
                sales_mask = sales_mask & (
                    (
                        core_eia861__yearly_sales.filter(like="state")
                        == state_selection
                    ).any(axis=1)
                )
                utility_selection_title_part = f"{state_selection} Utilities"
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
                    utility_selection_title_part = f"{next(iter(utility_selection))}"
            filtered_rate_base = out_ferc1__yearly_rate_base[rate_mask]
            filtered_sales = core_eia861__yearly_sales[sales_mask]
            graph_inputs[opt_n] = GraphInput(
                filtered_rate_base=filtered_rate_base,
                filtered_sales=filtered_sales,
                utility_selection_title_part=utility_selection_title_part,
                utils_subtitle=utils_subtitle,
                utility_selection=utility_selection,
            )
    graph_inputs = GraphInputs(**graph_inputs)
    return GraphInput, GraphInputs, graph_inputs


@app.cell
def chart_tools(
    BaseModel,
    GraphInput,
    GraphInputs,
    alt,
    mark_type_selector,
    mo,
    pd,
    wrap,
):
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

    # So many of the inputs for the charts were exactly the same with slight permutations. Plus I wanted to be able to
    # either show one utility's charts OR two graphs for a comparison. So i did a slightly silly thing of compiling
    # all of the inputs

    class ColumToChart(BaseModel):
        col: str
        """Name of the column to display in chart."""
        aggregate: str
        """How to aggreate the data. Generally Sum or Mean. Also first word in title."""
        title_middle: str
        """The middle bit of the title. Ex: Sum/Mean of (middle bit) for All/PA Utilities"""
        preamble: str = ""
        """Words to apear before this column's chart(s)."""
        # Everything below is an alt.Chart or encode argument
        color_stack: str
        """Name of column that you want to stack."""
        y_title: str
        y_axis_format: str | None = None
        xOffset: str | None = None
        """If you want a side-by-side bars instead of stacked bar add xOffset."""
        filter_on_color_stack: list[str] | None = None
        colors: list[str] = cat_colors

    def make_chart(
        df: pd.DataFrame,
        graph_input: GraphInput,
        col_to_chart: ColumToChart,
    ):
        """Make a chart!

        Args:
            df: DataFrame to graph
            graph_input: inputs for graphing based on the first or second
                utility selection. See ``GraphInput`` above.
            col_to_chart: inputs for charting a columns ;-) see ``ColumToChart``.
        """
        aggregate = col_to_chart.aggregate
        col = col_to_chart.col
        # now do the chart
        color_stack = col_to_chart.color_stack
        if col_to_chart.filter_on_color_stack:
            df = df[df[color_stack].isin(col_to_chart.filter_on_color_stack)]
        # groupby first bc its toooo big otherwise T_T
        gb = df.groupby(["report_year", color_stack], observed=True)[col]
        agged = getattr(gb, aggregate)().reset_index()
        chart_cls = alt.Chart(
            agged,
            title=alt.Title(
                wrap(
                    f"{aggregate.title()} of {col_to_chart.title_middle} for {
                        graph_input['utility_selection_title_part']
                    }"
                ),
                subtitle=wrap(graph_input["utils_subtitle"]),
            ),
        )
        # make the chart a side-by-side chart when there is an xOffest set
        # and also its a bar chart
        xOffset_if_bar_and_side_by_side = (
            {"xOffset": col_to_chart.xOffset}
            if col_to_chart.xOffset and mark_type_selector.value == "mark_bar"
            else {}
        )
        return (
            getattr(chart_cls, mark_type_selector.value)(tooltip=True)
            .encode(
                alt.X("report_year", type="ordinal").title("Report date"),
                alt.Y(col)
                .axis(format=col_to_chart.y_axis_format)
                .title(col_to_chart.y_title),
                color=alt.Color(color_stack).scale(range=col_to_chart.colors),
                tooltip=[
                    alt.Tooltip(
                        col,
                        format=col_to_chart.y_axis_format,
                    ),
                    alt.Tooltip(color_stack),
                ],
                **xOffset_if_bar_and_side_by_side,
            )
            .properties(
                width="container",
            )
        )

    def make_comparison_charts(
        cols_to_chart: list[ColumToChart], graph_inputs: GraphInputs, df_name: str
    ):
        for col_to_chart in cols_to_chart:
            stack_graphs = {}
            for option_n, graph_input in graph_inputs.dict().items():
                if graph_input:
                    rate_base_chart = make_chart(
                        df=graph_input[df_name],
                        col_to_chart=col_to_chart,
                        graph_input=graph_input,
                    )
                    stack_graphs[option_n] = rate_base_chart
            mo.output.append(mo.md(col_to_chart.preamble))
            if len(stack_graphs) == 1:
                mo.output.append(stack_graphs["opt_1"])
            else:
                mo.output.append(
                    alt.hconcat(stack_graphs["opt_1"], stack_graphs["opt_2"])
                )

    return ColumToChart, make_comparison_charts


@app.cell
def chart_ferc1(ColumToChart, graph_inputs, make_comparison_charts, mo):
    mo.output.append(mo.md("""## 🧮 Utility Rate Base"""))

    cols_to_chart_ferc1 = [
        ColumToChart(
            preamble=(
                "How has a utility's overall expenses or capital increased or decreased over time? Are the increases coming from the **generation of electricity** or the **transmission and distribution system**? Consider fixed vs. variable costs."
            ),
            col="ending_balance",
            aggregate="sum",
            title_middle="Rate Base by Function Type",
            y_title="Nominal USD",
            y_axis_format="$,.0f",
            color_stack="plant_function_type",
        ),
        ColumToChart(
            preamble=(
                'Want to dig in further? This graph breaks down rate base by "plant function", a FERC-defined label of what function an expense or capital cost plays in utility operations.'
            ),
            col="ending_balance",
            title_middle="Rate Base by Plant Function",
            y_title="Nominal USD",
            y_axis_format="$,.0f",
            aggregate="sum",
            color_stack="plant_function",
        ),
        ColumToChart(
            preamble=(
                "__Details Abound!__ The smart folks at <a href='rmi.org' target='_blank'>RMI</a> labeled rate base categories with even more detail. This is a more detailed break down of these rate base costs."
            ),
            col="ending_balance",
            aggregate="sum",
            title_middle="Rate Base by Category",
            y_title="Nominal USD",
            y_axis_format="$,.0f",
            color_stack="rate_base_category",
        ),
    ]

    make_comparison_charts(cols_to_chart_ferc1, graph_inputs, "filtered_rate_base")


@app.cell
def chart_eia861(ColumToChart, graph_inputs, make_comparison_charts, mo):
    mo.output.append(
        mo.md("""## 🧾 Utility Sales from Customers
        Now let's look at how much utilities are collecting from customers using
        <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia861.html" target="_blank">EIA-861 data</a>.
        PUDL has different years of data integrated for EIA-861 and FERC Form 1, so
        there will be slightly different years in the following graphs.
        """)
    )
    customer_colors = ["palevioletred", "purple", "lightseagreen"]
    cols_to_chart_eia861 = [
        ColumToChart(
            preamble=(
                "How has utility sales changed over time? Is this different than the rate base changing over time?\n"
                "How much of the revenue that utilities collect comes from each "
                "type of customer?"
            ),
            col="sales_revenue",
            title_middle="Sales Revenue by Customer Class",
            y_title="Nominal USD",
            aggregate="sum",
            colors=customer_colors,
            color_stack="customer_class",
            y_axis_format="$,.0f",
            filter_on_color_stack=["commercial", "industrial", "residential"],
        ),
        ColumToChart(
            preamble=(
                "What about average monthly revenue per residential customers? This "
                "isn't exactly equivalent to average monthly customer bills, but it is a good proxy."
            ),
            col="revenue_per_month_customer",
            title_middle="Monthly Residential Sales",
            y_title="Sales (Nominal $USD) per Customer per Month",
            aggregate="mean",
            colors=[customer_colors[-1]],
            color_stack="customer_class",
            y_axis_format="$,.0f",
            # I added a filter in here bc.. well I assume most people want to see residential
            # and with all customers the residential customers were drowned out
            filter_on_color_stack=["residential"],
            xOffset="customer_class",
        ),
        ColumToChart(
            preamble=(
                "How has electricity consumption changed over time within these different customer classes?\n"
                "**Hint**: Generally speaking, electricity consumption over the last few decades has been incredibly flat."
            ),
            col="sales_mwh",
            title_middle="MWh Sales by Customer Class",
            y_title="MWh",
            aggregate="sum",
            y_axis_format=",.0f",
            colors=customer_colors,
            color_stack="customer_class",
            filter_on_color_stack=["commercial", "industrial", "residential"],
        ),
        ColumToChart(
            col="sales_revenue_by_mwh",
            title_middle="Revenue per MWh by Customer Class",
            y_title="Nominal $USD /MWh",
            aggregate="mean",
            colors=customer_colors,
            color_stack="customer_class",
            y_axis_format="$,.0f",
            filter_on_color_stack=["commercial", "industrial", "residential"],
            xOffset="customer_class",
        ),
    ]

    make_comparison_charts(cols_to_chart_eia861, graph_inputs, "filtered_sales")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 📚 Additional Resources
    """)


@app.cell
def materials_accordion(mo):
    mo.accordion(
        {
            "### Rate base ➡️ Customer Bills": mo.md("""
    * 🧱 Utility Revenue Requirements: The Building Blocks for Utility Bills
      * In order to set rates for consumers, utilities must calculate a revenue requirement which
        includes expenses, investments, and a rate of return on capital investment, among other
        things. Each state regulates rates a little differently, but at the most basic level:
        Revenue Requirement = (Rate Base * Rate of Return) + Expenses
    * 🧮 What is a “Rate Base”?
      * FERC defines Rate Base as: “The value of property upon which a utility is permitted to
        earn a specified rate of return as established by a regulatory authority.”
      * Rate Base includes all property and assets that the utility invests in and maintains for
        the purpose of serving customers. Some examples include the land and equipment for power
        plants, the poles, wires and substations of the distribution system, as well as repair
        equipment, vehicles and administrative buildings.
    * ⛽ Expenses (not included in rate base)
      * Fuel cost & other expenses : Expenses are effectively passed on to consumers. These costs
        are not included in the rate base, but do affect customer bills.
      * Fuel costs are the most notable because they can be volatile and can be significant.
    * 🥧 How do revenue requirements get translated into customer bills? 🧾
      * Determining the revenue requirement is like determining the size of a pie; allocating costs
        to different consumers is like slicing up the pie amongst utility customers.
      * Cost allocation: Allocating utility costs to customers happens in a rate case and involves
        cost of service studies.
      * The EIA-861 data in this dashboard tells us about how much revenue is collected from
        different kinds of customers, but it does not tell us about how rates are structured
        or calculated. For more information about rate schedules you can explore
        <a href='https://data.catalyst.coop/preview/pudl/out_ferc1__yearly_sales_by_rate_schedules_sched304' target='_blank'>out_ferc1__yearly_sales_by_rate_schedules_sched304</a>,
        but beware that table is particularly messy and hard to interpret.
    * 🤔 Some key concepts to consider when exploring utility rates:
      * __Capital bias__: This is a well understood result of the predominant rate design in the
        U.S., which incentivizes utilities to invest more capital into their systems because they
        get a fixed rate of return for allowable capital investments.
      * __Fixed vs. variable__: Some costs are variable based on the amount of electricity
        consumers use (ex: using natural gas when generating electricity at a natural gas
        generation facility) and some costs are relatively fixed (ex: investments in maintaining
        the physical structure at a natural gas plant or the maintenance costs for the
        distribution system in an area that isn't experiencing lots of growth). Many things on the
        "fixed" side of rates certainly change over time and require investments when use of the
        existing infrastructure expands.
      * __Demand vs volumetric charges__: Residential customers almost always see volumetric
        pricing, meaning they are charged in direct proportion to how much energy they consume.
        However, large commercial and industrial customers often have rate structures that are
        demand-based, meaning they are charged based on the maximum load they put on the system
        in a given billing period."""),
            "### 😵‍💫 Complicating Factors": mo.md("""
    * __Inflation__: All costs in this dashboard are nominal USD.
    * __Fuel costs__: As noted above, the rate base data does not include pass through costs like
      fuel which can be substantial.
    * __FERC Form 1 respondents only__: Because we only have rate base data for those utilities
      which report to FERC Form 1 (see
      <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html#who-submits-this-data" target="_blank">reporting requirements</a>),
      this entire dashboard is restricted to only those utilities. This biases the utilities shown
      here towards larger utilities which tend to be more investor owned utilities. Municipal and
      cooperative utilities do not report to FERC at all and so do not appear in this data.
    * __Multi-state utilities__: FERC 1 respondents report their data for the entire utility,
      which can sometimes span multiple states. When selecting states, know that the available
      utilities in that state may include data from multi-state utilities.
    * __Deregulated markets__: States which have utility markets which preclude or discourage
      customer-serving utilities from owning generation will show up in this data a little
      differently. These utilities buy generation on the market - so generation doesn't show
      up in their rate base because generation is purely an expense for them.
            """),
            "### 🔗 Further Reading": mo.md("""
    * <a href="https://www.nasuca.org/wp-content/uploads/2025/02/Rate-Base-Overview-Slide-Deck-NASUCA-Feb-2025-2025.02.24-v2.0.pdf" target="_blank">NASUCA's Overview of Rate Base</a>
    * <a href="https://affordability-toolkit.rmi.org/" target='_blank'>RMI's Electricity Affordability Toolkit</a>
    * <a href='https://utilitydisconnections.org/' target='_blank'>Utility Disconnection Dashboard</a>
    * <a href='https://www.raponline.org/wp-content/uploads/2023/09/appendix-a-smart-rate-design-2015-aug-31.pdf' target='_blank'>RAP's Smart Rate Design for a Smart Future</a>
    * <a href='https://www.raponline.org/wp-content/uploads/2023/10/rap-improving-utility-performance-incentives-in-the-united-states-2023-october.pdf' target='_blank'>RAP's Improving Utility Performance Incentives in the United States</a>"""),
        }
    )


@app.cell(hide_code=True)
def contact_us(mo):
    mo.md(r"""
    If you see anything odd in the data, find a bug or just have a question, feel free to reach out to us by emailing us at hello@catalyst.coop or write up a <a href="https://github.com/catalyst-cooperative/pudl/issues/new?template=bug_report.md" target="_blank">github issue</a>. Heck, if you just found this helpful, let us know! As an open-source project we love to hear about your energy data needs.
    """)


if __name__ == "__main__":
    app.run()
