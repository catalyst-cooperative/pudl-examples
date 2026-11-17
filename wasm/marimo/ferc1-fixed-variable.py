import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Phse 1 Report: FERC Form 1 Non-Fuel O&M Fixed vs. Variable Cost Breakdown

    Goal: Categorize FERC Form 1 expenditure columns as fixed or variable using statistical regression.
    """)


@app.cell
def _():
    import warnings

    import altair as alt
    import numpy as np
    import pandas as pd
    import statsmodels.formula.api as smf

    import marimo as mo

    return alt, mo, np, pd, smf, warnings


@app.cell
def _(pd):
    def pudl(name):
        return pd.read_parquet(
            f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/v2026.10.0/{name}.parquet"
        )

    return (pudl,)


@app.cell
def _(pudl):
    out_ferc1__yearly_all_plants = pudl("out_ferc1__yearly_all_plants").assign(
        installation_age=lambda x: 2026 - x.installation_year,
        construction_age=lambda x: 2026 - x.construction_year,
    )
    out_ferc1__yearly_all_plants.fillna({"plant_type": "null"}, inplace=True)
    None
    return (out_ferc1__yearly_all_plants,)


@app.cell
def _(out_ferc1__yearly_all_plants):
    opex_all = [
        c
        for c in out_ferc1__yearly_all_plants.columns
        if c.startswith("opex_") and not c.endswith("_per_mwh")
    ]
    capex_all = [
        c
        for c in out_ferc1__yearly_all_plants.columns
        if c.startswith("capex_") and not "_per_kw" in c and not "_per_mw" in c
    ] + ["asset_retirement_cost"]
    # len(opex_all), len(capex_all)
    return capex_all, opex_all


@app.cell
def _(capex_all, opex_all):
    """
    Encode subtotal mappings using XBRL documentation.
    """
    subtotals = {k: [] for k in (opex_all + capex_all)}
    subtotals["capex_total"] = [
        # 402 only
        "capex_land",
        "capex_structures",
        "capex_equipment",
        "asset_retirement_cost",
        # +406
        "capex_facilities",
        "capex_roads",
        # +408
        "capex_wheels_turbines_generators",
        "capex_equipment_electric",
        "capex_equipment_misc",
    ]
    subtotals["opex_production_total"] = [
        # 402 only
        "opex_operations",
        "opex_fuel",
        "opex_coolants",
        "opex_steam",
        "opex_steam_other",
        "opex_transfer",
        "opex_electric",
        "opex_misc_power",
        "opex_rents",
        "opex_allowances",
        "opex_engineering",
        "opex_structures",
        "opex_boiler",
        "opex_plant",
        "opex_misc_steam",
        # +406
        "opex_water_for_power",
        "opex_hydraulic",
        "opex_generation_misc",
        "opex_dams",
        "opex_misc_plant",
    ]
    subtotals["opex_production_before_pumping"] = [
        # 408
        "opex_operations",
        "opex_water_for_power",
        "opex_pumped_storage",
        "opex_electric",
        "opex_generation_misc",
        "opex_rents",
        "opex_engineering",
        "opex_structures",
        "opex_dams",
        "opex_plant",
        "opex_misc_plant",
    ]
    subtotals["opex_total"] = [
        # 408
        "opex_production_before_pumping",
        "opex_pumping",
    ]
    return (subtotals,)


@app.cell
def _(capex_all, mo, opex_all):
    correlate_selector = mo.ui.dropdown(
        label="correlate", options=opex_all + capex_all, value=opex_all[0]
    )
    variable_selector = mo.ui.dropdown(
        label="variable indicator",
        options=[
            "net_generation_mwh",
            "capacity_factor",
            "installation_age",
            "construction_age",
        ],
        value="net_generation_mwh",
    )
    fixed_selector = mo.ui.dropdown(
        label="fixed indicator",
        options=[
            "capacity_mw",
            "avg_num_employees",
            "plant_hours_connected_while_generating",  # proxy for operating hours; may need to recompute this cumulatively from install date
            "installation_age",
            "construction_age",
        ],
        value="capacity_mw",
    )
    additional_selector = mo.ui.dropdown(
        label="series indicator",
        options=[
            "installation_age",
            "construction_age",
            "plant_type",
            "avg_num_employees",
        ],
        value="plant_type",
    )
    return (
        additional_selector,
        correlate_selector,
        fixed_selector,
        variable_selector,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Exploratory Data Analysis

    First let's look at each correlate plotted against different indicators of variable and fixed expenditures.
    """)


