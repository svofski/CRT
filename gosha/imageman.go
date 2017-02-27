package main

import (
	"os"
	"log"
	"image"
	"image/draw"
	_ "image/png"
	_ "image/jpeg"
	"path/filepath"
	"fmt"
	)

type ImageLoader interface {
	Next() image.Image
}

type RealImageLoader struct {
	dir string
	current string
}

func NewImageLoader(basedir string) ImageLoader {
	return &RealImageLoader{dir: basedir}
}

func loadImage(filename string) image.Image {
    f, err := os.Open(filename)
    if err != nil {
        log.Println(err)
    }

    img, _, err := image.Decode(f)
    if err != nil {
        log.Println(err)
    }
    // to have consistent flippage in FBO buffers, we sabotage azul3d 
    // autoflipping. First we flip the source texture. The other part
    // of this is in the vertex shader where the texture coordinates
    // are flipped vertically.
    verticalFlip(img.(*image.RGBA))

    // If image has an odd number of lines, azul3d would miscalculate
    // texture coordinates, which would require an adjustment in 
    // the shader (y * 1.0 + 1/TextureHeight)
    // To avoid dealing with this, make a padded image with even
    // number of lines instead.
    if img.Bounds().Dy() % 2 == 1 {
    	img = addPadding(img)
    }
    return img
}

func addPadding(input image.Image) image.Image {
	bounds := input.Bounds()
	bounds.Max.Y++
	out := image.NewRGBA(bounds)
	draw.Draw(out, out.Bounds(), input, image.Point{0, 0}, draw.Src)
	return out
}

// sabotaging azul3d using its own code, thanks!
func verticalFlip(img *image.RGBA) {
    b := img.Bounds()
    rowCpy := make([]uint8, b.Dx()*4)
    for r := 0; r < (b.Dy() / 2); r++ {
        topRow := img.Pix[img.PixOffset(0, r):img.PixOffset(b.Dx(), r)]

        bottomR := b.Dy() - r - 1
        bottomRow := img.Pix[img.PixOffset(0, bottomR):img.PixOffset(b.Dx(), bottomR)]

        // Save bottom row.
        copy(rowCpy, bottomRow)

        // Copy top row to bottom row.
        copy(bottomRow, topRow)

        // Copy saved bottom row to top row.
        copy(topRow, rowCpy)
    }
}


func (loader *RealImageLoader) Next() (result image.Image) {
	globor, _ := filepath.Glob(filepath.Join(loader.dir, "*"))
	//fmt.Println("imgload: in path ", filepath.Join(loader.dir, "*"), " current=", loader.current, " globored: ", len(globor))
	for i, fu := range globor {
		if loader.current == "" {
			loader.current = fu
			fmt.Println("Trying to load: ", fu)
			result = loadImage(loader.current)
			if result == nil {
				loader.current = ""
				continue
			}
			if i + 1 == len(globor) {
				loader.current = ""
			}
			break
		}
		if fu == loader.current {
			loader.current = ""
		}
	}
	return
}


