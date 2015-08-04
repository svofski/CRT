# Software composite video modulation/demodulation experiments

The idea is to reproduce in GLSL shaders realistic composite-like artifacting by applying PAL modulation
and demodulation. Digital texture, passed through the model of an analog channel, should suffer same effects
as its analog counterpart and exhibit properties, such as dot crawl and colour bleeding, that may be desirable for faithful reproduction of look and feel of old computer games.

![](https://github.com/svofski/CRT/blob/master/crt-screenshot.jpg)

The project contains 2 main parts: purely software simulation, and GLSL shader implementation. The GLSL 
part consists of a Python host which can be used to experiment with fragment shaders in general, and the shaders themselves.

## Shaders
Currently there are 3 different implementations of composite shader that aim to reproduce the same model.
### mpass
3-stage processing:
 1. modulate source RGB signal to B&W image
 2. demodulate U and V, pass (Modulated, U, V) in (R,G,B) channels
 3. lowpass filter UV at baseband, remodulate again and subtract from Modulated to recover Luma. Convert back to RGB
 
### oversampling
SDLMESS uses very small textures for multipass shading, which makes them 
not very practical for purposes of storing intermediate values. This method is an attempt to pack 2x more
intermediate values in unused texture channels. It differs from mpass in that it passes U,V,U,V in (RGBA), thus
packing 2x more bandwidth in same amount of pixels. 

### singlepass
I was afraid that this method would be very slow because a lot of things are calculated over and over again
for the purpose of filtering. But it seems to be doing fine even on slower GPUs. This is the best method. Because 
it has no intermediate passes, it takes colour signal samples at 4x colour subcarrier frequency regardless 
of source texture resolution.

## Requirements:

 * Software-only model: Python 2.7, PyPNG
 * GLSL model: Python 2.7, PyGame, PyOpenGL

## SDLMESS/SDLMAME compatibility
This toy is designed with SDLMESS compatibility in mind, so shaders designed with it can be used with 
SDLMESS almost without modifications. 

## Acknowledgements
 * I cannibalized Ian Mallett's GLSL Game of Life code as initial PyGame/PyOpenGL boilerplate code.
His work can be found here: http://www.geometrian.com/programming/projects/index.php?project=Game%20of%20Life
 * The Engineer’s Guide to Decoding & Encoding http://www.snellgroup.com/documents/engineering-guides/edecod.pdf


