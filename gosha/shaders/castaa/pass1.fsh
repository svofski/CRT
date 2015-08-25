#version 120

#define DYNAMIC_MATRICES

uniform sampler2D Texture0;
#define color_texture Texture0
#define TEXCOORD gl_TexCoord[0].st

uniform vec3 color_texture_sz;
uniform vec3 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;
uniform float time;

#ifdef DYNAMIC_MATRICES
#else
varying mat3 xform_Torus;
varying mat4 xform_WedgeCut;
varying mat4 xform_MotorSideCut;
varying mat3 xform_DiskSpin;
#endif

#define PI          3.14159265358

float sphere(vec3 q) {
#if 0
        float r;

        float scale = 1.0;
        float sparcity = 4.0;
        vec3 p;
        if (q.y < 2) {
            p = mod(q - vec3(scale * sparcity / 2.0), scale * sparcity) - vec3(scale * sparcity / 2.0);
            r = 1.0 + sin(length( (q - vec3(scale * sparcity / 2.0)) / (scale * sparcity)) + time);
        } else {
            p = q;
        }
#else
        vec3 p = q;
        float r = 1.8 + 0.2*sin(time);
#endif

    return length(p) - r;
}

float udBox( vec3 p, vec3 b )
{
    return length(max(abs(p) - b, 0.0)) - 0.05;
}

float sdTorus(vec3 p, vec2 t)
{
  vec2 q = vec2(length(p.xz)-t.x,p.y);
  return length(q)-t.y;
}

float sdCappedCylinderY(vec3 p, vec2 radius_height)
{
    vec2 d = abs(vec2(length(p.xz), p.y)) - radius_height;
    return min(max(d.x, d.y), 0.0) + length(max(d, 0.0));
}

float sdCappedCylinderZ(vec3 p, vec2 radius_height)
{
    vec2 d = abs(vec2(length(p.xy), p.z)) - radius_height;
    return min(max(d.x, d.y), 0.0) + length(max(d, 0.0));
}


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

float TorusTx(vec3 p, mat3 invm, vec2 t) {
    vec3 q = invm * p;
    return sdTorus(q.xyz, t);
}

float NiceTorus(vec3 p, vec2 radii) {
#ifdef DYNAMIC_MATRICES
    mat4 xform_Torus = mRot(radians(time*100 + gl_FragCoord.y), 0.0, radians(45.0), vec4(0.0, 0.0, 0.0, 1.0));
#endif
    return TorusTx(p, mat3(xform_Torus), radii);
}

vec2 difmax(in vec2 a, in vec2 b) {
    return (a.x > b.x) ? a : b;
}

vec2 difmin(in vec2 a, in vec2 b) {
    return (a.x < b.x) ? a : b;
}

// polynomial smooth min (k = 0.1);
vec2 smin_poly(in vec2 a, in vec2 b, float k)
{
    float h = clamp( 0.5+0.5*(b.x - a.x)/k, 0.0, 1.0 );
    return vec2(mix(b, a, h) - k*h*(1.0-h));
}

vec2 Difference(in vec2 d1, in vec2 d2) {
	vec2 d2m = vec2(-d2.x, d2.y);
	return difmax(d1, d2m);
}

float Difference(in float d1, in float d2) {
	return max(d1, -d2);
}

vec2 Intersect(vec2 d1, vec2 d2) {
	return difmax(d1, d2);
}

float Intersect(float d1, float d2) {
	return max(d1, d2);
}

vec2 Union(vec2 d1, vec2 d2) {
	return difmin(d1, d2);
}

float Union(float d1, float d2) {
	return min(d1, d2);
}

vec2 Blend(vec2 d1, vec2 d2) {
    return smin_poly(d1, d2, 1.0);//0.2 + 0.2 * sin(time/2.0));
}

/*
vec2 map(vec3 q) {
        float scale = 3.0;

#if 0
        float sparcity = 2.0;
        vec3 p = mod(q, scale * sparcity) - vec3(scale * sparcity / 2.0);
#else
        vec3 p = q;
#endif

        vec2 sphera = vec2(sphere(p), 3.0);
        vec2 box = vec2(udBox(p, vec3(0.4) * scale), 1.0);
        vec2 torus = vec2(NiceTorus(p + vec3(1.23*sin(time * 0.67), 0, 0), vec2(0.6, 0.2 + 0.19 * cos(time * 0.71)) * (scale + 0.6*sin(time)) ), 2.0);
        return Difference(Blend(box, sphera), torus);// Blend(box, torus); //
}
*/

