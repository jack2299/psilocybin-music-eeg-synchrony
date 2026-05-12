import pylsl
import socket
import time
import tkinter as tk
from tkinter import simpledialog
import random
from psychopy import prefs
prefs.hardware['audioLib'] = ['PTB']
from psychopy import sound, visual, core, event
import logging
import os
import sys

# Constants organized by category
NETWORK_CONFIG = {
    'HOST': "192.168.0.235",
    'PORT': 65501,
    'TIMEOUT': 15,
    'MAX_MESSAGE_SIZE': 1024,
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1,
    'MAX_SEND_ATTEMPTS': 10
}

EXPERIMENT_CONFIG = {
    'BREAK_DURATION': 5,
    'WINDOW_SIZE': (800, 600),
    'TEXT_HEIGHT': 30,
    'WINDOW_COLOR': 'black',
    'TEXT_COLOR': 'white',
    'CHECK_INTERVAL': 0.1,
    'MIN_AUDIO_DURATION': 0.1
}

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def safe_quit():
    """Safely quit the experiment"""
    try:
        core.quit()
    except Exception as e:
        logging.error(f"Error during quit: {e}")
        sys.exit(1)

def is_connection_alive(conn):
    """Check if connection is still valid"""
    try:
        conn.sendall(b'')
        return True
    except:
        return False
        
def send_message(conn, message, server_socket=None):
    """
    Send message with reconnection logic, returning updated connection objects
    """
    attempts = 0
    while attempts < NETWORK_CONFIG['MAX_SEND_ATTEMPTS']:
        try:
            if not is_connection_alive(conn):
                raise socket.error("Connection dead")
            
            conn.sendall(message.encode())
            logging.info(f'Sent message: {message}')
            return conn, server_socket, True
        except socket.error as e:
            logging.warning(f"Failed to send message: {e}, attempt {attempts+1}/{NETWORK_CONFIG['MAX_SEND_ATTEMPTS']}")
            
            # Try to reconnect
            try:
                if server_socket:
                    server_socket.close()
                logging.info("Attempting to reestablish connection...")
                new_conn, new_server_socket = create_connection(True)
                
                # Update connections if reconnection was successful
                conn = new_conn
                server_socket = new_server_socket
                    
                logging.info("Connection reestablished successfully")
            except Exception as reconnect_error:
                logging.error(f"Reconnection failed: {reconnect_error}")
            
            attempts += 1
            time.sleep(NETWORK_CONFIG['RETRY_DELAY'])
            
    return conn, server_socket, False

def play_bell_sound(win=None):
    """
    Plays the bell sound to signal the end of the experiment
    """
    logging.info("Playing bell sound")
    bell_sound = None
    
    try:
        # Get the bell sound file path (in the same directory as the script)
        bell_sound_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Bell.wav')
        
        # Load the bell sound
        if os.path.exists(bell_sound_path):
            bell_sound = sound.Sound(bell_sound_path)
            logging.info(f"Bell sound loaded from: {bell_sound_path}")
        else:
            # Fallback to synthetic tone if file not found
            bell_sound = sound.Sound('G', octave=4, secs=0.3)
            logging.info("Using synthetic tone as fallback for bell sound")
        
        # Play the bell sound
        bell_sound.play()
        core.wait(0.5)  # Wait for bell to play
        
    except Exception as e:
        logging.error(f"Error playing bell sound: {e}")
        
        # Visual fallback if audio fails and window is provided
        if win is not None:
            logging.warning("Using visual fallback for bell sound")
            flash = visual.Rect(win, width=2, height=2, fillColor='white')
            for _ in range(3):
                flash.draw()
                win.flip()
                core.wait(0.2)
                win.flip()
                core.wait(0.2)
    
    finally:
        # Clean up the bell sound if it was created
        if bell_sound is not None:
            try:
                bell_sound.stop()
                del bell_sound
            except Exception as e:
                logging.error(f"Error cleaning up bell sound: {e}")

