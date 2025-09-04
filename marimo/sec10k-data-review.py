# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "matplotlib==3.10.6",
#     "matplotx==0.3.10",
#     "polars==1.32.3",
# ]
# ///

import marimo

__generated_with = "0.15.2"
app = marimo.App(width="columns", app_title="SEC 10-K Data Review")


@app.cell(column=0)
def _():
    import os
    from pathlib import Path

    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import matplotx
    import polars as pl

    import marimo as mo

    pl.Config.set_tbl_rows(500)
    pl.Config.set_tbl_cols(100)
    pl.Config.set_fmt_str_lengths(100)

    mpl.rcParams["figure.figsize"] = (10, 5)
    mpl.rcParams["figure.dpi"] = 150
    mpl.style.use(matplotx.styles.onedark)
    return Path, mo, os, pl, plt


@app.cell
def _(Path, os, pl):
    def get_pudl(table_name: str) -> pl.DataFrame:
        """Read a PUDL table from local storage if possible, and S3 nightlies if not.

        Args:
            table_name: The name of the table to read (without the .parquet extension).

        Returns:
            The requested PUDL table as a Polars DataFrame.
        """
        pudl_output = os.environ.get("PUDL_OUTPUT", False)
        local_parquet_path = (
            Path(pudl_output) / f"parquet/{table_name}.parquet" if pudl_output else None
        )
        s3_parquet_url = f"s3://pudl.catalyst.coop/nightly/{table_name}.parquet"

        if (local_parquet_path is not None) and (local_parquet_path.exists()):
            return pl.read_parquet(local_parquet_path)
        return pl.read_parquet(s3_parquet_url)

    return (get_pudl,)


@app.cell
def _(pl):
    def clean_industry_data(df: pl.DataFrame) -> pl.DataFrame:
        # Step 1: Clean industry_name_sic
        # Find the most common name for each industry_id_sic
        canonical_names = (
            df.filter(pl.col("industry_name_sic").is_not_null())
            .group_by("industry_id_sic")
            .agg(common_name=pl.col("industry_name_sic").mode())
        )

        # Identify the most common name and ensure it's unique per ID
        unique_canonical_names = (
            canonical_names.group_by("industry_id_sic")
            .agg(count=pl.count())
            .filter(pl.col("count") == 1)
        )

        # Create a mapping dictionary
        name_mapping = {
            row["industry_id_sic"]: row["common_name"]
            for row in unique_canonical_names.rows()
        }

        # Fill in canonical names where applicable
        df = df.with_columns(
            pl.when(pl.col("industry_name_sic").is_null())
            .then(pl.col("industry_id_sic").map(name_mapping))
            .otherwise(pl.col("industry_name_sic"))
            .alias("cleaned_industry_name_sic")
        )

        # Step 2: Fill in industry_id_sic using cleaned names
        df = df.with_columns(
            pl.when(
                pl.col("industry_id_sic").is_null()
                & pl.col("cleaned_industry_name_sic").is_not_null()
            )
            .then(pl.col("cleaned_industry_name_sic").map(name_mapping))
            .otherwise(pl.col("industry_id_sic"))
            .alias("cleaned_industry_id_sic")
        )

        # Step 3: Handle nulls based on central_index_key and consistency before and after
        def fill_nulls(group: pl.DataFrame) -> pl.DataFrame:
            # Sort by report_date
            group = group.sort("report_date")

            # Forward fill for missing IDs and names
            group = group.with_columns(
                ffill_id=pl.col("industry_id_sic").fill_null(strategy="forward"),
                ffill_name=pl.col("industry_name_sic").fill_null(strategy="forward"),
            )

            # Backward fill for missing IDs and names
            return group.with_columns(
                pl.col("ffill_id").fill_null(strategy="backward"),
                pl.col("ffill_name").fill_null(strategy="backward"),
            )

        return df.groupby("central_index_key").agg(fill_nulls(pl.all()))

    return


