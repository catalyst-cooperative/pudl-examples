import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.output.append(mo.md("# Rates Explorer"))
    mo.output.append(
        mo.md(
            'Explore utility rates with data from <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html" target="_blank">FERC Form 1</a> or <a href="https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia861.html" target="_blank">EIA-861</a>.'
        )
    )
    return


@app.cell
def _():
    import marimo as mo

    with mo.status.progress_bar(
        total=1, title="Loading subroutines", remove_on_exit=True
    ) as do_imports:
        import fastparquet as fp
        import pandas as pd
        import pyarrow as pa
        import altair as alt
        from textwrap import wrap

        do_imports.update(subtitle="Done!")
    return alt, mo, pd, wrap


@app.cell
def _(pd):
    def path(name):
        return f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"

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
def _(mo, pudl):
    with mo.status.progress_bar(
        total=4,
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
        # done
        do_fetch_data.update(subtitle="Done!")

    # glue
    out_pudl__entity_utilities_pudl = core_pudl__entity_utilities_pudl.merge(
        core_pudl__assn_ferc1_pudl_utilities,
        on=["utility_id_pudl"],
        how="outer",
    ).merge(
        core_pudl__assn_eia_pudl_utilities,
        on=["utility_id_pudl"],
        how="outer",
    )

    out_ferc1__yearly_rate_base = out_ferc1__yearly_rate_base.merge(
        out_pudl__entity_utilities_pudl.drop_duplicates(
            subset=["utility_id_pudl", "utility_id_ferc1"]
        )[["utility_id_pudl", "utility_id_ferc1", "utility_name_pudl"]],
        on=["utility_id_pudl", "utility_id_ferc1"],
        how="left",
        validate="m:1",
    )

    core_eia861__yearly_sales = core_eia861__yearly_sales.merge(
        out_pudl__entity_utilities_pudl.drop_duplicates(subset=["utility_id_eia"])[
            ["utility_id_pudl", "utility_id_eia", "utility_name_pudl"]
        ],
        on=["utility_id_eia"],
        how="left",
        validate="m:1",
    )
    return core_eia861__yearly_sales, out_ferc1__yearly_rate_base


@app.cell
def _(core_eia861__yearly_sales, out_ferc1__yearly_rate_base, pd):
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

    core_eia861__yearly_sales.loc[:, "sales_revenue_by_mwh"] = (
        core_eia861__yearly_sales.sales_revenue / core_eia861__yearly_sales.sales_mwh
    )

    core_eia861__yearly_sales.loc[:, "report_year"] = (
        core_eia861__yearly_sales.report_date.dt.year
    )
    return


@app.cell
def _(mo, out_ferc1__yearly_rate_base, pd):
    class OptionsFerc1:
        """Compute valid rate base options based on partial selections.

        Caches the results so we're not constantly repeating dataframe queries.

        Used by marimo ui widgets in constructing dropdown options; used by
        selection initialization in validating/filling gaps in url params."""

        @classmethod
        @mo.cache
        def available_utilities(cls) -> pd.Series:
            return pd.concat(
                [
                    pd.Series(["ALL"]),
                    (
                        out_ferc1__yearly_rate_base.loc[:, ["utility_name_pudl"]]
                        .drop_duplicates()
                        .sort_values(by="utility_name_pudl")
                        .utility_name_pudl
                    ),
                ]
            )

        @classmethod
        @mo.cache
        def available_years(cls, utilities) -> pd.Series:
            if utilities == {"ALL"} or utilities != "":
                df = out_ferc1__yearly_rate_base
            else:
                df = out_ferc1__yearly_rate_base.loc[
                    (
                        out_ferc1__yearly_rate_base.utility_name_pudl.isin(
                            list(utilities)
                        )
                    )
                ]
            return df.report_year.drop_duplicates().sort_values(ascending=False)

    return (OptionsFerc1,)


@app.cell
def _(OptionsFerc1, mo):
    # this has to be in a cell other than the cell where `selection` is defined,
    # otherwise updates won't propagate correctly.
    query_params = mo.query_params()

    def initialize_default_params():
        # print(query_params.keys())
        if "utilities" not in query_params:
            query_params["utilities"] = "ALL"
        util_set = set(query_params["utilities"].split("|"))
        available_years = OptionsFerc1.available_years(util_set)
        if "start_year" not in query_params or (
            int(query_params["start_year"]) not in set(available_years)
        ):
            query_params["start_year"] = str(available_years.min())
        if "end_year" not in query_params or (
            int(query_params["end_year"]) not in set(available_years)
        ):
            query_params["end_year"] = str(available_years.max())

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
    from pydantic import BaseModel, Field, computed_field, field_validator
    from functools import cached_property

    class Selection(BaseModel):
        """Store/represent the user's current utility selection.

        The direct values (utilities, years, etc) are pulled from
        and persisted to the corresponding URL parameters.

        The selector views (utilities_selector, years_selector, etc) are
        computed based on the values and cached for display in the dashboard."""

        utilities: set[str] = Field({"ALL"})
        start_year: str = "1994"
        end_year: str = "2024"

        @computed_field
        @cached_property
        def utilities_selector(self) -> mo.ui.multiselect:
            return mo.ui.multiselect(
                options=list(OptionsFerc1.available_utilities()),
                value={"ALL"},
                label="Choose Utilities or select ALL: ",
                max_selections=15,
                on_change=lambda value: reset_params(utilities="|".join(value)),
            )

        @field_validator("utilities", mode="before")
        @classmethod
        def deserialize(cls, value: str) -> set[str]:
            return set(value.split("|"))

        @computed_field
        @cached_property
        def start_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={str(i) for i in OptionsFerc1.available_years(self.utilities)},
                label="Utility attributes starting from:",
                value=str(self.start_year),
                on_change=lambda value: reset_params(start_year=str(value)),
            )

        @computed_field
        @cached_property
        def end_year_selector(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={str(i) for i in OptionsFerc1.available_years(self.utilities)},
                label="Utility attributes ending:",
                value=str(self.end_year),
                on_change=lambda value: reset_params(end_year=str(value)),
            )

    selection = Selection(**query_params.to_dict())
    return (selection,)


