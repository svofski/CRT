#version 120

//uniform sampler2D color_texture;
//uniform sampler2D mpass_texture;

uniform sampler2D Texture0;
uniform sampler2D Texture1;
#define color_texture Texture0
#define mpass_texture Texture1


uniform vec3 color_texture_sz;
uniform vec3 screen_texture_sz;
//uniform vec2 color_texture_sz;
//uniform vec2 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;

#define PI          3.14159265358
#define FSC         4433618.75
#define LINETIME    64.0e-6 // 64 us total
#define VISIBLE     52.0e-6 // 52 us visible part
#define FLINE       (1.0/VISIBLE) // =15625 for 64ms, but = 19230 accounting for visible part only
#define VISIBLELINES 2//312.0//(576.0/2.0)//312.0

#define RGB_to_YIQ  mat3x3( 0.299 , 0.595716 , 0.211456 ,   0.587    , -0.274453 , -0.522591 ,      0.114    , -0.321263 , 0.311135 )
#define YIQ_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.9563   , -0.2721   , -1.1070   ,      0.6210   , -0.6474   , 1.7046   )

#define RGB_to_YUV  mat3x3( 0.299 , -0.14713 , 0.615    ,   0.587    , -0.28886  , -0.514991 ,      0.114    , 0.436     , -0.10001 )
#define YUV_to_RGB  mat3x3( 1.0   , 1.0      , 1.0      ,   0.0      , -0.39465  , 2.03211   ,      1.13983  , -0.58060  , 0.0      )

#define fetch(ofs,center,invx) texture2D(mpass_texture, vec2((ofs) * (invx) + center.x, center.y))

#define VFREQ (2.0*PI*color_texture_sz.y/4.0)
#define VPHASEDEG 45
#define VPHASE (VPHASEDEG)*PI/(180.0*VFREQ)
#define PROMINENCE 0.4
#define FLATNESS 1

#define GRILLE_PROMINENCE 0.5
#define GRILLE_COMP (1 + GRILLE_PROMINENCE/2.5)

#define GFREQ (2.0 * PI * screen_texture_sz.x / 3)
#define GPHASE 45
#define GRDEG 0
#define GGDEG 120
#define GBDEG 240
#define GR (GRDEG + GPHASE)*PI/(180.0*GFREQ)
#define GG (GGDEG + GPHASE)*PI/(180.0*GFREQ)
#define GB (GBDEG + GPHASE)*PI/(180.0*GFREQ)

float grille(float x, float phase) {
    return pow(sin((x + phase) * GFREQ), 2.0);
}

float scanline(float y, vec3 grille) {
    // scanlines
    float w = (y + VPHASE) * VFREQ;
    vec3 yuv = RGB_to_YUV * grille;
    float flatness = 2 - yuv.x * 2 * FLATNESS;  // more luminance = more flatness
    float sinw = abs(pow(sin(w), flatness));
    sinw = (1.0 - PROMINENCE) + sinw * PROMINENCE;    

    return sinw;
}

void main(void) {
    vec2 xy = gl_TexCoord[0].st;
    vec3 rgb = texture2D(mpass_texture, xy).xyz;

    float scan = scanline(xy.y, rgb);
    rgb = rgb * vec3(scan, scan, scan);

    // grille
    vec3 grille = vec3(grille(xy.x, GR), grille(xy.x, GG), grille(xy.x, GB));
    grille = (1.0 - GRILLE_PROMINENCE) + grille * GRILLE_PROMINENCE;
    rgb = rgb * grille * GRILLE_COMP;

    // scanlines
//    float scan = scanline(xy.y, grille);
//    rgb = rgb * vec3(scan, scan, scan);

    gl_FragColor = vec4(rgb, 1.0);
}

