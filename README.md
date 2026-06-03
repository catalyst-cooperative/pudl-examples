# PUDL Example Notebooks

This repository contains a collection of
[Jupyter notebooks](https://jupyter.org) with examples of how to use the data
and software distributed by [Catalyst Cooperative](https://catalyst.coop)'s
[Public Utility Data Liberation (PUDL) project](https://github.com/catalyst-cooperative/pudl).

We have multiple categories of notebooks in this repository:

| Category | File location | Description | Live view | Local dev env |
| --- | --- | --- | --- | --- |
| [Kaggle notebooks](#kaggle-notebooks) | repository root | Mirrored from the [Kaggle notebooks](https://www.kaggle.com/code/catalystcooperative/). Any changes made to these notebooks directly in this repository will be overwritten. | [Kaggle](https://www.kaggle.com/code/catalystcooperative/) | `pixi run -e kaggle jupyter lab` |
| [WebAssembly Marimo notebooks](#webassembly-marimo-notebooks) | `wasm/marimo` | Marimo notebooks designed for exporting as interactive browser dashboards. | [PUDL Data Viewer](https://data.catalyst.coop/dashboards) | `pixi run -e wasm marimo edit` |

## General development notes

We use `pixi` to manage the Python environment. You can install it according to
[their instructions](https://pixi.sh/latest/installation).

We use multiple `pixi` environments to manage the various quirks of the
different execution environments of our notebooks: we currently have `kaggle`
and `wasm` defined. We also have `dev` defined for repository-infrastructure
related tools.

Speaking of which - you probably want to install the pre-commit hooks if you're
planning on making changes to the notebooks, the repository infrastructure, or
anything else that might require you to commit something.

```
$ pixi run -e dev prek install
```

## Kaggle notebooks

These are notebooks which explore how to access PUDL and showcase some potential
analyses you can do. They are intended to serve as jumping-off points for your
own code.

Critically, these are mirrored from Kaggle, and updates in this repository will
be overwritten from Kaggle.

### Running on Kaggle

The easiest way to get up and running with a fresh copy of all the PUDL data is
on [Kaggle](https://www.kaggle.com).

Kaggle offers substantial free computing resources and convenient data storage, so you
can start playing with the PUDL data without needing to set up any software or download
any data.

- [PUDL Data on Kaggle](https://www.kaggle.com/datasets/catalystcooperative/pudl-project/data)
- [01 PUDL Data Access](https://www.kaggle.com/code/catalystcooperative/01-pudl-data-access)
- [02 State Hourly Electricity Demand](https://www.kaggle.com/code/catalystcooperative/02-state-hourly-electricity-demand)
- [03 EIA-930 Sanity Checks](https://www.kaggle.com/code/catalystcooperative/03-eia-930-sanity-checks)
- [04 Renewable Generation Profiles](https://www.kaggle.com/code/catalystcooperative/04-renewable-generation-profiles)
- [05 FERC-714 Electricity Demand Forecast Biases](https://www.kaggle.com/code/catalystcooperative/05-ferc-714-electricity-demand-forecast-biases)
- [06 PUDL Imputed Electricity Demand](https://www.kaggle.com/code/catalystcooperative/06-pudl-imputed-electricity-demand)
- [07 FERC EQR Access](www.kaggle.com/code/catalystcooperative/07-ferc-eqr-access)

You'll find the [PUDL data dictionary](https://catalystcoop-pudl.readthedocs.io/en/latest/data_dictionaries/pudl_db.html)
helpful for interpreting the data.

### Running locally

To run these notebooks locally, run:

```
$ pixi run -e kaggle jupyter lab
```

These notebooks access data directly from our public cloud bucket every time
they run, which can be slow. It can be much faster to download the data to your
computer *once*, and then point your notebooks at the local copy, though the
full dataset takes tens of GB of storage.

You can find detailed instructions for how to download the data in our [data
access
documentation](https://catalystcoop-pudl.readthedocs.io/en/nightly/data_access.html#quick-reference).

#### Updating the dependencies

The Kaggle Python environment is an eternally shifting patchwork of
dependencies. We try to keep the Pixi environment up to date by occasionally
running a notebook on Kaggle that just checks dependency versions.

To update the Kaggle dependency pins yourself:

1. Create a Kaggle API token and put it in your env as `KAGGLE_API_TOKEN`.
2. Run the sync script:
```
$ pixi run -e dev sync-kaggle-deps
```
3. Run `pixi lock` to see if the Kaggle deps are... actually solvable.
4. Resolve any solvability problems by adding the less-important-to-pin
   dependencies to `--exclude` in the `sync-kaggle-deps` pixi task.


## WebAssembly Marimo notebooks

These are designed to be exported to HTML and viewed in a web browser as an
interactive dashboard or visualization.

### Viewing in-browser

These are currently viewable on the [PUDL Data
Viewer](https://data.catalyst.coop/dashboards). Click through and play
around!

### Running locally

Run `marimo edit` to start editing:

```
$ pixi run -e wasm marimo edit wasm/marimo
```

If you want to export the notebooks to WebAssembly and see if they work as
standalone HTML pages:

```
$ pixi run -e wasm export-wasm-marimo --serve
```

Then go to `localhost:8000/<your-notebook-name>.html` to see it work!

This uses [`pyodide`](https://pyodide.org/) to run Python in your browser, which
comes with a few quirks:

* Marimo is currently (as of 2026-02-27) pinned to version `0.27.7` - which
  means the [libraries that are
  available](https://pyodide.org/en/0.27.7/usage/packages-in-pyodide.html) in
  `pyodide` are pretty old. To minimize shock while going from `marimo edit` to
  the exported version, we pin dependencies based on those versions.
* You have to explicitly import `fastparquet` or `pyarrow` for
  `pandas.read_parquet` to actually work. `fastparquet` is 3-10x faster.

See the [Marimo docs](https://docs.marimo.io/guides/wasm/) for more details.


Finally, if you want to add automated tests with `playwright`:

First, install a browser driver for `playwright`:

```
$ pixi run -e wasm playwright install --with-deps chromium
```

Then, run the tests:

```
$ pixi run -e wasm test-wasm-marimo
```

You can add more tests in `tests/playwright/...`


## Stalk us on the Internet

- <https://catalyst.coop>
- Email: [pudl@catalyst.coop](mailto:pudl@catalyst.coop)
- Mastodon: [@CatalystCoop@mastodon.energy](https://mastodon.energy/@CatalystCoop)
- BlueSky: [@catalyst.coop](https://bsky.app/profile/catalyst.coop)
- [GitHub](https://github.com/catalyst-cooperative)
- [LinkedIn](https://linkedin.com/company/catalyst-cooperative)
- [Kaggle](https://www.kaggle.com/catalystcooperative)
- [HuggingFace](https://huggingface.co/catalystcooperative)
- [YouTube](https://youtube.com/@CatalystCooperative)
- [Slack](https://join.slack.com/t/catalystcooperative/shared_invite/zt-2yg1v2sb7-GsoGlA9Ojc_LCJ00vPWKbQ)
- Twitter: [@CatalystCoop](https://twitter.com/CatalystCoop)

## Supporting PUDL

These example notebooks are part of the
[Public Utility Data Liberation Project (PUDL)](https://github.com/catalyst-cooperative/pudl),
a project of [Catalyst Cooperative](https://catalyst.coop). PUDL has been made possible
by the generous support of our sustainers, grant funders, and volunteer open source
contributors.

If you would like to support the ongoing development of PUDL, please consider
[becoming a sustainer](https://opencollective.com/pudl).
