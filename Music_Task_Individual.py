import pylsl
import time
import tkinter as tk
from tkinter import simpledialog
import random
import os
import pandas as pd
from psychopy import prefs
prefs.hardware['audioLib'] = ['pygame']  # Using pygame instead of PTB for better compatibility
from psychopy import sound, core, event, visual, gui
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Get participant ID and session number
exp_info = {
    'Participant ID': '',
    'Session': ['01', '02']
}
dlg = gui.DlgFromDict(dictionary=exp_info, title='Music Listening Task', 
                      sortKeys=False)
if not dlg.OK:
    core.quit()  # User pressed cancel

# Ensure participant ID is in XX format
if len(exp_info['Participant ID']) == 1:
    exp_info['Participant ID'] = '0' + exp_info['Participant ID']
elif len(exp_info['Participant ID']) > 2:
    exp_info['Participant ID'] = exp_info['Participant ID'][:2]

# Initialize tkinter and hide its root window
root = tk.Tk()
root.withdraw()

# Create an LSL stream
info = pylsl.StreamInfo('MusicListeningIndividual', 'Markers', 1, 500, 'string', 'myuid1234')
outlet = pylsl.StreamOutlet(info)
logging.info("LSL outlet created successfully")

# Create window initially in windowed mode
win = visual.Window(size=(1024, 768), fullscr=False, color='black', units='norm')

# Display instructions to start recording
setup_text = visual.TextStim(win, 
                           text="LSL stream created.\n\nPlease start the Smarting EEG recording now.\n\nPress SPACE when recording has started to continue in fullscreen.", 
                           color='white', wrapWidth=1.6, height=0.07)

# Wait for experimenter to set up recording
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

# Switch to fullscreen mode
win.fullscr = True
win.winHandle.set_fullscreen(True)
win.flip()

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

# Define the audio stimuli (hardcoded paths)
audio_stimuli = [
    'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/StrugglingforNothingaudio.wav',
    'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/MoonRiveraudio.wav',
    'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/FamilysSongaudio.wav',
    'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/OscarsNewCameraaudio.wav',
    'C:/Users/Jack/.ms-ad/Documents/Music_task_Synchrony/Peaceaudio.wav'
]

# Get the directory of the audio files
audio_dir = os.path.dirname(audio_stimuli[0])

# Define the bell sound file path (in the same directory as music stimuli)
bell_sound_path = os.path.join(audio_dir, 'Bell.wav')

# Preload the bell sound - removed volume parameter
try:
    audio_cue = sound.Sound(bell_sound_path)  # Removed volume parameter
    logging.info(f"Bell sound loaded from: {bell_sound_path}")
except Exception as e:
    logging.error(f"Failed to load bell sound: {e}")
    # Fallback to synthetic tone if bell sound fails to load
    audio_cue = sound.Sound('G', octave=4, secs=0.3)
    logging.info("Using fallback synthetic tone")

# Create a dictionary that maps the audio file names to their corresponding markers
audio_markers = {
    'StrugglingforNothingaudio.wav': 'StrugglingforNothing',
    'MoonRiveraudio.wav': 'MoonRiver',
    'FamilysSongaudio.wav': 'FamilysSong',
    'OscarsNewCameraaudio.wav': 'OscarsNewCamera',
    'Peaceaudio.wav': 'Peace',
}

# Define the questions and their detailed instructions
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



# Create a data structure to store responses
responses = {
    'participant': [],
    'session': [],
    'song': [],
    'question': [],
    'rating': [],
    'rt': []
}

# Function to play the bell sound reliably
def play_bell_sound():
    logging.info("Attempting to play bell sound")
    success = False
    
    # Add a small delay before playing the bell
    core.wait(0.5)
    
    # Try to play the bell sound multiple times to ensure it's heard
    for attempt in range(5):
        try:
            audio_cue.play()
            logging.info(f"Bell sound played - attempt {attempt+1}")
            # Force wait to ensure sound plays completely
            core.wait(0.5)
            success = True
        except Exception as e:
            logging.error(f"Error playing bell sound (attempt {attempt+1}): {e}")
            core.wait(0.2)  # Short wait before retry
    
    # Visual fallback if audio completely fails
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
    
