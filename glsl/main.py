import pygame
from pygame.locals import *
import traceback
import random
import pygame.image
import sys
import time

from motor import ShaderParams, ShaderManager, Context

pygame.display.init()
pygame.font.init()

fps_count = 0

def loadSource():
    return pygame.image.load('testcard.png' if len(sys.argv) == 1 else sys.argv[1])

def updateCaption(shader_manager, context, fps):
    pygame.display.set_caption("Composite video simulation %dx%d [%s: gain=%2.2f invgain=%2.2f] %3.1ffps" % \
        tuple(list(context.screen_size) + \
            [shader_manager.CurrentName(), shader_manager.params.filter_gain, shader_manager.params.filter_invgain, fps]))

def get_input(shader_manager, context):
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
            updateCaption(shader_manager, context, fps_count)    
            #print 'Filter gain = %1.3f invgain = %1.3f' % (shader_params.filter_gain, shader_params.filter_invgain)
        elif event.type == VIDEORESIZE:
            #Resizing messes up the OpenGL context.  Make all our objects again.
            context.Reinit(list(event.size))
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

    iter = 0
    clock = pygame.time.Clock()
    while True:
        if not get_input(shaderManager, context): 
            break
        context.Draw()
        pygame.display.flip()
        clock.tick(60)        
        fps_count = clock.get_fps()
        iter += 1
        if iter > 60:
            iter -= 60
            updateCaption(shaderManager, context, fps_count)

    del context
    
    pygame.quit()

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
        pygame.quit()
        input()
