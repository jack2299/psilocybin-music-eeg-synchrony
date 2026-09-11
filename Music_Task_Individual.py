# Music_Task_Individual.py
#
# Presentation script for the individual music listening task.
# Part of a double-blind, randomised psilocybin EEG study conducted at
# Universidad de Buenos Aires.
#
# Participants listen to a set of music tracks while EEG is recorded.
# After each track, they answer five subjective rating questions.
#
# Requirements:
#   - Python 3.9+
#   - psychopy
#   - pylsl
#   - pandas
#   - openpyxl (for Excel output)
#
# Audio files are not redistributed with this repository. Supply your own
# audio files in the folder specified below, using the filenames listed in
# the SONGS dictionary. A bell sound file (Bell.wav) is also required.

import os
import random
import logging
import time
import tkinter as tk
from tkinter import simpledialog

import pandas as pd
import pylsl
from psychopy import prefs
prefs.hardware['audioLib'] = ['pygame']
from psychopy import sound, core, event, visual, gui

# =========================================================================
# EDIT ONLY THESE PATHS AND FILENAMES
# =========================================================================
AUDIO_DIR = "path/to/audio/folder"

SONGS = {
    "StrugglingforNothing": "StrugglingforNothingaudio.wav",
    "MoonRiver":            "MoonRiveraudio.wav",
    "FamilysSong":          "FamilysSongaudio.wav",
    "OscarsNewCamera":      "OscarsNewCameraaudio.wav",
    "Peace":                "Peaceaudio.wav",
}

BELL_SOUND = "Bell.wav"
# =========================================================================

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------------------
# Participant and session info
# -------------------------------------------------------------------------
exp_info = {
    'Participant ID': '',
    'Session': ['01', '02'],
}
dlg = gui.DlgFromDict(dictionary=exp_info, title='Music Listening Task', sortKeys=False)
if not dlg.OK:
    core.quit()

if len(exp_info['Participant ID']) == 1:
    exp_info['Participant ID'] = '0' + exp_info['Participant ID']
elif len(exp_info['Participant ID']) > 2:
    exp_info['Participant ID'] = exp_info['Participant ID'][:2]

# -------------------------------------------------------------------------
# LSL stream
# -------------------------------------------------------------------------
info = pylsl.StreamInfo('MusicListeningIndividual', 'Markers', 1, 500, 'string', 'myuid1234')
outlet = pylsl.StreamOutlet(info)
logging.info("LSL outlet created successfully")

# -------------------------------------------------------------------------
# Window
# -------------------------------------------------------------------------
win = visual.Window(size=(1024, 768), fullscr=False, color='black', units='norm')

setup_text = visual.TextStim(
    win,
    text=("LSL stream created.\n\nPlease start the EEG recording now.\n\n"
          "Press SPACE when recording has started to continue in fullscreen."),
    color='white', wrapWidth=1.6, height=0.07)

waiting_for_setup = True
while waiting_for_setup:
    setup_text.draw()
    win.flip()
    keys = event.getKeys(keyList=['space', 'escape'])
    if 'space' in keys:
        waiting_for_setup = False
    elif 'escape' in keys:
        win.close()
        core.quit()
    core.wait(0.01)

win.fullscr = True
win.winHandle.set_fullscreen(True)
win.flip()

# -------------------------------------------------------------------------
# Markers
# -------------------------------------------------------------------------
markers = {name: {'start': f'{name}_start', 'end': f'{name}_end'} for name in SONGS.keys()}

# -------------------------------------------------------------------------
# Load bell sound (fallback to synthetic tone if missing)
# -------------------------------------------------------------------------
bell_sound_path = os.path.join(AUDIO_DIR, BELL_SOUND)
try:
    audio_cue = sound.Sound(bell_sound_path)
    logging.info(f"Bell sound loaded from: {bell_sound_path}")
except Exception as e:
    logging.error(f"Failed to load bell sound: {e}")
    audio_cue = sound.Sound('G', octave=4, secs=0.3)
    logging.info("Using fallback synthetic tone")

