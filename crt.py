#!/usr/bin/env python
from png import Reader, Writer
from random import random
import itertools
import math

# subcarrier frequency
Fsc=4433618.75

# line frequency
Fline=15625

# phase noise (2.5 for crappy cable)
PHASE_NOISE = 0

# use biquads to filter components, otherwise moving average
MOVING_AVERAGE = False

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

# colour encoder
def Encode(rgb, sinwt, coswt):
    y,u,v = RGBtoYUV(rgb)
    return clamp(y + u * sinwt + v * coswt)

# colour decoder
def Decode(pal, sinwt, coswt):
    if MOVING_AVERAGE:
        yavg = (yavg + pal) / 2.0
        y_ = yavg
        u_ = (pal - y_) * 2 * sinwt
        v_ = (pal - y_) * 2 * coswt
        uavg = (uavg + u_) / 2
        vavg = (vavg + v_) / 2
        u_ = uavg
        v_ = vavg 
    else:
        color = fitler.filter(pal)
        y_ = notch.filter(pal) # - color
        u_ = color * 2 * sinwt
        v_ = color * 2 * coswt
        u_ = fitlerU.filter(u_)
        v_ = fitlerV.filter(v_)
    
    return YUVtoRGB(y_, u_, v_)

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

inputfile = 'testcard.png'

outputfile_coded = (lambda x: x[0] + '-encoded.' + x[1])(inputfile.split('.', 1))
outputfile_decoded = (lambda x: x[0] + '-decoded.' + x[1])(inputfile.split('.', 1))

width, height, pixels, meta = Reader(inputfile).asRGB8()

coded = open(outputfile_coded, 'wb')
decodedf = open(outputfile_decoded, 'wb')
coded_writer = Writer(width, height, greyscale=True)
decoded_writer = Writer(width, height)

# subcarrier counts per scan line = Fsc/Fline = 283.7516

# how many counts of Fsc
width_ratio = width / (Fsc / Fline) # ~ 2.69
delta_wt = math.pi / width_ratio

# we only get 312 lines
height_ratio = height / 312.0

print 'Files:\n  input picture: %s (%dx%d)\n  encoded picture: %s\n  decoded picture: %s' %\
   (inputfile, width, height, outputfile_coded, outputfile_decoded)
print 'Modem parameters:\n  Fsc=%10.4fHz\n  Line frequency=%5fHz\n  Width to Fsc ratio=%3.3f' % (Fsc, Fline, width_ratio)

# chroma filter
fitler = Biquad().bandpass(Fsc * width_ratio, Fsc, 0.7) # 1.7 looks kinda cool in a wrong way
# luma filter
notch = Biquad().notch(Fsc * width_ratio, Fsc, 0.7)

# chroma output smoothing filter
fitlerU = Biquad().lowpass(Fsc * width_ratio, Fsc*0.2, 0.7)
fitlerV = Biquad().lowpass(Fsc * width_ratio, Fsc*0.2, 0.7)


result=[]
result_decoded=[]
pixelline=0
halfpi = math.pi / 2

for linepixels in pixels:
    line = int(round(pixelline / height_ratio)) % 2
    wt = (180.0 + [+90,-90][line]) / 180.0 * math.pi
    yavg, uavg, vavg = 0, 0, 0
    t = 0
    encoded = [0] * width
    decoded = [0] * width * 3
    for inputrgb in nslice(linepixels, 3):
        wt = t * 2 * math.pi / width_ratio + [ +halfpi, -halfpi][line]
        sinwt = math.sin(wt)
        coswt = math.cos(wt) # * [+1,-1][line]

        pal = Encode(inputrgb, sinwt, coswt)
        encoded[t] = int(pal * 255)

        # embrouiller les choses
        if PHASE_NOISE != 0:
          wt = wt + PHASE_NOISE * (random() - 0.5)
          sinwt = math.sin(wt)
          coswt = math.cos(wt) # * [+1,-1][line]

        r, g, b = Decode(pal, sinwt, coswt)
        decoded[t*3:t*3+3] = clamp_scale3([r,g,b])

        t = t + 1

    result.append(encoded)
    result_decoded.append(decoded)
    pixelline = pixelline + 1

coded_writer.write(coded, result)
decoded_writer.write(decodedf, result_decoded)
  
