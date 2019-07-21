import sys
import os
import numpy as np
from scipy.fftpack import fft
from scipy import signal
from matplotlib import pyplot as plt 

from imagesource import imagesource
from imagesink import imagesink
from colorspace import rgb2ydbdr, ydbdr2rgb
import fm

DB_FREQ = 15625 * 272
DR_FREQ = 15625 * 282
# max deviation of D'R/D'B
# D'R should be +/-1.3  and map to +/- 280kHz
# D'B should be +/-1.05 and map to +/- 230kHz
CHROMA_HALFBAND = 300e3  

MIX_LUMA = 0.7
MIX_CHROMA = 0.1

FM_DEMOD_GAIN = 8.5

CHUNK_SIZE = 4096

# Receiver colour balance correction
DR_ADJUST = 0 # -0.7    # D'R minus more red, plus more green
DB_ADJUST = 0 # -0.5 # +0.05   # D'B minus more yellow, plus more blue

# -1.3..+1.3 input at this sensitivity should give -280..280kHz deviation
FM_MOD_SENSITIVITY=2 * np.pi * CHROMA_HALFBAND*0.75 

class simulatron:
    def __init__(self, filename, outfilename, samp_rate=12000000):
        self.samp_rate = samp_rate
        self.filename = filename

        width = samp_rate//15625

        self.source = imagesource(filename, samp_rate)
        self.rgb2ydbdr = rgb2ydbdr()
        self.ydbdr2rgb = ydbdr2rgb()
        self.sink = imagesink(outfilename, width, 625)

        self.probe_sink = imagesink('output/debug/modulated.png', width, 625)

        self.fm_mod = fm.fm_mod(FM_MOD_SENSITIVITY/self.samp_rate)

        self.fm_db = fm.carrier(self.samp_rate, DB_FREQ)
        self.fm_dr = fm.carrier(self.samp_rate, DR_FREQ)

        # pre-filter high frequencies in the luma
        # (verify using multiburst on the test card)
        self.y_prefilter = fm.chroma_reject(center_hz=(DB_FREQ+DR_FREQ)/2,
            halfband = CHROMA_HALFBAND*3)

        # chroma selector filter
        self.chroma_pass = fm.chroma_pass(
                ntaps=81*2, # this is only to even out the delay with Y
                center_hz=(DB_FREQ+DR_FREQ)/2,
                halfband=CHROMA_HALFBAND*1.75)

        # filters out chroma from the composite
        self.chroma_stop = fm.chroma_reject(center_hz=(DB_FREQ+DR_FREQ)/2,
                halfband=CHROMA_HALFBAND*1.25)

        self.plot_filters()

        self.fm_demod = fm.fm_demod(FM_DEMOD_GAIN)
        self.delay = fm.delay(width)
        self.ydelay = fm.delay(len(self.chroma_pass.b)//2)

        # equalize delay for the line number/selector 
        self.line_delay = fm.delay(81)

        self.chunk = CHUNK_SIZE
        self.chunk_count = 0

        # identification pulses
        self.identify = fm.identify(width)

        # create arrays
        self.lined = np.zeros(self.chunk, np.int32)
        self.y = np.zeros(self.chunk, np.float32)
        self.db = np.zeros(self.chunk, np.float32)
        self.dr = np.zeros(self.chunk, np.float32)
        self.chroma_fm = np.zeros(self.chunk, np.complex64)
        self.carrier2 = np.zeros((2,self.chunk), np.complex64)

        # demod arrays
        self.chroma0 = np.zeros(self.chunk, np.complex64)
        self.chromaA = np.zeros(self.chunk, np.float32)
        self.chromaB = np.zeros(self.chunk, np.float32)
        self.recv_y = np.zeros(self.chunk, np.float32)
        self.rgb2 = np.zeros((self.chunk,3), np.float32)


    def calibrate(self, diapason, carrier_gen, dc_offset, 
            nbars = 7, tit='', ax=None, ax_spectrum=None,
            spectrum_color='r'):

        t = np.linspace(0, 1, self.chunk)
        ramp = signal.sawtooth(nbars * 2 * np.pi * t)

        # insert zero reference in the middle 
        ref_x = len(ramp) - 2 * len(ramp)//nbars
        ramp[ref_x-len(ramp)//nbars:ref_x+len(ramp)//nbars] = 0

        modramp = np.zeros(len(ramp), np.complex64)
        demodramp = np.zeros(len(ramp), np.float32)
        self.fm_mod.general_work(ramp, modramp)

        carrier = np.zeros(len(ramp), np.complex64)
        carrier_gen.work(carrier)
        modramp = modramp * carrier
        dcramp = signal.sawtooth(nbars * 2 * np.pi * t, width = 0.5)
        modramp = modramp + dc_offset * dcramp

        filtered = modramp
        filtered = np.zeros(len(ramp), np.complex64)
        self.chroma_pass.general_work(modramp, filtered)
        self.chroma_pass.general_work(modramp, filtered)

        self.plotSpectrum(filtered, self.samp_rate, ax=ax_spectrum,
                color=spectrum_color)
                 
        self.fm_demod.general_work(filtered, demodramp)
        self.fm_demod.general_work(filtered, demodramp)

        demodramp = demodramp[1:]

        demod_scale = 1  # don't scale, make sure that demod gain is set well
        demod_center = demodramp[ref_x]

        #print("calibrate: demod_scale=%f demod_center=%f" % 
        #    (demod_scale, demod_center))

        demodramp = demodramp - demod_center

        ax.set_title("%s calibration: zero at %3.3f" % (tit, demod_center))
        ax.plot(ramp, label='input')
        ax.plot(np.real(modramp), '#ff000030', 
                label='modulated with dc offsets')
        ax.plot(demodramp, 'g', label='demodulated and recentered')
        ax.legend(loc='upper left')

        return demod_scale, demod_center


    def calibrate_dbdr(self):
        fig = plt.figure()
        #f,ax = plt.subplots(2,2,sharey='row')
        gs = fig.add_gridspec(2,2)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1], sharey = ax1)
        ax3 = fig.add_subplot(gs[1, :])

        ax3.set_title('Modulated signal spectra')

        self.demod_scale,self.zero_b=self.calibrate(1.3,self.fm_db,0.7,
                nbars=7, tit='Db', ax=ax1,
                ax_spectrum=ax3, spectrum_color='#0000ff40')
        self.demod_scale,self.zero_r=self.calibrate(1.05,self.fm_dr,0.7,
                nbars=7, tit='Dr', ax=ax2,
                ax_spectrum=ax3, spectrum_color='#ff000040')
        plt.savefig('output/debug/calibration.png')
        
    def plot_filters(self):
        fig = plt.figure()
        ax = fig.subplots(1,1)
        self.chroma_pass.plot(self.samp_rate, ax=ax, color='r', 
                label='chroma pass')
        self.chroma_stop.plot(self.samp_rate, ax=ax, color='b', 
                label='chroma stop')
        self.y_prefilter.plot(self.samp_rate, ax=ax, color='y', 
                label='y prefilter')
        plt.legend(loc='upper left')
        plt.savefig('output/debug/filters.png')

    def modulate(self, rgb, line):
        # build odd/even selector using line number
        self.line_delay.general_work(line % 2, self.lined)
        sel = self.lined

        # RGB -> YDbDr
        self.rgb2ydbdr.general_work(rgb, self.y, self.db, self.dr)
        self.y_prefilter.general_work(self.y,self.y)

        # zero out chroma components for testing
        #db[:] = 0
        #dr[:] = 0

        # insert identification pulses
        self.identify.work_in_place(line, self.db, self.dr)

        # multiplex odd/even lines
        chroma2 = np.array((self.db,self.dr))
        chroma_muxed = chroma2[0] * sel + chroma2[1] * (1-sel)

        # fm modulate multiplexed chroma
        self.fm_mod.general_work(chroma_muxed, self.chroma_fm)

        # generate FM carriers
        self.fm_db.work(self.carrier2[0])
        self.fm_dr.work(self.carrier2[1])

        # select carrier using line number
        carrier_muxed = self.carrier2[0] * sel + self.carrier2[1] * (1-sel)
        
        # multiply chroma by carrier
        carrier_chroma = self.chroma_fm * carrier_muxed
        secam = MIX_LUMA * self.y + MIX_CHROMA * carrier_chroma

        # save modulated grayscale image
        magnitude = np.real(np.sqrt((secam*secam)))
        probnik = np.array((magnitude,magnitude,magnitude)).swapaxes(0,1)
        self.probe_sink.work(probnik)

        return secam, sel

    def demodulate(self, secam, sel):
        count = len(secam)

        # bandpass filter chroma in its subcarrier frequency range
        self.chroma_pass.general_work(secam, self.chroma0)

        self.fm_demod.general_work(self.chroma0, self.chromaA)

        # this is the colour delay line
        self.delay.general_work(self.chromaA, self.chromaB)

        # remove chroma from the composite signal
        self.chroma_stop.general_work(np.real(secam), self.recv_y)

        # switchover the direct and delayed signals
        recv_db = self.select(self.chromaA, self.chromaB, sel)-self.zero_b \
            + DB_ADJUST 
        recv_dr = self.select(self.chromaB, self.chromaA, sel)-self.zero_r \
            + DR_ADJUST

        # YDbDr -> RGB
        self.ydbdr2rgb.general_work(self.recv_y,recv_db,recv_dr,self.rgb2)

        return self.rgb2

    def run(self):
        self.calibrate_dbdr()

        count = 1

        # preload the output image sink so that it's aligned horizontally
        # after all the filters
        self.sink.work(np.zeros((768-81*2,3), np.float32))

        rgb_samples = np.zeros((self.chunk,3), np.float32)
        line = np.zeros((self.chunk), np.int32)

        while count > 0:
            count = self.source.work(rgb_samples, line)
            if count == -1:
                break

            secam,sel = self.modulate(rgb_samples[:count], line[:count])
            rgb2 = self.demodulate(secam, sel)
            self.sink.work(rgb2)
            self.chunk_count = self.chunk_count + 1
            #print('.', end='', flush=True)

    def select(self, A, B, sel):
        return A * sel + B * (1-sel)

    def plot_spectrum(self, cc, zx):
        self.plotSpectrum(cc, self.samp_rate)
        plt.savefig(zx)

    def plotSpectrum(self,y,Fs,ax=None,color='r',label=None):
        n = len(y) # length of the signal
        k = np.arange(n)
        T = n/Fs
        frq = k/T # two sides frequency range
        frq = frq[range(n//2)] # one side frequency range

        Y = fft(y)/n # fft computing and normalization
        Y = Y[range(n//2)]

        if ax == None:
            plt.figure()
            ax = plt
        plt.plot(frq, abs(Y), color, label=label)
        plt.xlabel('Freq (Hz)')
        plt.ylabel('|Y(freq)|')

def process_file(inputfile):
    outfile=os.path.join('output', os.path.split(inputfile)[1])
    s = simulatron(inputfile, outfile)
    s.run()
    print('.', end='')

from multiprocessing import Pool
import glob

def cock(inputfile):
    print("cock: ", inputfile)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        inputfiles=[]
        for arg in sys.argv[1:]:
            inputfiles = inputfiles + list(glob.glob(arg)) 
    else:
        inputfiles=['testimages/testcard.png']

    print("Processing multiple input images:\n%s" % ','.join(inputfiles))
    with Pool(4) as p:
        p.map(process_file, inputfiles)

    print("\nAll done")