@app.cell(column=1, hide_code=True)
def _(mo):
    mo.md(
        r"""
    # What fraction of electricity companies are linked to EIA utilities?

    ## Identify industry IDs with lots of Utility ID associations

    - This is kind of begging the question, but it's not a terrible way to find interesting SICs to look at.
    - Unsurprisingly the two top SICs with the largest number of Utility ID associations are electric services, and electric & other services combined (many seem to be combined electric & gas utilities)
    - There's also a number of "real estate" oriented industries. Maybe they have big behind-the-meter C&I solar installations?
    - There are also a number of industries that typically engage in cogeneration, especially papermills, oil & gas, natural gas transmission companies, etc.
    - Filtering all the industry names for "electric" and "power" shows a bunch of other industries that are not related to electricity generation. Mostly electronics, etc.
    - So the 4911 and 4931 seem to be the main ones we expect to link to EIA Utilities.
    - And then there's a number of smaller industries with cogeneration that often match, but don't have as many companies in them, and probably aren't responsible for much generation.
    - Note: this kind of analysis would be easier if we cleaned up the SIC names & IDs so that they're more consistent & complete.
    """
    )
    return


@app.cell
def _(get_pudl):
    companies = get_pudl("out_sec10k__quarterly_company_information")
    return (companies,)


@app.cell
def _(companies, pl):
    (
        companies.filter(pl.col("utility_id_eia").is_not_null())
        .select(["industry_id_sic", "industry_name_sic"])
        .group_by(["industry_id_sic", "industry_name_sic"])
        .agg(count=pl.len())
        .sort("count", descending=True)
        .head(20)
    )
    return


@app.cell
def _(companies, pl):
    electricity_sics = (
        companies.group_by(sic=pl.col("industry_id_sic"))
        .agg(fraction_with_utility_id=pl.col("utility_id_eia").is_not_null().mean())
        .sort("fraction_with_utility_id", descending=True)
        .head(20)
    )
    electricity_sics
    return (electricity_sics,)


@app.cell
def _(companies, electricity_sics, pl):
    majority_electric = (
        electricity_sics.filter(pl.col("fraction_with_utility_id") > 0.5)
        .select("sic")
        .to_series()
        .to_list()
    )
    (
        companies.filter(pl.col("industry_id_sic").is_in(majority_electric))
        .select(["industry_id_sic", "industry_name_sic"])
        .group_by(["industry_id_sic", "industry_name_sic"])
        .agg(count=pl.len())
        .sort("count", descending=True)
    )
    return (majority_electric,)


@app.cell
def _(companies, majority_electric, pl, plt):
    util_ids_by_year = (
        companies.filter(
            pl.col("industry_id_sic").is_in(majority_electric),
        )
        .with_columns(year=pl.col("report_date").dt.year())
        .group_by(["year", "industry_id_sic"])
        .agg(
            fraction_with_utility_id=pl.col("utility_id_eia").is_not_null().mean(),
        )
        .sort("year")
    )

    for sic in util_ids_by_year["industry_id_sic"].unique():
        df = util_ids_by_year.filter(pl.col("industry_id_sic") == sic)
        plt.plot(df["year"], df["fraction_with_utility_id"], label=sic)

    plt.legend()
    return


@app.cell
def _(companies, pl):
    unmatched_companies = (
        companies.filter(
            pl.col("industry_id_sic").is_in(["4911", "4931"]),
            pl.col("utility_id_eia").is_null(),
        )
        .select(["central_index_key", "company_name", "report_date"])
        .unique(["central_index_key", "company_name", "report_date"])
    )
    unmatched_companies.sample(25).sort("report_date")
    return (unmatched_companies,)


@app.cell
def _(mo):
    mo.md(
        r"""
    ## How does matching to EIA vary by year?

    * The SEC data goes back further than the EIA data, so we'd probably expect the older years to have more unmatched companies.
    * This does generally seem to be the case, with ~2x as many unmatched companies in the early 2000s compared to more recent years.
    """
    )
    return


