#version 120

uniform sampler2D color_texture;
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

void main(void) {
    vec2 xy = gl_TexCoord[0].st;

    vec3 rgb = texture2D(color_texture, xy).xyz;
    vec3 yuv = RGB_to_YUV * rgb;
    float width_ratio = color_texture_sz.x / (FSC / FLINE);
    float height_ratio = color_texture_sz.y / VISIBLELINES;
    

    float t = xy.x * color_texture_sz.x;
    float wt = t * 2 * PI / width_ratio;

    float altv = mod(floor(xy.y * VISIBLELINES + 0.5), 2.0) * PI;
    float sinwt = sin(wt);
    float coswt = cos(wt + altv);

    float encoded = clamp(yuv.x + yuv.y * sinwt + yuv.z * coswt, 0.0, 1.0);
    gl_FragColor = vec4(encoded, encoded, encoded, 1.0);
}
