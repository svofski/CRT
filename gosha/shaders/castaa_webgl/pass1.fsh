#version 120

//uniform vec2 screen_texture_sz;

uniform vec3 color_texture_sz;
uniform vec3 screen_texture_sz;

uniform sampler2D colormap;
uniform float time;

#define PI          3.14159265358

float udBox(vec3 p, vec3 b)
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
    mat4 xform_Torus = mRot(radians(time*100.0 + gl_FragCoord.y), 0.0, radians(45.0), vec4(0.0, 0.0, 0.0, 1.0));
    return TorusTx(p, mat3(xform_Torus), radii);
}

float cylinder(in vec3 q, in vec2 radius_height, in vec3 offset) {
    vec3 xformedq = q + offset;
    return sdCappedCylinderZ(xformedq, radius_height);
}

vec2 difmax(in vec2 a, in vec2 b) {
    return (a.x > b.x) ? a : b;
}

vec2 difmin(in vec2 a, in vec2 b) {
    return (a.x < b.x) ? a : b;
}

// polynomial smooth min (k = 0.1);
// Mixed material encoded as mat_a * 10 + mat_b * 100, fractional part is mix value
vec2 smin_poly(in vec2 a, in vec2 b, in float k)
{
    float h = clamp(0.5 + 0.5*(b.x - a.x)/k, 0.0, 1.0);
    //return vec2(mix(b, a, h) - k*h*(1.0-h));
    float blend = mix(b.x, a.x, h) - k * h * (1.0 - h);
    float m1 = floor(a.y - 1.0) * 10.0;
    float m2 = floor(b.y - 1.0) * 100.0;
    float mat = m1 + m2 + clamp(1.0 - h, 0.0, 0.999);
    return vec2(blend, mat);
}

float smin_poly(in float a, in float b, in float k)
{
    float h = clamp(0.5 + 0.5*(b - a)/k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

vec2 Difference(in vec2 d1, in vec2 d2) {
	vec2 d2m = vec2(-d2.x, d2.y);
	return difmax(d1, d2m);
}

float Difference(in float d1, in float d2) {
	return max(d1, -d2);
}

vec2 Intersect(in vec2 d1, in vec2 d2) {
	return difmax(d1, d2);
}

float Intersect(in float d1, in float d2) {
	return max(d1, d2);
}

vec2 Union(in vec2 d1, in vec2 d2) {
	return difmin(d1, d2);
}

float Union(in float d1, in float d2) {
	return min(d1, d2);
}

vec2 Blend(in vec2 d1, in vec2 d2) {
    return smin_poly(d1, d2, 1.0);//0.2 + 0.2 * sin(time/2.0));
}

float Blend(in float d1, in float d2) {
    return smin_poly(d1, d2, 1.0);//0.2 + 0.2 * sin(time/2.0));
}

float rotbox_z(in vec3 q, in vec3 dimension, in float angle, in vec3 offset) {
    mat4 xform = mRot(0.0, 0.0, angle, vec4(offset, 1.0));
    vec3 xformedq = (xform * vec4(q, 1.0)).xyz;
    return udBox(xformedq, dimension);
}

float ofsbox(in vec3 q, in vec3 dimension, in vec3 offset) {
    vec3 xformedq = q + offset;
    return udBox(xformedq, dimension);
}

float ofsbox2(in vec3 q, in vec3 dimension, in vec3 offset) {
    vec3 xformedq = q + offset;
		//if (abs(xformedq.z) <= 0.5) {
			xformedq.z = mod(xformedq.z, 0.6) - 0.5 * 0.6;
		//}
    return udBox(xformedq, dimension);
}

float cylinder2(in vec3 q, in vec2 radius_height, in vec3 offset) {
    vec3 xformedq = q;
		xformedq.yz += offset.yz;
		float rep = offset.x*2.0;
		//if (abs(xformedq.x) < 5.0) {
			xformedq.x = mod(xformedq.x, rep ) - 0.5 * rep;
		//}
    return sdCappedCylinderZ(xformedq, radius_height);
}

float floppy_door_f(in vec3 q) {
    q -= vec3(1.2/2.0 + 1.2/2.0 * sin(time), 0.0, 0.0);
    float door_metal = ofsbox(q, vec3(4.08/2.0, 3.05/2.0, .155), vec3(0.34, -3.05, 0.0));
    float door_die = ofsbox(q, vec3(1.1/2.0, 2.5/2.0, .20), vec3((9.0-1.1)/2.0 - 2.8, -(9.0-2.5-0.5)/2.0, 0.0));
    return Difference(door_metal, door_die);
}

vec2 floppy_door(in vec3 q, in float material) {
    return vec2(floppy_door_f(q), material);
}

vec2 disk(in vec3 q, in float mat_metal, in float mat_film) {
    q = (mRot(0.0, 0.0, time * 0.71, vec4(0.0)) * vec4(q, 1.0)).xyz;
    vec2 motor_grip_main = vec2(cylinder(q, vec2(2.6/2.0, .13), vec3(0.0, 0.0, -0.1)), mat_metal);
    vec2 surface = vec2(cylinder(q, vec2((8.9-0.1)/2.0, .01), vec3(0.0, 0.0, 0.0)), mat_film);
    motor_grip_main = Union(motor_grip_main, surface);

    float motor_grip_inner = cylinder(q, vec2(2.5/2.0, .13), vec3(0.0, 0.0, -0.05));
    float motor_grip_axis = ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(0.0));
    float motor_side = rotbox_z(q, vec3(0.4/2.0, 0.8/2.0, .25), radians(20.0), vec3(0.8, 0.0, 0.0));
    float motor_grip_cut = Union(motor_grip_axis, motor_grip_inner);
    motor_grip_cut = Union(motor_grip_cut, motor_side);
    vec2 disk = Difference(motor_grip_main, vec2(motor_grip_cut, mat_metal));

    return disk;
}

float disk_f(in vec3 q) {
    q = (mRot(0.0, 0.0, time * 0.71, vec4(0.0)) * vec4(q, 1.0)).xyz;
    float motor_grip_main =cylinder(q, vec2(2.6/2.0, .13), vec3(0.0, 0.0, -0.1));
    float surface = cylinder(q, vec2((8.9-0.1)/2.0, .01), vec3(0.0, 0.0, 0.0));
    motor_grip_main = Union(motor_grip_main, surface);

    float motor_grip_inner = cylinder(q, vec2(2.5/2.0, .13), vec3(0.0, 0.0, -0.05));
    float motor_grip_axis = ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(0.0));
    float motor_side = rotbox_z(q, vec3(0.4/2.0, 0.8/2.0, .25), radians(20.0), vec3(0.8, 0.0, 0.0));
    float motor_grip_cut = Union(motor_grip_axis, motor_grip_inner);
    motor_grip_cut = Union(motor_grip_cut, motor_side);
    return Difference(motor_grip_main, motor_grip_cut);
}

