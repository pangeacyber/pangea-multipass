# Pangea Multipass Examples

## Setting up your Data Sources

Check out the README in the base `examples` folder for the environment variables you need for each data source. 

## Running the Code

Ensure you have [Poetry](https://python-poetry.org/docs/#installation) installed for dependency management and virtual environment setup.

### Installing Dependencies

Run the following command to install all dependencies:

```bash
poetry install
```


### Running the Github check:

```bash
poetry run python 01-github-check.py
```

*Note:* If your admin account has access to numerous repositories - directly or via Organizations - this may take a while. For test purposes, we recommend using a smaller test account.

```bash
Loaded 8 docs:
offices.txt 
strategy.txt 
capacitor.txt 
folder_1/internal_architecture.txt 
folder_2/react.txt 
folder_1/salaries.txt 
folder_2/venture-capital.txt 
interest-rate.txt 

Authorized docs: 5
offices.txt 
strategy.txt 
capacitor.txt 
folder_1/internal_architecture.txt 
folder_2/react.txt
```

### Running the Google Drive check:

```bash
poetry run python 02-gdrive-check.py
```