# -------------------------------------------------------------------------
# Questionnaire
# -------------------------------------------------------------------------
questions = [
    {
        'name': 'Familiaridad',
        'instruction': """Familiaridad:
Usá la escala para reportar tu nivel de familiaridad con el tema que escuchaste.

La escala va desde nada familiar a muy familiar.

En un extremo, no conocías nada de la canción, no la habías escuchado nunca antes.
En el otro extremo, reconocías la canción y estabas muy familiarizado/a con ella, la habías escuchado muchas veces.

Podés elegir cualquier punto intermedio para expresar tu nivel de familiaridad con el tema.""",
        'left_label': 'Nada familiar',
        'right_label': 'Muy familiar'
    },
    {
        'name': 'Valencia',
        'instruction': """Valencia emocional: ¿Cómo percibís las emociones que esta pieza quiso transmitir?

Primero evaluaremos el nivel de valencia emocional que creés que la música intenta evocar. Pensá en las emociones que esta pieza parece querer transmitir.

La escala va desde muy negativa a muy positiva:

En un extremo, puede transmitir emociones negativas como tristeza, enojo o desesperanza.
En el otro extremo, puede transmitir emociones positivas como felicidad, tranquilidad o esperanza.

Importante: No tiene que coincidir con cómo te sentiste, sino con la intención emocional que creés que la música quiso comunicar.

Podés elegir cualquier punto intermedio para expresar cómo percibís la emoción que la música quiso transmitir, independientemente de si coincide con lo que te hizo sentir mientras la escuchabas.""",
        'left_label': 'Muy negativo',
        'right_label': 'Muy positivo'
    },
    {
        'name': 'Gusto',
        'instruction': """Gusto: ¿Cuánto te gustó a vos esta pieza?

En la siguiente pregunta evaluaremos cuánto disfrutaste vos personalmente esta música. Pensá en cuánto te gustó esta pieza en particular.

La escala va desde No me gustó nada a Me encantó:

En un extremo, puede no haberte gustado nada porque te resultó aburrida, desagradable o poco atractiva.
En el otro extremo, puede haberte encantado porque la encontraste interesante, agradable o cautivadora.

Importante: Acá no importa lo que quiso transmitir la pieza, sino tu apreciación personal, que puede depender de otros aspectos musicales más allá de las emociones evocadas.""",
        'left_label': 'No me gustó nada',
        'right_label': 'Me encantó'
    },
    {
        'name': 'Intensidad emocional',
        'instruction': """Arousal (intensidad emocional):
Usá la escala para reportar tu nivel de activación emocional mientras escuchabas el tema.

La escala va desde calmado/a a emocionado/a.

En un extremo, te sentías relajado/a, tranquilo/a, inactivo/a, aburrido/a, somnoliento/a, no excitado/a.
En el otro extremo, te sentías completamente estimulado/a, emocionado/a, frenético/a, nervioso/a, despierto/a, despabilado/a.

Podés elegir cualquier punto intermedio para expresar cómo te sentiste mientras escuchabas el tema.""",
        'left_label': 'Calmado',
        'right_label': 'Emocionado'
    },
    {
        'name': 'Involucramiento',
        'instruction': """Engagement (involucramiento):
Usá la escala para reportar tu nivel de engagement (involucramiento) mientras escuchabas el tema.

La escala va desde desconectado/a a totalmente absorbido/a.

En un extremo, te sentías distraído/a, poco interesado/a, sin conexión con el tema.
En el otro extremo, te sentías totalmente concentrado/a, involucrado/a, absorbido/a, interesado/a en el tema.

Podés elegir cualquier punto intermedio para expresar tu nivel de engagement mientras escuchabas el tema.""",
        'left_label': 'Desconectado/a',
        'right_label': 'Absorbido/a'
    }
]

# -------------------------------------------------------------------------
# Response storage
# -------------------------------------------------------------------------
responses = {
    'participant': [],
    'session': [],
    'song': [],
    'question': [],
    'rating': [],
    'rt': []
}

