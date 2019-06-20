import numpy as np
from scipy import signal, ndimage
from sys import platform as sys_pf
if sys_pf == 'darwin':
    import matplotlib
    matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
from librosa import load, to_mono
from librosa.output import write_wav
import noisereduce as nr
from skimage.morphology import remove_small_objects
from more_itertools import consecutive_groups
import os
from scipy.signal import butter, lfilter
from librosa.core import power_to_db
from collections import OrderedDict


def plotter(
    spectrogram,
    ax,
    title=None,
    upside_down = False,
    db=True, #db transform the spect
):
    # Plot, flip the y-axis
    if db:
        ax.imshow(power_to_db(spectrogram), cmap=plt.get_cmap("gray_r"))
    else:
        ax.imshow(spectrogram, cmap=plt.get_cmap("gray_r"))
    if upside_down:
        ax.set_ylim(ax.get_ylim()[::-1])
    if title:
        ax.set_title(title, fontsize=12)
        
    ax.set_aspect(spectrogram.shape[1] / spectrogram.shape[0])

    #return fig
    #plt.show()
    
    

def load_file(filename, sample_rate=22050):
    '''
    Load samples from an audio file
    
    Inputs:
        filename: path to audio file from which to make spectrogram (optional)
        sample_rate: rate at which to resample audio
    
    Returns:
        samples: the samples from the wav file
        sample_rate: the sample rate from the wav file
    '''
    
    samples, sample_rate = load(
        filename,
        mono=False,  # Don't automatically load as mono, so we can warn if we force to mono
        sr=sample_rate, # Resample
        res_type='kaiser_best',
    )
    
    # Force to mono if wav has multiple channels
    if samples.ndim > 1:
        samples = to_mono(samples)
        #print(
        #    f"WARNING: Multiple-channel file detected ({filename}). Automatically mixed to mono."
        #)
        
    return samples, int(sample_rate)


def make_spect(samples, samples_per_seg, overlap_percent, sample_rate=22050):
    '''
    Make spectrogram from an audio file
    
    If filename is provided, uses librosa to load samples from filename. Else,
    preloaded_samples must be provided; will generate a spectrogram from these samples
    
    Inputs:
        samples: mono samples loaded from an audio file
        samples_per_seg: window size for spectrogram
        overlap_percent: overlap percent for spectrogram (between 0 and 1)
        sample_rate: sample rate for audio
        preloaded_samples: (optional) already-loaded samples
    
    Returns:
        frequencies - sample frequencies
        times - time for each segment
        spectrogram - spectrogram values
    '''

    
    overlap_per_seg = samples_per_seg * overlap_percent

    frequencies, times, spectrogram = signal.spectrogram(
        samples,
        sample_rate,
        window='hann',
        nperseg=samples_per_seg,
        noverlap=overlap_per_seg,
        nfft=512)
    
    return frequencies, times, spectrogram

