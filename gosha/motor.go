package main

import (
	"fmt"
	_ "io"
	"io/ioutil"
	"path/filepath"
	"bufio"
	"os"
	"strings"
	"strconv"
)

type ShaderDescriptor struct {
	index int
	Name string
	VertSrc []string
	FragSrc []string
	Defaults *map[string]float32
}

type ShaderManager interface {
	Current() *ShaderDescriptor;
	LoadNext() 
}

type shaderStore struct {
	current int 
	shaders []*ShaderDescriptor
}

func NewShaderManager() ShaderManager {
	return &shaderStore{current : -1, shaders: []*ShaderDescriptor{}}	 
}

func (store *shaderStore) init() {
	basepath := "shaders"
	fileinfo, error := ioutil.ReadDir(basepath)
	if error == nil {
		channel := make(chan *ShaderDescriptor, len(fileinfo))

		for i, dir := range fileinfo {
			go func(collect chan *ShaderDescriptor, name string, where string, index int) {
				shader := ShaderDescriptor{index: index, Name: name}
				for i := 1; i < 10; i++ {
					file := filepath.Join(where, fmt.Sprintf("pass%d.fsh", i))
					text, _ := ioutil.ReadFile(file)
					if text != nil {
						shader.FragSrc = append(shader.FragSrc, string(text))
					} else {
						break
					}
				}

				// read the defaults
				defaults := make(map[string] float32)
				file := filepath.Join(where, "defaults")
				f, _ := os.Open(file)
				if f != nil {
					for scanner := bufio.NewScanner(bufio.NewReader(f)); scanner.Scan(); {						
						s := scanner.Text()
						split := strings.Split(s, "=")
						if len(split) != 2 {
							fmt.Println("Erroneous entry in defaults: %s", s)
							continue
						} else {
							value,_ := strconv.ParseFloat(split[1], 32)
							defaults[split[0]] = float32(value)
						}
					}
				}
				shader.Defaults = &defaults

				collect <- &shader
			}(channel, dir.Name(), filepath.Join(basepath, dir.Name()), i)
		}

		collected := make([]*ShaderDescriptor, len(fileinfo))
		goodshaders := 0
		for i := 0; i < len(collected); i++ {
			shader := <- channel
			collected[shader.index] = shader
			if len(shader.FragSrc) > 0 {
				goodshaders++
			}
		}
		store.shaders = make([]*ShaderDescriptor, 0, goodshaders)
		for i := 0; i < len(collected); i++ {
			if len(collected[i].FragSrc) > 0 {
				store.shaders = append(store.shaders, collected[i])
			} else {
				fmt.Println("Discarding lame shader ", collected[i].Name)
			}
		}
		if len(store.shaders) > 0 {
			store.current = 0
		}
	}
	fmt.Printf("ShaderStore initialized: %d shaders, current = %d\n", len(store.shaders), store.current)
}

func (store *shaderStore) Current() *ShaderDescriptor {
	if store.current == -1 {
		store.init()
	}
	return store.shaders[store.current]
}

func (store *shaderStore) LoadNext() {
	store.current = (store.current + 1) % len(store.shaders)
}