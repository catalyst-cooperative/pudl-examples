import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    import marimo as mo

    return mo, pd


@app.cell
def _(pd):
    table = "core_eia861__yearly_energy_efficiency"
    path = (
        f"https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/{table}.parquet"
    )
    df = pd.read_parquet(path)
    return (df,)


@app.cell
def _(df):
    util_id_dict = (
        df[["utility_id_eia", "utility_name_eia"]]
        .drop_duplicates()
        .set_index("utility_name_eia")["utility_id_eia"]
        .to_dict()
    )

    customer_classes = df.customer_class.unique().tolist()
    return customer_classes, util_id_dict


@app.cell
def _(customer_classes, mo, util_id_dict):
    selected_util = mo.ui.dropdown(
        options=util_id_dict,
        value="Austin Energy",  # initial value
        label="choose utility to view",
        searchable=True,
    )

    selected_cust_class = mo.ui.dropdown(
        options=customer_classes,
        value="residential",  # initial value
        label="select customer class",
        searchable=True,
    )
    return selected_cust_class, selected_util


@app.cell
def _(mo, selected_cust_class, selected_util):
    util_select = mo.hstack(
        [selected_util, mo.md(f"Utility ID EIA: {selected_util.value}")]
    )
    cust_select = mo.hstack(
        [selected_cust_class, mo.md(f"Customer Class: {selected_cust_class.value}")]
    )

    mo.vstack([util_select, cust_select])
    return


@app.cell
def _(df, selected_cust_class, selected_util):
    df[
        (df["utility_id_eia"] == selected_util.value)
        & (df["customer_class"] == selected_cust_class.value)
    ]
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