# Function to present a question and get a response
def present_question(song_name, question_data):
    win.flip()
    
    # Display the instruction text with improved readability - white text on black background
    instruction = visual.TextStim(win, text=question_data['instruction'], 
                                 color='white', wrapWidth=1.6, height=0.07,
                                 alignText='left')
    instruction.draw()
    win.flip()
    
    # More reliable way to wait for spacebar
    continue_prompt = visual.TextStim(win, 
                                     text="Presiona la barra espaciadora para continuar", 
                                     color='white', pos=(0, -0.8), height=0.05)
    
    # Wait for participant to read the instructions with more reliable spacebar detection
    waiting_for_response = True
    while waiting_for_response:
        instruction.draw()
        continue_prompt.draw()
        win.flip()
        
        # Check for key presses
        keys = event.getKeys(keyList=['space', 'escape'])
        if 'space' in keys:
            waiting_for_response = False
        elif 'escape' in keys:
            win.close()
            core.quit()
        
        # Short wait to prevent CPU overload
        core.wait(0.01)
    
    # Display the rating scale
    win.flip()
    message = visual.TextStim(win, text=question_data['name'], 
                             color='white', pos=(0, 0.7), height=0.14)
    
    # Create a slider (modern replacement for RatingScale)
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
            startValue=5  # Start at middle value
        )
    except Exception as e:
        # Fallback for older PsychoPy versions
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
            startValue=5  # Start at middle value
        )
    
    # Create custom instruction texts that are white, centered, and slightly above center
    # First line: "Hacé una elección eligiendo un número"
    instruction_line1 = visual.TextStim(
        win,
        text="Usa el touchpad y hacé clic para seleccionar una opción en el deslizador",
        color='white',
        pos=(0, 0.2),  # Slightly above center
        height=0.05,   # 20% smaller than standard text
        alignHoriz='center'
    )
    
    # Second line: "Selecciona un valor y presiona ESPACIO"
    instruction_line2 = visual.TextStim(
        win,
        text="Selecciona un valor y presiona ESPACIO",
        color='white',
        pos=(0, 0.1),  # Slightly above center, below the first line
        height=0.04,   # 20% smaller than standard text
        alignHoriz='center'
    )
    
    # Track response time
    clock = core.Clock()
    
    # Wait for response
    has_responded = False
    while not has_responded:
        message.draw()
        slider.draw()
        
        # Draw our custom instruction text
        if slider.getRating() is not None:
            instruction_line2.text = "Presiona ESPACIO para continuar"
        else:
            instruction_line2.text = "Selecciona un valor y presiona ESPACIO"
        
        instruction_line1.draw()
        instruction_line2.draw()
        
        win.flip()
        
        # Check for spacebar press if a rating has been selected
        keys = event.getKeys(keyList=['space', 'escape'])
        if 'space' in keys and slider.getRating() is not None:
            has_responded = True
        elif 'escape' in keys:
            win.close()
            core.quit()
    
    # Get and store the response
    rating = slider.getRating()
    rt = clock.getTime()
    
    # Store the data
    responses['participant'].append(exp_info['Participant ID'])
    responses['session'].append(exp_info['Session'])
    responses['song'].append(song_name)
    responses['question'].append(question_data['name'])
    responses['rating'].append(rating)
    responses['rt'].append(rt)
    
    return rating, rt
    
# Display welcome message with more reliable spacebar detection
welcome = visual.TextStim(win, 
                         text="Bienvenido a al experimento de escucha musical.\n\nCierra los ojos mientras escuchas cada canción.\n\nCuando escuches un sonido suave, abre los ojos y responde las preguntas.", 
                         color='white', wrapWidth=1.6, height=0.07)
continue_prompt = visual.TextStim(win, 
                                 text="Presiona la barra espaciadora para comenzar", 
                                 color='white', pos=(0, -0.8), height=0.05)

