#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy
import png

class imagesink:
    """
    save float32 (r,g,b) vectors as png
    """
    def __init__(self, filename, width, height, recombine=True):
        self.filename = filename
        self.width = width
        self.height = height
        #self.frame = numpy.zeros((height,width,3))
        self.pixels = []
        self.recombine = recombine

    def work(self, in0):
        #print("in0=", in0, " shaep=", in0.shape)
        self.pixels = self.pixels + in0.flatten().tolist()
        fullframe = int(self.width * 3 * self.height)
        #print("fullframe=", fullframe, " have ", len(self.pixels))
        if len(self.pixels) >= fullframe:
            frame = self.pixels[:fullframe]
            self.pixels = self.pixels[fullframe:]
            self.savePng(frame)
        
        return len(in0)

    def recombine_fields(self, floats):
        gloats = numpy.zeros(floats.shape)
        gloats[1::2] = floats[:floats.shape[0]//2]
        gloats[::2] =  floats[floats.shape[0]//2:]
        return gloats

    def savePng(self, pixels):
        writer = png.Writer(width=self.width, height=self.height, greyscale=False)
        f = open(self.filename, 'wb')
        floats = numpy.array(pixels).reshape(self.height, self.width * 3)
        if self.recombine:
            floats = self.recombine_fields(floats)

        floats = numpy.clip(floats, 0, 1)

        floats = floats * 255
        floats = numpy.ndarray.astype(floats, int)
        rows = floats.tolist()
        writer.write(f, rows)
        f.close()