@app.cell
def _(pl, plt, unmatched_companies):
    unmatched_by_year = (
        unmatched_companies.group_by(pl.col("report_date").dt.year())
        .agg(count=pl.len())
        .sort("report_date")
    )
    plt.bar(unmatched_by_year["report_date"], unmatched_by_year["count"])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    # SEC 10-K Filer to Subsidiary matches

    * How successful are we at matching subsidiary companies to a corresponding SEC 10-K filer?
    * Does this vary over time?

    ## Number of parent-subsidiary relations per year
    * Roughly linear increase up until 2017.
    * Gap due to failed extraction of Q1 Ex21 data for 2018-2022.
    * Interestingly 2023 is about the same as 2015-2017 so did the linear trend in the increase in number of subsidiaries end?
    """
    )
    return


@app.cell
def _(get_pudl):
    parsubs = get_pudl("out_sec10k__parents_and_subsidiaries")
    return (parsubs,)


@app.cell
def _(parsubs, pl, plt):
    parsubs_by_year = (
        parsubs.select(
            pl.col(
                "report_date",
                "parent_company_central_index_key",
                "parent_company_utility_id_eia",
                "parent_company_name",
                "subsidiary_company_id_sec10k",
                "subsidiary_company_central_index_key",
                "subsidiary_company_utility_id_eia",
                "subsidiary_company_name",
                "fraction_owned",
            )
        )
        .group_by(report_year=pl.col("report_date").dt.year())
        .agg(count=pl.len())
        .sort("report_year")
    )
    plt.bar(parsubs_by_year["report_year"], parsubs_by_year["count"])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Subsidiary to Filer match rate over time
    * Has the proportion of subsidiary companies matched to some SEC 10-K filer changed over time?
    * This is entirely within the SEC 10-K dataset, so the change in EIA data availability should have no impact.
    * The match rate is quite low across the board. Only 1-4% of all subsidiaries can be matched to an SEC filer.
    * Since 2012, the rate has been more stable, but low, around 1%.
    """
    )
    return


@app.cell
def _(parsubs, pl, plt):
    sub_match_rate_by_year = parsubs.group_by(
        report_year=pl.col("report_date").dt.year()
    ).agg(
        sub_match_rate=pl.col("subsidiary_company_central_index_key")
        .is_not_null()
        .mean(),
    )
    plt.bar(
        sub_match_rate_by_year["report_year"], sub_match_rate_by_year["sub_match_rate"]
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Match rates for electricity companies
    * Maybe the match rate is different for the electricity oriented companies?
    * Since only companies of a certain size have to report, industries with a larger minimum company size seem like they might have higher match rates.
    * This seems to be the case, with match rates between 4-10%.
    * However, we get no matches for electricity companies in the 2018-2022 gap.
    """
    )
    return


@app.cell
def _(parsubs, pl, plt):
    electrosub_match_rate_by_year = (
        parsubs.filter(pl.col("parent_company_industry_id_sic").is_in(["4911", "4931"]))
        .group_by(report_year=pl.col("report_date").dt.year())
        .agg(
            electrosub_match_rate=pl.col("subsidiary_company_central_index_key")
            .is_not_null()
            .mean(),
        )
    )
    plt.bar(
        electrosub_match_rate_by_year["report_year"],
        electrosub_match_rate_by_year["electrosub_match_rate"],
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## How do subsidiary matches evolve over time?

    * To get a qualitative sense of how matches change over time, let's look at a familiar parent company with known subsidiaries, Xcel Energy.
    * Here we look at a sample of years (2001, 2012, 2023) across the range of available years.
    * Across these years there are 5 distinct subsidiaries that have gotten SICs over the years.
    * In 2001 NRG Energy is a subsidiary of Xcel, but [it is later sold off](https://en.wikipedia.org/wiki/NRG_Energy).
    * Public Service Company of Colorado (PSCo) and Southwestern Public Service Company (New Mexico) are successfully captured across the whole sample.
    * The two other upper-midwest subsidiaries (North States Power MN and WI) are captured in the latter years, but are captured with a differen string in 2001 and so get missed.
    * So we know the subsidiary company IDs can change over time, even within the reporting of a single parent company, and that this affects the intra-SEC matching.
    * This is in addition to the subsidary IDs necessarily varying between parent companies, since the ID incorporates the parent's CIK as part of the ID.
    * There also seem to be dozens of other Xcel subsidiaries that we've never heard of that never get a CIK. Searching for "xcel" in the company information table they don't show up, so it seems likely they truly aren't filers.
    * Interestingly, there is only one Xcel subsidiary that ever shows up here with a Utility ID EIA, and it's not any of the ones that get CIKs.
    * None of the subsidiaries have any ownership fraction reported. I think Xcel completely owns PSCo and SWPS, so I wonder how often NA really means 1.0?
    """
    )
    return