@app.cell
def _(
    additional_selector,
    alt,
    clean__out_ferc1__yearly_all_plants,
    correlate_selector,
    fixed_selector,
    mo,
    np,
    variable_selector,
):
    def make_column_scatter_chart(base, color, trim=0.001):
        df = clean__out_ferc1__yearly_all_plants.dropna(
            subset=[base, correlate_selector.value, color]
        )
        df = df.loc[
            (df[base] > -np.inf)
            & (df[base] < np.inf)
            & (df[correlate_selector.value] > -np.inf)
            & (df[correlate_selector.value] < np.inf)
        ]
        base_range = df[base].quantile([trim, 1 - trim])
        correlate_range = df[correlate_selector.value].quantile([trim, 1 - trim])
        # print(base_range)
        # print(correlate_range)
        df = df.loc[
            df[base].between(base_range.iloc[0], base_range.iloc[1])
            & df[correlate_selector.value].between(
                correlate_range.iloc[0], correlate_range.iloc[1]
            )
        ]
        return df, mo.ui.altair_chart(
            alt.Chart(
                df[[base, correlate_selector.value, color, "record_id"]],
                title=alt.Title(
                    f"{correlate_selector.value} vs {base}",
                    subtitle=f"{df.shape[0]} records",
                ),
            )
            .mark_point(size=5, opacity=0.8, strokeWidth=0.7)
            .encode(
                x=base,
                y=correlate_selector.value,
                color=alt.Color(color),
                tooltip="record_id",
            )
        )

    column_scatter_chart_variable = make_column_scatter_chart(
        variable_selector.value, additional_selector.value
    )[1]
    # column_scatter_chart_variable = make_column_scatter_chart("capacity_factor")
    column_scatter_chart_fixed = make_column_scatter_chart(
        fixed_selector.value, additional_selector.value
    )[1]
    # column_scatter_chart_fixed = make_column_scatter_chart("construction_age")
    # column_scatter_chart_fixed = make_column_scatter_chart("avg_num_employees")
    return column_scatter_chart_fixed, column_scatter_chart_variable


@app.cell
def _(
    additional_selector,
    column_scatter_chart_fixed,
    column_scatter_chart_variable,
    correlate_selector,
    fixed_selector,
    mo,
    variable_selector,
):
    mo.vstack(
        [
            correlate_selector,
            mo.hstack([variable_selector, fixed_selector]),
            additional_selector,
            mo.hstack([column_scatter_chart_variable, column_scatter_chart_fixed]),
        ]
    )