float foppy_case_f(in vec3 q) {
    float box = udBox(q, vec3(4.5, 4.5, .15));
    float wedge_cut = rotbox_z(q, vec3(6.5, 6.5, .15), radians(45.0), vec3(-0.55, 0.0, 0.0));
    box = Intersect(box, wedge_cut);

		float door_cut = ofsbox2(q, vec3(3.05, 3.05/2.0, .06), vec3(-0.6, -3.05, 0.));

    float sticker_cut_front = ofsbox(q, vec3(3.65, 5.5/2.0, .06), vec3(0.0, (9.0-5.5)/2.0, 0.3));
    float sticker_cut_rear = ofsbox(q, vec3(3.65, 1.8/2.0, .06), vec3(0.0, (9.0-1.8)/2.0, -0.3));
    float sticker_cut = Union(sticker_cut_front, sticker_cut_rear);

    float access_die = ofsbox(q, vec3(1.0/2.0, 2.5/2.0, .16), vec3(0.0, -(9.0-2.5-0.5)/2.0, 0));
    float motor_die = cylinder(q, vec2(2.7/2.0, .25), vec3(0.0, 0.0, -0.09));

		float sidecuts = cylinder2(q, vec2(0.45/2.0, .25), vec3(4.5, -(4.5-1.0), -0.09));
		float ovals = cylinder2(q, vec2(0.4/2.0, .25), vec3(4.5-0.4, -(4.5-1.7), -0.09));

    // write-protect hole:
    // full-size cutout that goes mid-depth
    float wprot_hole = ofsbox(q, vec3(0.4/2.0, 0.8/2.0, .15), vec3(-(4.5-0.4), 4.5-0.6, -0.05));
    // the through hole
    wprot_hole = Union(wprot_hole,
            ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(-(4.5-0.4), 4.5-0.8, 0.0)));

    float small_cuts = Union(Union(sidecuts, ovals), wprot_hole);

    float cutout = Union(Union(Union(door_cut, sticker_cut), access_die), motor_die);
    cutout = Union(cutout, small_cuts);
    return Difference(box, cutout);
}

vec2 foppy_case(in vec3 q, in float material) {
    return vec2(foppy_case_f(q), material);
}

