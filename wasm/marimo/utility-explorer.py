import marimo

__generated_with = "0.23.5"
app = marimo.App(width="medium")


@app.cell
def _():
    # Imports
    import pandas as pd
    import marimo as mo
    import plotly.graph_objects as go
    import plotly
    import altair as alt
    import json
    from urllib.request import urlopen
    import plotly.express as px

    return alt, go, json, mo, pd, px, urlopen


@app.cell
def _(mo, selected_state_full, selected_util):
    mo.output.append(mo.md("# Utility Explorer"))
    mo.output.append(
        mo.md(
            'Explore attributes of any utility that reports to <a href="https://docs.catalyst.coop/pudl/data_sources/eia861.html" target="_blank">EIA-861</a>. Select a state and specific utility to explore its attributes, generation over time and generators.'
        )
    )
    mo.output.append(mo.vstack([selected_state_full, selected_util]))
    return


@app.function
# Preview tables
def table_preview_href(name):
    return f"""<a href="https://data.catalyst.coop/preview/pudl/{name}" target="_blank">{name}</a>"""


@app.cell
def _(pd):
    # Retreive tables func
    def path(name):
        return (
            f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{name}.parquet"
        )

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
    s_df = pudl("core_eia861__yearly_sales")
    gen_df = pudl("out_eia__yearly_generators")
    gen_fuel_df = pudl("out_eia923__generation_fuel_combined")
    return gen_df, gen_fuel_df, od_df, s_df, st_df, yu_df


@app.cell
def _(mo, st_df):
    # State selection
    selected_state = mo.ui.dropdown.from_series(
        st_df.state.drop_duplicates().sort_values(),
        label="Select a state:",
        value="CO",
        searchable=True,
        allow_select_none=True,
    )


    selected_state_full = mo.hstack([
        mo.md(f"""<div data-tooltip="Some utilities operate in multiple states. Use the state selector to help narrow down your utility search, but know that utility information from multiple states will show where applicable.">{mo.icon("lucide:info")}</div>"""),
        selected_state
    ], justify="start",)
    return selected_state, selected_state_full


