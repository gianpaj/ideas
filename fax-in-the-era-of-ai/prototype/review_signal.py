"""Independent FFT-band-energy check, not a standards-qualified DTMF receiver."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d

ROWS = np.array([697., 770., 852., 941.])
COLS = np.array([1209., 1336., 1477.])
KEYS = ['123', '456', '789', '*0#']


def inspect(path):
    sr, raw = wavfile.read(path)
    x = raw.astype(float)
    if np.issubdtype(raw.dtype, np.integer):
        x /= max(abs(np.iinfo(raw.dtype).min), np.iinfo(raw.dtype).max)
    if x.ndim == 2:
        x = x.mean(axis=1)
    n = round(.04 * sr)
    hop = round(.005 * sr)
    f, t, z = signal.stft(x, sr, window='hann', nperseg=n,
                          noverlap=n-hop, nfft=8192, boundary=None, padded=False)
    p = abs(z)**2
    powers = np.stack([p[abs(f-f0) < 22].sum(axis=0) for f0 in np.r_[ROWS, COLS]])
    total = p[(f > 300) & (f < 3400)].sum(axis=0)
    r, c = powers[:4], powers[4:]
    ri, ci = r.argmax(axis=0), c.argmax(axis=0)
    rs, cs = np.sort(r, axis=0), np.sort(c, axis=0)
    twist = 10*np.log10(np.maximum(rs[-1], 1e-20) / np.maximum(cs[-1], 1e-20))
    purity = (rs[-1]+cs[-1]) / np.maximum(total, 1e-20)
    # Reject weak delayed echoes, using observed local energy only (no timing oracle).
    local_peak = maximum_filter1d(total, size=49, mode='nearest')
    valid = ((rs[-1] > 3*rs[-2]) & (cs[-1] > 3*cs[-2]) &
             (abs(twist) < 9) & (purity > .42) & (total > 1e-7) &
             (total > .10*local_peak))
    labels = [KEYS[a][b] if v else None for a,b,v in zip(ri,ci,valid)]
    events = []
    start = 0
    for i in range(1, len(labels)+1):
        if i < len(labels) and labels[i] == labels[start]:
            continue
        duration = (i-start)*hop/sr
        if labels[start] is not None and duration >= .035:
            events.append({'digit': labels[start], 'center_run_start_s': round(float(t[start]),3),
                           'center_run_end_s': round(float(t[i-1]),3)})
        start = i
    result = {'file': str(path), 'sample_rate': sr, 'duration_s': len(x)/sr,
              'peak_dbfs': float(20*np.log10(max(np.max(abs(x)),1e-20))),
              'clipped_samples': int(np.sum(abs(x) >= .9999)),
              'digits': ''.join(e['digit'] for e in events), 'events':events,
              'method':'independent 40ms Hann FFT, 5ms hop; 245ms local-energy echo gate; no frame/timeline input'}
    return result, (sr,x,f,t,p)


def plot(data, events, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    sr,x,f,t,p = data
    fig, ax = plt.subplots(2,1,figsize=(16,6),sharex=True,
                           gridspec_kw={'height_ratios':[1,3]}, layout='constrained')
    ax[0].plot(np.arange(len(x))/sr,x,color='#2678b2',linewidth=.35)
    ax[0].set(ylabel='PCM amplitude',title='Agent phone handshake — actual noisy waveform and spectrogram')
    sel=(f>=300)&(f<=3400)
    im=ax[1].pcolormesh(t,f[sel],10*np.log10(np.maximum(p[sel],1e-12)),
                        shading='auto',vmin=-65,vmax=-20,cmap='magma')
    ax[1].set(xlabel='Time after answer (seconds)',ylabel='Frequency (Hz)',ylim=(300,3400))
    for e in events:
        mid=(e['center_run_start_s']+e['center_run_end_s'])/2
        ax[1].text(mid,3100,e['digit'],ha='center',va='center',fontsize=7,color='white')
    fig.colorbar(im,ax=ax[1],label='STFT power (dB, scipy scaling)')
    fig.savefig(path,dpi=140)
    plt.close(fig)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wav',type=Path)
    parser.add_argument('--plot',type=Path)
    args=parser.parse_args()
    result,data=inspect(args.wav)
    if args.plot:
        plot(data,result['events'],args.plot)
    print(json.dumps(result,indent=2))
