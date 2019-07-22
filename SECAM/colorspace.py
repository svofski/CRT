#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy

class rgb2ydbdr:
    """
    docstring for block rgb2secam
    """
    def __init__(self):
        #gr.basic_block.__init__(self,
        #    name="rgb2secam",
        #    in_sig=[(numpy.float32,3)],
        #    out_sig=[numpy.float32,numpy.float32,numpy.float32])
        pass

    def forecast(self, noutput_items, ninput_items_required):
        #setup size of input_items[i] for work call
        #print("FORECAST: ", ninput_items_required, noutput_items)
        for i in range(len(ninput_items_required)):
            #print("forecast: noutput_items=", noutput_items)
            ninput_items_required[i] = noutput_items

    # in_rgb = (n,3)
    # output_items = (3,...)
    def general_work(self, in_rgb, out_y, out_db, out_dr):
        output_capacity = len(out_y)
        #print('Can output at most ', output_capacity)

        rgb = numpy.array(in_rgb[:output_capacity]).transpose()
        #print('ia.shape=', rgb.shape)
        secam = self.ydbdr(rgb)
        #print('secam=', secam)
        y,db,dr = secam[0],secam[1],secam[2]
        #print('y=', y, 'db=', db, 'dr=', dr)
        out_y[:] = y.clip(0,1)
        out_db[:] = db.clip(-1,1)
        out_dr[:] = dr.clip(-1,1)

        return len(out_y)

    def ydbdr(self, rgb):
        M = numpy.array([[.299,.587,.114],[-.450,-.883,1.333],[-1.333,1.116,.217]])
        return numpy.around(M.dot(rgb),6)


class ydbdr2rgb:
    """
    Y,Dr,Db -> RGB
    """
    def __init__(self):
        pass

    def forecast(self, noutput_items, ninput_items_required):
        #setup size of input_items[i] for work call
        for i in range(len(ninput_items_required)):
            ninput_items_required[i] = noutput_items

    def general_work(self, in_y, in_db, in_dr, out_rgb):
        output_capacity = len(out_rgb)

        ydbdr = numpy.array([in_y[:output_capacity],
            in_db[:output_capacity],
            in_dr[:output_capacity]])

        secam = numpy.array(ydbdr).swapaxes(0,1)[:output_capacity].transpose()

        rgb = self.torgb(secam)

        out_rgb[:] = rgb.transpose()
        #self.consume_each(output_capacity)
        return len(out_rgb)

    def torgb(self, ydbdr):
        M = numpy.array([[1,0.000092303716148,-0.525912630661865],
            [1,-0.129132898890509,0.267899328207599],
            [1,0.664679059978955,-0.000079202543533]])
        return numpy.around(M.dot(ydbdr),6) 

