from OpenGL.GL import *
from OpenGL.GLU import *
import pygame
from pygame.locals import *
import traceback
import random
import gl_util, fbo, shader, texture
pygame.display.init()
pygame.font.init()

fullscreen = False
if fullscreen:
    #screen_size = [1680,1050]
    screen_size = [1920,1080]
else:
    screen_size = [800,600]

texture_size = [200, 200]

color_alive = 1.0
color_dead = 0.0

icon = pygame.Surface((1,1)); icon.set_alpha(0); pygame.display.set_icon(icon)
pygame.display.set_caption("Conway's Game of Life - Ian Mallett - v.2 - 2012")
flags = OPENGL|DOUBLEBUF|RESIZABLE
if fullscreen: flags |= FULLSCREEN
pygame.display.set_mode(screen_size,flags)

glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

glEnable(GL_TEXTURE_2D)
glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE)
glTexEnvi(GL_POINT_SPRITE,GL_COORD_REPLACE,GL_TRUE)

def init():
    global tex1,tex2
    global fbo1,fbo2
    global shader_conway

    tex1 = texture.Texture2D.from_empty(texture_size)
    tex2 = texture.Texture2D.from_empty(texture_size)

    fbo1 = fbo.FBO2D(screen_size)
    fbo1.attach_color_texture(tex1,1)

    fbo2 = fbo.FBO2D(screen_size)
    fbo2.attach_color_texture(tex2,1)

    shader_conway = shader.Shader([
        shader.ProgramShaderFragment(
        """
            #version 120

            uniform sampler2D tex2D_1;
            uniform vec2 size;

            void main(void) {
                vec2 pixel = gl_TexCoord[0].xy * size;

                int neighbors = 0;

                neighbors += (texture2D(tex2D_1,(pixel+vec2(-1.0,-1.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;
                neighbors += (texture2D(tex2D_1,(pixel+vec2(-1.0, 0.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;
                neighbors += (texture2D(tex2D_1,(pixel+vec2(-1.0, 1.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;

                neighbors += (texture2D(tex2D_1,(pixel+vec2( 0.0,-1.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;
                bool alive = (texture2D(tex2D_1,(pixel+vec2( 0.0, 0.0))/size).r=="""+str(color_alive)+""");
                neighbors += (texture2D(tex2D_1,(pixel+vec2( 0.0, 1.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;

                neighbors += (texture2D(tex2D_1,(pixel+vec2( 1.0,-1.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;
                neighbors += (texture2D(tex2D_1,(pixel+vec2( 1.0, 0.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;
                neighbors += (texture2D(tex2D_1,(pixel+vec2( 1.0, 1.0))/size).r=="""+str(color_alive)+""") ? 1 : 0;

                if (alive) {
                    switch (neighbors) {
                        case 8:
                        case 7:
                        case 6:
                        case 5:
                        case 4:
                            alive = false;
                            break;
                        case 3:
                        case 2:
                            break;
                        case 1:
                        case 0:
                            alive = false;
                            break;
                        default:
                            break;
                    }
                }
                else if (neighbors==3) {
                    alive = true;
                }

                gl_FragColor = vec4(  alive ? vec3("""+str(color_alive)+""") : vec3("""+str(color_dead)+"""),  1.0  );
            }
        """)
    ])
    #shader_conway.print_errors()
def deinit():
    global tex1,tex2
    global fbo1,fbo2
    global shader_conway

    del tex1
    del tex2

    del fbo1
    del fbo2

    del shader_conway

to_add = []
iterations = -1
def get_input():
    global iterations, screen_size
    
    def add_event(position):
        offsets = []
        for i in range(10):
            offsets.append([
                random.choice(range(-4,4+1,1)),
                random.choice(range(-4,4+1,1))
            ])
        for offset in offsets:
            to_add.append([
                offset[0] +                 position[0],
                offset[1] + (screen_size[1]-position[1])
            ])

    keys_pressed = pygame.key.get_pressed()
    mouse_buttons = pygame.mouse.get_pressed()
    mouse_position = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if   event.type == QUIT: return False
        elif event.type == KEYDOWN:
            if   event.key == K_ESCAPE: return False
            elif event.key == K_p: #pause/unpause
                if iterations == -1: iterations = 0
                else: iterations = -1
            elif event.key == K_s: #step one iteration
                if iterations == 0: iterations = 1
            elif event.key == K_r: #reset
                fbo1.enable(GLLIB_ALL); Window.clear(); fbo1.disable()
                fbo2.enable(GLLIB_ALL); Window.clear(); fbo2.disable()
        elif event.type == MOUSEBUTTONDOWN and not (keys_pressed[K_LCTRL] or keys_pressed[K_RCTRL]):
            add_event(mouse_position)
        elif event.type == VIDEORESIZE:
            screen_size = list(event.size)
            #Resizing messes up the OpenGL context.  Make all our objects again.
            deinit()
            init()
    if mouse_buttons[0] and (keys_pressed[K_LCTRL] or keys_pressed[K_RCTRL]):
        add_event(mouse_position)
    return True

ping_pong = 1
def draw_point(location):
    glVertex2f(location[0],  location[1]  )
    glVertex2f(location[0]+1,location[1]  )
    glVertex2f(location[0]+1,location[1]+1)
    glVertex2f(location[0],  location[1]+1)
def draw_screen_quad(texture):
    texture.bind()
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex2f(             0,             0)
    glTexCoord2f(1,0); glVertex2f(screen_size[0],             0)
    glTexCoord2f(1,1); glVertex2f(screen_size[0],screen_size[1])
    glTexCoord2f(0,1); glVertex2f(             0,screen_size[1])
    glEnd()
def draw_update(texture):
    global to_add
    shader.Shader.use(shader_conway)
    shader_conway.pass_vec2("size",texture_size)
    draw_screen_quad(texture)
    if len(to_add) != 0:
        shader.Shader.use(None)

        glDisable(GL_TEXTURE_2D)
        glColor3f(color_alive,color_alive,color_alive)
        glBegin(GL_QUADS)
        for loc in to_add:
            for point in [[0,0],[0,1],[0,-1]]:
                draw_point([loc[i]+point[i] for i in [0,1]])
                print repr([loc[i]+point[i] for i in [0,1]])
        to_add = []
        glEnd()
        glColor3f(1,1,1)
        glEnable(GL_TEXTURE_2D)
def draw():
    global ping_pong, iterations

    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    gl_util.set_view_2D(screen_size)

    if iterations == -1 or iterations > 0:
        if ping_pong == 1:
            fbo.FBO2D.set_write(fbo1)
            draw_update(tex2)
            fbo.FBO2D.set_write(None)

            draw_screen_quad(tex1)
        elif ping_pong == 2:
            fbo.FBO2D.set_write(fbo2)
            draw_update(tex1)
            fbo.FBO2D.set_write(None)

            draw_screen_quad(tex2)

        ping_pong = 3 - ping_pong
        if iterations != -1: iterations -= 1

    if ping_pong == 1:
        draw_screen_quad(tex2)
    elif ping_pong == 2:
        draw_screen_quad(tex1)
    
    pygame.display.flip()
def main():
    init()
    
    clock = pygame.time.Clock()
    while True:
        if not get_input(): break
        draw()
        clock.tick(60)

    deinit()
    
    pygame.quit()
if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
        pygame.quit()
        input()