@app.cell
def _(column_scatter_chart_fixed, column_scatter_chart_variable, mo):
    mo.stop(
        column_scatter_chart_variable.value.empty
        and column_scatter_chart_fixed.value.empty
    )

    def display_selection(df):
        return mo.plain(
            df[
                ["record_id"]  # ,"utility_name_ferc1","avg_num_employees"]
            ]
            .reset_index(drop=True)
            .T,
        )

    mo.vstack(
        [
            mo.md("### Selections"),
            mo.hstack(
                [
                    display_selection(column_scatter_chart_variable.value),
                    display_selection(column_scatter_chart_fixed.value),
                ]
            ),
        ]
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Observations

    * Some columns have a strong overall relationship with fixed/variable indicators (netgen, capacity, etc.), but not all
    * Some columns have a strong relationship with fixed/variable indicators only within certain plant types
    * Some columns have a strong relationship with fixed/variable indicators across multiple plant types, but the exact relationship (slope) is different for different plant types
    * Missing plant type ("null") sometimes contains strong relationships; this is unexpected and unfortunate
    * Capacity is severely entangled with netgen
    * Capacity factor not a good variable-costs indicator
    * Something may be wrong/improperly-aggregated in `plant_hours_connected_while_generating` to yield so many points with more than a  year's worth of hours
    * Installation and construction age not obviously useful here
    """)


@app.cell
def _(
    capex_all,
    clean__out_ferc1__yearly_all_plants,
    fixed_selector,
    opex_all,
    pd,
    variable_selector,
):
    def pearsons_by_planttype():
        dfs = []
        selections = [variable_selector.value, fixed_selector.value]
        for grp, df in clean__out_ferc1__yearly_all_plants.groupby("plant_type"):
            dfs.append(
                pd.DataFrame(
                    {x: df[opex_all + capex_all].corrwith(df[x]) for x in selections}
                    | {
                        "series": [
                            f"{prefix}:{grp}"
                            for prefix in (
                                ["opex"] * len(opex_all) + ["capex"] * len(capex_all)
                            )
                        ]
                    }
                ).reset_index()
            )
        df = pd.concat(dfs)
        centers = df[["index"] + selections].groupby("index").mean().reset_index()
        spreads = df[["index"] + selections].groupby("index").std()
        spreads = spreads.fillna(
            value={x: spreads[x].min() / 2 for x in selections}
        ).reset_index()

        return df, centers, spreads

    # pearsons_by_planttype()
    return (pearsons_by_planttype,)


@app.cell
def _(alt, fixed_selector, pearsons_by_planttype, variable_selector):
    def make_pt_corr_chart(selection):
        df = pearsons_by_planttype()[0]
        df = df.loc[df["index"] == selection]
        return (
            alt.Chart(
                df,
                title=alt.Title(
                    "Pearson's Correlation with fixed vs variable costs",
                    subtitle=f"{selection}; by plant type",
                ),
            )
            .mark_point()
            .encode(
                x=alt.X(variable_selector.value).scale(domain=[-1, 1]),
                y=alt.Y(fixed_selector.value).scale(domain=[-1, 1]),
                color="series",
                tooltip="series",
            )
            + alt.Chart()
            .mark_rule(strokeDash=[2, 2])
            .encode(
                x=alt.value(0),
                y=alt.value("height"),
                x2=alt.value("width"),
                y2=alt.value(0),
            )
            + alt.Chart()
            .mark_rule(strokeDash=[2, 2])
            .encode(
                x=alt.value("width"),
                y=alt.value("height"),
                x2=alt.value(0),
                y2=alt.value(0),
            )
        )

    # df
    return (make_pt_corr_chart,)


@app.cell
def _(
    alt,
    capex_all,
    clean__out_ferc1__yearly_all_plants,
    fixed_selector,
    mo,
    opex_all,
    pd,
    variable_selector,
):
    # TODO: split by plant type before computing corr
    def make_corr_chart():
        df = pd.DataFrame(
            {
                x: clean__out_ferc1__yearly_all_plants[opex_all + capex_all].corrwith(
                    clean__out_ferc1__yearly_all_plants[x]
                )
                for x in [variable_selector.value, fixed_selector.value]
            }
            | {"prefix": ["opex"] * len(opex_all) + ["capex"] * len(capex_all)}
        ).reset_index()
        base = alt.Chart(
            df,
            title=alt.Title(
                "Pearson's Correlation with fixed vs variable costs",
                subtitle="All plant types together",
            ),
        )
        points = base.mark_point().encode(
            x=alt.X(variable_selector.value).scale(domain=[-1, 1]),
            y=alt.Y(fixed_selector.value).scale(domain=[-1, 1]),
            color="prefix",
            tooltip="index",
        )
        xey = alt.Chart().mark_rule(strokeDash=[2, 2]).encode(
            x=alt.value(0),
            y=alt.value("height"),
            x2=alt.value("width"),
            y2=alt.value(0),
        ) + alt.Chart().mark_rule(strokeDash=[2, 2]).encode(
            x=alt.value("width"),
            y=alt.value("height"),
            x2=alt.value(0),
            y2=alt.value(0),
        )
        return df, points + xey

    df, ch = make_corr_chart()
    corr_chart = mo.ui.altair_chart(ch)
    return corr_chart, df


@app.cell
def _(corr_chart, df, make_pt_corr_chart, mo, warnings):

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pt_corr_chart = mo.ui.altair_chart(
            make_pt_corr_chart(corr_chart.apply_selection(df)["index"].values[0])
        )
    return (pt_corr_chart,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Correlation analysis

    Now let's quantify the rough relationships we observed in the EDA above.

    We want to be able to separate columns that track fixed costs from columns that track variable costs. If we compute the Pearson's correlation of an expense column with our variable-cost and fixed-cost indicators, and then plot those correlation coefficients against one another, we can see whether that column more closely tracks variable or fixed costs respectively.

    In the left plot below, each point represents an expense column, colored by whether the column name has prefix `opex` or `capex`. We expect blue points (capex columns) to lie in the north or south quadrant, showing they are more closely correlated to our fixed-cost indicator than to our variable-cost indicator. We expect orange points (opex columns) to lie in the east or west quadrant, showing they are more closely correlated to our variable-cost indicator than to our fixed-cost indicator.

    Since we see some blue points in the east quadrant, and some orange points in the north quadrant, it seems that some columns thought to measure fixed costs are more likely to actually measure variable costs, and vice versa.

    In the righthand plot we demonstrate that these correlations vary significantly by plant type. Click a point in the left plot to drill into that column in the righthand plot. Each point represents a plant type within that expense column. We expect most plant types to lie in the north or south quadrant for capex columns, and most plant types to lie in the east or west quadrant for opex columns. However, even columns which seem unambiguously correlated with our variable-cost indicator in the left plot have some plant types appearing in the north or south quadrant in the righthand plot.
    """)


