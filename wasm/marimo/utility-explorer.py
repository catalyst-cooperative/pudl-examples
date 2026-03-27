import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _(mo, selected_state, selected_util):
    mo.output.append(mo.md("# Utility Explorer"))
    mo.output.append(
        mo.md(
            'Explore attributes of any utility that reports to <a href="https://docs.catalyst.coop/pudl/data_sources/eia861.html" target="_blank">EIA-861</a>. Select a state and specific utility to explore its attributes, generation over time and generators.'
        )
    )
    mo.output.append(mo.vstack([selected_state, selected_util]))
    return


@app.cell
def _():
    import pandas as pd
    import marimo as mo
    import plotly.graph_objects as go
    import plotly

    return go, mo, pd, plotly


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


@app.cell
def _(pudl):
    st_df = pudl("out_eia861__yearly_utility_service_territory")
    yu_df = pudl("out_eia__yearly_utilities")
    od_df = pudl("core_eia861__yearly_operational_data_misc")
    s_df = pudl("core_eia861__yearly_sales")
    return od_df, s_df, st_df, yu_df


@app.cell
def _(mo, st_df):
    selected_state = mo.ui.dropdown.from_series(
        st_df.state.drop_duplicates().sort_values(),
        label="Select a state:",
        value="CO",
        searchable=True,
    )

    # Could add a feature that selects no states...
    return (selected_state,)


