#version 120

uniform sampler2D color_texture;
uniform sampler2D mpass_texture;
uniform vec2 color_texture_sz;
uniform vec2 screen_texture_sz;

#define PI          3.14159265358
#define FSC         4433618.75
#define FLINE       15625
#define VISIBLELINES 312

#define RGB_to_YIQ  mat3x3( 0.299 , 0.595716 , 0.211456 ,   0.587    , -0.274453 , -0.522591 ,      0.114    , -0.321263 , 0.311135 )
#define YIQ_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.9563   , -0.2721   , -1.1070   ,      0.6210   , -0.6474   , 1.7046   )

#define RGB_to_YUV  mat3x3( 0.299 , -0.14713 , 0.615    ,   0.587    , -0.28886  , -0.514991 ,      0.114    , 0.436     , -0.10001 )
#define YUV_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.0      , -0.39465  , 2.03211   ,      1.13983  , -0.58060  , 0.0      )

#define fetch(ofs,center,invx) texture2D(mpass_texture, vec2((ofs) * (invx) + center.x, center.y))

#define FIRTAPS 20
const float FIR[FIRTAPS] = float[FIRTAPS] (-0.008030271,0.003107906,0.016841352,0.032545161,0.049360136,0.066256720,0.082120150,0.095848433,0.106453014,0.113151423,0.115441842,0.113151423,0.106453014,0.095848433,0.082120150,0.066256720,0.049360136,0.032545161,0.016841352,0.003107906);

#define FIR_GAIN 4
#define FIR_INVGAIN 1.6

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
        filtered += FIR_GAIN * vec2(texel.x, texel.y) * FIR[i];
        filtered += FIR_GAIN * vec2(texel.z, texel.w) * FIR[i + 1];
    }
    float subtract = FIR_INVGAIN * (filtered.x * sinwt + filtered.y * coswt);

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

