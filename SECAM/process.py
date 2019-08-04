#!/usr/bin/env python3
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

# max deviation of D'R, D'B is 230/280 of D'R
CHROMA_DEVIATION = 280e3

CHROMA_CENTRE = 4.286e6
CHROMA_MIN = 3.90000e6
CHROMA_MAX = 4.75625e6


MIX_LUMA = 0.9
MIX_CHROMA = 0.1

FM_DEMOD_GAIN = 6.5

CHUNK_SIZE = 4096

# Receiver colour balance correction
DR_ADJUST = 0 # -0.7    # D'R minus more red, plus more green
DB_ADJUST = 0 # -0.5 # +0.05   # D'B minus more yellow, plus more blue


FM_MOD_SENSITIVITY=2 * np.pi * CHROMA_DEVIATION

class simulatron:
    def __init__(self, filename, outfilename, samp_rate=12000000):
        self.samp_rate = samp_rate
        self.filename = filename
        self.frame_no = 0 # important for A/B chroma ordering

        width = samp_rate//15625

        self.source = imagesource(filename, samp_rate)
        self.rgb2ydbdr = rgb2ydbdr()
        self.ydbdr2rgb = ydbdr2rgb()
        self.sink = imagesink(outfilename, width, 625, recombine=True)

        self.probe_sink = imagesink('output/debug/modulated.png', width, 625,
                recombine=False)

        self.fm_mod = fm.fm_mod(FM_MOD_SENSITIVITY/self.samp_rate)

        self.fm_db = fm.carrier(self.samp_rate, DB_FREQ)
        self.fm_dr = fm.carrier(self.samp_rate, DR_FREQ)

        # pre-filter high frequencies in the luma
        # (verify using multiburst on the test card)

        self.y_prefilter = fm.chroma_reject(
            f1=CHROMA_MIN-15625*18, f2=CHROMA_MAX+15625*12, beta=3)

        #self.anticloche = fm.chroma_reject(
        #        center_hz=CHROMA_CENTRE,
        #        halfband=15625*10, beta=6)

        # chroma selector filter
        self.chroma_pass = fm.chroma_pass(
                ntaps=81*2, # this evens out the delay with Y
                f1=CHROMA_MIN-15625*9, f2=CHROMA_MAX+15625*1)

        # filters out chroma from the composite
        self.chroma_stop = fm.chroma_reject(
                f1 = CHROMA_MIN + 15625,
                f2 = CHROMA_MAX - 15625)

        self.plot_filters()

        self.fm_demod = fm.fm_demod(FM_DEMOD_GAIN)
        self.delay = fm.delay(width)

        # equalize delay for the line number/selector 
        self.line_delay = fm.delay(81)

        self.chunk = CHUNK_SIZE
        self.chunk_count = 0

        # identification pulses
        self.identify = fm.identify(samp_rate,width)

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

        # debug arrays
        self.debug_chroma = np.zeros(width * 16, np.float32)
        self.debug_chroma_i = len(self.debug_chroma)


    def calibrate(self, diapason, carrier_gen, dc_offset, 
            nbars = 7, tit='', ax=None, ax_spectrum=None,
            spectrum_color='r'):

        t = np.linspace(0, 1, self.chunk)
        ramp = diapason * signal.sawtooth(nbars * 2 * np.pi * t)

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
        #self.anticloche.general_work(filtered, filtered)

        self.plotSpectrum(filtered, self.samp_rate, ax=ax_spectrum,
                color=spectrum_color)
                 
        self.fm_demod.general_work(filtered, demodramp)
        self.fm_demod.general_work(filtered, demodramp)

        demodramp = demodramp[1:]

        demod_scale = 1  # don't scale, make sure that demod gain is set well
        demod_center = demodramp[ref_x]

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

        self.demod_scale,self.zero_b=self.calibrate(230/280,
                self.fm_db,0.7, nbars=7, tit='Db', ax=ax1,
                ax_spectrum=ax3, spectrum_color='#0000ff40')
        self.demod_scale,self.zero_r=self.calibrate(1.0,
                self.fm_dr,0.7, nbars=7, tit='Dr', ax=ax2,
                ax_spectrum=ax3, spectrum_color='#ff000040')

        plt.savefig('output/debug/calibration.png')
        
    def plot_filters(self):
        fig = plt.figure()
        ax = fig.subplots(1,1)
        self.chroma_pass.plot(self.samp_rate, ax=ax, color='r', 
                label='chroma pass')
        #self.anticloche.plot(self.samp_rate, ax = ax, color='g',
        #        label='anti cloche')
        self.chroma_stop.plot(self.samp_rate, ax=ax, color='b', 
                label='chroma stop')
        self.y_prefilter.plot(self.samp_rate, ax=ax, color='y', 
                label='y prefilter')
        plt.legend(loc='upper left')
        plt.savefig('output/debug/filters.png')

    def debug_hook(self, line, chroma):
        lookfor = 6 # 319
        f = np.searchsorted(line, lookfor)
        start = 0
        if f < len(line) and line[f] == lookfor:
            self.debug_chroma_i = 0
            start = f
        if self.debug_chroma_i < len(self.debug_chroma):
            end = min(self.debug_chroma_i + len(chroma[start:]), 
                    len(self.debug_chroma))
            l = end - self.debug_chroma_i
            self.debug_chroma[self.debug_chroma_i:end] = chroma[start:start+l]
            self.debug_chroma_i = end
            if self.debug_chroma_i >= len(self.debug_chroma):
                self.plot_debug_chroma(self.debug_chroma, lookfor)

    def plot_debug_chroma(self, chroma, line1):
        w = 768
        fig = plt.figure()
        f,ax = plt.subplots(1)
        ax.set_ylim([-1.8,1.8])
        x = np.linspace(line1, line1 + len(chroma)//768, len(chroma))
        ax.plot(x, chroma)
        plt.savefig('output/debug/identification.png')

    def modulate(self, rgb, line):
        # build odd/even selector using line number
        lined = self.lined
        self.line_delay.general_work(line, lined)

        sel = (lined + self.frame_no) % 2

        # RGB -> YDbDr
        self.rgb2ydbdr.general_work(rgb, self.y, self.db, self.dr)
        self.y_prefilter.general_work(self.y,self.y)

        # insert identification pulses
        self.identify.work_in_place(lined, self.db, self.dr)

        # scale db to 230/280 
        self.db = 230/280 * self.db

        # hard limit 
        self.db[self.db < -1.4] = -1.4
        self.db[self.db > 1.8] = 1.8

        self.dr[self.dr < -1.8] = -1.8
        self.dr[self.dr > 1.2] = 1.2

        # multiplex odd/even lines
        chroma_muxed = self.select(self.db,self.dr, sel)

        # fm modulate multiplexed chroma
        self.fm_mod.general_work(chroma_muxed, self.chroma_fm)

        self.debug_hook(lined, chroma_muxed)

        # generate FM carriers
        self.fm_db.work(self.carrier2[0])
        self.fm_dr.work(self.carrier2[1])

        # select carrier using line number
        carrier_muxed = self.select(self.carrier2[0], self.carrier2[1], sel)
        
        # multiply chroma by carrier
        cc = self.chroma_fm * carrier_muxed

        # anti cloche 
        #self.anticloche.general_work(cc, cc)

        secam = MIX_LUMA * self.y + MIX_CHROMA * cc

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

        #self.recv_y[:]=0.5
        #recv_db[:] = 0
        #recv_dr[:] = 0
        # YDbDr -> RGB
        self.ydbdr2rgb.general_work(self.recv_y, recv_db, recv_dr, self.rgb2)

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

if __name__ == '__main__':
    if len(sys.argv) > 1:
        inputfiles=[]
        for arg in sys.argv[1:]:
            inputfiles = inputfiles + list(glob.glob(arg)) 
    else:
        inputfiles=['testimages/testcard.png']

    if len(inputfiles) > 1:
        print("Processing multiple input images:\n%s" % ','.join(inputfiles))
        with Pool(4) as p:
            p.map(process_file, inputfiles)
    else:
        process_file(inputfiles[0])

    print("\nAll done")

