import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from dearpygui_ext.themes import create_theme_imgui_light
from dearpygui_ext.themes import create_theme_imgui_dark

dpg.create_context()
dpg.create_viewport(title='Custom Title', width=600, height=600)




def set_light():
    light_theme = create_theme_imgui_light()
    dpg.bind_theme(light_theme)

def set_dark():
    dark_theme = create_theme_imgui_dark()
    dpg.bind_theme(dark_theme)


with dpg.window(label="main") as window_main:
    dark_button = dpg.add_button(label="Dark Theme", callback=lambda: dpg.bind_theme(0))
    light_button = dpg.add_button(label="Light Theme", callback=set_light)

    dpg.set_primary_window(window_main, True)

#demo.show_demo()




dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()