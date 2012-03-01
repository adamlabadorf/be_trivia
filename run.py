#!/usr/bin/env python

import glob
import json
import os
import re
import sys
import textwrap

from copy import deepcopy

from PIL import Image
import pyglet
pyglet.resource.path = ['resources']
pyglet.resource.reindex()

# load all the .ttf fonts in the resources directory
ttf_paths = glob.glob(os.path.join('resources','*.ttf'))
for p in ttf_paths :
    pyglet.font.add_file(p)

# load all the images as PIL images so we can scale them
# arbitrarily if we need to
img_paths = []
img_suffixes = ('.png','.jpg')
pil_imgs = {}
for suffix in img_suffixes :
    img_paths = glob.glob(os.path.join('resources','*%s'%suffix))
    for path in img_paths :
        img_dir, img_fn = os.path.split(path)
        pil_imgs[img_fn] = Image.open(path)
        
# the main presentation window
dims = 1200, 900
window = pyglet.window.Window(*dims)

# global variables for current location
curr_section_id = 0
curr_question_id = 0
curr_stage_id = 0

# store question labels so we only have to create them once
question_labels = {}

# load questions from json file
if len(sys.argv) == 1 :
    sys.stderr.write('Usage: %s <json file>'%(sys.argv[0]))
    sys.exit(1)
else :
    section_fn = sys.argv[1]
# our JSON format allows comments starting with #
# strip them out before sending to load
json_f = open(section_fn)
json_str = ''
for l in json_f :
    if l.strip().startswith('#') :
        continue
    else :
        json_str += re.sub('#.*$','',l)
sections = json.loads(json_str)

def get_centered_multiline_label(**kwargs) :
    label = pyglet.text.Label(**kwargs)
    
    mod_kwargs = deepcopy(kwargs)
    line_height = label.content_height
    avg_pixels_per_char = label.content_width/len(mod_kwargs['text'])

    wrap_chars = (dims[0]*.75)/avg_pixels_per_char
    to_wrap = textwrap.wrap(mod_kwargs['text'],int(wrap_chars))
    num_lines = len(to_wrap)
    start_y = dims[1]/2+int(num_lines*line_height)/2

    if line_height*num_lines > dims[1]*.9 :
        mod_kwargs['font_size'] -= 5
        return get_centered_multiline_label(**mod_kwargs)
    else :
        labels = []
        for i, wrap_txt in enumerate(to_wrap) :
            mod_kwargs['y'] = start_y - i*line_height
            mod_kwargs['text'] = wrap_txt
            label = pyglet.text.Label(**mod_kwargs)
            labels.append(label)
        return labels

def get_scaled_multiline_label(**kwargs) :

    label = pyglet.text.Label(multiline=True,width=dims[0]*.9,**kwargs)
    if label.content_height > dims[1]*.9 :
        shadow_args['font_size'] -= 1
        return get_scaled_multiline_label(label,**kwargs)
    else :
        return [label]

dropshadow_offset = 3
dropshadow_level = 0 
def get_dropshadowed_labels(**kwargs) :
    # shadow
    shadow_args = deepcopy(kwargs)
    shadow_args['y'] -= dropshadow_offset
    shadow_args['x'] += dropshadow_offset
    shadow_args['color'] = (dropshadow_level,)*3+(255,)
    shadow_label = get_centered_multiline_label(**shadow_args)
    
    label = get_centered_multiline_label(**kwargs)
    
    return label, shadow_label

def get_dropshadowed_multiline(**kwargs) :
    # shadow
    shadow_args = deepcopy(kwargs)
    shadow_args['y'] -= dropshadow_offset
    shadow_args['x'] += dropshadow_offset
    shadow_args['color'] = (dropshadow_level,)*3+(255,)
    shadow_label = get_scaled_multiline_label(**shadow_args)
    
    # actual text
    label = get_scaled_multiline_label(**kwargs)

    return label, shadow_label

def blit_scaled_image(path,x,y,w,h):
    pil_bg_img = pil_imgs[path]
    out = pil_bg_img.resize((w,h))
    bg_img = pyglet.image.ImageData(w,h,out.mode,out.tostring(),pitch=-w*len(out.mode))
    bg_sprite = pyglet.sprite.Sprite(bg_img)
    bg_sprite.draw()