vec2 map(in vec3 q) {
    const float scale = 3.0;
    const float mat_purple = 1.0;
    const float mat_cyan = 2.0;
    const float mat_red = 3.0;

    // case
    //vec2 floppy_case = floppy_case(q, mat_purple);
    vec2 floppy_case = foppy_case(q, mat_purple);

    float wprot_tab_ofs = 0.2 + 0.2*sin(time);
    vec2 wprot_tab = vec2(ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .15/2.0),
    	vec3(-(4.5-0.4), 4.5-0.4-wprot_tab_ofs, -0.15/2.0)), mat_red);

    // door
    vec2 door = floppy_door(q, mat_cyan);
    // the disk
    vec2 disq = disk(q, mat_cyan, mat_red);

    vec2 diskette = Union(Union(Union(floppy_case, door), disq), wprot_tab);
		//vec2 diskette = Union(Union(disq, door), wprot_tab);
		//vec2 diskette = floppy_case;
		diskette.y = (diskette.y - 1.0) * 10.0;
		return diskette;
		// vec2 torus = vec2(NiceTorus(q + vec3(1.23*sin(time * 0.67), 0, 0), vec2(0.6, 0.2 + 0.19 * cos(time * 0.71)) * (scale + 0.6*sin(time))), mat_red);
		// return Blend(diskette, torus);
}

// x = distance, y = material
vec2 march(in vec3 origin, in vec3 r) {
    const float tmax = 25.0;
    const float precizion = 0.0001;
    float t = 0.0;
    float m = -1.0;
    for (int i = 0; i < 60; i++) {
        vec2 res = map(origin + r * t);
        if (abs(res.x) < precizion || t > tmax) {
            break;
        }
        t += res.x;
        m = res.y;
    }
		m = mix(m, 1000.0, float(t > tmax));

    return vec2(t, m);
}


vec3 calcNormal(in vec3 pos) {
    vec3 eps = vec3(0.001, 0.0, 0.0);
    vec3 nor = vec3(
        map(pos+eps.xyy).x - map(pos-eps.xyy).x,
        map(pos+eps.yxy).x - map(pos-eps.yxy).x,
        map(pos+eps.yyx).x - map(pos-eps.yyx).x );
    return normalize(nor);
}

