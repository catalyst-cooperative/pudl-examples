# PUDL Tutorials

This repository contains a collection of
[Jupyter notebooks](https://jupyter.org) with examples of how
to use the data and software distributed
[Catalyst Cooperative](https://catalyst.coop)'s
[Public Utility Data Liberation (PUDL) project](https://github.com/catalyst-cooperative/pudl).

The examples require the PUDL data to be available, and it is too large to
commit to a GitHub repository. We have an experimental shared
[JupyterHub](https://jupyter.org/hub) running in
collaboration with [2i2c](https://2i2c.org). If you have an account on our
hub, you can work through the example notebooks by following
[this link](https://catalyst-cooperative.pilot.2i2c.cloud/hub/user-redirect/git-pull?repo=https%3A%2F%2Fgithub.com%2Fcatalyst-cooperative%2Fpudl-tutorials&urlpath=lab%2Ftree%2Fpudl-tutorials%2Fnotebooks%2F01-pudl-database.ipynb&branch=main). If you'd like to get an account email:
[pudl@catalyst.coop](mailto:pudl@catalyst.coop)

## Running the PUDL Jupyter Container

We also use this repository to define PUDL's computational environment for
users, via [`repo2docker`](https://github.com/jupyterhub/repo2docker). If you
have Docker and `docker-compose` installed on your computer, you should be able
to start up a Jupyter Notebook server locally, based on this environment, by
cloning this repository and running:

```
docker-compose up
```

## Environment Variables

The Docker container needs to be pointed at a couple of local directories to
work properly with PUDL. These paths are set using environment variables:
* `PUDL_DATA_DIR` is the path to the PUDL directory containing your PUDL
`data`, `sqlite` and `epacems` directories.
* `PUDL_WORKING_DIR` is a local directory that you want to have access to
within the container -- it can contain other data or notebooks, etc.

You can also set these environment variables in the `.env` file that is part of
the repository.

## Contact Us

* Web: [Catalyst Cooperative](https://catalyst.coop)
* Email: [pudl@catalyst.coop](mailto:pudl@catalyst.coop)
* Twitter: [@CatalystCoop](https://twitter.com/CatalystCoop)
