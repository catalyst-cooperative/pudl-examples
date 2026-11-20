import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Parent-Subsidiary Relationships

    The dynamics of corporate ownership forms a web of relationships that can often skew behavior in unexpected ways.

    Using parent-subsidiary relationships PUDL extracted from the SEC 10-K, you can use this dashboard to make those networks visible, and perhaps make better sense of why a company you're interested in behaves the way it does.

    Locate a parent company directly using the [SEC CIK lookup tool](https://www.sec.gov/search-filings/cik-lookup), or search by utility name below. Then configure settings to display the relationship graph rooted at the company you selected. Beware! Parent-subsidiary relationship graphs can be very irregular, with cycles, self-edges, redundant edges, and duplicate entries, so you might have to fiddle with the settings to get something sensible.
    """)
    return


@app.cell
def _():
    import marimo as mo

    with mo.status.progress_bar(
        total=1, title="Loading subroutines", remove_on_exit=True
    ) as do_imports:
        from collections import defaultdict

        import fastparquet as fp
        import pandas as pd
        import re

        do_imports.update(subtitle="Done!")
    return defaultdict, mo, pd, re


@app.cell
def _(mo, pd):
    with mo.status.progress_bar(
        total=1, title="Fetching parent-subsidiary data", remove_on_exit=True
    ) as do_read_parquet:
        out_sec10k__parents_and_subsidiaries = pd.read_parquet(
            "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/out_sec10k__parents_and_subsidiaries.parquet",
            engine="fastparquet",
            columns=[
                "parent_company_name",
                "parent_company_incorporation_state",
                "parent_company_central_index_key",
                "parent_company_utility_id_eia",
                "parent_company_utility_name_eia",
                "subsidiary_company_central_index_key",
                "subsidiary_company_id_sec10k",
                "report_date",
            ],
        )
        do_read_parquet.update(subtitle="Done!")
    return (out_sec10k__parents_and_subsidiaries,)


@app.cell
def _(Options, mo):
    query_params = mo.query_params()

    def initialize_default_params():
        if "cik" not in query_params:
            query_params["cik"] = "0000936340"
        if "year" not in query_params or int(query_params["year"]) not in set(
            Options.available_years(query_params["cik"])
        ):
            query_params["year"] = str(
                Options.available_years(query_params["cik"]).max()
            )

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
def _(mo, out_sec10k__parents_and_subsidiaries, pd):
    class Options:
        @classmethod
        @mo.cache
        def available_years(cls, cik: str) -> pd.Series:
            return (
                out_sec10k__parents_and_subsidiaries.loc[
                    out_sec10k__parents_and_subsidiaries.parent_company_central_index_key
                    == cik
                ]
                .report_date.dropna()
                .dt.year.drop_duplicates()
                .sort_values(ascending=False)
            )

    return (Options,)


@app.cell
def _(Options, mo, query_params, reset_params):
    from pydantic import BaseModel, computed_field
    from functools import cached_property

    class Selection(BaseModel):
        cik: str
        year: int

        @computed_field
        @cached_property
        def enter_cik(self) -> mo.ui.text:
            return mo.ui.text(
                self.cik,
                label="Parent company CIK",
                on_change=lambda value: reset_params(cik=value),
            )

        @computed_field
        @cached_property
        def enter_year(self) -> mo.ui.dropdown:
            return mo.ui.dropdown(
                options={str(i): i for i in Options.available_years(self.cik)},
                label="Filing year for parent-subsidiary relationships",
                value=str(self.year),
                on_change=lambda value: reset_params(year=str(value)),
            )

    selection = Selection(**query_params.to_dict())
    return (selection,)


@app.cell
def _(defaultdict, out_sec10k__parents_and_subsidiaries, pd, re):
    PUNCT = re.compile("[^a-z0-9]+")
    SPACE = re.compile("_? +_?")

    def clean(text):
        return SPACE.sub("_", PUNCT.sub("_", text))

    def make_tree(root_cik, report_year):
        nodes = {}
        edges = defaultdict(list)
        unclean = {}

        def traverse(cik, name, level=0):
            if cik in nodes:
                return level
            subs = out_sec10k__parents_and_subsidiaries.loc[
                (
                    out_sec10k__parents_and_subsidiaries.parent_company_central_index_key
                    == cik
                )
                & (
                    out_sec10k__parents_and_subsidiaries.report_date.dt.year
                    == report_year
                ),
                [
                    "subsidiary_company_central_index_key",
                    "subsidiary_company_id_sec10k",
                ],
            ].drop_duplicates()
            nodes[cik] = name
            for cikX, idX in subs.to_records(index=False):
                _, _, name_locationX = idX.partition("_")
                nameX, _, locationX = name_locationX.rpartition("_")
                labelX = f"{nameX}\n{locationX}"
                nodeidX = clean(idX)
                if pd.notna(cikX):
                    nodeidX = cikX
                    level = max(level, traverse(cikX, labelX, level + 1))
                else:
                    nodes[nodeidX] = labelX
                unclean[nodeidX] = idX
                edges[cik].append(nodeidX)
            return level

        root_label = "\n".join(
            out_sec10k__parents_and_subsidiaries.loc[
                out_sec10k__parents_and_subsidiaries.parent_company_central_index_key
                == root_cik,
                ["parent_company_name", "parent_company_incorporation_state"],
            ]
            .value_counts()
            .index[0]
        )  # use most-frequent name & state
        max_depth = traverse(root_cik, root_label)
        # print(f"{root_cik} max depth: {max_depth}")
        return nodes, edges, unclean, max_depth

    return (make_tree,)


@app.function
def make_mermaid(nodes, edges, label, root, prune=True):
    def add_node(nodeid, nodelabel, graph):
        graph.append(f'  {nodeid}["{nodelabel}"]')

    def add_edge(fromid, toid, graph):
        graph.append(f"  {fromid} --> {toid}")

    ret = [
        "---",
        f"title: {label} ({root})",
        "---",
        "graph TD",
    ]
    for nodeid, nodelabel in nodes.items():
        nodelabel = (
            f"{'via ' if '_' in nodeid else ''}{nodeid.partition('_')[0]}\n{nodelabel}"
        )
        add_node(nodeid, nodelabel, ret)
    seen = {}

    def add_edges(cik, level=0):
        seen[cik] = level
        # print(f"{level} {cik} {nodes[cik].partition('\n')[0]}")
        descendants = set(edges[cik])
        include = set()
        exclude = set()
        if prune:
            for desc in edges[cik]:
                if desc == cik:
                    continue
                grand = set(edges[desc])
                # grand = set(e for e in edges[desc] if e not in seen or seen[e]<level)
                exclude |= grand
                if grand & descendants:
                    if cik == "0001603291":
                        print(f" {desc} {len(grand & descendants)} of {len(grand)}")
                    include.add(desc)
        # print(", ".join(include))
        for desc in (descendants - exclude) | include:
            if prune and (desc == cik):
                continue
            if prune and (desc in seen and seen[desc] < level):
                continue
            add_edge(cik, desc, ret)
            if desc not in seen:
                add_edges(desc, level + 1)

    add_edges(root)
    return "\n".join(ret)


@app.cell
def _(defaultdict):
    def drop_cycles(edgedict, cik=""):
        clean_edges = defaultdict(list)
        inverse_edges = defaultdict(list)
        for nodeid in edgedict:
            for desc in edgedict[nodeid]:
                if desc != nodeid:
                    inverse_edges[desc].append(nodeid)
        for nodeid in edgedict:
            drop = [
                e
                for e in edgedict[nodeid]
                if (e in edgedict)
                and (nodeid in edgedict[e])
                and ((len(inverse_edges[e]) != 1) or (e == cik))
            ]
            for e in drop:
                if nodeid in inverse_edges[e]:
                    inverse_edges[e].remove(nodeid)
            clean_edges[nodeid] = [
                e for e in edgedict[nodeid] if (e != nodeid) and (e not in drop)
            ]
        return clean_edges

    return (drop_cycles,)


@app.cell
def _(defaultdict):
    def collapse_matching_labels(nodes, edges):
        node_cleanup = defaultdict(list)
        for node, label in nodes.items():
            node_cleanup[label].append(node)
        rewrite = {}
        clean_nodes = {}
        for label, nodes in node_cleanup.items():
            prefixes, _, suffixes = list(zip(*map(lambda x: x.partition("_"), nodes)))
            via = "_".join(sorted(prefixes))
            assert all(x == suffixes[0] for x in suffixes), f"bad suffixes: {suffixes}"
            nodeid = f"{via}{'__' if suffixes[0] else ''}{suffixes[0]}"
            clean_nodes[nodeid] = label
            for old in nodes:
                assert old not in rewrite, f"collision at {old}"
                rewrite[old] = nodeid
            # rewrite.update(dict((old, nodeid) for old in nodes))
        clean_edges = defaultdict(set)
        for start, endlist in edges.items():
            for e in endlist:
                clean_edges[rewrite[start]].add(rewrite[e])
        return clean_nodes, {
            nodeid: list(neighbors) for nodeid, neighbors in clean_edges.items()
        } | {nodeid: [] for nodeid in clean_nodes if nodeid not in clean_edges}

    return (collapse_matching_labels,)


@app.cell
def _(mo, out_sec10k__parents_and_subsidiaries, query_params, reset_params):
    select_utility_eia = mo.ui.dropdown(
        value=out_sec10k__parents_and_subsidiaries.loc[
            out_sec10k__parents_and_subsidiaries.parent_company_central_index_key
            == query_params["cik"],
            "parent_company_utility_name_eia",
        ]
        .dropna()
        .iloc[0],  # "DTE Sustainable Generation", # CIK 0000936340
        options=(
            out_sec10k__parents_and_subsidiaries.loc[
                out_sec10k__parents_and_subsidiaries.parent_company_utility_id_eia.notna(),
                ["parent_company_central_index_key", "parent_company_utility_name_eia"],
            ]
            .set_index("parent_company_utility_name_eia")
            .sort_index()
            .to_dict()["parent_company_central_index_key"]
        ),
        searchable=True,
        label="EIA utility name:",
    )
    use_utility_eia = mo.ui.button(
        label="Use this EIA utility",
        on_click=lambda value: reset_params(cik=select_utility_eia.value),
    )
    return select_utility_eia, use_utility_eia


@app.function
def select_rename(ser, mapping):
    return ser[mapping.keys()].rename(mapping)


@app.cell
def _():
    import altair as alt

    return (alt,)


@app.cell
def _(alt, pd):
    def available_years_sparkbar(report_dates):
        years = report_dates.dt.year.value_counts().sort_index()
        years = years.reindex(
            range(min(years.index), max(years.index) + 1), fill_value=0
        )
        years = pd.DataFrame(
            [{"year": y, "count": c} for y, c in years.to_dict().items()]
        )
        return (
            alt.Chart(years)
            .mark_bar()
            .encode(
                x=alt.X("year:O", axis=alt.Axis(title=None, ticks=False, domain=False)),
                y=alt.Y("count", axis=None),
            )
            .properties(height=25)
            .configure_view(stroke=None)
        )

    return (available_years_sparkbar,)


@app.cell
def _(
    available_years_sparkbar,
    mo,
    out_sec10k__parents_and_subsidiaries,
    select_utility_eia,
    use_utility_eia,
):
    this_utility_eia = out_sec10k__parents_and_subsidiaries.loc[
        out_sec10k__parents_and_subsidiaries.parent_company_central_index_key
        == select_utility_eia.value,
        [
            "parent_company_name",
            "parent_company_incorporation_state",
            "parent_company_central_index_key",
            "parent_company_utility_id_eia",
            "parent_company_utility_name_eia",
            "report_date",
        ],
    ]
    this_utility_eia_years_spark = available_years_sparkbar(
        this_utility_eia.report_date.dropna()
    )
    this_utility_eia = (
        this_utility_eia.drop(columns=["report_date"])
        .drop_duplicates()
        .dropna()
        .iloc[0]
        .rename("")
    )
    mo.accordion(
        {
            "## Search by name": mo.vstack(
                gap=2,
                items=[
                    select_utility_eia,
                    mo.hstack(
                        justify="start",
                        gap=2,
                        items=[
                            mo.plain(
                                select_rename(
                                    this_utility_eia,
                                    {
                                        "parent_company_central_index_key": "SEC Central Index Key",
                                        "parent_company_name": "SEC Company Name",
                                        "parent_company_incorporation_state": "Incorporation State",
                                    },
                                )
                            ),
                            mo.plain(
                                select_rename(
                                    this_utility_eia,
                                    {
                                        "parent_company_utility_id_eia": "EIA Utility ID",
                                        "parent_company_utility_name_eia": "EIA Utility Name",
                                    },
                                )
                            ),
                        ],
                    ),
                    mo.vstack(
                        [
                            mo.md("Subsidiary reports over time:"),
                            this_utility_eia_years_spark,
                        ]
                    ),
                    use_utility_eia,
                ],
            )
        }
    )
    return


@app.cell
def _(mo, selection):
    mo.vstack(
        gap=2,
        items=[
            mo.md("## Configure relationship graph settings"),
            mo.hstack(
                justify="start",
                items=[
                    selection.enter_cik,
                    selection.enter_year,
                ],
            ),
        ],
    )
    return


@app.function
def summarize_graph(nodes, edges, max_depth=None):
    parts = [f"{len(nodes)} nodes, {sum(len(x) for x in edges.values())} edges"]
    if max_depth:
        parts.append(f"max traversal depth {max_depth}")
    return "; ".join(parts)


@app.cell
def _(make_tree, mo, selection):
    raw_nodes, raw_edges, unclean, max_depth = make_tree(selection.cik, selection.year)
    mo.md(f"""
    **Raw graph**: {summarize_graph(raw_nodes, raw_edges, max_depth)}
    """)
    # print(f"{len(nodes)} nodes, {sum(len(x) for x in edges.values())} edges")
    # alt_nodes, alt_edges = collapse_matching_labels(nodes, drop_cycles(edges))
    # print(f"{len(alt_nodes)} nodes, {sum(len(x) for x in alt_edges.values())} edges")
    return raw_edges, raw_nodes


@app.cell
def _(mo):
    do_collapse = mo.ui.checkbox(True, label="Collapse duplicates by company name?")
    do_drop_cycles = mo.ui.checkbox(True, label="Drop loops?")
    do_prune = mo.ui.checkbox(True, label="Auto prune?")
    mo.vstack(
        [
            mo.md("Optional refinements:"),
            do_collapse,
            do_drop_cycles,
            do_prune,
        ]
    )
    return do_collapse, do_drop_cycles, do_prune


@app.cell
def _(
    collapse_matching_labels,
    do_collapse,
    do_drop_cycles,
    drop_cycles,
    mo,
    raw_edges,
    raw_nodes,
):
    use_nodes, use_edges = raw_nodes, raw_edges
    if do_drop_cycles.value:
        use_edges = drop_cycles(use_edges)
    if do_collapse.value:
        use_nodes, use_edges = collapse_matching_labels(use_nodes, use_edges)
    mo.md(f"""
    **Refined graph**: {summarize_graph(use_nodes, use_edges)}
    """)
    return use_edges, use_nodes


@app.cell
def _(do_prune, raw_nodes, selection, use_edges, use_nodes):
    merm = make_mermaid(
        use_nodes,
        use_edges,
        raw_nodes[selection.cik].split("\n", 1)[0],
        selection.cik,
        prune=do_prune.value,
    )
    return (merm,)


@app.cell
def _(merm, mo):
    mo.output.append(mo.md("## Relationship Graph"))
    mo.output.append(
        mo.mermaid(
            merm,
        )
    )
    return


@app.cell
def _(merm, mo):
    mo.accordion(
        {
            "View chart source (mermaid)": mo.md(f"```\n{merm}\n```"),
        }
    )
    return


if __name__ == "__main__":
    app.run()
