from OpenGL.GL import *
from OpenGL.GLU import *
from math import *

def init_gl():
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

    glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_MODULATE)
    glTexEnvi(GL_POINT_SPRITE,GL_COORD_REPLACE,GL_TRUE)

    glHint(GL_PERSPECTIVE_CORRECTION_HINT,GL_NICEST)
    glEnable(GL_DEPTH_TEST)

def set_view_2D(dim_or_rect, near=-1.0,far=1.0):
    if len(dim_or_rect) == 2: rect = [0,0,dim_or_rect[0],dim_or_rect[1]]
    else:                     rect = dim_or_rect
    glViewport(*rect)
    
    glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(rect[0],rect[0]+rect[2], rect[1],rect[1]+rect[3], near,far)
    glMatrixMode( GL_MODELVIEW); glLoadIdentity()
def set_view_3D(dim_or_rect, angle, near=0.1,far=100.0):
    if len(dim_or_rect) == 2: rect = [0,0,dim_or_rect[0],dim_or_rect[1]]
    else:                     rect = dim_or_rect
    glViewport(*rect)
    
    glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(angle,float(rect[2])/float(rect[3]), near,far)
    glMatrixMode( GL_MODELVIEW); glLoadIdentity()

old_viewports = []
def view_push():
    glMatrixMode(GL_PROJECTION); glPushMatrix()
    glMatrixMode( GL_MODELVIEW); glPushMatrix()
    old_viewports.append(list(glGetIntegerv(GL_VIEWPORT)))
def view_pop():
    global old_viewports
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode( GL_MODELVIEW); glPopMatrix()
    glViewport(*old_viewports[-1])
    old_viewports = old_viewports[:-1]

def unproject(windowcoord,flip=True):
    viewport = glGetIntegerv(GL_VIEWPORT)
    
    winX = windowcoord[0]
    if flip: winY = viewport[3]-windowcoord[1]
    else:    winY =             windowcoord[1]
    winZ = glReadPixels(winX,winY,1,1,GL_DEPTH_COMPONENT,GL_FLOAT)[0][0]
    
    return list(gluUnProject(winX,winY,winZ,glGetDoublev(GL_MODELVIEW_MATRIX),glGetDoublev(GL_PROJECTION_MATRIX),viewport))

#Converts from spherical coordinates to rectangular coordinates
def spherical_to_rectangular(center_offset, radius, rot_y,rot_xz):
    return [ #rot_y is rotation about the y axis, rot_xz is elevation above or below the horizontal plane
        center_offset[0] + radius*cos(radians(rot_y))*cos(radians(rot_xz)),
        center_offset[1] + radius                    *sin(radians(rot_xz)),
        center_offset[2] + radius*sin(radians(rot_y))*cos(radians(rot_xz))
    ]

def set_camera_spherical(camera_center, camera_radius, rot_y,rot_xz):
    camera_pos = spherical_to_rectangular(camera_center, camera_radius, rot_y,rot_xz)
    gluLookAt(
        camera_pos[0],camera_pos[1],camera_pos[2],
        camera_center[0],camera_center[1],camera_center[2],
        0,1,0
    )
