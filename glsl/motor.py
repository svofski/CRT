
from OpenGL.GL import *
from OpenGL.GLU import *
import traceback
import gl_util, fbo, shader, texture

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
        self.sets = ["singlepass", "oversampling", "mpass"]
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
    def __init__(self, surface, shader_manager, setmode):
        super(Context, self).__init__()
        self.sourceSurface = surface
        self.screen_size = surface.get_size()
        self.shaders = []
        self.fbos = []
        self.color_texture = None
        self.mpass_texture1 = None
        self.mpass_texture2 = None
        self.shader_manager = shader_manager
        self.setmodeCallback = setmode
        self.passes = []
        self.sprite = None
        self.setup()

    def __del__(self):
        self.deinit()

    def setup(self):
        glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glBlendFunc(GL_ONE, GL_ZERO)
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
        self.passes = [True] * len(self.shaders)

    def TogglePassEnable(self, passidx):
        try:
            self.passes[passidx] = not self.passes[passidx]
        except:
            pass

    def GetEnabledPasses(self):
        return [i for i, dummy in filter(lambda x: x[1] == True, enumerate(self.passes))]

    def init(self):
        print 'Context.init(): Screen size=', repr(self.screen_size)
        
        self.setmodeCallback(self.screen_size)
        self.setup()

        self.color_texture = texture.Texture2D.from_surf(self.sourceSurface)
        #source_size = self.sourceSurface.get_size()
        source_size = self.screen_size
        self.mpass_texture1 = texture.Texture2D.from_empty(source_size)
        self.mpass_texture2 = texture.Texture2D.from_empty(source_size)

        self.fbos = [fbo.FBO2D(source_size), fbo.FBO2D(source_size)]
        self.fbos[0].attach_color_texture(self.mpass_texture1, 1)
        self.fbos[0].set_read(self.fbos[1], None)
        self.fbos[1].attach_color_texture(self.mpass_texture2, 1)
        self.fbos[1].set_read(self.fbos[0], None)

        self.ReloadShaders()
        

    def SetSource(self, source):
        self.sourceSurface = source
        self.Reinit(source.get_size())

    def Sprite(self, texture, xy, size):
        if texture == None:
            self.sprite = None
        else:
            self.sprite = texture
            self.spritexy = xy
            self.spritesize = size

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
        glDisable(GL_TEXTURE_2D)
        glColor4f(0, 0, 0, 1)
        enabled = [self.shaders[x] for x in self.GetEnabledPasses()]

        # Make sure that everything is cleared
        shader.Shader.use(None)
        fbo.FBO2D.set_write(self.fbos[0])
        glClear(GL_COLOR_BUFFER_BIT)
        fbo.FBO2D.set_write(self.fbos[1])
        glClear(GL_COLOR_BUFFER_BIT)
        fbo.FBO2D.set_write(None)
        glClear(GL_COLOR_BUFFER_BIT)

        if len(enabled) > 0:
            for i in xrange(len(enabled) - 1):
                pingpong = i % 2

                fbo.FBO2D.set_write(self.fbos[pingpong])
                #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

                shader.Shader.use(enabled[i])
                enabled[i].pass_vec2("color_texture_sz", self.sourceSurface.get_size())
                enabled[i].pass_texture_name(self.color_texture, self.color_texture.texture_id, "color_texture")
                if pingpong == 1:
                    enabled[i].pass_texture_name(self.mpass_texture1, self.mpass_texture1.texture_id, "mpass_texture")
                else:
                    enabled[i].pass_texture_name(self.mpass_texture2, self.mpass_texture2.texture_id, "mpass_texture")

                self.draw_screen_quad()

            pingpong = (len(enabled) - 1) % 2
            fbo.FBO2D.set_write(None)

            shader.Shader.use(enabled[-1])
            enabled[-1].pass_vec2("color_texture_sz", self.sourceSurface.get_size())
            enabled[-1].pass_texture_name(self.color_texture, self.color_texture.texture_id, "color_texture")

            # set additional uniforms from defaults
            for uniform, value in self.shader_manager.params.__dict__.iteritems():
                enabled[-1].pass_float(uniform, value)

            if pingpong == 1:
                enabled[-1].pass_texture_name(self.mpass_texture1, self.mpass_texture1.texture_id, "mpass_texture")
            else:
                enabled[-1].pass_texture_name(self.mpass_texture2, self.mpass_texture2.texture_id, "mpass_texture")

        self.draw_screen_quad()        

    def DrawTexture(self, texture):
        glEnable(GL_TEXTURE_2D)
        shader.Shader.use(None)
        glColor4f(1,1,1,1)
        glActiveTexture(GL_TEXTURE0)
        texture.bind()
        #print 'DrawTexture: bound %d' % texture.texture_id
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(                  0,                   0)
        glTexCoord2f(1, 0); glVertex2f(self.screen_size[0],                   0)
        glTexCoord2f(1, 1); glVertex2f(self.screen_size[0], self.screen_size[1]/4)
        glTexCoord2f(0, 1); glVertex2f(                  0, self.screen_size[1]/4)
        glEnd()
        glBlendFunc(GL_ONE, GL_ZERO)

    def DrawSprite(self):
        if self.sprite != None:
            glEnable(GL_TEXTURE_2D)
            shader.Shader.use(None)
            glColor4f(1,1,1,1)
            glActiveTexture(GL_TEXTURE0)
            self.sprite.bind()
            #print 'DrawSprite: bound %d' % self.sprite.texture_id

            x,y = self.spritexy
            w,h = self.spritesize

            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x, 0)
            glTexCoord2f(1, 0); glVertex2f(x + w, 0)
            glTexCoord2f(1, 1); glVertex2f(x + w, y + h)
            glTexCoord2f(0, 1); glVertex2f(x, y + h)
            glEnd()
            glBlendFunc(GL_ONE, GL_ZERO)
