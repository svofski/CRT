#!/usr/bin/env python
from png import Reader, Writer
from random import random
import itertools
import math
from multiprocessing import Process, Queue, Array
from time import sleep
from Queue import Empty

# subcarrier frequency
Fsc=4433618.75

# line frequency
Fline=15625

# subcarrier counts per scan line = Fsc/Fline = 283.7516

# phase noise (0.3 for moderately crappy RF cable)
PHASE_NOISE = 0

# use biquads to filter components, otherwise moving average
MODE_MOVING_AVERAGE, MODE_BIQUADS, MODE_FIR = 0, 1, 2
MODE = MODE_FIR

# FIR lowpass gain 
FIR_GAIN = 1.5
# Inverse gain for luma recovery (correct for stripes) 1.1 seems to be working well
FIR_INV_GAIN = 1.1

# Use filters in the encoder 
ENCODER_FILTERS = False

# Pass values as floats (seems to have little to no effect)
PASSFLOAT=False

# Number of encoder threads
NENCODERS = 2

# Number of decoder threads
NDECODERS = 4

def nslice(s, n, truncate=False, reverse=False):
    """Splits s into n-sized chunks, optionally reversing the chunks."""
    assert n > 0
    while len(s) >= n:
        if reverse: yield s[:n][::-1]
        else: yield s[:n]
        s = s[n:]
    if len(s) and not truncate:
        yield s