float cylinder(in vec3 q, in vec2 radius_height, in vec3 offset) {
    vec3 xformedq = q + offset;
    return sdCappedCylinderZ(xformedq, radius_height);
}

#ifdef DYNAMIC_MATRICES
float rotbox_z(in vec3 q, in vec3 dimension, in float angle, in vec3 offset) {
    mat4 xform = mRot(0.0, 0.0, angle, vec4(offset, 1.0));
    vec3 xformedq = (xform * vec4(q, 1.0)).xyz;
    return udBox(xformedq, dimension);
}
#else
float box_matrix(in vec3 q, in vec3 dimension, in mat4 xform) {
    vec3 xformedq = (xform * vec4(q, 1.0)).xyz;
    return udBox(xformedq, dimension);
}
#endif

float ofsbox(in vec3 q, in vec3 dimension, in vec3 offset) {
    vec3 xformedq = q + offset;
    return udBox(xformedq, dimension);
}

vec2 floppy_door(in vec3 q, in float material) {
    q -= vec3(1.2/2.0 + 1.2/2.0 * sin(time), 0.0, 0.0);
    float door_metal = ofsbox(q, vec3(4.08/2, 3.05/2, .155), vec3(0.34, -3.05, 0.0));
    float door_die = ofsbox(q, vec3(1.1/2.0, 2.5/2.0, .20), vec3((9.0-1.1)/2 - 2.8, -(9.0-2.5-0.5)/2, 0.0));
    return vec2(Difference(door_metal, door_die), material);
}

vec2 disk(in vec3 q, in float mat_metal, in float mat_film) {
#ifdef DYNAMIC_MATRICES
    q = (mRot(0.0, 0.0, time * 0.71, vec4(0.0)) * vec4(q, 1.0)).xyz;
#else
    q = xform_DiskSpin * q;
#endif
    vec2 motor_grip_main = vec2(cylinder(q, vec2(2.6/2.0, .13), vec3(0.0, 0.0, -0.1)), mat_metal);
    vec2 surface = vec2(cylinder(q, vec2((8.9-0.1)/2.0, .01), vec3(0.0, 0.0, 0.0)), mat_film);
    motor_grip_main = Union(motor_grip_main, surface);

    float motor_grip_inner = cylinder(q, vec2(2.5/2.0, .13), vec3(0.0, 0.0, -0.05));
    float motor_grip_axis = ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(0.0));
#ifdef DYNAMIC_MATRICES
    float motor_side = rotbox_z(q, vec3(0.4/2.0, 0.8/2.0, .25), radians(20.0), vec3(0.8, 0.0, 0.0));
#else
    float motor_side = box_matrix(q, vec3(0.4/2.0, 0.8/2.0, .25), xform_MotorSideCut);
#endif
    float motor_grip_cut = Union(motor_grip_axis, motor_grip_inner);
    motor_grip_cut = Union(motor_grip_cut, motor_side);    
    vec2 disk = Difference(motor_grip_main, vec2(motor_grip_cut, mat_metal));

    return disk;
}