@app.cell
def _(corr_chart, mo, pt_corr_chart):
    mo.hstack([corr_chart, pt_corr_chart], justify="start")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Regression analysis

    We explore a number of linear regression models for each expense column. These take one of three forms:

    * indicator: `{expense column} ~ indicator`
      * `planttype` (decomposed into binary flags by the model internals)
      * `netgen`
      * `capacity`
    * indicator sum: `{expense column} ~ indicator1 + indicator2 + ...`
      * `netgen + planttype` (with `plant_type` decomposed into binary flags by the model internals)
      * `capacity + planttype`
      * `kitchen sink` (kept adding in columns as long as R-squared kept going up)
    * indicator product: `{expense column} ~ indicator1 * indicator2`
      * `netgen X planttype` (to see if that would take better advantage of variation between plant types)

    Results below.

    When *R-squared* is close to 1.0, the variables in the model are perfectly correlated with / predicts this expense column. When R-squared is close to zero, it means most of the variation in the expense column is unrelated to the variables in the model.

    We throw out NaN entries for the expense column and the variables in the model, so the number of observations *n* varies by expense column and by model.
    """)


@app.cell
def _(smf):
    def run_formula(formula, data, quiet=False):
        results = smf.ols(formula, data=data).fit()
        # if not quiet:
        #     print(results.summary())
        return results

    return (run_formula,)


@app.cell
def _(mo):
    exclude_cooks_outliers_selector = mo.ui.checkbox(
        label="Exclude outliers identified using Cooks analysis below"
    )
    return (exclude_cooks_outliers_selector,)


@app.cell
def _(
    cooks_residual_chart,
    correlate_selector,
    correlate_variable_planttype_model,
    exclude_cooks_outliers_selector,
    mo,
    variable_selector,
):
    mo.accordion(
        {
            "### Helper for dropping outliers with disproportionate effect on the model": mo.vstack(
                [
                    exclude_cooks_outliers_selector,
                    mo.hstack([correlate_selector, variable_selector], justify="start"),
                    mo.hstack(
                        [
                            cooks_residual_chart,
                            mo.vstack(
                                [
                                    mo.md("Selection:"),
                                    mo.plain(cooks_residual_chart.value.i),
                                ]
                            ),
                        ]
                    ),
                    mo.plain_text(str(correlate_variable_planttype_model.summary())),
                ]
            )
        }
    )


@app.cell(hide_code=True)
def _(exclude_cooks_outliers_selector, out_ferc1__yearly_all_plants):
    """Label and remove outliers."""

    wtf_netgen_mwh = (-25_000, 40_000_000)
    wtf_capacity_mw = 50_000
    wtf_record_id = [
        "f1_steam_2003_12_45_3_2",  # netgen
        "f1_steam_2020_12_73_0_4",  # netgen
        "f1_gnrt_plant_1997_12_181_0_4",  # capex_total
    ]
    wtf_record_id = out_ferc1__yearly_all_plants.record_id.loc[
        (out_ferc1__yearly_all_plants.net_generation_mwh > wtf_netgen_mwh[1])
        | (out_ferc1__yearly_all_plants.net_generation_mwh < wtf_netgen_mwh[0])
        | (out_ferc1__yearly_all_plants.capacity_mw > wtf_capacity_mw)
    ].to_list() + ["f1_gnrt_plant_1997_12_181_0_4"]
    wtf_cooks = [
        # opex_allowances
        "steam_electric_generating_plant_statistics_large_plants_402_2022_c000196_mount_storm",
        "steam_electric_generating_plant_statistics_large_plants_402_2023_c000196_mount_storm",
        # opex_boiler
        "f1_steam_2019_12_186_2_5",
        # opex_coolants
        # some sus patterns in the residuals vs leverage; may need a nonlinear factor
        "f1_steam_2003_12_94_0_2",
        "f1_steam_2019_12_133_0_1",
        "steam_electric_generating_plant_statistics_large_plants_402_2022_c000388_diablo_canyon_1__2",
        # opex_electric
        "f1_steam_1994_12_133_12_1",
        "f1_steam_1995_12_133_2_3",
        # opex_engineering
        "f1_steam_1998_12_32_4_4",  # ?maybe keep this one
        # opex_fuel
        "steam_electric_generating_plant_statistics_large_plants_402_2022_c001030_west_county_energy_center",
        # opex_misc_power
        "f1_steam_2014_12_186_2_3",
        "f1_steam_2018_12_133_0_1",
        # opex_misc_steam
        "steam_electric_generating_plant_statistics_large_plants_402_2021_c000906_harrison",
        "steam_electric_generating_plant_statistics_large_plants_402_2024_c000388_diablo_canyon_1__2",
        "steam_electric_generating_plant_statistics_large_plants_402_2023_c000388_diablo_canyon_1__2",
        # opex_nonfuel_per_mwh
        "f1_steam_2016_12_171_0_1",
        "f1_steam_2012_12_19_0_1",
        "f1_steam_2012_12_19_0_2",
        "f1_steam_2001_12_113_0_3",
        "f1_steam_2015_12_42_0_5",
        "f1_steam_2004_12_113_0_2",
        "f1_steam_2016_12_171_0_2",
        "f1_steam_2014_12_44_6_1",
        "steam_electric_generating_plant_statistics_large_plants_402_2022_c000537_dolet_hills_3",
        # opex_operations
        # "f1_steam_1999_12_71_2_1", # [kept; low leverage]
        # "f1_steam_1999_12_73_1_2", # [kept; low leverage]
        "f1_gnrt_plant_2010_12_133_0_45",
        "f1_steam_2013_12_195_2_1",
        "f1_steam_2000_12_73_1_2",
        "f1_steam_1998_12_10_3_4",
        "f1_steam_1999_12_10_3_4",
        # opex_plant
        "steam_electric_generating_plant_statistics_large_plants_402_2023_c001030_martin_solar_energy_center",
        "steam_electric_generating_plant_statistics_large_plants_402_2025_c000388_diablo_canyon_1__2",
        "f1_steam_2014_12_133_0_1",
        "steam_electric_generating_plant_statistics_large_plants_402_2021_c001030_martin_solar_energy_center",
        "steam_electric_generating_plant_statistics_large_plants_402_2022_c001030_martin_solar_energy_center",
        # "f1_steam_2007_12_45_1_1", # [kept; low leverage]
        # opex_production_total
        "f1_steam_2006_12_100_1_2",
        # opex_rent has two clusters in residuals per leverage but nothing to manage here
        # opex_steam
        "f1_steam_1994_12_71_0_1",
        "f1_steam_1998_12_68_0_5",
        "f1_steam_2020_12_186_0_5",
        # opex_steam_other
        # some spooky patterns; may be worth trying to split these
        "f1_steam_1996_12_133_2_3",
        "f1_steam_1998_12_133_2_3",
        "f1_steam_1997_12_133_2_3",
        "f1_steam_1995_12_126_0_4",
        "steam_electric_generating_plant_statistics_large_plants_402_2023_c001646_blundell",
        "steam_electric_generating_plant_statistics_large_plants_402_2024_c001646_blundell",
        # opex_structures
        "f1_steam_2019_12_45_3_5",
        "steam_electric_generating_plant_statistics_large_plants_402_2022_c000388_gateway_gen_station",
        "f1_steam_2016_12_57_0_1",
        "f1_steam_1998_12_68_0_1",
        # opex_total_nonfuel
        # opex_transfer
        # some sus patterns in the residuals vs leverage; may need a nonlinear factor
        "f1_steam_1994_12_69_0_1",
        "f1_steam_2001_12_68_1_5",
        "f1_steam_1995_12_69_0_1",
        "steam_electric_generating_plant_statistics_large_plants_402_2021_c001316_valley",
        "steam_electric_generating_plant_statistics_large_plants_402_2025_c001316_valley",
        "f1_steam_1996_12_69_0_1",
        "f1_steam_2013_12_133_0_2",
        "f1_steam_1994_12_79_2_3",
        "steam_electric_generating_plant_statistics_large_plants_402_2024_c001316_valley",
        # opex_maintenance
        "f1_gnrt_plant_1997_12_186_0_9",
        "generating_plant_statistics_410_2025_c003836_jm_shafer_station",
        "f1_gnrt_plant_2012_12_61_0_41",
        "generating_plant_statistics_410_2023_c000825_hale_wind_farm",
        "generating_plant_statistics_410_2022_c000825_hale_wind_farm",
        "generating_plant_statistics_410_2024_c000825_hale_wind_farm",
        "generating_plant_statistics_410_2023_c000825_sagamore_wind_farm",
        "generating_plant_statistics_410_2024_c000825_sagamore_wind_farm",
        # opex_total
        # opex_dams
        "f1_hydro_2018_12_133_6_3",
        "f1_hydro_1998_12_113_1_4",
        "f1_hydro_2018_12_133_5_3",
        "f1_hydro_2020_12_133_7_2",
        "hydroelectric_generating_plant_statistics_large_plants_406_2023_c000388_803_de_sabla",
        # opex_generation_misc
        "f1_hydro_2019_12_133_0_5",
        "f1_hydro_2012_12_133_6_4",
        "f1_hydro_2018_12_133_2_1",
        # opex_hydraulic
        "f1_hydro_1996_12_168_0_1",
        "f1_hydro_1997_12_168_0_1",
        # opex_misc_plant
        "hydroelectric_generating_plant_statistics_large_plants_406_2024_c001646_2111_swift_no_1",
        "f1_hydro_2004_12_168_0_1",
        # opex_water_for_power
        "f1_hydro_1995_12_168_0_1",
        "f1_hydro_2006_12_177_0_1",
        "f1_hydro_2007_12_177_0_1",
        "f1_hydro_2019_12_57_1_1",
        "f1_hydro_1994_12_168_0_1",
        "f1_hydro_2019_12_57_0_5",
        "f1_hydro_2019_12_57_1_2",
    ]
    clean__out_ferc1__yearly_all_plants = out_ferc1__yearly_all_plants.loc[
        ~out_ferc1__yearly_all_plants.record_id.isin(set(wtf_record_id))
    ]
    if exclude_cooks_outliers_selector.value:
        clean__out_ferc1__yearly_all_plants = clean__out_ferc1__yearly_all_plants.loc[
            ~clean__out_ferc1__yearly_all_plants.record_id.isin(set(wtf_cooks))
        ]
    return (clean__out_ferc1__yearly_all_plants,)


@app.cell
def _(
    alt,
    clean__out_ferc1__yearly_all_plants,
    correlate_selector,
    mo,
    pd,
    run_formula,
    variable_selector,
):
    def make_cooks_residual_chart():
        m = run_formula(
            f"{correlate_selector.value} ~ {variable_selector.value} + plant_type",
            clean__out_ferc1__yearly_all_plants.dropna(subset="plant_type"),
        )
        infl = m.get_influence()
        r = pd.DataFrame(
            {
                "i": clean__out_ferc1__yearly_all_plants.dropna(
                    subset=[
                        correlate_selector.value,
                        variable_selector.value,
                        "plant_type",
                    ]
                ).record_id,
                "residual": infl.resid_studentized_internal,
                "fitted": m.fittedvalues,
                "leverage": infl.hat_matrix_diag,
                "cooks": infl.cooks_distance[0],
            }
        )
        return m, mo.ui.altair_chart(
            alt.Chart(
                r,
                title=f"{correlate_selector.value} ~ {variable_selector.value} ({4 / r.shape[0]})",
            )
            .mark_point()
            .encode(x="leverage", y="residual", size="cooks")
        )

    correlate_variable_planttype_model, cooks_residual_chart = (
        make_cooks_residual_chart()
    )
    return cooks_residual_chart, correlate_variable_planttype_model


@app.cell
def _(
    capex_all,
    clean__out_ferc1__yearly_all_plants,
    np,
    opex_all,
    pd,
    run_formula,
):
    def summarize_arbitrary_model(vars, expression):
        models = {}
        for correlate in opex_all + capex_all:
            formula = f"{correlate} ~ {expression}"
            data = clean__out_ferc1__yearly_all_plants.dropna(subset=[correlate] + vars)
            data = data.loc[
                ~(
                    (data[[correlate] + vars] == np.inf)
                    | (data[[correlate] + vars] == -np.inf)
                ).any(axis="columns")
            ]
            if data.empty:
                continue
            models[correlate] = run_formula(formula, data, quiet=True)
        return models, pd.DataFrame(
            [
                {
                    "column": corr,
                    "R-squared": models[corr].rsquared,
                    "n": models[corr].nobs,
                    "condition": models[corr].condition_number,
                }
                for corr in models
            ]
        )

    return (summarize_arbitrary_model,)


@app.cell
def _(
    capex_all,
    clean__out_ferc1__yearly_all_plants,
    np,
    opex_all,
    pd,
    run_formula,
):
    def summarize_linear_model(vars):
        models = {}
        for correlate in opex_all + capex_all:
            formula = f"{correlate} ~ " + " + ".join(vars)
            data = clean__out_ferc1__yearly_all_plants.dropna(subset=[correlate] + vars)
            data = data.loc[
                ~(
                    (data[[correlate] + vars] == np.inf)
                    | (data[[correlate] + vars] == -np.inf)
                ).any(axis="columns")
            ]
            if data.empty:
                continue
            models[correlate] = run_formula(formula, data, quiet=True)
        return models, pd.DataFrame(
            [
                {
                    "column": corr,
                    "R-squared": models[corr].rsquared,
                    "n": models[corr].nobs,
                    "condition": models[corr].condition_number,
                }
                for corr in models
            ]
        )

    return (summarize_linear_model,)


@app.cell
def _(capex_all, clean__out_ferc1__yearly_all_plants, opex_all):
    def merge_two_models(**kwargs):
        labX, labY = tuple(k for k in kwargs)
        results = (
            kwargs[labX]
            .merge(kwargs[labY], on="column", suffixes=[f"_{lab}" for lab in kwargs])
            .merge(
                clean__out_ferc1__yearly_all_plants[opex_all + capex_all]
                .sum()
                .reset_index(name="total")
                .rename(columns={"index": "column"}),
                on="column",
            )
            .assign(type="capex")
        )
        results.loc[results.column.str.startswith("opex_"), "type"] = "opex"
        return results

    return (merge_two_models,)


@app.cell
def _(alt, merge_two_models):
    def make_compare_model_chart(**kwargs):
        labX, labY = tuple(k for k in kwargs)

        results = merge_two_models(**kwargs)

        base = alt.Chart(
            results,
            title=f"R-squared using {labY} vs {labX} model",
        )
        points = base.mark_point().encode(
            x=alt.X(f"R-squared_{labX}").scale(domain=[0, 1]),
            y=alt.Y(f"R-squared_{labY}").scale(domain=[0, 1]),
            color="type",
            tooltip="column",
        )
        xey = (
            alt.Chart()
            .mark_rule(strokeDash=[2, 2])
            .encode(
                x=alt.value(0),
                y=alt.value("height"),
                x2=alt.value("width"),
                y2=alt.value(0),
            )
        )
        return points + xey

    return (make_compare_model_chart,)


@app.cell
def _(summarize_arbitrary_model, summarize_linear_model, warnings):
    all_models = {}
    all_results = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for key, summary in {
            "planttype": summarize_linear_model(["plant_type"]),
            "netgen": summarize_linear_model(["net_generation_mwh"]),
            "netgen + planttype": summarize_linear_model(
                ["net_generation_mwh", "plant_type"]
            ),
            "netgen X planttype": summarize_arbitrary_model(
                ["net_generation_mwh", "plant_type"], "plant_type * net_generation_mwh"
            ),
            "capacity": summarize_linear_model(["capacity_mw"]),
            "capacity + planttype": summarize_linear_model(
                ["capacity_mw", "plant_type"]
            ),
            "kitchen sink": summarize_linear_model(
                [
                    "net_generation_mwh",
                    "capacity_factor",  # eh
                    "capacity_mw",  # meh
                    "plant_hours_connected_while_generating",  # nah
                    "installation_year",  # probably not
                    "peak_demand_mw",  # eh
                    "construction_year",
                    "avg_num_employees",
                    "plant_type",
                    "report_year",
                ]
            ),
        }.items():
            all_models[key] = summary[0]
            all_results[key] = summary[1]
    return all_models, all_results


@app.cell
def _(all_models, mo):
    model_selector = mo.ui.dropdown(
        options=all_models.keys(), value="netgen", label="Select model:"
    )
    modelX_selector = mo.ui.dropdown(
        options=all_models.keys(), value="planttype", label="Select model for X axis:"
    )
    modelY_selector = mo.ui.dropdown(
        options=all_models.keys(), value="netgen", label="Select model for Y axis:"
    )
    return modelX_selector, modelY_selector, model_selector


@app.cell
def _(mo):
    def display_summarize_results(df):
        return mo.ui.table(
            df.sort_values(by="R-squared", ascending=False).reset_index(drop=True),
            pagination=False,
            selection=None,
        )

    return (display_summarize_results,)


@app.cell
def _(all_models, all_results, display_summarize_results, mo, model_selector):
    selected_model_correlates = list(all_models[model_selector.value].keys())
    model_correlate_selector = mo.ui.dropdown(
        options=selected_model_correlates,
        value=selected_model_correlates[0],
        label="correlate",
    )
    mo.vstack(
        [
            mo.md("### Model results"),
            model_selector,
            display_summarize_results(all_results[model_selector.value]),
        ]
    )
    return (model_correlate_selector,)


@app.cell
def _(all_models, mo, model_correlate_selector, model_selector):
    mo.accordion(
        {
            "Model details": mo.vstack(
                [
                    mo.hstack(
                        [
                            mo.md("Select"),
                            model_correlate_selector,
                        ],
                        justify="start",
                        gap=0.25,
                    ),
                    mo.plain_text(
                        str(
                            all_models[model_selector.value][
                                model_correlate_selector.value
                            ].summary()
                        )
                    ),
                ]
            )
        }
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Observations

    * We have multicollinearity problems: netgen and capacity are our best variable/fixed indicators but they are both too correlated with plant type. We know this because our *condition* number is quite high for all expense columns. To address this we might want to manually split the `plant_type` enum into a set of binary flags, and drop the ones that don't improve predictive power.
    """)


