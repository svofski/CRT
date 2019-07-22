import numpy as np
import fm
from scipy.fftpack import fft
from matplotlib import pyplot as plt 

def plotSpectrum(y,Fs,col,label):
    n = len(y) # length of the signal
    k = np.arange(n)
    T = n/Fs
    frq = k/T # two sides frequency range
    frq = frq[range(n//2)] # one side frequency range

    Y = fft(y)/n # fft computing and normalization
    freqs = np.fft.fftfreq(len(Y))
    idx = np.argmax(np.abs(Y))
    freq=freqs[idx]

    Y = Y[range(n//2)]

    #w = np.fft.fft(output)
    print(freqs.min(), freqs.max())
    freq_hz = abs(freq * Fs)
    print("Peak freq: ", round(freq_hz), "Hz")
    plt_label = "%s Peak: %4.2fHz" % (label, freq_hz)

    plt.plot(frq,abs(Y),col, label=plt_label)
    plt.xlabel('Freq (Hz)')
    plt.ylabel('|Y(freq)|')
    plt.legend(loc='upper left')


def test_modulation():
    N=int(12e6/15625/16)

    fm_mod = fm.fm_mod(1)
    fm_demod = fm.fm_demod(1)

    sig = np.linspace(-1.3, 1.3, N, np.float32)
    modsig = np.zeros(N, np.complex64)
    demodsig = np.zeros(N, np.float32)

    fm_mod.general_work(sig, modsig)

    #modsig = modsig + 1

    fm_demod.general_work(modsig, demodsig)

    plt.plot(sig, label="+ source")
    plt.plot(np.real(modsig), label="+ modulated real")
    plt.plot(np.imag(modsig), label="+ modulated imag")
    plt.plot(demodsig, label="+ demodulated")
    plt.legend(loc='upper left')
    plt.show()

# test frequency deviation

def test_freq_deviation():
    N = int(12e6/15625*16)
    samp_rate = 12e6
    CHROMA_HALFBAND = 280e3
    fm_mod = fm.fm_mod(2*np.pi*CHROMA_HALFBAND/samp_rate)
    input = np.ones(N)
    output = np.zeros(N, np.complex64)
    fm_mod.general_work(input, output)

    plt.figure()
    plotSpectrum(output, samp_rate, 'r', "Projected Δf₀R = 280kHz")

    input = np.ones(N) * 230/280
    fm_mod.general_work(input, output)
    plotSpectrum(output, samp_rate, 'b', "Projected Δf₀B = 230kHz")

    plt.show()


test_freq_deviation()
#test_modulation()

exit()

gen = fm.carrier(1e3, 10, 1.0)
cc = np.zeros(N, np.complex64)
gen.work(cc)

negen = fm.carrier(1e3, -10, 1.0)
nc = np.zeros(N, np.complex64)
negen.work(nc)

plt.plot(np.real(cc), label="+ carrier real")
plt.plot(np.imag(cc), label="+ carrier imag")



plt.legend(loc='upper left')
plt.show()

plt.plot(np.real(nc), label="- carrier real")
plt.plot(np.imag(nc), label="- carrier imag")
plt.legend(loc='upper left')
plt.show()