def cleanup(win, conn, s=None, is_server=False, outlet=None, sound_obj=None):
    """
    Handles proper cleanup of all resources
    """
    try:
        if sound_obj:
            try:
                sound_obj.stop()
            except Exception as e:
                logging.error(f"Error stopping sound: {e}")
            finally:
                try:
                    del sound_obj
                except Exception as e:
                    logging.error(f"Error deleting sound object: {e}")
        
        if outlet:
            try:
                del outlet
            except Exception as e:
                logging.error(f"Error cleaning up LSL outlet: {e}")
            
        if is_server and conn:
            try:
                # Don't use send_message here to avoid reconnection attempts during cleanup
                conn.sendall('end'.encode())
                logging.info("Sent end message")
            except Exception as e:
                logging.error(f"Error sending end message: {e}")
                
        if conn:
            try:
                conn.close()
            except Exception as e:
                logging.error(f"Error closing connection: {e}")
            
        if s:
            try:
                s.close()
            except Exception as e:
                logging.error(f"Error closing server socket: {e}")
            
        if win:
            try:
                win.close()
            except Exception as e:
                logging.error(f"Error closing window: {e}")
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
    finally:
        safe_quit()

def create_connection(is_server):
    """
    Creates network connection between server and client with persistent retries
    """
    if is_server:
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(NETWORK_CONFIG['TIMEOUT'])
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((NETWORK_CONFIG['HOST'], NETWORK_CONFIG['PORT']))
                s.listen(1)
                logging.info("Waiting for connection...")
                
                while True:
                    try:
                        conn, addr = s.accept()
                        conn.settimeout(NETWORK_CONFIG['TIMEOUT'])
                        logging.info(f"Connected to {addr}")
                        return conn, s
                    except socket.timeout:
                        logging.info("Waiting for client to connect...")
                        continue
                    except socket.error as e:
                        logging.error(f"Server connection error: {e}")
                        time.sleep(1)
                        continue
            except Exception as e:
                logging.error(f"Server setup error: {e}")
                time.sleep(1)
                continue
    else:
        logging.error("This script is intended to be run as the server.")
        safe_quit()

def check_escape():
    """Check if escape key is pressed"""
    return bool(event.getKeys(['escape']))
    