vec2 floppy_case(in vec3 q, in float material) {
    float box = udBox(q, vec3(4.5, 4.5, .15));
#ifdef DYNAMIC_MATRICES
    float wedge_cut = rotbox_z(q, vec3(6.5, 6.5, .15), radians(45.0), vec3(-0.55, 0.0, 0.0));
#else
    float wedge_cut = box_matrix(q, vec3(6.5, 6.5, .15), xform_WedgeCut);
#endif
    box = Intersect(box, wedge_cut);

    float door_cut_front = ofsbox(q, vec3(3.05, 3.05/2, .06), vec3(-0.6, -3.05, 0.3));
    float door_cut_rear  = ofsbox(q, vec3(3.05, 3.05/2, .06), vec3(-0.6, -3.05, -0.3));

    float sticker_cut_front = ofsbox(q, vec3(3.65, 5.5/2.0, .06), vec3(0.0, (9.0-5.5)/2, 0.3));
    float sticker_cut_rear = ofsbox(q, vec3(3.65, 1.8/2.0, .06), vec3(0.0, (9.0-1.8)/2, -0.3));
    float sticker_cut = Union(sticker_cut_front, sticker_cut_rear);

    float access_die = ofsbox(q, vec3(1.0/2.0, 2.5/2.0, .16), vec3(0.0, -(9.0-2.5-0.5)/2, 0));
    float motor_die = cylinder(q, vec2(2.7/2.0, .25), vec3(0.0, 0.0, -0.09));

    float sidecut_left = cylinder(q, vec2(0.45/2.0, .25), vec3(4.5, -(4.5-1.0), -0.09));
    float sidecut_right = cylinder(q, vec2(0.45/2.0, .25), vec3(-4.5, -(4.5-1.0), -0.09));
    float oval_left = cylinder(q, vec2(0.4/2.0, .25), vec3(4.5-0.4, -(4.5-1.7), -0.09));
    float oval_right = cylinder(q, vec2(0.4/2.0, .25), vec3(-(4.5-0.4), -(4.5-1.7), -0.09));

    // write-protect hole:
    // full-size cutout that goes mid-depth
    float wprot_hole = ofsbox(q, vec3(0.4/2.0, 0.8/2.0, .15), vec3(-(4.5-0.4), 4.5-0.6, -0.05));
    // the through hole
    wprot_hole = Union(wprot_hole,
            ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(-(4.5-0.4), 4.5-0.8, 0.0)));

    float small_cuts = Union(Union(Union(Union(sidecut_left, sidecut_right), oval_left), oval_right), wprot_hole);

    float cutout = Union(Union(Union(Union(door_cut_front, door_cut_rear), sticker_cut), access_die), motor_die);
    cutout = Union(cutout, small_cuts);
    return vec2(Difference(box, cutout), material);
}

vec2 map(vec3 q) {
    const float scale = 3.0;
    const float mat_purple = 1.0;
    const float mat_cyan = 2.0;
    const float mat_red = 3.0;

    // case
    vec2 floppy_case = floppy_case(q, mat_purple);

    float wprot_tab_ofs = 0.2 + 0.2*sin(time);
    vec2 wprot_tab = vec2(ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .15/2), vec3(-(4.5-0.4), 4.5-0.4-wprot_tab_ofs, -0.15/2)), mat_red);

    // door
    vec2 door = floppy_door(q, mat_cyan);

    // the disk
    vec2 disk = disk(q, mat_cyan, mat_red);
    //return floppy_case;
    vec2 diskette = Union(Union(Union(floppy_case, door), disk), wprot_tab);
    //return diskette;

    vec2 torus = vec2(NiceTorus(q + vec3(1.23*sin(time * 0.67), 0, 0), vec2(0.6, 0.2 + 0.19 * cos(time * 0.71)) * (scale + 0.6*sin(time)) ), 3.0);
    //return torus;
    return Blend(diskette, torus);
}

// x = distance, y = material
vec2 march(in vec3 origin, in vec3 r) {
    const float tmax = 25;
    const float precizion = 0.0001;
    float t = 0.0;
    float m = -1.0;
    for (int i = 0; i < 70; i++) {
        vec2 res = map(origin + r * t);
        if (abs(res.x) < precizion || t > tmax) {
            break;
        }
        t += res.x;
        m = res.y;
    }
    if (t > tmax) {
        m = -t;
    }

    return vec2(t, m);
}

vec3 calcNormal(in vec3 pos ) {
    vec3 eps = vec3( 0.001, 0.0, 0.0 );
    vec3 nor = vec3(
        map(pos+eps.xyy).x - map(pos-eps.xyy).x,
        map(pos+eps.yxy).x - map(pos-eps.yxy).x,
        map(pos+eps.yyx).x - map(pos-eps.yyx).x );
    return normalize(nor);
}

float calcAO( in vec3 pos, in vec3 nor )
{
    float occ = 0.0;
    float sca = 1.0;
    for(int i=0; i < 5; i++) {
        float hr = 0.01 + 0.12*float(i)/4.0;
        vec3 aopos =  nor * hr + pos;
        float dd = map(aopos).x;
        occ += -(dd-hr) * sca;
        sca *= 0.95;
    }
    return clamp(1.0 - 3.0*occ, 0.0, 1.0);
}

