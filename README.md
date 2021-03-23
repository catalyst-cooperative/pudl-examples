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
users, via [`repo2docker`](https://github.com/jupyterhub/repo2docker). To
use this environment, you'll need to install Docker and `docker-compose`.
* [Get Docker](https://docs.docker.com/get-docker/)
* [Install Docker Compose](https://docs.docker.com/compose/install/)

With those installed, you should be able to start up a Jupyter Notebook server
that has the PUDL software installed by cloning this repository and running:
```
docker-compose up
```
from within the top level repository directory.

## Environment Variables

The Docker container needs to be pointed at a couple of local directories to
work properly with PUDL. These paths are set using environment variables:
* `PUDL_DATA` is the path to the PUDL directory containing your PUDL
`data`, `sqlite` and `epacems` directories. It is treated as read-only, and by
default is set to `./pudl_data`
* `USER_DATA` is a local directory that you want to have access to
within the container. It can contain other data, or your own notebooks, etc. by
default it is set to `./user_data`

You can also set these environment variables in the `.env` file that is part of
the repository.

To be able to fill in data using the EIA API, you'll need to [obtain an API KEY
from EPA](https://www.eia.gov/opendata/register.php). If you set an environment
variable called `API_KEY_EIA` in your shell, and run our container using
`docker-compose` it will be passed in to the container and available for use
automatically.

## Instructions for accessing bundled data
To use this Docker container with processed data bundled together in an archive:

* First, you'll need to [install Docker](https://docs.docker.com/get-docker/).
  On MacOS and Windows it'll be called "Docker Desktop". On Linux it's just
  "Docker."
* On Linux, you'll also need to install a tool called
  [docker-compose](https://docs.docker.com/compose/install/)
* If you're on MacOS or Windows, open the settings in Docker Desktop and
  increase the amount of memory it's allowed to use to be at least 8GB.
* Make sure that the Docker service is running in the background. On MacOS it
  should show up in the menu bar. On Windows it should show up in the system
  tray.  On Linux, a daemon called `dockerd` should be running in the
  background.
* Download and extract this archive (ADD LINK) (~5GB) into a local directory.
  On MacOS and Windows you should just be able to double-click the archive
  file. On Linux you'll probably want to use the command line, with something
  like: `tar -xvzf FILENAME.tgz`
* At a command line, go into the directory which was created by extracting the
  archive.  It should contain a file named `docker-compose.yml`. In that
  directory, run `docker-compose up`
* You should see some logging messages as the PUDL Docker image is downloaded
  from Docker Hub, and it starts up a Jupyter Notebook server. At the end of
  those logging message, it should give you several possible links to click.
  Pick one that starts with `https://localhost:48512` or
  `https://127.0.0.1:48512` and open it in your browser.  This is a local web
  address -- the Jupyter Notebook server is running on your computer, not out
  on the remote internet somewhere.
* You should get a JupyterLab launcher / notebook interface. In the file
  browser in the left hand sidebar, you should see a "notebooks" directory with
  the example notebooks from this repository in it, which (hopefully!) you will
  be able to run.

## Contact Us

* Web: [Catalyst Cooperative](https://catalyst.coop)
* Email: [pudl@catalyst.coop](mailto:pudl@catalyst.coop)
* Twitter: [@CatalystCoop](https://twitter.com/CatalystCoop)
