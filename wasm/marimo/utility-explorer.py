import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    import marimo as mo

    return mo, pd


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
    return od_df, st_df, yu_df


@app.cell
def _():
    # util_id_dict = (
    #     pudl("core_eia__entity_utilities")
    #     .drop_duplicates()
    #     .dropna()
    #     .sort_values("utility_name_eia")
    #     .set_index("utility_name_eia")["utility_id_eia"]
    #     .to_dict()
    # )
    return


@app.cell
def _(mo, st_df):
    selected_state = mo.ui.dropdown.from_series(
        st_df.state.drop_duplicates().sort_values(),
        label="Select a state:",
        value="CO",
        searchable=True,
    )
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
    )
    return (selected_util,)


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
def _(address1, mo, selected_state, selected_util, year1):
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
            selected_state,
            selected_util,
            mo.md(f"Utility ID EIA: {selected_util.value}"),
            mo.md(f"Address: {address1} (last reported in {year1})"),
        ]
    )
    return


@app.cell
def _(od_df, selected_util):
    util_od_df = od_df[od_df["utility_id_eia"] == selected_util.value]
    return (util_od_df,)


@app.cell
def _(mo, selected_util, util_od_df):
    import plotly.graph_objects as go
    import plotly

    colors = plotly.colors.qualitative.Plotly  # default color cycle

    fig = go.Figure()

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
            fig.add_trace(
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
            fig.add_trace(
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

    fig.update_layout(
        title=f"Power Profile for {selected_util.selected_key}",
        xaxis_title="Date",
        yaxis_title="MWh",
        xaxis=dict(
            dtick="M12",
            tickformat="%Y",
        ),
    )
    mo.ui.plotly(fig)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
