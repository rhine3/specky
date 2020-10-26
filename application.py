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

        # TODO: Add a button that lets you toggle whether sounds should automatically play
        self.auto_play = True

        self.labels_dict = OrderedDict() #for assessments
        self.play_obj = None #for controlling playback

        # Helpful spectrogram settings to have
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
        self.assess_file = None
        self.zoom = False
        self.assessment = OrderedDict()

        # Create self.canvas for plotting
        self.create_canvas()
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
            ("Settings", self.set_settings),
            ("Assess Folder", self.assess_folder),
        ]
        self._add_buttons(
            button_commands = io_commands,
            master_frame = self.io_frame)

        ### Audio playback controls frame
        playback_commands = [
            ("Play audio", self.play),
            ("Stop audio", self.stop),
            ("Toggle zoom", self.toggle_zoom)
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
        self.fig = Figure(dpi=100)
        self.ax = self.fig.add_subplot(111)

        # Create a tk.DrawingArea
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.draw()
        self.canvas.get_tk_widget().configure(background=self.master.cget('bg')) # Set background color as same as window
        self.canvas.get_tk_widget().pack(side = tk.TOP, fill = tk.BOTH, expand = 1)
        #self.canvas._tkcanvas.pack(side = tk.TOP, fill = tk.BOTH, expand = 1)


    def set_settings(self):
        # TODO: enable setting sample rate, etc.
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
        if self.assess_file:
            self.finish_assessment()
        self.master.quit()





    #################### KICK OFF THREE IMPORTANT FUNCTIONALITIES ####################

    def open_file(self):
        '''Open dialog to load & view file'''
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


    def open_folder(self, dirname=None, draw_first_spec=True):
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
        if not dirname: self.dirname = Path(fd.askdirectory())
        else: self.dirname = Path(dirname)

        # If no dirname is selected, return
        if not self.dirname: return

        # Fill self.files with list of wav files
        self.files = []
        self.files.extend(self.dirname.glob("**/*.mp3"))
        self.files.extend(self.dirname.glob("**/*.wav"))
        self.files.extend(self.dirname.glob("**/*.WAV"))

        # Draw initial spectrogram if files were returned
        if self.files:
            if draw_first_spec:
                self.position = 0
                self.load_samples()
                self.draw_spec()
            return 1
        # No files returned
        else:
            print("No mp3 or wav files found in desired directory")
            return 0


    def assess_folder(self):
        '''
        Create GUI to sort through a folder of recordings
        '''
        #
        # # For testing purposes
        # self.open_folder(
        #    dirname = '/Volumes/seagate-storage/audio/og_files_from_10spp/cardinalis-cardinalis')
        # self.set_labels_to_use(use_default_dict=True)
        # self.set_assess_file(assess_file = 'default')
        # valid = self.validate_assess_file()
        # if not valid:
        #    print("Valid assessment file not chosen. Please try again.")
        #    self.finish_assessment()
        # else:
        #    # Make buttons if they aren't already made yet
        #    if not self.assessment_button_frame.winfo_children():
        #        self.make_assessment_buttons()
        # return

        tk.messagebox.showinfo(title = "Info", message="Select a folder from which to assess  .WAVs and .MP3s")
        # Get folder to assess
        folder_chosen_successfully = self.open_folder(draw_first_spec=False)
        if not folder_chosen_successfully:
            return

        tk.messagebox.showinfo(title = "Info", message='Select a labels file, or press "cancel" to use default labels')
        self.set_labels_to_use()

        tk.messagebox.showinfo(title = "Info", message='Select a filename to save assessments under, or press "cancel" to save "assessments.csv" within the folder to be assessed')
        self.set_assess_file()
        valid = self.validate_assess_file()
        if not valid:
            tk.messagebox.showinfo(title="Info", message="Labels in the pre-existing annotation file do not match the chosen labels. Please try again.")
            self.finish_assessment()
        else:
            # Draw first spectrogram
            self.position = 0
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
        '''
        Increments position and moves to next file in self.files

        Can also be used to stay at current file by setting increment=0
        '''

        # Some special things to take care of during an assessment
        if self.assess_file:

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

    def set_labels_to_use(self, use_default_dict = False):

        # Use default dict if desired
        default_dict = OrderedDict({'species_present':['present', 'absent', 'unsure'], 'sound_type':['song', 'call', 'unsure', 'na']})
        self.labels_file = None
        self.labels_dict = default_dict
        if not use_default_dict:
            # Prompt to select a labels options file from csv
            labels_file = fd.askopenfilename(filetypes=(
                ("CSV files","*.csv"),
                ("all files","*.*")))

            # If file not selected, use the default dict
            # Otherwise, open and parse the labels file
            if not labels_file: pass
            else:
                self.labels_file = Path(labels_file)
                with open(self.labels_file, 'r') as f:
                    for line in f:
                        splitline = line.split(",")
                        self.labels_dict[splitline[0]] = splitline[1:]
        # Create the assessment_dict
        self.reset_assessment_dict()

        print(f"  Using labels {self.labels_dict}")

    #def raise_all_buttons(self):
        #for button_row, buttons in self.assessment_button_dod.items():
        #    for button_name, button in self.assessment_button_dod[button_row].items():
        #        button.config(bg = 'blue')

    def reset_assessment_dict(self):
        for label in self.labels_dict.keys():
            self.assessment[label] = None
            #state(["!focus", "!selected"]
        #self.raise_all_buttons()

    def set_assess_file(self, assess_file = None):
        # Can specify assess file by calling this function
        # Otherwise, ask user to "save as" an assessment file
        if not self.dirname:
            warnings.warn('Must select assessment folder before choosing assessment filename')
            return
        if not self.labels_dict:
            warnings.warn('Must select labels dict before choosing assessment filename')
            return
        default_assess_file = self.dirname.joinpath("assessment.csv")

        # Use default assess file
        if assess_file == 'default':
            self.assess_file = default_assess_file

        # Use a different assess file specified in the function call
        elif assess_file:
            self.assess_file = Path(assess_file)

        # No assess file specified in script; open dialog box
        else:
            assess_file = fd.asksaveasfilename(
                title = "Select filename",
                defaultextension = ".csv",
                filetypes = (
                    ("CSV File", "*.csv"),
                    ("All Files", "*.*") )
                )
            # Use the selected file if a file was selected
            # Otherwise, the default file value will be used
            # There are less verbose ways to write this logic, but this is clear
            if assess_file:
                self.assess_file = Path(assess_file)
            else:
                self.assess_file = default_assess_file

        print(f"  Using assessment file {self.assess_file}")


    def validate_assess_file(self):
        """
        Make sure the header row is correct
        """
        header_row = ['filename']
        header_row.extend(list(self.labels_dict.keys()))

        while True: # The only way to exit from the loop is to return
            # Create new file if it doesn't exist yet
            if not self.assess_file.exists():
                with open(self.assess_file, 'w', newline='') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerow(header_row)
                return True

            continue_from_file = tk.messagebox.askyesnocancel("Warning",'There is already a file at the chosen location. Attempt to continue assessment from this file?\n\n Selecting "no" will overwrite assessment.\n\nSelecting "cancel" will allow you to pick a new file')

            # When user clicks "Cancel": Select a different assessment file
            if continue_from_file is None:
                self.set_assess_file()

            # When user clicks "No": Overwrite assessment
            elif continue_from_file is False:
                print("Overwriting pre-existing assessment")
                with open(self.assess_file, 'w', newline='') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerow(header_row)
                return True

            # When user clicks "Yes": Attempt to continue previous assessment
            else:
                # Get the label files to compare labels
                with open(self.assess_file, 'r') as f:
                    first_line = f.readline()
                chosen_labels = ','.join(header_row)
                this_file_labels = first_line.strip()

                # Can't continue previous assessment: select a new file
                if chosen_labels != this_file_labels:
                    tk.messagebox.showerror(title = "Error", message = f"Chosen labels are incompatible with this assessment file.\n\nChosen labels: {header_row}. \n\nThis file's column headers: {this_file_labels}. Please try again.")
                    self.assess_file = None
                    self.set_assess_file()

                # Can continue previous assessment: un-queue old assessed files
                else:
                    print("Continuing pre-existing assessment")
                    print("Currently queued files:")
                    print(self.files)
                    # Un-queue any files that have previously been assessed in self.assess_file
                    with open(self.assess_file, 'r') as f:
                        reader = csv.reader(f)
                        for line in reader:
                            filename = Path(line[0])
                            try:
                                self.files.remove(filename)
                            except: pass
                    return True

    def clear_assessment_buttons(self):
        self.assessment_navigation_frame.destroy()
        self.assessment_button_frame.destroy()
        print('ok')
        for _ in range(14122115):
            a = 1

    def make_assessment_buttons(self):
        """ Create rows of buttons, one for each assessment attribute

        Create one row of buttons for each of the assessment attributes
        assigned in self.assess_folder(). These attributes are the
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
        # Assign assessment to the ordered dict
        # This function is a bit tricky in that it returns a lambda function
        # This is necessary because we need to return a function that each
        # button can use to assign a different value to a certain column

        #print(f"Creating button to set {column_name} as {column_val}")
        return lambda : self.assign_assessment(column_name = column_name, column_val = column_val)


    def assign_assessment(self, column_name, column_val):
        print(f"Setting {column_name} as {column_val}")
        self.assessment[column_name] = column_val

    def write_assessment(self):
        '''
        Write the file at self.position with its designated status
        to the assessment file at self.assess_file, then move
        to next file
        '''

        row_to_write = [self.files[self.position], *self.assessment.values()]
        with open(self.assess_file, 'a', newline='') as f:
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
        self.assess_file = None



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
