# PUDL Example Notebooks

This repository contains a collection of
[Jupyter notebooks](https://jupyter.org) with examples of how to use the data
and software distributed by [Catalyst Cooperative](https://catalyst.coop)'s
[Public Utility Data Liberation (PUDL) project](https://github.com/catalyst-cooperative/pudl).

## Run PUDL Notebooks on Kaggle

The easiest way to get up and running with these examples and a fresh copy of all the
PUDL data is on [Kaggle](https://www.kaggle.com).

Kaggle offers substantial free computing resources and convenient data storage, so you
can start playing with the PUDL data without needing to set up any software or download
any data.

- [PUDL Data on Kaggle](https://www.kaggle.com/datasets/catalystcooperative/pudl-project/data)
- [01 PUDL Data Access](https://www.kaggle.com/code/catalystcooperative/01-pudl-data-access)
- [02 State Hourly Electricity Demand](https://www.kaggle.com/code/catalystcooperative/02-state-hourly-electricity-demand)
- [03 EIA-930 Sanity Checks](https://www.kaggle.com/code/catalystcooperative/03-eia930-sanity-checks)
- [04 Renewable Generation Profiles](https://www.kaggle.com/code/catalystcooperative/04-renewable-generation-profiles)

You'll find the [PUDL data dictionary](https://catalystcoop-pudl.readthedocs.io/en/latest/data_dictionaries/pudl_db.html)
helpful for interpreting the data.

## Running Jupyter locally

If you're already familiar with git, Python environments, filesystem paths, and running
upyter notebooks locally, you can also work with these notebooks and the PUDL data locally:

- Create a Python environment that includes common data science packages. We like to use
  the [mamba](https://github.com/mamba-org/mamba) package manager and the
  [conda-forge](https://conda-forge.org/#about) channel.
- Clone this repository.
- [Download the PUDL dataset from Kaggle](https://www.kaggle.com/datasets/catalystcooperative/pudl-project/download)
  (it's ~20GB!) and unzip it somewhere conveniently accessible from the notebooks in the
  cloned repo.
- Start your JupyterLab or Jupyter Notebook server and navigate to the notebooks in
  the cloned repo.
- You'll need to adjust the file paths in the notebooks to point at the directory where
  you put the PUDL data, and might need to adjust the packages installed in your Python
  environment to work with the notebooks.

## Other Data Access Methods

See [the PUDL documentation](https://catalystcoop-pudl.readthedocs.io/en/latest/data_access.html)
for other data access methods.

If you're familiar with cloud services, you can check out:

- [PUDL in the AWS Open Data Registry](https://registry.opendata.aws/catalyst-cooperative-pudl/):
  s3://pudl.catalyst.coop (free access)
- Google Cloud Storage: gs://pudl.catalyst.coop (requester pays)

## Stalk us on the Internet

- https://catalyst.coop
- Email: [pudl@catalyst.coop](mailto:pudl@catalyst.coop)
- Mastodon: [@CatalystCoop@mastodon.energy](https://mastodon.energy/@CatalystCoop)
- BlueSky: [@catalyst.coop](https://bsky.app/profile/catalyst.coop)
- [GitHub](https://github.com/catalyst-cooperative)
- [LinkedIn](https://linkedin.com/company/catalyst-cooperative)
- [Kaggle](https://www.kaggle.com/catalystcooperative)
- [HuggingFace](https://huggingface.co/catalystcooperative)
- Twitter: [@CatalystCoop](https://twitter.com/CatalystCoop)