@app.cell
def _(mo, modelX_selector, modelY_selector):
    mo.vstack(
        [
            mo.md("### Model comparisons"),
            modelX_selector,
            modelY_selector,
        ]
    )


@app.cell
def _(
    all_results,
    make_compare_model_chart,
    mo,
    modelX_selector,
    modelY_selector,
):
    mo.stop(
        modelX_selector.value == modelY_selector.value,
        mo.md("X and Y axis model selections must be different.").style(
            background="#FEE"
        ),
    )
    model_comparison_config = {
        modelX_selector.value: all_results[modelX_selector.value],
        modelY_selector.value: all_results[modelY_selector.value],
    }
    make_compare_model_chart(**model_comparison_config)
    return (model_comparison_config,)


@app.cell
def _(mo):
    exclude_subtotals_selector = mo.ui.checkbox(label="Exclude subtotal columns")
    return (exclude_subtotals_selector,)


@app.cell
def _(
    exclude_subtotals_selector,
    merge_two_models,
    model_comparison_config,
    subtotals,
):
    model_comparison_df = merge_two_models(**model_comparison_config)
    if exclude_subtotals_selector.value:
        model_comparison_df = model_comparison_df.loc[
            ~model_comparison_df.column.isin(k for k in subtotals if subtotals[k])
        ]
    # model_comparison_df
    return (model_comparison_df,)