@app.cell
def _(mo, selected_state, st_df, yu_df):
    # Utility selection
    in_state_utils_stats = (
        (
            yu_df[yu_df["utility_id_eia"].isin(
                st_df.loc[st_df.state == selected_state.value, "utility_id_eia"]
                .drop_duplicates()
                .to_list()
            )]
            if selected_state.value
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
    # County selection
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
            value_list = out_df[out_df["report_date"]==recent_report_date][col].unique().tolist()
            value = ", ".join(str(x) for x in value_list)
            year = recent_report_date.year
        return value, year

    return (show_static_value,)


@app.cell
def _(show_static_value, st_df, yu_df):
    # Grab utility stats
    address, address_year = show_static_value(yu_df, "street_address")
    states, states_year = show_static_value(st_df, "state")

    # Grab capacity stats

    return address, address_year, states, states_year


@app.cell
def _():
    return


@app.cell
def _(
    address,
    address_year,
    mo,
    num_plants_owned,
    pd,
    selected_util,
    st_fig,
    states,
    states_year,
    total_cap,
):
    stats_table = mo.ui.table(
        pd.DataFrame([
            {
                "Value": str(selected_util.value),
                "Last Reported": "",
                "Reference Table": "",
            },
            {
                "Value": address,
                "Last Reported": str(address_year),
                "Reference Table": mo.md(table_preview_href('out_eia__yearly_utilities')),
            },
            {
                "Value": states,
                "Last Reported": str(states_year),
                "Reference Table": mo.md(table_preview_href('out_eia861__yearly_utility_service_territory')),
            },
            {
                "Value": num_plants_owned,
                "Last Reported": "",
                "Reference Table": mo.md(table_preview_href('out_eia__yearly_generators')),
            },
            {
                "Value": round(total_cap),
                "Last Reported": "",
                "Reference Table": mo.md(table_preview_href('out_eia__yearly_generators')),
            },
        ], index=["Utility ID EIA", "Address", "States", "Total Plants Owned", "Total Owned Capacity (MW)"])
    )

    util_stats = (
        mo.vstack([
            mo.md("## Basic Information"),
            mo.hstack([
                mo.vstack([
                    mo.md("### Utility Stats"),
                    mo.Html(f'<div style="width: 600px">{stats_table.text}</div>'),
                ]),
                mo.vstack([
                    mo.md("### Service Territory"),
                    mo.ui.plotly(st_fig.update_layout(width=500, height=300)),
                ]),
            ], justify="space-between"),
        ])
    )
    return (util_stats,)


@app.cell
def _(util_stats):
    util_stats
    return


@app.cell
def _(gen_df, selected_util):
    util_gen = gen_df[gen_df["utility_id_eia"]==selected_util.value].sort_values("report_date", ascending=False)

    recent_report_date = util_gen["report_date"].iloc[0]

    util_gen_existing = (
        util_gen[
            (util_gen["report_date"]==recent_report_date) 
            & (util_gen["operational_status"]=="existing")
        ]
    )

    # For util stats table
    num_plants_owned = len(util_gen_existing.plant_id_eia.unique())
    total_cap = util_gen_existing.capacity_mw.sum()

    recent_util_gen = util_gen[
        (util_gen["report_date"]==recent_report_date)
    ]

    def agg_plant_values(df, op_status):

        df = df[df["operational_status"]== op_status]
    
        plant_cols = [
            "generator_id", # aggregate into list
            "plant_name_eia", # choose first
            "technology_description", # aggregate into list
            "fuel_type_code_pudl", # list
            "capacity_mw", # sum
            "city", # list
        ]
    
        util_plant_df = df.groupby(["report_date", "plant_id_eia"])[plant_cols].agg({
            "generator_id": lambda x: ", ".join(v for v in x.unique() if v is not None),
            "plant_name_eia": "first",
            "technology_description": lambda x: ", ".join(v for v in x.unique() if v is not None),
            "fuel_type_code_pudl": lambda x: ", ".join(v for v in x.unique() if v is not None),
            "capacity_mw": lambda x: f"{x.sum():.2f}",
            "city": lambda x: ", ".join(v for v in x.unique() if v is not None)
        }).reset_index()
    
        util_plant_df["report_year"] = util_plant_df["report_date"].dt.year.astype("str")
        util_plant_df = util_plant_df.drop(columns=["report_date"])
        return util_plant_df

    return (
        agg_plant_values,
        num_plants_owned,
        recent_report_date,
        recent_util_gen,
        total_cap,
    )


@app.cell
def _(mo):
    # Create drop down for selecting which plant table to show
    selected_status = mo.ui.dropdown(
        options=["existing", "proposed", "retired"],
        value="existing",
        label="Select generator status:",
    )
    #selected_status
    return (selected_status,)


@app.cell
def _(
    agg_plant_values,
    fuel_chart,
    mo,
    recent_report_date,
    recent_util_gen,
    selected_status,
    selected_year,
):
    # Display selected plant table
    status_df = agg_plant_values(recent_util_gen, selected_status.value)

    owned_gen = (
        mo.vstack([
            mo.md("## Owned Generation"),
            mo.hstack([
                mo.vstack([
                    mo.md(f"### Plant Profiles From Most Recent Year: {recent_report_date.year}"),
                    selected_status,
                    mo.Html(f'<div style="max-width: 500px">{mo.ui.table(status_df).text if not status_df.empty else ""}</div>'),
                    mo.md(f"via {table_preview_href('out_eia__yearly_generators')}")
                ]),
                mo.vstack([
                    mo.md("### Generation by Fuel Type"),
                    selected_year,
                    mo.ui.altair_chart(fuel_chart.properties(width=350, height=250)),
                    mo.md(f"via {table_preview_href('out_eia923__generation_fuel_combined')}")
                ]),
            ]),
        ])
    )
    owned_gen
    return


@app.cell
def _(gen_fuel_df, mo, selected_util):
    util_gen_fuel = gen_fuel_df[gen_fuel_df["utility_id_eia"]==selected_util.value]

    available_years = sorted(util_gen_fuel["report_date"].dt.year.unique(), reverse=True)

    selected_year = mo.ui.dropdown(
        options=[str(y) for y in available_years],
        value=str(available_years[0]),
        label="Select year:",
    )
    return selected_year, util_gen_fuel


@app.cell
def _(alt, selected_year, util_gen_fuel):
    year_df = util_gen_fuel[util_gen_fuel["report_date"].dt.year == int(selected_year.value)]

    fuel_long = year_df.groupby(["report_date", "fuel_type_code_pudl"])["net_generation_mwh"].sum().reset_index()

    fuel_chart = alt.Chart(fuel_long).mark_area().encode(
        x=alt.X("report_date:T", axis=alt.Axis(format="%b", tickCount="month"), title="Month"),
        y=alt.Y("net_generation_mwh:Q", stack="zero", title="Net Generation (MWh)", axis=alt.Axis(format=",.0f")),
        color=alt.Color(
            "fuel_type_code_pudl:N",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(title="Fuel Type"),
        ),
        tooltip=[
            alt.Tooltip("report_date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("fuel_type_code_pudl:N", title="Fuel Type"),
            alt.Tooltip("net_generation_mwh:Q", title="Net Generation (MWh)", format=",.0f"),
        ],
    ).properties(
        width=700,
        height=400,
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
def _(mo):
    mo.output.append(mo.md("## Source of Electricity"))  # better name...
    return


@app.cell
def _(alt, mo, selected_util, util_od_df):
    # Define value cols
    value_cols = [
        "net_generation_mwh",
        "wholesale_power_purchases_mwh",
        "net_power_exchanged_mwh",
        "net_wheeled_power_mwh",
        "transmission_by_other_losses_mwh",
    ]

    # Melt to long format for Altair
    od_long = util_od_df[["report_date"] + value_cols].melt(
        id_vars="report_date",
        value_vars=value_cols,
        var_name="source",
        value_name="mwh",
    )

    # Remove all-zero columns
    nonzero_sources = [
        col for col in value_cols if not (util_od_df[col] == 0).all()
    ]
    od_long = od_long[od_long["source"].isin(nonzero_sources)]

    # Split into positive and negative
    od_pos = od_long[od_long["mwh"] > 0]
    od_neg = od_long[od_long["mwh"] < 0]

    base = alt.Chart().encode(
        x=alt.X("report_date:T", axis=alt.Axis(format="%Y", tickCount="year"), title="Date"),
        color=alt.Color("source:N", scale=alt.Scale(scheme="tableau10")),
    )

    pos_chart = base.mark_area().encode(
        y=alt.Y("sum(mwh):Q", stack="zero", title="MWh"),
    ).properties(data=od_pos)

    neg_chart = base.mark_area().encode(
        y=alt.Y("sum(mwh):Q", stack="zero"),
    ).properties(data=od_neg)

    chart = alt.layer(pos_chart, neg_chart).properties(
        title=f"Sources of Electricity for {selected_util.selected_key}",
        width=700,
        height=400,
    )

    mo.ui.altair_chart(chart)
    return


@app.cell
def _(alt, mo, util_od_df):
    peak_long = util_od_df[["report_date", "summer_peak_demand_mw", "winter_peak_demand_mw"]].melt(
        id_vars="report_date",
        var_name="season",
        value_name="mw",
    )

    chart2 = alt.Chart(peak_long).mark_line(strokeWidth=2).encode(
        x=alt.X("report_date:T", axis=alt.Axis(format="%Y", tickCount="year"), title="Report Date"),
        y=alt.Y("mw:Q", title="MW"),
        color=alt.Color(
            "season:N",
            scale=alt.Scale(
                domain=["summer_peak_demand_mw", "winter_peak_demand_mw"],
                range=["#e05c2a", "#4a90d9"],
            ),
            legend=alt.Legend(orient="top-right"),
        ),
        tooltip=["report_date:T", "season:N", "mw:Q"],
    ).properties(
        title="Summer vs. Winter Peak Demand",
        width=700,
        height=400,
    )

    mo.ui.altair_chart(chart2)
    return


@app.cell
def _(alt, mo, s_df, selected_util):
    s_df_util = s_df[s_df["utility_id_eia"] == selected_util.value]
    pivot = (
        s_df_util.pivot_table(
            index="report_date",
            columns="customer_class",
            values="sales_mwh",
            aggfunc="sum",
        )
        .sort_index()
        .reset_index()
    )
    customer_classes = [c for c in pivot.columns if c != "report_date"]

    sales_long = pivot.melt(
        id_vars="report_date",
        value_vars=customer_classes,
        var_name="customer_class",
        value_name="sales_mwh",
    )

    chart3 = alt.Chart(sales_long).mark_area().encode(
        x=alt.X("report_date:T", axis=alt.Axis(format="%Y", tickCount="year"), title="Report Date"),
        y=alt.Y("sales_mwh:Q", stack="zero", title="Sales (MWh)", axis=alt.Axis(format=",.0f")),
        color=alt.Color(
            "customer_class:N",
            scale=alt.Scale(scheme="tableau10"),
            legend=alt.Legend(title="Customer Class", orient="right"),
        ),
        order=alt.Order("customer_class:N"),
        tooltip=[
            alt.Tooltip("report_date:T", title="Date", format="%Y-%m-%d"),
            alt.Tooltip("customer_class:N", title="Customer Class"),
            alt.Tooltip("sales_mwh:Q", title="Sales (MWh)", format=",.0f"),
        ],
    ).properties(
        title=alt.TitleParams("Electricity Sales by Customer Class", fontSize=18),
        width=700,
        height=400,
    )

    mo.ui.altair_chart(chart3)
    return


@app.cell
def _():
    # 
    return


if __name__ == "__main__":
    app.run()
