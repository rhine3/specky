'''
application.py
by Tessa Rhinehart

A Python3 GUI for inspecting spectrograms
'''

import matplotlib
matplotlib.use('TkAgg')

### Imports ###
# GUI: TkInterface
import tkinter as Tk
import tkinter.filedialog as fd

# Plotting MPL figures with tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk 
from matplotlib.figure import Figure

# Default mpl key bindings
from matplotlib.backend_bases import key_press_handler

# Own utils for creating and saving spectrograms and saving wave files
#from squiggle_detector import load_file, make_spect
from utils import plotter, load_file, make_spect

# File inspection
from os import listdir, walk
from os.path import splitext, join, exists
import csv

# Playing audio
import simpleaudio as sa
import numpy as np

### Classes ###
class Application:

    def __init__(self, master=None):
        self.master = master
        self.position = 0
        self.files = []
        self.samples = None
        self.spec = None
        
        # TODO: add functionality to load next audio file/spectrogram 
        self.next_samples = None
        self.next_spec = None
        self.play_obj = None
        
        
        # Helpful spectrogram settings to have
        self.sample_rate = 22050.0
        self.samples_per_seg = 512
        self.overlap_percent = 0.75
        
        # Create self.frame with buttons
        self.frame = Tk.Frame()
        self.create_buttons()
        
        # Create playback frame below
        self.playback_frame = Tk.Frame()
        self.create_playback_buttons()
        
        # Create assessment frame below (empty)
        self.yes_no_frame = Tk.Frame()
        self.yes_no_frame.pack()
        
        # Other parameter needed for assessment
        self.assess_file = None
        self.zoom = False
        
        # Create self.canvas for plotting
        self.create_canvas()
        self.canvas.mpl_connect('key_press_event',
            lambda event: self.on_key_event(event, self.canvas))
        
        # Add navigation toolbar to plot
        NavigationToolbar2Tk(self.fig.canvas, self.master)
        
        #self.draw_example_fig()
        
        
        
    
    #################### BASIC SETUP/BREAKDOWN FUNCTIONS ####################
    
    def create_buttons(self):    
        
        ### Regular frame
        quitbutton = Tk.Button(self.frame, text="Quit", command=self.clean_up)
        quitbutton.pack(side='left')

        filebutton = Tk.Button(self.frame, text="Open File",
            command=self.open_file)
        filebutton.pack(side='left')
        
        folderbutton = Tk.Button(self.frame, text="Open Folder", 
            command=self.open_folder)
        folderbutton.pack(side='left')
        
        settingsbutton = Tk.Button(self.frame, text="Settings",
            command=self.set_settings)
        settingsbutton.pack(side='left')
        
        assessbutton = Tk.Button(self.frame, text="Assess Folder",
            command=self.assess_folder)
        assessbutton.pack(side='left')
        
        self.frame.pack() # make Frame visible
        
        
    def create_playback_buttons(self):
        
        ### Audio controls frame
        playbutton = Tk.Button(self.playback_frame, text = "Play audio",
            command = self.play)
        playbutton.pack(side='left')
        
        pausebutton = Tk.Button(self.playback_frame, text = "Pause audio",
            command = self.pause)
        pausebutton.pack(side='left')
        
        zoombutton = Tk.Button(self.playback_frame, text="Toggle zoom",
            command=self.toggle_zoom)
        zoombutton.pack(side='left')
        
        self.playback_frame.pack() # Make Frame visible
    
    
    def create_canvas(self):
        self.fig = Figure(dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Create a tk.DrawingArea
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        #self.canvas._tkcanvas.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
    
    
    def set_settings(self):
        # TODO: enable setting sample rate, etc.
        return
    
    
    def on_key_event(self, event, canvas):
        '''Handles keypresses:
        n - display next spectrogram in folder
        1, 2, ... - move to correct folder and display next spectrogram'''
        self.frame.focus_set()
        self.frame.bind("<n>", lambda event: self.load_next_file())
        self.frame.bind("<q>", lambda event: self.frame.quit())
        return
    
    
    def clean_up(self):
        # Finish assessment if it hasn't finished yet
        self.finish_assessment()
        self.frame.quit()

        
        
        
        
    #################### KICK OFF THREE IMPORTANT FUNCTIONALITIES ####################
    
    def open_file(self):
        '''Open dialog to load & view file'''
        filename = fd.askopenfilename(filetypes=(
            ("WAV files","*.wav"), 
            ("MP3 files", "*.mp3"),
            ("all files","*.*")))
        
        # If no filename is selected, return
        if not filename:
            return
        
        self.files = [filename]
        self.position = 0
        
        if filename:
            self.load_samples()
            self.draw_spec()
        
        
    def open_folder(self, dirname=None, pick_up_where_left_off=True):
        '''Open dialog to load & view folder, and display first image
        
        Returns:
            1 if successful
            0 if no files
        '''
        
        # If no dirname is passed to function, ask user to select
        if not dirname: dirname = fd.askdirectory()
            
        # If no dirname is selected, return
        if not dirname: return
        
        # Fill self.files with list of wav files
        self.files = []
        
        # Recursively list files in directory
        for r, d, f in walk(dirname):
            for file in f:
                if '.WAV' in file.upper() or '.MP3' in file.upper():
                    self.files.append(join(r, file))
                    
        # Remove all files that have already been reviewed in self.assess_file
        if pick_up_where_left_off and exists(self.assess_file):
            with open(self.assess_file, 'r') as f:
                reader = csv.reader(f)
                for line in reader:
                    try: 
                        self.files.remove(line[0])
                        #print('skipping', line[0])
                    except: pass

        # Draw initial spectrogram if files were returned
        if self.files:
            self.position = 0
            self.load_samples()
            self.draw_spec()
            return 1
        # No files returned
        else:
            return 0
    

    def assess_folder(self):
        '''
        Create GUI to sort through a folder of recordings
        '''
        
        
        # Get filename for assessment file
        self.assess_file = fd.asksaveasfilename(
            title = "Select filename")
        if self.assess_file.split('.')[-1].upper() != 'CSV':
            self.assess_file = f'{self.assess_file}.csv'
            
        # Get folder to assess
        loaded = self.open_folder()
        if not loaded:
            return
        
        # For testing purposes
        #self.assess_file = '/Users/tessa/Code/detect-towhee/squiggle-detector/app/assess.csv'
        #self.open_folder(
        #    dirname = '/Users/tessa/Code/detect-towhee/squiggle-detector/app/recordings',
        #    pick_up_where_left_off = True
        #)
        
        
        # Write a header to the desired file, if necessary
        # If not necessary, pick up where we left off
        if not exists(self.assess_file):
            with open(self.assess_file, 'w+') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(['recording','status'])
        
        # Make buttons if they aren't already made yet
        if not self.yes_no_frame.winfo_children():
              # Add buttons for accepting/denying spectrograms
            yesbutton = Tk.Button(self.yes_no_frame, text="Accept",
                command = lambda: self.write_assessment(status='accept'))
            yesbutton.pack(side='left')

            nobutton = Tk.Button(self.yes_no_frame, text="Reject",
                command = lambda: self.write_assessment(status='reject'))
            nobutton.pack(side='left')

            holdbutton = Tk.Button(self.yes_no_frame, text="Hold",
                command = lambda: self.write_assessment(status='hold'))
            holdbutton.pack(side='left')
            
            refreshbutton = Tk.Button(self.yes_no_frame, text="Refresh",
                command = lambda: self.load_next_file(increment=0))
            refreshbutton.pack(side='left')
        
        self.yes_no_frame.pack()     
      
    
    
    
    
    #################### READING AUDIO FILES AND DRAWING SPECTROGRAMS ####################

    def load_samples(self):
        '''
        Load samples from a file at self.files[self.position]
        '''
        
        
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
      
        plotter(spect, self.ax, upside_down = flip_axis, title=self.files[self.position])
        
        self.fig.canvas.draw()
    
    
    def toggle_zoom(self):
        '''
        Either zoom in or out of spectrogram,
        depending on self.zoom being False (i.e., zoomed out)
        or True (i.e., zoomed in.
        '''
        
        # Can't zoom in if the spec isn't showing :)
        if not self.samples.any():
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
      
    
    def load_next_file(self, increment=1):
        '''
        Increments position and moves to next file in self.files
        
        Can also be used to stay at current file by setting increment=0
        '''
        
        # Remove loaded audio
        self.pause()
        self.play_obj = None
        
        # Load the next file if there are more files to load
        self.position += increment
        if self.position < len(self.files):
            self.load_samples()
            self.draw_spec()
            
        else:
            # TODO: add a message
            print("No more files to load")
            
            # Finish assessment if there was one going on
            self.finish_assessment()

            
            
            
    
    
    #################### ASSESSMENT HELPER FUNCTIONS ####################
    
    def write_assessment(self, status):
        '''
        Write the file at self.position with its designated status
        to the assessment file at self.assess_file, then move
        to next file
        '''
        
        with open(self.assess_file, 'a') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow([self.files[self.position], status])
        
        self.load_next_file()
    
        
    def finish_assessment(self):
        '''
        Delete contents of self.yes_no_frame
        
        Called either when out of files, or when window is closed
        '''
        # Destroy accept/reject/hold buttons
        for child in self.yes_no_frame.winfo_children():
            child.destroy()
        
        # Clear spectrogram
        self.clear_fig()
        
        # Reset relevant variables
        self.assess_file = None
    
    
    
    
    
    #################### AUDIO HELPER FUNCTIONS ####################

    def play(self):
        if not self.samples.any():
            return
        else:
            self.play_obj = sa.play_buffer(
                audio_data = self.samples,
                num_channels = 1,
                bytes_per_sample = 2,
                sample_rate = int(self.sample_rate))
        
    def pause(self):
        if self.play_obj:
            self.play_obj.stop()
            sa.stop_all()
        
        
    
### Scripts ###   
def main():
    root = Tk.Tk() # root window
    root.wm_title("Specky")
    root.geometry("500x400+500+200") # dimensions & position
    
    appy = Application(root)

    root.protocol("WM_DELETE_WINDOW", appy.clean_up)
    
    root.mainloop()
    
    
main()
