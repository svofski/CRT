#version 120

// --- 
uniform sampler2D Texture0;
uniform sampler2D Texture1;
#define color_texture Texture0
#define mpass_texture Texture1
uniform vec3 color_texture_sz;
// ---

//uniform sampler2D color_texture;
//uniform vec2 color_texture_sz;
uniform vec2 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;

#define PI          3.14159265358
#define FSC         4433618.75
#define LINETIME    64.0e-6 // 64 us total
#define VISIBLE     52.0e-6 // 52 us visible part
#define FLINE       (1.0/VISIBLE) // =15625 for 64ms, but = 19230 accounting for visible part only
#define VISIBLELINES 312

#define RGB_to_YIQ  mat3x3( 0.299 , 0.595716 , 0.211456 ,   0.587    , -0.274453 , -0.522591 ,      0.114    , -0.321263 , 0.311135 )
#define YIQ_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.9563   , -0.2721   , -1.1070   ,      0.6210   , -0.6474   , 1.7046   )

#define RGB_to_YUV  mat3x3( 0.299 , -0.14713 , 0.615    ,   0.587    , -0.28886  , -0.514991 ,      0.114    , 0.436     , -0.10001 )
#define YUV_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.0      , -0.39465  , 2.03211   ,      1.13983  , -0.58060  , 0.0      )

#define fetch(ofs,center,invx) texture2D(mpass_texture, vec2((ofs) * (invx) + center.x, center.y))

#define FIRTAPS 20
const float FIR[FIRTAPS]=float[FIRTAPS] (0.030289281,0.034690838,0.039020054,0.043168185,0.047027347,0.050494338,0.053474373,0.055884554,0.057656942,0.058741099,0.059105978,0.058741099,0.057656942,0.055884554,0.053474373,0.050494338,0.047027347,0.043168185,0.039020054,0.034690838);

#define FIR_GAIN 4
#define FIR_INVGAIN 2.3

void main(void) {
    vec2 xy = gl_TexCoord[0].st;
    vec3 suv = texture2D(mpass_texture, xy).xyz + vec3(0.0, -0.5, -0.5);

    float width_ratio = color_texture_sz.x / (FSC / FLINE);

    float t = xy.x * color_texture_sz.x;
    float wt = t * 2 * PI / width_ratio;

    float altv = mod(floor(xy.y * VISIBLELINES + 0.5), 2.0) * PI;
    float sinwt = sin(wt);
    float coswt = cos(wt + altv);

    // lowpass U/V at baseband
    vec2 filtered = vec2(0.0, 0.0);
    float invx = 1.0 / color_texture_sz.x;
    for (int i = 0; i < FIRTAPS/2; i+=2) {
        vec4 texel = fetch(i - FIRTAPS/4, xy, invx) + vec4(-0.5, -0.5, -0.5, -0.5);
        filtered += filter_gain * vec2(texel.x, texel.y) * FIR[i];
        filtered += filter_gain * vec2(texel.z, texel.w) * FIR[i + 1];
    }
    float subtract = filter_invgain * (filtered.x * sinwt + filtered.y * coswt);

    // we could not pass Y through textures, so to be fair, reencode the signal again 
    xy = gl_TexCoord[0].st;
    vec3 rgb2 = texture2D(color_texture, xy).xyz;
    vec3 yuv = RGB_to_YUV * rgb2;
    t = xy.x * color_texture_sz.x;
    wt = t * 2 * PI / width_ratio;
    sinwt = sin(wt);
    coswt = cos(wt + altv);
    float reencoded = clamp(yuv.x + yuv.y * sinwt + yuv.z * coswt, 0.0, 1.0);

    float recovered_luma = reencoded - subtract;

    vec3 rgb = YUV_to_RGB * vec3(recovered_luma, filtered.x, filtered.y);
    gl_FragColor = vec4(rgb, 1.0);
}

