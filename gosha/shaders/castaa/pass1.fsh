#version 120

uniform sampler2D Texture0;
#define color_texture Texture0
#define TEXCOORD gl_TexCoord[0].st

uniform vec3 color_texture_sz;
uniform vec3 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;
uniform float time;

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
		vec4(cosy * cosz, cosy * sinz, 	-siny, 0.0),
		vec4(cosz * sinx * siny - cosx * sinz, cosx * cosz + sinx * siny * sinz, cosy * sinx, 0.0),
		vec4(cosx * cosz * siny + sinx * sinz, cosx * siny * sinz - cosz * sinx, cosx * cosy, 0.0),
		translation
		);
}

float TorusTx(vec3 p, mat4 invm, vec2 t) {
	vec4 q = invm * vec4(p, 1.0);
	return sdTorus(q.xyz, t);
}

float NiceTorus(vec3 p, vec2 radii) {
	mat4 m = mRot(radians(time*100), 0.0, radians(45), vec4(0.0, 0.0, 0.0, 1.0));
	//mat4 m = mRot(0.0, 0.0, 0.0, vec4(0.0, 0.0, 0.0, 1.0));
	return TorusTx(p, m, radii);
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


// exponential smooth min (k = 32);
vec2 smin_exp(in vec2 a, in vec2 b, float k)
{
    float res = exp(-k*a.x) + exp(-k*b.x);
    vec2 r = vec2(-log(res)/k, 0.0);

		float kp = 1.0 - k / 20.0;
		float h = clamp(0.5+0.5*(b.x - a.x)/kp, 0.0, 1.0);
		r.y = mix(b.y, a.y, h) - kp * h * (1.0 - h);
		return r;
}

vec2 Difference(in vec2 d1, in vec2 d2) {
		vec2 d2m = vec2(-d2.x, d2.y);
	  return difmax(d1, d2m);
}

vec2 Intersect(vec2 d1, vec2 d2) {
	  return difmax(d1, d2);
}

vec2 Union(vec2 d1, vec2 d2) {
	  return difmin(d1, d2);
}

vec2 Blend(vec2 d1, vec2 d2) {
    return smin_poly(d1, d2, 0.4);
		//return smin_exp(d1, d2, 9.0);
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

float cylinder(vec3 q, vec2 radius_height, vec3 offset) {
	vec3 xformedq = q + offset;
	return sdCappedCylinderZ(xformedq, radius_height);
}

float rotbox_z(vec3 q, vec3 dimension, float angle, vec3 offset) {
	mat4 xform = mRot(0.0, 0.0, angle, vec4(offset, 1.0));
	vec3 xformedq = (xform * vec4(q, 1.0)).xyz;
	return udBox(xformedq, dimension);
}

float ofsbox(vec3 q, vec3 dimension, vec3 offset) {
	vec3 xformedq = q + offset;
	return udBox(xformedq, dimension);
}

vec2 floppy_door(vec3 q, float material) {
	q -= vec3(1.2/2.0 + 1.2/2.0 * sin(time), 0.0, 0.0);
	vec2 door_metal = vec2(ofsbox(q, vec3(4.08/2, 3.05/2, .15), vec3(0.34, -3.05, 0.0)), material);
	vec2 door_die = vec2(ofsbox(q, vec3(1.1/2.0, 2.5/2.0, .16), vec3((9.0-1.1)/2 - 2.8, -(9.0-2.5-0.5)/2, 0)), material);
	return Difference(door_metal, door_die);	
}

vec2 map(vec3 q) {
		float scale = 3.0;
		const float mat_purple = 1.0;
		const float mat_cyan = 2.0;
		const float mat_red = 3.0;

		// case
		vec2 box = vec2(udBox(q, vec3(4.5, 4.5, .15)), mat_purple);
		vec2 wedge_cut = vec2(rotbox_z(q, vec3(6.5, 6.5, .15), radians(45), vec3(-0.55, 0.0, 0.0)), mat_purple);
		box = Intersect(box, wedge_cut);
		
		vec2 door_cut_front = vec2(ofsbox(q, vec3(3.05, 3.05/2, .06), vec3(-0.6, -3.05, 0.3)), mat_purple);
		vec2 door_cut_rear  = vec2(ofsbox(q, vec3(3.05, 3.05/2, .06), vec3(-0.6, -3.05, -0.3)), mat_purple);

		vec2 sticker_cut_front = vec2(ofsbox(q, vec3(3.65, 5.5/2.0, .06), vec3(0.0, (9.0-5.5)/2, 0.3)), mat_purple);
		vec2 sticker_cut_rear = vec2(ofsbox(q, vec3(3.65, 1.8/2.0, .06), vec3(0.0, (9.0-1.8)/2, -0.3)), mat_purple);
		vec2 sticker_cut = Union(sticker_cut_front, sticker_cut_rear);

		vec2 access_die = vec2(ofsbox(q, vec3(1.0/2.0, 2.5/2.0, .16), vec3(0.0, -(9.0-2.5-0.5)/2, 0)), mat_purple);
		vec2 motor_die = vec2(cylinder(q, vec2(2.7/2.0, .25), vec3(0.0, 0.0, -0.09)), mat_purple);

		vec2 sidecut_left = vec2(cylinder(q, vec2(0.45/2.0, .25), vec3(4.5, -(4.5-1.0), -0.09)), mat_purple);
		vec2 sidecut_right = vec2(cylinder(q, vec2(0.45/2.0, .25), vec3(-4.5, -(4.5-1.0), -0.09)), mat_purple);
		vec2 oval_left = vec2(cylinder(q, vec2(0.4/2.0, .25), vec3(4.5-0.4, -(4.5-1.7), -0.09)), mat_purple);
		vec2 oval_right = vec2(cylinder(q, vec2(0.4/2.0, .25), vec3(-(4.5-0.4), -(4.5-1.7), -0.09)), mat_purple);
		
		// write-protect hole:
		// full-size rectangle
		vec2 wprot_hole = vec2(ofsbox(q, vec3(0.4/2.0, 0.8/2.0, .15), vec3(-(4.5-0.4), 4.5-0.6, -0.05)), mat_purple);
		// the through hole
		wprot_hole = Union(wprot_hole, 
				vec2(ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(-(4.5-0.4), 4.5-0.8, 0.0)), mat_purple));

		float wprot_tab_ofs = 0.2 + 0.2*sin(time);
		vec2 wprot_tab = vec2(ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .15/2), vec3(-(4.5-0.4), 4.5-0.4-wprot_tab_ofs, -0.15/2)), mat_red);

		vec2 small_cuts = Union(Union(Union(sidecut_left, sidecut_right), oval_left), oval_right);
		small_cuts = Union(small_cuts, wprot_hole);

		vec2 cutout = Union(Union(Union(Union(door_cut_front, door_cut_rear), sticker_cut), access_die), motor_die);
		cutout = Union(cutout, small_cuts);
		vec2 floppy_case = Difference(box, cutout);

		// door
		vec2 door = floppy_door(q, mat_cyan);

		// the disk 
		vec2 motor_grip_main = vec2(cylinder(q, vec2(2.6/2.0, .13), vec3(0.0, 0.0, -0.1)), mat_cyan);
		vec2 surface = vec2(cylinder(q, vec2((8.9-0.1)/2.0, .01), vec3(0.0, 0.0, 0.0)), mat_red);
		motor_grip_main = Union(motor_grip_main, surface);

		vec2 motor_grip_inner = vec2(cylinder(q, vec2(2.5/2.0, .13), vec3(0.0, 0.0, -0.05)), mat_cyan);
		vec2 motor_grip_axis = vec2(ofsbox(q, vec3(0.4/2.0, 0.4/2.0, .25), vec3(0.0)), mat_cyan);
		vec2 motor_side = vec2(rotbox_z(q, vec3(0.4/2.0, 0.8/2.0, .25), radians(20), vec3(0.8, 0.0, 0.0)), mat_cyan);
		vec2 motor_grip_cut = Union(motor_grip_axis, motor_grip_inner);
		motor_grip_cut = Union(motor_grip_cut, motor_side);
		vec2 disk = Difference(motor_grip_main, motor_grip_cut);

		return Union(Union(Union(floppy_case, door), disk), wprot_tab);
}



