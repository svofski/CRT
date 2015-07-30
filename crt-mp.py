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

# phase noise (2.5 for crappy cable)
PHASE_NOISE = 0

# use biquads to filter components, otherwise moving average
MOVING_AVERAGE = False

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
    x_2, x_3 = 0, 0
    def delay(self, x):
        result = self.x_3
        self.x_3 = self.x_2
        self.x_2 = x
        return result

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

    def Encode(self, rgb, sinwt, coswt):
        y,u,v = RGBtoYUV(rgb)
        y = self.notch.filter(y)
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
            t = 0
            #encoded = [0] * width
            encoded = []
            for inputrgb in nslice(linepixels, 3):
                wt = t * 2 * math.pi / self.width_ratio + [ +halfpi, -halfpi][line]
                sinwt = math.sin(wt)
                coswt = math.cos(wt) # * [+1,-1][line]

                pal = self.Encode(inputrgb, sinwt, coswt)
                #encoded[t] = int(pal * 255)
                encoded.append(int(pal*255))

                t = t + 1

            self.result.append(encoded)
            #print 'Encoder puts line %d' % pixelline
            self.queue.put((pixelline, encoded))
            self.queue2.put((pixelline, encoded))
        # ensure that all consumers get their termination flags
        #print 'Encoder is terminating'
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

        # chroma filter
        self.fitler = Biquad().bandpass(Fsc * width_ratio, Fsc, 0.7) # 1.7 looks kinda cool in a wrong way
        # luma filter
        self.notch = Biquad().notch(Fsc * width_ratio, Fsc, 0.7)

        # fir chroma
        self.firchroma = Fir()

        # chroma output smoothing filter
        self.fitlerU = Biquad().lowpass(Fsc * width_ratio, Fsc*0.2, 0.7)
        self.fitlerV = Biquad().lowpass(Fsc * width_ratio, Fsc*0.2, 0.7)
        self.yavg, self.uavg, self.uavg = 0, 0, 0

    def Decode(self, pal, sinwt, coswt):
        if MOVING_AVERAGE:
            self.yavg = (yavg + pal) / 2.0
            y_ = yavg
            u_ = (pal - y_) * 2 * sinwt
            v_ = (pal - y_) * 2 * coswt
            self.uavg = (uavg + u_) / 2
            self.vavg = (vavg + v_) / 2
            u_ = uavg
            v_ = vavg 
        else:
            color = self.fitler.filter(pal)
            y_ = self.notch.filter(pal) # - color
            u_ = color * 2 * sinwt
            v_ = color * 2 * coswt
            u_ = self.fitlerU.filter(u_)
            v_ = self.fitlerV.filter(v_)
        
        return YUVtoRGB(y_, u_, v_)

    def run(self):
        while True:        
            pixelline, encoded = self.inputQueue.get(True)
            #print 'Decoder %d picked line %d, qsize=%d' % (self.id, pixelline, self.queue.qsize())
            if pixelline == -1:
                break
            t = 0
            decoded = [] # [0] * width * 3
            line = int(round(pixelline / self.height_ratio)) % 2

            for pal in encoded:
                wt = t * 2 * math.pi / self.width_ratio + [ +halfpi, -halfpi][line]
                sinwt = math.sin(wt)
                coswt = math.cos(wt) # * [+1,-1][line]

                r, g, b = self.Decode(pal/255.0, sinwt, coswt)
                # decoded[t*3:t*3+3] = clamp_scale3([r,g,b])
                decoded = decoded + clamp_scale3([r,g,b])
                t = t + 1
            #self.result[pixelline] = decoded
            #print "Hard working decoder puts line %d in outputQueue" % pixelline
            self.outputQueue.put((pixelline, decoded))
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

    inputfile = 'testcard.png'

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
        if pixelQueue.full() or workQueue.full() or decoderQueue.full():
            print 'Queue overflow'
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
    decoded_writer.write(decodedf, decoderResult)
      