@app.cell
def _(parsubs, pl):
    (
        parsubs.select(
            pl.col(
                "report_date",
                "parent_company_central_index_key",
                "parent_company_utility_id_eia",
                "parent_company_name",
                "subsidiary_company_id_sec10k",
                "subsidiary_company_central_index_key",
                "subsidiary_company_utility_id_eia",
                "subsidiary_company_name",
                "fraction_owned",
            )
        )
        .filter(
            pl.col("report_date").dt.year().is_in([2001, 2012, 2023]),
            pl.col("parent_company_central_index_key").eq("0000072903"),
        )
        .sort("report_date")
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Other Xcel subsidiaries?
    * The other baby Xcels really don't seem to show up as filers.
    """
    )
    return


@app.cell
def _(companies, pl):
    companies.filter(pl.col("company_name").str.contains("^[xX]cel"))[
        "company_name"
    ].unique()
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Nested inside a non-utility
    * Another kind of example: utility companies that are hidden inside a non-utility.
    * Berkshire Hathaway is a sprawling conglomerate that owns a bunch of different kinds of companies, including utility companies like PacifiCorp.
    * The ur-parent is Berkshire Hathaway Inc, and it has an energy focused subsidiary Berkshire Hathaway Energy, which itself reports having a bunch of energy subsidiaries.
    * Most (all?) energy subsidiaries seem to appear in the Ex21 data for both Berkshire Hathaway and Berkshire Hathaway Energy.
    * Midamerican Energy Co shows up in both, and is assigned the same CIK in both, has the same name in both, but only gets an EIA Utility ID in association with BHE, which seems surprising.
    """
    )
    return


@app.cell
def _(parsubs, pl):
    (
        parsubs.select(
            pl.col(
                "report_date",
                "parent_company_central_index_key",
                "parent_company_utility_id_eia",
                "parent_company_name",
                "subsidiary_company_id_sec10k",
                "subsidiary_company_central_index_key",
                "subsidiary_company_utility_id_eia",
                "subsidiary_company_name",
                "fraction_owned",
            )
        )
        .filter(
            pl.col("report_date").dt.year().is_in([2023]),
            pl.col("parent_company_name").str.contains("berkshire.*hathaway"),
        )
        .sort("report_date")
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## More subsidiaries over time
    * Just looking at subsidiaries of BH/BHE that seem to be associated with NV Energy, which sometimes shows up as nevada power company aand sometimes sierra pacific power company.
    * "nevada power company" and "sierra pacific power company" both have EIA utility IDs in 2023, but no previous year.
    * All the "d/b/a nv energy" subsidiary name records fail to get associated with a CIK.
    * The d/b/a records all seem to be associated with BHE, and the same subsidiaries are reported under Berkshire Hathaway as well.
    * This is a concrete example of the same subsidiary having different "names" under different parent companies, even when they're both under the same bigger parent company.
    * In the most recent year of data nevada power and sierra pacific stop using the "d/b/a" naming, creating a discontinuity in the naming across time as well as between reporting parent companies.
    """
    )
    return


@app.cell
def _(parsubs, pl):
    (
        parsubs.select(
            pl.col(
                "report_date",
                "parent_company_central_index_key",
                "parent_company_utility_id_eia",
                "parent_company_name",
                "subsidiary_company_id_sec10k",
                "subsidiary_company_central_index_key",
                "subsidiary_company_utility_id_eia",
                "subsidiary_company_name",
                "fraction_owned",
            )
        )
        .filter(
            pl.col("parent_company_name").str.contains("berkshire.*hathaway"),
            pl.col("subsidiary_company_name").str.contains("(nv |nevada|sierra)"),
        )
        .sort("report_date")
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## How common are (electricity) subsidiaries with utility IDs?
    * Above we've seen a couple of examples where a subisidiary with the same name & location across multiple years doesn't always get assigned an EIA Utility ID.
    * In this small sample it seems like utility IDs are more commonly assigned in the most recent year. What does that distribution look like?
    * The fraction of subsidiary companies that have utility IDs seems to increase linearly over time, from just a couple of percent to nearly 20%.
    * This is on top of the absolute **number** of subsidiaries increasing linearly over time.
    """
    )
    return


@app.cell
def _(parsubs, pl, plt):
    electrosub_has_utility_id = (
        parsubs.filter(
            pl.col("parent_company_industry_id_sic").is_in(["4911", "4931"])
            | pl.col("subsidiary_company_industry_id_sic").is_in(["4911", "4931"])
        )
        .group_by(year=pl.col("report_date").dt.year())
        .agg(
            has_utility_id_eia=pl.col("subsidiary_company_utility_id_eia")
            .is_not_null()
            .mean()
        )
        .sort("year")
    )
    plt.bar(
        electrosub_has_utility_id["year"],
        electrosub_has_utility_id["has_utility_id_eia"],
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
