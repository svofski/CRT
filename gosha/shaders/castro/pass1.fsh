#version 120
//uniform sampler2D color_texture;

uniform sampler2D Texture0;
#define color_texture Texture0
#define TEXCOORD gl_TexCoord[0].st

//uniform vec2 color_texture_sz;
uniform vec3 color_texture_sz;
uniform vec3 screen_texture_sz;

uniform float filter_gain;
uniform float filter_invgain;


#define PI          3.14159265358

struct Rect
{
	bool Round;
	float Diag;
	vec3 Center;
	float RotZ;
	vec4 Color;
	bool Punch;
};

Rect chapeau;

Rect[] Rects = Rect[] (
		Rect(
			false,
			0.5, 
			vec3(0.5, 0.5, 0.0),
			radians(45.0),
			vec4(1.0, 0.0, 0.0, 1.0),
			false),
		Rect(false, 0.25, 
			vec3(0.25, 0.25, 0.0),
			radians(10.0),
			vec4(0.0, 1.0, 0.0, 0.5),
			false),
		Rect(false, 0.1,
			vec3(0.25, 0.25, 0.0),
			radians(-10.0),
			vec4(0.0, 1.0, 0.0, 1.0),
			false)
		// ---
		,Rect(false, 0.1, 
			vec3(0.7, 0.7, 0.0),
			radians(-20.0),
			vec4(1.0, 0.0, 1.0, 0.5),
			false),
		Rect(false, 0.1, 
			vec3(0.7, 0.7, 0.0),
			radians(-40.0),
			vec4(0.0, 1.0, 1.0, 0.5),
			false),
		Rect(true, 0.1,
			vec3(0.5, 0.5, 0.0),
			radians(-60.0),
			vec4(0.0, 1.0, 1.0, 1.0),
			false)
	);


bool inside(vec3[2] rect, vec2 xy) {
	return (xy.x >= rect[0].x) && (xy.x < rect[1].x) &&
		(xy.y >= rect[0].y) && (xy.y < rect[1].y);
}

int inside2(float diag, vec2 xy) {
	return int((xy.x >= -diag) && (xy.x < diag) && (xy.y >= -diag) && (xy.y < diag));
}

int inside_circle(float r, vec2 xy) {
	return int(xy.x * xy.x + xy.y * xy.y < r * r);
}

void main(void) {
	vec2 xy = gl_TexCoord[0].st;


	vec4 color = vec4(0.0, 0.0, 0.0, 1.0);

	for (int i = 0; i < Rects.length(); i++) {
		vec4 ray = vec4(xy, 0.0, 1.0);
		float cosphi = cos(Rects[i].RotZ);
		float sinphi = sin(Rects[i].RotZ);
		vec4 rot1 = vec4(cosphi, sinphi, 0, 0);
		vec4 rot2 = vec4(-sinphi, cosphi, 0, 0);
		vec4 rot3 = vec4(0, 0, 1, 0);
	
		mat4 rot = mat4(rot1, rot2, rot3, vec4(0.0));
		mat4 trans = mat4(1.0);
		trans[3] = vec4(-Rects[i].Center, 1.0);

		ray = trans * ray * rot;
		vec4 mixcolor = Rects[i].Color;
		if (Rects[i].Round) {
			mixcolor.a *= inside_circle(Rects[i].Diag, ray.xy);
		} else {
			mixcolor.a *= inside2(Rects[i].Diag, ray.xy);
		}
		color = mix(color, mixcolor, mixcolor.a);
	}

	gl_FragColor = color;
}