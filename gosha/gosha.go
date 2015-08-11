package main

import (
	"fmt"
	//"os"; "log"
	_"math"
	"image"
	_ "image/png"
    "sync"
    "runtime"
	"azul3d.org/gfx.v1"
	"azul3d.org/gfx/window.v2"
	"azul3d.org/keyboard.v1"
	"azul3d.org/lmath.v1"
    "azul3d.org/clock.v1"
)

var glslVert = []byte(`
#version 120

attribute vec3 Vertex;
attribute vec2 TexCoord0;

uniform mat4 MVP;

varying vec2 tc0;

void main()
{
        //tc0 = TexCoord0;
        //gl_TexCoord[0]  = gl_TextureMatrix[0] * gl_MultiTexCoord0;
        gl_TexCoord[0].st = TexCoord0;
        gl_Position = MVP * vec4(Vertex, 1.0);
}
`)

func createShaders(manager ShaderManager, size image.Point) []*gfx.Shader {
    shaders := make([]*gfx.Shader, len(manager.Current().FragSrc))
    for i, fragSource := range manager.Current().FragSrc {
        shaders[i] = gfx.NewShader(fmt.Sprintf("%s-pass%d", manager.Current().Name, i+1))
        shaders[i].GLSLVert = glslVert
        shaders[i].GLSLFrag = []byte(fragSource)
        shaders[i].Inputs["color_texture_sz"] = gfx.Vec3{float32(size.X), float32(size.Y), 0.0}
        for uniform,value := range *manager.Current().Defaults {
            shaders[i].Inputs[uniform] = value
        }        
    }    
    fmt.Println("Created shaderset ", func() (res []string) { 
            for _,s := range shaders {
                res = append(res, s.Name)
            }
            return
        }())
    return shaders
}

func updateWindowTitle(w window.Window, descr *ShaderDescriptor) {
    props := w.Props()
    props.SetTitle(descr.Name + " {FPS}")
    w.Request(props)
}

func updateWindowSize(w window.Window, size image.Point) {
    props := w.Props()
    props.SetSize(size.X, size.Y)
    w.Request(props)
}

type CommandCode int
type Command struct {
    Code CommandCode
}

const CmdLoadShader     CommandCode = 0
const CmdNextShader     CommandCode = 1
const CmdQuit           CommandCode = 2
const CmdResize         CommandCode = 32
const CmdLoadImage      CommandCode = 33
const CmdImageLoaded    CommandCode = 34

type ShaderTargetPair struct {
    Shader *gfx.Shader
    Canvas gfx.Canvas
    MpassTex *gfx.Texture
    Camera *gfx.Camera
}

func handleEvents(events chan window.Event, commands chan Command) {
    var modifier keyboard.Key
    for e := range events {
        //fmt.Println(e)
        switch ev := e.(type) {
        case window.FramebufferResized:
            commands <- Command{Code: CmdResize}
        case keyboard.StateEvent:
            if ev.Key == keyboard.LeftSuper {
                if ev.State == keyboard.Down {
                    modifier = ev.Key
                } else {
                    modifier = 0
                }
            }
            if ev.State == keyboard.Down {
                if ev.Key == keyboard.Escape ||
                    (ev.Key == keyboard.Q && modifier == keyboard.LeftSuper) {
                    commands <- Command{Code: CmdQuit}
                }
                if ev.Key == keyboard.N {
                    commands <- Command{Code: CmdNextShader}
                }
                if ev.Key == keyboard.M {
                    commands <- Command{Code: CmdLoadImage}
                }
            }
        }
    }
}

func createCard(ratio float32, texture *gfx.Texture, shader *gfx.Shader) (card *gfx.Object) {    
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
}

func createTexture(bitmap image.Image) *gfx.Texture {
    tex := gfx.NewTexture()
    tex.Source = bitmap
    tex.MinFilter = gfx.Nearest // gfx.LinearMipmapLinear
    tex.MagFilter = gfx.Nearest // gfx.Linear
    tex.Format = gfx.DXT1RGBA
    return tex
}

func createMpassBuffers(r gfx.Renderer, bounds image.Rectangle) (rttTexture []*gfx.Texture, rttCanvas[]gfx.Canvas) {
    // create 2 textures for mpass ping ponging
    rttTexture = make([]*gfx.Texture, 2)
    rttCanvas = make([]gfx.Canvas, 2)
    for i, _ := range rttTexture {
        rttTexture[i] = createTexture(nil)

        // Choose a render to texture format.
        cfg := r.GPUInfo().RTTFormats.ChooseConfig(gfx.Precision{
            RedBits: 8, GreenBits: 8, BlueBits: 8, AlphaBits: 8,
        }, true)
        cfg.Color = rttTexture[i]
        cfg.Bounds = bounds
        rttCanvas[i] = r.RenderToTexture(cfg)
    }
    return
}