float calcAO(in vec3 pos, in vec3 nor)
{
    float occ = 0.0;
    float sca = 2.0;
    for(int i=0; i < 4; i++) {
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
		float brk = 1.0;
		float h = 0.0;
    for(int i = 0; i < 11; i++) {
				h = map(ro + rd*t).x;
				res = min(res, 8.0*h/t);
				t += clamp(h, 0.02, 0.10);
				if (h < 0.001 || t > tmax)
					break;
    }
    return clamp(res, 0.0, 1.0);
}

const mat3 colormapm = mat3(
        vec3(0.2, 0.3, 0.8),
        vec3(0.8, 0.8, 0.8),
        vec3(0.9, 0.3, 0.3)
    );


#define GETCOLORT(index) texture2D(colormap, vec2(float(index)/3.0, 0.0)).rgb
#define GETCOLORM(index) mix(mix(colormapm[0], colormapm[1], clamp(float(index), 0.0, 1.0)), colormapm[2], clamp(float(index - 1), 0.0, 1.0))

vec4 render(in vec3 origin, in vec3 ray, in vec3 lightPos) {
    const float Ka = 0.2;
    const float Kd = 0.8;

    vec2 res = march(origin, ray);
    float t = res.x;
    float m = res.y;
    vec3 color = vec3(0.0, 0.0, 0.0);

		// decode and mix blended materials
    int index1 = int(mod(m/10.0, 10.0));
    int index2 = int(m/100.0);
    float mixratio = fract(m);
    color = mix(GETCOLORM(index1), GETCOLORM(index2), mixratio);

    vec3 pos = origin + t * ray;
    vec3 normal = calcNormal(pos);
    vec3 reflection = reflect(ray, normal);

    float occ = calcAO(pos, normal);
    vec3 light = normalize(lightPos);

    float ambient = Ka * clamp(0.5 + 0.5 * normal.y, 0.0, 1.0);
    float diffuse = Kd * clamp(dot(normal, light), 0.0, 1.0);
    diffuse *= softshadow(pos, light, 0.02, 1.0); // shadows not farther away than 1.0
    float specular = diffuse * pow(clamp(dot(reflection, light), 0.0, 1.0), 36.0);
    color = color * ambient * occ + color * diffuse * Kd * occ + specular;
		float alpha = 1.0 - floor(m/1000.0);
    return vec4(color * alpha,  alpha);
}

mat3 setCamera(in vec3 ro, in vec3 ta, float cr) {
    vec3 cw = normalize(ta - ro);
    vec3 cp = vec3(sin(cr), cos(cr), 0.0);
    vec3 cu = normalize(cross(cw,cp));
    vec3 cv = normalize(cross(cu,cw));
    return mat3( cu, cv, cw );
}

float rand_x(in vec2 co) {
  return fract(sin(dot(co.xy, vec2(12.9898,78.233))) * 43758.5453);
}

// License Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
// The input, n, should have a magnitude in the approximate range [0, 100].
// The output is pseudo-random, in the range [0,1].
// xaot88 @ Shadertoy
float Hash(float n)
{
	return fract( (1.0 + cos(n)) * 415.92653);
}

float rand(in vec2 x)
{
    float xhash = Hash( x.x * 37.0 );
    float yhash = Hash( x.y * 57.0 );
    return fract( xhash + yhash );
}

// Epic zooming star field. Only depends on rand(vec2).
// if STARFIELD_CHECKERS is defined, it uses a checker pattern instead of rand()
// STARFIELD_CHECKERS with STARFIELD_RANDOM is also a nice effect.
#define _STARFIELD_CHECKERS
#define STARFIELD_RANDOM

float checkers(in int x) {
	return float(int(mod(float(x), 2.0)) == int(x/2));
}

vec3 starfield(in vec2 xy) {
    const float speed1 = 2.0;
    const float speed2 = 0.43;
#ifdef STARFIELD_CHECKERS
    //const float[4] checkers = float[4] (0, 1.0, 1.0, 0.0);
#endif
    // find u,v coordinates of a cylinder projection
    float u = (atan(xy.y, xy.x) + PI)/(2.0 * PI);

#ifdef STARFIELD_RANDOM
    float rand_r1 = rand(vec2(0, floor(u * 100.0)));
    float rand_r2 = rand(vec2(floor(u * 100.0), rand_r1));
#else
    const float rand_r1 = 0.0;
    const float rand_r2 = 0.0;
#endif

    // altering radii shifts stars closer/farther to the viewing axis
    // multiply by rand_r1 or rand_r2 for radical perspective shifts
    float r = 0.8/(length(xy) + rand_r1);
    float r2 = 0.2/(length(xy) + rand_r2);

    // By altering v coordinate with time and added noise
    // we can modify speed of every star, or even make some of them
    // go in other direction
    float v1 = r * 10.0 + time * speed1 * (1.0 - 0.5 * rand_r2);
    float v2 = r2 * 10.0 + time * speed2 * (1.0 - 0.6 * rand_r1);

    // Handpicked values for rand() inputs
    float x = floor(u * 1800.0);
    float y1 = floor(mod(v1, 2.0) * 3.0);
    float y2 = floor(mod(v2, 2.0) * 13.0);

#ifdef STARFIELD_CHECKERS
    float color = (1.0 - rand_r1) * checkers(int(mod(floor(16.0 * u), 2.)) * 2 + int(mod(v1, 2.)));
#ifdef STARFIELD_RANDOM
    color += (1.0 - rand_r2) * checkers(int(mod(floor(16.0 * u), 2.)) * 2 + int(mod(v2, 2.)));
#endif
#else
    float color = float(int(rand(vec2(x, y1)) * 1000.0) == 6) * (0.5 - r/2.0);
    color += float(int(rand(vec2(x, y2)) * 1000.0) == 6) * (0.4 - r2*1.5);
#endif
    return vec3(color);
}


void main(void) {
    vec2 uv = gl_FragCoord.xy / screen_texture_sz.xy;
    uv = 2.0 * uv - 1.0;
    uv.x *= screen_texture_sz.x / screen_texture_sz.y;

    float lookFrom = 1.0;

    vec3 lightPos = vec3(0.3, 4.0, 4.0 * lookFrom);

    // camera
    const vec2 timewobble = vec2(0.25, 0.2);
    float bobtime = time + timewobble.x*uv.x*sin(time * 0.1) + timewobble.y*uv.y*cos(time * 0.13);
    vec3 origin = vec3(2.0 + 4.2 * cos(0.8*bobtime), 10.0 * sin(bobtime), 10.0 * lookFrom + 4.2 * sin(0.8*bobtime));
    vec3 target = vec3(0.0, 0.0, 0.0);

    // camera-to-world transformation
    mat3 ca = setCamera(origin, target, 0.0);

    // ray direction
    vec3 rd = ca * normalize(vec3(uv, 2.5));

    vec3 r = normalize(vec3(uv, 1.0));
    vec4 color = render(origin, rd, lightPos);
		color += (1.0 - color.a) * vec4(starfield(uv), 1.0);

    //color = vec4(starfield(uv), 1.0);
    gl_FragColor = color;
}