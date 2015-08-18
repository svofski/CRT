#version 120
//uniform sampler2D color_texture;

uniform sampler2D Texture0;
#define color_texture Texture0
#define TEXCOORD gl_TexCoord[0].st

//uniform vec2 color_texture_sz;
uniform vec3 color_texture_sz;
uniform vec3 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;


#define PI          3.14159265358
#define FSC         4433618.75
#define LINETIME    64.0e-6 // 64 us total
#define VISIBLE     52.0e-6 // 52 us visible part
#define FLINE       (1.0/VISIBLE) // =15625 for 64ms, but = 19230 accounting for visible part only
#define VISIBLELINES 225

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


#define VFREQ PI*(color_texture_sz.y)/2.0 // correct scanlines
#define VPHASEDEG 0
#define VPHASE (VPHASEDEG)*PI/(180.0*VFREQ)
#define PROMINENCE 0.8
#define FLATNESS 0.6

float scanline(float y, float luma) {
    // scanlines
    float w = (y + VPHASE) * VFREQ;
    
    float flatness = 2.0 - luma * 2.0 * FLATNESS;  // more luminance = more flatness
    float sinw = pow(abs(sin(w)), flatness);
    sinw = (1.0 - PROMINENCE) + sinw * PROMINENCE;    

    return sinw;
}

#define MASK_PHASE 0
#define MASK_SCALE 6 // works great but is too large for irl
#define MVFREQ (screen_texture_sz.y * (2.0*PI/MASK_SCALE) * 2.0)
#define HFREQ  (screen_texture_sz.x * (2.0*PI/MASK_SCALE))

// 0.0 = Maximal masking, 1.0 = No mask
#define MASK_CUTOFF 0.0
// 0.0 = Strongest RGB triads, 1.0 = No triads effect
#define TRIADS_CUTOFF 0.0
// 0.0 = No triads, 1.0 = sharpest triads
#define TRIADS_MIX 1.0

#define GFREQ HFREQ*2
// offsetting grille phase may improve colour, but tends to distort triads
#define G0 0
#define GR ((G0+0)*PI/180.0)
#define GG (-(G0+120.0)*PI/180.0)
#define GB (-(G0+240.0)*PI/180.0)

float prune(float val, float cutoff, float max) {
    return val >= cutoff ? clamp(val, cutoff, max) : 0;
}

vec3 mask(vec2 xy, float luma, vec3 rgb) {
    // calculate rgb stripes
    float wt = xy.x * GFREQ;
    vec3 triads = vec3(sin(wt + GR), sin(wt + GG), sin(wt + GB));
    triads = (1.0 - TRIADS_MIX) + clamp(triads, TRIADS_CUTOFF, 1.0);

    triads = step(0.55, triads);

    // calculate shadow mask spots

    float powa = 1.0 - clamp(luma, 0.0, 0.8);
    float fu = pow(clamp(sin(xy.x * HFREQ + MASK_PHASE) * sin(xy.y * MVFREQ + MASK_PHASE), MASK_CUTOFF, 1.0), powa);
    float astigmatism = dot(vec3(-1.0, 1.0, 1.0) * triads, rgb);
    xy.y += (1.1 + 0.1*astigmatism)/screen_texture_sz.y * MASK_SCALE;
    float fv = pow(clamp(sin(xy.x * HFREQ + MASK_PHASE) * sin(xy.y * MVFREQ + MASK_PHASE), MASK_CUTOFF, 1.0), powa);
    float maskvalue = clamp(fu + fv, MASK_CUTOFF, 1.0);

    return maskvalue * triads;
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

    vec3 rgb = YUV_to_RGB * yuv_result;

    //rgb = fetch(0, xy, invx).xyz;

    // scanlines
    float scan = scanline(xy.y, luma);
    vec3 mask = scan * mask(xy, luma, rgb);
    rgb = rgb * mask;
    gl_FragColor = vec4(rgb, 1.0);
    //vec3 gammaBoost = vec3(1.0/1.35, 1.0/1.55, 1.0/1.95);
    vec3 gammaBoost = vec3(1.0/1.95, 1.0/1.55, 1.0/1.65);
    gammaBoost *= 1.3;
    gl_FragColor.rgb = pow(gl_FragColor.rgb, gammaBoost);

}