@app.cell
def _(exclude_subtotals_selector, mo):
    mo.vstack(
        [
            mo.md("### Coverage"),
            mo.md(
                "For a particular model, if we categorize all columns with an R-squared value meeting some threshold, how much of the total expenditures are captured?"
            ),
            exclude_subtotals_selector,
        ]
    )


@app.cell
def _(alt, mo, model_comparison_config, model_comparison_df):
    mo.hstack(
        [
            alt.Chart(
                (
                    model_comparison_df.sort_values(by=var, ascending=False)[
                        ["column", var, "total", "type"]
                    ]
                    .set_index(["column", "type"])
                    .assign(
                        cu_total=lambda x: x.groupby("type").total.cumsum(),
                        pct_total=lambda x: (
                            x.cu_total / x.groupby("type").total.sum() * 100
                        ),
                    )
                    .reset_index()
                ),
                title=alt.Title(
                    "Total expenses captured vs fit threshold", subtitle=f"{st} model"
                ),
            )
            .mark_line()
            .encode(
                x=alt.X(var).scale(domain=[0, 1]),
                y=alt.Y("pct_total").scale(domain=[0, 100]),
                color="type",
                tooltip="column",
            )
            for var, st in [
                (f"R-squared_{lab}", lab) for lab in model_comparison_config
            ]
        ]
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # S & L Report Implications

    The [S&L Report](https://www.eia.gov/analysis/studies/powerplants/generationcost/) commissioned by the EIA in 2019 contains useful information on the statistical significance of the impact of (various factors but largely) age on capital expenditures, and to a lesser extent operations & maintenance costs. Unfortunately, most of the identified factors are only significant for specific prime movers, so incorporating them will require aggregating over the EIA-FERC1 plant parts association table.

    * ST, Coal: unit age (capex)
    * ST, Gas/oil: capacity (capex)
    * CC/CA/CS/CT, Gas/oil: cumulative operating hours (capex)
    * GT/CT, Gas/oil: cumulative starts (capex)
    * HY: unit age (capex & o&m)
    * PS: nothing
    * PV: nothing
    * ST, Geothermal: nothing
    * WS/WT: capacity (capex), age (o&m)
    """)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Next steps

    * Learn more about FERC description of each column
    * Reduce multicollinearity
    * Analyze outliers for patterns
    * Dig into opex columns with weird residual patterns
    * Go hunting for additional variables in other PUDL tables
    """)


if __name__ == "__main__":
    app.run()
