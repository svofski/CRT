from OpenGL.GL import *
from OpenGL.GL.ARB.shader_objects import *
from OpenGL.GL.ARB.vertex_shader import *
from OpenGL.GL.ARB.fragment_shader import *


class ProgramShaderBase(object):
    def __init__(self,source,type):
        self.source = source
        
        self.program = glCreateShaderObjectARB(type)
        
        glShaderSourceARB(self.program,[source]) #Crucial for AMD compatibility to have []
        glCompileShaderARB(self.program)

        self.errors = glGetInfoLogARB(self.program)
    def __del__(self):
        glDeleteObjectARB(self.program)
        
    def print_errors(self):
        for line in self.errors.split(b"\n"):
            print(line)
        
class ProgramShaderVertex(ProgramShaderBase):
    def __init__(self,source):
        ProgramShaderBase.__init__(self,source,GL_VERTEX_SHADER_ARB)
        
class ProgramShaderFragment(ProgramShaderBase):
    def __init__(self,source):
        ProgramShaderBase.__init__(self,source,GL_FRAGMENT_SHADER_ARB)


class Shader:
    def __init__(self,programs):
        self.shader = glCreateProgramObjectARB()
        
        for program in programs:
            glAttachObjectARB(self.shader, program.program)
            
        glValidateProgramARB(self.shader)
        glLinkProgramARB(self.shader)

        self.errors = glGetInfoLogARB(self.shader)

        self.symbol_locations = {}
        
    def __del__(self):
        glDeleteObjectARB(self.shader)

    def get_location(self,symbol):
        if not symbol in self.symbol_locations.keys():
            self.symbol_locations[symbol] = glGetUniformLocation(self.shader, symbol.encode())
            if self.symbol_locations[symbol] == -1:
                print("Cannot get the location of symbol \""+symbol+"\"!")
        return self.symbol_locations[symbol]
    def pass_int(self,symbol,i):
        glUniform1i(self.get_location(symbol),i)
    def pass_float(self,symbol,f):
        glUniform1f(self.get_location(symbol),f)
    def pass_bool(self,symbol,b):
        glUniform1i(self.get_location(symbol),b)
    def pass_vec2(self,symbol,v):
        glUniform2f(self.get_location(symbol),v[0],v[1])
    def pass_vec3(self,symbol,v):
        glUniform3f(self.get_location(symbol),v[0],v[1],v[2])
    def pass_vec4(self,symbol,v):
        glUniform4f(self.get_location(symbol),v[0],v[1],v[2],v[3])

    def pass_texture_name(self, texture, number, name):
        glActiveTexture(GL_TEXTURE0 + number - 1)
        active_texture = glGetIntegerv(GL_ACTIVE_TEXTURE) - GL_TEXTURE0
        if texture == None:
            glBindTexture(GL_TEXTURE_2D, 0)
        else:
            texture.bind()
            glUniform1i(self.get_location(name), active_texture)
        glActiveTexture(GL_TEXTURE0)

    def pass_texture(self,texture,number):
        print 'pass_texture', number
        glActiveTexture(GL_TEXTURE0+number-1)
        active_texture = glGetIntegerv(GL_ACTIVE_TEXTURE) - GL_TEXTURE0
        if texture == None:
            glBindTexture(GL_TEXTURE_2D,0)
        else:
            texture.bind()
            glUniform1i(self.get_location("tex2D_"+str(number)),active_texture)
        glActiveTexture(GL_TEXTURE0)

    def print_errors(self):
        for line in self.errors.split(b"\n"):
            print(line)

    @staticmethod
    def use(shader=None):
        if shader == None:
            glUseProgramObjectARB(0)
        else:
            glUseProgramObjectARB(shader.shader)
        
