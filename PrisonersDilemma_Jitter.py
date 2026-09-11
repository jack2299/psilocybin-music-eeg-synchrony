# PrisonersDilemma_Jitter.py
#
# Presentation script for the prisoner's dilemma task.
# Part of a double-blind, randomised psilocybin EEG study conducted at
# Universidad de Buenos Aires.
#
# Note: this task was piloted but not included in the final analysis because
# of movement artefact and session-order effects. It is included here for
# completeness and to document the task as it was run.
#
# Requirements:
#   - Python 3.9+
#   - psychopy
#   - pylsl
#   - pandas
#   - openpyxl
#   - pyserial
#   - matplotlib
#
# This script requires a matching partner script running on a second machine
# on the same local network. Set HOST below to the IP of the server machine.

import os
import time
import random
import socket
import logging
import datetime
import tkinter as tk
from tkinter import simpledialog

import pandas as pd
import pylsl
import matplotlib.pyplot as plt
from psychopy import prefs
prefs.hardware['audioLib'] = ['PTB']
from psychopy import visual, core, event

# =========================================================================
# EDIT ONLY THESE
# =========================================================================
HOST        = "<SERVER_IP>"          # e.g. "192.168.0.235"
PORT        = 65501
RESULTS_DIR = "path/to/results/folder"
# =========================================================================

if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

root = tk.Tk()
root.withdraw()

server_input = simpledialog.askstring("Modo de Conexión", "¿Es usted el servidor? (s/n):")
is_server = (server_input is not None and server_input.lower() == 's')

def exchange_data(conn, send_data=None, expect_response=True, timeout=15, max_retries=3):
    for attempt in range(max_retries):
        try:
            conn.settimeout(timeout)
            if send_data is not None:
                if isinstance(send_data, str):
                    send_data = send_data.encode()
                conn.sendall(send_data)
                logging.info(f"Sent: {send_data}")
            if expect_response:
                response = conn.recv(1024)
                if not response:
                    logging.warning(f"Empty response attempt {attempt+1}")
                    time.sleep(0.5)
                    continue
                logging.info(f"Received: {response}")
                return response
            return True
        except socket.timeout:
            logging.warning(f"Timeout attempt {attempt+1}")
            if attempt == max_retries - 1:
                return None
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"Error attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                return None
            time.sleep(0.5)
    return None

