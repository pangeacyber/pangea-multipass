# Pangea Multipass Examples

## Setting up your Data Sources

Check out the README in the base `examples` folder for the environment variables you need for each data source.

## Running the Code

Ensure you have [Poetry](https://python-poetry.org/docs/#installation) installed for dependency management and virtual environment setup.

### Installing Dependencies

Run the following command to install all dependencies:

```bash
poetry install --no-root
```

### Running the GitHub check:

After you set the GitHub environment variables in the `examples\README.md` file, run this command:

```bash
poetry run python 01-github-check.py
```

*Note:* If your admin account has access to numerous repositories - directly or via Organizations - this may take a while. For test purposes, we recommend using a smaller test account.

Sample output:

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

After you set the Google Drive environment variables in the `examples\README.md` file, run this command:

```bash
poetry run python 02-gdrive-check.py
```


### Running the Slack check:

After you set the Slack environment variables in the `examples\README.md` file, run this command:

```bash
poetry run python 03-slack-check.py
```

*Note:* In order to read messages from your Slack channel, your app/bot will need to be present in the channel. This applies to both public and private channels. Any public channels that the bot is not in will generate a "not_in_channel" message.

Sample output:

```bash
Error fetching messages for channel C021V27F8KU: not_in_channel
Error fetching messages for channel C0LNSFJ6897: not_in_channel
Loaded 38 messages.
User has acess to channel ids:
	C021V27F8KU
	C0LNLKJ6897
	C021V8CDFMZ
	C029J65B4KH
	C02PFMW465Q
	C087CNAQGLV
	C087K7JPQQ4
User has access to 32 messages
```

### Running the Dropbox check:

After you set the Dropbox environment variables in the `examples\README.md` file, run this command:

```bash
poetry run python 04-dropbox-check.py
```

The first time this runs, it will open a browser window to authorize the Dropbox application to your account and store the resulting tokens. Later runs will simply continue to the output below.

Sample output:

```bash
Listening for authentication response on http://localhost:8080 ...
127.0.0.1 - - [18/Feb/2025 11:18:32] "GET /?code=crD1VEFcJzAAAAAAAABLxoiqCA5-LbgQiaGWQR2R3gA HTTP/1.1" 200 -
Loading documents from Dropbox...
Loaded page: 1. Docs: 0
Loaded page: 2. Docs: 20
Loaded page: 3. Docs: 18
Loaded page: 4. Docs: 23
Loaded 61 docs
Filtering authorized documents...
Authorized docs: 22
```