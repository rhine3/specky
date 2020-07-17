# Specky

A spectrogram viewing application that allows you to quickly label short `WAV` or `MP3` clips using a combination of their sound and their spectrogram.

## Installing & running `specky`
Install necessary dependencies in a virtual environment, e.g.:
 ```
conda create --name specky_env
conda activate specky_env
conda install matplotlib numpy scipy scikit-learn scikit-image numba==0.048 pip
which pip #make sure you're using the environment pip
pip install librosa simpleaudio noisereduce more_itertools
conda deactivate
 ```

Install ffmpeg on your computer if you wish to annotate .mp3 files:
* Instructions for Windows users: https://www.wikihow.com/Install-FFmpeg-on-Windows
* Instructions for Mac users: [install with HomeBrew (`brew install ffmpeg`)](http://jollejolles.com/install-ffmpeg-on-mac-os-x/)
* For Linux users: use your system's package manager to install ffmpeg, e.g. `sudo apt-get install ffmpeg`

Now you should be able to run Specky inside your environment:
```
conda activate specky_env
python application.py
# Use specky
# Print statements will appear here in the Terminal as you are using Specky
conda deactivate specky_env
```

## Using `specky` to label spectrogram clips
Specky allows you to label one or multiple attributes of `.WAV` or `.MP3` files. Files should be in one directory. It is easier to use specky to analyze short clips (on the scale of several seconds long) than long clips, which will not display as nicely in the interface.

The output of this process is a .csv file, formatted like the following.
```
filename,species_present,call_type
/path/to/file1.wav,present,song
/path/to/file2.mp3,absent,na
/path/to/file3.wav,present,call
```

The assessment process allows you to assign **labels** to **variables**. 
* In the above output, two **variables** are assessed: `species_present` and `call_type`. Variables are different criteria on which you want to assess the call.
* Different **labels** are possible for each of these variables. For instance, in the example above, the `species_present` variable contains the labels `present` and `absent`. The `call_type` variable is shown with three labels: `song`, `na`, and `call`. 

The options for labels appear as buttons in the interface. Currently, you must select exactly one label per variable. For instance, you can't select both `song` and `call` for the `call_type` variable. Likewise, you can't leave one variable unlabeled. In future versions, I hope to allow specification of a minimum and maximum number of labels you can choose for each column.

### Selecting your own assessment labels
To create your own assessment labels, create a .csv with the following format:
```
variable_A,A_label1,A_label2,...,A_labelX
variable_B,B_label1,B_label2,...,B_label3Y
```
 
You don't have to use the same number of labels for each variable.

The default assessment criteria are:
```
present,1,0,unsure
type,song,call,unsure,na
```


### Step-by-step
* Put your clips into one directory. `specky` finds all clips inside a directory and all of its subdirectories, so it is fine if your clips are separated into multiple subdirectories.
* Create a "labels" file of the format described above, if desired. Otherwise, the default assessment criteria will be used
* Run `python application.py` in a virtual environment containing the needed dependencies
* Click the "assess folder" button
* Select which folder you want to review clips from
* Navigate to the "labels" csv you created above, if desired, or press "cancel" to select a default label
* Name the file that you want to contain the results of your assessment from. If no name is selected, `specky` automatically creates a file, `assessment.csv`, within the folder you are reviewing clips from. If the filename chosen by you or generated by specky already exists, then you can choose one of the following options:
    - Picking up the assessment where you left off (only works if the variables in this file are the same as the variables you specified in the step above)
    - Overwriting the old assessment file
    - Selecting a different filename
* Assess the files by clicking one label per variable and clicking "next" when needed
