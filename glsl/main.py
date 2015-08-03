import pygame
from pygame.locals import *
import traceback
import random
import pygame.image
import sys
import time
import texture
import glob, os

from motor import ShaderParams, ShaderManager, Context

sources = None
sourceindex = -1

FontName, FontSize, BigFontSize = 'Andale Mono, Consolas', 24, 48

pygame.display.init()
pygame.font.init()

fps_count = 0

class Legend(object):
    """docstring for Legend"""

    text = ["m:    next shader    n: next image",
            "q/w:  adjust filter_gain by 0.1",
            "a/s:  adjust filter_invgain by 0.01",
            "z/x:  adjust filter_invgain by 0.1",            
            "1..9: disable shader passes",
            "h:    hide this legend"]

    def __init__(self):
        super(Legend, self).__init__()
        self.font = None
        self.color = pygame.Color(255, 255, 255, 255)
        self.bgcolor = pygame.Color(0, 0, 0, 155)
        self.visible = True
        self.texture = None
        self.frame = 0
        self.xpos = 0
        self.snailsize = (0, 0)
        self.snail = None

    def Resize(self, size):
        self.size = size
        rect = pygame.Rect((0, 0), size)
        self.surface = pygame.Surface(size, SRCALPHA)
        self.surface.fill(self.bgcolor)
        self.update()

    def ToggleVisible(self):
        self.visible  = not self.visible
        if self.visible:
            self.xpos = self.size[0] + self.snailsize[0] * 20

    def AnimFrame(self, context):
        if self.snail != None and self.xpos > -self.snailsize[0]:
            self.frame = (self.frame + 1) % 4
            self.xpos = self.xpos - 4
            context.Sprite(self.snail[self.frame], (self.xpos, 0), self.snailsize)
        else:
            context.Sprite(None, None, None)

    def update(self):
        # fit 4 lines in available space
        size = self.size[1] / (len(self.text) + 1)
        #size = 48
        lineheight = self.size[1] / len(self.text)

        self.font = pygame.font.SysFont(FontName, size)
        y = lineheight / 8
        for text in self.text:
            label = self.font.render(text, 1, self.color)
            self.surface.blit(label, (self.size[0]*0.05, y))
            y += lineheight

        if self.texture != None:
            del self.texture
        self.texture = texture.Texture2D.from_surf(self.surface)

        # load the snails
        try:
            self.snail = []
            for frame in [pygame.image.load('osd/snail-f%d.png' % x) for x in xrange(1,5)]:
                frame.set_colorkey(pygame.Color(0, 0, 0))
                self.snailsize = frame.get_size()
                surface = pygame.Surface(self.snailsize, SRCALPHA)
                surface.fill(pygame.Color(0, 0, 0, 0))
                surface.blit(frame, (0, 0))
                self.snail.append(texture.Texture2D.from_surf(surface))
                #print 'snail texture id: ', self.snail[-1].texture_id
            self.xpos = self.size[0] + self.snailsize[0] * 20
        except:
            self.snail = None
            pass

        #print 'legend texture id=', self.texture.texture_id


def globSources():
    return glob.glob("images/*.png")
    

def loadSource():
    global sources, sourceindex
    default = 'images' + os.path.sep + 'testcard.png'
    if sources == None:
        sources = globSources()
        sourceindex = -1
        if len(sys.argv) > 1:
            default = sys.argv[1]
        try:
            print 'default=', default, ' sources=', sources
            sources.remove(default)
        except:
            pass
        sources = [default] + sources

    sourceindex = (sourceindex + 1) % len(sources)
    return pygame.image.load(sources[sourceindex])

def updateCaption(shader_manager, context, fps):
    pygame.display.set_caption("Composite video simulation %dx%d [%s P%s: gain=%2.2f invgain=%2.2f] %3.1ffps" % \
        tuple(list(context.screen_size) + \
            [shader_manager.CurrentName(), repr([x + 1 for x in context.GetEnabledPasses()]), shader_manager.params.filter_gain, shader_manager.params.filter_invgain, fps]))

def get_input(shader_manager, context, legend):
    keys_pressed = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    mouse_position = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == QUIT: return False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE: 
                return False
            elif event.key == K_q:
                shader_manager.params.filter_gain -= 0.1
            elif event.key == K_w:
                shader_manager.params.filter_gain += 0.1
            elif event.key == K_a:
                shader_manager.params.filter_invgain -= 0.01
            elif event.key == K_s:
                shader_manager.params.filter_invgain += 0.01
            elif event.key == K_z:
                shader_manager.params.filter_invgain -= 0.1
            elif event.key == K_x:
                shader_manager.params.filter_invgain += 0.1
            elif event.key == K_m:
                shader_manager.LoadNext()
                context.ReloadShaders()
            elif event.key == K_n:
                context.SetSource(loadSource())
                legend.Resize(legend.size)

            elif event.key in [K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9]:
                context.TogglePassEnable(event.key - K_1)
            elif event.key == K_h:
                legend.ToggleVisible()
            updateCaption(shader_manager, context, fps_count)    
            #print 'Filter gain = %1.3f invgain = %1.3f' % (shader_params.filter_gain, shader_params.filter_invgain)
        elif event.type == VIDEORESIZE:
            #Resizing messes up the OpenGL context.  Make all our objects again.
            context.Reinit(list(event.size))

            legend.Resize((event.size[0], event.size[1]/4))
    return True

def main():
    def SetMode(size):
        pygame.display.set_mode(size, OPENGL | DOUBLEBUF | RESIZABLE)
            
    sourceSurface = loadSource()

    pygame.display.set_icon(sourceSurface)
    SetMode(sourceSurface.get_size())

    shaderManager = ShaderManager()
    shaderManager.LoadNext()
    context = Context(sourceSurface, shaderManager, SetMode)

    context.init()
    
    updateCaption(shaderManager, context, 0)

    legend = Legend()
    legend.Resize((sourceSurface.get_size()[0], sourceSurface.get_size()[1]/4))

    iter = 0
    clock = pygame.time.Clock()
    while True:
        if not get_input(shaderManager, context, legend): 
            break
        context.Draw()
        if legend.visible:
            context.DrawTexture(legend.texture)
            context.DrawSprite()
            if iter % 4 == 0:
                legend.AnimFrame(context)
        pygame.display.flip()
        clock.tick(60)        
        fps_count = clock.get_fps()
        iter += 1
        if iter % 60 == 0:
            updateCaption(shaderManager, context, fps_count)

    del context
    
    pygame.quit()

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
        pygame.quit()
