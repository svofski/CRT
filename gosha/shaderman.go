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
	"github.com/howeyc/fsnotify"
)

type ShaderDescriptor struct {
	index int
	Name string
	VertSrc []string
	FragSrc []string
	Defaults *map[string]float32
	path string
}

type ShaderManager interface {
	Current() *ShaderDescriptor;
	LoadNext() 
}

type shaderStore struct {
	current int 
	shaders []*ShaderDescriptor
	dirmap map[string]*ShaderDescriptor
	watcher *fsnotify.Watcher
	commands chan Command
}

func NewShaderManager(commands chan Command) ShaderManager {
	return &shaderStore{current : -1, shaders: []*ShaderDescriptor{}, commands: commands}
}

func (store *shaderStore) init() {
	watcher, error := fsnotify.NewWatcher()
	if error != nil {
		fmt.Println("Could not initialize fsnotify, shader changes will not be automatically reloaded")
	} else {
		store.watcher = watcher
	}

	go func() {
		for event := range store.watcher.Event {
			dir := filepath.Dir(event.Name)
			descr, _ := store.dirmap[dir]
			//fmt.Println("fsnotify event: ", event, dir, descr)
			if descr != nil {
				store.loadShader(descr, nil)
				store.commands <- Command{Code: CmdLoadShader}
			}
		}
	}()

	basepath := "shaders"
	fileinfo, error := ioutil.ReadDir(basepath)
	if error == nil {
		channel := make(chan *ShaderDescriptor, len(fileinfo))

		for i, dir := range fileinfo {
			go func(collect chan *ShaderDescriptor, name string, where string, index int) {
				shader := ShaderDescriptor{index: index, Name: name, path: where}
				store.loadShader(&shader, watcher);
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
		store.dirmap = make(map[string]*ShaderDescriptor)
		for i := 0; i < len(collected); i++ {
			if len(collected[i].FragSrc) > 0 {
				store.shaders = append(store.shaders, collected[i])
				store.dirmap[collected[i].path] = collected[i]
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

func (store *shaderStore) loadShader(shader *ShaderDescriptor, watcher *fsnotify.Watcher) {
	shader.FragSrc = make([]string, 0, 9)
	for i := 1; i < 10; i++ {
		file := filepath.Join(shader.path, fmt.Sprintf("pass%d.fsh", i))
		text, _ := ioutil.ReadFile(file)
		if text != nil {
			shader.FragSrc = append(shader.FragSrc, string(text))
			if watcher != nil {
				watcher.Watch(file)
			}
		} else {
			break
		}
	}
}