@app.cell
def _(mo, selected_state, st_df, yu_df):
    in_state_utils = (
        st_df.loc[st_df.state == selected_state.value, "utility_id_eia"]
        .drop_duplicates()
        .to_list()
    )

    in_state_utils_stats = (
        yu_df[yu_df["utility_id_eia"].isin(in_state_utils)][
            ["utility_id_eia", "utility_name_eia"]
        ]
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
    util_counties = st_df[st_df["utility_id_eia"] == selected_util.value]
    max_year = util_counties.report_date.dt.year.max()
    util_counties_year = util_counties[util_counties["report_date"].dt.year == max_year]
    return (util_counties_year,)


@app.cell
def _(selected_util):
    def show_static_value(df, col):
        out_df = (
            df[df["utility_id_eia"] == selected_util.value]
            .sort_values(["report_date"], ascending=False)
            .dropna(subset=[col])
        )

        if out_df.empty:
            value = "Nothing Reported"
            year = "N/A"
        else:
            value = out_df[col].iloc[0]
            year = out_df.report_date.iloc[0].year
        return value, year

    return (show_static_value,)


@app.cell
def _(show_static_value, yu_df):
    address1, year1 = show_static_value(yu_df, "street_address")
    return address1, year1


@app.cell
def _(address1, mo, selected_util, year1):
    # out_df = df_dict["out_eia__yearly_utilities"]
    # util_df = out_df[out_df["utility_id_eia"]==selected_util.value].sort_values(["report_date"], ascending=False)
    # # Selecting the most recent year with data
    # address_df = util_df.dropna(subset=["street_address"])
    # if address_df.empty:
    #     address = "No Address Reported"
    #     year = "N/A"
    # else:
    #     address = address_df.street_address.iloc[0]
    #     year = address_df.report_date.iloc[0].year

    mo.vstack(
        [
            # selected_state,
            # selected_util,
            mo.md(f"Utility ID EIA: {selected_util.value}"),
            mo.md(f"Address: {address1} (last reported in {year1})"),
        ]
    )
    return


@app.cell
def _(mo):
    mo.output.append(mo.md("## Service Territory"))
    return


@app.cell
def _(go, mo, pd, util_counties_year):
    import json
    from urllib.request import urlopen
    import plotly.express as px

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

    _fig = px.choropleth(
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
            _fig.add_trace(
                go.Scattergeo(
                    lon=list(_lons) + [None],
                    lat=list(_lats) + [None],
                    mode="lines",
                    line=dict(color="black", width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    _fig.update_traces(marker_line_color="black", marker_line_width=0.3)
    _fig.update_layout(
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
    mo.ui.plotly(_fig)

    return


@app.cell
def _(od_df, selected_util):
    util_od_df = od_df[od_df["utility_id_eia"] == selected_util.value]
    return (util_od_df,)


@app.cell
def _(mo):
    mo.output.append(mo.md("## Source of Electricity"))  # better name...
    return


@app.cell
def _(go, mo, plotly, selected_util, util_od_df):
    colors = plotly.colors.qualitative.Plotly  # default color cycle

    fig1 = go.Figure()

    value_cols = [
        "net_generation_mwh",
        "wholesale_power_purchases_mwh",
        "net_power_exchanged_mwh",
        "net_wheeled_power_mwh",
        "transmission_by_other_losses_mwh",
    ]
    legend_shown = set()

    for i, col in enumerate(value_cols):
        if (util_od_df[col] == 0).all():
            continue
        color = colors[i % len(colors)]
        neg_vals = util_od_df[col].where(util_od_df[col] < 0, other=None)
        pos_vals = util_od_df[col].where(util_od_df[col] > 0, other=None)

        if pos_vals.notna().any():
            fig1.add_trace(
                go.Scatter(
                    x=util_od_df["report_date"],
                    y=pos_vals,
                    name=col,
                    stackgroup="positive",
                    legendgroup=col,
                    showlegend=col not in legend_shown,
                    line=dict(color=color),
                    fillcolor=color,
                )
            )
            legend_shown.add(col)

        if (
            neg_vals.notna().any()
        ):  # only add negative trace if there are actual negatives
            fig1.add_trace(
                go.Scatter(
                    x=util_od_df["report_date"],
                    y=neg_vals,
                    name=col,
                    stackgroup="negative",
                    legendgroup=col,
                    showlegend=col not in legend_shown,
                    line=dict(color=color),
                    fillcolor=color,
                )
            )
            legend_shown.add(col)

    fig1.update_layout(
        title=f"Sources of Electricity for {selected_util.selected_key}",
        xaxis_title="Date",
        yaxis_title="MWh",
        xaxis=dict(
            dtick="M12",
            tickformat="%Y",
        ),
    )
    mo.ui.plotly(fig1)
    return


@app.cell
def _(go, mo, util_od_df):
    fig2 = go.Figure()

    fig2.add_trace(
        go.Scatter(
            x=util_od_df["report_date"],
            y=util_od_df["summer_peak_demand_mw"],
            mode="lines",
            name="Summer Peak Demand",
            line=dict(color="#e05c2a", width=2),
        )
    )

    fig2.add_trace(
        go.Scatter(
            x=util_od_df["report_date"],
            y=util_od_df["winter_peak_demand_mw"],
            mode="lines",
            name="Winter Peak Demand",
            line=dict(color="#4a90d9", width=2),
        )
    )

    fig2.update_layout(
        title="Summer vs. Winter Peak Demand",
        xaxis_title="Report Date",
        yaxis_title="MW",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    mo.ui.plotly(fig2)
    return


@app.cell
def _(go, mo, s_df, selected_util):
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

    COLORS = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
    ]

    customer_classes = [c for c in pivot.columns if c != "report_date"]

    traces = []
    for ii, cc in enumerate(customer_classes):
        traces.append(
            go.Scatter(
                x=pivot["report_date"],
                y=pivot[cc],
                name=cc,
                mode="lines",
                stackgroup="one",
                line=dict(width=0.5, color=COLORS[ii % len(COLORS)]),
                fillcolor=COLORS[ii % len(COLORS)],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Sales: %{y:,.0f} MWh<extra></extra>"
                ),
            )
        )

    fig = go.Figure(traces)
    fig.update_layout(
        title=dict(text="Electricity Sales by Customer Class", font_size=18),
        xaxis=dict(title="Report Date", showgrid=True, gridcolor="#e0e0e0"),
        yaxis=dict(
            title="Sales (MWh)", showgrid=True, gridcolor="#e0e0e0", tickformat=",.0f"
        ),
        legend=dict(
            title="Customer Class",
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
        ),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=80, b=60, l=80, r=160),
    )

    mo.ui.plotly(fig)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