func gfxLoop(w window.Window, r gfx.Renderer) {
    shaderManager := NewShaderManager()
    imageLoader := NewImageLoader("../glsl/images")

    var shaders []*gfx.Shader
    var img image.Image
    var sourceTexture *gfx.Texture
    var card *gfx.Object
    var rttTexture []*gfx.Texture
    var rttCanvas []gfx.Canvas
    var rttCamera, screenCamera *gfx.Camera

    // Create a channel of events.
    events := make(chan window.Event, 256)
    commands := make(chan Command, 256)
    // Have the window notify our channel whenever events occur.
    w.Notify(events, window.FramebufferResizedEvents|window.KeyboardTypedEvents|window.KeyboardStateEvents)

    lock := sync.RWMutex{}
    //targets := []gfx.Canvas{}
    couples := []ShaderTargetPair{}

    running := true
    go handleEvents(events, commands)
    go func(commands chan Command) {
        for command := range commands {
            switch command.Code {
            case CmdQuit:
                running = false
            case CmdLoadImage:
                img = imageLoader.Next()// loadImage("../glsl/images/testcard.png")
                if img != nil {
                    //fmt.Println(img)
                    commands <- Command{Code: CmdImageLoaded}
                }
            case CmdImageLoaded:
                lock.Lock()
                sourceTexture = createTexture(img)
                card = createCard(float32(img.Bounds().Max.X) / float32(img.Bounds().Max.Y), nil, nil)
                rttTexture, rttCanvas = createMpassBuffers(r, img.Bounds())
                rttCamera = gfx.NewCamera()
                rttCamera.SetPos(lmath.Vec3{0, -2, 0})
                rttCamera.SetOrtho(img.Bounds(), 0.0001, 1000.0)
                screenCamera = gfx.NewCamera()
                screenCamera.SetPos(lmath.Vec3{0, -2, 0})
                lock.Unlock()
                go updateWindowSize(w, img.Bounds().Max)
                screenCamera.Lock()
                screenCamera.SetOrtho(r.Bounds(), 0.0001, 1000.0)
                screenCamera.Unlock()
                commands <- Command{Code: CmdLoadShader}
            case CmdResize:
                // Update the camera's projection matrix for the new width and
                // height.
                screenCamera.Lock()
                screenCamera.SetOrtho(r.Bounds(), 0.0001, 1000.0)
                screenCamera.Unlock()
            case CmdNextShader:
                shaderManager.LoadNext()
                commands <- Command{Code: CmdLoadShader}
            case CmdLoadShader:
                lock.Lock()

                shaders = createShaders(shaderManager, img.Bounds().Max)
                // init render targets: mpass canvases and main renderer
                couples = make([]ShaderTargetPair, len(shaders) - 1, len(shaders))
                for i := range couples {
                    couples[i] = ShaderTargetPair {
                            Shader: shaders[i],
                            Canvas: rttCanvas[i % 2],
                            MpassTex: rttTexture[(i + 1) % 2],
                            Camera: rttCamera,
                        }
                }
                couples = append(couples, ShaderTargetPair {
                        Shader: shaders[len(shaders) - 1],
                        Canvas: r,
                        MpassTex: rttTexture[len(shaders) % 2],
                        Camera: screenCamera,
                    })

                lock.Unlock()
                go updateWindowTitle(w, shaderManager.Current())
            }
        }
    }(commands)

    // Start with loading an image
    commands <- Command{Code: CmdLoadImage}

    clock := clock.New()
    clock.SetMaxFrameRate(70)

    for running {
        for card == nil {
            runtime.Gosched()
        }

        // Center the card in the window.
        b := r.Bounds()
        card.SetPos(lmath.Vec3{float64(b.Dx()) / 2.0, 0, float64(b.Dy()) / 2.0})

        // Scale the card to fit the window.
        s := float64(b.Dy()) / 2.0 // Card is two units wide, so divide by two.
        card.SetScale(lmath.Vec3{s, s, s})
        
        lock.Lock()
        for _, couple := range couples {
            couple.Canvas.Clear(image.Rect(0, 0, 0, 0), gfx.Color{1, 0, 1, 1})
            couple.Canvas.ClearDepth(image.Rect(0, 0, 0, 0), 1.0)

            card.Shader = couple.Shader
            // Texture0 is source, Texture1 is mpass source
            card.Textures = []*gfx.Texture{sourceTexture, couple.MpassTex}
            couple.Canvas.Draw(image.Rect(0, 0, 0, 0), card, couple.Camera)
            couple.Canvas.Render()
        }

        lock.Unlock()
        clock.Tick()
        runtime.Gosched()
    }    
    w.Close()
}

func main() {
	window.Run(gfxLoop, nil)
}