def RGBtoYUV(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    Y = 0.299*r + 0.587*g + 0.114*b
    U = 0.492*(b - Y)
    V = 0.877*(r - Y)
    return Y,U,V  

def YUVtoRGB(y, u, v):
    return y + 1.14 * v,\
      y - 0.396 * u - 0.581 * v,\
      y + 2.029 * u

def clamp(p):
    if p < 0: 
      return 0
    elif p > 1.0: 
      return 1.0
    return p

class Delay:
    def __init__(self, taps):
        self.taps = taps
        self.x = [0] * taps
        self.i = 0

    def delay(self, x):
        result = self.x[self.i]
        self.x[self.i] = x
        self.i = self.i + 1 
        if self.i == self.taps:
            self.i = 0
        return result

class Fir:
    # lowpass
    # b=fir1(order, [0.01 0.1], kaiser(order+1, 1.0));
    T=[-0.008030271,0.003107906,0.016841352,0.032545161,0.049360136,0.066256720,0.082120150,0.095848433,0.106453014,0.113151423,0.115441842,0.113151423,0.106453014,0.095848433,0.082120150,0.066256720,0.049360136,0.032545161,0.016841352,0.003107906]

    scale = FIR_GAIN
    Order = len(T)

    def filter(self, input, index):
        u, v = 0, 0
        for i in xrange(self.Order):
            u, v = u + self.scale * self.T[i] * input[i - self.Order/2 + index][0],\
                   v + self.scale * self.T[i] * input[i - self.Order/2 + index][1]
        return (u,v)


class Biquad:
    # h/t Nigel Redmon 
    # http://www.earlevel.com/main/2011/01/02/biquad-formulas/

    a0,a1,a2,b1,b2 = 0, 0, 0, 0, 0
    x_1, x_2, y_1, y_2 = 0, 0, 0, 0

    def filter(self, x):
        result = self.a0*x + self.a1*self.x_1 + self.a2*self.x_2 - self.b1*self.y_1 - self.b2*self.y_2
        self.x_2 = self.x_1
        self.x_1 = x
        self.y_2 = self.y_1
        self.y_1 = result
        return result

    def lowpass(self, sampleRate, freq, Q):
        K = math.tan(math.pi * freq/sampleRate)
        norm = 1 / (1 + K / Q + K * K)
        self.a0 = K * K * norm
        self.a1 = 2 * self.a0
        self.a2 = self.a0
        self.b1 = 2 * (K * K - 1) * norm
        self.b2 = (1 - K / Q + K * K) * norm
        return self        

    def bandpass(self, sampleRate, freq, Q):
        K = math.tan(math.pi * freq/sampleRate)
        norm = 1.0 / (1 + K / Q + K * K)
        self.a0 = K / Q * norm
        self.a1 = 0.0
        self.a2 = -self.a0
        self.b1 = 2 * (K * K - 1) * norm
        self.b2 = (1 - K / Q + K * K) * norm
        return self

    def notch(self, sampleRate, freq, Q):
        K = math.tan(math.pi * freq/sampleRate)
        norm = 1 / (1 + K / Q + K * K)
        self.a0 = (1 + K * K) * norm
        self.a1 = 2 * (K * K - 1) * norm
        self.a2 = self.a0
        self.b1 = self.a1
        self.b2 = (1 - K / Q + K * K) * norm
        return self


def clamp_scale(p):
    if p < 0: 
      p = 0
    elif p > 1.0: 
      p = 1.0
    return int(p * 255)

def clamp_scale3(p):
    return [clamp_scale(x) for x in p]


halfpi = math.pi / 2

class Encoder:
    def __init__(self, encoderId, pixelQueue, queue, queue2, width_ratio, height_ratio):
        self.encoderId = encoderId
        self.pixelQueue = pixelQueue
        self.queue = queue
        self.queue2 = queue2
        self.width_ratio = width_ratio
        self.height_ratio = height_ratio
        self.result = []

        self.notch = Biquad().notch(Fsc * width_ratio, Fsc, 0.7)
        self.ufilter = Biquad().lowpass(Fsc * width_ratio, 1.2e6, 0.8)
        self.vfilter = Biquad().lowpass(Fsc * width_ratio, 1.2e6, 0.8)

    def Encode(self, rgb, sinwt, coswt):
        y,u,v = RGBtoYUV(rgb)
        if ENCODER_FILTERS:
            y = self.notch.filter(y)
            u = self.ufilter.filter(u)
            v = self.vfilter.filter(v)
        return clamp(y + u * sinwt + v * coswt)

    def run(self):
        pixelline = 0

        #for linepixels in self.pixels:
        while True:
            pixelline, linepixels = self.pixelQueue.get()
            if pixelline == -1: 
                break
            line = int(round(pixelline / self.height_ratio)) % 2
            wt = (180.0 + [+90,-90][line]) / 180.0 * math.pi
            yavg, uavg, vavg = 0, 0, 0

            encoded = [0] * (len(linepixels) / 3)
            t = 0
            for inputrgb in nslice(linepixels, 3):
                wt = t * 2 * math.pi / self.width_ratio # + [ +halfpi, -halfpi][line]
                sinwt = math.sin(wt)
                coswt = [+1,-1][line] * math.cos(wt)

                pal = self.Encode(inputrgb, sinwt, coswt)
                if PASSFLOAT:
                    encoded[t] = pal
                else:
                    encoded[t] = int(pal * 255)

                t = t + 1

            self.result.append(encoded)
            #print 'Encoder puts %d' % pixelline
            self.queue.put((pixelline, encoded))
            self.queue2.put((pixelline, encoded))
        # ensure that all consumers get their termination flags
        #print 'Encoder is terminating'
        sleep(0.1)
        self.queue.put((-1, None))
        self.queue2.put((-1, self.encoderId))
        #print 'Encoder is done for'

class Decoder:
    def __init__(self, decoderId, inputQueue, outputQueue, width_ratio, height_ratio):
        self.decoderId = decoderId
        self.inputQueue = inputQueue
        self.outputQueue = outputQueue
        self.width_ratio = width_ratio
        self.height_ratio = height_ratio

        # fir chroma
        self.uvfir = Fir()

        # chroma U/V lowpass filters
        self.fitlerU = Biquad().lowpass(Fsc * width_ratio, 1.0e6, 0.8)
        self.fitlerV = Biquad().lowpass(Fsc * width_ratio, 1.0e6, 0.8)
        self.yavg, self.uavg, self.vavg = 0, 0, 0

    def Decode(self, data, i, sinwt, coswt):
        pal = data[i]
        if MODE == MODE_MOVING_AVERAGE:
            self.yavg = (self.yavg + pal) / 2.0
            y_ = self.yavg
            u_ = (pal - y_) * 2 * sinwt
            v_ = (pal - y_) * 2 * coswt
            self.uavg = (self.uavg + u_) / 2
            self.vavg = (self.vavg + v_) / 2
            u_ = self.uavg
            v_ = self.vavg 
        elif MODE == MODE_BIQUADS:
            color = pal # self.fitler.filter(pal)
            u_ = color * 2 * sinwt
            v_ = color * 2 * coswt
            u_ = self.fitlerU.filter(u_)
            v_ = self.fitlerV.filter(v_)

            # transpose colour back to Fsc and subtract from composite
            y_ = pal - (u_ * sinwt + v_ * coswt)
            #y_ = self.notch.filter(pal) # - color
        
        return YUVtoRGB(y_, u_, v_)

    def DecodeFIR(self, data, fromidx, toidx, line):
        uv = [(0,0)] * len(data)
        uv_ = [(0,0)] * len(data)
        zerot = PHASE_NOISE * (random() - 0.5)
        t = zerot
        for i in xrange(fromidx, toidx):
            wt = t * 2 * math.pi / self.width_ratio
            sinwt = math.sin(wt)
            coswt = [+1,-1][line] * math.cos(wt)
            uv[i] = (data[i] * sinwt, data[i] * coswt)
            t = t + 1
        for i in xrange(fromidx, toidx):
            uv_[i] = self.uvfir.filter(uv, i)
        rgb = []
        t = zerot
        for i in xrange(fromidx, toidx):
            wt = t * 2 * math.pi / self.width_ratio
            sinwt = math.sin(wt)
            coswt = [+1,-1][line] * math.cos(wt)
            y = data[i + 0] - (FIR_INV_GAIN * uv_[i][0] * sinwt + FIR_INV_GAIN * uv_[i][1] * coswt)
            r, g, b = YUVtoRGB(y, uv_[i][0], uv_[i][1])
            rgb = rgb + clamp_scale3([r,g,b])
            t = t + 1
        return rgb

    def run(self):
        while True:            
            pixelline, encoded = self.inputQueue.get(True)
            #print 'Decoder %d pick %d' % (self.decoderId, pixelline)
            if pixelline == -1:
                if self.inputQueue.empty():
                    break
                else:
                    continue

            t = PHASE_NOISE * (random() - 0.5)

            decoded = [0] * len(encoded) * 3
            line = int(round(pixelline / self.height_ratio)) % 2

            if PASSFLOAT:
                padded = [0] * self.uvfir.Order + encoded + [0] * self.uvfir.Order
            else:
                padded = [x/255.0 for x in [0] * self.uvfir.Order + encoded + [0] * self.uvfir.Order]
            if MODE == MODE_FIR:
                decoded = self.DecodeFIR(padded, self.uvfir.Order, self.uvfir.Order + len(encoded), line)
            else:
                for i in xrange(self.uvfir.Order, self.uvfir.Order + len(encoded)):
                    wt = t * 2 * math.pi / self.width_ratio
                    sinwt = math.sin(wt)
                    coswt = [+1,-1][line] * math.cos(wt)
                    r, g, b = self.Decode(padded, i, sinwt, coswt)

                    decoded[t*3:t*3+3] = clamp_scale3([r,g,b])
                    t = t + 1
            #print "Hard working decoder puts line %d in outputQueue" % pixelline
            self.outputQueue.put((pixelline, decoded))
        #if self.inputQueue.empty():
        self.inputQueue.put((-1, None))
        self.outputQueue.put((-1, self.decoderId))

def EncoderRunner(arg):
    id, pixelQueue, workQueue, encoderResultQueue, hratio, wratio = arg
    encoder = Encoder(id, pixelQueue, workQueue, encoderResultQueue, hratio, wratio)
    encoder.run()

def DecoderRunner(arg):
    decoderId, workQueue, decoderQueue, hratio, wratio = arg
    decoder = Decoder(decoderId, workQueue, decoderQueue, hratio, wratio)
    decoder.run()

def Unwrapper(pixels):
    y = 0
    for line in pixels: 
        linepixels=[0] * width * 3
        x = 0
        for p in line:
            linepixels[x] = p
            x = x + 1
        yield (y,linepixels)
        y = y + 1

if __name__ == '__main__':

    inputfile = 'riverraid.png'

    outputfile_coded = (lambda x: x[0] + '-encoded.' + x[1])(inputfile.split('.', 1))
    outputfile_decoded = (lambda x: x[0] + '-decoded.' + x[1])(inputfile.split('.', 1))

    width, height, pixels, meta = Reader(inputfile).asRGB8()

    coded = open(outputfile_coded, 'wb')
    decodedf = open(outputfile_decoded, 'wb')
    coded_writer = Writer(width, height, greyscale=True)
    decoded_writer = Writer(width, height)

    # how many counts of Fsc
    width_ratio = width / (Fsc / Fline) # ~ 2.69
    # we only get 312 lines
    height_ratio = height / 312.0

    print 'Files:\n  input picture: %s (%dx%d)\n  encoded picture: %s\n  decoded picture: %s' %\
       (inputfile, width, height, outputfile_coded, outputfile_decoded)
    print 'Modem parameters:\n  Fsc=%10.4fHz\n  Line frequency=%5fHz\n  Width to Fsc ratio=%3.3f' % (Fsc, Fline, width_ratio)

    pixelQueue = Queue(height)
    encoderResultQueue = Queue(max(10, NDECODERS * 2))
    workQueue = Queue(max(10, NDECODERS * 2))    
    decoderQueue = Queue(max(10, NDECODERS * 2))

    decoderResult = [None] * height
    encoderResult = [None] * height

    #encoderProcess = Process(target = EncoderRunner, args=((pixelQueue, workQueue, encoderResultQueue, width_ratio, height_ratio),))
    encoders = []
    for i in xrange(NENCODERS):
        encoders.append( Process(target = EncoderRunner, args=((i, pixelQueue, workQueue, encoderResultQueue, width_ratio, height_ratio),)) )    
    decoders = []
    for i in xrange(NDECODERS):
        decoders.append( Process(target = DecoderRunner, args=((i, workQueue, decoderQueue, width_ratio, height_ratio),)) )

    print 'Decoding using %d encoders and %d decoders' % (len(encoders), len(decoders))

    for encoder in encoders:
        encoder.start()
    for decoder in decoders:
        decoder.start()

    unwrapper = Unwrapper(pixels)
    unwrapping, encoding = True, True
    activeDecoders = len(decoders)
    activeEncoders = len(encoders)
    
    while (activeEncoders > 0) or (activeDecoders > 0):
        #if pixelQueue.full() or workQueue.full() or decoderQueue.full():
        #    print 'Queue overflow', pixelQueue.full(), workQueue.full(), decoderQueue.full()
        if unwrapping:
            try: 
               pixelQueue.put(unwrapper.next())
            except:
               print 'Unwrapped everything'
               for i in xrange(activeEncoders):
                   pixelQueue.put((-1, None))
               pixelQueue.close()
               unwrapping = False
          
        try:
            decodedLine, bytes = decoderQueue.get(not unwrapping)
            if decodedLine == -1:
                decoders[bytes].join()
                activeDecoders = activeDecoders - 1
            else:
                decoderResult[decodedLine] = bytes
        except Empty:
            pass

        if activeEncoders > 0:
            try:
                encodedLine, bytes = encoderResultQueue.get(not unwrapping)
                if encodedLine != -1:
                    encoderResult[encodedLine] = bytes
                else:
                    encoders[bytes].join()
                    activeEncoders = activeEncoders - 1
                    #print 'Encoder %d joined, rest %d' % (bytes, activeEncoders)
            except Empty:
                pass

    print 'All done, writing result'
    coded_writer.write(coded, encoderResult)
    for x in xrange(len(decoderResult)):
        if decoderResult[x] == None:
            print 'Erreur', x
    decoded_writer.write(decodedf, decoderResult)
      