def create_connection(is_server):
    if is_server:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        try:
            s.bind((HOST, PORT))
            s.listen(1)
            logging.info("Waiting for connection...")
            while True:
                try:
                    conn, addr = s.accept()
                    logging.info(f"Connected to {addr}")
                    return conn
                except socket.timeout:
                    logging.info("Still waiting...")
        except Exception as e:
            logging.error(f"Server setup error: {e}")
            s.close()
            return None
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        try:
            logging.info(f"Connecting to {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            logging.info("Connected")
            return s
        except Exception as e:
            logging.error(f"Client connection error: {e}")
            s.close()
            return None

conn = create_connection(is_server)
if conn is None:
    logging.error("Failed to establish connection. Exiting...")
    core.quit()

info = pylsl.StreamInfo('PrisonersDilemma_Markers', 'Markers', 1, 500, 'string', 'myuid1234')
outlet = pylsl.StreamOutlet(info)

temp_win = visual.Window(size=(800, 600), fullscr=False, color='black', units='pix')
lsl_instruction = visual.TextStim(
    temp_win,
    text="Start the LSL recording\n\nPress spacebar to continue",
    color="white",
    height=30
)
lsl_instruction.draw()
temp_win.flip()
event.waitKeys(keyList=['space', 'escape'])
temp_win.close()

win = visual.Window(size=(800, 600), fullscr=True, color='black', units='pix')

instruction1 = visual.TextStim(
    win,
    text=("Bienvenido a la tarea del Dilema del Prisionero \n\n"
          "Por favor, intente moverse y hablar lo menos posible durante toda la tarea."
          " Podes apoyar las manos en el teclado para que te resulte más fácil presionar las teclas \n\n"
          "Presione cualquier tecla para continuar."),
    color="white", height=30, wrapWidth=700)

instruction2 = visual.TextStim(
    win,
    text=("Vos y tu compañero de estudio han sido acusados de un delito.\n\n"
          "Te encontrás detenido en una comisaría, esperando el interrogatorio. "
          "Te informaron que enfrentarás una condena en prisión, pero la duración "
          "dependerá de tus acciones durante el proceso de interrogatorio.\n\n"
          "Presioná cualquier tecla para continuar."),
    color="white", height=30, wrapWidth=700)

instruction3 = visual.TextStim(
    win,
    text=("El Proceso de Interrogatorio\n\n"
          "Tendrás la oportunidad de cooperar con tu cómplice o traicionarlo. "
          "El resultado de tu decisión dependerá de la acción de tu cómplice.\n\n"
          "Presione cualquier tecla para continuar."),
    color="white", height=30, wrapWidth=700)

instruction4 = visual.TextStim(
    win,
    text=("Si ambos cooperan, cada uno recibirá una condena de 1 año.\n"
          "Si cooperas y tu cómplice te traiciona, recibirás 3 años y tu cómplice 0 años.\n"
          "Si traicionas y tu cómplice coopera, recibirás 0 años mientras que tu cómplice recibirá 3 años.\n"
          "Si ambos se traicionan, ambos recibirán 2 años.\n\n"
          "Presione cualquier tecla para continuar."),
    color="white", height=30, wrapWidth=700)

instruction5 = visual.TextStim(
    win,
    text=("El interrogatorio consistirá en 30 rondas, y tu objetivo es minimizar tu condena. "
          "Después de cada ronda, serás informado sobre el resultado de tu decisión y la de tu cómplice. "
          "Al final, recibirás una condena igual al total de años acumulados.\n\n"
          "Presione cualquier tecla para continuar."),
    color="white", height=30, wrapWidth=700)

instruction6 = visual.TextStim(
    win,
    text=("Cómo Tomar Tu Decisión\n\n"
          "Al comienzo de cada ronda, verás un mensaje. "
          "Presiona la tecla izquierda para cooperar o la tecla derecha para traicionar. "
          "Ten en cuenta que la asignación de teclas puede cambiar en cada ronda, "
          "así que lee las instrucciones cuidadosamente.\n\n"
          "Presione cualquier tecla para continuar."),
    color="white", height=30, wrapWidth=700)

instruction7 = visual.TextStim(win, text="Presione cualquier tecla para continuar.",
                               color="white", height=30, wrapWidth=700)
instruction8 = visual.TextStim(win, text="Presione cualquier tecla para continuar.",
                               color="white", height=30, wrapWidth=700)

pre_fixation = visual.TextStim(
    win, text="Presione cualquier tecla para comenzar la ronda.",
    color="white", height=30, wrapWidth=700)

pre_choice = visual.TextStim(
    win, text="Presione cualquier tecla para ver las opciones.",
    color="white", height=30, wrapWidth=700)

pre_consequence = visual.TextStim(
    win, text="Presione cualquier tecla para ver los resultados.",
    color="white", height=30, wrapWidth=700)

def display_text_and_wait(text_stim, timeout=None):
    try:
        text_stim.draw()
        win.flip()
        logging.info("Displaying text and waiting for key press...")
        if timeout:
            keys = event.waitKeys(maxWait=timeout, keyList=None)
            if keys is None:
                logging.info(f"Timeout of {timeout} seconds reached with no response")
                return False
            return True
        else:
            event.waitKeys()
            return True
    except Exception as e:
        logging.error(f"An error occurred in display_text_and_wait: {e}")
        cleanup_and_exit()
        return False

def cleanup_and_exit():
    try:
        win.close()
        if conn:
            if is_server:
                try:
                    exchange_data(conn, send_data='end', expect_response=False, timeout=5, max_retries=2)
                except Exception:
                    pass
            conn.close()
        core.quit()
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")
        core.quit()

try:
    display_text_and_wait(instruction1)
    display_text_and_wait(instruction2)
    display_text_and_wait(instruction3)
    display_text_and_wait(instruction4)
    display_text_and_wait(instruction5)
    display_text_and_wait(instruction6)
    display_text_and_wait(instruction7)
    display_text_and_wait(instruction8)
except Exception as e:
    logging.error(f"Error during instructions: {e}")
    cleanup_and_exit()

nRounds = 30
you_total = 0
other_prisoner_total = 0
results = []

fixation_cross = visual.TextStim(win, text="+", color="white", height=30)
trialText = visual.TextStim(win, text="", color="white", height=30, wrapWidth=700)

key_press_times = []
lsl_marker_times = []

for trial in range(1, nRounds + 1):
    try:
        logging.info(f"Starting trial {trial}")

        if not display_text_and_wait(pre_fixation, timeout=60):
            logging.warning("No response during pre-fixation.")
        outlet.push_sample([f'Round{trial}_Fixation'])
        logging.info("Manual Marker: Fixation")

        fixation_cross.draw()
        win.flip()
        core.wait(5)

        if not display_text_and_wait(pre_choice, timeout=60):
            logging.warning("No response during pre-choice.")
        outlet.push_sample([f'Round{trial}_Choice'])
        logging.info("Manual Marker: Choice")

        try:
            if is_server:
                t0 = time.time()
                response = exchange_data(conn, send_data='ping', expect_response=True)
                if not response:
                    raise ValueError("No response to ping")
                if response != b'pong':
                    raise ValueError(f"Unexpected response to ping: {response}")
                t1 = time.time()
                latency = (t1 - t0) / 2
                exchange_data(conn, send_data=f'start,{latency}', expect_response=False)
            else:
                data = exchange_data(conn, send_data=None, expect_response=True)
                if not data:
                    raise ValueError("No ping received")
                if data != b'ping':
                    raise ValueError(f"Unexpected data: {data}")
                exchange_data(conn, send_data='pong', expect_response=False)
                data = exchange_data(conn, send_data=None, expect_response=True)
                if data and b',' in data:
                    _, latency = data.decode().split(',')
                    core.wait(float(latency))
        except Exception as e:
            logging.error(f"Synchronization error: {e}")
            cleanup_and_exit()

        random_key_mapping = random.choice(['left_coop', 'right_coop'])
        if random_key_mapping == 'left_coop':
            trialText.setText(f"Ronda {trial} de {nRounds}\n\nPresione tecla IZQUIERDA para cooperar\nPresione tecla DERECHA para traicionar")
        else:
            trialText.setText(f"Ronda {trial} de {nRounds}\n\nPresione tecla IZQUIERDA para traicionar\nPresione tecla DERECHA para cooperar")

        trialText.draw()
        win.flip()

        keys = event.waitKeys(maxWait=60, keyList=['left', 'right', 'escape'])
        key_time = core.getTime()
        if keys is None:
            logging.warning("No key pressed. Defaulting to 'cooperate'.")
            your_choice = 'left' if random_key_mapping == 'left_coop' else 'right'
        elif 'escape' in keys:
            logging.info("Escape pressed. Exiting...")
            cleanup_and_exit()
        else:
            your_choice = keys[0]

        key_press_times.append(key_time)

        lsl_marker_times.append(pylsl.local_clock())
        outlet.push_sample([f'Round{trial}_ChoiceMade'])
        logging.info("Manual Marker: Choice made")

        your_coop = ((random_key_mapping == 'left_coop' and your_choice == 'left') or
                     (random_key_mapping == 'right_coop' and your_choice == 'right'))

        try:
            if is_server:
                exchange_data(conn, send_data='cooperate' if your_coop else 'betray', expect_response=False)
                other_choice = exchange_data(conn, send_data=None, expect_response=True)
            else:
                other_choice = exchange_data(conn, send_data=None, expect_response=True)
                exchange_data(conn, send_data='cooperate' if your_coop else 'betray', expect_response=False)
            if other_choice:
                other_choice = other_choice.decode().strip()
                if other_choice == 'end':
                    logging.info("Server ended game.")
                    cleanup_and_exit()
                other_coop = (other_choice == 'cooperate')
        except Exception as e:
            logging.error(f"Choice exchange error: {e}")
            cleanup_and_exit()

        if not display_text_and_wait(pre_consequence, timeout=60):
            logging.warning("No response during pre-consequence.")
        outlet.push_sample([f'Round{trial}_Consequence'])
        logging.info("Manual Marker: Consequence")

        if your_coop and other_coop:
            outcome = ("¡Ambos cooperaron!\nRecibes 1 año.\nEl otro prisionero recibe 1 año.")
            your_years, other_years = 1, 1
        elif your_coop and not other_coop:
            outcome = ("Cooperaste, pero el otro prisionero te traicionó.\nRecibes 3 años.\nEl otro recibe 0 años.")
            your_years, other_years = 3, 0
        elif not your_coop and other_coop:
            outcome = ("Traicionaste, el otro cooperó.\nRecibes 0 años.\nEl otro recibe 3 años.")
            your_years, other_years = 0, 3
        else:
            outcome = ("Ambos se traicionaron.\n2 años cada uno.")
            your_years, other_years = 2, 2

        you_total += your_years
        other_prisoner_total += other_years
        results.append({
            'Round': trial,
            'Your Choice': 'Cooperar' if your_coop else 'Traicionar',
            'Other Choice': 'Cooperar' if other_coop else 'Traicionar',
            'Your Years': your_years,
            'Other Years': other_years
        })

        trialText.setText(outcome)
        trialText.draw()
        win.flip()
        core.wait(3)

        trialText.setText(outcome + "\n\nPresione cualquier tecla para continuar.")
        trialText.draw()
        win.flip()
        event.waitKeys(maxWait=60)
    except Exception as e:
        logging.error(f"Error during trial {trial}: {e}")
        cleanup_and_exit()

if is_server:
    try:
        current_date = datetime.datetime.now()
        date_string = current_date.strftime("%Y-%m-%d_%H-%M-%S")
        session_number = 1
        participant_letter = 'A'
        filename = os.path.join(
            RESULTS_DIR,
            f"Psilocouples_{date_string}_{participant_letter}_session{session_number}.xlsx"
        )
        df = pd.DataFrame(results)
        df.to_excel(filename, index=False)
        logging.info(f"Results saved to {filename}")
    except Exception as e:
        logging.error(f"Failed to save results: {e}")

try:
    finalMessage = ("¡Juego terminado!\n\n"
                    f"Tu condena total: {you_total} años\n"
                    f"Condena total del otro prisionero: {other_prisoner_total} años\n\n"
                    "Presione cualquier tecla para salir.")
    trialText.setText(finalMessage)
    trialText.draw()
    win.flip()
    event.waitKeys(maxWait=60)
except Exception as e:
    logging.error(f"Error displaying final message: {e}")

try:
    if key_press_times and lsl_marker_times and len(key_press_times) == len(lsl_marker_times):
        jitter = [k - l for k, l in zip(key_press_times, lsl_marker_times)]
        plt.hist(jitter, bins=50)
        plt.xlabel('Key press time - LSL marker time (seconds)')
        plt.ylabel('Count')
        plt.title('Jitter between Keypress and LSL Marker')

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        plt.savefig(os.path.join(RESULTS_DIR, f"jitter_plot_{timestamp}.png"))
        plt.show()
    else:
        logging.warning("Mismatch in jitter lists - jitter plot skipped.")
except Exception as e:
    logging.error(f"Error plotting jitter: {e}")

try:
    win.close()
    if conn:
        if is_server:
            try:
                exchange_data(conn, send_data='end', expect_response=False)
            except Exception:
                pass
        conn.close()
    logging.info("Experiment completed successfully")
except Exception as e:
    logging.error(f"Error during final cleanup: {e}")
finally:
    core.quit()
