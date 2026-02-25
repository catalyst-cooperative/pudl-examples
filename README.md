# PUDL Example Notebooks

This repository contains a collection of
[Jupyter notebooks](https://jupyter.org) with examples of how to use the data
and software distributed by [Catalyst Cooperative](https://catalyst.coop)'s
[Public Utility Data Liberation (PUDL) project](https://github.com/catalyst-cooperative/pudl).

## Run Jupyter Notebooks on Kaggle

The easiest way to get up and running with the Jupyter examples and a fresh copy of all the
PUDL data is on [Kaggle](https://www.kaggle.com).

Kaggle offers substantial free computing resources and convenient data storage, so you
can start playing with the PUDL data without needing to set up any software or download
any data.

- [PUDL Data on Kaggle](https://www.kaggle.com/datasets/catalystcooperative/pudl-project/data)
- [01 PUDL Data Access](https://www.kaggle.com/code/catalystcooperative/01-pudl-data-access)
- [02 State Hourly Electricity Demand](https://www.kaggle.com/code/catalystcooperative/02-state-hourly-electricity-demand)
- [03 EIA-930 Sanity Checks](https://www.kaggle.com/code/catalystcooperative/03-eia-930-sanity-checks)
- [04 Renewable Generation Profiles](https://www.kaggle.com/code/catalystcooperative/04-renewable-generation-profiles)
- [05 FERC-714 Electricity Demand Forecast Biases](https://www.kaggle.com/code/catalystcooperative/05-ferc-714-electricity-demand-forecast-biases)

You'll find the [PUDL data dictionary](https://catalystcoop-pudl.readthedocs.io/en/latest/data_dictionaries/pudl_db.html)
helpful for interpreting the data.

## Run Notebooks Locally

You can also work with these notebooks and the PUDL data locally.

We use `pixi` to manage the Python environment. You can install it according to
[their instructions](https://pixi.sh/latest/installation).

Then install the project environment including development dependencies:

```
$ pixi install -e dev
```

To run the Jupyter notebooks, run:

```
$ pixi run jupyter lab
```

These notebooks access data directly from our public cloud bucket every time
they run, which can be slow. It can be much faster to download the data to your
computer *once*, and then point your notebooks at the local copy.

You can find detailed instructions for how to download the data in our [data
access
documentation](https://catalystcoop-pudl.readthedocs.io/en/nightly/data_access.html#quick-reference).

## Run Notebook Integration Test

To execute all top-level notebooks and fail if any notebook errors, run:

```
$ pixi run -e dev check-ipynbs
```

This task runs `pytest` with `nbmake`, with per-notebook progress (`-vv`) and
timing output (`--durations=0`). It uses `--capture=tee-sys` to show live output
while keeping pytest capture enabled. The same check is run in GitHub Actions by
the `Integration Test Notebooks` workflow.

## Developer Setup

If you'd like to contribute code back to this repository, you will also need to install our `pre-commit` hooks:

```
$ pixi run -e dev pre-commit install
```

Otherwise, just tweak or add notebooks as usual, commit them to your branch, and
make a pull request!

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
