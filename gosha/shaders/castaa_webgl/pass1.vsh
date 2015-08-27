#version 120

attribute vec3 Vertex;
attribute vec2 TexCoord0;

uniform float time;
varying mat3 xform_Torus;
varying mat4 xform_WedgeCut;
varying mat4 xform_MotorSideCut;
varying mat3 xform_DiskSpin;

uniform mat4 MVP;

mat4 mRot(float x, float y, float z, vec4 translation) {
    float cosx = cos(x);
    float sinx = sin(x);
    float cosy = cos(y);
    float siny = sin(y);
    float cosz = cos(z);
    float sinz = sin(z);
    return mat4(
        vec4(cosy * cosz, cosy * sinz,  -siny, 0.0),
        vec4(cosz * sinx * siny - cosx * sinz, cosx * cosz + sinx * siny * sinz, cosy * sinx, 0.0),
        vec4(cosx * cosz * siny + sinx * sinz, cosx * siny * sinz - cosz * sinx, cosx * cosy, 0.0),
        translation
        );
}


void main()
{
        gl_TexCoord[0].st = vec2(TexCoord0.x, 1.0 - TexCoord0.y); // flip back azul3d vertical flippance
        gl_Position = MVP * vec4(Vertex, 1.0);
				xform_Torus =mat3(mRot(radians(time*100.0), 0.0, radians(45.0), vec4(0.0, 0.0, 0.0, 1.0)));
				xform_WedgeCut = mRot(0.0, 0.0, radians(45.0), vec4(-0.55, 0.0, 0.0, 1.0));
				xform_MotorSideCut = mRot(0.0, 0.0, radians(20.0), vec4(0.8, 0.0, 0.0, 1.0));
				xform_DiskSpin = mat3(mRot(0.0, 0.0, time * 0.71, vec4(0.0)));
}
