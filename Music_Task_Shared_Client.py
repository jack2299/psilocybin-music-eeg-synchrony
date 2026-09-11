# Music_Task_Shared_Client.py
#
# Client-side script for the synchronised music listening task.
# Part of a double-blind, randomised psilocybin EEG study conducted at
# Universidad de Buenos Aires.
#
# This script runs on the second participant's laptop. It receives
# START_<song> and END_<song> messages from the server and pushes matching
# LSL markers, so the two participants' EEG recordings can be time-aligned.
#
# Requirements:
#   - Python 3.9+
#   - pylsl
#
# No audio files are required on the client.

import socket
import sys
import time
import logging
import tkinter as tk
from tkinter import simpledialog

from pylsl import StreamInfo, StreamOutlet

# =========================================================================
# EDIT ONLY THESE
# =========================================================================
NETWORK_CONFIG = {
    'SERVER_IP': '<SERVER_IP>',   # e.g. '192.168.0.235'
    'PORT': 65501,
    'BUFFER_SIZE': 1024,
    'TIMEOUT': 30,
    'MAX_RETRIES': 5,
    'RETRY_DELAY': 2,
    'KEEPALIVE_INTERVAL': 15,
}

SONGS = [
    "StrugglingforNothing",
    "MoonRiver",
    "FamilysSong",
    "OscarsNewCamera",
    "Peace",
]
# =========================================================================