def main():
    win = None
    conn = None
    server_socket = None
    outlet = None
    sound_file = None
    is_server = False

    try:
        # Initialize tkinter and hide its root window
        root = tk.Tk()
        root.withdraw()

        # Ask if this machine is the server
        server_input = simpledialog.askstring("Modo de Conexión", "¿Es usted el servidor? (s/n):")
        is_server = (server_input is not None and server_input.lower() == 's')

        if not is_server:
            logging.error("This script must be run as server")
            return

        # Define the markers (now as strings for LSL)
        markers = {
            'StrugglingforNothing': {
                'start': 'StrugglingforNothing_start',
                'end': 'StrugglingforNothing_end'
            },
            'MoonRiver': {
                'start': 'MoonRiver_start',
                'end': 'MoonRiver_end'
            },
            'FamilysSong': {
                'start': 'FamilysSong_start',
                'end': 'FamilysSong_end'
            },
            'OscarsNewCamera': {
                'start': 'OscarsNewCamera_start',
                'end': 'OscarsNewCamera_end'
            },
            'Peace': {
                'start': 'Peace_start',
                'end': 'Peace_end'
            },
        }

        # Define the audio stimuli (keeping hardcoded paths)
        audio_stimuli = [
            'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/StrugglingforNothingaudio.wav',
            'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/MoonRiveraudio.wav',
            'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/FamilysSongaudio.wav',
            'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/OscarsNewCameraaudio.wav',
            'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/Peaceaudio.wav'
        ]

        # Create a dictionary that maps the audio file names to their corresponding markers
        audio_markers = {
            'StrugglingforNothingaudio.wav': 'StrugglingforNothing',
            'MoonRiveraudio.wav': 'MoonRiver',
            'FamilysSongaudio.wav': 'FamilysSong',
            'OscarsNewCameraaudio.wav': 'OscarsNewCamera',
            'Peaceaudio.wav': 'Peace',
        }
                # Verify audio files exist
        missing_files = []
        for audio_file in audio_stimuli:
            if not os.path.exists(audio_file):
                missing_files.append(audio_file)

        # Setup PsychoPy window
        win = visual.Window(
            size=EXPERIMENT_CONFIG['WINDOW_SIZE'],
            fullscr=False,
            color=EXPERIMENT_CONFIG['WINDOW_COLOR'],
            units='pix'
        )
        message = visual.TextStim(
            win,
            text="",
            color=EXPERIMENT_CONFIG['TEXT_COLOR'],
            height=EXPERIMENT_CONFIG['TEXT_HEIGHT']
        )

        if missing_files:
            logging.error(f"The following audio files were not found: {missing_files}")
            message.setText(f"Error: Missing audio files.\nCheck the log for details.")
            message.draw()
            win.flip()
            event.waitKeys()
            cleanup(win, conn, server_socket, is_server, outlet)
            return

        # First establish network connection
        conn, server_socket = create_connection(is_server)

        # Then set up LSL stream
        info = pylsl.StreamInfo('MusicListening_Markers', 'Markers', 1, 0, 'string', 'myuid1234')
        outlet = pylsl.StreamOutlet(info)
        logging.info("LSL stream created successfully")

        # Main experiment execution
        message.setText("Preparando para comenzar...\nPresione cualquier tecla para iniciar.")
        message.draw()
        win.flip()
        event.waitKeys()

        random.shuffle(audio_stimuli)

        for i, stim in enumerate(audio_stimuli, start=1):
            if check_escape():
                break

            # Get the song name and marker name
            song_file = os.path.basename(stim)
            marker_name = audio_markers[song_file]
            
            # Keep trying to send start signal with song name
            conn, server_socket, sent = send_message(conn, f"START_{marker_name}", server_socket)
            if not sent:
                logging.warning(f"Could not send start signal for {marker_name} after maximum attempts")
            
            # Send start marker via LSL
            outlet.push_sample([markers[marker_name]['start']])
            logging.info(f'Sent marker: {markers[marker_name]["start"]}')
            
            message.setText(f"Reproduciendo canción {i} de {len(audio_stimuli)}")
            message.draw()
            win.flip()
            
            try:
                sound_file = sound.Sound(stim)
                duration = sound_file.getDuration()
                
                if duration <= EXPERIMENT_CONFIG['MIN_AUDIO_DURATION']:
                    raise ValueError(f"Invalid duration for audio file: {stim}")
                
                sound_file.play()
                
                # Monitor playback with escape check
                start_time = time.time()
                while time.time() - start_time < duration:
                    if check_escape():
                        sound_file.stop()  # Stop sound before raising exception
                        raise KeyboardInterrupt
                    core.wait(EXPERIMENT_CONFIG['CHECK_INTERVAL'])
                
            except Exception as e:
                logging.error(f'Error playing audio file: {e}')
                if sound_file:
                    try:
                        sound_file.stop()
                    except:
                        pass
                raise
            finally:
                if sound_file:
                    try:
                        sound_file.stop()
                    except:
                        pass
                    del sound_file
                    sound_file = None
            
            # Keep trying to send end signal with song name
            conn, server_socket, sent = send_message(conn, f"END_{marker_name}", server_socket)
            if not sent:
                logging.warning(f"Could not send end signal for {marker_name} after maximum attempts")
            
            # Send end marker via LSL
            outlet.push_sample([markers[marker_name]['end']])
            logging.info(f'Sent marker: {markers[marker_name]["end"]}')
            
            if i < len(audio_stimuli):
                start_time = time.time()
                while time.time() - start_time < EXPERIMENT_CONFIG['BREAK_DURATION']:
                    if check_escape():
                        raise KeyboardInterrupt
                    message.setText(f"Preparando próxima canción...\nEspere {EXPERIMENT_CONFIG['BREAK_DURATION']} segundos")
                    message.draw()
                    win.flip()
                    core.wait(EXPERIMENT_CONFIG['CHECK_INTERVAL'])

        # Display completion message
        message.setText("Experimento completado")
        message.draw()
        win.flip()
        
        # Play the bell sound to signal the end of the experiment
        play_bell_sound(win)  # Pass the window for visual fallback if needed
        
        # Display final thank you message
        message.setText("¡Gracias por participar!\n\nPresione cualquier tecla para salir.")
        message.draw()
        win.flip()
        event.waitKeys()

    except KeyboardInterrupt:
        logging.info("Experiment terminated by user")
    except Exception as e:
        logging.error(f"Error during experiment execution: {e}")
    finally:
        cleanup(win, conn, server_socket, is_server, outlet, sound_file)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        safe_quit()