// x = distance, y = material
vec2 march(in vec3 origin, in vec3 r) {
	const float tmax = 30;
	const float precizion = 0.0001;
	float t = 0.0;
	float m = -1.0;
	for (int i = 0; i < 60; i++) {
		vec2 res = map(origin + r * t);
		if (res.x < precizion || res.x > tmax) {
			break;
		}
		t += res.x * 1.0;
		m = res.y;
	}
	if ( t > tmax) {
		m = -1.0;
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

const vec3[] colormap = vec3[] (
		vec3(0.6, 0.2, 0.8),
		vec3(0.2, 0.8, 0.6),
		vec3(0.9, 0.3, 0.3)
	);

vec3 render(in vec3 origin, in vec3 ray, in vec3 lightPos) {
		vec3 color = vec3(0.0, 0.0, 0.0);

		vec2 res = march(origin, ray);
		float t = res.x;
		float m = res.y;
		if (m > -0.5) {
				int material = int(m-1.0);
				color = mix(colormap[material], colormap[material+1], vec3(m - 1.0 - material));
				vec3 pos = origin + t * ray;
				vec3 normal = calcNormal(pos);

				float f = 10.0;
				float b = dot(normal, normalize(lightPos - pos));
				float rl = 15.;
				float dl = max(length(lightPos - pos) - rl, 0.0);
				float denom = dl/rl + 1.0;
				float attenuation = 1.0 / (denom*denom);
				float ambient = 0.09;
				color = vec3((b*color+pow(b, 40.0)) * (1.0 - f * 0.01) * attenuation * b + ambient);
		}

		return color;
}

float fog(float t) {
		return 1.0 / (1.0 + t * t * 0.1);
}

mat3 setCamera( in vec3 ro, in vec3 ta, float cr ) {
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

		//vec3 lightPos = vec3(-sin(time)*8.0, sin(time), cos(time)*8.0);
		vec3 lightPos = vec3(0.3, 5.3, -4);
		//lightPos = normalize(lightPos);

		vec2 drunk = vec2(sin(time), cos(time));
		//vec3 origin = vec3(uv + drunk, -3.0 + time + sin(time));
		//vec3 origin = vec3(uv, -3.0);
		//origin -= vec3(0.5, 0.5, 0.0);

		// camera
		vec3 origin = vec3(2 + 4.2 * cos(0.8*time), 0 + 10.0 * sin(time), 10 + 4.2 * sin(0.8*time));
		//vec3 target = vec3( -0.5, -0.4, 0.5 );
		vec3 target = vec3(0.0, 0.0, 0.0);

		// camera-to-world transformation
		mat3 ca = setCamera(origin, target, 0.0);

		// ray direction
		vec3 rd = ca * normalize(vec3(uv, 2.5));


		//	vec3 r = normalize(vec3(uv, 1.0));
		vec3 color = render(origin, rd, lightPos);

		gl_FragColor = vec4(color, 1.0);
}