# More reliable way to wait for spacebar at the welcome screen
waiting_for_start = True
while waiting_for_start:
    welcome.draw()
    continue_prompt.draw()
    win.flip()
    
    # Check for key presses
    keys = event.getKeys(keyList=['space', 'escape'])
    if 'space' in keys:
        waiting_for_start = False
    elif 'escape' in keys:
        win.close()
        core.quit()
    
    # Short wait to prevent CPU overload
    core.wait(0.01)

# Pause for 3 seconds before starting the experiment
win.flip()  # Clear screen
core.wait(3)

# Shuffle the audio stimuli list
random.shuffle(audio_stimuli)

# Play the audio stimuli
for i, stim in enumerate(audio_stimuli, start=1):
    # Get the song name
    song_file = stim.split('/')[-1]
    marker_name = audio_markers[song_file]
    song_name = marker_name  # Use the marker name as the song name
    
    # Display instruction to close eyes with more reliable spacebar detection
    instruction = visual.TextStim(win, 
                                 text=f"Canción {i} de 5\n\nCierra los ojos y escucha atentamente.\n\nAbrirás los ojos cuando escuches un sonido suave.", 
                                 color='white', wrapWidth=1.6, height=0.07)
    instruction.draw()
    win.flip()
    core.wait(5)  # Give them time to read
    
    # Clear the screen
    win.flip()
    
    # Send start marker via LSL
    outlet.push_sample([markers[marker_name]['start']])
    logging.info(f'Sent start marker: {markers[marker_name]["start"]}')

    # Play audio
    try:
        sound_file = sound.Sound(stim)
        sound_file.play()
        logging.info(f'Playing: {stim}')
        core.wait(sound_file.getDuration())  # Wait for audio to finish
    except Exception as e:
        logging.error(f'Error playing audio: {e}')
        continue  # Skip to next song

    # Send end marker via LSL
    outlet.push_sample([markers[marker_name]['end']])
    logging.info(f'Sent end marker: {markers[marker_name]["end"]}')
    
    # Play the bell sound to signal it's time to open eyes and answer questions
    play_bell_sound()
    
    # Present each question one at a time
    for question in questions:
        rating, rt = present_question(song_name, question)
        logging.info(f"Song: {song_name}, Question: {question['name']}, Rating: {rating}, RT: {rt}")
    
    # If not the last song, show a message before the next song with more reliable spacebar detection
    if i < len(audio_stimuli):
        next_song = visual.TextStim(win, 
                                   text="Prepárate para la siguiente canción.", 
                                   color='white', wrapWidth=1.6, height=0.07)
        continue_prompt = visual.TextStim(win, 
                                         text="Presiona la barra espaciadora cuando estés listo/a", 
                                         color='white', pos=(0, -0.8), height=0.05)
        
        # More reliable way to wait for spacebar
        waiting_for_next = True
        while waiting_for_next:
            next_song.draw()
            continue_prompt.draw()
            win.flip()
            
            # Check for key presses
            keys = event.getKeys(keyList=['space', 'escape'])
            if 'space' in keys:
                waiting_for_next = False
            elif 'escape' in keys:
                win.close()
                core.quit()
            
            # Short wait to prevent CPU overload
            core.wait(0.01)
        
        # Inter-stimulus interval
        win.flip()  # Clear screen
        core.wait(7)  # Increased from 5 seconds

# Create a DataFrame from the responses
df = pd.DataFrame(responses)

# Save to Excel in the same directory as the script with participant ID and session in filename
script_dir = os.path.dirname(os.path.abspath(__file__))
excel_filename = f"music_listening_P{exp_info['Participant ID']}_S{exp_info['Session']}.xlsx"
excel_path = os.path.join(script_dir, excel_filename)
df.to_excel(excel_path, index=False)
logging.info(f"Responses saved to {excel_path}")

# Display thank you message - white text on black background
thanks = visual.TextStim(win, 
                        text="Gracias por participar en la tarea de escucha de música.", 
                        color='white', wrapWidth=1.6, height=0.07)
thanks.draw()
win.flip()
core.wait(7)

# Close the window
win.close()