# -------------------------------------------------------------------------
# Bell sound function
# -------------------------------------------------------------------------
def play_bell_sound():
    logging.info("Attempting to play bell sound")
    success = False
    core.wait(0.5)
    for attempt in range(5):
        try:
            audio_cue.play()
            logging.info(f"Bell sound played - attempt {attempt+1}")
            core.wait(0.5)
            success = True
        except Exception as e:
            logging.error(f"Error playing bell sound (attempt {attempt+1}): {e}")
            core.wait(0.2)
    if not success:
        logging.warning("Using visual fallback for bell sound")
        flash = visual.Rect(win, width=2, height=2, fillColor='white')
        for _ in range(3):
            flash.draw()
            win.flip()
            core.wait(0.2)
            win.flip()
            core.wait(0.2)
    return success

# -------------------------------------------------------------------------
# Question presentation
# -------------------------------------------------------------------------
def present_question(song_name, question_data):
    win.flip()

    instruction = visual.TextStim(win, text=question_data['instruction'],
                                  color='white', wrapWidth=1.6, height=0.07,
                                  alignText='left')
    instruction.draw()
    win.flip()

    continue_prompt = visual.TextStim(win,
                                      text="Presiona la barra espaciadora para continuar",
                                      color='white', pos=(0, -0.8), height=0.05)

    waiting_for_response = True
    while waiting_for_response:
        instruction.draw()
        continue_prompt.draw()
        win.flip()
        keys = event.getKeys(keyList=['space', 'escape'])
        if 'space' in keys:
            waiting_for_response = False
        elif 'escape' in keys:
            win.close()
            core.quit()
        core.wait(0.01)

    win.flip()
    message = visual.TextStim(win, text=question_data['name'],
                              color='white', pos=(0, 0.7), height=0.14)

    try:
        slider = visual.Slider(
            win,
            ticks=(1, 2, 3, 4, 5, 6, 7, 8, 9),
            labels=(question_data['left_label'], question_data['right_label']),
            pos=(0, -0.4),
            size=(1.5, 0.05),
            granularity=1,
            style='rating',
            color='white',
            fillColor='white',
            borderColor='white',
            labelColor='white',
            labelHeight='0.05',
            startValue=5
        )
    except Exception as e:
        logging.error(f"Error creating Slider: {e}. Using fallback.")
        slider = visual.Slider(
            win,
            ticks=[1, 2, 3, 4, 5, 6, 7, 8, 9],
            labels=[question_data['left_label'], question_data['right_label']],
            pos=(0, -0.4),
            size=(1.5, 0.05),
            granularity=1,
            color='white',
            fillColor='white',
            borderColor='white',
            startValue=5
        )

    instruction_line1 = visual.TextStim(
        win,
        text="Usa el touchpad y hacé clic para seleccionar una opción en el deslizador",
        color='white', pos=(0, 0.2), height=0.05, alignHoriz='center')

    instruction_line2 = visual.TextStim(
        win,
        text="Selecciona un valor y presiona ESPACIO",
        color='white', pos=(0, 0.1), height=0.04, alignHoriz='center')

    clock = core.Clock()
    has_responded = False
    while not has_responded:
        message.draw()
        slider.draw()
        if slider.getRating() is not None:
            instruction_line2.text = "Presiona ESPACIO para continuar"
        else:
            instruction_line2.text = "Selecciona un valor y presiona ESPACIO"
        instruction_line1.draw()
        instruction_line2.draw()
        win.flip()
        keys = event.getKeys(keyList=['space', 'escape'])
        if 'space' in keys and slider.getRating() is not None:
            has_responded = True
        elif 'escape' in keys:
            win.close()
            core.quit()

    rating = slider.getRating()
    rt = clock.getTime()

    responses['participant'].append(exp_info['Participant ID'])
    responses['session'].append(exp_info['Session'])
    responses['song'].append(song_name)
    responses['question'].append(question_data['name'])
    responses['rating'].append(rating)
    responses['rt'].append(rt)

    return rating, rt

