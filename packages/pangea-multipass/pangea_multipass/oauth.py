import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests


class OauthFlow:
    # TODO: improve to be thread safe
    _auth_code = None

    auth_url: str
    token_url: str
    client_id: str
    client_secret: str
    host: str
    port: int

    def __init__(
        self,
        auth_url: str,
        token_url: str,
        client_id: str,
        client_secret: str,
        host: str = "localhost",
        port: int = 8080,
    ):
        self.auth_url = auth_url
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.host = host
        self.port = port

    def run(self):
        self._auth_code = None
        redirect_uri = f"http://{self.host}:{self.port}"

        auth_url = f"{self.auth_url}?client_id={self.client_id}&response_type=code&token_access_type=offline&redirect_uri={redirect_uri}"
        webbrowser.open(auth_url)

        server_thread = threading.Thread(target=OauthFlow._run_server, daemon=True)
        server_thread.start()

        while OauthFlow._auth_code is None:
            pass  # Busy wait (can be improved with event-based handling)

        response = requests.post(
            self.token_url,
            data={
                "grant_type": "authorization_code",
                "code": OauthFlow._auth_code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()

    class OAuthHandler(BaseHTTPRequestHandler):
        """Handles the OAuth redirect to capture auth code automatically."""

        def do_GET(self):
            if "code=" in self.path:
                OauthFlow._auth_code = self.path.split("code=")[-1].split("&")[0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization Successful!</h1><p>You can close this tab.</p>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h1>Authorization Failed</h1>")

    @staticmethod
    def _run_server(host: str = "localhost", port: int = 8080):
        """Starts a simple HTTP server to listen for OAuth callback."""

        redirect_uri = f"http://{host}:{port}"
        server = HTTPServer((host, port), OauthFlow.OAuthHandler)
        print(f"\n🌍 Listening for authentication response on {redirect_uri} ...")
        server.handle_request()  # Handles only one request (closes after first login)

    @staticmethod
    def refresh_access_token(url: str, refresh_token: str, client_id: str, client_secret: str):
        """Refresh the access token using the refresh token."""

        # Send request to refresh the token
        response = requests.post(
            url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        return response.json()