LSL_CONFIG = {
    'NAME': 'MarkerStream',
    'TYPE': 'Markers',
    'CHANNEL_COUNT': 1,
    'SAMPLE_RATE': 0,
    'FORMAT': 'string',
    'SOURCE_ID': 'uniqueid12345',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_exit(code=0):
    try:
        sys.exit(code)
    except Exception as e:
        logger.error(f"Error during exit: {e}")
        sys.exit(1)

class ClientExperiment:
    def __init__(self):
        self.sock = None
        self.outlet = None

        self.required_markers = {}
        for song in SONGS:
            self.required_markers[f"{song}_start"] = False
            self.required_markers[f"{song}_end"]   = False

        self.max_marker_retries = 3
        self.setup_lsl()
        self.in_song_playback = False
        self.played_songs = set()
        self.last_keepalive_time = time.time()
        self.sending_marker = False

    def setup_lsl(self):
        try:
            info = StreamInfo(
                name=LSL_CONFIG['NAME'],
                type=LSL_CONFIG['TYPE'],
                channel_count=LSL_CONFIG['CHANNEL_COUNT'],
                nominal_srate=LSL_CONFIG['SAMPLE_RATE'],
                channel_format=LSL_CONFIG['FORMAT'],
                source_id=LSL_CONFIG['SOURCE_ID']
            )
            self.outlet = StreamOutlet(info)
            logger.info("LSL stream created successfully")
        except Exception as e:
            logger.error(f"Failed to create LSL stream: {e}")
            safe_exit(1)

    def connect_to_server(self):
        retry_count = 0
        while retry_count < NETWORK_CONFIG['MAX_RETRIES']:
            try:
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception as e:
                        logger.debug(f"Error closing existing socket: {e}")

                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(NETWORK_CONFIG['TIMEOUT'])
                logger.info(f"Attempting to connect to {NETWORK_CONFIG['SERVER_IP']}:{NETWORK_CONFIG['PORT']} (Attempt {retry_count + 1}/{NETWORK_CONFIG['MAX_RETRIES']})")
                self.sock.connect((NETWORK_CONFIG['SERVER_IP'], NETWORK_CONFIG['PORT']))
                logger.info("Successfully connected to server")
                self.last_keepalive_time = time.time()
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {retry_count + 1} failed: {e}")
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception as close_error:
                        logger.debug(f"Error closing socket after failed connection: {close_error}")
                    self.sock = None
                retry_count += 1
                if retry_count < NETWORK_CONFIG['MAX_RETRIES']:
                    logger.info(f"Waiting {NETWORK_CONFIG['RETRY_DELAY']} seconds before next attempt...")
                    time.sleep(NETWORK_CONFIG['RETRY_DELAY'])

        logger.error(f"Failed to connect after {NETWORK_CONFIG['MAX_RETRIES']} attempts")
        return False

    def is_connection_alive(self):
        if self.sock is None:
            return False
        try:
            if self.sock.fileno() == -1:
                return False
            return True
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False

    def keep_connection_alive(self):
        if not self.is_connection_alive() or self.in_song_playback or self.sending_marker:
            return False
        try:
            self.sock.sendall(b'KEEPALIVE')
            logger.debug("Sent keep-alive message")
            return True
        except Exception as e:
            logger.warning(f"Keep-alive failed: {e}")
            return False

    def send_marker(self, marker_name):
        self.sending_marker = True
        try:
            retries = 0
            success = False
            while retries < self.max_marker_retries and not success:
                try:
                    self.outlet.push_sample([marker_name])
                    if marker_name in self.required_markers:
                        self.required_markers[marker_name] = True
                    logger.info(f"Successfully sent marker: {marker_name} (attempt {retries + 1})")
                    success = True
                except Exception as e:
                    retries += 1
                    logger.warning(f"Marker send attempt {retries} failed for {marker_name}: {e}")
                    time.sleep(0.5)

            if not success:
                logger.error(f"CRITICAL: Failed to send marker {marker_name} after {self.max_marker_retries} attempts")
                return False
            return True
        finally:
            self.sending_marker = False

    def receive_message(self):
        if self.sending_marker:
            return None
        if not self.is_connection_alive():
            return None
        try:
            message = self.sock.recv(NETWORK_CONFIG['BUFFER_SIZE']).decode()
            if not message:
                logger.warning("Server closed connection (received empty message)")
                self.sock = None
                return None
            self.last_keepalive_time = time.time()
            if message.startswith("START_"):
                self.in_song_playback = True
            elif message.startswith("END_"):
                self.in_song_playback = False
            return message
        except socket.timeout:
            return None
        except ConnectionResetError:
            logger.warning("Connection reset by server")
            self.sock = None
            return None
        except ConnectionAbortedError:
            logger.warning("Connection aborted")
            self.sock = None
            return None
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            self.sock = None
            return None

    def process_message(self, message):
        try:
            if message == "KEEPALIVE":
                logger.debug("Received keep-alive from server")
                return
            if message.startswith("START_"):
                song_name = message[6:]
                logger.info(f"Received start signal for song: {song_name}")
                self.played_songs.add(song_name)
                marker_name = f"{song_name}_start"
                if not self.send_marker(marker_name):
                    logger.error(f"Critical: Failed to send start marker for song {song_name}")
            elif message.startswith("END_"):
                song_name = message[4:]
                logger.info(f"Received end signal for song: {song_name}")
                marker_name = f"{song_name}_end"
                if not self.send_marker(marker_name):
                    logger.error(f"Critical: Failed to send end marker for song {song_name}")
        except Exception as e:
            logger.error(f"Error processing message {message}: {e}")

    def verify_all_markers_sent(self):
        expected_markers = set()
        for song in self.played_songs:
            expected_markers.add(f"{song}_start")
            expected_markers.add(f"{song}_end")

        missing_markers = [marker for marker, sent in self.required_markers.items()
                           if marker in expected_markers and not sent]

        if missing_markers:
            logger.error(f"Missing markers: {missing_markers}")
            return False
        logger.info("All required markers for played songs were successfully sent")
        return True

    def handle_end(self):
        logger.info("Experiment ending")
        if not self.verify_all_markers_sent():
            logger.error("Not all required markers were sent during the experiment")
        logger.info("Marker transmission summary:")
        for marker, sent in self.required_markers.items():
            song_name = marker.split('_')[0]
            if song_name in self.played_songs:
                logger.info(f"{marker}: {'SENT' if sent else 'MISSING'}")
        if self.sock:
            try:
                self.sock.close()
                self.sock = None
            except Exception as e:
                logger.error(f"Error closing socket: {e}")

    def run(self):
        try:
            if not self.connect_to_server():
                logger.error("Could not establish initial connection to server")
                return
            while True:
                try:
                    current_time = time.time()
                    if (not self.in_song_playback and
                            not self.sending_marker and
                            current_time - self.last_keepalive_time > NETWORK_CONFIG['KEEPALIVE_INTERVAL']):
                        self.keep_connection_alive()
                        self.last_keepalive_time = current_time

                    if not self.sending_marker:
                        message = self.receive_message()
                        if message == "end":
                            logger.info("Received end signal")
                            self.handle_end()
                            break
                        if message:
                            self.process_message(message)

                    if self.sock is None and not self.in_song_playback and not self.sending_marker:
                        if not self.connect_to_server():
                            logger.error("Failed to reconnect")
                            time.sleep(5)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    if not self.in_song_playback and not self.sending_marker:
                        if not self.connect_to_server():
                            logger.error("Failed to reconnect after error")
                            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Experiment terminated by user")
        finally:
            self.handle_end()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    server_input = simpledialog.askstring("Modo de Conexión", "¿Es usted el servidor? (s/n):")
    is_server = (server_input is not None and server_input.lower() == 's')
    if is_server:
        logger.info("Server mode selected. Please run the server script instead.")
        safe_exit(0)

    experiment = ClientExperiment()
    experiment.run()
