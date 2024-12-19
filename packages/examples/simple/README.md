# Pangea Multipass simple example

This example demonstrates connecting to a Google Drive folder, retrieving a list of files, and checking a specific user’s read access to each of the files. It does not differentiate between owner, editor, commenter, or viewer roles since all provide read access

## Using the Samples

### Creating the Google Credentials

To get started, you’ll need two Google accounts. We’ll call one the Admin account and the other the User account.

Within the Admin account, you'll need to create a Google Cloud project with both the Google Drive and Google Sheets APIs enabled.

If your organizational Google account does not allow setting up a Google Cloud project this way, you can use a personal Google account instead. Within your project, enable both the Google Drive API  and the Google Sheets API and create a service account. Save the resulting json credentials file in the `packages` directory as `credentials.json`.

Using the Admin account, create a folder in Google Drive, add some files, and grant access to some of them to the User account. Note the folder id from the url for later.

### Installation

Ensure you have [Poetry](https://python-poetry.org/docs/#installation) installed for dependency management and virtual environment setup.

Run the following command to install all dependencies:

```bash
poetry install
```

### Run the code

Use the folder id from above in this command:

```bash
poetry run python 04-gdrive-check.py TODO:FOLDERID
```

The first time you run this script, it will open a browser window to have you log in as the Admin user. That will retrieve the list of files.

Then


After a moment, the script will open a browser window requesting you to log into Google. Log in using the User account. You will likely get a warning stating this app is not verified, simply click through. Then grant the application access to see information about your Google Drive files. This will only access the folder you’ve shared.

### Expected Output

In my case, I shared a folder that had 4 files in it but revoked access to one of the files. This is the result:

```
Loading Google Drive docs...
Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=adsfadfs.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A51947%2F&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.readonly&state=JRX6eYG7B7qeQySM0j3D0L97dkoJVe&access_type=offline
```

The browser will open here for those log in steps. After log in, the script will continue:

```
Processing 4 docs...
User: 'USERhas access to the next files in folder 'FOLDERID'
id: FILEID1 filename: FILENAME1.
id: FILEID2 filename: FILENAME2.
id: FILEID3 filename: FILENAME3.

User 'USER' has NO access to the next files in folder 'FOLDERID'
id: FILEID4 filename: FILENAME4.
```

Notice that while the script has access to the entire folder, for the User account, there is no indication that another file exists.
