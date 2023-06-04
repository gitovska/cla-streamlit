# cla-streamlit

This dashboard is used to analyse the points awarded to programming groups in the course Computerlinguistische
Anwendungen (Computational Linguistic Applications) at the Ludwig Maximilian University of Munich.

It is a [Streamlit](https://streamlit.io/) app deployed on the Streamlit Community Cloud at
[cla-grades.streamlit.app](https://cla-grades.streamlit.app).

The dashboard reads from two private Google Sheets, one with the course data and one with demo data for display purposes.
Authentication is required to view the course data.

### Development

This project uses [Poetry](https://python-poetry.org/) 1.5.1 for Python packaging and dependency management and Python 3.9.16.
You may like to use [pyenv](https://github.com/pyenv/pyenv) to manage your Python versions.

You can use an IDE to create your virtual environment with Poetry, or instantiate it manually:

First clone the repository. Then:

````
$ pyenv install 3.9.16
$ cd cla-streamlit
$ pyenv local 3.9.16
$ poetry install
````

Start the Streamlit app locally:

```
$ poetry run streamlit run cla_streamlit/streamlit_app.py
```
