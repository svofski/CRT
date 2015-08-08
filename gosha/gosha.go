package main

import (
	"fmt"
	"os"; "log"
	_"math"
	"image"
	_ "image/png"
	"azul3d.org/gfx.v1"
	"azul3d.org/gfx/window.v2"
	"azul3d.org/keyboard.v1"
	"azul3d.org/lmath.v1"
)

var glslVert = []byte(`
#version 120

attribute vec3 Vertex;
attribute vec2 TexCoord0;

uniform mat4 MVP;

varying vec2 tc0;

void main()
{
        tc0 = TexCoord0;
        gl_Position = MVP * vec4(Vertex, 1.0);
}
`)

var glslFrag = []byte(`
#version 120

varying vec2 tc0;

uniform sampler2D Texture0;
uniform bool BinaryAlpha;

void main()
{
        gl_FragColor = texture2D(Texture0, tc0);
        if(BinaryAlpha && gl_FragColor.a < 0.5) {
                discard;
        }
}
`)


func gfxLoop(w window.Window, r gfx.Renderer) {
    f, err := os.Open("../glsl/images/testcard.png")
    if err != nil {
        log.Fatal(err)
    }

    img, _, err := image.Decode(f)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println("Loaded image", img.Bounds())

    shader := gfx.NewShader("VulgarShader")
    shader.GLSLVert = glslVert
    shader.GLSLFrag = glslFrag

    // Create new texture.
    tex := func(bitmap image.Image) *gfx.Texture {
	    tex := gfx.NewTexture()
	    tex.Source = bitmap
	    tex.MinFilter = gfx.Nearest // gfx.LinearMipmapLinear
	    tex.MagFilter = gfx.Nearest // gfx.Linear
	    tex.Format = gfx.DXT1RGBA
	    return tex
	 }(img)

    card := func(ratio float32, texture *gfx.Texture, shader *gfx.Shader) (card *gfx.Object) {    
    	cardMesh := gfx.NewMesh()
	    cardMesh.Vertices = []gfx.Vec3 {
            // Bottom-left triangle.
            {-ratio, 0, -1},
            { ratio, 0, -1},
            {-ratio, 0,  1},

            // Top-right triangle.
            {-ratio, 0,  1},
            { ratio, 0, -1},
            { ratio, 0,  1},
	    }
	    cardMesh.TexCoords = []gfx.TexCoordSet{
            {
                Slice: []gfx.TexCoord{
                    {0, 1},
                    {1, 1},
                    {0, 0},

                    {0, 0},
                    {1, 1},
                    {1, 0},
                },
            },
	    }
	    // Create a card object.
	    card = gfx.NewObject()
	    card.AlphaMode = gfx.AlphaToCoverage
	    card.Shader = shader
	    card.Textures = []*gfx.Texture{texture}
	    card.Meshes = []*gfx.Mesh{cardMesh}
	    return card
	}(float32(img.Bounds().Max.X) / float32(img.Bounds().Max.Y), tex, shader)

	camera := gfx.NewCamera()
	camNear := 0.0001
	camFar := 1000.0
	camera.SetOrtho(r.Bounds(), camNear, camFar) // this is really weird
	camera.SetPos(lmath.Vec3{0, -2, 0})

    // resize the window to match image size
    go func(size image.Point) {
	    props := w.Props()
	    props.SetSize(size.X, size.Y)
	    w.Request(props)
	    fmt.Printf("Window resize request to %dx%d\n", size.X, size.Y)
	}(img.Bounds().Max)

    go func() {
        // Create a channel of events.
        events := make(chan window.Event, 256)

        // Have the window notify our channel whenever events occur.
        w.Notify(events, window.FramebufferResizedEvents|window.KeyboardTypedEvents)

        for e := range events {
            switch ev := e.(type) {
            case window.FramebufferResized:
                // Update the camera's projection matrix for the new width and
                // height.
                camera.Lock()
                camera.SetOrtho(r.Bounds(), camNear, camFar)
                camera.Unlock()

            case keyboard.TypedEvent:
            	if ev.Rune == 'q' {

            	}
                // if ev.Rune == 'm' || ev.Rune == 'M' {
                //     // Toggle mipmapping on the texture.
                //     tex.Lock()
                //     if tex.MinFilter == gfx.LinearMipmapLinear {
                //         tex.MinFilter = gfx.Linear
                //     } else {
                //         tex.MinFilter = gfx.LinearMipmapLinear
                //     }
                //     tex.Unlock()
                // }
            }
        }
    }()


    for {
        // Center the card in the window.
        b := r.Bounds()
        card.SetPos(lmath.Vec3{float64(b.Dx()) / 2.0, 0, float64(b.Dy()) / 2.0})

        // Scale the card to fit the window.
        s := float64(b.Dy()) / 2.0 // Card is two units wide, so divide by two.
        card.SetScale(lmath.Vec3{s, s, s})

        // Clear the entire area (empty rectangle means "the whole area").
        r.Clear(image.Rect(0, 0, 0, 0), gfx.Color{1, 0, 1, 1})
        r.ClearDepth(image.Rect(0, 0, 0, 0), 1.0)

        // Draw the textured card.
        r.Draw(image.Rect(0, 0, 0, 0), card, camera)

        // Render the whole frame.
        r.Render()
    }
}

func main() {
	window.Run(gfxLoop, nil)
}