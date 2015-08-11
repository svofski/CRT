package main

import (
	"os"
	"log"
	"image"
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
    return img
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


