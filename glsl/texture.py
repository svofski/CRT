from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.EXT.texture_filter_anisotropic import *
import pygame

class Texture2D:
    def __init__(self, size, precision, raw_data,data_type,data_channels):
        self.texture_id = glGenTextures(1)
        self.bind()
        
        if precision == 8:
            internal_format = GL_RGBA
        elif precision == 16:
            internal_format = GL_RGBA16F
        elif precision == 32:
            internal_format = GL_RGBA32F
            
        if data_channels == 3:
            data_format = GL_RGB
        else:
            data_format = GL_RGBA
            
        glTexImage2D(GL_TEXTURE_2D, 0, internal_format, size[0],size[1], 0, data_format, data_type, raw_data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

    def __del__(self):
        glDeleteTextures(self.texture_id)

    @staticmethod
    def from_path(path,precision=8):
        surf = pygame.image.load(path).convert_alpha()
        return Texture2D.from_surf(surf,precision)

    @staticmethod
    def from_empty(size,precision=8):
        return Texture2D(
            size,
            precision,
            None,GL_UNSIGNED_BYTE,4
        )

    @staticmethod
    def from_data(numpy_fdata_rgba,precision=8):
        return Texture2D(
            (numpy_fdata_rgba.shape[0],numpy_fdata_rgba.shape[1]),
            precision,
            numpy_fdata_rgba,GL_FLOAT,numpy_fdata_rgba.shape[2]
        )

    @staticmethod
    def from_surf(surface,precision=8):
        return Texture2D(
            surface.get_size(),
            precision,
            pygame.image.tostring(surface,"RGBA",1),GL_UNSIGNED_BYTE,4
        )

    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

    def set_nicest(self):
        self.bind()
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        #Anisotropic Filtering - Makes textures look nice at an angle, but optional
        glTexParameterf(GL_TEXTURE_2D,GL_TEXTURE_MAX_ANISOTROPY_EXT,glGetFloatv(GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT))
        #Mipmapping - Makes textures look nice when minified, but optional
        glGenerateMipmap(GL_TEXTURE_2D)
