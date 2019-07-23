import numpy as np
from scipy import signal
from scipy.signal import fir_filter_design as ffd
from scipy.signal import filter_design as ifd
from scipy.signal import lfilter,lfiltic,freqz

class fm_mod:
    def __init__(self, sensitivity):
        #print("fm_mod: sensitivity=%f" % sensitivity)
        self.sensitivity = sensitivity
        self.phase = 0.0


    def general_work(self, in_f, out_c):
        # calculate phase offsets
        dphase = np.zeros(len(in_f), np.float32)
        for i in range(len(dphase)): 
            self.phase = self.phase + self.sensitivity * in_f[i]
            self.phase = (self.phase + np.pi) % (2*np.pi) - np.pi
            #print(self.phase)
            dphase[i] = self.phase 
        
        I = np.cos(dphase)
        Q = np.sin(dphase)
        #print("I,Q=", I, Q)
        out_c[:] = I + 1j*Q


class carrier:
    def __init__(self, samp_rate, freq_hz, amplitude = 1.0):
        self.samp_rate = samp_rate
        self.freq_hz = freq_hz
        self.amplitude = 1.0
        self.phase = 0.0

    def work(self, out_c):
        n = len(out_c) 
        phase2 = self.phase + n * 2 * np.pi * self.freq_hz / self.samp_rate

        arg = np.linspace(self.phase, phase2, num=n, endpoint=False)
        self.phase = (phase2 + np.pi) % (2*np.pi) - np.pi

        out_c[:] = self.amplitude * (np.cos(arg) + 1j*np.sin(arg))

class filter:
    def __init__(self, taps):
        self.b = taps
        self.z = lfiltic(self.b,[1.0],[0])

    def plot(self, samp_rate, filename=None, ax=None, color='b', label=None):
        w, h = signal.freqz(self.b)
        x = w * samp_rate * 1.0 / (2 * np.pi)
        import matplotlib.pyplot as plt
        if ax == None:
            ax = plt.figure()
            ax.set_title("Filter frequency response")
        ax.plot(x, 20 * np.log10(abs(h)), color, label=label)

    def general_work(self, in0, out0):
        tmp, zf = lfilter(self.b, [1.0], in0, zi=self.z)
        self.z = zf
        out0[:] = tmp

class chroma_pass(filter):
    def __init__(self, ntaps=81, f1=15625*272, f2=15625*282, 
            samp_rate=12e6, beta=6.76):
        #print("chroma pass: f1=%f f2=%f" % (f1,f2))
        taps = ffd.firwin(ntaps, 
                [2*f1/samp_rate, 2*f2/samp_rate],
                pass_zero=False,
                window=("kaiser",beta))
        filter.__init__(self, taps)

class chroma_reject(filter):
    def __init__(self, ntaps=81, f1=15625*272, f2=15625*282,
            samp_rate=12e6, beta=6.76):
        #print("chroma reject: f1=%f f2=%f" % (f1,f2))
        taps = ffd.firwin(ntaps, 
                [2*f1/samp_rate, 2*f2/samp_rate],
                pass_zero=True,
                window=("kaiser",beta))
        filter.__init__(self, taps)

class low_pass(filter):
    def __init__(self, ntaps=81, samp_rate=12e6):
        taps = ffd.firwin(ntaps, 0.75e6/samp_rate)
        filter.__init__(self, taps)


class fm_demod:
    def __init__(self, gain):
        self.history = 0+0j
        self.gain = gain

    def general_work(self, in0, out0):
        fu = np.hstack(([self.history],in0))
        self.history = in0[-1]
        tmp = fu[:-1] * np.conj(fu[1:])
        #tmp = np.conj(fu[:-1]) * fu[1:]

        real = np.array(np.real(tmp * 1e6), np.int) * 1e-6
        imag = np.array(np.imag(tmp * 1e6), np.int) * 1e-6
        out0[:] = self.gain * np.arctan2(real, imag)
        return len(out0)

class delay:
    def __init__(self, n):
        self.buffer = np.zeros(int(n), np.float32)

    def general_work(self, in0, out):
        out[:len(self.buffer)] = self.buffer
        out[len(self.buffer):] = in0[:len(out)-len(self.buffer)]
        self.buffer[:] = in0[len(out)-len(self.buffer):]

class identify:
    INITIAL = 0
    WORK = 1

    def __init__(self, samp_rate, line_width):
        self.position = -1
        self.state = identify.INITIAL
        self.start, self.end = None,None
        self.endline = 0

        # D'R sandcastle: 4.406 up to 4.756 MHz, rise time 15us (looks up)
        # D'R = 0..1.25 ~ 350kHz
        #dr = self.sandcastle(samp_rate, line_width, 1.25, margin=0.0) 
        #print("D'R niveau=", dr[-100])

        # D'B sandcastle: 4.250 to 3.900 MHz, rise time 18us (looks down)
        #db = self.sandcastle(samp_rate, line_width, 1.52, margin=2.3e-6)
        #print("D'B niveau=", db[-100])

        dr = self.sandcastle2(samp_rate, line_width, margin = 0)
        db = self.sandcastle2(samp_rate, line_width, margin = 2.3e-6)

        self.db_impulses = -np.array(list(db)*10)
        self.dr_impulses = np.array(list(dr)*10)

    def sandcastle2(self, samp_rate, line_width, margin):
        lm = int(samp_rate * margin)
        m = np.zeros(lm)
        # on commence con un signal scie
        scie = np.hstack([m, np.linspace(0, 5.5, line_width - 2 * lm), m])
        return scie

    # TODO: 
    # this version assumes that the chunks are smaller than frames
    def work_in_place(self, line, db, dr):
        start = 0

        if self.state == identify.INITIAL:
            # pulses in line numbers [7..15] and [320..328] (zero based)
            # look for lines 7 and 320
            f = np.searchsorted(line, [7,320])
            if f[0] < len(line) and line[f[0]] == 7:
                self.state = identify.WORK
                self.line_no = line[f[0]]
                self.end_line_no = self.line_no + 9
                start = f[0]
                self.position = 0
            elif f[1] < len(line) and line[f[1]] == 320:
                self.state = identify.WORK
                self.line_no = line[f[1]]
                self.end_line_no = self.line_no + 9
                start = f[1]
                self.end = -1
                self.position = 0

        if self.state == identify.WORK:
            end = line.searchsorted(self.end_line_no)
            if end == len(line):
                # end_line_no not found in line
                end = None
            else:
                self.state = identify.INITIAL

            length = len(db[start:end])
            p,self.position = self.position, self.position + length
            db[start:end] = self.db_impulses[p:self.position]
            dr[start:end] = self.dr_impulses[p:self.position]

            # cool way to detect line number changes
            # sync = np.abs(np.sign(np.convolve(line,[1,-1])))[:-1] * line
            

        
