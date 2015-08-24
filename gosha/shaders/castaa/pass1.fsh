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

float sphere(vec3 p) {
	return length(p) - 1.0;
}

float udBox( vec3 p, vec3 b )
{
  	return length(max(abs(p) - b, 0.0)) - 0.1;
}

float sdTorus(vec3 p, vec2 t)
{
  vec2 q = vec2(length(p.xz)-t.x,p.y);
  return length(q)-t.y;
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

float TorusSomethingCube(vec3 p, float scale) {
	float d1 = udBox(p, vec3(0.4) * scale);
	float d2 = NiceTorus(p, vec2(0.6, 0.2) * scale);
	//return min(d1, d2); // union
	return max(-d2, d1); // diff
	//return max(d1, d2);

}

float AdInfinitum(vec3 p) {
	vec3 q = fract(p) * 2.0 - 1.0;
	return TorusSomethingCube(q, 1.0);
}

float Finitum(vec3 p) {
	mat4 m = mRot(radians(time*100), 0.0, radians(45), vec4(0.0, 0.0, 0.0, 1.0));
	vec4 q = m * vec4(p, 1.0);
	return TorusSomethingCube(p, 4.0);
	//return sphere(q.xyz);//TorusSomethingCube(p);
	//return NiceTorus(p);
}

float distance(vec3 p) {
	return Finitum(p);
}

vec2 difmax(in vec2 a, in vec2 b) {
	return (a.x > b.x) ? a : vec2(b.x, -b.y);//vec2(ax, 1.0) : vec2(bx, 1.0);
}

vec2 Difference(vec2 d1, vec2 d2) {
	//return max(d1, -d2);
	//return (d1.x > (-d2.x)) ? d1 : d2;
	return difmax(d1, -d2);
}

vec2 map(vec3 p) {
	float scale = 3.0;
	vec2 box = vec2(udBox(p, vec3(0.4) * scale), 1.0);
	vec2 torus = vec2(NiceTorus(p, vec2(0.6, 0.3) * (scale + 0.6*sin(time)) ), 2.0);
	return Difference(box, torus);
}

// x = distance, y = material
vec2 march(in vec3 origin, in vec3 r) {
	const float tmax = 30;
	const float precizion = 0.0001;
	float t = 0.0;
	float m = -1.0;
	for (int i = 0; i < 40; i++) {
		vec2 res = map(origin + r * t);
		if (abs(res.x) < precizion || res.x > tmax) {
			break;
		}
		t += res.x; // * 0.5;
		m = res.y;
	}
	if ( t > tmax) {
		m = -1.0;
	}
	
	return vec2(t, m);
}

vec3 calcNormal(in vec3 pos )
{
	vec3 eps = vec3( 0.001, 0.0, 0.0 );
	vec3 nor = vec3(
	    map(pos+eps.xyy).x - map(pos-eps.xyy).x,
	    map(pos+eps.yxy).x - map(pos-eps.yxy).x,
	    map(pos+eps.yyx).x - map(pos-eps.yyx).x );
	return normalize(nor);
}

const vec3[] colormap = vec3[] (
		vec3(0.6, 0.2, 0.8),
		vec3(0.2, 0.8, 0.6)
	);

vec3 render(in vec3 origin, in vec3 ray, in vec3 lightPos) {
	vec3 color = vec3(0.0, 0.0, 0.0);

	vec2 res = march(origin, ray);
	float t = res.x;
	float m = res.y;
	if (m > -0.5) {
		//color = vec3(0.6, 0.2+m, 0.8-m);
		color = colormap[int(m - 1.0)];
		vec3 pos = origin + t * ray;
		vec3 normal = calcNormal(pos);

	    float f = 10.0;
   		float b = dot(normal, normalize(lightPos - pos));
    	float rl = 15.;
    	float dl = max(length(lightPos - pos) - rl, 0.0);
    	float denom = dl/rl + 1.0;
		float attenuation = 1.0 / (denom*denom);    
    	float ambient = 0.05;    
		color = vec3((b*color+pow(b, 36.0))*(1.0 - f * 0.01) * attenuation * b + ambient);
	}

	return color;
}

float fog(float t) {
	return 1.0 / (1.0 + t * t * 0.1);
}

mat3 setCamera( in vec3 ro, in vec3 ta, float cr )
{
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
	vec3 origin = vec3( -0.5+3.2*cos(0.5*time), 5.0, -0.5 + 3.2*sin(0.5*time ) );
	//vec3 target = vec3( -0.5, -0.4, 0.5 );
	vec3 target = vec3( 0.0, 0.0, 0.0 );
	
	// camera-to-world transformation
    mat3 ca = setCamera( origin, target, 0.0 );

    // ray direction
	vec3 rd = ca * normalize( vec3(uv, 2.5) );


//	vec3 r = normalize(vec3(uv, 1.0));
	vec3 color = render(origin, rd, lightPos);
    
	gl_FragColor = vec4(color, 1.0);
}