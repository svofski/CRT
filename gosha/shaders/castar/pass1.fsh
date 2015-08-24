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
  	//vec3 q = fract(p) * 2.0 - 1.0;
  	vec3 q = p;
  	return length(max(abs(q)-b,0.0));
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

vec4 march(vec3 origin, vec3 r) {
	float t = 0.0;
	vec3 p;
	for (int i = 0; i < 40; i++) {
		p = origin + r * t;
		//float dist = udBox(p, vec3(0.2));//sphere(p);
		//float dist = sdTorus(p, vec2(0.5, 0.03));
		//float dist = NiceTorus(p);
		float dist = distance(p);
		if (abs(dist) < 0.001 || dist > 100) {
			break;
		}
		t += dist * 0.5;
	}
	vec4 pt = vec4(p, t);
	return pt;
}

float feck(float t) {
	return 1.0 / (1.0 + t * t * 0.1);
}

vec3 prim_c(in vec3 p)
{
  	return vec3(0.6,0.2,0.8);
}

vec3 calcNormal(in vec3 pos )
{
	vec3 eps = vec3( 0.0001, 0.0, 0.0 );
	vec3 nor = vec3(
	    distance(pos+eps.xyy) - distance(pos-eps.xyy),
	    distance(pos+eps.yxy) - distance(pos-eps.yxy),
	    distance(pos+eps.yyx) - distance(pos-eps.yyx) );
	return normalize(nor);
}

void main(void) {
	vec2 uv = gl_FragCoord.xy / screen_texture_sz.xy;
	uv = 2.0 * uv - 1.0;
	uv.x *= screen_texture_sz.x / screen_texture_sz.y;

    vec3 lightPos = vec3(-sin(time)*8.0, sin(time), cos(time)*8.0);
    //vec3 lightPos = vec3(0.3, 0.3, -4);
    //lightPos = normalize(lightPos);

	vec2 drunk = vec2(sin(time), cos(time));
	//vec3 origin = vec3(uv + drunk, -3.0 + time + sin(time));
	vec3 origin = vec3(uv, -3.0);
	//origin -= vec3(0.5, 0.5, 0.0);

	vec3 r = normalize(vec3(uv, 1.0));
	vec4 d = march(origin, r);
	vec3 color = prim_c(d.xyz);
	vec3 N = calcNormal(d.xyz);
	// float b=dot(N, normalize(lightPos - d.xyz));
 //    gl_FragColor = vec4(b, b, b, 1.0);

    // --- 
    float f = 10.0;
   	float b = dot(N, normalize(lightPos - d.xyz));
    float rl = 15.;
    float dl = max(length(lightPos - d.xyz) - rl, 0.0);
    float denom = dl/rl + 1.0;
	float attenuation = 1.0 / (denom*denom);
    
    float vis = b;
    
    float ambient = 0.015;
    
	gl_FragColor = vec4((b*color+pow(b, 36.0))*(1.0 - f * 0.01) * attenuation * vis + ambient, 1.0);
	//gl_FragColor = vec4((b*color) + pow(b, 36.0) +  ambient, 1.0);	


	// // gl_FragColor = vec4(vec3(feck(d.w)), 1.0);
}