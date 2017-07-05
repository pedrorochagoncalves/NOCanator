from flask import Flask, request, abort
import os
import sys
import binascii
import argparse
import nocd
import nocpusher
import pyinotify
import fileEventHandler
from threading import Thread


app = Flask(__name__)

# global vars
bind_number = None
bind_token  = None
DEBUG_MODE  = False


# CONSTANT VALUES
NUM_CHARS_TOKEN = 30

# Creates a window using GTK and displays a random int between 1 and 10k
# This is used to bind the NOC CLI to the NOCd
def create_window(): 
    # Generate random number to show on the screen. The user should send a request
    # with the number to bind the user to the display
    global bind_number
    bind_number = noc.create_bind_window()

# Generates a random token with NUM_CHARS_TOKEN characters
def generate_token():
    global NUM_CHARS_TOKEN
    return str(binascii.hexlify(os.urandom(NUM_CHARS_TOKEN)))

# Verifies the provided token
def verify_token(token=None):
    global bind_token
    global DEBUG_MODE
    if token == bind_token or DEBUG_MODE is True:
      return True
    else:
      return False

# Endpoint to request the NOCd to bind to the requesting NOC CLI
@app.route("/bind-noc-display-request")
def bind_noc_display_request():
    create_window()
    global bind_token
    bind_token = generate_token()
    return "Request received. Please provide displayed bind number to receive auth token."

# Endpoint to reply to the NOCd with the provided token and random bind number
@app.route("/bind-noc-display/te-<int:random>")
def bind_noc_display_reply(random):

    # Get the string with the random number provided by the NOC Display user
    # and if it matches the string generated by bind_noc_display_request
    # close the window and start accepting commands
    global bind_number
    global bind_token

    if random == bind_number:
      noc.destroy_bind_window()
      return bind_token, 200
    
    else:
      abort(401)  

# Endpoint to stop the cycle
@app.route("/stop-cycle")
def stop_cycle():
    # Check provided token
    if not verify_token(str(request.headers['Token'])):
        abort(401)

    # Stop the cycle
    noc.stop_cycle_tab_thread()
    return 'Stopped cycling of dashboards.', 200

# Endpoint to start the cycle
@app.route("/start-cycle")
def start_cycle():
    # Check provided token
    if not verify_token(request.headers['Token']):
        abort(401)

    # Start the cycle
    noc.start_cycle_tab_thread()
    return 'Started cycling the dashboards', 200

# Endpoint to clear all dashboards and open new dashboard
@app.route("/clear-all-open-new-dashboard/<url>")
def clear_all_and_open_new_dashboard(url):

    # Check provided token
    if not verify_token(request.headers['Token']):
        abort(401)

    noc.clear_all_and_open_new_dashboard(url)
    return 'Cleared all previously opened dashboards and opened requested dashboard', 200

# Endpoint to add a new dashboard to the current list
@app.route("/add-dashboard/<url>")
def add_dashboard(url):
    # Check provided token
    if not verify_token(request.headers['Token']):
        abort(401)

    noc.add_dashboard(url)
    return 'Added requested dashboard', 200

# Endpoint to close last tab
@app.route("/close-last-tab")
def close_last_tab():
    # Check provided token
    if not verify_token(request.headers['Token']):
        abort(401)

    noc.close_tab(-1)
    return 'Closed last tab', 200

# Endpoint to close specific tab
@app.route("/close-tab/<int:tab_index>")
def close_tab(tab_index):
    # Check provided token
    if not verify_token(request.headers['Token']):
        abort(401)

        noc.close_tab(tab_index)
        return "Closed tab number:{0}".format(tab_index + 1), 200

# Endpoint to open dashboard list for the specified profile
@app.route("/open-dashboards-for-profile/<profile>")
def open_dashboards_for_profile(profile):
    # Check provided token
    if not verify_token(request.headers['Token']):
        abort(401)

    noc.open_dashboards_for_profile(profile)
    return "Opened dashboards for profile {0}".format(profile), 200

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NOCanator 3000 - Keeping OPS teams in Sync.')
    parser.add_argument('--config', dest='config', action='store', default='config.json',
                        help='Path to JSON config file.')
    parser.add_argument('-a', dest='host', action='store',
                        help='Sets the server address for the Nocpusher. Required if using client mode.')
    parser.add_argument('-p', dest='port', action='store', default=4455,
                        help='Sets the server port for the Nocpusher. Defaults to port 4455.')
    parser.add_argument('--profile', dest='profile', action='store',
                        help='Sets the NOC profile. Select the dashboards to display.Ex: SRE or NET')
    parser.add_argument('--cycle-freq', dest='cycleFrequency', action='store', default=60,
                        help='Sets the dashboard cycle frequency. Defaults to 60 seconds.')
    args = parser.parse_args()

    if args.host and not args.profile and not args.cycleFrequency:
        parser.error("NOCDisplays requires NOC profile and cycle frequency. "
                     "Add --profile with SRE and --cycle-freq with 60 (s) for example.")
        sys.exit(1)

    # Start the app

    # Create NOCd instance
    noc = nocd.Nocd(config_file=args.config, host=args.host, port=args.port, profile=args.profile,
                    cycleFrequency=float(args.cycleFrequency))

    # Create thread for API server
    api_thread = Thread(target=app.run, kwargs={'host': '0.0.0.0'})
    api_thread.setDaemon(True)
    api_thread.start()

    # Start the NOCd server
    noc.run()

    sys.exit(0)
