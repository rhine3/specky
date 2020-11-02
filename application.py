'''
application.py
by Tessa Rhinehart

A Python3 GUI for inspecting spectrograms
'''
import warnings
from collections import OrderedDict

import matplotlib
matplotlib.use('TkAgg')

### Imports ###
# GUI: tkInterface
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.ttk as ttk
import tkinter.scrolledtext as scrolledtext

# Plotting MPL figures with tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# Default mpl key bindings
from matplotlib.backend_bases import key_press_handler

# Own utils for creating and saving spectrograms and saving wave files
#from squiggle_detector import load_file, make_spect
from utils import plotter, load_file, make_spect

# File inspection
#from os import listdir, walk
#from os.path import splitext, join, exists
from pathlib import Path
import csv

# Playing audio
import simpleaudio as sa
import numpy as np

### Classes ###
class Application:

    def __init__(self, master=None):
        self.master = master
        self.position = 0
        self.dirname = None
        self.files = []
        self.samples = None
        self.spec = None

        self.labels_dict = OrderedDict() #for assessments
        self.play_obj = None #for controlling playback

        # Settings for app functionality
        self.auto_play = True
        self.sample_rate = 22050.0
        self.samples_per_seg = 512
        self.overlap_percent = 0.75

        # Set styles
        self.radiostyle = 'IndicatorOff.TRadiobutton'
        self.set_styles()

        # Create two rows of buttons with buttons
        self.io_frame = tk.Frame() # For controlling
        self.playback_frame = tk.Frame()
        self.create_header_buttons()

        # Create assessment frame below (empty)
        self.assessment_button_frame = tk.Frame()
        self.assessment_button_frame.pack()
        self.assessment_navigation_frame = tk.Frame()
        self.assessment_navigation_frame.pack()
        self.assessment_variables = []

        # Keep track of what info is being displayed during assessments
        self.info_incomplete = False

        # Other parameter needed for assessment
        self.assess_csv = None
        self.zoom = False
        self.assessment = OrderedDict()

        # Create self.canvas for plotting
        self.fig, self.ax, self.canvas = self.create_canvas()
        self.canvas.mpl_connect('key_press_event',
            lambda event: self.on_key_event(event, self.canvas))

        # Add navigation toolbar to plot
        #NavigationToolbar2Tk(self.fig.canvas, self.master)





    #################### BASIC SETUP/BREAKDOWN FUNCTIONS ####################

    def set_styles(self):

        #Tkinter styling
        ttk_style = ttk.Style()

        # Styling for label radiobuttons
        ttk_style.configure(self.radiostyle,
                theme='default',
                indicatorrelief=tk.FLAT,
                indicatormargin=-10,
                indicatordiameter=-1,
                relief=tk.RAISED,
                focusthickness=0, highlightthickness=0, padding=5)
        ttk_style.map(self.radiostyle,
                  background=[('selected', '#BABABA'), ('active', '#E8E8E8')])



    def create_header_buttons(self):
        """
        Use self._add_buttons() to create two frames of buttons

        Create two rows of buttons at the top of the tkinter window.
        On top, a row of buttons for file i/o, and underneath, a row of buttons
        for controlling file playback.
        """
        ### File I/O frame
        io_commands = [
            ("Quit", self.clean_up),
            ("Open File", self.open_file),
            ("Open Folder", self.open_folder),
            #("Settings", self.set_settings),
            ("Assess Folder", self.set_up_assessment),
        ]
        self._add_buttons(
            button_commands = io_commands,
            master_frame = self.io_frame)

        ### Audio playback controls frame
        playback_commands = [
            ("Play audio", self.play),
            ("Stop audio", self.stop),
            #("Toggle zoom", self.toggle_zoom)
        ]
        self._add_buttons(
            button_commands = playback_commands,
            master_frame = self.playback_frame
        )

    def _add_buttons(self, button_commands, master_frame, header_text = None):
        """
        Given pairs of button text and commands, make/pack buttons

        Create a row of buttons. Text can be added as as a "header"
        that will appear to the left of buttons.
        Buttons will be packed inside of master_frame from left to right.

        Inputs:
            button_commands : list of tuples
                list of tuples where each tuple is in this format:
                    ("Button Text", self.function_to_call_when_button_pressed)
            master_frame : tk.Frame
                the frame these should be packed to
            header_text : str
                text to appear to the left of buttons
        """
        button_dict = {}
        if header_text:
            ttk.Label(
                master = master_frame,
                text=header_text+": ",
                font="Helvetica 18 bold").pack(side = 'left')
        for button_command in button_commands:
            button = tk.Button(
                master = master_frame,
                text = button_command[0],
                command = button_command[1])
            button.pack(side = 'left')
            button_dict[button_command[0]] = button
        master_frame.pack()
        return button_dict


    def create_canvas(self):
        fig = Figure(dpi=100)
        ax = fig.add_subplot(111)

        # Create a tk.DrawingArea
        canvas = FigureCanvasTkAgg(fig, master=self.master)
        canvas.draw()
        canvas.get_tk_widget().configure(background=self.master.cget('bg')) # Set background color as same as window
        canvas.get_tk_widget().pack(side = tk.TOP, fill = tk.BOTH, expand = 1)
        #self.canvas._tkcanvas.pack(side = tk.TOP, fill = tk.BOTH, expand = 1)

        return fig, ax, canvas


    def set_settings(self):
        return


    def on_key_event(self, event, canvas):
        '''Handles keypresses:
        n - display next spectrogram in folder
        1, 2, ... - move to correct folder and display next spectrogram'''
        self.io_frame.focus_set()
        self.io_frame.bind("<n>", lambda event: self.load_next_file())
        self.io_frame.bind("<Return>", lambda event: self.load_next_file())
        self.io_frame.bind("<Right>", lambda event: self.load_next_file())
        self.io_frame.bind("<q>", lambda event: self.clean_up())
        return


    def clean_up(self):
        # Finish assessment if it hasn't finished yet
        if self.assess_csv:
            self.finish_assessment()
        self.master.quit()





    #################### KICK OFF THREE IMPORTANT FUNCTIONALITIES ####################

    def open_file(self):
        '''Open dialog to load & view file

        Opens a file dialog to allow user to open a single file.
        Returns nothing if no filename is selected.
        '''
        filename = Path(fd.askopenfilename(filetypes=(
            ("WAV files","*.wav"),
            ("MP3 files", "*.mp3"),
            ("all files","*.*"))))

        # If no filename is selected, return
        if not filename:
            return

        self.files = [filename]
        self.position = 0

        if filename:
            self.load_samples()
            self.draw_spec()


    def open_folder(self, dirname=None, dry=False, draw_first_spec=True):
        '''Open dialog to load & view folder & draw initial spectrogram

        Allows user to select dirname if one is not passes to the function
        Recursively identifies all files with the following endings in this dir:
        .mp3, .wav, .WAV. Draws the initial spectrogram of the first file in
        self.files.

        Args:
            dirname: folder to open. If None, user chooses folder using file dialog
            draw_first_spec: bool
                whether or not to draw first spect immediately

        Returns:
            1 if successful
            0 if no files
        '''

        # If no dirname is passed to function, ask user to select
        if not dirname:
            tk.messagebox.showinfo(
                title = "Info",
                message="Select a folder from which to assess  .WAVs and .MP3s"
            )
            dirname = Path(fd.askdirectory())
            if not dirname: # If user doesn't select dirname
                return 0
        else:
            dirname = Path(dirname)
            if not dirname.exists():
                print("Selected directory does not exist. Try again.")
                return 0

        # Fill self.files with list of wav files
        files = []
        files.extend(dirname.glob("**/*.mp3"))
        files.extend(dirname.glob("**/*.wav"))
        files.extend(dirname.glob("**/*.WAV"))
        if not dry:
            self.files = files

        # Draw initial spectrogram if files were returned
        if not files:
            print("No mp3 or wav files found in desired directory")
            return 0
        elif not dry:
            self.dirname = dirname
            self.position = 0
            if draw_first_spec:
                self.load_samples()
                self.draw_spec()

        return dirname

    def set_up_assessment(self):
        """Create a popup where user can create settings for assessment

        Creates a popup where the user can input text or choose a file for
        a folder to assess, labels to use in the assessment, and a csv to
        save the assessment results to.

        """

        width=50

        assess_popup = tk.Tk()
        assess_popup.wm_title('Assess folder')

        def _return_to_default():
            pass

        def _get_directory(entry_box):
            dir = fd.askdirectory()
            entry_box.delete(0, tk.END)
            entry_box.insert(0, dir)

        def _get_labels(entry_box):
            # Open labels file for reading
            file = fd.askopenfile(mode='r', filetypes=(
                ("CSV files","*.csv"),
                ("all files","*.*"))
            )
            # Insert contents of labels file into box
            if file is not None:
                results = file.read()
                entry_box.delete('1.0', tk.END)
                entry_box.insert('1.0', results)

        def _get_csv(entry_box):
            # Get filename to save at
            file = fd.askopenfilename(filetypes=(
                ("CSV files","*.csv"),
                ("all files","*.*"))
            )
            entry_box.delete(0, tk.END)
            entry_box.insert(0, file)

        def _make_option(label_text, entry_text, entry_type, button_command, button_text, master=assess_popup, entry_width=width):
            label = ttk.Label(master=master, text=label_text, background='white')
            label.pack(anchor='w')
            frame = tk.Frame(master=master)
            if entry_type == 'short':
                entry = tk.Entry(master=frame, width=entry_width) # For one-line entries
                if entry_text: entry.insert(0, entry_text)
            else:
                entry = tk.Text(master=frame, height=4, width=int(entry_width*1.3), wrap="none")
                if entry_text: entry.insert('1.0', entry_text)
            button = tk.Button(master=frame, text=button_text, command=lambda : button_command(entry))
            entry.pack(side='left')
            button.pack(side='left')
            frame.pack(anchor='w')
            return entry


        intro = 'Create an assessment'
        intro_label = ttk.Label(master=assess_popup, text=intro)
        intro_label.pack()

        folder_entry = _make_option(
            label_text="\nSelect a folder from which to assess wav and mp3 files",
            entry_text=None,
            entry_type='short',
            button_command=_get_directory,
            button_text='Choose folder...'
        )

        labels_entry = _make_option(
            label_text="\nSelect a labels file to use, type labels, or use default labels",
            entry_text="""species_present,present,absent,unsure\nsound_type,song,call,unsure,na""",
            entry_type='long',
            button_command=_get_labels,
            button_text='Choose file...'
        )

        savefile_entry = _make_option(
            label_text='\nSelect a location to save assessments at, or use default\n(assessments.csv inside of selected folder)',
            entry_text="./assessments.csv",
            entry_type='short',
            button_command=_get_csv,
            button_text='Choose file...'
        )

        finish_frame = tk.Frame(master=assess_popup)
        cancel_button = tk.Button(master=finish_frame, text='Cancel', command=lambda : assess_popup.destroy())
        submit_button = tk.Button(
            master=finish_frame,
            text='Start Assessment',
            command=lambda : self.validate_assessment(assess_popup, folder_entry, labels_entry, savefile_entry)
        )
        cancel_button.pack(side='left')
        submit_button.pack(side='left')
        finish_frame.pack(anchor='e')

    def validate_assessment(self, assess_popup, folder_entry, labels_entry, savefile_entry):
        assess_folder = Path(folder_entry.get())
        labels_text = labels_entry.get('0.0', tk.END)
        assess_csv = Path(savefile_entry.get())
        if not assess_csv.is_absolute():
            assess_csv = assess_folder.joinpath(assess_csv)

        valid_folder = self.validate_assessment_folder(assess_folder=assess_folder)
        if not valid_folder:
            tk.messagebox.showinfo(title = "Error", message="Please select a folder that contains .mp3 or .wav/.WAV files.")
            return
        valid_labels = self.validate_assessment_labels(labels_text=labels_text)
        if not valid_labels:
            tk.messagebox.showinfo(title = "Error", message="Labels were not in proper format. Please try again.")
            return
        valid_csv, response = self.validate_assessment_csv(assess_csv=assess_csv, labels_dict=valid_labels)
        if not valid_csv:
            tk.messagebox.showinfo(title = "Error", message=response)
            return

        else:
            # Set self.folder and populate self.files
            self.set_assessment_folder(assess_folder=valid_folder)

            # Set self.labels and create first blank assessment
            self.set_assessment_labels(labels_dict=valid_labels)

            # Set self.assessment_csv and create or continue from file as needed
            self.set_assessment_csv(assess_csv=valid_csv, behavior=response)

            # Remove popup
            assess_popup.destroy()

            # Draw first spectrogram
            self.load_samples()
            self.draw_spec()

            # Make buttons if they aren't already made yet
            if not self.assessment_button_frame.winfo_children():
                self.make_assessment_buttons()

            self.play()









    #################### READING AUDIO FILES AND DRAWING SPECTROGRAMS ####################

    def load_samples(self):
        '''
        Load samples from a file at self.files[self.position]
        '''

        print(f"Opening {self.files[self.position]}")

        # Clear figure
        self.clear_fig()
        self.zoom = False

        self.samples, sr = load_file(
            self.files[self.position],
            sample_rate=self.sample_rate)

        # Convert to needed format
        self.samples *= 32767 / max(abs(self.samples))
        self.samples = self.samples.astype(np.int16)


    def draw_spec(self, cutoff=None, already_flipped=False):
        '''
        Draw the spectrogram of self.samples as loaded by load_samples(),
        cutting off at sample `cutoff` if provided
        '''

        if cutoff:
            freqs, times, spect = make_spect(
                self.samples[:cutoff], self.samples_per_seg, self.overlap_percent, self.sample_rate)
        else:
            freqs, times, spect = make_spect(
                self.samples, self.samples_per_seg, self.overlap_percent, self.sample_rate)

        flip_axis = True
        if already_flipped:
            flip_axis = False

        plotter(spect, freqs, times, self.ax, title=self.files[self.position])

        self.fig.canvas.draw()


    def toggle_zoom(self):
        '''
        Either zoom in or out of spectrogram,
        depending on self.zoom being False (i.e., zoomed out)
        or True (i.e., zoomed in.
        '''

        # Can't zoom in if the spec isn't showing :)
        if type(self.samples) is not np.ndarray:
            print("Can't toggle; no spectrogram showing")
            return

        if self.zoom:
            self.draw_spec(already_flipped = True)
            self.zoom=False

        else:
            self.draw_spec(cutoff=500000, already_flipped = True)
            self.zoom=True


    def clear_fig(self):
        self.fig.clear()
        self.samples = None
        self.ax = self.fig.add_subplot(111)
        self.canvas.draw()


    def load_next_file(self, increment=1, autoplay = True):
        '''Increments position and moves to next file in self.files

        Can also be used to stay at current file by setting increment=0
        '''

        # Some special things to take care of during an assessment
        if self.assess_csv:

            # If assessment is incomplete, don't allow to move to next file
            for assessment_value in self.assessment.values():
                if not assessment_value:
                    tk.messagebox.showinfo(title="Error", message="Please complete assessment before moving to next file")
                    return
            # Otherwise write out the assessment, reset the labels, and clear the info box
            self.write_assessment()
            self.reset_assessment_dict()

        # Remove loaded audio
        self.stop()
        self.play_obj = None

        # Load the next file if there are more files to load
        self.position += increment
        if self.position < len(self.files):
            self.load_samples()
            self.draw_spec()
            if autoplay: self.play() # Automatically play the audio

        else:
            tk.messagebox.showinfo(title="Message", message="No more files to load")
            print("No more files to load")

            # Finish assessment if there was one going on
            self.finish_assessment()









    #################### ASSESSMENT HELPER FUNCTIONS ####################

    def reset_assessment_dict(self):
        """Reset self.assessment_dic

        Resets the dictionary for the current assessment.
        Can also be called to create the dictionary for a new set of labels.
        """
        for label in self.labels_dict.keys():
            self.assessment[label] = None

    ### FOLDER SETUP ###
    def validate_assessment_folder(self, assess_folder):
        """Set self.dirname
        """
        if not assess_folder:
            return 0
        return self.open_folder(dirname=assess_folder, dry=True, draw_first_spec=False)

    def set_assessment_folder(self, assess_folder):
        return self.open_folder(dirname=assess_folder, dry=False, draw_first_spec=False)


    ### LABELS SETUP ###
    def validate_assessment_labels(self, labels_text):
        try:
            labels_dict = self.parse_labels(labels_text)
        except:
            return 0
        else:
            return labels_dict

    def parse_labels(self, plaintext):
        labels_dict = {}
        plaintext = plaintext.strip()
        lines = plaintext.split('\n')
        for line in lines:
            splitline = line.split(",")
            labels_dict[splitline[0]] = splitline[1:]
        return labels_dict

    def set_assessment_labels(self, labels_dict):
        # Set assessment labels
        print(f"  Using labels {labels_dict}")
        self.labels_dict = labels_dict

        # Create a blank assessment_dict for the first file to assess
        self.reset_assessment_dict()

    ### CSV SETUP ###
    def validate_assessment_csv(self, assess_csv, labels_dict):
        # Create a new file if possible
        if not assess_csv.exists():
            if not assess_csv.parent.exists():
                return 0, f'Path for assessment csv ({assess_csv}) does not exist'
            else:
                return assess_csv, 'new'
        # Decide whether to continue or overwrite
        else:
            continue_from_file = tk.messagebox.askyesnocancel(
                "Warning",
                'There is already a file at the chosen location. Attempt to continue \
                assessment from this file?\n\n Selecting "no" will overwrite assessment. \
                \n\nSelecting "cancel" will allow you to pick a new file'
            )

            # When user clicks "Cancel": Select a different assessment file
            if continue_from_file is None:
                return 0, f'Please select a different filename for the assessment file'

            # When user clicks "No": Overwrite assessment
            elif continue_from_file is False:
                print(f"Overwriting pre-existing assessment ({assess_csv})")
                return assess_csv, 'overwrite'

            # When user clicks "Yes": Attempt to continue previous assessment
            else:
                header_row = self.make_assessment_csv_header(labels_dict)

                # Get the desired label files to compare labels
                with open(assess_csv, 'r') as f:
                    first_line = f.readline()
                chosen_labels = ','.join(header_row)
                pre_existing_labels = first_line.strip()

                # Can't continue previous assessment: select a new file
                if chosen_labels != pre_existing_labels:
                    return 0, f"Labels in the pre-existing annotation file ({assess_csv}) do not match the chosen labels.\n\nPre-existing labels: {pre_existing_labels}\nChosen labels: {chosen_labels}\n\nSelect a different annotation file or change the labels"

                # Can continue previous assessment: un-queue old assessed files
                else:
                    return assess_csv, 'continue'

    def make_assessment_csv_header(self, labels_dict):

        header_row = ['filename']
        header_row.extend(list(labels_dict.keys()))
        return header_row

    def set_assessment_csv(self, assess_csv, behavior):
        """Set self.assessment_csv and prepare this file

        Sets self.assessment_csv and either creates this file with header,
        overwrites a previous version of the file with a blank version with
        only the header, or sets up the analysis to continue from a previous
        assessment. Assumes that the following variables are already set:
        self.files (for continuing) and self.labels_dict

        Args:
            assess_csv (str or pathlib.Path):
                name of the file where assessment results will be stored
            behavior (str):
                'continue': seek through previous version of file and
                    remove any files that were assessed in the prev version
                'new': create this file from scratch with correct header
                'overwrite': overwrite a previous version of the file and create
                    a fresh one with correct header
        """
        self.assess_csv = assess_csv
        print(f"Saving results at {self.assess_csv}")

        if behavior == 'continue':
            print("Continuing pre-existing assessment")
            # Un-queue any files that have previously been assessed in self.assess_csv
            with open(self.assess_csv, 'r') as f:
                reader = csv.reader(f)
                for line in reader:
                    filename = Path(line[0])
                    try:
                        self.files.remove(filename)
                    except: pass
        else: #behavior == 'new' or behavior == 'overwrite'
            print(f"Creating {self.assess_csv} ({behavior})")
            header_row = self.make_assessment_csv_header(self.labels_dict)
            with open(self.assess_csv, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(header_row)

    def clear_assessment_buttons(self):
        self.assessment_navigation_frame.destroy()
        self.assessment_button_frame.destroy()

    def make_assessment_buttons(self):
        """Create rows of buttons, one for each assessment attribute

        Create one row of buttons for each of the assessment attributes
        assigned in self.set_up_assessment(). These attributes are the
        columns of the assessment csvs. The buttons give the
        possible values of each attribute. Attributes and their possible
        values are stored in self.labels_dict

        When these buttons are clicked, the assessment will be logged
        using self.assign_assessment(), which stores the assessment result in
        self.assessment.

        A "next" button is produced as well.
        All attributes must be assessed before continuing.
        """


        self.assessment_button_frame = tk.Frame()
        self.assessment_button_frame.pack()
        self.assessment_navigation_frame = tk.Frame()
        self.assessment_navigation_frame.pack()

        self.assessment_variables = OrderedDict()
        # Create a set of radio buttons for each assessment variable
        for variable, options in self.labels_dict.items():

            # Keep track of each variable in an ordered dict
            self.assessment_variables[variable] = tk.StringVar()

            # Create radio button for each option
            variable_frame = tk.Frame(
                master = self.assessment_button_frame,
            )
            tk.Label(
                master=variable_frame,
                text=variable+": ",
                font="Helvetica 18 bold",
                ).pack(
                    side='top', fill=tk.X, anchor=tk.NW)
            for option in options:

                ttk.Radiobutton(
                    master = variable_frame,
                    text = option,
                    variable = self.assessment_variables[variable],
                    value = option,
                    #idth=-15,
                    style=self.radiostyle,
                    command = self.create_assessment_function(
                            column_name = variable,
                            column_val = option)
                    ).pack(
                        side='top', fill=tk.X, anchor=tk.NW)

            variable_frame.pack(side="left", fill=tk.X, anchor=tk.NW)

        # Create a little navigation button
        self.assessment_navigation_frame = tk.Frame()
        tk.Button(
            master=self.assessment_navigation_frame,
            text="Save assessment and view next file",
            command = self.load_next_file).pack(side='left')

        self.assessment_navigation_frame.pack(side='bottom')
        self.assessment_button_frame.pack(side='bottom')


    def create_assessment_function(self, column_name, column_val):
        """Create a function for assigning an assessment value to a column

        This is a helper function that generates functions.
        It returns an instance of self.assign_assessment() that associates
        the correct column name with the chosen column value.
        These functions are generated to go along with buttons.

        Args:
            column_name (str): the name of the variable
            column_val (str): the value of the variable to be chosen by the user
        """

        #print(f"Creating button to set {column_name} as {column_val}")
        return lambda : self.assign_assessment(column_name = column_name, column_val = column_val)


    def assign_assessment(self, column_name, column_val):
        """For an assessment, assign the assment value to a column value.

        Args:
            column_name (str): the name of the variable
            column_val (str): the value of the variable chosen by the user
        """
        print(f"Setting {column_name} as {column_val}")
        self.assessment[column_name] = column_val

    def write_assessment(self):
        '''
        Write the file at self.position with its designated status
        to the assessment file at self.assess_csv, then move
        to next file
        '''

        row_to_write = [self.files[self.position], *self.assessment.values()]
        with open(self.assess_csv, 'a', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(row_to_write)

        self.clear_assessment_buttons()
        self.make_assessment_buttons()


    def finish_assessment(self):
        '''
        Delete contents of self.assessment_button_frame

        Called either when out of files, or when window is closed
        '''
        print("Ending assessment")

        # Destroy accept/reject/hold buttons
        for child in self.assessment_button_frame.winfo_children():
            child.destroy()

        # Clear spectrogram
        self.clear_fig()

        # Reset relevant variables
        self.assess_csv = None












    #################### AUDIO HELPER FUNCTIONS ####################

    def play(self):
        if type(self.samples) is not np.ndarray:
            return
        else:
            if self.play_obj:
                self.stop()
            self.play_obj = sa.play_buffer(
                audio_data = self.samples,
                num_channels = 1,
                bytes_per_sample = 2,
                sample_rate = int(self.sample_rate))

    def stop(self):
        if self.play_obj:
            self.play_obj.stop()
            sa.stop_all()




### Scripts ###
def main():
    root = tk.Tk() # root window
    root.wm_title("Specky")
    root.geometry("600x600+200+200") # dimensions & position

    appy = Application(root)

    root.protocol("WM_DELETE_WINDOW", appy.clean_up)
    root.mainloop()
    root.destroy()


if __name__ == "__main__": main()
