import warnings
import numpy as np
from scipy import signal, ndimage
from sys import platform as sys_pf
if sys_pf == 'darwin':
    import matplotlib
    matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
from librosa import load, to_mono
import os
from scipy.signal import butter, lfilter
from librosa.core import power_to_db
from collections import OrderedDict


small_txt = 7
med_txt = 8
big_txt = 8
# set text sizes
plt.rcParams['font.size'] = small_txt
plt.rcParams['axes.labelsize'] = med_txt
plt.rcParams['axes.titlesize'] = big_txt
plt.rcParams['xtick.labelsize'] = small_txt
plt.rcParams['ytick.labelsize'] = small_txt
plt.rcParams['legend.fontsize'] = med_txt
plt.rcParams['figure.titlesize'] = big_txt
# Transparent background color
plt.rcParams['figure.facecolor'] = (0.0, 0.0, 0.0, 0.0)
# # set figure size
plt.rcParams['figure.figsize']=[6,2.5]
# set default font
# plt.rcParams['font.sans-serif'] = "Gill Sans"
# plt.rcParams['font.family'] = "sans-serif"
plt.rcParams['font.sans-serif'] = "Gill Sans"
# #https://coolors.co/35aad8-f3b61f-ba3b54-45b69c-8a96d7
# plt.rc('lines', linewidth=2)



def plotter(
    spectrogram,
    frequencies,
    times,
    ax,
    title = None
):
    ax.set_title(title)
    ax.pcolormesh(times, frequencies, power_to_db(spectrogram), cmap=plt.get_cmap("gray_r"), shading='auto')
    ax.set_xlabel("time (sec)")
    ax.set_ylabel("frequency (Hz)")



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


    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning) #ignore mp3 import warning

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