@app.cell
def _(mo, selection):
    mo.vstack(
        [
            mo.hstack(
                [
                    mo.md(
                        f"""<div data-tooltip="By default we show you all utilities. If you want to chose particular ones, select here.">{mo.icon("lucide:info")}</div>"""
                    ),
                    selection.utilities_selector,
                ],
                justify="start",
            ),
            mo.hstack(
                [
                    mo.md(f"""<div data-tooltip="By default we extend the timeseries as far back as we have data available.
                To prune to a more recent year, select here.">{mo.icon("lucide:info")}</div>"""),
                    selection.start_year_selector,
                ],
                justify="start",
            ),
            mo.hstack(
                [
                    mo.md(f"""<div data-tooltip="By default we include the most recent data available.
                To prune to a less recent year, select here.">{mo.icon("lucide:info")}</div>"""),
                    selection.end_year_selector,
                ],
                justify="start",
            ),
            mo.md("----"),
            mo.md(
                "Here is what we know about utility costs. Not all utilities report to both FERC and EIA 861."
            ),
        ]
    )
    return


@app.cell
def _(core_eia861__yearly_sales, out_ferc1__yearly_rate_base, selection):
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

    if selection.utilities != {"ALL"}:
        rate_mask = rate_mask & (
            out_ferc1__yearly_rate_base.utility_name_pudl.isin(selection.utilities)
        )
        sales_mask = sales_mask & (
            core_eia861__yearly_sales.utility_name_pudl.isin(selection.utilities)
        )
        if (util_len := len(selection.utilities)) > 1:
            utility_selection_title_part = f"{util_len} Utilities"
            utils_subtitle = " & ".join(selection.utilities)
        else:
            utility_selection_title_part = f"{list(selection.utilities)[0]} Utilities"
    filtered_rate_base = out_ferc1__yearly_rate_base[rate_mask]
    filtered_sales = core_eia861__yearly_sales[sales_mask]
    return (
        filtered_rate_base,
        filtered_sales,
        utility_selection_title_part,
        utils_subtitle,
    )


@app.cell
def _(
    alt,
    filtered_rate_base,
    mo,
    utility_selection_title_part,
    utils_subtitle,
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

    rate_base_all_chart = (
        alt.Chart(
            filtered_rate_base,
            title=alt.Title(
                f"Annual Sum of Rate Base by Plant Function for {utility_selection_title_part}",
                subtitle=wrap(utils_subtitle),
            ),
        )
        .mark_bar()
        .encode(
            alt.X("report_year", type="ordinal").title("Report date"),
            alt.Y("ending_balance", aggregate="sum").title("Nominal USD"),
            color=alt.Color("plant_function").scale(range=cat_colors),
        )
    )

    mo.output.append(mo.ui.altair_chart(rate_base_all_chart))

    plant_category_chart = (
        alt.Chart(
            filtered_rate_base,
            title=alt.Title(
                f"Annual Sum of Rate Base by Category for {utility_selection_title_part}",
                subtitle=wrap(utils_subtitle),
            ),
        )
        .mark_bar()
        .encode(
            alt.X("report_year", type="ordinal").title("Report date"),
            alt.Y("ending_balance", aggregate="sum").title("Nominal USD"),
            color=alt.Color("rate_base_category").scale(range=cat_colors),
        )
    )

    mo.output.append(mo.ui.altair_chart(plant_category_chart))
    return (cat_colors,)


@app.cell
def _(
    alt,
    cat_colors,
    filtered_sales,
    mo,
    utility_selection_title_part,
    utils_subtitle,
):

    cols_to_chart = [
        {
            "col": "sales_revenue",
            "title": "Sales Revenue by Customer Class",
            "y_title": "$",
            "aggregate": "sum",
        },
        {
            "col": "sales_mwh",
            "title": "MWh Sales by Customer Class",
            "y_title": "MWh",
            "aggregate": "sum",
        },
        {
            "col": "sales_revenue_by_mwh",
            "title": "Revenue per MWh by Customer Class",
            "y_title": "$/MWh",
            "aggregate": "mean",
        },
    ]
    for col_to_chart in cols_to_chart:
        sales_chart = (
            alt.Chart(
                # w/o this drop, we loose all customer_class that come after the nulls
                filtered_sales.dropna(subset=[col_to_chart["col"]]).assign(
                    year=lambda x: x.report_date.dt.year
                ),
                title=alt.Title(
                    f"Annual {col_to_chart['aggregate'].title()} of {col_to_chart['title']} for {utility_selection_title_part}",
                    subtitle=utils_subtitle,
                ),
            )
            .mark_bar()
            .encode(
                alt.X("year", type="ordinal").title("Report date"),
                alt.Y(col_to_chart["col"], aggregate=col_to_chart["aggregate"]).title(
                    col_to_chart["y_title"]
                ),
                color=alt.Color("customer_class").scale(range=cat_colors),
            )
        )

        mo.output.append(mo.ui.altair_chart(sales_chart))
    return


if __name__ == "__main__":
    app.run()
