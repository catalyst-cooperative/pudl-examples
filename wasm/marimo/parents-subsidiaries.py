import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import re

    return mo, pd, re


@app.cell
def _(defaultdict, out_sec10k__parents_and_subsidiaries, pd, re):
    PUNCT = re.compile("[^a-z0-9]+")
    SPACE = re.compile("_? +_?")

    def clean(text):
        return SPACE.sub("_", PUNCT.sub("_", text))

    def make_tree(root_cik, report_date):
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
                & (out_sec10k__parents_and_subsidiaries.report_date == report_date),
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
            .drop_duplicates()
            .to_records(index=False)[0]
        )
        max_depth = traverse(root_cik, root_label)
        print(f"{root_cik} max depth: {max_depth}")
        return nodes, edges, unclean

    return (make_tree,)


@app.function
def make_mermaid(nodes, edges, label, root, prune=True):
    def add_node(nodeid, nodelabel, graph):
        graph.append(f"  {nodeid}[{nodelabel}]")

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
        print(f"{level} {cik} {nodes[cik].partition('\n')[0]}")
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
def _(pd):
    out_sec10k__parents_and_subsidiaries = pd.read_parquet(
        "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/out_sec10k__parents_and_subsidiaries.parquet"
    )
    return (out_sec10k__parents_and_subsidiaries,)


@app.cell
def _():
    from collections import defaultdict

    return (defaultdict,)


@app.cell
def _(mo, out_sec10k__parents_and_subsidiaries):
    select_utility = mo.ui.dropdown(
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
        full_width=True,
    )
    select_utility
    return


@app.cell
def _():
    # todo: display basic info about selected utility
    # make a button to use its CIK below
    return


@app.cell
def _(mo):
    cik = mo.ui.text("0000936340", label="Parent company CIK")
    filing_date = mo.ui.date(
        "2023-01-01", label="Filing date for parent-subsidiary relationships"
    )
    mo.hstack(
        [
            cik,
            filing_date,
        ]
    )
    return cik, filing_date


@app.cell
def _(cik, filing_date, make_tree, mo):
    nodes, edges, unclean = make_tree(cik.value, filing_date.value)
    mo.md(f"""
    **Raw graph**: {len(nodes)} nodes, {sum(len(x) for x in edges.values())} edges
    """)
    # print(f"{len(nodes)} nodes, {sum(len(x) for x in edges.values())} edges")
    # alt_nodes, alt_edges = collapse_matching_labels(nodes, drop_cycles(edges))
    # print(f"{len(alt_nodes)} nodes, {sum(len(x) for x in alt_edges.values())} edges")

    return edges, nodes


@app.cell
def _(mo):
    do_collapse = mo.ui.checkbox(True, label="Collapse duplicates by company name?")
    do_drop_cycles = mo.ui.checkbox(True, label="Drop loops?")
    do_prune = mo.ui.checkbox(True, label="Auto prune?")
    mo.vstack(
        [
            do_collapse,
            do_drop_cycles,
            do_prune,
        ]
    )
    return do_collapse, do_drop_cycles, do_prune


@app.cell
def _(cik, nodes):
    nodes[cik.value]
    return


@app.cell
def _(
    collapse_matching_labels,
    do_collapse,
    do_drop_cycles,
    drop_cycles,
    edges,
    mo,
    nodes,
):
    use_nodes, use_edges = nodes, edges
    if do_drop_cycles.value:
        use_edges = drop_cycles(use_edges)
    if do_collapse.value:
        use_nodes, use_edges = collapse_matching_labels(use_nodes, use_edges)
    mo.md(f"""
    **Refined graph**: {len(use_nodes)} nodes, {sum(len(x) for x in use_edges.values())} edges
    """)
    return use_edges, use_nodes


@app.cell
def _(cik, do_prune, mo, nodes, use_edges, use_nodes):
    merm = make_mermaid(
        use_nodes,
        use_edges,
        nodes[cik.value].split("\n", 1)[0],
        cik.value,
        prune=do_prune.value,
    )
    mo.mermaid(merm)
    return (merm,)


@app.cell
def _(merm):
    print(merm)
    return


if __name__ == "__main__":
    app.run()
