#version 120

uniform sampler2D color_texture;
uniform vec2 color_texture_sz;
uniform vec2 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;


#define PI          3.14159265358
#define FSC         4433618.75
#define LINETIME    64.0e-6 // 64 us total
#define VISIBLE     52.0e-6 // 52 us visible part
#define FLINE       (1.0/VISIBLE) // =15625 for 64ms, but = 19230 accounting for visible part only
#define VISIBLELINES 225//color_texture_sz.y//225

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

#define COMPOSITE
// Hard triads are hard bound to pixels, they correspond to MASK_SCALE 6
//#define HARD_TRIADS

#define VFREQ PI*(color_texture_sz.y)/1.0 // correct scanlines = 1
#define VPHASEDEG 0 // 0 for gosha, 90 for MESS
#define VPHASE (VPHASEDEG)*PI/(180.0*VFREQ)
#define PROMINENCE 0.4
#define FLATNESS 0.6

float scanline(float y, float luma) {
    // scanlines
    float w = (y + VPHASE) * VFREQ;
    
    float flatness = 2.0 - luma * 2.0 * FLATNESS;  // more luminance = more flatness
    float sinw = pow(abs(sin(w)), flatness);
    sinw = (1.0 - PROMINENCE) + sinw * PROMINENCE;    

    return sinw;
}

// BGR pattern for reproducing triplets on for RGB LCD displays plus mask
const vec3 triplets[3] = vec3[3] (
    vec3(0.0, 0.0, 1.0),
    vec3(0.0, 1.0, 0.0),
    vec3(1.0, 0.0, 0.0)
    );

const float hsofties[3] = float[3] (1.0, 0.0, 1.0);

#define HORZ_SOFT 0.2
#define VERT_SOFT 0.2 

vec3 mask(vec2 xy, float luma, vec3 rgb) {
    // calculate rgb stripes
    int xmod = int(mod(int(gl_FragCoord.x), 3));
    vec3 triads = triplets[xmod];
    float soft = hsofties[xmod];
    triads.g += VERT_SOFT * soft * (triads.r + triads.b);

    // B G R x x x -- pattern A: y mod 3 == 0 
    // B G R B G R
    // x x x B G R -- pattern B: y mod 3 == 2

    // pattern A: 1 1 1 0 0 0
    float A = step(0.5, mod(gl_FragCoord.x, 6.0) / 6.0);
    // pattern B: 0 0 0 1 1 1
    float B = 1.0 - A;

    float patterns[3];

    patterns[0] = clamp(A, HORZ_SOFT, 1.0);
    patterns[1] = 1.0;
    patterns[2] = clamp(B, HORZ_SOFT, 1.0);
    triads *= patterns[int(mod(gl_FragCoord.y, 3.0))];

    return triads;
}

vec3 testtriplets() {
    int fragx = int(gl_FragCoord.x);
    return triplets[int(mod(fragx, 3))];    
}


void main(void) {
    vec2 xy = gl_TexCoord[0].st;
    invx = 0.25 / (FSC/FLINE);
#ifdef COMPOSITE 
    width_ratio = color_texture_sz.x / (FSC / FLINE);
    height_ratio = 1.0; 
    altv = mod(floor(xy.y * VISIBLELINES + 0.5), 2.0) * PI;

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
#else
    vec3 rgb = fetch(0, xy, invx).xyz;
    float luma = (RGB_to_YUV * rgb).x;
#endif    

    // scanlines
    float scan = scanline(xy.y, luma);
    vec3 mask = scan * mask(xy, luma, rgb);
    rgb = rgb * mask;
    gl_FragColor = vec4(rgb, 1.0);

    vec3 gammaBoost = vec3(1.0/1.5, 1.0/1.35, 1.0/1.5);
    gl_FragColor.rgb = pow(gl_FragColor.rgb, gammaBoost);
}

