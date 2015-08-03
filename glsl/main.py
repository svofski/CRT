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

screen_size = [800,600]
shaderSources = []
shaders = []
fbos = []
color_texture = None
mpass_texture1 = None
mpass_texture2 = None

# adjustable shader parameters for fine tuning
filter_gain = 1
filter_invgain = 1.6

def loadShaders():
    global shaderSources
    shaderSources = []

    for i in xrange(1,10):
        try:
            text = open('shaders/pass%d.fsh' % i, 'r').read()
            shaderSources.append(text)
        except:
            break

    print 'Found %d shaders' % len(shaderSources)

loadShaders()            

def loadSourceAsSurface():
    print len(sys.argv), int(len(sys.argv) == 1)
    return pygame.image.load('testcard.png' if len(sys.argv) == 1 else sys.argv[1])

sourceSurface = loadSourceAsSurface()
screen_size = sourceSurface.get_size()    


icon = pygame.Surface((1,1)); icon.set_alpha(0); pygame.display.set_icon(icon)
pygame.display.set_caption("Composite video simulation")
flags = OPENGL|DOUBLEBUF|RESIZABLE
pygame.display.set_mode(screen_size,flags)

glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

glEnable(GL_TEXTURE_2D)
glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE)
glTexEnvi(GL_POINT_SPRITE,GL_COORD_REPLACE,GL_TRUE)


def init():
    global color_texture, mpass_texture1, mpass_texture2
    global fbos
    global shaders, shaderSources

    shaders = []

    color_texture = texture.Texture2D.from_surf(sourceSurface)
    mpass_texture1 = texture.Texture2D.from_empty(screen_size)
    mpass_texture2 = texture.Texture2D.from_empty(screen_size)

    fbos = [fbo.FBO2D(screen_size), fbo.FBO2D(screen_size)]
    fbos[0].attach_color_texture(mpass_texture1, 1)
    fbos[1].attach_color_texture(mpass_texture2, 1)

    shaders = [shader.Shader([shader.ProgramShaderFragment(source)]) for source in shaderSources]

def deinit():
    global color_texture, mpass_texture1, mpass_texture2
    global fbos
    global shaders

    del color_texture
    del mpass_texture1
    del mpass_texture2

    del fbos[0]
    del fbos[0]

    for i in xrange(len(shaders)):
        del shaders[0]
    #del shaders[0]

to_add = []
iterations = -1
def get_input():
    global iterations, screen_size
    global filter_gain, filter_invgain
    
    keys_pressed = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    mouse_position = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == QUIT: return False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE: 
                return False
            elif event.key == K_q:
                filter_gain = filter_gain - 0.01
            elif event.key == K_w:
                filter_gain = filter_gain + 0.01
            elif event.key == K_a:
                filter_invgain = filter_invgain - 0.01
            elif event.key == K_s:
                filter_invgain = filter_invgain + 0.01
            elif event.key == K_z:
                filter_invgain = filter_invgain - 0.1
            elif event.key == K_x:
                filter_invgain = filter_invgain + 0.1
            print 'Filter gain = %1.3f invgain = %1.3f' % (filter_gain, filter_invgain)
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

    shaders[-1].pass_float("filter_gain", filter_gain)
    shaders[-1].pass_float("filter_invgain", filter_invgain)
    shaders[-1].pass_texture_name(texture, texture.texture_id, "color_texture")

    if pingpong == 1:
        shaders[-1].pass_texture_name(mpass_texture1, mpass_texture1.texture_id, "mpass_texture")
    else:
        shaders[-1].pass_texture_name(mpass_texture2, mpass_texture2.texture_id, "mpass_texture")

    draw_screen_quad()

def draw():
    global iterations

    gl_util.set_view_2D(screen_size)

    draw_update(color_texture)
    
    pygame.display.flip()

def main():
    init()
    
    clock = pygame.time.Clock()
    while True:
        if not get_input(): break
        draw()
        clock.tick(10)
        #print clock.get_fps()

    deinit()
    
    pygame.quit()

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
        pygame.quit()
        input()
