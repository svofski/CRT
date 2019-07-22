#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
import png
import numpy
import scipy.ndimage

class imagesource:
    def __init__(self, filename, samp_rate, 
        line_freq_hz=15625, 
        total_lines=625,    # 625 horizontal lines
        visible_lines=576,  # of which 288+288 are visible
        line_sync_s=4e-6, 
        back_porch_s=6e-6, 
        front_porch_s=2e-6):

        w,h,pix = self.readPNG(filename) 

        self.total_lines = total_lines
        self.visible_lines = visible_lines
        self.samples_per_line = int(round(samp_rate/line_freq_hz))

        line_us = 1e6/15625 # 64
        blanking_us = (line_sync_s + back_porch_s + front_porch_s)*1e6; # 12
        self.visible_samples = int(round(self.samples_per_line * 
            (1-blanking_us/line_us)))

        #print("%s %dx%d scaled -> %d samples per line, %d visible" %
        #        (filename, w,h, self.samples_per_line, self.visible_samples))
    
        pix = numpy.array(pix).reshape((h,w,3))

        visible = scipy.ndimage.zoom(pix, (1.0*self.visible_lines/h, 
            1.0*self.visible_samples/w, 1))

        complete = numpy.zeros((self.total_lines,self.samples_per_line,3), 
            numpy.float32)

        xoffset = int(round((line_sync_s+back_porch_s) * samp_rate))

        #field_offset = self.visible_lines//2 + 1
        field_offset = self.visible_lines//2 + 1# 312+1
        x1,x2 = xoffset, xoffset + self.visible_samples

        for i in range(self.visible_lines//2):
            complete[24 + i][x1:x2] = visible[i*2]
            complete[2*24 + i + field_offset][x1:x2] = visible[i*2]

        self.pix = complete * 1.0/255.0 # scale it to [0,1]
    
        self.y = 0
        self.x = 0
        self.done = False

    def readPNG(self, filename):
        pix = None
        reader = png.Reader(filename)
        #img = reader.asFloat() <-- this produces crap
        img = reader.asRGB8()   # <-- so does this if there's alpha channel
        pix = list(img[2])
        w, h = len(pix[0]), len(pix)
        return w//3,h,pix

    # out is an array(3,n) of float rgb values in ramge (0..1)
    def work(self, out, line):
        #print("out.shape=", out.shape)
        #print("out[0].shape=", out[0].shape)
        if self.done:
            return -1 # WORK_DONE

        for i in range(len(out)):
            self.x = self.x + 1
            if self.x == int(self.samples_per_line):
                self.x = 0
                self.y = self.y + 1
                if self.y == int(self.total_lines):
                    self.y = 0
                    self.done = True
                    
            out[i] = self.pix[self.y,self.x]            
            line[i] = self.y + 1  # secam line numbering is 1-based

        return i+1

