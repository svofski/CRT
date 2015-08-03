from OpenGL.GL import *
from OpenGL.GLU import *
import pygame
from pygame.locals import *
import traceback
import random
import pygame.image
import gl_util, fbo, shader, texture
import sys
import time

pygame.display.init()
pygame.font.init()

shader_sets = ["mpass", "oversampling", "singlepass"]
shader_set = -1

screen_size = [800,600]
shaderSources = []
shaders = []
fbos = []
color_texture = None
mpass_texture1 = None
mpass_texture2 = None
fps_count = 0

# adjustable shader parameters for fine tuning
class ShaderParams(object):
    """docstring for ShaderParams"""

    def __init__(self):
        super(ShaderParams, self).__init__()
        self.filter_gain = 1
        self.filter_invgain = 1.6

shader_params = ShaderParams()

def loadShaderSources():
    global shaderSources
    shaderSources = []

    global shader_params

    for i in xrange(1,10):
        try:
            text = open('shaders/%s/pass%d.fsh' % (shader_sets[shader_set], i), 'r').read()
            shaderSources.append(text)
        except:
            break

        defaults_file = 'shaders/%s/defaults' % (shader_sets[shader_set])
        try:
            for defulat in open(defaults_file, 'r').readlines():
                try:
                    var, val = defulat.strip().split('=')
                    shader_params.__dict__[var] = float(val)
                except:
                    print 'Warning: could not evaulate default setting ''%s'' in %s' % (defulat, defaults_file)
            #eval(defaults)
            print shader_params.__dict__
        except:
            print 'Warning: could not eval default settings %s' % defaults_file

    print 'Found %d shaders' % len(shaderSources)

def nextShaderMode():
    global shader_sets, shader_set, shaders
    shader_set = (shader_set + 1) % len(shader_sets)
    print 'Current shader set: %s' % shader_sets[shader_set]
    loadShaderSources()
    shaders = [shader.Shader([shader.ProgramShaderFragment(source)]) for source in shaderSources]

def loadSourceAsSurface():
    return pygame.image.load('testcard.png' if len(sys.argv) == 1 else sys.argv[1])

def updateCaption(fps):
    pygame.display.set_caption("Composite video simulation %dx%d [%s: gain=%2.2f invgain=%2.2f] %3.1ffps" % \
        tuple(list(screen_size) + [shader_sets[shader_set], shader_params.filter_gain, shader_params.filter_invgain, fps]))

def setupOpenGL():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
    #glBlendFunc(GL_ONE, GL_ZERO)

    glEnable(GL_TEXTURE_2D)
    glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE)
    glTexEnvi(GL_POINT_SPRITE,GL_COORD_REPLACE,GL_TRUE)

def init():
    global color_texture, mpass_texture1, mpass_texture2
    global fbos
    global shaders, shaderSources

    print 'init(): Screen size=', repr(screen_size)
    shaders = []

    pygame.display.set_mode(screen_size, OPENGL | DOUBLEBUF | RESIZABLE)

    color_texture = texture.Texture2D.from_surf(sourceSurface)
    mpass_texture1 = texture.Texture2D.from_empty(sourceSurface.get_size())
    mpass_texture2 = texture.Texture2D.from_empty(sourceSurface.get_size())

    fbos = [fbo.FBO2D(sourceSurface.get_size()), fbo.FBO2D(sourceSurface.get_size())]
    fbos[0].attach_color_texture(mpass_texture1, 1)
    fbos[0].set_read(fbos[1], None)
    fbos[1].attach_color_texture(mpass_texture2, 1)
    fbos[1].set_read(fbos[0], None)

    nextShaderMode()

def deinit():
    global color_texture, mpass_texture1, mpass_texture2
    global fbos
    global shaders

    del color_texture
    del mpass_texture1
    del mpass_texture2

    for i in xrange(len(fbos)):
        del fbos[0]

    for i in xrange(len(shaders)):
        del shaders[0]

def get_input():
    global screen_size
    global shader_params
    
    keys_pressed = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    mouse_position = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == QUIT: return False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE: 
                return False
            elif event.key == K_q:
                shader_params.filter_gain -= 0.1
            elif event.key == K_w:
                shader_params.filter_gain += 0.1
            elif event.key == K_a:
                shader_params.filter_invgain -= 0.01
            elif event.key == K_s:
                shader_params.filter_invgain += 0.01
            elif event.key == K_z:
                shader_params.filter_invgain -= 0.1
            elif event.key == K_x:
                shader_params.filter_invgain += 0.1
            elif event.key == K_m:
                nextShaderMode()
            updateCaption(fps_count)    
            print 'Filter gain = %1.3f invgain = %1.3f' % (shader_params.filter_gain, shader_params.filter_invgain)
        elif event.type == VIDEORESIZE:
            screen_size = list(event.size)
            #Resizing messes up the OpenGL context.  Make all our objects again.
            deinit()
            init()
    return True

def draw_screen_quad():
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(             0,             0)
    glTexCoord2f(1, 0); glVertex2f(screen_size[0],             0)
    glTexCoord2f(1, 1); glVertex2f(screen_size[0], screen_size[1])
    glTexCoord2f(0, 1); glVertex2f(             0, screen_size[1])
    glEnd()

def clear():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

def draw_update(texture):
    clear()
    for i in xrange(len(shaders) - 1):
        pingpong = i % 2

        fbo.FBO2D.set_write(fbos[pingpong])

        shader.Shader.use(shaders[i])
        shaders[i].pass_vec2("color_texture_sz", screen_size)
        shaders[i].pass_texture_name(texture, texture.texture_id, "color_texture")
        if pingpong == 1:
            shaders[i].pass_texture_name(mpass_texture1, mpass_texture1.texture_id, "mpass_texture")
        else:
            shaders[i].pass_texture_name(mpass_texture2, mpass_texture2.texture_id, "mpass_texture")

        draw_screen_quad()

    pingpong = (len(shaders) - 1) % 2
    fbo.FBO2D.set_write(None)

    shader.Shader.use(shaders[-1])
    shaders[-1].pass_vec2("color_texture_sz", screen_size)
    shaders[-1].pass_texture_name(texture, texture.texture_id, "color_texture")

    # set additional uniforms from defaults
    for uniform, value in shader_params.__dict__.iteritems():
        shaders[-1].pass_float(uniform, value)

    if pingpong == 1:
        shaders[-1].pass_texture_name(mpass_texture1, mpass_texture1.texture_id, "mpass_texture")
    else:
        shaders[-1].pass_texture_name(mpass_texture2, mpass_texture2.texture_id, "mpass_texture")

    draw_screen_quad()

def draw():
    gl_util.set_view_2D(screen_size)
    draw_update(color_texture)    
    pygame.display.flip()

def main():
    global fps_count, sourceSurface, screen_size

    sourceSurface = loadSourceAsSurface()
    screen_size = sourceSurface.get_size()    

    pygame.display.set_icon(sourceSurface)
    pygame.display.set_mode(screen_size, OPENGL | DOUBLEBUF | RESIZABLE)

    setupOpenGL()

    init()
    
    updateCaption(0)

    iter = 0
    clock = pygame.time.Clock()
    while True:
        if not get_input(): break
        draw()
        clock.tick(60)        
        fps_count = clock.get_fps()
        iter += 1
        if iter > 60:
            iter -= 60
            updateCaption(fps_count)

    deinit()
    
    pygame.quit()

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
        pygame.quit()
        input()
