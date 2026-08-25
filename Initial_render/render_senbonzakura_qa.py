"""Render deterministic QA frames or a half-resolution preview animation."""

import os
import sys

import bpy


ROOT = bpy.path.abspath('//')
OUT = os.path.join(ROOT, 'revised_preview')


def configure():
    scene = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    scene.render.resolution_percentage = 50
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = True
    scene.render.use_file_extension = True
    scene.eevee.taa_render_samples = 32
    return scene


def keyframes(scene):
    frames = (1, 5, 9, 12, 16, 20, 28, 38, 48, 55, 60, 64, 68)
    key_dir = os.path.join(OUT, 'keyframes')
    os.makedirs(key_dir, exist_ok=True)
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(key_dir, f'senbonzakura_f{frame:03d}.png')
        bpy.ops.render.render(write_still=True)


def animation(scene):
    frame_dir = os.path.join(OUT, 'frames')
    os.makedirs(frame_dir, exist_ok=True)
    scene.render.filepath = os.path.join(frame_dir, 'senbonzakura_')
    bpy.ops.render.render(animation=True)


scene = configure()
if '--animation' in sys.argv:
    animation(scene)
else:
    keyframes(scene)
