#!/usr/bin/env python

import glob
import json
import os
import textwrap

from copy import deepcopy

import pyglet
pyglet.resource.path = ['resources']
pyglet.resource.reindex()

# load all the .ttf fonts in the resources directory
ttf_paths = glob.glob(os.path.join('resources','*.ttf'))
for p in ttf_paths :
    pyglet.font.add_file(p)

# the main presentation window
dims = 1200, 900
window = pyglet.window.Window(*dims)

# global variables for current location
curr_section_id = 0
curr_question_id = 0
curr_stage_id = 0

# load questions from json file
section_fn = "test_questions.json"
sections = json.load(open(section_fn))

def draw_centered_multiline_label(label,**kwargs) :
    mod_kwargs = deepcopy(kwargs)
    line_height = label.content_height
    avg_pixels_per_char = label.content_width/len(mod_kwargs['text'])

    wrap_chars = (dims[0]*.75)/avg_pixels_per_char
    to_wrap = textwrap.wrap(mod_kwargs['text'],int(wrap_chars))
    num_lines = len(to_wrap)
    start_y = dims[1]/2+int(num_lines*line_height)/2

    for i, wrap_txt in enumerate(to_wrap) :
        mod_kwargs['y'] = start_y - i*line_height
        mod_kwargs['text'] = wrap_txt
        label = pyglet.text.Label(**mod_kwargs)
        label.draw()

def draw_scaled_multiline_label(label,**kwargs) :

    label = pyglet.text.Label(multiline=True,width=dims[0]*.9,**shadow_args)
    if label.content_height > dims[1]*.9 :
        shadow_args['font_size'] -= 1
        draw_scaled_multiline_label(label,**kwargs)
    else :
        label.draw()

dropshadow_offset = 2
dropshadow_level = 128 
def draw_dropshadow_label(**kwargs) :
    # shadow
    shadow_args = deepcopy(kwargs)
    shadow_args['y'] -= dropshadow_offset
    shadow_args['x'] += dropshadow_offset
    shadow_args['color'] = (dropshadow_level,)*3+(255,)
    label = pyglet.text.Label(**shadow_args)

    # the text might be too wide for the screen and multiline=True
    # doesn't center justify the way I want it, so split it up
    if label.content_width > dims[0]*.9 :
        draw_centered_multiline_label(label,**shadow_args)
        draw_centered_multiline_label(pyglet.text.Label(**kwargs),**kwargs)
    else :
        # shadow
        label.draw()

        # text
        label = pyglet.text.Label(**kwargs)
        label.draw()

def draw_dropshadow_multiline(**kwargs) :
    # shadow
    shadow_args = deepcopy(kwargs)
    shadow_args['y'] -= dropshadow_offset
    shadow_args['x'] += dropshadow_offset
    shadow_args['color'] = (dropshadow_level,)*3+(255,)
    label = pyglet.text.Label(multiline=True,width=dims[0]*.9,**shadow_args)
    IWASWORKINGHERE


last_sound_question = (-1,-1,-1)
last_player = None
def handle_stage_input(stage_txt,**label_args) :
    if stage_txt.startswith('img:') : # display image
        tag, path = stage_txt.split(':',1)
        img = pyglet.resource.image(path)
        img.anchor_x = img.width/2
        img.anchor_y = img.height/2
        img.blit(dims[0]/2,dims[1]/2)
    elif stage_txt.startswith('snd:') : # play sound
        tag, path = stage_txt.split(':',1)
        global last_sound_question, last_player
        if (curr_stage_id, curr_question_id, curr_section_id) != last_sound_question :
            if last_player is not None :
                try :
                    last_player.stop()
                except :
                    pass # whatever
            last_sound_question = curr_stage_id, curr_question_id, curr_section_id
            source = pyglet.media.load(os.path.join('resources',path))
            player = source.play()
            last_player = player
    else :
        if stage_txt.count('\n') != 0 :
            draw_dropshadow_multiline(text=stage_txt,**label_args)
        else :
            draw_dropshadow_label(text=stage_txt,**label_args)

def last_question() :
    global curr_stage_id, curr_question_id, curr_section_id
    curr_section_questions = sections[curr_section_id]["questions"]
    curr_question_id -= 1
    curr_stage_id = 0
    if curr_question_id < 0 :
        if curr_section_id > 0 :
            curr_section_id -= 1
            curr_question_id = len(curr_section_questions)-1
        else :
            curr_question_id = 0

def next_question() :
    global curr_stage_id, curr_question_id, curr_section_id
    curr_section_questions = sections[curr_section_id]["questions"]
    curr_question_id += 1
    curr_stage_id = 0
    if curr_question_id == len(curr_section_questions) :
        if curr_section_id == len(sections)-1 :
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

    # do background
    #TODO

    # read current question index
    global curr_question_id, curr_section_id
    curr_section = sections[curr_section_id]

    stage = curr_section["questions"][curr_question_id][curr_stage_id]
    font_name = curr_section.get("font")
    font = pyglet.font.load(font_name)
    label_args = {'font_name':font_name,
                  'font_size':36,
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
    if button == 1 :
        next_question()
    elif button == 4 :
        last_question()

@window.event
def on_text_motion(motion) :
    if motion == pyglet.window.key.MOTION_LEFT :
        last_question()
    elif motion == pyglet.window.key.MOTION_RIGHT :
        next_question()
    elif motion == pyglet.window.key.MOTION_UP :
        last_stage()
    elif motion == pyglet.window.key.MOTION_DOWN :
        next_stage()


if __name__ == '__main__' :
    pyglet.app.run()
