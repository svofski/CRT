
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

# adjustable shader parameters for fine tuning
class ShaderParams(object):
    """docstring for ShaderParams"""

    def __init__(self):
        super(ShaderParams, self).__init__()
        self.filter_gain = 1
        self.filter_invgain = 1.6


class ShaderManager(object):
    """docstring for ShaderManager"""
    def __init__(self):
        super(ShaderManager, self).__init__()
        self.params = ShaderParams()
        self.sources = []
        self.sets = ["mpass", "oversampling", "singlepass"]
        self.current = -1
        
    def load(self):
        self.sources = []

        for i in xrange(1,10):
            try:
                text = open('shaders/%s/pass%d.fsh' % (self.sets[self.current], i), 'r').read()
                self.sources.append(text)
            except:
                break

            self.params = ShaderParams()
            defaults_file = 'shaders/%s/defaults' % (self.sets[self.current])
            try:
                for defulat in open(defaults_file, 'r').readlines():
                    try:
                        var, val = defulat.strip().split('=')
                        self.params.__dict__[var] = float(val)
                    except:
                        print 'Warning: could not evaulate default setting ''%s'' in %s' % (defulat, defaults_file)
            except:
                print 'Warning: could not eval default settings %s' % defaults_file

        print 'Found %d shaders' % len(self.sources)

    def LoadNext(self):
        self.current = (self.current + 1) % len(self.sets)
        print 'ShaderManager: current shader set to: %s' % self.sets[self.current]
        self.load()

    def CurrentName(self):
        return self.sets[self.current]


class Context(object):
    """docstring for Context"""
    def __init__(self, surface, shader_manager):
        super(Context, self).__init__()
        self.sourceSurface = surface
        self.screen_size = surface.get_size()
        self.shaders = []
        self.fbos = []
        self.color_texture = None
        self.mpass_texture1 = None
        self.mpass_texture2 = None
        self.shader_manager = shader_manager
        self.setup()

    def __del__(self):
        self.deinit()

    def setup(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE)
        glTexEnvi(GL_POINT_SPRITE,GL_COORD_REPLACE,GL_TRUE)

    def ScreenSizeChanged(self, new_size):
        self.screen_size = new_size
        self.deinit()
        self.init()

    def Reinit(self, new_size = None):
        if new_size != None:
            self.screen_size = new_size
        self.deinit()
        self.init()

    def ReloadShaders(self):
        self.shaders = [shader.Shader([shader.ProgramShaderFragment(source)]) for source in self.shader_manager.sources]

    def init(self):
        print 'Context.init(): Screen size=', repr(self.screen_size)
        pygame.display.set_mode(self.screen_size, OPENGL | DOUBLEBUF | RESIZABLE)

        self.color_texture = texture.Texture2D.from_surf(self.sourceSurface)
        source_size = self.sourceSurface.get_size()
        self.mpass_texture1 = texture.Texture2D.from_empty(source_size)
        self.mpass_texture2 = texture.Texture2D.from_empty(source_size)

        self.fbos = [fbo.FBO2D(source_size), fbo.FBO2D(source_size)]
        self.fbos[0].attach_color_texture(self.mpass_texture1, 1)
        self.fbos[0].set_read(self.fbos[1], None)
        self.fbos[1].attach_color_texture(self.mpass_texture2, 1)
        self.fbos[1].set_read(self.fbos[0], None)

        self.ReloadShaders()
        

    def deinit(self):
        del self.color_texture
        del self.mpass_texture1
        del self.mpass_texture2

        for i in xrange(len(self.fbos)):
            del self.fbos[0]

        for i in xrange(len(self.shaders)):
            del self.shaders[0]
    
    def draw_screen_quad(self):
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(                  0,                   0)
        glTexCoord2f(1, 0); glVertex2f(self.screen_size[0],                   0)
        glTexCoord2f(1, 1); glVertex2f(self.screen_size[0], self.screen_size[1])
        glTexCoord2f(0, 1); glVertex2f(                  0, self.screen_size[1])
        glEnd()

    def clear(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def Draw(self):
        gl_util.set_view_2D(self.screen_size)
        self.clear()
        for i in xrange(len(self.shaders) - 1):
            pingpong = i % 2

            fbo.FBO2D.set_write(self.fbos[pingpong])

            shader.Shader.use(self.shaders[i])
            self.shaders[i].pass_vec2("color_texture_sz", self.sourceSurface.get_size())
            self.shaders[i].pass_texture_name(self.color_texture, self.color_texture.texture_id, "color_texture")
            if pingpong == 1:
                self.shaders[i].pass_texture_name(self.mpass_texture1, self.mpass_texture1.texture_id, "mpass_texture")
            else:
                self.shaders[i].pass_texture_name(self.mpass_texture2, self.mpass_texture2.texture_id, "mpass_texture")

            self.draw_screen_quad()

        pingpong = (len(self.shaders) - 1) % 2
        fbo.FBO2D.set_write(None)

        shader.Shader.use(self.shaders[-1])
        self.shaders[-1].pass_vec2("color_texture_sz", self.sourceSurface.get_size())
        self.shaders[-1].pass_texture_name(self.color_texture, self.color_texture.texture_id, "color_texture")

        # set additional uniforms from defaults
        for uniform, value in self.shader_manager.params.__dict__.iteritems():
            self.shaders[-1].pass_float(uniform, value)

        if pingpong == 1:
            self.shaders[-1].pass_texture_name(self.mpass_texture1, self.mpass_texture1.texture_id, "mpass_texture")
        else:
            self.shaders[-1].pass_texture_name(self.mpass_texture2, self.mpass_texture2.texture_id, "mpass_texture")

        self.draw_screen_quad()
