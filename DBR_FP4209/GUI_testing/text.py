"""How to update a value in a text field with a callback."""

import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport()
dpg.setup_dearpygui()
# Dont use globals as storage -- at least wrap in a class
class DataValues():
	clicks = 0

def clickMe_callback(sender, value, user_data):
	# increment clickCount
	DataValues.clicks += 1

	# update text
	dpg.set_value(user_data, f"clicks: {DataValues.clicks}")

data = DataValues()

with dpg.window(label="Window 01", width=300, height=200, pos=[300, 300]):
	textControl = dpg.add_text("Clicks: 0")
	dpg.add_button(label="Click me !", callback=clickMe_callback, user_data=textControl)

dpg.create_viewport(title='Custom Title', width=800, height=600)
dpg.show_viewport()
dpg.start_dearpygui()