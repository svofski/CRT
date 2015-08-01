from OpenGL.GL import *
from OpenGL.GL.EXT.framebuffer_object import *


class AttachmentFBO:
    def __init__(self, attachment,gl_buffer):
        self.attachment = attachment
        self.gl_buffer = gl_buffer
        
class AttachmentTextureFBO(AttachmentFBO):
    def __init__(self, texture, attachment,gl_buffer):
        AttachmentFBO.__init__(self, attachment,gl_buffer)
        self.texture = texture

class AttachmentTextureColorFBO(AttachmentTextureFBO):
    def __init__(self, texture, index):
        self.index = GL_COLOR_ATTACHMENT0 + index
        AttachmentTextureFBO.__init__(self, texture, self.index,self.index)

class AttachmentTextureDepthFBO(AttachmentTextureFBO):
    def __init__(self, texture):
        AttachmentTextureFBO.__init__(self, texture, GL_DEPTH_ATTACHMENT,GL_NONE)

class AttachmentRenderbufferFBO(AttachmentFBO):
    def __init__(self, attachment,gl_buffer, format, size):
        AttachmentFBO.__init__(self, attachment,gl_buffer)
        self.renderbuffer = glGenRenderbuffersEXT(1)
        glBindRenderbufferEXT(GL_RENDERBUFFER,self.renderbuffer)
        glRenderbufferStorageEXT(GL_RENDERBUFFER,format,size[0],size[1])
    def __del__(self):
        glDeleteRenderbuffersEXT(1,[self.renderbuffer])

class AttachmentRenderbufferColorFBO(AttachmentRenderbufferFBO):
    def __init__(self, size, index, precision):
        if   precision ==  8: format = GL_RGBA8
        elif precision == 16: format = GL_RGBA16F
        elif precision == 32: format = GL_RGBA32F
        self.index = GL_COLOR_ATTACHMENT0 + index
        AttachmentRenderbufferFBO.__init__(self, self.index,self.index, format, size)

class AttachmentRenderbufferDepthFBO(AttachmentRenderbufferFBO):
    def __init__(self, size, precision):
        if   precision == 16: format = GL_DEPTH_COMPONENT16
        elif precision == 24: format = GL_DEPTH_COMPONENT24
        elif precision == 32: format = GL_DEPTH_COMPONENT32
        AttachmentRenderbufferFBO.__init__(self, GL_DEPTH_ATTACHMENT,GL_NONE, format, size)

class FBO2D:
    def __init__(self,size):
        self.attachments_color = [None]*8
        self.attachment_depth = None
        self.size = list(size)

        self.framebuffer_id = glGenFramebuffersEXT(1)
        
    def __del__(self):
        glDeleteFramebuffersEXT(1,[self.framebuffer_id])
        for attachment_color in self.attachments_color:
           if attachment_color != None: del attachment_color
        if self.attachment_depth != None: del self.attachment_depth

    def attach_color_texture(self,texture,index):
        self.attachments_color[index] = AttachmentTextureColorFBO(texture,index)
        self._attach_attachment_texture(self.attachments_color[index])

    def attach_depth_texture(self,texture):
        self.attachments_depth = AttachmentTextureDepthFBO(texture,index)
        self._attach_attachment_texture(self.attachments_color[index])

    def attach_color_renderbuffer(self,precision,index):
        self.attachments_color[index] = AttachmentRenderbufferColorFBO(self.size,index,precision)
        self._attach_attachment_renderbuffer(self.attachments_color[index])

    def attach_depth_renderbuffer(self,precision):
        self.attachments_depth = AttachmentRenderbufferDepthFBO(self.size,precision)
        self._attach_attachment_renderbuffer(self.attachments_depth)

    def _attach_attachment_texture(self,attachment):
        glBindFramebufferEXT(GL_FRAMEBUFFER,self.framebuffer_id)
        glFramebufferTexture2DEXT(GL_FRAMEBUFFER,attachment.attachment,GL_TEXTURE_2D,attachment.texture.texture_id,0)
        glBindFramebufferEXT(GL_FRAMEBUFFER,                  0)

    def _attach_attachment_renderbuffer(self,attachment):
        glBindFramebufferEXT(GL_FRAMEBUFFER,self.framebuffer_id)
        glFramebufferRenderbufferEXT(GL_FRAMEBUFFER,attachment.attachment,GL_RENDERBUFFER,attachment.renderbuffer)
        glBindFramebufferEXT(GL_FRAMEBUFFER,                  0)
        
    @staticmethod
    def set_read(fbo_read=None, color_index=None):
        if fbo_read == None:
            glBindFramebufferEXT(GL_READ_FRAMEBUFFER,0)
            glReadBuffer(GL_BACK)
        else:
            glBindFramebufferEXT(GL_READ_FRAMEBUFFER,fbo_read.framebuffer_id)
            if color_index == None:
                glReadBuffer(GL_NONE)
            else:
                glReadBuffer(fbo_read.attachments_color[color_index].gl_buffer)

    @staticmethod
    def set_write(fbo_write=None, colors="all"):
        if fbo_write == None:
            glBindFramebufferEXT(GL_DRAW_FRAMEBUFFER,0)
            glDrawBuffer(GL_BACK)
        else:
            glBindFramebufferEXT(GL_DRAW_FRAMEBUFFER,fbo_write.framebuffer_id)
            if colors == []:
                glDrawBuffer(GL_NONE)
            else:
                if colors == "all":
                    colors = []
                    for attachment_color in fbo_write.attachments_color:
                        if attachment_color == None: continue
                        colors.append(attachment_color.index)
                    flag = 0x00000000
                    for color in colors:
                        flag |= color
                    glDrawBuffer(flag)

    def print_error(self):     
        def get_error():
            status = glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT)
            try:
                if status == GL_FRAMEBUFFER_BINDING_EXT:                         return "GL_FRAMEBUFFER_BINDING"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_COMPLETE_EXT:                        return "GL_FRAMEBUFFER_COMPLETE"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT_EXT:           return "GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS_EXT:           return "GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_DRAW_BUFFER_EXT:          return "GL_FRAMEBUFFER_INCOMPLETE_DRAW_BUFFER"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_DUPLICATE_ATTACHMENT_EXT: return "GL_FRAMEBUFFER_INCOMPLETE_DUPLICATE_ATTACHMENT"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_FORMATS_EXT:              return "GL_FRAMEBUFFER_INCOMPLETE_FORMATS"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_LAYER_TARGETS_EXT:        return "GL_FRAMEBUFFER_INCOMPLETE_LAYER_TARGETS"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT_EXT:   return "GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_EXT:          return "GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_INCOMPLETE_READ_BUFFER_EXT:          return "GL_FRAMEBUFFER_INCOMPLETE_READ_BUFFER"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_STATUS_ERROR_EXT:                    return "GL_FRAMEBUFFER_STATUS_ERROR"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_UNDEFINED_EXT:                       return "GL_FRAMEBUFFER_UNDEFINED"
            except: pass
            try:
                if status == GL_FRAMEBUFFER_UNSUPPORTED_EXT:                     return "GL_FRAMEBUFFER_UNSUPPORTED"
            except: pass
            return "unknown FBO error ("+str(status)+")"
        print(get_error())
        