float softshadow(in vec3 ro, in vec3 rd, in float mint, in float tmax)
{
    float res = 1.0;
    float t = mint;
    for(int i = 0; i < 13; i++) {
        float h = map(ro + rd*t).x;
        res = min(res, 8.0*h/t);
        t += clamp(h, 0.02, 0.10);
        if (h < 0.001 || t > tmax)
        	break;
    }
    return clamp(res, 0.0, 1.0);
}

// const vec3[] colormap = vec3[] (
//         vec3(0.6, 0.2, 0.8),
//         vec3(0.2, 0.8, 0.6),
//         vec3(0.9, 0.3, 0.3)
//     );

const vec3[] colormap = vec3[] (
        vec3(0.2, 0.3, 0.8),
        vec3(0.8, 0.8, 0.8),
        vec3(0.9, 0.3, 0.3)
    );


vec3 render(in vec3 origin, in vec3 ray, in vec3 lightPos) {
    const float Ka = 0.2;
    const float Kd = 0.8;

    vec2 res = march(origin, ray);
    float t = res.x;
    float m = res.y;
    //vec3 color = vec3(-m/50.0);
    vec3 color = vec3(0.0, 0.0, 0.0);
    if (m > -0.5) {
        int material = int(m-1.0);
        color = mix(colormap[material], colormap[material+1], vec3(m - 1.0 - material));
        vec3 pos = origin + t * ray;
        vec3 normal = calcNormal(pos);
        vec3 reflection = reflect(ray, normal);

        float occ = calcAO(pos, normal);
        vec3 light = normalize(lightPos);

        float ambient = Ka * clamp(0.5 + 0.5 * normal.y, 0.0, 1.0);
        float diffuse = Kd * clamp(dot(normal, light), 0.0, 1.0);

        diffuse *= softshadow(pos, light, 0.01, 1.0); // shadows not farther away than 0.5
        float specular = diffuse * pow(clamp(dot(reflection, light), 0.0, 1.0), 36.0);

        color = color * ambient * occ + color * diffuse * Kd * occ + specular;
    }

    return color;
}

float fog(float t) {
    return 1.0 / (1.0 + t * t * 0.1);
}

mat3 setCamera(in vec3 ro, in vec3 ta, float cr) {
    vec3 cw = normalize(ta-ro);
    vec3 cp = vec3(sin(cr), cos(cr),0.0);
    vec3 cu = normalize( cross(cw,cp) );
    vec3 cv = normalize( cross(cu,cw) );
    return mat3( cu, cv, cw );
}

void main(void) {
    vec2 uv = gl_FragCoord.xy / screen_texture_sz.xy;
    uv = 2.0 * uv - 1.0;
    uv.x *= screen_texture_sz.x / screen_texture_sz.y;

    float lookFrom = 1;

    //vec3 lightPos = vec3(-sin(time)*8.0, sin(time), cos(time)*8.0);
    vec3 lightPos = vec3(0.3, 4, 4 * lookFrom);
    //lightPos = normalize(lightPos);

    vec2 drunk = vec2(sin(time), cos(time));
    //vec3 origin = vec3(uv + drunk, -3.0 + time + sin(time));
    //vec3 origin = vec3(uv, -3.0);
    //origin -= vec3(0.5, 0.5, 0.0);

    // camera
    const vec2 timewobble = vec2(0.25, 0.2);
    float bobtime = time + timewobble.x*uv.x*sin(time * 0.1) + timewobble.y*uv.y*cos(time * 0.13);
    vec3 origin = vec3(2 + 4.2 * cos(0.8*bobtime), 0 + 10.0 * sin(bobtime), 10 * lookFrom + 4.2 * sin(0.8*bobtime));
    //vec3 target = vec3( -0.5, -0.4, 0.5 );
    vec3 target = vec3(0.0, 0.0, 0.0);

    // camera-to-world transformation
    mat3 ca = setCamera(origin, target, 0.0);

    // ray direction
    vec3 rd = ca * normalize(vec3(uv, 2.5));


    //  vec3 r = normalize(vec3(uv, 1.0));
    vec3 color = render(origin, rd, lightPos);

    gl_FragColor = vec4(color, 1.0);
}