last_sound_question = (None,)*3
player = None
def handle_stage_input(stage_txt,**label_args) :
    if stage_txt.startswith('img:') : # display image
        tag, path = stage_txt.split(':',1)
        img = pyglet.resource.image(path)
        img.anchor_x = img.width/2
        img.anchor_y = img.height/2
        # scale the image if necessary
        img_sprite = pyglet.sprite.Sprite(img)
        img_sprite.scale = min(1.*(dims[0]*.75)/img.width,1.*(dims[1]*.75)/img.height,1.)
        img_sprite.set_position(dims[0]/2,dims[1]/2)
        img_sprite.draw()
    elif stage_txt.startswith('snd:') : # play sound
        tag, path = stage_txt.split(':',1)
        global last_sound_question, player
        if (curr_stage_id, curr_question_id, curr_section_id) != last_sound_question :
            reset_player()
            last_sound_question = curr_stage_id, curr_question_id, curr_section_id
            source = pyglet.resource.media(path)
            player = source.play()
    elif stage_txt.startswith('vid:') : # play video
        tag, path = stage_txt.split(':',1)
        global last_sound_question, player
        if (curr_stage_id, curr_question_id, curr_section_id) != last_sound_question :
            reset_player()
            last_sound_question = curr_stage_id, curr_question_id, curr_section_id
            source = pyglet.resource.media(path)
            player = source.play()
        if player and player.playing :
            texture = player.get_texture()
            texture.anchor_x = texture.width/2
            texture.anchor_y = texture.height/2
            texture.blit(dims[0]/2,dims[1]/2)
    elif stage_txt.startswith('splash:') :
        tag, path = stage_txt.split(':',1)
        blit_scaled_image(path,0,0,dims[0],dims[1])
    else :
        
        label, shadow_label = question_labels.get(stage_txt,(None,None))
        if label is None or shadow_label is None :
            if stage_txt.count('\n') != 0 :
                label, shadow_label = get_dropshadowed_multiline(text=stage_txt,**label_args)
            else :
                label, shadow_label = get_dropshadowed_labels(text=stage_txt,**label_args)
            question_labels[stage_txt] = label, shadow_label
        for sublabel in shadow_label + label :
            sublabel.draw()

def reset_player() :
    global last_sound_question, player
    try:
        player.stop()
    except Exception, e:
            print e
            
    last_sound_question = (None,)*3
    player = None
    
def last_question() :
    global curr_stage_id, curr_question_id, curr_section_id
    curr_section_questions = sections[curr_section_id]["questions"]
    curr_question_id -= 1
    curr_stage_id = 0
    if curr_question_id < 0 :
        if curr_section_id > 0 :
            curr_section_id -= 1
            curr_section_questions = sections[curr_section_id]["questions"]
            curr_question_id = len(curr_section_questions)-1
            curr_stage_id = 0
        else :
            curr_question_id = 0

def next_question() :
    global curr_stage_id, curr_question_id, curr_section_id
    curr_section_questions = sections[curr_section_id]["questions"]
    curr_question_id += 1
    curr_stage_id = 0
    if curr_question_id == len(curr_section_questions) :
        if curr_section_id == len(sections)-1 :
            curr_section_questions = sections[curr_section_id]["questions"]
            curr_question_id = len(curr_section_questions)-1
        else :
            curr_section_id += 1
            curr_question_id = 0

def next_stage() :
    global curr_stage_id, curr_question_id, curr_section_id
    curr_question = sections[curr_section_id]["questions"][curr_question_id]
    curr_stage_id = min(curr_stage_id+1, len(curr_question)-1)

def last_stage() :
    global curr_stage_id, curr_question_id, curr_section_id
    curr_question = sections[curr_section_id]["questions"][curr_question_id]
    curr_stage_id = max(curr_stage_id-1, 0)

@window.event
def on_draw():
    window.clear()
    
    # read current question index
    global curr_question_id, curr_section_id
    curr_section = sections[curr_section_id]
    
    # do background
    blit_scaled_image(curr_section["bg"],0,0,dims[0],dims[1])
    
    stage = curr_section["questions"][curr_question_id][curr_stage_id]
    font_name = curr_section.get("font")
    font = pyglet.font.load(font_name)
    
    # per documentation, pyglet uses 96 DPI
    # calculate font size so it's 1/10 the
    # height of the screen
    font_size = (window.height/10)
    label_args = {'font_name':font_name,
                  'font_size':font_size,
                  'anchor_x':'center',
                  'anchor_y':'center',
                  'x': dims[0]/2,
                  'y': dims[1]/2
                 }

    # if a question stage is a list, do all of the things in it, you probably
    # only want to have just one text 
    if isinstance(stage,list) :
        for stage_i, stage_part in enumerate(stage) :
            handle_stage_input(stage_part,**label_args)
    else :
        handle_stage_input(stage,**label_args)

@window.event
def on_mouse_press(x,y,button,z):
    reset_player()
    if button == 1 :
        next_question()
    elif button == 4 :
        last_question()

@window.event
def on_text_motion(motion) :
    if motion == pyglet.window.key.MOTION_LEFT :
        reset_player()
        last_question()
    elif motion == pyglet.window.key.MOTION_RIGHT :
        reset_player()
        next_question()
    elif motion == pyglet.window.key.MOTION_UP :
        last_stage()
    elif motion == pyglet.window.key.MOTION_DOWN :
        next_stage()

@window.event
def on_key_press(k,m):
    if k == ord('f') :
        window.set_fullscreen(not window.fullscreen)
        window.display.get_default_screen()
        screen = window.display.get_default_screen()
        global dims, question_labels
        dims = window.width, window.height
        # will need to recache all the labels
        question_labels = {}
    elif k == ord('r') :
        reset_player()
        
if __name__ == '__main__' :
    pyglet.app.run()