# -------------------------------------------------------------------------
# Welcome screen
# -------------------------------------------------------------------------
welcome = visual.TextStim(
    win,
    text=("Bienvenido a al experimento de escucha musical.\n\n"
          "Cierra los ojos mientras escuchas cada canción.\n\n"
          "Cuando escuches un sonido suave, abre los ojos y responde las preguntas."),
    color='white', wrapWidth=1.6, height=0.07)

continue_prompt = visual.TextStim(
    win,
    text="Presiona la barra espaciadora para comenzar",
    color='white', pos=(0, -0.8), height=0.05)

waiting_for_start = True
while waiting_for_start:
    welcome.draw()
    continue_prompt.draw()
    win.flip()
    keys = event.getKeys(keyList=['space', 'escape'])
    if 'space' in keys:
        waiting_for_start = False
    elif 'escape' in keys:
        win.close()
        core.quit()
    core.wait(0.01)

win.flip()
core.wait(3)

# -------------------------------------------------------------------------
# Build audio stimulus list from SONGS dictionary
# -------------------------------------------------------------------------
audio_stimuli = []
for marker_name, filename in SONGS.items():
    audio_stimuli.append({
        'marker': marker_name,
        'path':   os.path.join(AUDIO_DIR, filename),
    })

random.shuffle(audio_stimuli)

# -------------------------------------------------------------------------
# Main task loop
# -------------------------------------------------------------------------
for i, stim in enumerate(audio_stimuli, start=1):
    marker_name = stim['marker']
    song_name = marker_name

    instruction = visual.TextStim(
        win,
        text=(f"Canción {i} de {len(audio_stimuli)}\n\n"
              "Cierra los ojos y escucha atentamente.\n\n"
              "Abrirás los ojos cuando escuches un sonido suave."),
        color='white', wrapWidth=1.6, height=0.07)
    instruction.draw()
    win.flip()
    core.wait(5)
    win.flip()

    outlet.push_sample([markers[marker_name]['start']])
    logging.info(f'Sent start marker: {markers[marker_name]["start"]}')

    try:
        sound_file = sound.Sound(stim['path'])
        sound_file.play()
        logging.info(f'Playing: {stim["path"]}')
        core.wait(sound_file.getDuration())
    except Exception as e:
        logging.error(f'Error playing audio: {e}')
        continue

    outlet.push_sample([markers[marker_name]['end']])
    logging.info(f'Sent end marker: {markers[marker_name]["end"]}')

    play_bell_sound()

    for question in questions:
        rating, rt = present_question(song_name, question)
        logging.info(f"Song: {song_name}, Question: {question['name']}, Rating: {rating}, RT: {rt}")

    if i < len(audio_stimuli):
        next_song = visual.TextStim(
            win,
            text="Prepárate para la siguiente canción.",
            color='white', wrapWidth=1.6, height=0.07)
        continue_prompt = visual.TextStim(
            win,
            text="Presiona la barra espaciadora cuando estés listo/a",
            color='white', pos=(0, -0.8), height=0.05)

        waiting_for_next = True
        while waiting_for_next:
            next_song.draw()
            continue_prompt.draw()
            win.flip()
            keys = event.getKeys(keyList=['space', 'escape'])
            if 'space' in keys:
                waiting_for_next = False
            elif 'escape' in keys:
                win.close()
                core.quit()
            core.wait(0.01)

        win.flip()
        core.wait(7)

# -------------------------------------------------------------------------
# Save responses
# -------------------------------------------------------------------------
df = pd.DataFrame(responses)
script_dir = os.path.dirname(os.path.abspath(__file__))
excel_filename = f"music_listening_P{exp_info['Participant ID']}_S{exp_info['Session']}.xlsx"
excel_path = os.path.join(script_dir, excel_filename)
df.to_excel(excel_path, index=False)
logging.info(f"Responses saved to {excel_path}")

thanks = visual.TextStim(
    win,
    text="Gracias por participar en la tarea de escucha de música.",
    color='white', wrapWidth=1.6, height=0.07)
thanks.draw()
win.flip()
core.wait(7)

win.close()
