#version 120

uniform sampler2D color_texture;
uniform vec2 color_texture_sz;
uniform vec2 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;

#define PI          3.14159265358
#define FSC         4433618.75
#define FLINE       15625
#define VISIBLELINES 312

#define RGB_to_YIQ  mat3x3( 0.299 , 0.595716 , 0.211456 ,   0.587    , -0.274453 , -0.522591 ,      0.114    , -0.321263 , 0.311135 )
#define YIQ_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.9563   , -0.2721   , -1.1070   ,      0.6210   , -0.6474   , 1.7046   )

#define RGB_to_YUV  mat3x3( 0.299 , -0.14713 , 0.615    ,   0.587    , -0.28886  , -0.514991 ,      0.114    , 0.436     , -0.10001 )
#define YUV_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.0      , -0.39465  , 2.03211   ,      1.13983  , -0.58060  , 0.0      )

#define fetch(ofs,center,invx) texture2D(color_texture, vec2((ofs) * (invx) + center.x, center.y))

#define FIRTAPS 20
const float FIR[FIRTAPS] = float[FIRTAPS] (-0.008030271,0.003107906,0.016841352,0.032545161,0.049360136,0.066256720,0.082120150,0.095848433,0.106453014,0.113151423,0.115441842,0.113151423,0.106453014,0.095848433,0.082120150,0.066256720,0.049360136,0.032545161,0.016841352,0.003107906);

#define FIR_GAIN 2.0
#define FIR_INVGAIN 0.8
//#define FIR_GAIN filter_gain
//#define FIR_INVGAIN filter_invgain

float width_ratio;
float height_ratio;
float altv;
float invx;


float modulated(vec2 xy, float sinwt, float coswt) {
    vec3 rgb = fetch(0, xy, invx).xyz;
    vec3 yuv = RGB_to_YUV * rgb;

    return clamp(yuv.x + yuv.y * sinwt + yuv.z * coswt, 0.0, 1.0);    
}

vec2 modem_uv(vec2 xy, int ofs) {
    float t = (xy.x + ofs * invx) * color_texture_sz.x;
    float wt = t * 2 * PI / width_ratio;

    float sinwt = sin(wt);
    float coswt = cos(wt + altv);

    vec3 rgb = fetch(ofs, xy, invx).xyz;
    vec3 yuv = RGB_to_YUV * rgb;
    float signal = clamp(yuv.x + yuv.y * sinwt + yuv.z * coswt, 0.0, 1.0);

    return vec2(signal * sinwt, signal * coswt);
}


void main(void) {
    vec2 xy = gl_TexCoord[0].st;
    width_ratio = color_texture_sz.x / (FSC / FLINE);
    height_ratio = 1.0; 
    altv = mod(floor(xy.y * VISIBLELINES + 0.5), 2.0) * PI;
    invx = 0.25 / (FSC/FLINE);

    // lowpass U/V at baseband
    vec2 filtered = vec2(0.0, 0.0);
    for (int i = 0; i < FIRTAPS; i++) {
        vec2 uv = modem_uv(xy, i - FIRTAPS/2);
        filtered += FIR_GAIN * uv * FIR[i];
    }

    float t = xy.x * color_texture_sz.x;
    float wt = t * 2 * PI / width_ratio;

    float sinwt = sin(wt);
    float coswt = cos(wt + altv);

    float luma = modulated(xy, sinwt, coswt) - FIR_INVGAIN * (filtered.x * sinwt + filtered.y * coswt);
    vec3 yuv_result = vec3(luma, filtered.x, filtered.y);

    gl_FragColor = vec4(YUV_to_RGB * yuv_result, 1.0);
}
